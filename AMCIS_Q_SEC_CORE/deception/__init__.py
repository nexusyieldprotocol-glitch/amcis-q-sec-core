"""
AMCIS Deception Module
======================

Honeypot and deception technology for advanced threat detection.
"""

from .honeypot import Honeypot, DeceptionEvent
from .decoy_generator import DecoyGenerator

__all__ = ["Honeypot", "DeceptionEvent", "DecoyGenerator"]
