"""
AMCIS Threat Intelligence Module
=================================

Threat intelligence aggregation, analysis, and IOC matching.
Integrates with MISP, STIX/TAXII, and custom threat feeds.
"""

from .threat_feed import ThreatFeed, IOC, ThreatActor
from .ioc_matcher import IOCMatcher
from .stix_parser import STIXParser

__all__ = ["ThreatFeed", "IOC", "ThreatActor", "IOCMatcher", "STIXParser"]
