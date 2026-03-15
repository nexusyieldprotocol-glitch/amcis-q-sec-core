"""
AMCIS Memory Inspector
======================

Memory analysis for detecting:
- RWX (Read-Write-Execute) memory pages
- Code injection indicators
- Suspicious memory allocations
- Hollow process detection

NIST Alignment: SP 800-53 (SI-3 Malicious Code Protection)
"""

import hashlib
import os
import platform
import struct
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import structlog

try:
    from core.amcis_exceptions import EDRException, ErrorCode
    from core.amcis_error_utils import safe_method, timing_context, ignore_errors
except ImportError:
    from ..core.amcis_exceptions import EDRException, ErrorCode
    from ..core.amcis_error_utils import safe_method, timing_context, ignore_errors


class MemoryProtection(Enum):
    """Memory protection flags."""
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    NONE = auto()
    RWX = auto()  # Combined for convenience


class MemoryRegionType(Enum):
    """Types of memory regions."""
    CODE = auto()
    DATA = auto()
    HEAP = auto()
    STACK = auto()
    MMAP = auto()
    SHARED = auto()
    ANONYMOUS = auto()
    UNKNOWN = auto()


@dataclass
class MemoryRegion:
    """Memory region information."""
    start_address: int
    end_address: int
    size: int
    protection: Set[MemoryProtection]
    region_type: MemoryRegionType
    mapped_file: Optional[str] = None
    offset: int = 0
    inode: int = 0
    
    # Analysis results
    is_rwx: bool = False
    is_writable_executable: bool = False
    is_stack_executable: bool = False
    has_code_injection_indicators: bool = False
    entropy: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "start_address": hex(self.start_address),
            "end_address": hex(self.end_address),
            "size": self.size,
            "protection": [p.name for p in self.protection],
            "region_type": self.region_type.name,
            "mapped_file": self.mapped_file,
            "is_rwx": self.is_rwx,
            "is_writable_executable": self.is_writable_executable,
            "is_stack_executable": self.is_stack_executable,
            "has_code_injection_indicators": self.has_code_injection_indicators,
            "entropy": self.entropy
        }


@dataclass
class MemoryAnomaly:
    """Memory anomaly report."""
    pid: int
    region: MemoryRegion
    anomaly_type: str
    severity: str
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pid": self.pid,
            "region": self.region.to_dict(),
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "details": self.details
        }


