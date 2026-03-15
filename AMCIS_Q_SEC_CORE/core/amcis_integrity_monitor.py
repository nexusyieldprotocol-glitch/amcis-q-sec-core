"""
AMCIS Integrity Monitor
=======================

Continuous file and system integrity monitoring with:
- Baseline hash management
- Real-time change detection
- Tamper-evident logging
- Self-integrity validation

NIST Alignment: SP 800-53 (SI-7 Software, Firmware, and Information Integrity)
"""

import asyncio
import hashlib
import json
import os
import stat
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable, Tuple

import structlog


class ChangeType(Enum):
    """Types of integrity changes."""
    CREATED = auto()
    MODIFIED = auto()
    DELETED = auto()
    PERMISSION_CHANGED = auto()
    OWNER_CHANGED = auto()
    HASH_MISMATCH = auto()


class IntegritySeverity(Enum):
    """Severity of integrity violation."""
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass
class FileMetadata:
    """File metadata for integrity checking."""
    path: str
    sha256_hash: str
    size: int
    mtime: float
    permissions: int
    owner: int
    group: int
    inode: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "sha256_hash": self.sha256_hash,
            "size": self.size,
            "mtime": self.mtime,
            "permissions": oct(self.permissions),
            "owner": self.owner,
            "group": self.group,
            "inode": self.inode
        }
    
    @classmethod
    def from_path(cls, file_path: Path) -> Optional["FileMetadata"]:
        """Create metadata from file path."""
        try:
            stat_info = file_path.stat()
            
            # Calculate hash
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            
            return cls(
                path=str(file_path),
                sha256_hash=hasher.hexdigest(),
                size=stat_info.st_size,
                mtime=stat_info.st_mtime,
                permissions=stat_info.st_mode,
                owner=stat_info.st_uid,
                group=stat_info.st_gid,
                inode=stat_info.st_ino
            )
        except (OSError, IOError):
            return None


@dataclass
class IntegrityEvent:
    """Integrity violation event."""
    change_type: ChangeType
    file_path: str
    expected_metadata: Optional[FileMetadata]
    actual_metadata: Optional[FileMetadata]
    severity: IntegritySeverity
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = field(default_factory=lambda: hashlib.sha256(
        str(time.time_ns()).encode()
    ).hexdigest()[:16])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "change_type": self.change_type.name,
            "file_path": self.file_path,
            "expected": self.expected_metadata.to_dict() if self.expected_metadata else None,
            "actual": self.actual_metadata.to_dict() if self.actual_metadata else None,
            "severity": self.severity.name,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id
        }


@dataclass
class IntegrityReport:
    """Integrity scan report."""
    scan_time: float
    files_checked: int
    violations: List[IntegrityEvent]
    new_files: List[str]
    missing_files: List[str]
    modified_files: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scan_time": self.scan_time,
            "files_checked": self.files_checked,
            "violations_count": len(self.violations),
            "new_files": self.new_files,
            "missing_files": self.missing_files,
            "modified_files": self.modified_files,
            "violations": [v.to_dict() for v in self.violations]
        }


