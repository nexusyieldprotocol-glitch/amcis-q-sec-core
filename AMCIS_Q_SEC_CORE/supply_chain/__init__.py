"""
AMCIS Supply Chain Security Module
===================================

Supply chain security components for AMCIS_Q_SEC_CORE.
Provides SBOM generation, dependency validation, and
signature enforcement capabilities.

NIST Alignment: SP 800-161 (Supply Chain Risk Management)
"""

from .amcis_sbom_generator import SBOMGenerator, SBOMFormat, Component
from .amcis_dependency_validator import DependencyValidator, VulnerabilityReport
from .amcis_signature_enforcer import SignatureEnforcer, SignatureStatus

__all__ = [
    "SBOMGenerator",
    "SBOMFormat",
    "Component",
    "DependencyValidator",
    "VulnerabilityReport",
    "SignatureEnforcer",
    "SignatureStatus",
]

__version__ = "1.0.0"
