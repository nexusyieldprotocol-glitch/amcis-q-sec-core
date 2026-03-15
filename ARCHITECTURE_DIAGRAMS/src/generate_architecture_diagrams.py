"""
AMCIS Architecture Diagram Generator
Generates system architecture, data flow, and component diagrams
"""

import os
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "AMCIS_Q_SEC_CORE"))

def generate_module_structure():
    """Generate text-based module structure diagram"""
    
    structure = """
# AMCIS Q-SEC CORE - Module Structure
# =====================================

amcis_q_sec_core/
│
├── core/                          [FOUNDATION LAYER]
│   ├── amcis_kernel.py           - Central security orchestrator
│   ├── amcis_trust_engine.py     - Trust scoring & verification
│   └── ...
│
├── crypto/                        [CRYPTOGRAPHY LAYER]
│   ├── amcis_key_manager.py      - Quantum-safe key management
│   ├── amcis_merkle_log.py       - Immutable audit logging
│   └── ...
│
├── network/                       [NETWORK SECURITY LAYER]
│   ├── amcis_dns_tunnel_detector.py
│   ├── amcis_microsegmentation.py
│   └── amcis_port_surface_mapper.py
│
├── ai_security/                   [AI SECURITY LAYER]
│   ├── amcis_prompt_firewall.py  - LLM injection protection
│   ├── amcis_output_validator.py - AI output validation
│   └── amcis_rag_provenance.py   - RAG tracking
│
├── compliance/                    [COMPLIANCE LAYER]
│   ├── nist_csf.py               - NIST CSF 2.0 automation
│   ├── compliance_engine.py
│   └── report_generator.py
│
├── edr/                           [ENDPOINT SECURITY LAYER]
│   └── Endpoint Detection & Response
│
├── threat_intel/                  [THREAT INTELLIGENCE LAYER]
│   └── Threat intelligence aggregation
│
├── secrets_mgr/                   [SECRETS MANAGEMENT LAYER]
│   └── Vault integration & secret rotation
│
├── forensics/                     [FORENSICS LAYER]
│   └── Timeline reconstruction
│
├── soar/                          [AUTOMATION LAYER]
│   └── Security orchestration
│
├── supply_chain/                  [SUPPLY CHAIN LAYER]
│   ├── amcis_sbom_generator.py
│   └── amcis_dependency_validator.py
│
└── tests/                         [TEST LAYER]
    └── Comprehensive test suites

"""
    return structure


def generate_system_architecture_mermaid():
    """Generate Mermaid diagram for system architecture"""
    
    mermaid = """
```mermaid
graph TB
    subgraph "User Layer"
        CLI[CLI Interface]
        API[REST API]
        DASH[Dashboard]
    end
    
    subgraph "Core Layer"
        KERNEL[AMCIS Kernel]
        TRUST[Trust Engine]
        POLICY[Policy Engine]
    end
    
    subgraph "Security Modules"
        CRYPTO[Crypto Module]
        EDR[EDR/XDR]
        NET[Network Security]
        AI[AI Security]
        COMP[Compliance]
        THREAT[Threat Intel]
        SECRETS[Secrets Mgr]
        FORENSICS[Forensics]
        SOAR[SOAR]
        SC[Supply Chain]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL)]
        CACHE[(Redis)]
        VAULT[(HashiCorp Vault)]
        LOG[(Audit Logs)]
    end
    
    CLI --> KERNEL
    API --> KERNEL
    DASH --> KERNEL
    
    KERNEL --> TRUST
    KERNEL --> POLICY
    
    KERNEL --> CRYPTO
    KERNEL --> EDR
    KERNEL --> NET
    KERNEL --> AI
    KERNEL --> COMP
    KERNEL --> THREAT
    KERNEL --> SECRETS
    KERNEL --> FORENSICS
    KERNEL --> SOAR
    KERNEL --> SC
    
    CRYPTO --> VAULT
    EDR --> DB
    NET --> DB
    AI --> DB
    COMP --> DB
    THREAT --> CACHE
    SECRETS --> VAULT
    FORENSICS --> DB
    SOAR --> DB
    SC --> DB
    
    KERNEL --> LOG
```
"""
    return mermaid


