"""
AMCIS File Integrity Monitor (EDR)
===================================

Real-time file integrity monitoring for the EDR module.
Focuses on runtime-critical files and directories.

Features:
- Hash-based file monitoring
- Real-time change detection
- Baseline management
- Event correlation

NIST Alignment: SP 800-53 (SI-7 Software, Firmware, and Information Integrity)
"""

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable, Tuple

import structlog

try:
    from core.amcis_exceptions import EDRException, ErrorCode
    from core.amcis_error_utils import safe_method, timing_context, ignore_errors
except ImportError:
    from ..core.amcis_exceptions import EDRException, ErrorCode
    from ..core.amcis_error_utils import safe_method, timing_context, ignore_errors


class FileChangeType(Enum):
    """Types of file changes."""
    CREATED = auto()
    MODIFIED = auto()
    DELETED = auto()
    PERMISSIONS_CHANGED = auto()
    ATTRIBUTES_CHANGED = auto()


class FileSeverity(Enum):
    """Severity of file change."""
    INFO = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class FileBaseline:
    """Baseline file information."""
    path: str
    sha256_hash: str
    size: int
    mtime: float
    permissions: int
    uid: int
    gid: int
    inode: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "sha256_hash": self.sha256_hash,
            "size": self.size,
            "mtime": self.mtime,
            "permissions": oct(self.permissions),
            "uid": self.uid,
            "gid": self.gid,
            "inode": self.inode
        }
    
    @classmethod
    def from_path(cls, file_path: Path) -> Optional["FileBaseline"]:
        """Create baseline from file."""
        try:
            stat = file_path.stat()
            
            # Calculate hash
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            
            return cls(
                path=str(file_path),
                sha256_hash=hasher.hexdigest(),
                size=stat.st_size,
                mtime=stat.st_mtime,
                permissions=stat.st_mode,
                uid=stat.st_uid,
                gid=stat.st_gid,
                inode=stat.st_ino
            )
        except (OSError, IOError):
            return None


@dataclass
class FileChangeEvent:
    """File change event."""
    change_type: FileChangeType
    file_path: str
    baseline: Optional[FileBaseline]
    current: Optional[FileBaseline]
    severity: FileSeverity
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "change_type": self.change_type.name,
            "file_path": self.file_path,
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "current": self.current.to_dict() if self.current else None,
            "severity": self.severity.name,
            "timestamp": self.timestamp
        }


