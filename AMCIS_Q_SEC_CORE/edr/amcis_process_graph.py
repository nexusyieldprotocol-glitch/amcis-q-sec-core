"""
AMCIS Process Graph
===================

Real-time process lineage tracking with parent-child relationship
analysis and anomaly detection for process trees.

Features:
- Process lineage graph construction
- Parent-child anomaly detection
- Process tree visualization
- Suspicious process chain detection

NIST Alignment: SP 800-53 (AU-6 Audit Record Analysis)
"""

import hashlib
import json
import os
import platform
import subprocess
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Iterator, Callable

import structlog

try:
    from core.amcis_exceptions import EDRException, ErrorCode
    from core.amcis_error_utils import safe_method, timing_context, ignore_errors
except ImportError:
    from ..core.amcis_exceptions import EDRException, ErrorCode
    from ..core.amcis_error_utils import safe_method, timing_context, ignore_errors


class ProcessState(Enum):
    """Process states."""
    RUNNING = auto()
    SLEEPING = auto()
    STOPPED = auto()
    ZOMBIE = auto()
    UNKNOWN = auto()


class ProcessAnomalyType(Enum):
    """Types of process anomalies."""
    ORPHAN_PROCESS = auto()
    UNEXPECTED_PARENT = auto()
    DEEP_NESTING = auto()
    RAPID_SPAWN = auto()
    HIDDEN_PROCESS = auto()
    PRIVILEGE_ESCALATION = auto()
    SUSPICIOUS_CMDLINE = auto()


@dataclass
class ProcessNode:
    """Process node in graph."""
    pid: int
    ppid: int
    name: str
    cmdline: str
    uid: int
    gid: int
    state: ProcessState
    start_time: float
    memory_mb: float
    cpu_percent: float
    exe_path: Optional[str] = None
    cwd: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    children: Set[int] = field(default_factory=set)
    hash_id: str = field(default_factory=lambda: hashlib.sha256(
        str(time.time_ns()).encode()
    ).hexdigest()[:16])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pid": self.pid,
            "ppid": self.ppid,
            "name": self.name,
            "cmdline": self.cmdline[:200] if self.cmdline else "",
            "uid": self.uid,
            "gid": self.gid,
            "state": self.state.name,
            "start_time": self.start_time,
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
            "exe_path": self.exe_path,
            "cwd": self.cwd,
            "children": list(self.children),
            "hash_id": self.hash_id
        }


@dataclass
class ProcessAnomaly:
    """Process anomaly report."""
    anomaly_type: ProcessAnomalyType
    process: ProcessNode
    confidence: float
    details: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "anomaly_type": self.anomaly_type.name,
            "process": self.process.to_dict(),
            "confidence": self.confidence,
            "details": self.details,
            "timestamp": self.timestamp
        }


