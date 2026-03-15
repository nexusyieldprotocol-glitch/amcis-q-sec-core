"""
Alert Manager
=============

Security alert generation, correlation, and notification.
"""

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable

import structlog


class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(Enum):
    NEW = auto()
    ACKNOWLEDGED = auto()
    INVESTIGATING = auto()
    RESOLVED = auto()
    FALSE_POSITIVE = auto()


@dataclass
class SecurityAlert:
    """Security alert."""
    alert_id: str
    title: str
    description: str
    severity: AlertSeverity
    source: str
    timestamp: float
    correlation_id: Optional[str] = None
    status: AlertStatus = AlertStatus.NEW
    assigned_to: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "source": self.source,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "status": self.status.name,
            "assigned_to": self.assigned_to,
            "tags": self.tags
        }


class AlertManager:
    """
    AMCIS Alert Manager
    ===================
    
    Manages security alerts with correlation and notification.
    """
    
    def __init__(self) -> None:
        self.logger = structlog.get_logger("amcis.alerts")
        self._alerts: List[SecurityAlert] = []
        self._notification_handlers: List[Callable[[SecurityAlert], None]] = []
        
        self.logger.info("alert_manager_initialized")
    
    def create_alert(self, title: str, description: str,
                    severity: AlertSeverity, source: str,
                    evidence: Optional[Dict[str, Any]] = None) -> SecurityAlert:
        """Create new security alert."""
        alert_id = hashlib.sha256(
            f"{title}:{source}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        alert = SecurityAlert(
            alert_id=alert_id,
            title=title,
            description=description,
            severity=severity,
            source=source,
            timestamp=time.time(),
            evidence=evidence or {}
        )
        
        self._alerts.append(alert)
        
        # Use appropriate log level based on severity
        log_method = {
            AlertSeverity.CRITICAL: self.logger.critical,
            AlertSeverity.HIGH: self.logger.error,
            AlertSeverity.MEDIUM: self.logger.warning,
            AlertSeverity.LOW: self.logger.info,
            AlertSeverity.INFO: self.logger.info
        }[severity]
        
        log_method(
            "security_alert_created",
            alert_id=alert_id,
            title=title,
            severity=severity.value
        )
        
        # Send notifications
        for handler in self._notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error("notification_failed", error=str(e))
        
        return alert
    
    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.assigned_to = user
                self.logger.info("alert_acknowledged", alert_id=alert_id, user=user)
                return True
        return False
    
    def resolve_alert(self, alert_id: str, resolution: str) -> bool:
        """Resolve alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.RESOLVED
                alert.evidence["resolution"] = resolution
                self.logger.info("alert_resolved", alert_id=alert_id)
                return True
        return False
    
    def get_alerts(self, severity: Optional[AlertSeverity] = None,
                  status: Optional[AlertStatus] = None,
                  source: Optional[str] = None) -> List[SecurityAlert]:
        """Get filtered alerts."""
        filtered = self._alerts
        
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        if status:
            filtered = [a for a in filtered if a.status == status]
        if source:
            filtered = [a for a in filtered if a.source == source]
        
        return sorted(filtered, key=lambda a: a.timestamp, reverse=True)
    
    def register_notification_handler(self, handler: Callable[[SecurityAlert], None]) -> None:
        """Register notification handler."""
        self._notification_handlers.append(handler)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        by_severity = {}
        by_status = {}
        
        for alert in self._alerts:
            sev = alert.severity.value
            status = alert.status.name
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_alerts": len(self._alerts),
            "open_alerts": sum(1 for a in self._alerts if a.status == AlertStatus.NEW),
            "by_severity": by_severity,
            "by_status": by_status
        }