class FileIntegrityMonitor:
    """
    AMCIS File Integrity Monitor (EDR)
    ==================================
    
    Runtime file integrity monitoring focused on security-critical
    files such as executables, libraries, and configuration files.
    """
    
    # Critical paths to monitor
    CRITICAL_PATHS = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/group",
        "/etc/sudoers",
        "/etc/ssh/sshd_config",
        "/bin",
        "/sbin",
        "/usr/bin",
        "/usr/sbin",
        "/lib",
        "/lib64",
        "/usr/lib",
        "/usr/lib64",
    ]
    
    # Excluded patterns
    EXCLUDE_PATTERNS = [
        "*.log",
        "*.tmp",
        "*.swp",
        "*~",
        "*.cache",
        "__pycache__",
        "*.pyc",
    ]
    
    def __init__(
        self,
        kernel=None,
        baseline_path: Optional[Path] = None,
        scan_interval: float = 60.0
    ) -> None:
        """
        Initialize file integrity monitor.
        
        Args:
            kernel: AMCIS kernel reference
            baseline_path: Path for baseline storage
            scan_interval: Scan interval in seconds
        """
        self.kernel = kernel
        self.baseline_path = baseline_path or Path("/var/lib/amcis/file_baseline.json")
        self.scan_interval = scan_interval
        
        self.logger = structlog.get_logger("amcis.file_integrity")
        
        # Baselines
        self._baselines: Dict[str, FileBaseline] = {}
        self._critical_files: Set[str] = set()
        
        # Monitoring
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Callbacks
        self._change_callbacks: List[Callable[[FileChangeEvent], None]] = []
        
        # Event history
        self._event_history: List[FileChangeEvent] = []
        self._max_history = 10000
        
        # Load existing baselines
        self._load_baselines()
        
        self.logger.info("file_integrity_monitor_initialized")
    
    def register_change_callback(self, callback: Callable[[FileChangeEvent], None]) -> None:
        """Register callback for file changes."""
        self._change_callbacks.append(callback)
    
    def _load_baselines(self) -> None:
        """Load existing baselines."""
        if not self.baseline_path.exists():
            return
        
        with ignore_errors(OSError, IOError, json.JSONDecodeError, KeyError, ValueError):
            with open(self.baseline_path, 'r') as f:
                data = json.load(f)
            
            for path, baseline_data in data.get("baselines", {}).items():
                self._baselines[path] = FileBaseline(
                    path=baseline_data["path"],
                    sha256_hash=baseline_data["sha256_hash"],
                    size=baseline_data["size"],
                    mtime=baseline_data["mtime"],
                    permissions=int(baseline_data["permissions"], 8),
                    uid=baseline_data["uid"],
                    gid=baseline_data["gid"],
                    inode=baseline_data["inode"]
                )
            
            self._critical_files = set(data.get("critical_files", []))
            
            self.logger.info("baselines_loaded", count=len(self._baselines))
    
    def _save_baselines(self) -> None:
        """Save baselines to disk."""
        with ignore_errors(OSError, IOError, PermissionError):
            self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "baselines": {
                    path: baseline.to_dict()
                    for path, baseline in self._baselines.items()
                },
                "critical_files": list(self._critical_files),
                "updated_at": time.time()
            }
            
            temp_path = self.baseline_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.baseline_path)
    
    def establish_baseline(
        self,
        paths: Optional[List[str]] = None,
        recursive: bool = True
    ) -> int:
        """
        Establish baseline for specified paths.
        
        Args:
            paths: Paths to baseline (None for defaults)
            recursive: Recurse into directories
            
        Returns:
            Number of files baselined
        """
        paths = paths or self.CRITICAL_PATHS
        count = 0
        
        for path_str in paths:
            path = Path(path_str)
            
            if not path.exists():
                self.logger.warning("path_not_found", path=path_str)
                continue
            
            if path.is_file():
                baseline = FileBaseline.from_path(path)
                if baseline:
                    self._baselines[str(path)] = baseline
                    count += 1
            
            elif path.is_dir() and recursive:
                for file_path in self._walk_directory(path):
                    baseline = FileBaseline.from_path(file_path)
                    if baseline:
                        self._baselines[str(file_path)] = baseline
                        count += 1
                        
                        if count % 100 == 0:
                            self.logger.info("baseline_progress", count=count)
        
        self._save_baselines()
        
        self.logger.info("baseline_established", file_count=count)
        return count
    
    def _walk_directory(self, directory: Path) -> List[Path]:
        """Walk directory and return files to monitor."""
        files = []
        
        try:
            for item in directory.rglob("*"):
                if item.is_file() and not self._should_exclude(item):
                    files.append(item)
        except PermissionError:
            self.logger.warning("permission_denied", path=str(directory))
        
        return files
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded."""
        path_str = str(path)
        name = path.name
        
        for pattern in self.EXCLUDE_PATTERNS:
            if self._match_pattern(name, pattern):
                return True
        
        # Skip symlinks
        if path.is_symlink():
            return True
        
        return False
    
    def _match_pattern(self, name: str, pattern: str) -> bool:
        """Match name against glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(name, pattern)
    
    @safe_method(default=[], error_code=ErrorCode.PERMISSION_DENIED, log=True)
    def scan(self) -> List[FileChangeEvent]:
        """
        Scan all baselined files for changes.
        
        Returns:
            List of change events
        """
        events = []
        
        with timing_context("file_integrity_scan", threshold_ms=60000.0):
            for path_str, baseline in list(self._baselines.items()):
                path = Path(path_str)
                
                if not path.exists():
                    # File deleted
                    event = FileChangeEvent(
                        change_type=FileChangeType.DELETED,
                        file_path=path_str,
                        baseline=baseline,
                        current=None,
                        severity=FileSeverity.HIGH
                    )
                    events.append(event)
                    self._notify_change(event)
                    continue
                
                # Get current state
                current = FileBaseline.from_path(path)
                if not current:
                    continue
                
                # Compare
                change_type, severity = self._compare_baselines(baseline, current)
                
                if change_type != FileChangeType.MODIFIED or severity != FileSeverity.INFO:
                    event = FileChangeEvent(
                        change_type=change_type,
                        file_path=path_str,
                        baseline=baseline,
                        current=current,
                        severity=severity
                    )
                    events.append(event)
                    self._notify_change(event)
                    
                    # Update baseline for non-critical changes
                    if severity != FileSeverity.CRITICAL:
                        self._baselines[path_str] = current
            
            if events:
                self._save_baselines()
        
        return events
    
    def _compare_baselines(
        self,
        baseline: FileBaseline,
        current: FileBaseline
    ) -> Tuple[FileChangeType, FileSeverity]:
        """
        Compare baseline to current state.
        
        Returns:
            (change_type, severity)
        """
        # Content change (hash differs)
        if baseline.sha256_hash != current.sha256_hash:
            severity = self._determine_content_severity(baseline, current)
            return FileChangeType.MODIFIED, severity
        
        # Permission change
        if baseline.permissions != current.permissions:
            return FileChangeType.PERMISSIONS_CHANGED, FileSeverity.MEDIUM
        
        # Ownership change
        if baseline.uid != current.uid or baseline.gid != current.gid:
            return FileChangeType.ATTRIBUTES_CHANGED, FileSeverity.HIGH
        
        # Mtime change only (not a real change for our purposes)
        return FileChangeType.MODIFIED, FileSeverity.INFO
    
    def _determine_content_severity(
        self,
        baseline: FileBaseline,
        current: FileBaseline
    ) -> FileSeverity:
        """Determine severity of content change."""
        path = baseline.path
        
        # Critical system files
        critical_paths = [
            "/etc/passwd", "/etc/shadow", "/etc/group",
            "/etc/sudoers", "/etc/ssh/sshd_config"
        ]
        
        if any(path.startswith(cp) for cp in critical_paths):
            return FileSeverity.CRITICAL
        
        # Executable files
        if path.startswith(("/bin/", "/sbin/", "/usr/bin/", "/usr/sbin/")):
            return FileSeverity.CRITICAL
        
        # Library files
        if "/lib" in path:
            return FileSeverity.HIGH
        
        # Critical files list
        if path in self._critical_files:
            return FileSeverity.CRITICAL
        
        return FileSeverity.MEDIUM
    
    def _notify_change(self, event: FileChangeEvent) -> None:
        """Notify change callbacks."""
        self.logger.log(
            {
                FileSeverity.INFO: self.logger.info,
                FileSeverity.LOW: self.logger.info,
                FileSeverity.MEDIUM: self.logger.warning,
                FileSeverity.HIGH: self.logger.error,
                FileSeverity.CRITICAL: self.logger.critical
            }.get(event.severity, self.logger.warning),
            "file_change_detected",
            change_type=event.change_type.name,
            file_path=event.file_path,
            severity=event.severity.name
        )
        
        # Store in history
        self._event_history.append(event)
        while len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Execute callbacks
        for callback in self._change_callbacks:
            with ignore_errors(Exception):
                callback(event)
        
        # Notify kernel for critical events
        if self.kernel and event.severity in (FileSeverity.HIGH, FileSeverity.CRITICAL):
            with ignore_errors(Exception):
                import asyncio
                asyncio.create_task(self.kernel.emit_event(
                    event_type=self.kernel.__class__.__dict__.get(
                        'SecurityEvent', {}
                    ).get('INTEGRITY_VIOLATION'),
                    source_module="file_integrity_monitor",
                    severity=9 if event.severity == FileSeverity.CRITICAL else 7,
                    data=event.to_dict()
                ))
    
    def start_monitoring(self) -> None:
        """Start background monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._shutdown_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="AMCIS-FileIntegrity",
            daemon=True
        )
        self._monitor_thread.start()
        
        self.logger.info("file_monitoring_started")
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._monitoring = False
        self._shutdown_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=10.0)
        
        self.logger.info("file_monitoring_stopped")
    
    def _monitor_loop(self) -> None:
        """Monitoring loop."""
        while self._monitoring and not self._shutdown_event.is_set():
            with ignore_errors(EDRException):
                self.scan()
            
            self._shutdown_event.wait(timeout=self.scan_interval)
    
    def add_critical_file(self, path: str) -> None:
        """Add a file to critical files list."""
        self._critical_files.add(path)
        self.logger.info("critical_file_added", path=path)
    
    def remove_critical_file(self, path: str) -> None:
        """Remove a file from critical files list."""
        self._critical_files.discard(path)
        self.logger.info("critical_file_removed", path=path)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        return {
            "baseline_count": len(self._baselines),
            "critical_files": len(self._critical_files),
            "monitoring": self._monitoring,
            "event_history_size": len(self._event_history)
        }
    
    def verify_file(self, path: str) -> Tuple[bool, Optional[str]]:
        """
        Verify a single file against baseline.
        
        Args:
            path: File path
            
        Returns:
            (valid, error_message)
        """
        path_str = str(path)
        baseline = self._baselines.get(path_str)
        
        if not baseline:
            return False, "No baseline for file"
        
        current = FileBaseline.from_path(Path(path))
        if not current:
            return False, "File not accessible"
        
        if baseline.sha256_hash != current.sha256_hash:
            return False, f"Hash mismatch: {baseline.sha256_hash[:16]}... != {current.sha256_hash[:16]}..."
        
        return True, None