class ProcessGraph:
    """
    AMCIS Process Graph
    ===================
    
    Real-time process lineage tracking with graph-based analysis
    for anomaly detection in process trees.
    """
    
    # Anomaly detection thresholds
    MAX_TREE_DEPTH = 10
    RAPID_SPAWN_THRESHOLD = 10  # processes per second
    RAPID_SPAWN_WINDOW = 5.0  # seconds
    
    # Suspicious command patterns
    SUSPICIOUS_PATTERNS = [
        "nc -e", "ncat -e", "netcat -e",
        "/dev/tcp/", "/dev/udp/",
        "python -c", "python3 -c",
        "perl -e", "ruby -e",
        "base64 -d", "base64 --decode",
        "eval(", "exec(",
        ".decode('base64')",
        "powershell -enc", "powershell -encodedcommand",
    ]
    
    def __init__(
        self,
        kernel=None,
        scan_interval: float = 5.0,
        history_size: int = 10000
    ) -> None:
        """
        Initialize process graph.
        
        Args:
            kernel: AMCIS kernel reference
            scan_interval: Process scan interval in seconds
            history_size: Maximum history entries
        """
        self.kernel = kernel
        self.scan_interval = scan_interval
        self.logger = structlog.get_logger("amcis.process_graph")
        
        # Process storage
        self._processes: Dict[int, ProcessNode] = {}
        self._process_history: List[ProcessNode] = []
        self._history_size = history_size
        
        # Spawn tracking for rapid spawn detection
        self._spawn_times: Dict[int, List[float]] = defaultdict(list)
        
        # Monitoring
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Anomaly detection
        self._expected_parents: Dict[str, Set[int]] = {
            "sshd": {1},  # sshd should be child of init/systemd
            "nginx": {1},
            "apache2": {1},
        }
        self._anomaly_callbacks: List[Callable[[ProcessAnomaly], None]] = []
        
        self.logger.info("process_graph_initialized")
    
    def register_anomaly_callback(self, callback: Callable[[ProcessAnomaly], None]) -> None:
        """Register callback for process anomalies."""
        self._anomaly_callbacks.append(callback)
    
    @safe_method(default={}, error_code=ErrorCode.EDR_ERROR, log=True)
    def scan_processes(self) -> Dict[int, ProcessNode]:
        """
        Scan system processes and build graph.
        
        Returns:
            Dictionary of process nodes
        """
        processes = {}
        
        with timing_context("process_scan", threshold_ms=5000.0):
            if platform.system() == "Windows":
                processes = self._scan_windows()
            else:
                processes = self._scan_unix()
        
        return processes
    
    def _scan_windows(self) -> Dict[int, ProcessNode]:
        """Scan processes on Windows."""
        processes = {}
        
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'ppid', 'name', 'cmdline', 
                                              'username', 'status', 'create_time',
                                              'memory_info', 'cpu_percent', 'exe', 'cwd']):
                try:
                    pinfo = proc.info
                    pid = pinfo['pid']
                    
                    cmdline = " ".join(pinfo['cmdline']) if pinfo['cmdline'] else ""
                    
                    node = ProcessNode(
                        pid=pid,
                        ppid=pinfo['ppid'] or 0,
                        name=pinfo['name'] or "unknown",
                        cmdline=cmdline,
                        uid=0,  # Windows uses different model
                        gid=0,
                        state=self._map_windows_state(pinfo['status']),
                        start_time=pinfo['create_time'] or time.time(),
                        memory_mb=(pinfo['memory_info'].rss / 1024 / 1024) if pinfo['memory_info'] else 0,
                        cpu_percent=pinfo['cpu_percent'] or 0.0,
                        exe_path=pinfo['exe'],
                        cwd=pinfo['cwd']
                    )
                    
                    processes[pid] = node
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
            # Fallback to wmic
            with ignore_errors(subprocess.SubprocessError, OSError):
                result = subprocess.run(
                    ["wmic", "process", "get", 
                     "ProcessId,ParentProcessId,Name,CommandLine,PageFileUsage", 
                     "/format:csv"],
                    capture_output=True,
                    text=True
                )
                # Parse CSV output
                for line in result.stdout.strip().split('\n')[1:]:
                    parts = line.strip().split(',')
                    if len(parts) >= 4:
                        with ignore_errors(ValueError):
                            pid = int(parts[2])
                            ppid = int(parts[3]) if parts[3] else 0
                            node = ProcessNode(
                                pid=pid,
                                ppid=ppid,
                                name=parts[1],
                                cmdline=parts[4] if len(parts) > 4 else "",
                                uid=0, gid=0,
                                state=ProcessState.RUNNING,
                                start_time=time.time(),
                                memory_mb=0, cpu_percent=0.0
                            )
                            processes[pid] = node
        
        return processes
    
    def _scan_unix(self) -> Dict[int, ProcessNode]:
        """Scan processes on Unix-like systems."""
        processes = {}
        proc_dir = Path("/proc")
        
        for pid_dir in proc_dir.glob("[0-9]*"):
            with ignore_errors(OSError, IOError, ValueError):
                pid = int(pid_dir.name)
                
                # Read process status
                status_file = pid_dir / "status"
                status_data = {}
                if status_file.exists():
                    with open(status_file, 'r') as f:
                        for line in f:
                            if ':' in line:
                                key, value = line.split(':', 1)
                                status_data[key.strip()] = value.strip()
                
                # Read command line
                cmdline_file = pid_dir / "cmdline"
                cmdline = ""
                if cmdline_file.exists():
                    cmdline = cmdline_file.read_text().replace('\x00', ' ').strip()
                
                # Read stat for timing
                stat_file = pid_dir / "stat"
                start_time = time.time()
                if stat_file.exists():
                    with ignore_errors(OSError, IOError):
                        stat_content = stat_file.read_text()
                        # Parse starttime from stat (field 22)
                        stat_parts = stat_content.split()
                        if len(stat_parts) > 21:
                            # This is simplified - real parsing is complex
                            pass
                
                # Read exe symlink
                exe_path = None
                with ignore_errors(OSError, IOError):
                    exe_path = os.readlink(pid_dir / "exe")
                
                # Read cwd
                cwd = None
                with ignore_errors(OSError, IOError):
                    cwd = os.readlink(pid_dir / "cwd")
                
                # Parse status data
                ppid = int(status_data.get('PPid', '0'))
                uid = int(status_data.get('Uid', '0').split()[0])
                gid = int(status_data.get('Gid', '0').split()[0])
                name = status_data.get('Name', 'unknown')
                
                # Get state
                state_char = status_data.get('State', 'R')[0]
                state = self._map_unix_state(state_char)
                
                # Get memory
                vm_rss = status_data.get('VmRSS', '0 kB')
                memory_mb = 0.0
                with ignore_errors(ValueError, IndexError):
                    memory_mb = int(vm_rss.split()[0]) / 1024
                
                node = ProcessNode(
                    pid=pid,
                    ppid=ppid,
                    name=name,
                    cmdline=cmdline,
                    uid=uid,
                    gid=gid,
                    state=state,
                    start_time=start_time,
                    memory_mb=memory_mb,
                    cpu_percent=0.0,  # Would need additional calculation
                    exe_path=exe_path,
                    cwd=cwd
                )
                
                processes[pid] = node
        
        return processes
    
    def _map_windows_state(self, status: str) -> ProcessState:
        """Map Windows process status to ProcessState."""
        status_map = {
            'running': ProcessState.RUNNING,
            'sleeping': ProcessState.SLEEPING,
            'stopped': ProcessState.STOPPED,
        }
        return status_map.get(status, ProcessState.UNKNOWN)
    
    def _map_unix_state(self, state_char: str) -> ProcessState:
        """Map Unix process state character to ProcessState."""
        state_map = {
            'R': ProcessState.RUNNING,
            'S': ProcessState.SLEEPING,
            'D': ProcessState.SLEEPING,
            'T': ProcessState.STOPPED,
            't': ProcessState.STOPPED,
            'Z': ProcessState.ZOMBIE,
            'X': ProcessState.UNKNOWN,
        }
        return state_map.get(state_char, ProcessState.UNKNOWN)
    
    @safe_method(default={}, error_code=ErrorCode.EDR_ERROR, log=True)
    def update_graph(self) -> Dict[int, ProcessNode]:
        """
        Update process graph with current system state.
        
        Returns:
            Updated process dictionary
        """
        with timing_context("update_graph", threshold_ms=5000.0):
            new_processes = self.scan_processes()
        
        # Build parent-child relationships
        for pid, node in new_processes.items():
            if node.ppid in new_processes:
                new_processes[node.ppid].children.add(pid)
        
        # Detect new processes
        for pid, node in new_processes.items():
            if pid not in self._processes:
                self._record_spawn(node)
                self._check_anomalies(node, new_processes)
        
        # Detect terminated processes
        for pid in list(self._processes.keys()):
            if pid not in new_processes:
                self.logger.debug("process_terminated", pid=pid)
        
            # Update storage
            self._processes = new_processes
            
            # Add to history
            for node in new_processes.values():
                self._process_history.append(node)
            
            while len(self._process_history) > self._history_size:
                self._process_history.pop(0)
        
            return new_processes
    
    def _record_spawn(self, node: ProcessNode) -> None:
        """Record process spawn for rapid spawn detection."""
        now = time.time()
        ppid = node.ppid
        
        self._spawn_times[ppid].append(now)
        
        # Clean old entries
        self._spawn_times[ppid] = [
            t for t in self._spawn_times[ppid]
            if now - t < self.RAPID_SPAWN_WINDOW
        ]
        
        # Check threshold
        if len(self._spawn_times[ppid]) > self.RAPID_SPAWN_THRESHOLD:
            parent = self._processes.get(ppid)
            if parent:
                anomaly = ProcessAnomaly(
                    anomaly_type=ProcessAnomalyType.RAPID_SPAWN,
                    process=parent,
                    confidence=0.8,
                    details={
                        "spawn_count": len(self._spawn_times[ppid]),
                        "window_seconds": self.RAPID_SPAWN_WINDOW
                    }
                )
                self._notify_anomaly(anomaly)
    
    def _check_anomalies(
        self,
        node: ProcessNode,
        all_processes: Dict[int, ProcessNode]
    ) -> None:
        """Check for process anomalies."""
        # Orphan process check
        if node.ppid != 0 and node.ppid not in all_processes:
            if node.ppid != 1:  # init/systemd adopting orphans is normal
                anomaly = ProcessAnomaly(
                    anomaly_type=ProcessAnomalyType.ORPHAN_PROCESS,
                    process=node,
                    confidence=0.6,
                    details={"original_ppid": node.ppid}
                )
                self._notify_anomaly(anomaly)
        
        # Unexpected parent check
        if node.name in self._expected_parents:
            expected = self._expected_parents[node.name]
            if node.ppid not in expected:
                anomaly = ProcessAnomaly(
                    anomaly_type=ProcessAnomalyType.UNEXPECTED_PARENT,
                    process=node,
                    confidence=0.7,
                    details={
                        "expected_parents": list(expected),
                        "actual_parent": node.ppid
                    }
                )
                self._notify_anomaly(anomaly)
        
        # Deep nesting check
        depth = self._calculate_depth(node, all_processes)
        if depth > self.MAX_TREE_DEPTH:
            anomaly = ProcessAnomaly(
                anomaly_type=ProcessAnomalyType.DEEP_NESTING,
                process=node,
                confidence=0.5 + (depth - self.MAX_TREE_DEPTH) * 0.05,
                details={"depth": depth}
            )
            self._notify_anomaly(anomaly)
        
        # Suspicious command line check
        if self._is_suspicious_cmdline(node.cmdline):
            anomaly = ProcessAnomaly(
                anomaly_type=ProcessAnomalyType.SUSPICIOUS_CMDLINE,
                process=node,
                confidence=0.75,
                details={"matched_patterns": self._get_matching_patterns(node.cmdline)}
            )
            self._notify_anomaly(anomaly)
        
        # Privilege escalation check
        parent = all_processes.get(node.ppid)
        if parent and node.uid != parent.uid:
            if node.uid == 0:  # Became root
                anomaly = ProcessAnomaly(
                    anomaly_type=ProcessAnomalyType.PRIVILEGE_ESCALATION,
                    process=node,
                    confidence=0.85,
                    details={
                        "parent_uid": parent.uid,
                        "process_uid": node.uid
                    }
                )
                self._notify_anomaly(anomaly)
    
    def _calculate_depth(
        self,
        node: ProcessNode,
        all_processes: Dict[int, ProcessNode]
    ) -> int:
        """Calculate depth in process tree."""
        depth = 0
        current = node
        visited = {node.pid}
        
        while current.ppid != 0 and depth < 100:
            parent = all_processes.get(current.ppid)
            if not parent or parent.pid in visited:
                break
            depth += 1
            visited.add(parent.pid)
            current = parent
        
        return depth
    
    def _is_suspicious_cmdline(self, cmdline: str) -> bool:
        """Check if command line contains suspicious patterns."""
        cmdline_lower = cmdline.lower()
        return any(pattern.lower() in cmdline_lower for pattern in self.SUSPICIOUS_PATTERNS)
    
    def _get_matching_patterns(self, cmdline: str) -> List[str]:
        """Get list of matching suspicious patterns."""
        cmdline_lower = cmdline.lower()
        return [
            pattern for pattern in self.SUSPICIOUS_PATTERNS
            if pattern.lower() in cmdline_lower
        ]
    
    def _notify_anomaly(self, anomaly: ProcessAnomaly) -> None:
        """Notify anomaly callbacks."""
        self.logger.warning(
            "process_anomaly_detected",
            anomaly_type=anomaly.anomaly_type.name,
            pid=anomaly.process.pid,
            name=anomaly.process.name,
            confidence=anomaly.confidence
        )
        
        for callback in self._anomaly_callbacks:
            with ignore_errors(Exception):
                callback(anomaly)
    
    def start_monitoring(self) -> None:
        """Start background monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._shutdown_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="AMCIS-ProcessGraph",
            daemon=True
        )
        self._monitor_thread.start()
        
        self.logger.info("process_monitoring_started")
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._monitoring = False
        self._shutdown_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        
        self.logger.info("process_monitoring_stopped")
    
    def _monitor_loop(self) -> None:
        """Monitoring loop."""
        while self._monitoring and not self._shutdown_event.is_set():
            with ignore_errors(EDRException):
                self.update_graph()
            
            self._shutdown_event.wait(timeout=self.scan_interval)
    
    def get_process_tree(self, root_pid: Optional[int] = None) -> Dict[str, Any]:
        """
        Get process tree starting from root.
        
        Args:
            root_pid: Root process ID (None for all)
            
        Returns:
            Process tree structure
        """
        if root_pid is None:
            # Find root processes (ppid = 0 or 1)
            roots = [
                p for p in self._processes.values()
                if p.ppid == 0 or p.ppid == 1
            ]
            return {
                "roots": [self._build_subtree(r.pid) for r in roots]
            }
        else:
            return self._build_subtree(root_pid)
    
    def _build_subtree(self, pid: int) -> Dict[str, Any]:
        """Build subtree for process."""
        node = self._processes.get(pid)
        if not node:
            return {"error": f"Process {pid} not found"}
        
        return {
            "process": node.to_dict(),
            "children": [
                self._build_subtree(child_pid)
                for child_pid in node.children
                if child_pid in self._processes
            ]
        }
    
    def get_process_lineage(self, pid: int) -> List[ProcessNode]:
        """
        Get process lineage (ancestors).
        
        Args:
            pid: Process ID
            
        Returns:
            List of ancestor processes
        """
        lineage = []
        visited = set()
        current_pid = pid
        
        while current_pid != 0 and len(lineage) < 100:
            node = self._processes.get(current_pid)
            if not node or node.pid in visited:
                break
            
            lineage.append(node)
            visited.add(node.pid)
            current_pid = node.ppid
        
        return lineage
    
    def find_processes_by_name(self, name: str) -> List[ProcessNode]:
        """Find processes by name."""
        return [
            p for p in self._processes.values()
            if p.name == name or p.name.startswith(name)
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get process statistics."""
        return {
            "total_processes": len(self._processes),
            "by_state": {
                state.name: sum(1 for p in self._processes.values() if p.state == state)
                for state in ProcessState
            },
            "history_size": len(self._process_history),
            "monitoring": self._monitoring
        }
