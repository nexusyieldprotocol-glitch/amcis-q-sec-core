# AMCIS Architecture Diagrams
## Complete Technical Documentation Package

**Generated:** 2026-03-14  
**Project:** AMCIS Q-SEC CORE v1.0  
**Classification:** Internal/Commercial

---

## 📁 Contents Overview

This package contains comprehensive architecture diagrams for the AMCIS Q-SEC CORE cybersecurity platform, including:

| Diagram | Format | Description |
|---------|--------|-------------|
| System Architecture | PNG + Mermaid | High-level component overview |
| Deployment Architecture | PNG + Text | Docker Compose deployment layout |
| Security Modules | PNG + Text | All 22 security modules organized |
| Data Flow Pipeline | PNG + Mermaid | End-to-end data processing flow |
| Component Relationships | Text | Detailed dependency mapping |
| Module Structure | Text | Directory/file organization |

---

## 🖼️ Visual Diagrams (PNG Format)

### 1. amcis_system_architecture.png
**Shows:** Complete system stack from user interfaces through security modules to data storage

**Layers Depicted:**
- **User Interfaces:** CLI, REST API, Dashboard, SDK
- **Core Layer:** AMCIS Kernel, Trust Engine, Policy Engine
- **Security Modules:** 22 specialized security modules
- **Data Layer:** PostgreSQL, Redis, Vault, Audit Logs
- **Monitoring:** Prometheus, Grafana, Alerting

**Use Case:** Executive presentations, technical documentation, sales materials

---

### 2. amcis_deployment_architecture.png
**Shows:** Docker Compose deployment with all services and port mappings

**Services:**
- `amcis-core` (ports 8080, 9090)
- `postgres` (port 5432)
- `redis` (port 6379)
- `vault` (port 8200)
- `prometheus` (port 9091)
- `grafana` (port 3000)
- `mailpit` (ports 8025, 8026)

**Network:** amcis-network (172.20.0.0/16)

**Use Case:** DevOps documentation, deployment guides, infrastructure planning

---

### 3. amcis_security_modules.png
**Shows:** All 22 security modules organized by functional category

**Categories:**
- **Core Security:** Crypto, Key Manager, EDR/XDR
- **Network & AI:** Network Security, AI Security, Threat Intel
- **Governance:** Compliance, Secrets Manager, Forensics
- **Operations:** SOAR, Supply Chain, Biometrics
- **Additional:** Cloud Security, Container Security, DLP, Deception, Sandbox, WAF

**Use Case:** Feature documentation, module selection guides, training materials

---

### 4. amcis_data_flow.png
**Shows:** End-to-end data processing pipeline from input to storage

**Pipeline Stages:**
1. **Input:** Security Events, Log Streams, API Calls, User Actions
2. **Ingestion:** Normalize, Enrich, Validate
3. **Processing:** AI Detection, Risk Analysis, Correlation
4. **Response:** Alert, Auto-Remediate, Escalate
5. **Storage:** Encrypt & Store, Audit Trail, Archive

**Use Case:** Security architecture reviews, compliance documentation, DevSecOps

---

## 📝 Text-Based Diagrams

### 5. 01_module_structure.txt
Plain-text tree structure showing the complete directory organization of AMCIS Q-SEC CORE with 22 modules and their purposes.

### 6. 02_system_architecture.mmd
Mermaid.js diagram code for the system architecture. Can be rendered in:
- GitHub/GitLab markdown
- Notion
- Draw.io
- Mermaid Live Editor (https://mermaid.live)

### 7. 03_data_flow.mmd
Mermaid.js diagram code for data flow visualization.

### 8. 04_component_relationships.txt
ASCII-art diagram showing detailed component dependencies and relationships using box-drawing characters.

### 9. 05_deployment_architecture.txt
Text-based deployment diagram with service dependencies, port mappings, and health check endpoints.

---

## 🎯 Quick Reference: Module Purposes

| Module | Purpose | Category |
|--------|---------|----------|
| Crypto | Post-quantum cryptography (NIST FIPS 203/204) | Core |
| Key Manager | Quantum-safe key lifecycle management | Core |
| EDR/XDR | Endpoint detection and response | Core |
| AI Security | LLM prompt firewall, output validation | Advanced |
| Compliance | NIST CSF 2.0, CMMC, FedRAMP automation | Governance |
| Network Security | DNS tunnel detection, microsegmentation | Network |
| Threat Intel | Intelligence aggregation and analysis | Intelligence |
| SOAR | Security orchestration and automation | Operations |
| Supply Chain | SBOM generation, dependency validation | Operations |
| Forensics | Timeline reconstruction and analysis | Operations |

---

## 🚀 How to Use These Diagrams

### For Investors:
- Use `amcis_system_architecture.png` in pitch decks
- Reference the comprehensive module coverage
- Highlight the production-ready Docker deployment

### For Technical Teams:
- Use Mermaid files in documentation (GitHub/GitLab)
- Reference component relationships for integration planning
- Use data flow diagram for security reviews

### For Sales:
- Use security modules diagram to explain features
- Reference deployment architecture for infrastructure discussions
- Use system architecture for executive presentations

### For DevOps:
- Use deployment architecture for infrastructure setup
- Reference port mappings for firewall configuration
- Use health check endpoints for monitoring setup

---

## 🔧 Regenerating Diagrams

### Requirements:
```bash
pip install pillow
```

### Generate PNG diagrams:
```bash
cd ARCHITECTURE_DIAGRAMS
python src/generate_simple_diagrams.py
```

### Generate text diagrams:
```bash
python src/generate_architecture_diagrams.py
```

---

## 📊 Statistics

- **Total Diagrams:** 9 files (4 PNG + 5 text/Mermaid)
- **Python Modules:** 22 security modules
- **Code Files:** 79+ Python files
- **Lines of Code:** 18,000+
- **Docker Services:** 7 containers
- **External Ports:** 8 exposed ports

---

## 📞 Contact

**Technical Questions:** architecture@amcis.local  
**Sales Inquiries:** sales@amcis-security.com  
**Documentation:** https://docs.amcis-security.com

---

*AMCIS Q-SEC CORE - Production-Ready Quantum-Secure Security Framework*  
*Version 1.0 | Generated 2026-03-14*
