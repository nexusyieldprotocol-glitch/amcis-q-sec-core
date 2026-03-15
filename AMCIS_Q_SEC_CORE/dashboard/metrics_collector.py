"""
Metrics Collector
=================

Collects and aggregates security metrics for dashboard visualization.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


class MetricType(Enum):
    COUNTER = auto()
    GAUGE = auto()
    HISTOGRAM = auto()


@dataclass
class SecurityMetric:
    """Security metric data point."""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.name,
            "labels": self.labels,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat()
        }


class MetricsCollector:
    """
    AMCIS Metrics Collector
    =======================
    
    Collects security metrics from all AMCIS modules.
    """
    
    def __init__(self, retention_hours: int = 24) -> None:
        self.logger = structlog.get_logger("amcis.metrics")
        self.retention_hours = retention_hours
        
        self._metrics: List[SecurityMetric] = []
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        
        self.logger.info("metrics_collector_initialized")
    
    def record_counter(self, name: str, value: float = 1,
                      labels: Optional[Dict[str, str]] = None) -> None:
        """Record counter metric."""
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        self._counters[key] += value
        
        metric = SecurityMetric(
            name=name,
            value=self._counters[key],
            metric_type=MetricType.COUNTER,
            labels=labels or {}
        )
        self._metrics.append(metric)
        self._cleanup_old_metrics()
    
    def record_gauge(self, name: str, value: float,
                    labels: Optional[Dict[str, str]] = None) -> None:
        """Record gauge metric."""
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        self._gauges[key] = value
        
        metric = SecurityMetric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels or {}
        )
        self._metrics.append(metric)
        self._cleanup_old_metrics()
    
    def get_metric(self, name: str, metric_type: Optional[MetricType] = None) -> List[SecurityMetric]:
        """Get metrics by name."""
        filtered = [m for m in self._metrics if m.name == name]
        if metric_type:
            filtered = [m for m in filtered if m.metric_type == metric_type]
        return filtered
    
    def get_latest(self, name: str) -> Optional[SecurityMetric]:
        """Get latest metric by name."""
        metrics = self.get_metric(name)
        return max(metrics, key=lambda m: m.timestamp) if metrics else None
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary for dashboard."""
        now = time.time()
        one_hour_ago = now - 3600
        
        recent_metrics = [m for m in self._metrics if m.timestamp > one_hour_ago]
        
        # Security score calculation
        threat_metrics = [m for m in recent_metrics if "threat" in m.name]
        blocked_metrics = [m for m in recent_metrics if "blocked" in m.name]
        
        threat_count = len(threat_metrics)
        blocked_count = sum(m.value for m in blocked_metrics)
        
        # Calculate security score (0-100)
        if threat_count == 0:
            security_score = 100
        else:
            blocked_ratio = blocked_count / max(threat_count, 1)
            security_score = min(100, blocked_ratio * 100)
        
        return {
            "security_score": round(security_score, 1),
            "threats_detected_1h": threat_count,
            "attacks_blocked_1h": int(blocked_count),
            "total_metrics": len(self._metrics),
            "last_updated": datetime.fromtimestamp(now).isoformat()
        }
    
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff = time.time() - (self.retention_hours * 3600)
        self._metrics = [m for m in self._metrics if m.timestamp > cutoff]
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics."""
        if format == "json":
            return json.dumps({
                "exported_at": datetime.now().isoformat(),
                "metrics": [m.to_dict() for m in self._metrics[-1000:]]
            }, indent=2)
        elif format == "prometheus":
            lines = []
            for name, value in self._counters.items():
                lines.append(f"# TYPE {name.split(':')[0]} counter")
                lines.append(f"{name.split(':')[0]} {value}")
            return "\n".join(lines)
        return ""


# Import json for use in the class
import json
