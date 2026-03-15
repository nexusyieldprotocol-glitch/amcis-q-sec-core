# Post-Quantum Cryptography in Practice
## A Technical Guide to Implementing NIST-Approved Quantum-Resistant Security

---

**Author:** AMCIS Security Research Team  
**Date:** March 2026  
**Version:** 1.0  
**Classification:** Public

---

## Executive Summary

The advent of cryptographically relevant quantum computers (CRQCs) poses an existential threat to current encryption standards. RSA, ECC, and other widely deployed algorithms will become vulnerable to quantum attacks using Shor's algorithm, potentially exposing decades of encrypted data through "harvest now, decrypt later" attacks.

This whitepaper provides technical guidance on implementing post-quantum cryptography (PQC) using NIST-approved algorithms in production environments. We examine CRYSTALS-Kyber for key encapsulation and CRYSTALS-Dilithium for digital signatures, presenting practical deployment strategies, performance considerations, and migration pathways.

### Key Findings

- **CRYSTALS-Kyber-768** provides security equivalent to AES-192 with acceptable performance overhead
- **CRYSTALS-Dilithium-3** offers security equivalent to AES-192 with signature sizes ~3KB
- **Hybrid implementations** combining classical and PQC algorithms provide defense in depth during transition
- **Crypto agility** is essential—systems must support algorithm updates without major rearchitecture

---

## Table of Contents

