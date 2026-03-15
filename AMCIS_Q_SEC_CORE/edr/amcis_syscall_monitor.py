"""
AMCIS Syscall Monitor
=====================

System call monitoring for detecting:
- Suspicious syscall patterns
- Privilege escalation attempts
- Unauthorized access attempts
- Injection techniques

Platform: Linux (using seccomp, ptrace, or audit)

NIST Alignment: SP 800-53 (AU-6 Audit Record Analysis)
"""

import errno
import hashlib
import json
import os
import platform
import signal
import struct
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import structlog


class SyscallType(Enum):
    """Types of system calls."""
    FILE = auto()
    PROCESS = auto()
    NETWORK = auto()
    MEMORY = auto()
    SIGNAL = auto()
    PRIVILEGE = auto()
    IPC = auto()
    UNKNOWN = auto()


class SyscallAction(Enum):
    """Actions for syscall rules."""
    ALLOW = auto()
    DENY = auto()
    LOG = auto()
    ALERT = auto()


@dataclass
class SyscallEvent:
    """System call event."""
    syscall_number: int
    syscall_name: str
    pid: int
    uid: int
    gid: int
    arguments: List[int]
    return_value: int
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "syscall_number": self.syscall_number,
            "syscall_name": self.syscall_name,
            "pid": self.pid,
            "uid": self.uid,
            "gid": self.gid,
            "arguments": self.arguments,
            "return_value": self.return_value,
            "timestamp": self.timestamp
        }


@dataclass
class SyscallRule:
    """Syscall monitoring rule."""
    syscall_name: Optional[str]
    syscall_type: Optional[SyscallType]
    filter_func: Optional[Callable[[SyscallEvent], bool]]
    action: SyscallAction
    message: str
    severity: int = 5  # 1-10


