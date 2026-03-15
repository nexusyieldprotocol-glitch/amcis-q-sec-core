"""
Forensic Timeline
=================

Reconstructs security events into a forensic timeline for incident analysis.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import structlog


class EventCategory(Enum):
    FILE = auto()
    NETWORK = auto()
    PROCESS = auto()
    AUTH = auto()
    REGISTRY = auto()
    MEMORY = auto()


class EventSeverity(Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    INFO = 0


@dataclass
class TimelineEvent:
    """Single forensic timeline event."""
    timestamp: float
    category: EventCategory
    event_type: str
    source: str  # source system/process
    target: str  # target file/IP/etc
    details: Dict[str, Any]
    severity: EventSeverity
    correlation_id: str = field(default_factory=lambda: hashlib.sha256(
        str(time.time()).encode()
    ).hexdigest()[:16])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "category": self.category.name,
            "type": self.event_type,
            "source": self.source,
            "target": self.target,
            "severity": self.severity.name,
            "correlation_id": self.correlation_id,
            "details": self.details
        }


class ForensicTimeline:
    """
    Forensic Timeline Reconstruction
    ================================
    
    Aggregates security events into a chronological timeline for incident analysis.
    """
    
    def __init__(self, case_id: str, storage_path: Optional[Path] = None) -> None:
        self.case_id = case_id
        self.storage_path = storage_path or Path(f"/var/lib/amcis/forensics/{case_id}")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger("amcis.forensics")
        
        self._events: List[TimelineEvent] = []
        self._correlations: Dict[str, Set[str]] = {}  # correlation_id -> related events
        
        self.logger.info("forensic_timeline_created", case_id=case_id)
    
    def add_event(self, event: TimelineEvent) -> None:
        """Add event to timeline."""
        self._events.append(event)
        
        # Maintain chronological order
        self._events.sort(key=lambda e: e.timestamp)
        
        # Track correlations
        if event.correlation_id:
            if event.correlation_id not in self._correlations:
                self._correlations[event.correlation_id] = set()
            self._correlations[event.correlation_id].add(event.timestamp)
    
    def add_events(self, events: List[TimelineEvent]) -> None:
        """Add multiple events."""
        for event in events:
            self.add_event(event)
    
    def get_timeline(self, start_time: Optional[float] = None,
                    end_time: Optional[float] = None,
                    category: Optional[EventCategory] = None,
                    severity: Optional[EventSeverity] = None) -> List[TimelineEvent]:
        """Get filtered timeline."""
        filtered = self._events
        
        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]
        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]
        if category:
            filtered = [e for e in filtered if e.category == category]
        if severity:
            filtered = [e for e in filtered if e.severity.value >= severity.value]
        
        return filtered
    
    def get_event_chain(self, correlation_id: str) -> List[TimelineEvent]:
        """Get all events related to a correlation ID."""
        return [e for e in self._events if e.correlation_id == correlation_id]
    
    def export_timeline(self, format: str = "json") -> str:
        """Export timeline to file."""
        if format == "json":
            output_file = self.storage_path / "timeline.json"
            data = {
                "case_id": self.case_id,
                "exported_at": datetime.now().isoformat(),
                "event_count": len(self._events),
                "events": [e.to_dict() for e in self._events]
            }
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            return str(output_file)
        
        elif format == "csv":
            import csv
            output_file = self.storage_path / "timeline.csv"
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Category", "Type", "Source", "Target", "Severity"])
                for e in self._events:
                    writer.writerow([
                        datetime.fromtimestamp(e.timestamp).isoformat(),
                        e.category.name,
                        e.event_type,
                        e.source,
                        e.target,
                        e.severity.name
                    ])
            return str(output_file)
        
        return ""
    
    def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze timeline for attack patterns."""
        patterns = {
            "lateral_movement": [],
            "privilege_escalation": [],
            "data_exfiltration": [],
            "persistence": []
        }
        
        # Check for lateral movement (multiple systems accessed)
        systems_accessed: Dict[str, Set[float]] = {}
        for event in self._events:
            if event.category == EventCategory.NETWORK:
                system = event.target
                if system not in systems_accessed:
                    systems_accessed[system] = set()
                systems_accessed[system].add(event.timestamp)
        
        if len(systems_accessed) > 3:
            patterns["lateral_movement"].append({
                "systems": list(systems_accessed.keys()),
                "indicators": "Multiple systems accessed within timeframe"
            })
        
        # Check for privilege escalation attempts
        auth_events = [e for e in self._events if e.category == EventCategory.AUTH]
        failed_auths = [e for e in auth_events if "failed" in e.event_type.lower()]
        
        if len(failed_auths) > 5:
            patterns["privilege_escalation"].append({
                "count": len(failed_auths),
                "indicators": "Multiple authentication failures"
            })
        
        return patterns
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get timeline statistics."""
        by_category = {}
        by_severity = {}
        
        for event in self._events:
            by_category[event.category.name] = by_category.get(event.category.name, 0) + 1
            by_severity[event.severity.name] = by_severity.get(event.severity.name, 0) + 1
        
        return {
            "case_id": self.case_id,
            "total_events": len(self._events),
            "time_range": {
                "start": datetime.fromtimestamp(self._events[0].timestamp).isoformat() if self._events else None,
                "end": datetime.fromtimestamp(self._events[-1].timestamp).isoformat() if self._events else None
            },
            "by_category": by_category,
            "by_severity": by_severity
        }