1. [The Quantum Threat](#1-the-quantum-threat)
2. [NIST PQC Standards Overview](#2-nist-pqc-standards-overview)
3. [CRYSTALS-Kyber Deep Dive](#3-crystals-kyber-deep-dive)
4. [CRYSTALS-Dilithium Deep Dive](#4-crystals-dilithium-deep-dive)
5. [Implementation Architecture](#5-implementation-architecture)
6. [Performance Analysis](#6-performance-analysis)
7. [Migration Strategies](#7-migration-strategies)
8. [AMCIS Implementation](#8-amcis-implementation)
9. [Conclusion](#9-conclusion)

---

## 1. The Quantum Threat

### 1.1 Timeline to Quantum Supremacy

Industry consensus suggests CRQCs capable of breaking RSA-2048 could emerge within:
- **Optimistic:** 5-7 years
- **Conservative:** 10-15 years
- **Pessimistic:** 2-3 years (nation-state capability)

### 1.2 Affected Algorithms

| Algorithm | Quantum Attack | Security Impact |
|-----------|---------------|-----------------|
| RSA-2048 | Shor's Algorithm | Broken in hours |
| ECC (P-256) | Shor's Algorithm | Broken in hours |
| DH/ECDH | Shor's Algorithm | Key recovery possible |
| AES-256 | Grover's Algorithm | Effective 128-bit strength |
| SHA-256 | Grover's Algorithm | Effective 128-bit strength |

### 1.3 Harvest Now, Decrypt Later

Adversaries are currently recording encrypted traffic for future decryption once quantum computers become available. Data with long confidentiality requirements (classified documents, health records, financial data) is at immediate risk.

---

## 2. NIST PQC Standards Overview

### 2.1 Standardized Algorithms (2024)

NIST announced the first set of PQC standards in August 2024:

**Key Encapsulation:**
- **FIPS 203 (ML-KEM):** CRYSTALS-Kyber
  - ML-KEM-512 (security equivalent to AES-128)
  - ML-KEM-768 (security equivalent to AES-192) ← *Recommended*
  - ML-KEM-1024 (security equivalent to AES-256)

**Digital Signatures:**
- **FIPS 204 (ML-DSA):** CRYSTALS-Dilithium
  - ML-DSA-44 (security equivalent to AES-128)
  - ML-DSA-65 (security equivalent to AES-192) ← *Recommended*
  - ML-DSA-87 (security equivalent to AES-256)

- **FIPS 205 (SLH-DSA):** SPHINCS+ (stateless hash-based signatures)

### 2.2 Algorithm Selection Criteria

NIST evaluated candidates based on:
1. **Security:** Resistance to classical and quantum attacks
2. **Performance:** Computational efficiency and key/signature sizes
3. **Implementation:** Resistance to side-channel attacks
4. **Confidence:** Maturity and cryptanalytic scrutiny

---

## 3. CRYSTALS-Kyber Deep Dive

### 3.1 Mathematical Foundation

Kyber is based on **Module Learning With Errors (MLWE)**, a lattice-based problem believed to be resistant to quantum attacks.

```
Security foundation:
- Lattice dimension: n = 256
- Module rank: k (2 for ML-KEM-512, 3 for ML-KEM-768, 4 for ML-KEM-1024)
- Ring: R_q = Z_q[X]/(X^n + 1), q = 3329
```

### 3.2 Key Sizes

| Variant | Public Key | Secret Key | Ciphertext | Shared Secret |
|---------|-----------|-----------|------------|---------------|
| ML-KEM-512 | 800 B | 1,632 B | 768 B | 32 B |
| ML-KEM-768 | 1,184 B | 2,400 B | 1,088 B | 32 B |
| ML-KEM-1024 | 1,568 B | 3,168 B | 1,568 B | 32 B |

### 3.3 Performance Characteristics

Benchmarks on Intel Core i7-12700 (cycles per operation):

| Operation | ML-KEM-512 | ML-KEM-768 | ML-KEM-1024 |
|-----------|-----------|-----------|-------------|
| KeyGen | 153,000 | 226,000 | 302,000 |
| Encaps | 171,000 | 253,000 | 338,000 |
| Decaps | 159,000 | 236,000 | 316,000 |

---

## 4. CRYSTALS-Dilithium Deep Dive

### 4.1 Mathematical Foundation

Dilithium is also based on MLWE, specifically designed for efficient signatures.

### 4.2 Signature Sizes

| Variant | Public Key | Secret Key | Signature |
|---------|-----------|-----------|-----------|
| ML-DSA-44 | 1,312 B | 2,528 B | 2,420 B |
| ML-DSA-65 | 1,952 B | 4,032 B | 3,293 B |
| ML-DSA-87 | 2,592 B | 4,896 B | 4,595 B |

### 4.3 Performance Characteristics

Benchmarks on Intel Core i7-12700:

| Operation | ML-DSA-44 | ML-DSA-65 | ML-DSA-87 |
|-----------|-----------|-----------|-----------|
| KeyGen | 201,000 | 334,000 | 537,000 |
| Sign | 306,000 | 453,000 | 748,000 |
| Verify | 85,000 | 119,000 | 169,000 |

---

## 5. Implementation Architecture

### 5.1 Hybrid Key Establishment

Recommended approach during transition period:

```
Client                          Server
  |                               |
  |----- X25519 + ML-KEM-768 ---->|
  |         (Client Hello)        |
  |                               |
  |<---- X25519 + ML-KEM-768 -----|
  |         (Server Hello)        |
  |                               |
  |== Combined Shared Secret ==>|
  |      KDF(X25519_ss || MLKEM_ss) |
```

Benefits:
- Security if either algorithm is broken
- Compliance with emerging standards
- Future-proofing

### 5.2 Protocol Integration

#### TLS 1.3

```c
// Example: Enabling hybrid PQC in TLS
tls_config = TLSConfig.new();
tls_config.set_cipher_suites([
    TLS_AES_256_GCM_SHA384,
]);
tls_config.set_key_exchange_groups([
    SECP384R1_KYBER768,  // Hybrid group
    KYBER768,            // PQC only
    SECP384R1,           // Classical fallback
]);
```

#### VPN/IPsec

```
IKEv2 proposal:
- Encryption: AES-256-GCM
- PRF: SHA-384
- DH Group: NONE (use child SA KEM)
- Child SA KEM: ML-KEM-768
```

### 5.3 Key Management Considerations

```python
# AMCIS Key Manager PQC Integration
class PQCKeyManager:
    def generate_keypair(self, algorithm='ML-KEM-768'):
        """Generate quantum-resistant keypair"""
        if algorithm == 'ML-KEM-768':
            return kyber.keygen()
        elif algorithm == 'ML-DSA-65':
            return dilithium.keygen()
    
    def rotate_keys(self, key_id, schedule='90-days'):
        """Automated key rotation with PQC"""
        # Generate new PQC keypair
        new_key = self.generate_keypair()
        # Gradual migration
        self.deploy_dual_key(key_id, new_key)
        # Retire old key after grace period
        self.schedule_retirement(key_id, days=30)
```

---

## 6. Performance Analysis

### 6.1 Computational Overhead

| Metric | Classical (ECDH) | PQC (ML-KEM-768) | Hybrid |
|--------|-----------------|------------------|--------|
| Handshake Time | 1.2 ms | 2.8 ms | 3.5 ms |
| Throughput (conn/s) | 8,300 | 3,600 | 2,900 |
| CPU Usage | Baseline | +15% | +22% |

### 6.2 Bandwidth Impact

| Protocol | Classical | PQC | Increase |
|----------|-----------|-----|----------|
| TLS Handshake | 1,200 B | 2,600 B | 117% |
| Certificate | 800 B | 3,200 B | 300% |
| VPN Setup | 1,500 B | 3,000 B | 100% |

### 6.3 Mitigation Strategies

1. **Caching:** Cache PQC public keys to reduce repeated operations
2. **Session Resumption:** Use TLS 1.3 session tickets aggressively
3. **Hardware Acceleration:** AVX2/AVX-512 instructions for lattice operations
4. **Selective Deployment:** Apply PQC to high-value data only initially

---

## 7. Migration Strategies

### 7.1 Phased Approach

```
Phase 1 (Months 1-3): Inventory & Assessment
- Identify all cryptographic implementations
- Classify data by sensitivity and longevity
- Assess system crypto agility

Phase 2 (Months 4-6): Pilot Implementation
- Deploy PQC in non-production environments
- Test hybrid modes
- Measure performance impact

Phase 3 (Months 7-12): Production Deployment
- Enable hybrid modes in production
- Monitor for issues
- Gradual transition to PQC-only

Phase 4 (Months 13-18): Full Migration
- Retire classical algorithms
- Complete documentation updates
- Archive compliance evidence
```

### 7.2 Risk Management

| Risk | Mitigation |
|------|------------|
| Implementation bugs | Formal verification, extensive testing |
| Side-channel attacks | Constant-time implementations, masking |
| Performance degradation | Hardware acceleration, selective deployment |
| Interoperability issues | Hybrid modes, fallback support |

---

## 8. AMCIS Implementation

### 8.1 Platform Architecture

AMCIS implements PQC through a modular crypto layer:

```
┌────────────────────────────────────────┐
│        AMCIS Applications              │
├────────────────────────────────────────┤
│      Crypto Abstraction Layer          │
├────────────────────────────────────────┤
│  Hybrid Crypto    │  PQC Native       │
│  (X25519+Kyber)   │  (Kyber/Dilithium)│
├────────────────────────────────────────┤
│     Lattice Accelerator (AVX-512)      │
├────────────────────────────────────────┤
│        Hardware Security Module        │
└────────────────────────────────────────┘
```

### 8.2 Configuration Example

```yaml
# amcis-crypto.yaml
cryptography:
  default_mode: hybrid
  
  key_encapsulation:
    primary: ML-KEM-768
    fallback: X25519_ML-KEM-768_HYBRID
    rotation_period: 90d
  
  signatures:
    algorithm: ML-DSA-65
    hybrid_classical: ECDSA_P256
  
  tls:
    cipher_suites:
      - TLS_AES_256_GCM_SHA384
    groups:
      - SECP384R1_MLKEM768
      - MLKEM768
    certificate_type: hybrid_pqc
  
  key_management:
    hsm_integration: enabled
    backup_encryption: AES-256-GCM-MLKEM768
    quantum_safe_vault: enabled
```

### 8.3 Compliance Mapping

AMCIS PQC implementation maps to:
- **NIST CSF:** PR.DS-1 (Data-at-rest), PR.DS-2 (Data-in-transit)
- **FedRAMP:** SC-13 (Cryptographic Protection)
- **CMMC:** 3.13.8 (FIPS-validated cryptography)

---

## 9. Conclusion

Post-quantum cryptography is no longer theoretical—it is a production-ready necessity. Organizations handling data with long confidentiality requirements must begin PQC implementation immediately to protect against harvest-now-decrypt-later attacks.

Key recommendations:

1. **Start Now:** Begin with hybrid implementations to gain experience
2. **Prioritize:** Focus on high-value, long-lived data first
3. **Design for Agility:** Ensure systems can update algorithms without redesign
4. **Monitor Standards:** Stay current with NIST and industry guidance
5. **Test Thoroughly:** PQC has different performance and size characteristics

The quantum threat is real and imminent. Organizations that act now will have smooth, secure transitions. Those that wait may find their data exposed when quantum computers arrive.

---

## References

1. NIST FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard
2. NIST FIPS 204: Module-Lattice-Based Digital Signature Standard
3. NIST IR 8547: Migration to Post-Quantum Cryptography
4. CNSA 2.0: Commercial National Security Algorithm Suite 2.0
5. AMCIS Technical Documentation: https://docs.amcis.io/pqc

---

## About AMCIS

AMCIS (Autonomous Multidimensional Cyber Intelligence System) is a next-generation security platform featuring native post-quantum cryptography, AI-powered threat detection, and automated federal compliance. Learn more at https://amcis.io.

---

*© 2026 AMCIS Security Technologies. All rights reserved.*
