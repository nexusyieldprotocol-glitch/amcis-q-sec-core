"""
Threat Feed Management
======================

Manages threat intelligence feeds including:
- MISP integration
- STIX/TAXII feeds
- Custom IOC lists
- Threat actor profiles
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
from urllib.parse import urlparse

import structlog


class IOCTypes(Enum):
    IP = "ip-dst"
    DOMAIN = "domain"
    URL = "url"
    HASH_MD5 = "md5"
    HASH_SHA1 = "sha1"
    HASH_SHA256 = "sha256"
    EMAIL = "email"
    CVE = "cve"
    MUTEX = "mutex"
    YARA = "yara"


class ThreatSeverity(Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    INFO = 0


@dataclass
class IOC:
    """Indicator of Compromise."""
    value: str
    ioc_type: IOCTypes
    severity: ThreatSeverity
    source: str
    description: str
    first_seen: float
    last_seen: float
    tags: List[str] = field(default_factory=list)
    malware_family: Optional[str] = None
    threat_actor: Optional[str] = None
    confidence: int = 80  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value[:50] + "..." if len(self.value) > 50 else self.value,
            "type": self.ioc_type.value,
            "severity": self.severity.name,
            "source": self.source,
            "description": self.description,
            "tags": self.tags,
            "confidence": self.confidence
        }


@dataclass
class ThreatActor:
    """Threat actor profile."""
    name: str
    aliases: List[str]
    country: Optional[str]
    motivation: List[str]
    targets: List[str]
    ttp_ids: List[str]  # MITRE ATT&CK technique IDs
    active: bool = True
    first_observed: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "aliases": self.aliases,
            "country": self.country,
            "motivation": self.motivation,
            "targets": self.targets[:5],
            "ttp_count": len(self.ttp_ids),
            "active": self.active
        }


class ThreatFeed:
    """
    Threat Intelligence Feed Manager
    ================================
    
    Aggregates and manages threat intelligence from multiple sources.
    """
    
    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self.storage_path = storage_path or Path("/var/lib/amcis/threat_intel")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger("amcis.threat_intel")
        
        self._iocs: Dict[str, IOC] = {}
        self._actors: Dict[str, ThreatActor] = {}
        self._feed_metadata: Dict[str, Any] = {}
        self._last_update: float = 0
        
        # Built-in threat actor profiles
        self._load_builtin_actors()
        
        self.logger.info("threat_feed_initialized", ioc_count=len(self._iocs))
    
    def _load_builtin_actors(self) -> None:
        """Load builtin threat actor profiles."""
        actors = [
            ThreatActor(
                name="APT28",
                aliases=["Fancy Bear", "Sofacy", "Sednit", "STRONTIUM"],
                country="Russia",
                motivation=["espionage", "political"],
                targets=["government", "military", "media"],
                ttp_ids=["T1078", "T1059", "T1027", "T1071"]
            ),
            ThreatActor(
                name="APT29",
                aliases=["Cozy Bear", "The Dukes", "Cloaked Ursa"],
                country="Russia",
                motivation=["espionage"],
                targets=["government", "think_tank", "healthcare"],
                ttp_ids=["T1071", "T1053", "T1003", "T1087"]
            ),
            ThreatActor(
                name="Lazarus Group",
                aliases=["Hidden Cobra", "Zinc", "Nickel Academy"],
                country="North Korea",
                motivation=["financial", "espionage", "destruction"],
                targets=["financial", "cryptocurrency", "media"],
                ttp_ids=["T1071", "T1485", "T1491", "T1027"]
            ),
        ]
        for actor in actors:
            self._actors[actor.name] = actor
    
    def add_ioc(self, ioc: IOC) -> bool:
        """Add IOC to feed."""
        key = f"{ioc.ioc_type.value}:{ioc.value}"
        
        if key in self._iocs:
            # Update existing
            existing = self._iocs[key]
            existing.last_seen = time.time()
            existing.severity = max(existing.severity, ioc.severity, key=lambda x: x.value)
        else:
            self._iocs[key] = ioc
        
        return True
    
    def load_stix_bundle(self, bundle_path: Path) -> int:
        """Load STIX 2.1 bundle."""
        try:
            with open(bundle_path) as f:
                bundle = json.load(f)
            
            count = 0
            for obj in bundle.get("objects", []):
                if obj.get("type") == "indicator":
                    pattern = obj.get("pattern", "")
                    # Parse STIX pattern
                    ioc = self._parse_stix_pattern(pattern)
                    if ioc:
                        ioc.source = obj.get("created_by_ref", "STIX")
                        self.add_ioc(ioc)
                        count += 1
            
            self.logger.info("stix_bundle_loaded", count=count)
            return count
            
        except Exception as e:
            self.logger.error("stix_load_failed", error=str(e))
            return 0
    
    def _parse_stix_pattern(self, pattern: str) -> Optional[IOC]:
        """Parse STIX indicator pattern."""
        # Simplified parsing
        import re
        
        # Extract IPv4
        ip_match = re.search(r"ipv4-addr:value = '([^']+)'", pattern)
        if ip_match:
            return IOC(
                value=ip_match.group(1),
                ioc_type=IOCTypes.IP,
                severity=ThreatSeverity.HIGH,
                source="STIX",
                description="Malicious IP from STIX feed",
                first_seen=time.time(),
                last_seen=time.time()
            )
        
        # Extract domain
        domain_match = re.search(r"domain-name:value = '([^']+)'", pattern)
        if domain_match:
            return IOC(
                value=domain_match.group(1),
                ioc_type=IOCTypes.DOMAIN,
                severity=ThreatSeverity.HIGH,
                source="STIX",
                description="Malicious domain from STIX feed",
                first_seen=time.time(),
                last_seen=time.time()
            )
        
        return None
    
    def check_ioc(self, value: str, ioc_type: IOCTypes) -> Optional[IOC]:
        """Check if value is a known IOC."""
        key = f"{ioc_type.value}:{value}"
        return self._iocs.get(key)
    
    def get_actor_profile(self, name: str) -> Optional[ThreatActor]:
        """Get threat actor profile."""
        return self._actors.get(name)
    
    def search_iocs(self, tags: Optional[List[str]] = None, 
                   severity: Optional[ThreatSeverity] = None) -> List[IOC]:
        """Search IOCs by criteria."""
        results = []
        for ioc in self._iocs.values():
            if tags and not any(t in ioc.tags for t in tags):
                continue
            if severity and ioc.severity != severity:
                continue
            results.append(ioc)
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get threat intelligence statistics."""
        by_type = {}
        by_severity = {}
        
        for ioc in self._iocs.values():
            by_type[ioc.ioc_type.value] = by_type.get(ioc.ioc_type.value, 0) + 1
            by_severity[ioc.severity.name] = by_severity.get(ioc.severity.name, 0) + 1
        
        return {
            "total_iocs": len(self._iocs),
            "threat_actors": len(self._actors),
            "by_type": by_type,
            "by_severity": by_severity,
            "last_update": self._last_update
        }
