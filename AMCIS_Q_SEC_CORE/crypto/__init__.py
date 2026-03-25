"""
AMCIS Cryptographic Module
===========================

Production-grade cryptographic components for AMCIS_Q_SEC_CORE.
Provides hybrid encryption, digital signatures, key management, 
certificate generation, and tamper-evident logging.

CURRENT STATUS (Phase 1):
- Key Exchange: X25519 (ECDH)
- Signatures: ECDSA P-384
- Encryption: AES-256-GCM
- Hashing: SHA3-256

PQC UPGRADE PATH (Phase 2):
- X25519 → X25519 + Kyber768
- ECDSA → ECDSA + Dilithium3

Backend: OpenSSL 3.x via Python cryptography library
"""

from .amcis_hybrid_pqc import (
    ProductionCryptoProvider,
    HybridPQCCipher,  # Backward compatibility alias
    HybridCiphertext,
    HybridSignature,
    CryptoKeypair,
    EncapsulationResult
)
from .amcis_key_manager import KeyManager, KeyType, KeyMaterial
from .amcis_cert_generator import CertificateGenerator, CertificateChain
from .amcis_merkle_log import MerkleLog, LogEntry, MerkleProof

__all__ = [
    # Production crypto
    "ProductionCryptoProvider",
    "HybridPQCCipher",
    "HybridCiphertext",
    "HybridSignature",
    "CryptoKeypair",
    "EncapsulationResult",
    # Key management
    "KeyManager",
    "KeyType",
    "KeyMaterial",
    # Certificates
    "CertificateGenerator",
    "CertificateChain",
    # Logging
    "MerkleLog",
    "LogEntry",
    "MerkleProof",
]

__version__ = "1.0.0-salvage"
__status__ = "EXPERIMENTAL - Phase 1"
