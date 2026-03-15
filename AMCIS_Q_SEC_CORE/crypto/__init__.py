"""
AMCIS Cryptographic Module
===========================

Post-quantum cryptographic components for AMCIS_Q_SEC_CORE.
Provides hybrid PQC implementations, key management, certificate
generation, and tamper-evident logging.

NIST Alignment: FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA)
"""

from .amcis_hybrid_pqc import HybridPQCCipher, PQCKEM, PQCSignature
from .amcis_key_manager import KeyManager, KeyType, KeyMaterial
from .amcis_cert_generator import CertificateGenerator, CertificateChain
from .amcis_merkle_log import MerkleLog, LogEntry, MerkleProof

__all__ = [
    "HybridPQCCipher",
    "PQCKEM",
    "PQCSignature",
    "KeyManager",
    "KeyType",
    "KeyMaterial",
    "CertificateGenerator",
    "CertificateChain",
    "MerkleLog",
    "LogEntry",
    "MerkleProof",
]

__version__ = "1.0.0"