def generate_data_flow_mermaid():
    """Generate data flow diagram"""
    
    mermaid = """
```mermaid
flowchart LR
    subgraph "Input"
        EVENTS[Security Events]
        LOGS[Log Streams]
        API[API Calls]
        USER[User Actions]
    end
    
    subgraph "Ingestion"
        NORMALIZE[Telemetry Normalization]
        ENRICH[Data Enrichment]
        VALIDATE[Input Validation]
    end
    
    subgraph "Processing"
        DETECT[Threat Detection AI]
        ANALYZE[Risk Analysis]
        CORRELATE[Event Correlation]
    end
    
    subgraph "Response"
        ALERT[Alert Generation]
        AUTO[Auto-Remediation]
        ESCALATE[Human Escalation]
    end
    
    subgraph "Storage"
        ENCRYPT[Encrypt & Store]
        AUDIT[Audit Trail]
        ARCHIVE[Long-term Archive]
    end
    
    EVENTS --> NORMALIZE
    LOGS --> NORMALIZE
    API --> VALIDATE
    USER --> VALIDATE
    
    NORMALIZE --> ENRICH
    VALIDATE --> ENRICH
    
    ENRICH --> DETECT
    DETECT --> ANALYZE
    ANALYZE --> CORRELATE
    
    CORRELATE --> ALERT
    CORRELATE --> AUTO
    CORRELATE --> ESCALATE
    
    ALERT --> ENCRYPT
    AUTO --> AUDIT
    ESCALATE --> AUDIT
    
    ENCRYPT --> ARCHIVE
    AUDIT --> ARCHIVE
```
"""
    return mermaid


def generate_component_relationships():
    """Generate component relationship text diagram"""
    
    diagram = """
# AMCIS Component Relationships
# =============================

## Core Dependencies

┌─────────────────────────────────────────────────────────────────────┐
│                        AMCIS KERNEL                                 │
│                    (Central Orchestrator)                           │
└────────────┬───────────────────────────────┬────────────────────────┘
             │                               │
    ┌────────▼────────┐              ┌───────▼────────┐
    │  Trust Engine   │              │ Policy Engine  │
    │  (Scoring)      │              │ (Rules)        │
    └────────┬────────┘              └───────┬────────┘
             │                               │
             └───────────────┬───────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐        ┌──────▼──────┐      ┌────▼─────┐
   │ Crypto  │        │ Compliance  │      │  EDR     │
   │ Module  │        │   Engine    │      │  Module  │
   └────┬────┘        └──────┬──────┘      └────┬─────┘
        │                    │                   │
        │            ┌───────▼──────┐          │
        │            │ NIST CSF 2.0 │          │
        │            │  Automation  │          │
        │            └──────────────┘          │
        │                                      │
   ┌────▼──────────────────────────────────────▼─────┐
   │           HashiCorp Vault                       │
   │    (Secrets, Keys, Certificates)                │
   └─────────────────────────────────────────────────┘

## AI Agent Ecosystem

┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                           │
│                   (Task Routing & Control)                      │
└──────────────┬──────────────────────────────────┬───────────────┘
               │                                  │
    ┌──────────▼──────────┐            ┌──────────▼──────────┐
    │  Detection Agents   │            │  Response Agents    │
    │  - Threat Detect    │            │  - SOAR Playbook    │
    │  - Telemetry Norm   │            │  - Forensics        │
    │  - Red Team         │            │  - Incident Command │
    └──────────┬──────────┘            └──────────┬──────────┘
               │                                  │
               └──────────────┬───────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   MEMORY FABRIC   │
                    │ (Shared Knowledge)│
                    └───────────────────┘

## Data Storage Architecture

┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL                                  │
│           (Structured Data & Config)                            │
├─────────────────────────────────────────────────────────────────┤
│  • Security Events          • User Data                         │
│  • Compliance Records       • Policy Config                     │
│  • Audit Logs               • Asset Inventory                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │  Redis  │          │  Vault  │          │ S3/MinIO│
   │ (Cache) │          │(Secrets)│          │(Archive)│
   └─────────┘          └─────────┘          └─────────┘

"""
    return diagram