class MemoryInspector:
    """
    AMCIS Memory Inspector
    ======================
    
    Memory analysis tool for detecting code injection,
    RWX pages, and other memory-based attacks.
    """
    
    # Entropy thresholds
    HIGH_ENTROPY_THRESHOLD = 7.0  # Encrypted/encoded data
    LOW_ENTROPY_THRESHOLD = 1.0   # Nulls/padding
    
    # Suspicious patterns (simplified shellcode indicators)
    SUSPICIOUS_OPCODES = [
        b'\x90\x90\x90\x90',  # NOP sled
        b'\xCC\xCC\xCC\xCC',  # INT3 (debugger trap)
        b'\xEB\xFE',          # Infinite jump
        b'\xE9\x00\x00\x00\x00',  # Jump to offset
    ]
    
    def __init__(self, kernel=None) -> None:
        """
        Initialize memory inspector.
        
        Args:
            kernel: AMCIS kernel reference
        """
        self.kernel = kernel
        self.logger = structlog.get_logger("amcis.memory_inspector")
        
        # Cache for process memory maps
        self._memory_maps: Dict[int, List[MemoryRegion]] = {}
        
        self.logger.info("memory_inspector_initialized")
    
    @safe_method(default=[], error_code=ErrorCode.MEMORY_ACCESS_DENIED, log=True)
    def inspect_process(self, pid: int) -> List[MemoryAnomaly]:
        """
        Inspect process memory for anomalies.
        
        Args:
            pid: Process ID to inspect
            
        Returns:
            List of memory anomalies
        """
        anomalies = []
        
        with timing_context(f"inspect_process_{pid}", threshold_ms=10000.0):
            regions = self._get_memory_map(pid)
            self._memory_maps[pid] = regions
            
            for region in regions:
                # Analyze each region
                self._analyze_region(region, pid)
                
                # Check for RWX
                if region.is_rwx:
                    anomalies.append(MemoryAnomaly(
                        pid=pid,
                        region=region,
                        anomaly_type="RWX_MEMORY",
                        severity="HIGH",
                        details={"region_size": region.size}
                    ))
                
                # Check for writable+executable (not necessarily read)
                elif region.is_writable_executable:
                    anomalies.append(MemoryAnomaly(
                        pid=pid,
                        region=region,
                        anomaly_type="WRITABLE_EXECUTABLE",
                        severity="MEDIUM",
                        details={"region_size": region.size}
                    ))
                
                # Check for executable stack
                elif region.is_stack_executable:
                    anomalies.append(MemoryAnomaly(
                        pid=pid,
                        region=region,
                        anomaly_type="EXECUTABLE_STACK",
                        severity="MEDIUM",
                        details={"region_size": region.size}
                    ))
                
                # Check for code injection indicators
                if region.has_code_injection_indicators:
                    anomalies.append(MemoryAnomaly(
                        pid=pid,
                        region=region,
                        anomaly_type="CODE_INJECTION_INDICATORS",
                        severity="HIGH",
                        details={
                            "region_size": region.size,
                            "entropy": region.entropy
                        }
                    ))
        
        return anomalies
    
    def _get_memory_map(self, pid: int) -> List[MemoryRegion]:
        """
        Get memory map for process.
        
        Args:
            pid: Process ID
            
        Returns:
            List of memory regions
        """
        if platform.system() == "Linux":
            return self._parse_linux_maps(pid)
        elif platform.system() == "Windows":
            return self._parse_windows_memory(pid)
        else:
            return []
    
    def _parse_linux_maps(self, pid: int) -> List[MemoryRegion]:
        """Parse /proc/PID/maps on Linux."""
        regions = []
        maps_file = Path(f"/proc/{pid}/maps")
        
        if not maps_file.exists():
            return regions
        
        try:
            with open(maps_file, 'r') as f:
                for line in f:
                    region = self._parse_maps_line(line)
                    if region:
                        regions.append(region)
        except (PermissionError, IOError) as e:
            self.logger.warning("maps_parse_error", pid=pid, error=str(e))
            raise EDRException(
                f"Failed to parse memory maps for PID {pid}",
                error_code=ErrorCode.MEMORY_ACCESS_DENIED,
                details={'pid': pid, 'error': str(e)}
            ) from e
        
        return regions
    
    def _parse_maps_line(self, line: str) -> Optional[MemoryRegion]:
        """Parse a single line from /proc/PID/maps."""
        parts = line.strip().split()
        if len(parts) < 2:
            return None
        
        # Parse address range
        addr_range = parts[0]
        if '-' not in addr_range:
            return None
        
        start_str, end_str = addr_range.split('-')
        try:
            start = int(start_str, 16)
            end = int(end_str, 16)
        except ValueError:
            return None
        
        # Parse permissions
        perms = parts[1] if len(parts) > 1 else "----"
        protection = set()
        
        if len(perms) >= 4:
            if perms[0] == 'r':
                protection.add(MemoryProtection.READ)
            if perms[1] == 'w':
                protection.add(MemoryProtection.WRITE)
            if perms[2] == 'x':
                protection.add(MemoryProtection.EXECUTE)
        
        # Parse offset, device, inode
        offset = int(parts[2], 16) if len(parts) > 2 else 0
        inode = int(parts[4]) if len(parts) > 4 else 0
        
        # Parse mapped file
        mapped_file = None
        if len(parts) > 5:
            mapped_file = parts[5]
        
        # Determine region type
        region_type = MemoryRegionType.UNKNOWN
        if mapped_file:
            if '[stack' in mapped_file:
                region_type = MemoryRegionType.STACK
            elif '[heap]' in mapped_file:
                region_type = MemoryRegionType.HEAP
            elif '[vdso]' in mapped_file or '[vsyscall]' in mapped_file:
                region_type = MemoryRegionType.CODE
            elif '.so' in mapped_file:
                region_type = MemoryRegionType.CODE
            else:
                region_type = MemoryRegionType.MMAP
        else:
            region_type = MemoryRegionType.ANONYMOUS
        
        region = MemoryRegion(
            start_address=start,
            end_address=end,
            size=end - start,
            protection=protection,
            region_type=region_type,
            mapped_file=mapped_file,
            offset=offset,
            inode=inode
        )
        
        # Determine RWX status
        region.is_rwx = (
            MemoryProtection.READ in protection and
            MemoryProtection.WRITE in protection and
            MemoryProtection.EXECUTE in protection
        )
        
        region.is_writable_executable = (
            MemoryProtection.WRITE in protection and
            MemoryProtection.EXECUTE in protection
        )
        
        region.is_stack_executable = (
            region_type == MemoryRegionType.STACK and
            MemoryProtection.EXECUTE in protection
        )
        
        return region
    
    def _parse_windows_memory(self, pid: int) -> List[MemoryRegion]:
        """Parse Windows process memory."""
        regions = []
        
        with ignore_errors(subprocess.SubprocessError, OSError):
            # Use VMMap or similar tool if available
            # For now, use basic WMI query
            result = subprocess.run(
                ["wmic", "process", "where", f"ProcessId={pid}", 
                 "get", "WorkingSetSize", "/format:value"],
                capture_output=True,
                text=True
            )
            
            # Windows memory inspection typically requires external tools
            # or the Windows API directly (VirtualQueryEx)
            self.logger.debug("windows_memory_inspect_stub", pid=pid)
        
        return regions
    
    def _analyze_region(self, region: MemoryRegion, pid: int) -> None:
        """Analyze memory region for anomalies."""
        # Skip regions we can't read
        if MemoryProtection.READ not in region.protection:
            return
        
        # Skip very large regions (would be too slow)
        if region.size > 100 * 1024 * 1024:  # 100MB
            return
        
        with ignore_errors(EDRException, OSError, IOError, ValueError):
            # Read memory content
            content = self._read_process_memory(pid, region.start_address, region.size)
            
            if content:
                # Calculate entropy
                region.entropy = self._calculate_entropy(content)
                
                # Check for injection indicators
                region.has_code_injection_indicators = self._check_injection_indicators(
                    content, region
                )
    
    def _read_process_memory(
        self,
        pid: int,
        address: int,
        size: int
    ) -> Optional[bytes]:
        """
        Read process memory.
        
        Args:
            pid: Process ID
            address: Start address
            size: Number of bytes to read
            
        Returns:
            Memory content or None
        """
        # Limit read size
        read_size = min(size, 64 * 1024)  # Max 64KB per region
        
        if platform.system() == "Linux":
            return self._read_linux_memory(pid, address, read_size)
        else:
            return None
    
    def _read_linux_memory(
        self,
        pid: int,
        address: int,
        size: int
    ) -> Optional[bytes]:
        """Read Linux process memory via /proc/PID/mem."""
        mem_file = Path(f"/proc/{pid}/mem")
        
        if not mem_file.exists():
            return None
        
        try:
            with open(mem_file, 'rb') as f:
                f.seek(address)
                return f.read(size)
        except (PermissionError, IOError, OSError):
            return None
    
    def _calculate_entropy(self, data: bytes) -> float:
        """
        Calculate Shannon entropy of data.
        
        Args:
            data: Binary data
            
        Returns:
            Entropy value (0-8 for bytes)
        """
        if not data:
            return 0.0
        
        from collections import Counter
        import math
        
        counts = Counter(data)
        length = len(data)
        
        entropy = 0.0
        for count in counts.values():
            p = count / length
            entropy -= p * math.log2(p)
        
        return entropy
    
    def _check_injection_indicators(
        self,
        content: bytes,
        region: MemoryRegion
    ) -> bool:
        """
        Check for code injection indicators.
        
        Args:
            content: Memory content
            region: Memory region
            
        Returns:
            True if injection indicators found
        """
        indicators = []
        
        # Check entropy (high entropy may indicate encrypted shellcode)
        if region.entropy > self.HIGH_ENTROPY_THRESHOLD:
            indicators.append("high_entropy")
        
        # Check for suspicious opcodes
        for pattern in self.SUSPICIOUS_OPCODES:
            if pattern in content[:4096]:  # Check first 4KB
                indicators.append(f"suspicious_pattern_{pattern.hex()}")
        
        # Check for MZ header (Windows executable) in unexpected location
        if content[:2] == b'MZ' and region.region_type not in (MemoryRegionType.CODE, MemoryRegionType.MMAP):
            indicators.append("embedded_pe_header")
        
        # Check for ELF header in unexpected location
        if content[:4] == b'\x7fELF' and region.region_type not in (MemoryRegionType.CODE, MemoryRegionType.MMAP):
            indicators.append("embedded_elf_header")
        
        return len(indicators) > 0
    
    @safe_method(default=None, error_code=ErrorCode.PROCESS_NOT_FOUND, log=True)
    def detect_hollow_process(self, pid: int) -> Optional[MemoryAnomaly]:
        """
        Detect process hollowing (executable replacement).
        
        Args:
            pid: Process ID
            
        Returns:
            Anomaly if hollowing detected
        """
        # Get process executable path
        exe_path = os.readlink(f"/proc/{pid}/exe")
        
        # Get mapped executable regions
        regions = self._get_memory_map(pid)
        code_regions = [
            r for r in regions
            if r.region_type == MemoryRegionType.CODE and
            r.mapped_file == exe_path
        ]
        
        if not code_regions:
            return None
        
        # Check if code regions are writable (suspicious)
        for region in code_regions:
            if MemoryProtection.WRITE in region.protection:
                return MemoryAnomaly(
                    pid=pid,
                    region=region,
                    anomaly_type="PROCESS_HOLLOWING",
                    severity="CRITICAL",
                    details={
                        "exe_path": exe_path,
                        "writable_code_region": True
                    }
                )
        
        return None
    
    @safe_method(default={}, error_code=ErrorCode.EDR_ERROR, log=True)
    def scan_all_processes(self) -> Dict[int, List[MemoryAnomaly]]:
        """
        Scan all accessible processes.
        
        Returns:
            Dictionary mapping PID to anomalies
        """
        results = {}
        
        with timing_context("scan_all_processes", threshold_ms=30000.0):
            for pid_dir in Path("/proc").glob("[0-9]*"):
                with ignore_errors(ValueError):
                    pid = int(pid_dir.name)
                    anomalies = self.inspect_process(pid)
                    if anomalies:
                        results[pid] = anomalies
        
        return results
    
    def get_process_statistics(self, pid: int) -> Dict[str, Any]:
        """Get memory statistics for process."""
        regions = self._memory_maps.get(pid, [])
        
        total_size = sum(r.size for r in regions)
        rwx_count = sum(1 for r in regions if r.is_rwx)
        anonymous_size = sum(
            r.size for r in regions
            if r.region_type == MemoryRegionType.ANONYMOUS
        )
        
        return {
            "pid": pid,
            "total_regions": len(regions),
            "total_size_mb": total_size / (1024 * 1024),
            "rwx_regions": rwx_count,
            "anonymous_size_mb": anonymous_size / (1024 * 1024),
            "executable_regions": sum(
                1 for r in regions
                if MemoryProtection.EXECUTE in r.protection
            )
        }
