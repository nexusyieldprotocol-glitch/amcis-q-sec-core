"""
AMCIS Network Security Module
==============================

Network defense components for AMCIS_Q_SEC_CORE.
Provides microsegmentation, DNS tunnel detection, and
attack surface mapping capabilities.

NIST Alignment: SP 800-53 (SC-7 Boundary Protection)
"""

from .amcis_microsegmentation import MicrosegmentationEngine, FirewallRule
from .amcis_dns_tunnel_detector import DNSTunnelDetector, DNSQuery
from .amcis_port_surface_mapper import PortSurfaceMapper, PortService

__all__ = [
    "MicrosegmentationEngine",
    "FirewallRule",
    "DNSTunnelDetector",
    "DNSQuery",
    "PortSurfaceMapper",
    "PortService",
]

__version__ = "1.0.0"
