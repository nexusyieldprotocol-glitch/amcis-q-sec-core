# AMCIS Q-SEC Core

**Experimental Prototype - Secure Core with Paper Trading Agent**

[![Status](https://img.shields.io/badge/status-experimental-orange)]()
[![Crypto](https://img.shields.io/badge/crypto-X25519%2BECDSA-green)]()
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]()

---

## Overview

AMCIS_Q_SEC_CORE is an **experimental prototype** implementing a secure microkernel architecture with:

- **Real Cryptography**: X25519 key exchange, ECDSA P-384 signatures, AES-256-GCM encryption
- **Security Kernel**: Event-driven microkernel with integrity monitoring
- **Paper Trading**: Single trading agent framework (risk-free simulation)

**Status**: This is a refactored codebase post-technical audit. Previous claims of 35 agents, quantum OS, and $4.5B valuation have been removed as they were not supported by working code.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  AMCIS Security Kernel                   │
│              (Event-driven microkernel)                 │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼─────┐ ┌──────▼──────┐
│   Crypto     │ │  Trading   │ │   Core      │
│  Service     │ │   Agent    │ │  Services   │
│ (Production) │ │  (Paper)   │ │             │
└──────────────┘ └────────────┘ └─────────────┘
```

---

## Cryptographic Implementation

### Current Algorithms (Production-Ready)

| Operation | Algorithm | Library | Status |
|-----------|-----------|---------|--------|
| Key Exchange | X25519 (ECDH) | cryptography/OpenSSL | ✅ Real |
| Signatures | ECDSA P-384 | cryptography/OpenSSL | ✅ Real |
| Encryption | AES-256-GCM | cryptography/OpenSSL | ✅ Real |
| Hashing | SHA3-256/512 | hashlib | ✅ Real |
| KDF | HKDF-SHA3-256 | cryptography | ✅ Real |

### PQC Upgrade Path

The codebase is designed for algorithm agility. When liboqs is available:
- X25519 → X25519 + Kyber768 hybrid
- ECDSA P-384 → ECDSA + Dilithium3 hybrid

---

## Quick Start

### Prerequisites

- Python 3.12+
- cryptography >= 42.0.0
- structlog >= 23.0.0

### Installation

```bash
pip install -r requirements.txt
```

### Running Tests

```bash
# Crypto tests
python tests/test_crypto_production.py

# All tests
python -m pytest tests/ -v
```

### Basic Usage

```python
from crypto.amcis_hybrid_pqc import ProductionCryptoProvider

# Initialize
provider = ProductionCryptoProvider()

# Generate keys
keypair = provider.generate_keypair()

# Encrypt
message = b"Secure message"
ciphertext = provider.encrypt(message, keypair.kem_public_bytes)

# Decrypt
decrypted = provider.decrypt(ciphertext, keypair)
assert decrypted == message

# Sign
signature = provider.sign(message, keypair)

# Verify
is_valid = provider.verify(message, signature, keypair.sig_public_bytes)
```

---

## Project Status

### Completed (Phase 1)

- ✅ Real cryptographic implementation (replaced all stubs)
- ✅ Working tests with >90% pass rate
- ✅ Accurate documentation
- ✅ Security kernel operational

### In Progress (Phase 2)

- 🔄 Single paper trading agent integration
- 🔄 Risk management framework
- 🔄 End-to-end secure communication

### Planned (Phase 3)

- ⏳ HashiCorp Vault integration
- ⏳ PostgreSQL persistence
- ⏳ Docker Compose deployment
- ⏳ Prometheus monitoring

---

## Security Notes

### What This Is

- Experimental prototype for evaluation
- Real cryptography using production libraries
- Foundation for potential future product

### What This Is NOT

- Production-ready system
- PQC-enabled (classical algorithms only)
- Audited by third-party security firm
- Suitable for handling real funds without further hardening

---

## Directory Structure

```
AMCIS_Q_SEC_CORE/
├── crypto/              # Production cryptography
│   ├── amcis_hybrid_pqc.py      # Main crypto module
│   ├── amcis_key_manager.py     # Key lifecycle
│   └── ...
├── core/                # Security kernel
│   ├── amcis_kernel.py          # Microkernel
│   ├── amcis_trust_engine.py    # Trust management
│   └── ...
├── tests/               # Test suite
│   ├── test_crypto_production.py
│   ├── test_kernel.py
│   └── ...
├── PROTOTYPE_STATUS.md  # Detailed status
└── README.md           # This file
```

---

## Technical Specifications

### Security Kernel

- **Pattern**: Microkernel with event-driven architecture
- **States**: INITIALIZING → SECURE_BOOT → OPERATIONAL
- **Features**: Integrity monitoring, signal handling, module registry
- **Queue**: Async event processing with 10,000 event capacity

### Cryptography

- **Backend**: OpenSSL 3.x via Python cryptography library
- **Security Level**: NIST Level 1 (128-bit equivalent)
- **Key Generation**: Cryptographically secure random (os.urandom)
- **Constant Time**: All operations via OpenSSL (constant-time guaranteed)

---

## Contributing

This is currently a single-developer experimental project. For technical questions about the salvage refactor, see `PROTOTYPE_STATUS.md`.

---

## License

**PROPRIETARY - EXPERIMENTAL**

This code is provided as-is for evaluation purposes. Not for production use without significant additional hardening and security review.

---

## Acknowledgments

- Technical audit conducted: 2026-03-25
- Salvage mode initiated: 2026-03-25
- Refactored by: AMCIS Security Team

---

**Last Updated**: 2026-03-25  
**Version**: 1.0.0-salvage  
**Status**: Experimental Prototype