class SyscallMonitor:
    """
    AMCIS Syscall Monitor
    =====================
    
    System call monitoring using various backends (audit, ptrace, etc.)
    to detect suspicious process behavior.
    """
    
    # Common syscall numbers for x86_64 Linux
    SYSCALL_NAMES = {
        0: "read", 1: "write", 2: "open", 3: "close",
        9: "mmap", 10: "mprotect", 11: "munmap",
        39: "getpid", 56: "clone", 57: "fork", 58: "vfork",
        59: "execve", 60: "exit", 61: "wait4",
        62: "kill", 101: "ptrace",
        165: "mount", 166: "umount2",
        257: "openat", 273: "setns",
        321: "bpf", 332: "statx",
    }
    
    # Syscall type mapping
    SYSCALL_TYPES = {
        "open": SyscallType.FILE,
        "openat": SyscallType.FILE,
        "read": SyscallType.FILE,
        "write": SyscallType.FILE,
        "close": SyscallType.FILE,
        "mmap": SyscallType.MEMORY,
        "mprotect": SyscallType.MEMORY,
        "munmap": SyscallType.MEMORY,
        "fork": SyscallType.PROCESS,
        "vfork": SyscallType.PROCESS,
        "clone": SyscallType.PROCESS,
        "execve": SyscallType.PROCESS,
        "exit": SyscallType.PROCESS,
        "kill": SyscallType.SIGNAL,
        "ptrace": SyscallType.PRIVILEGE,
        "setuid": SyscallType.PRIVILEGE,
        "setgid": SyscallType.PRIVILEGE,
        "setns": SyscallType.PRIVILEGE,
        "bpf": SyscallType.PRIVILEGE,
    }
    
    # Suspicious syscall patterns
    SUSPICIOUS_PATTERNS = [
        ("ptrace", "Process debugging detected"),
        ("execve", "Program execution"),
        ("setuid", "Privilege escalation attempt"),
        ("setgid", "Group privilege change"),
        ("mount", "Filesystem mount"),
        ("bpf", "BPF program loading"),
    ]
    
    def __init__(self, kernel=None) -> None:
        """
        Initialize syscall monitor.
        
        Args:
            kernel: AMCIS kernel reference
        """
        self.kernel = kernel
        self.logger = structlog.get_logger("amcis.syscall_monitor")
        
        # Rules
        self._rules: List[SyscallRule] = []
        self._setup_default_rules()
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Event callbacks
        self._event_callbacks: List[Callable[[SyscallEvent], None]] = []
        self._alert_callbacks: List[Callable[[SyscallEvent, SyscallRule], None]] = []
        
        # Event history
        self._event_history: List[SyscallEvent] = []
        self._max_history = 10000
        
        # Statistics
        self._syscall_counts: Dict[str, int] = {}
        
        self.logger.info("syscall_monitor_initialized")
    
    def _setup_default_rules(self) -> None:
        """Setup default monitoring rules."""
        # ptrace monitoring
        self.add_rule(SyscallRule(
            syscall_name="ptrace",
            syscall_type=None,
            filter_func=None,
            action=SyscallAction.ALERT,
            message="ptrace syscall detected - possible debugging/injection",
            severity=8
        ))
        
        # setuid monitoring
        self.add_rule(SyscallRule(
            syscall_name="setuid",
            syscall_type=None,
            filter_func=None,
            action=SyscallAction.LOG,
            message="setuid syscall - privilege change",
            severity=6
        ))
        
        # execve monitoring for root
        self.add_rule(SyscallRule(
            syscall_name="execve",
            syscall_type=None,
            filter_func=lambda e: e.uid == 0,
            action=SyscallAction.LOG,
            message="Root process execution",
            severity=5
        ))
        
        # bpf monitoring
        self.add_rule(SyscallRule(
            syscall_name="bpf",
            syscall_type=None,
            filter_func=None,
            action=SyscallAction.ALERT,
            message="BPF syscall - kernel code loading",
            severity=7
        ))
    
    def add_rule(self, rule: SyscallRule) -> None:
        """Add monitoring rule."""
        self._rules.append(rule)
    
    def register_event_callback(self, callback: Callable[[SyscallEvent], None]) -> None:
        """Register callback for syscall events."""
        self._event_callbacks.append(callback)
    
    def register_alert_callback(self, callback: Callable[[SyscallEvent, SyscallRule], None]) -> None:
        """Register callback for syscall alerts."""
        self._alert_callbacks.append(callback)
    
    def start_monitoring(self, method: str = "audit") -> bool:
        """
        Start syscall monitoring.
        
        Args:
            method: Monitoring method (audit, ptrace, ebpf)
            
        Returns:
            True if monitoring started
        """
        if self._monitoring:
            return True
        
        if platform.system() != "Linux":
            self.logger.warning("syscall_monitor_linux_only")
            return False
        
        self._monitoring = True
        self._shutdown_event.clear()
        
        if method == "audit":
            return self._start_audit_monitoring()
        elif method == "ptrace":
            return self._start_ptrace_monitoring()
        else:
            self.logger.error("unknown_monitoring_method", method=method)
            self._monitoring = False
            return False
    
    def _start_audit_monitoring(self) -> bool:
        """Start monitoring using Linux audit subsystem."""
        try:
            # Check if auditd is available
            result = subprocess.run(
                ["which", "auditctl"],
                capture_output=True
            )
            if result.returncode != 0:
                self.logger.warning("auditctl_not_available")
                return False
            
            # Setup audit rules
            self._setup_audit_rules()
            
            # Start monitoring thread
            self._monitor_thread = threading.Thread(
                target=self._audit_monitor_loop,
                name="AMCIS-SyscallMonitor",
                daemon=True
            )
            self._monitor_thread.start()
            
            self.logger.info("audit_monitoring_started")
            return True
            
        except Exception as e:
            self.logger.error("audit_monitoring_failed", error=str(e))
            self._monitoring = False
            return False
    
    def _setup_audit_rules(self) -> None:
        """Setup audit rules for syscall monitoring."""
        # Monitor ptrace
        subprocess.run(
            ["auditctl", "-a", "always,exit", "-S", "ptrace"],
            capture_output=True
        )
        
        # Monitor execve
        subprocess.run(
            ["auditctl", "-a", "always,exit", "-S", "execve", "-F", "arch=b64"],
            capture_output=True
        )
    
    def _audit_monitor_loop(self) -> None:
        """Monitor loop for audit events."""
        try:
            # Use ausearch or tail audit log
            process = subprocess.Popen(
                ["tail", "-F", "/var/log/audit/audit.log"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            while self._monitoring and not self._shutdown_event.is_set():
                line = process.stdout.readline()
                if line:
                    self._parse_audit_line(line.strip())
                    
        except Exception as e:
            self.logger.error("audit_monitor_loop_error", error=str(e))
        finally:
            if 'process' in locals():
                process.terminate()
    
    def _parse_audit_line(self, line: str) -> None:
        """Parse audit log line."""
        # Simplified parsing - real implementation would parse audit format
        if "type=SYSCALL" in line:
            try:
                # Extract syscall number
                if "syscall=" in line:
                    syscall_str = line.split("syscall=")[1].split()[0]
                    syscall_num = int(syscall_str)
                    
                    syscall_name = self.SYSCALL_NAMES.get(syscall_num, f"syscall_{syscall_num}")
                    syscall_type = self.SYSCALL_TYPES.get(syscall_name, SyscallType.UNKNOWN)
                    
                    # Extract PID
                    pid = 0
                    if "pid=" in line:
                        pid_str = line.split("pid=")[1].split()[0]
                        pid = int(pid_str)
                    
                    # Extract UID
                    uid = 0
                    if "uid=" in line:
                        uid_str = line.split("uid=")[1].split()[0]
                        uid = int(uid_str)
                    
                    event = SyscallEvent(
                        syscall_number=syscall_num,
                        syscall_name=syscall_name,
                        pid=pid,
                        uid=uid,
                        gid=0,
                        arguments=[],
                        return_value=0
                    )
                    
                    self._process_event(event)
                    
            except Exception as e:
                self.logger.debug("audit_parse_error", error=str(e))
    
    def _start_ptrace_monitoring(self) -> bool:
        """Start monitoring using ptrace."""
        # ptrace-based monitoring is complex and requires attaching to processes
        # This is a stub for the actual implementation
        self.logger.info("ptrace_monitoring_stub")
        return False
    
    def _process_event(self, event: SyscallEvent) -> None:
        """Process syscall event."""
        # Update statistics
        self._syscall_counts[event.syscall_name] = \
            self._syscall_counts.get(event.syscall_name, 0) + 1
        
        # Add to history
        self._event_history.append(event)
        while len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Notify event callbacks
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error("event_callback_error", error=str(e))
        
        # Check rules
        for rule in self._rules:
            if self._matches_rule(event, rule):
                self._handle_rule_match(event, rule)
    
    def _matches_rule(self, event: SyscallEvent, rule: SyscallRule) -> bool:
        """Check if event matches rule."""
        if rule.syscall_name and event.syscall_name != rule.syscall_name:
            return False
        
        if rule.syscall_type:
            event_type = self.SYSCALL_TYPES.get(event.syscall_name, SyscallType.UNKNOWN)
            if event_type != rule.syscall_type:
                return False
        
        if rule.filter_func and not rule.filter_func(event):
            return False
        
        return True
    
    def _handle_rule_match(self, event: SyscallEvent, rule: SyscallRule) -> None:
        """Handle rule match."""
        if rule.action == SyscallAction.ALLOW:
            return
        
        if rule.action == SyscallAction.LOG:
            self.logger.info(
                "syscall_rule_match",
                syscall=event.syscall_name,
                pid=event.pid,
                message=rule.message
            )
        
        elif rule.action == SyscallAction.ALERT:
            self.logger.warning(
                "syscall_alert",
                syscall=event.syscall_name,
                pid=event.pid,
                severity=rule.severity,
                message=rule.message
            )
            
            # Notify alert callbacks
            for callback in self._alert_callbacks:
                try:
                    callback(event, rule)
                except Exception as e:
                    self.logger.error("alert_callback_error", error=str(e))
            
            # Notify kernel
            if self.kernel and rule.severity >= 7:
                try:
                    import asyncio
                    asyncio.create_task(self.kernel.emit_event(
                        event_type=self.kernel.__class__.__dict__.get(
                            'SecurityEvent', {}
                        ).get('SYSTEM_CALL_ALERT'),
                        source_module="syscall_monitor",
                        severity=rule.severity,
                        data={
                            "syscall": event.syscall_name,
                            "pid": event.pid,
                            "message": rule.message
                        }
                    ))
                except Exception as e:
                    self.logger.error("kernel_notification_failed", error=str(e))
    
    def stop_monitoring(self) -> None:
        """Stop syscall monitoring."""
        self._monitoring = False
        self._shutdown_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        
        # Remove audit rules
        try:
            subprocess.run(
                ["auditctl", "-d", "always,exit", "-S", "ptrace"],
                capture_output=True
            )
        except Exception:
            pass
        
        self.logger.info("syscall_monitoring_stopped")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "monitoring": self._monitoring,
            "event_history_size": len(self._event_history),
            "syscall_counts": dict(self._syscall_counts),
            "rules_count": len(self._rules)
        }
    
    def get_recent_events(self, count: int = 100) -> List[SyscallEvent]:
        """Get recent syscall events."""
        return self._event_history[-count:] if self._event_history else []
    
    def analyze_process(self, pid: int, duration: float = 10.0) -> Dict[str, Any]:
        """
        Analyze syscalls for specific process.
        
        Args:
            pid: Process ID
            duration: Analysis duration in seconds
            
        Returns:
            Analysis results
        """
        events = [
            e for e in self._event_history
            if e.pid == pid and time.time() - e.timestamp < duration
        ]
        
        syscall_counts = {}
        for event in events:
            syscall_counts[event.syscall_name] = \
                syscall_counts.get(event.syscall_name, 0) + 1
        
        # Check for suspicious patterns
        alerts = []
        for event in events:
            for pattern_name, message in self.SUSPICIOUS_PATTERNS:
                if event.syscall_name == pattern_name:
                    alerts.append({
                        "syscall": event.syscall_name,
                        "message": message,
                        "timestamp": event.timestamp
                    })
        
        return {
            "pid": pid,
            "event_count": len(events),
            "syscall_breakdown": syscall_counts,
            "alerts": alerts
        }
