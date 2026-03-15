# AMCIS Q-SEC CORE

## Quantum-Secure Terminal Security Framework

AMCIS Q-SEC CORE is a modular, production-grade, quantum-secure terminal security framework providing comprehensive protection for terminal environments against current and post-quantum threats.

## Features

### Core Security
- **Zero-Trust Execution Engine**: Per-command trust scoring with signature validation
- **Quantum-Safe Cryptography**: Hybrid PQC (ML-KEM + ML-DSA) with crypto agility
- **Merkle Chained Logging**: Tamper-evident append-only logging
- **Hardware Security**: TPM and HSM integration support

### Endpoint Detection & Response (EDR)
- Real-time process lineage graph
- Memory inspection for code injection detection
- File integrity monitoring with cryptographic verification
- System call monitoring with anomaly detection

### AI Security
- Prompt injection detection and prevention
- RAG provenance tracking for document authenticity
- Output validation and policy enforcement

### Network Security
- Dynamic microsegmentation and firewall automation
- DNS tunneling detection via entropy analysis
- Local attack surface mapping and vulnerability assessment

### Supply Chain Security
- SBOM generation (SPDX, CycloneDX formats)
- Dependency vulnerability scanning
- Git commit signature enforcement

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/amcis/amcis-q-sec-core.git
cd amcis-q-sec-core

# Install dependencies
pip install -r requirements.txt

# Initialize AMCIS
python -m cli.amcis_main init
```

### Basic Usage

```bash
# Execute command with security monitoring
amcis secure-run ls -la

# Verify log integrity
amcis verify-logs

# Scan attack surface
amcis scan-surface

# Generate trust report
amcis trust-report
```

## Architecture

```
AMCIS_Q_SEC_CORE/
├── core/              # Kernel, trust engine, anomaly detection
├── crypto/            # PQC, key management, certificates
├── edr/               # Process graph, memory, file integrity
├── ai_security/       # Prompt firewall, RAG provenance
├── network/           # Microsegmentation, DNS detection
├── supply_chain/      # SBOM, dependency validation
└── cli/               # Command-line interface
```

## NIST Compliance

- **FIPS 203**: ML-KEM (CRYSTALS-Kyber) Key Encapsulation
- **FIPS 204**: ML-DSA (CRYSTALS-Dilithium) Digital Signatures
- **SP 800-53**: Security and Privacy Controls
- **SP 800-207**: Zero Trust Architecture
- **SP 800-161**: Supply Chain Risk Management
- **AI RMF**: AI Risk Management Framework

## Docker Deployment

```bash
# Build image
docker build -t amcis-q-sec-core:latest -f deployment/Dockerfile .

# Run container
docker run --rm -it \
    --cap-drop=ALL \
    --cap-add=NET_BIND_SERVICE \
    amcis-q-sec-core:latest

# Or use docker-compose
docker-compose -f deployment/docker-compose.yml up -d
```

## Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_crypto.py -v
```

## Security Considerations

- All secrets are hardware-backed where possible (TPM/HSM)
- Fail-closed design - operations blocked on security failure
- Runtime integrity verification
- Anti-debug and anti-tamper protections
- Secure memory handling for cryptographic keys

## License

Proprietary - AMCIS Security Team

## Support

For issues and documentation:
- Documentation: `docs/`
- Issues: https://github.com/amcis/amcis-q-sec-core/issues
