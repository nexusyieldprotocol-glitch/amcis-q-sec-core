"""
SPHINX™ Distributed AI Consensus Network
=========================================
Byzantine Fault-Tolerant distributed intelligence system.

Version: 2.0.0-Commercial
Classification: Proprietary

Copyright (c) 2026 AMCIS Global. All rights reserved.
"""

__version__ = "2.0.0"
__author__ = "AMCIS Global"
__license__ = "Commercial"

from .sphinx_node import SphinxNode
from .consensus_engine import HotStuffConsensus
from .p2p_network import P2PNetwork
from .crypto_primitives import MLKEMKeyExchange, DilithiumSignature, FRISystem, ThresholdSignature

__all__ = [
    "SphinxNode",
    "HotStuffConsensus", 
    "P2PNetwork",
    "MLKEMKeyExchange",
    "DilithiumSignature",
]
