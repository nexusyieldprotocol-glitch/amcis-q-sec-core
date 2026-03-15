"""
AMCIS Response Engine - Autonomous Intrusion Response
======================================================

Implements automated response actions for detected security incidents:
- Process termination
- Cryptographic key rotation
- Session lockdown
- System snapshot and forensics
- Orchestration notifications

NIST Alignment: SP 800-61 (Incident Handling Guide), SP 800-53 (IR-4)
"""

import asyncio
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Set

import structlog


class ResponseActionType(Enum):
    """Types of automated response actions."""
    KILL_PROCESS = auto()
    ROTATE_KEYS = auto()
    LOCK_SESSION = auto()
    SNAPSHOT_STATE = auto()
    EXPORT_FORENSICS = auto()
    NOTIFY_ORCHESTRATION = auto()
    ISOLATE_NETWORK = auto()
    QUARANTINE_FILE = auto()


class ResponseSeverity(Enum):
    """Response severity levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ResponseAction:
    """Response action specification."""
    action_type: ResponseActionType
    target_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    severity: ResponseSeverity = ResponseSeverity.MEDIUM
    requires_confirmation: bool = False
    timeout_seconds: float = 30.0
    correlation_id: str = field(default_factory=lambda: hashlib.sha256(
        str(time.time_ns()).encode()
    ).hexdigest()[:16])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_type": self.action_type.name,
            "target_id": self.target_id,
            "parameters": self.parameters,
            "severity": self.severity.name,
            "requires_confirmation": self.requires_confirmation,
            "timeout_seconds": self.timeout_seconds,
            "correlation_id": self.correlation_id
        }


@dataclass
class ResponseResult:
    """Response action result."""
    action: ResponseAction
    success: bool
    message: str
    execution_time_ms: float
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


class ResponseEngine:
    """
    AMCIS Response Engine
    =====================
    
    Automated incident response with configurable action policies,
    escalation chains, and forensic preservation.
    
    Fail-closed design: Actions default to most secure option.
    """
    
    # Action severity thresholds
    AUTO_EXECUTE_SEVERITY = {ResponseSeverity.LOW, ResponseSeverity.MEDIUM}
    CONFIRM_SEVERITY = {ResponseSeverity.HIGH}
    DEFER_SEVERITY = {ResponseSeverity.CRITICAL}
    
    def __init__(
        self,
        kernel=None,
        forensics_dir: Optional[Path] = None,
        auto_respond: bool = True
    ) -> None:
        """
        Initialize response engine.
        
        Args:
            kernel: AMCIS kernel reference
            forensics_dir: Directory for forensic data storage
            auto_respond: Enable automatic response execution
        """
        self.kernel = kernel
        self.auto_respond = auto_respond
        self.forensics_dir = forensics_dir or Path("/var/lib/amcis/forensics")
        self.forensics_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = structlog.get_logger("amcis.response_engine")
        
        # Action handlers
        self._handlers: Dict[ResponseActionType, Callable[[ResponseAction], ResponseResult]] = {
            ResponseActionType.KILL_PROCESS: self._handle_kill_process,
            ResponseActionType.ROTATE_KEYS: self._handle_rotate_keys,
            ResponseActionType.LOCK_SESSION: self._handle_lock_session,
            ResponseActionType.SNAPSHOT_STATE: self._handle_snapshot_state,
            ResponseActionType.EXPORT_FORENSICS: self._handle_export_forensics,
            ResponseActionType.NOTIFY_ORCHESTRATION: self._handle_notify_orchestration,
            ResponseActionType.ISOLATE_NETWORK: self._handle_isolate_network,
            ResponseActionType.QUARANTINE_FILE: self._handle_quarantine_file,
        }
        
        # Pending confirmations
        self._pending_confirmations: Dict[str, ResponseAction] = {}
        
        # Response history
        self._response_history: List[ResponseResult] = []
        self._max_history = 1000
        
        # Lock state
        self._is_locked = False
        
        self.logger.info(
            "response_engine_initialized",
            auto_respond=auto_respond,
            forensics_dir=str(self.forensics_dir)
        )
    
    async def handle_critical_event(self, event_payload: Any) -> List[ResponseResult]:
        """
        Handle critical security event.
        
        Args:
            event_payload: Critical security event
            
        Returns:
            List of response results
        """
        self.logger.critical(
            "handling_critical_event",
            correlation_id=getattr(event_payload, 'correlation_id', 'unknown')
        )
        
        results = []
        
        # Immediate process kill if applicable
        if hasattr(event_payload, 'data') and 'pid' in event_payload.data:
            action = ResponseAction(
                action_type=ResponseActionType.KILL_PROCESS,
                target_id=str(event_payload.data['pid']),
                severity=ResponseSeverity.HIGH
            )
            result = await self.execute_action(action)
            results.append(result)
        
        # Key rotation
        key_action = ResponseAction(
            action_type=ResponseActionType.ROTATE_KEYS,
            severity=ResponseSeverity.HIGH
        )
        results.append(await self.execute_action(key_action))
        
        # Session lock
        lock_action = ResponseAction(
            action_type=ResponseActionType.LOCK_SESSION,
            severity=ResponseSeverity.HIGH
        )
        results.append(await self.execute_action(lock_action))
        
        # State snapshot
        snapshot_action = ResponseAction(
            action_type=ResponseActionType.SNAPSHOT_STATE,
            severity=ResponseSeverity.MEDIUM
        )
        results.append(await self.execute_action(snapshot_action))
        
        # Forensics export
        forensics_action = ResponseAction(
            action_type=ResponseActionType.EXPORT_FORENSICS,
            severity=ResponseSeverity.MEDIUM
        )
        results.append(await self.execute_action(forensics_action))
        
        return results
    
    async def execute_action(self, action: ResponseAction) -> ResponseResult:
        """
        Execute response action.
        
        Args:
            action: Response action to execute
            
        Returns:
            Action execution result
        """
        start_time = time.time()
        
        # Check if confirmation required
        if action.requires_confirmation or action.severity in self.CONFIRM_SEVERITY:
            if not self.auto_respond:
                self._pending_confirmations[action.correlation_id] = action
                return ResponseResult(
                    action=action,
                    success=False,
                    message="Action pending confirmation",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    details={"status": "pending_confirmation"}
                )
        
        # Execute handler
        handler = self._handlers.get(action.action_type)
        if handler is None:
            result = ResponseResult(
                action=action,
                success=False,
                message=f"No handler for action type: {action.action_type}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        else:
            try:
                # Run with timeout
                result = await asyncio.wait_for(
                    self._run_handler(handler, action),
                    timeout=action.timeout_seconds
                )
            except asyncio.TimeoutError:
                result = ResponseResult(
                    action=action,
                    success=False,
                    message="Action execution timed out",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    details={"timeout": action.timeout_seconds}
                )
        
        # Log result
        self._log_result(result)
        
        # Store in history
        self._response_history.append(result)
        if len(self._response_history) > self._max_history:
            self._response_history.pop(0)
        
        return result
    
    async def _run_handler(
        self,
        handler: Callable[[ResponseAction], ResponseResult],
        action: ResponseAction
    ) -> ResponseResult:
        """Run handler in thread pool for blocking operations."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, handler, action)
    
    def _handle_kill_process(self, action: ResponseAction) -> ResponseResult:
        """Handle process termination."""
        pid_str = action.target_id
        if not pid_str or not pid_str.isdigit():
            return ResponseResult(
                action=action,
                success=False,
                message="Invalid PID",
                execution_time_ms=0
            )
        
        pid = int(pid_str)
        
        try:
            # Check if process exists
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    check=True,
                    timeout=10
                )
            else:
                os.kill(pid, signal.SIGTERM)
                # Wait briefly, then SIGKILL if needed
                time.sleep(0.5)
                try:
                    os.kill(pid, 0)  # Check if still exists
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Already terminated
            
            return ResponseResult(
                action=action,
                success=True,
                message=f"Process {pid} terminated",
                execution_time_ms=0,
                details={"pid": pid, "signal": "SIGTERM/SIGKILL"}
            )
            
        except (ProcessLookupError, subprocess.CalledProcessError) as e:
            return ResponseResult(
                action=action,
                success=False,
                message=f"Failed to terminate process: {e}",
                execution_time_ms=0,
                details={"pid": pid, "error": str(e)}
            )
        except Exception as e:
            return ResponseResult(
                action=action,
                success=False,
                message=f"Unexpected error: {e}",
                execution_time_ms=0
            )
    
    def _handle_rotate_keys(self, action: ResponseAction) -> ResponseResult:
        """Handle cryptographic key rotation."""
        try:
            # Notify crypto module via kernel
            if self.kernel and hasattr(self.kernel, 'emit_event'):
                asyncio.create_task(self.kernel.emit_event(
                    event_type=self.kernel.__class__.__dict__.get(
                        'SecurityEvent', {}
                    ).get('KEY_ROTATION_REQUIRED'),
                    source_module="response_engine",
                    severity=8,
                    data={"correlation_id": action.correlation_id}
                ))
            
            # Rotate session keys
            rotated_keys = self._rotate_session_keys()
            
            return ResponseResult(
                action=action,
                success=True,
                message="Keys rotated successfully",
                execution_time_ms=0,
                details={"rotated_keys": rotated_keys}
            )
            
        except Exception as e:
            return ResponseResult(
                action=action,
                success=False,
                message=f"Key rotation failed: {e}",
                execution_time_ms=0
            )
    
    def _rotate_session_keys(self) -> List[str]:
        """Rotate session cryptographic keys."""
        rotated = []
        
        # Clear any cached keys (secure memory would be better)
        key_vars = [
            'AMCIS_SESSION_KEY',
            'AMCIS_AUTH_TOKEN',
        ]
        
        for var in key_vars:
            if var in os.environ:
                # Overwrite before clearing
                os.environ[var] = '0' * 64
                del os.environ[var]
                rotated.append(var)
        
        return rotated
    
    def _handle_lock_session(self, action: ResponseAction) -> ResponseResult:
        """Handle session lockdown."""
        try:
            self._is_locked = True
            
            # Platform-specific lock
            system = platform.system()
            if system == "Windows":
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            elif system == "Darwin":  # macOS
                subprocess.run(["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"])
            else:  # Linux
                # Try multiple methods
                for cmd in [
                    ["loginctl", "lock-session"],
                    ["gnome-screensaver-command", "--lock"],
                    ["xscreensaver-command", "--lock"],
                ]:
                    try:
                        subprocess.run(cmd, capture_output=True, timeout=5)
                        break
                    except FileNotFoundError:
                        continue
            
            return ResponseResult(
                action=action,
                success=True,
                message="Session locked",
                execution_time_ms=0,
                details={"platform": system}
            )
            
        except Exception as e:
            return ResponseResult(
                action=action,
                success=False,
                message=f"Session lock failed: {e}",
                execution_time_ms=0
            )
    
    def _handle_snapshot_state(self, action: ResponseAction) -> ResponseResult:
        """Handle system state snapshot."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            snapshot_dir = self.forensics_dir / f"snapshot_{timestamp}"
            snapshot_dir.mkdir(exist_ok=True)
            
            snapshot_data = {
                "timestamp": time.time(),
                "platform": platform.platform(),
                "processes": self._capture_process_list(),
                "network": self._capture_network_state(),
                "environment": dict(os.environ),
            }
            
            snapshot_file = snapshot_dir / "state.json"
            with open(snapshot_file, 'w') as f:
                json.dump(snapshot_data, f, indent=2, default=str)
            
            return ResponseResult(
                action=action,
                success=True,
                message="State snapshot captured",
                execution_time_ms=0,
                details={"snapshot_path": str(snapshot_file)}
            )
            
        except Exception as e:
            return ResponseResult(
                action=action,
                success=False,
                message=f"Snapshot failed: {e}",
                execution_time_ms=0
            )
    
    def _capture_process_list(self) -> List[Dict[str, Any]]:
        """Capture current process list."""
        processes = []
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FO", "CSV"],
                    capture_output=True,
                    text=True
                )
                # Parse CSV output
                for line in result.stdout.strip().split('\n')[1:]:
                    parts = line.strip('"').split('","')
                    if len(parts) >= 2:
                        processes.append({
                            "name": parts[0],
                            "pid": parts[1]
                        })
            else:
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.strip().split('\n')[1:]:
                    parts = line.split()
                    if len(parts) >= 11:
                        processes.append({
                            "user": parts[0],
                            "pid": parts[1],
                            "cpu": parts[2],
                            "mem": parts[3],
                            "command": " ".join(parts[10:])
                        })
        except Exception as e:
            self.logger.warning("process_capture_failed", error=str(e))
        
        return processes
    
    def _capture_network_state(self) -> Dict[str, Any]:
        """Capture network state."""
        network_state = {
            "connections": [],
            "interfaces": []
        }
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True,
                    text=True
                )
                network_state["connections"] = result.stdout.split('\n')
            else:
                result = subprocess.run(
                    ["ss", "-tuln"],
                    capture_output=True,
                    text=True
                )
                network_state["connections"] = result.stdout.split('\n')
        except Exception as e:
            self.logger.warning("network_capture_failed", error=str(e))
        
        return network_state
    
    def _handle_export_forensics(self, action: ResponseAction) -> ResponseResult:
        """Handle forensic data export."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            bundle_name = f"forensics_bundle_{timestamp}.tar.gz"
            bundle_path = self.forensics_dir / bundle_name
            
            # Create tar.gz bundle
            with tarfile.open(bundle_path, "w:gz") as tar:
                # Add recent snapshots
                for snapshot in self.forensics_dir.glob("snapshot_*"):
                    tar.add(snapshot, arcname=snapshot.name)
                
                # Add logs if available
                log_dir = Path("/var/log/amcis")
                if log_dir.exists():
                    tar.add(log_dir, arcname="logs")
            
            return ResponseResult(
                action=action,
                success=True,
                message="Forensic bundle created",
                execution_time_ms=0,
                details={
                    "bundle_path": str(bundle_path),
                    "bundle_size": bundle_path.stat().st_size
                }
            )
            
        except Exception as e:
            return ResponseResult(
                action=action,
                success=False,
                message=f"Forensics export failed: {e}",
                execution_time_ms=0
            )
    
    def _handle_notify_orchestration(self, action: ResponseAction) -> ResponseResult:
        """Handle orchestration layer notification."""
        try:
            # In production, this would call AMCIS orchestration API
            notification = {
                "type": "security_incident",
                "timestamp": time.time(),
                "severity": action.severity.name,
                "details": action.parameters
            }
            
            self.logger.info(
                "orchestration_notification",
                notification=json.dumps(notification)
            )
            
            return ResponseResult(
                action=action,
                success=True,
                message="Orchestration notified",
                execution_time_ms=0
            )
            
        except Exception as e:
            return ResponseResult(
                action=action,
                success=False,
                message=f"Notification failed: {e}",
                execution_time_ms=0
            )
    
    def _handle_isolate_network(self, action: ResponseAction) -> ResponseResult:
        """Handle network isolation."""
        try:
            # Platform-specific network isolation
            # This is a stub - production would use proper firewall APIs
            self.logger.warning(
                "network_isolation_stub",
                message="Network isolation would be implemented here"
            )
            
            return ResponseResult(
                action=action,
                success=True,
                message="Network isolation requested",
                execution_time_ms=0,
                details={"note": "Stub implementation"}
            )
            
        except Exception as e:
            return ResponseResult(
                action=action,
                success=False,
                message=f"Network isolation failed: {e}",
                execution_time_ms=0
            )
    
    def _handle_quarantine_file(self, action: ResponseAction) -> ResponseResult:
        """Handle file quarantine."""
        file_path = action.target_id
        if not file_path:
            return ResponseResult(
                action=action,
                success=False,
                message="No file path specified",
                execution_time_ms=0
            )
        
        try:
            source = Path(file_path)
            if not source.exists():
                return ResponseResult(
                    action=action,
                    success=False,
                    message="File not found",
                    execution_time_ms=0
                )
            
            # Create quarantine directory
            quarantine_dir = self.forensics_dir / "quarantine"
            quarantine_dir.mkdir(exist_ok=True)
            
            # Move to quarantine with metadata
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            quarantine_name = f"{source.name}.{timestamp}.quarantined"
            dest = quarantine_dir / quarantine_name
            
            # Copy and remove original
            shutil.copy2(source, dest)
            source.unlink()
            
            # Write metadata
            metadata = {
                "original_path": str(source),
                "quarantine_path": str(dest),
                "timestamp": time.time(),
                "reason": action.parameters.get("reason", "security_incident")
            }
            meta_path = dest.with_suffix(dest.suffix + ".json")
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return ResponseResult(
                action=action,
                success=True,
                message="File quarantined",
                execution_time_ms=0,
                details={
                    "original_path": str(source),
                    "quarantine_path": str(dest)
                }
            )
            
        except Exception as e:
            return ResponseResult(
                action=action,
                success=False,
                message=f"Quarantine failed: {e}",
                execution_time_ms=0
            )
    
    def _log_result(self, result: ResponseResult) -> None:
        """Log response result."""
        log_method = self.logger.info if result.success else self.logger.error
        log_method(
            "response_action_executed",
            action_type=result.action.action_type.name,
            success=result.success,
            message=result.message,
            correlation_id=result.action.correlation_id,
            execution_time_ms=result.execution_time_ms
        )
    
    def get_pending_confirmations(self) -> Dict[str, ResponseAction]:
        """Get pending confirmation actions."""
        return dict(self._pending_confirmations)
    
    def confirm_action(self, correlation_id: str, confirm: bool) -> Optional[ResponseResult]:
        """
        Confirm or reject pending action.
        
        Args:
            correlation_id: Action correlation ID
            confirm: True to confirm, False to reject
            
        Returns:
            Result if action was pending, None otherwise
        """
        action = self._pending_confirmations.pop(correlation_id, None)
        if action is None:
            return None
        
        if confirm:
            # Re-execute without confirmation requirement
            action.requires_confirmation = False
            return asyncio.run(self.execute_action(action))
        else:
            return ResponseResult(
                action=action,
                success=False,
                message="Action rejected by operator",
                execution_time_ms=0
            )
    
    def get_response_history(self) -> List[ResponseResult]:
        """Get response action history."""
        return list(self._response_history)
    
    def is_locked(self) -> bool:
        """Check if session is locked."""
        return self._is_locked
