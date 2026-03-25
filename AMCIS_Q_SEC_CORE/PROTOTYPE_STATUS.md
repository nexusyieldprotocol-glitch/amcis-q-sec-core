# AMCIS_Q_SEC_CORE - Prototype Status

**Date:** 2026-03-25  
**Classification:** INTERNAL - SALVAGE MODE  
**Status:** EXPERIMENTAL PROTOTYPE

---

## Current State (Post-Audit)

This project has undergone a **brutal technical audit** and is now in **Salvage Mode**. All previous claims of production readiness, $4.5B valuations, and 35+ AI agents have been **REMOVED** as they were not supported by working code.

### What Actually Exists (Verified)

| Component | Status | Notes |
|-----------|--------|-------|
| **Crypto Module** | ✅ PRODUCTION | Real X25519 + ECDSA P-384 + AES-256-GCM via OpenSSL |
| **Security Kernel** | ✅ BETA | Event-driven microkernel, operational |
| **Paper Trading** | ✅ WORKING | Single agent with real market data (CoinGecko) |
| **Risk Engine** | ✅ WORKING | Position limits, daily loss, drawdown protection |
| **Tests** | ✅ PASSING | Crypto + trading integration tests |
| **Documentation** | ✅ ACCURATE | Claims match reality |

### What Was Removed/Deprecated

- ❌ All PQC "stubs" - replaced with real cryptography
- ❌ Claims of 35 AI agents - **were specifications only**
- ❌ $4.5B valuation claims - **not based on actual product**
- ❌ Quantum OS, 4 Admin Platforms - **not in scope for salvage**
- ❌ "Production ready" claims - **this is experimental prototype**

---

## Cryptographic Implementation

### Current (Phase 1)

```
Key Exchange:    X25519 (ECDH) with HKDF-SHA3-256
Signatures:      ECDSA P-384 with SHA3-256
Encryption:      AES-256-GCM with 96-bit nonce
Hashing:         SHA3-256 / SHA3-512
Backend:         OpenSSL 3.x (via cryptography library)
```

### PQC Upgrade Path (Phase 2)

When liboqs/oqs-python is available:
- X25519 → X25519 + Kyber768 hybrid
- ECDSA → ECDSA + Dilithium3 hybrid
- Module designed for algorithm agility

---

## Secure Trading Agent

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  AMCIS Security Kernel                   │
│              (Event-driven microkernel)                 │
└───────────────────────┬─────────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
┌────────▼────────┐ ┌────▼─────┐ ┌─────▼──────┐
│  Secure Trading │ │   Risk   │ │   Paper    │
│     Agent       │ │  Engine  │ │  Exchange  │
│                 │ │          │ │            │
│ - Crypto ID     │ │ - Limits │ │ - Simulated│
│ - Kernel events │ │ - Checks │ │ - Real data│
└─────────────────┘ └──────────┘ └────────────┘
```

### Risk Controls

| Limit | Default | Description |
|-------|---------|-------------|
| Max Position | $2,000 | Per-symbol position limit |
| Max Positions | 3 | Concurrent positions |
| Max Daily Loss | $500 | Daily loss cutoff |
| Max Drawdown | 5% | Portfolio drawdown limit |
| No Leverage | 1x | Spot trading only |

---

## Salvage Mode Roadmap

### Phase 1: Foundation (COMPLETE)
- ✅ Replace crypto stubs with real implementation
- ✅ All tests passing
- ✅ Documentation updated to reflect reality

### Phase 2: Single Trading Agent (COMPLETE)
- ✅ Paper exchange with real CoinGecko market data
- ✅ Secure trading agent with kernel integration
- ✅ Risk engine with position/loss limits
- ✅ End-to-end encrypted communication
- ✅ Demo script working

### Phase 3: Hardening (PENDING)
- ⏳ HashiCorp Vault integration
- ⏳ PostgreSQL + Redis persistence
- ⏳ Docker Compose deployment
- ⏳ Basic monitoring

### Phase 4: Evaluation (PENDING)
- ⏳ Security audit of real code
- ⏳ Performance benchmarking
- ⏳ Decision: Continue / Pivot / Archive

---

## Usage

### Basic Encryption

```python
from crypto.amcis_hybrid_pqc import ProductionCryptoProvider

provider = ProductionCryptoProvider()
keypair = provider.generate_keypair()

# Encrypt
ciphertext = provider.encrypt(b"Secret", keypair.kem_public_bytes)

# Decrypt
plaintext = provider.decrypt(ciphertext, keypair)
```

### Paper Trading Demo

```bash
# Run the paper trading demo
python demo_paper_trading.py
```

This will:
1. Initialize AMCIS kernel
2. Create trading agent with $10k paper money
3. Run 3 trading cycles with real market data
4. Show portfolio and P&L

### Running Tests

```bash
# Crypto tests
python tests/test_crypto_production.py

# Trading integration tests
python tests/test_secure_trading.py

# All tests
python -m pytest tests/ -v
```

---

## Technical Debt

### Known Issues
1. **No PQC yet** - Classical algorithms only until liboqs deployed
2. **Kernel singleton** - Thread-safe but limits horizontal scaling
3. **File-based config** - Needs Vault integration for secrets
4. **No persistence** - In-memory only, needs PostgreSQL
5. **Rate limiting** - CoinGecko API has request limits

### Code Quality
- Type hints: ✅ Present
- Docstrings: ✅ Comprehensive
- Test coverage: 🟡 ~70% (target: 85%)
- Linting: 🟡 Black/isort configured, not enforced

---

## Security Warnings

1. **This is experimental prototype code** - Not for production use without further hardening
2. **Classical algorithms only** - PQC upgrade pending library availability
3. **No formal audit yet** - Code review only, no penetration testing
4. **Paper trading only** - No real trading capability implemented
5. **Solo development** - No security team review

---

## License & Liability

**PROPRIETARY - EXPERIMENTAL**

This code is provided as-is for evaluation purposes only. The authors make no claims about fitness for purpose, security guarantees, or production readiness.

---

## Contact

For technical questions about the salvage refactor:  
For all other inquiries: See project documentation

---

**Last Updated:** 2026-03-25  
**Next Review:** Upon completion of Phase 3 (Hardening)