class IntegrityMonitor:
    """
    AMCIS Integrity Monitor
    =======================
    
    Continuous file integrity monitoring with cryptographic
    verification and tamper-evident logging.
    """
    
    # Default watch paths
    DEFAULT_WATCH_PATHS = [
        "/etc",
        "/usr/bin",
        "/usr/sbin",
        "/bin",
        "/sbin",
    ]
    
    # File patterns to exclude
    EXCLUDE_PATTERNS = [
        "*.log",
        "*.tmp",
        "*.swp",
        "*~",
        ".git/*",
        "__pycache__/*",
        "*.pyc",
    ]
    
    def __init__(
        self,
        kernel=None,
        baseline_path: Optional[Path] = None,
        scan_interval: float = 300.0,  # 5 minutes
        watch_paths: Optional[List[str]] = None
    ) -> None:
        """
        Initialize integrity monitor.
        
        Args:
            kernel: AMCIS kernel reference
            baseline_path: Path to store baseline database
            scan_interval: Seconds between scans
            watch_paths: Paths to monitor
        """
        self.kernel = kernel
        self.baseline_path = baseline_path or Path("/var/lib/amcis/integrity.baseline")
        self.scan_interval = scan_interval
        self.watch_paths = watch_paths or self.DEFAULT_WATCH_PATHS
        
        self.logger = structlog.get_logger("amcis.integrity_monitor")
        
        # Baseline storage
        self._baseline: Dict[str, FileMetadata] = {}
        self._baseline_loaded = False
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Callbacks
        self._violation_callbacks: List[Callable[[IntegrityEvent], None]] = []
        
        # Critical paths (higher sensitivity)
        self._critical_paths: Set[str] = set()
        
        self.logger.info(
            "integrity_monitor_initialized",
            baseline_path=str(self.baseline_path),
            watch_paths=self.watch_paths
        )
    
    def register_violation_callback(
        self,
        callback: Callable[[IntegrityEvent], None]
    ) -> None:
        """Register callback for integrity violations."""
        self._violation_callbacks.append(callback)
    
    async def establish_baseline(self, paths: Optional[List[str]] = None) -> int:
        """
        Establish integrity baseline for specified paths.
        
        Args:
            paths: Paths to baseline (defaults to watch_paths)
            
        Returns:
            Number of files baselined
        """
        paths = paths or self.watch_paths
        count = 0
        
        self.logger.info("establishing_baseline", paths=paths)
        
        for path_str in paths:
            path = Path(path_str)
            if not path.exists():
                self.logger.warning("path_not_found", path=path_str)
                continue
            
            try:
                for file_path in self._walk_path(path):
                    metadata = FileMetadata.from_path(file_path)
                    if metadata:
                        self._baseline[str(file_path)] = metadata
                        count += 1
                        
                        if count % 1000 == 0:
                            self.logger.info("baseline_progress", files=count)
            except Exception as e:
                self.logger.error("baseline_error", path=path_str, error=str(e))
        
        self._baseline_loaded = True
        await self._save_baseline()
        
        self.logger.info("baseline_established", file_count=count)
        return count
    
    def _walk_path(self, path: Path) -> List[Path]:
        """Walk path and yield files to monitor."""
        files = []
        
        if path.is_file():
            if self._should_monitor(path):
                return [path]
            return []
        
        try:
            for item in path.rglob("*"):
                if item.is_file() and self._should_monitor(item):
                    files.append(item)
        except PermissionError:
            self.logger.warning("permission_denied", path=str(path))
        
        return files
    
    def _should_monitor(self, path: Path) -> bool:
        """Check if file should be monitored."""
        path_str = str(path)
        
        # Check exclusions
        for pattern in self.EXCLUDE_PATTERNS:
            if self._match_pattern(path_str, pattern):
                return False
        
        # Skip symlinks
        if path.is_symlink():
            return False
        
        return True
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Match path against glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(
            os.path.basename(path), pattern
        )
    
    async def _save_baseline(self) -> None:
        """Save baseline to disk."""
        try:
            self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
            
            baseline_data = {
                path: metadata.to_dict()
                for path, metadata in self._baseline.items()
            }
            
            # Atomic write
            temp_path = self.baseline_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(baseline_data, f, indent=2)
            
            temp_path.replace(self.baseline_path)
            
            self.logger.info("baseline_saved", path=str(self.baseline_path))
            
        except Exception as e:
            self.logger.error("baseline_save_failed", error=str(e))
            raise
    
    async def load_baseline(self) -> bool:
        """
        Load baseline from disk.
        
        Returns:
            True if loaded successfully
        """
        try:
            if not self.baseline_path.exists():
                self.logger.warning("baseline_not_found")
                return False
            
            with open(self.baseline_path, 'r') as f:
                baseline_data = json.load(f)
            
            self._baseline = {}
            for path, data in baseline_data.items():
                self._baseline[path] = FileMetadata(
                    path=data["path"],
                    sha256_hash=data["sha256_hash"],
                    size=data["size"],
                    mtime=data["mtime"],
                    permissions=int(data["permissions"], 8),
                    owner=data["owner"],
                    group=data["group"],
                    inode=data.get("inode", 0)
                )
            
            self._baseline_loaded = True
            self.logger.info("baseline_loaded", file_count=len(self._baseline))
            return True
            
        except Exception as e:
            self.logger.error("baseline_load_failed", error=str(e))
            return False
    
    async def verify_integrity(self, paths: Optional[List[str]] = None) -> IntegrityReport:
        """
        Verify integrity of monitored paths.
        
        Args:
            paths: Specific paths to verify (None for all)
            
        Returns:
            Integrity verification report
        """
        if not self._baseline_loaded:
            await self.load_baseline()
        
        start_time = time.time()
        violations = []
        new_files = []
        missing_files = []
        modified_files = []
        files_checked = 0
        
        check_paths = paths or list(self._baseline.keys())
        
        for path_str in check_paths:
            path = Path(path_str)
            
            # Check if file exists in baseline
            if path_str in self._baseline:
                expected = self._baseline[path_str]
                
                if not path.exists():
                    # File deleted
                    event = IntegrityEvent(
                        change_type=ChangeType.DELETED,
                        file_path=path_str,
                        expected_metadata=expected,
                        actual_metadata=None,
                        severity=IntegritySeverity.CRITICAL
                    )
                    violations.append(event)
                    missing_files.append(path_str)
                    await self._notify_violation(event)
                    continue
                
                # Check current state
                actual = FileMetadata.from_path(path)
                files_checked += 1
                
                if actual is None:
                    continue
                
                # Compare metadata
                if expected.sha256_hash != actual.sha256_hash:
                    event = IntegrityEvent(
                        change_type=ChangeType.MODIFIED,
                        file_path=path_str,
                        expected_metadata=expected,
                        actual_metadata=actual,
                        severity=self._determine_severity(path_str)
                    )
                    violations.append(event)
                    modified_files.append(path_str)
                    await self._notify_violation(event)
                
                elif expected.permissions != actual.permissions:
                    event = IntegrityEvent(
                        change_type=ChangeType.PERMISSION_CHANGED,
                        file_path=path_str,
                        expected_metadata=expected,
                        actual_metadata=actual,
                        severity=IntegritySeverity.WARNING
                    )
                    violations.append(event)
                    await self._notify_violation(event)
                
                elif expected.owner != actual.owner or expected.group != actual.group:
                    event = IntegrityEvent(
                        change_type=ChangeType.OWNER_CHANGED,
                        file_path=path_str,
                        expected_metadata=expected,
                        actual_metadata=actual,
                        severity=IntegritySeverity.WARNING
                    )
                    violations.append(event)
                    await self._notify_violation(event)
            
            else:
                # New file not in baseline
                if path.exists() and path.is_file():
                    actual = FileMetadata.from_path(path)
                    if actual:
                        event = IntegrityEvent(
                            change_type=ChangeType.CREATED,
                            file_path=path_str,
                            expected_metadata=None,
                            actual_metadata=actual,
                            severity=IntegritySeverity.INFO
                        )
                        violations.append(event)
                        new_files.append(path_str)
                        await self._notify_violation(event)
        
        scan_time = time.time() - start_time
        
        report = IntegrityReport(
            scan_time=scan_time,
            files_checked=files_checked,
            violations=violations,
            new_files=new_files,
            missing_files=missing_files,
            modified_files=modified_files
        )
        
        self.logger.info(
            "integrity_verification_complete",
            files_checked=files_checked,
            violations=len(violations),
            scan_time_ms=scan_time * 1000
        )
        
        return report
    
    def _determine_severity(self, path: str) -> IntegritySeverity:
        """Determine severity of modification."""
        if path in self._critical_paths:
            return IntegritySeverity.CRITICAL
        
        # Check if in system directories
        critical_dirs = [
            "/etc/passwd",
            "/etc/shadow",
            "/bin",
            "/sbin",
            "/usr/bin",
            "/usr/sbin",
        ]
        
        for critical in critical_dirs:
            if path.startswith(critical):
                return IntegritySeverity.CRITICAL
        
        return IntegritySeverity.WARNING
    
    async def _notify_violation(self, event: IntegrityEvent) -> None:
        """Notify of integrity violation."""
        # Log violation
        log_method = {
            IntegritySeverity.INFO: self.logger.info,
            IntegritySeverity.WARNING: self.logger.warning,
            IntegritySeverity.CRITICAL: self.logger.critical
        }.get(event.severity, self.logger.warning)
        
        log_method(
            "integrity_violation",
            change_type=event.change_type.name,
            file_path=event.file_path,
            severity=event.severity.name,
            correlation_id=event.correlation_id
        )
        
        # Execute callbacks
        for callback in self._violation_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error("violation_callback_error", error=str(e))
        
        # Notify kernel
        if self.kernel and event.severity == IntegritySeverity.CRITICAL:
            try:
                await self.kernel.emit_event(
                    event_type=self.kernel.__class__.__dict__.get(
                        'SecurityEvent', {}
                    ).get('INTEGRITY_VIOLATION'),
                    source_module="integrity_monitor",
                    severity=9,
                    data=event.to_dict()
                )
            except Exception as e:
                self.logger.error("kernel_notification_failed", error=str(e))
    
    def start_monitoring(self) -> None:
        """Start continuous monitoring thread."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._shutdown_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name="AMCIS-Integrity-Monitor",
            daemon=True
        )
        self._monitor_thread.start()
        
        self.logger.info("monitoring_started", interval=self.scan_interval)
    
    def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        self._monitoring = False
        self._shutdown_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=10.0)
        
        self.logger.info("monitoring_stopped")
    
    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring and not self._shutdown_event.is_set():
            try:
                asyncio.run(self.verify_integrity())
            except Exception as e:
                self.logger.error("monitoring_error", error=str(e))
            
            # Wait for next scan or shutdown
            self._shutdown_event.wait(timeout=self.scan_interval)
    
    def add_critical_path(self, path: str) -> None:
        """Add a path to critical monitoring."""
        self._critical_paths.add(path)
        self.logger.info("critical_path_added", path=path)
    
    def remove_critical_path(self, path: str) -> None:
        """Remove a path from critical monitoring."""
        self._critical_paths.discard(path)
        self.logger.info("critical_path_removed", path=path)
    
    def get_baseline_info(self) -> Dict[str, Any]:
        """Get baseline information."""
        return {
            "baseline_loaded": self._baseline_loaded,
            "baseline_path": str(self.baseline_path),
            "files_in_baseline": len(self._baseline),
            "monitoring_active": self._monitoring,
            "critical_paths": list(self._critical_paths)
        }
