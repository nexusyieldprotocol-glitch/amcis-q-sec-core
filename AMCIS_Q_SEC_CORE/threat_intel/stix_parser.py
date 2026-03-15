"""
STIX Parser
===========

Parses STIX 2.1 threat intelligence bundles.
"""

import json
from typing import Any, Dict, List, Optional

import structlog


class STIXParser:
    """
    STIX 2.1 Bundle Parser
    ======================
    
    Parses STIX threat intelligence for IOC extraction.
    """
    
    def __init__(self) -> None:
        self.logger = structlog.get_logger("amcis.stix_parser")
    
    def parse_bundle(self, bundle_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse STIX bundle and extract indicators."""
        indicators = []
        
        objects = bundle_data.get("objects", [])
        
        for obj in objects:
            obj_type = obj.get("type")
            
            if obj_type == "indicator":
                indicator = self._parse_indicator(obj)
                if indicator:
                    indicators.append(indicator)
            elif obj_type == "malware":
                indicators.append(self._parse_malware(obj))
            elif obj_type == "threat-actor":
                indicators.append(self._parse_threat_actor(obj))
        
        return indicators
    
    def _parse_indicator(self, obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse STIX indicator object."""
        pattern = obj.get("pattern", "")
        
        return {
            "type": "indicator",
            "id": obj.get("id"),
            "pattern": pattern,
            "labels": obj.get("labels", []),
            "created": obj.get("created"),
            "valid_from": obj.get("valid_from"),
            "description": obj.get("description", "")
        }
    
    def _parse_malware(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Parse STIX malware object."""
        return {
            "type": "malware",
            "id": obj.get("id"),
            "name": obj.get("name"),
            "labels": obj.get("labels", []),
            "description": obj.get("description", "")
        }
    
    def _parse_threat_actor(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Parse STIX threat actor object."""
        return {
            "type": "threat_actor",
            "id": obj.get("id"),
            "name": obj.get("name"),
            "aliases": obj.get("aliases", []),
            "description": obj.get("description", "")
        }
