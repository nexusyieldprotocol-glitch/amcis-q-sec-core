# Quantum-Resistant Infrastructure
## Building Systems for the Post-Quantum Era

---

**Author:** AMCIS Infrastructure Architecture Team  
**Date:** March 2026  
**Version:** 1.0  
**Classification:** Public

---

## Executive Summary

The transition to post-quantum cryptography (PQC) represents the most significant cryptographic migration in history. Unlike previous algorithm transitions, the move to quantum-resistant systems affects every layer of the technology stack—from TLS handshakes to database encryption, from code signing to secure boot processes.

This whitepaper provides a comprehensive guide for building quantum-resistant infrastructure. We cover architectural patterns, migration strategies, hardware considerations, and operational procedures necessary to maintain security in the quantum era.

### Key Findings

- **Crypto agility** is the foundation of quantum-resistant infrastructure
- **Hybrid deployments** provide defense in depth during transition
- **Hardware security modules** require PQC firmware updates
- **Supply chain** must be secured end-to-end with quantum-resistant signatures

---

## Table of Contents

1. [Infrastructure Threat Model](#1-infrastructure-threat-model)
2. [Architectural Principles](#2-architectural-principles)
3. [Network Layer Security](#3-network-layer-security)
4. [Storage and Database Security](#4-storage-and-database-security)
5. [Compute and Container Security](#5-compute-and-container-security)
6. [Identity and Access Management](#6-identity-and-access-management)
7. [Supply Chain Security](#7-supply-chain-security)
8. [Migration Roadmap](#8-migration-roadmap)
9. [AMCIS Reference Architecture](#9-amcis-reference-architecture)

---

## 1. Infrastructure Threat Model

### 1.1 Quantum Attack Vectors

```
┌─────────────────────────────────────────────────────────────────┐
│                 QUANTUM INFRASTRUCTURE THREATS                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SHORT TERM (Now - 5 years)          LONG TERM (5-15 years)    │
│  ─────────────────────────           ────────────────────────   │
│                                                                 │
│  • Harvest now, decrypt later        • Real-time TLS breaking   │
│  • Long-term key compromise          • Certificate forgery      │
│  • Encrypted backup exposure         • Supply chain attacks     │
│  • Encrypted database theft          • Firmware compromise      │
│  • VPN tunnel recording              • Identity theft at scale  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Critical Assets at Risk

| Asset | Current Protection | Quantum Risk | Priority |
|-------|-------------------|--------------|----------|
| TLS Certificates | ECC P-256 | Broken | Critical |
| VPN Tunnels | ECDH/ECDSA | Broken | Critical |
| Database Encryption | AES-256-GCM | Reduced | High |
| Backup Encryption | RSA-2048 | Broken | Critical |
| Code Signing | ECDSA | Broken | Critical |
| SSH Keys | ECDSA/Ed25519 | Broken | High |
| Disk Encryption | AES-XTS | Reduced | Medium |

---

## 2. Architectural Principles

### 2.1 Crypto Agility

```python
class CryptoAgilityFramework:
    """
    Design systems to support cryptographic algorithm evolution
    """
    
    def __init__(self):
        self.algorithms = self.load_algorithm_registry()
        self.policy = self.load_crypto_policy()
    
    def encrypt(self, data: bytes, context: dict) -> Ciphertext:
        """
        Encrypt using policy-defined algorithm
        Algorithm can be updated without code changes
        """
        # Get algorithm based on policy and context
        algorithm = self.policy.select_algorithm(
            operation="encrypt",
            data_classification=context['classification'],
            compliance_requirements=context['compliance']
        )
        
        # Algorithm implementation loaded dynamically
        cipher = self.load_cipher(algorithm)
        
        # Include algorithm identifier in output for future decryption
        return Ciphertext(
            algorithm_id=algorithm.id,
            version=algorithm.version,
            ciphertext=cipher.encrypt(data),
            parameters=cipher.get_parameters()
        )
    
    def decrypt(self, ciphertext: Ciphertext, key: Key) -> bytes:
        """
        Decrypt using algorithm specified in ciphertext
        Supports legacy algorithms during migration
        """
        cipher = self.load_cipher(
            id=ciphertext.algorithm_id,
            version=ciphertext.version
        )
        return cipher.decrypt(ciphertext.ciphertext, key)
```

### 2.2 Hybrid Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYBRID SECURITY STACK                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Application Layer                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Data encrypted with: AES-256-GCM + ML-KEM key wrap    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Transport Layer                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  TLS 1.3 with: X25519Kyber768 hybrid key exchange      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Authentication Layer                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Certificates with: ECDSA + ML-DSA dual signatures     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Storage Layer                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Disk encryption: AES-XTS with ML-KEM wrapped keys     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Layered Defense

| Layer | Classical Security | Quantum Enhancement |
|-------|-------------------|---------------------|
| Perimeter | Firewall, IDS | PQC VPN, quantum-safe TLS |
| Network | TLS 1.3, mTLS | Hybrid PQC handshakes |
| Application | OAuth, JWT | PQC-signed tokens |
| Data | AES encryption | ML-KEM wrapped keys |
| Storage | Disk encryption | PQC key hierarchy |

---

## 3. Network Layer Security

### 3.1 Quantum-Safe TLS

```go
// TLS Configuration with Hybrid PQC
tlsConfig := &tls.Config{
    CipherSuites: []uint16{
        tls.TLS_AES_256_GCM_SHA384,
        tls.TLS_CHACHA20_POLY1305_SHA256,
    },
    Curves: []tls.CurveID{
        tls.X25519Kyber768Draft00,  // Hybrid PQC
        tls.SecP384r1MLKEM768,      // Hybrid PQC
        tls.X25519,                  // Classical fallback
        tls.SecP384r1,               // Classical fallback
    },
    Certificates: []tls.Certificate{
        {
            Certificate: [][]byte{hybridCert},
            PrivateKey:  hybridPrivateKey,
        },
    },
    MinVersion: tls.VersionTLS13,
}
```

### 3.2 VPN Architecture

```
┌─────────────┐                    ┌─────────────┐
│   Office    │◄─────IPsec VPN────►│    Cloud    │
│   Network   │   ML-KEM-768 +     │  Resources  │
│             │   AES-256-GCM      │             │
└─────────────┘                    └─────────────┘
       │                                  │
       │         ┌──────────────┐         │
       └────────►│  Quantum Key │◄────────┘
                 │  Distribution│
                 │    (QKD)     │
                 └──────────────┘
```

### 3.3 Certificate Infrastructure

```python
class QuantumSafePKI:
    """
    PKI with hybrid classical-PQC certificates
    """
    
    def issue_hybrid_certificate(self, csr: CSR) -> Certificate:
        """Issue certificate with dual signatures"""
        
        # Generate classical keypair (ECDSA P-384)
        classical_key = ec.generate_private_key(ec.SECP384R1())
        
        # Generate PQC keypair (ML-DSA-65)
        pqc_key = dilithium.keygen(variant='ML-DSA-65')
        
        # Create certificate with both public keys
        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(csr.subject)
        cert_builder = cert_builder.issuer_name(self.ca_name)
        cert_builder = cert_builder.public_key(classical_key.public_key())
        
        # Add PQC public key as extension
        cert_builder = cert_builder.add_extension(
            x509.SubjectAlternativePQCKey(pqc_key.public_key),
            critical=False
        )
        
        # Sign with both algorithms
        classical_sig = classical_key.sign(cert_tbs, ec.ECDSA(hashes.SHA384()))
        pqc_sig = pqc_key.sign(cert_tbs)
        
        return HybridCertificate(
            certificate=cert_builder.build(),
            classical_signature=classical_sig,
            pqc_signature=pqc_sig
        )
```

---

## 4. Storage and Database Security

### 4.1 Database Encryption

```python
class QuantumSafeDatabaseEncryption:
    """
    Transparent database encryption with PQC key management
    """
    
    def __init__(self, key_manager):
        self.key_manager = key_manager
        self.data_key_cache = {}
    
    def encrypt_record(self, table: str, record_id: str, plaintext: bytes) -> bytes:
        """Encrypt database record with PQC-wrapped key"""
        
        # Get or generate data encryption key
        dek = self.get_data_key(table, record_id)
        
        # Encrypt with AES-256-GCM
        aesgcm = AESGCM(dek)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        # Wrap DEK with ML-KEM
        wrapped_dek = self.key_manager.wrap_key(dek, algorithm='ML-KEM-768')
        
        return json.dumps({
            'ciphertext': base64.b64encode(ciphertext).decode(),
            'nonce': base64.b64encode(nonce).decode(),
            'wrapped_key': wrapped_dek,
            'key_version': self.key_manager.current_version()
        })
```

### 4.2 Backup Encryption

```yaml
# Backup encryption configuration
backup_encryption:
  algorithm: AES-256-GCM
  key_management:
    type: hierarchical
    root_key:
      algorithm: ML-KEM-768
      storage: HSM
    data_keys:
      rotation_period: 30d
      algorithm: AES-256
  signature:
    algorithm: ML-DSA-65
    certificate_chain: /etc/amcis/backup-certs.pem
  integrity:
    hash_algorithm: SHA3-256
    merkle_tree: enabled
```

---

## 5. Compute and Container Security

### 5.1 Secure Boot with PQC

```
┌─────────────────────────────────────────────────────────────────┐
│                 SECURE BOOT WITH PQC SIGNATURES                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │   BIOS   │──→│  UEFI    │──→│  Boot    │──→│   OS     │    │
│  │  (RoT)   │   │  Firmware│   │  Loader  │   │  Kernel  │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘    │
│       │              │              │              │           │
│       ▼              ▼              ▼              ▼           │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │  ECDSA   │   │  ECDSA   │   │  ECDSA   │   │  ECDSA   │    │
│  │ ML-DSA-65│   │ ML-DSA-65│   │ ML-DSA-65│   │ ML-DSA-65│    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘    │
│                                                                 │
│  Each stage verifies the next using both classical and PQC     │
│  signatures for defense in depth                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Container Image Signing

```dockerfile
# Build quantum-safe container image
FROM amcis/builder:latest as builder

# Sign image with hybrid signature
RUN amcis-container-sign \
    --image $IMAGE_NAME \
    --classical-key /keys/ecdsa.pem \
    --pqc-key /keys/dilithium.pem \
    --output manifest.json

# Verify on deployment
RUN amcis-container-verify \
    --manifest manifest.json \
    --trust-anchor /etc/amcis/trusted-keys.pem
```

### 5.3 Kubernetes Integration

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: quantum-safe-tls-secret
type: kubernetes.io/tls
data:
  # Hybrid certificate with both ECDSA and ML-DSA signatures
  tls.crt: <base64-encoded-hybrid-cert>
  tls.key: <base64-encoded-hybrid-key>
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: quantum-safe-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-pqc: "true"
spec:
  tls:
  - hosts:
    - app.example.com
    secretName: quantum-safe-tls-secret
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        backend:
          service:
            name: app-service
```

---

## 6. Identity and Access Management

### 6.1 Quantum-Safe Authentication

```python
class QuantumSafeAuthentication:
    """
    Multi-factor authentication with PQC resistance
    """
    
    def authenticate(self, credentials: AuthRequest) -> AuthResult:
        """Authenticate user with quantum-safe factors"""
        
        # Factor 1: Password (upgraded to Argon2id)
        password_valid = self.verify_password(
            credentials.username,
            credentials.password
        )
        
        # Factor 2: Hardware token (FIDO2 with PQC)
        fido_result = self.verify_fido2(
            credentials.fido_assertion,
            algorithms=['ES256', 'ML-DSA-65']  # Hybrid
        )
        
        # Factor 3: Biometric (template encrypted with PQC)
        biometric_valid = self.verify_biometric(
            credentials.biometric_data,
            encryption='ML-KEM-768'
        )
        
        if all([password_valid, fido_result.valid, biometric_valid]):
            # Issue quantum-safe session token
            token = self.issue_token(
                subject=credentials.username,
                signing_algorithm='ML-DSA-65',
                encryption_algorithm='ML-KEM-768'
            )
            return AuthResult(success=True, token=token)
        
        return AuthResult(success=False)
```

### 6.2 SSH Key Migration

```bash
#!/bin/bash
# Generate hybrid SSH keypair

# Generate classical Ed25519 key
ssh-keygen -t ed25519 -f ~/.ssh/id_hybrid -C "user@host"

# Generate PQC key (using AMCIS tools)
amcis-ssh-keygen --algorithm ML-DSA-65 --output ~/.ssh/id_hybrid.pqc

# Combine into hybrid key format
cat ~/.ssh/id_hybrid.pub > ~/.ssh/id_hybrid_hybrid.pub
echo "PQC:$(cat ~/.ssh/id_hybrid.pqc.pub)" >> ~/.ssh/id_hybrid_hybrid.pub

# Configure SSH to use hybrid authentication
cat >> ~/.ssh/config << EOF
Host quantum-ready-host
    HostName host.example.com
    IdentityFile ~/.ssh/id_hybrid_hybrid
    PubkeyAcceptedAlgorithms ssh-ed25519,ml-dsa-65
EOF
```

---

## 7. Supply Chain Security

### 7.1 Software Bill of Materials (SBOM) Signing

```python
class QuantumSafeSBOM:
    """
    SBOM generation and signing with PQC
    """
    
    def generate_and_sign_sbom(self, artifact: Artifact) -> SignedSBOM:
        """Generate and sign SBOM with hybrid signatures"""
        
        # Generate SBOM
        sbom = {
            'specVersion': '1.5',
            'serialNumber': f'urn:uuid:{uuid.uuid4()}',
            'components': self.analyze_components(artifact),
            'dependencies': self.analyze_dependencies(artifact),
            'vulnerabilities': self.scan_vulnerabilities(artifact)
        }
        
        # Sign with ECDSA
        ecdsa_sig = self.sign_with_ecdsa(
            json.dumps(sbom, sort_keys=True),
            self.ecdsa_key
        )
        
        # Sign with ML-DSA-65
        pqc_sig = self.sign_with_dilithium(
            json.dumps(sbom, sort_keys=True),
            self.dilithium_key
        )
        
        return SignedSBOM(
            sbom=sbom,
            signatures={
                'ecdsa': ecdsa_sig,
                'ml-dsa-65': pqc_sig
            },
            timestamp=datetime.utcnow().isoformat()
        )
```

### 7.2 Artifact Verification

```yaml
# Supply chain verification policy
supply_chain_policy:
  required_signatures:
    - algorithm: ECDSA
      key_source: https://ca.example.com/ecdsa.pem
    - algorithm: ML-DSA-65
      key_source: https://ca.example.com/dilithium.pem
  
  sbom_requirements:
    format: spdx-json
    signature_required: true
    vulnerability_scan: true
  
  provenance:
    slsa_level: 3
    attestation_required: true
    attestation_signature: ML-DSA-65
```

---

## 8. Migration Roadmap

### 8.1 Phased Migration Strategy

```
Year 1: Assessment & Preparation
├── Q1: Cryptographic inventory
├── Q2: Crypto agility framework implementation
├── Q3: Pilot hybrid deployments
└── Q4: Policy and procedure updates

Year 2: Core Infrastructure
├── Q1: TLS and VPN migration
├── Q2: Certificate authority upgrade
├── Q3: Database encryption migration
└── Q4: Authentication system upgrade

Year 3: Applications & Workloads
├── Q1: Code signing migration
├── Q2: Container and K8s security
├── Q3: Application-level encryption
└── Q4: Supply chain security

Year 4: Retirement & Optimization
├── Q1: Legacy algorithm deprecation
├── Q2: Performance optimization
├── Q3: Full PQC-only mode (optional)
└── Q4: Compliance validation
```

### 8.2 Risk-Based Prioritization

| Priority | Systems | Timeline |
|----------|---------|----------|
| **Critical** | TLS termination, VPN gateways, root CAs | 6 months |
| **High** | Database encryption, backup systems, code signing | 12 months |
| **Medium** | Internal APIs, service mesh, SSH | 18 months |
| **Low** | Static data archives, legacy systems | 24 months |

---

## 9. AMCIS Reference Architecture

### 9.1 Platform Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    AMCIS QUANTUM-READY PLATFORM                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    SECURITY LAYER                          │ │
│  │  • ML-KEM-768 key encapsulation                           │ │
│  │  • ML-DSA-65 digital signatures                           │ │
│  │  • Hybrid TLS 1.3 with X25519Kyber768                     │ │
│  │  • PQC certificate management                             │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    INFRASTRUCTURE LAYER                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │ │
│  │  │   Network   │  │   Compute   │  │   Storage   │       │ │
│  │  │   (PQC VPN) │  │   (Secure   │  │   (PQC Key  │       │ │
│  │  │             │  │    Boot)    │  │    Wrap)    │       │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    COMPLIANCE LAYER                        │ │
│  │  • NIST CSF PQC controls                                  │ │
│  │  • FedRAMP crypto requirements                            │ │
│  │  • CNSA 2.0 compliance                                    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Deployment Configurations

**Configuration 1: Hybrid Mode (Recommended)**
```yaml
crypto_mode: hybrid
algorithms:
  key_exchange: [X25519Kyber768, SecP384r1MLKEM768, X25519]
  signatures: [ECDSA+MLDSA65, MLDSA65, ECDSA]
  encryption: [AES256GCM, AES256GCM_MLKEM768]
```

**Configuration 2: PQC-Preferred**
```yaml
crypto_mode: pqc_preferred
algorithms:
  key_exchange: [MLKEM768, X25519Kyber768, X25519]
  signatures: [MLDSA65, ECDSA+MLDSA65, ECDSA]
  encryption: [AES256GCM_MLKEM768, AES256GCM]
```

**Configuration 3: PQC-Only (Future)**
```yaml
crypto_mode: pqc_only
algorithms:
  key_exchange: [MLKEM768]
  signatures: [MLDSA65]
  encryption: [AES256GCM_MLKEM768]
```

---

## Conclusion

Building quantum-resistant infrastructure is not a future requirement—it is an immediate necessity. Organizations that begin migration now will be positioned for a smooth transition; those that wait will face rushed implementations and potential security gaps.

The AMCIS platform provides a comprehensive foundation for quantum-resistant infrastructure, combining post-quantum cryptography with automated compliance and AI-powered security operations.

Key actions:
1. **Inventory** all cryptographic implementations
2. **Implement** crypto agility frameworks
3. **Deploy** hybrid PQC solutions
4. **Plan** for algorithm retirement
5. **Validate** with compliance frameworks

---

## References

1. NIST SP 800-208: Recommendation for Stateful Hash-Based Signature Schemes
2. CNSA 2.0: Commercial National Security Algorithm Suite 2.0
3. IETF RFC 9191: Kyber Post-Quantum KEM
4. AMCIS Infrastructure Hardening Guide

---

## About AMCIS

AMCIS provides quantum-resistant infrastructure solutions including post-quantum cryptography, automated compliance, and AI-powered security. Learn more at https://amcis.io.

---

*© 2026 AMCIS Security Technologies. All rights reserved.*