def generate_deployment_architecture():
    """Generate deployment architecture diagram"""
    
    diagram = """
# AMCIS Deployment Architecture
# =============================

## Docker Compose Stack

┌─────────────────────────────────────────────────────────────────────────┐
│                           DOCKER NETWORK                                  │
│                        (amcis-network: 172.20.0.0/16)                    │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐
│  amcis-core     │  │   postgres      │  │     redis       │  │    vault    │
│  (Main App)     │  │  (Database)     │  │   (Cache)       │  │   (Secrets) │
│                 │  │                 │  │                 │  │             │
│  Port: 8080     │  │  Port: 5432     │  │  Port: 6379     │  │ Port: 8200  │
│  Port: 9090     │  │                 │  │                 │  │             │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘
         │                    │                    │                  │
         └────────────────────┴────────────────────┴──────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                              │
           ┌────────▼────────┐            ┌────────▼────────┐
           │   prometheus    │            │    grafana      │
           │  (Metrics)      │            │  (Dashboards)   │
           │  Port: 9091     │            │  Port: 3000     │
           └─────────────────┘            └─────────────────┘

## Service Dependencies

    amcis-core
         │
    ┌────┴────┬──────────┐
    │         │          │
    ▼         ▼          ▼
postgres   redis      vault
    │         │          │
    └────┬────┘          │
         │               │
         ▼               ▼
    prometheus      grafana

## Port Mapping

┌────────────────┬──────────────┬─────────────────────────────┐
│ Service        │ Internal Port│ External Port               │
├────────────────┼──────────────┼─────────────────────────────┤
│ amcis-core     │ 8080, 9090   │ 8080 (API), 9090 (Metrics)  │
│ postgres       │ 5432         │ 5432 (Database)             │
│ redis          │ 6379         │ 6379 (Cache)                │
│ vault          │ 8200         │ 8200 (Secrets UI)           │
│ prometheus     │ 9090         │ 9091 (Monitoring)           │
│ grafana        │ 3000         │ 3000 (Dashboards)           │
│ mailpit        │ 8025, 8026   │ 8025 (SMTP), 8026 (Web UI)  │
└────────────────┴──────────────┴─────────────────────────────┘

## Health Check Endpoints

┌─────────────────────────────────────────────────────────────────┐
│  Service        │ Health Endpoint                               │
├─────────────────────────────────────────────────────────────────┤
│  amcis-core     │ http://localhost:8080/health/live             │
│                 │ http://localhost:8080/health/ready            │
│  postgres       │ pg_isready -U amcis -d amcis                  │
│  redis          │ redis-cli ping                                │
│  vault          │ vault status                                  │
│  prometheus     │ http://localhost:9091/-/healthy               │
│  grafana        │ http://localhost:3000/api/health              │
└─────────────────────────────────────────────────────────────────┘

"""
    return diagram


def main():
    """Generate all architecture diagrams"""
    
    output_dir = Path(__file__).parent.parent
    
    # Generate all diagrams
    diagrams = {
        "01_module_structure.txt": generate_module_structure(),
        "02_system_architecture.mmd": generate_system_architecture_mermaid(),
        "03_data_flow.mmd": generate_data_flow_mermaid(),
        "04_component_relationships.txt": generate_component_relationships(),
        "05_deployment_architecture.txt": generate_deployment_architecture(),
    }
    
    # Write all files
    for filename, content in diagrams.items():
        filepath = output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Generated: {filepath}")
    
    print(f"\n✅ Generated {len(diagrams)} architecture diagrams in: {output_dir}")
    return list(diagrams.keys())


if __name__ == "__main__":
    main()
