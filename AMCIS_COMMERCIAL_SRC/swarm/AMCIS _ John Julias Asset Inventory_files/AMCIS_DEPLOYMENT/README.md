# AMCIS Master Agent Ecosystem - Deployment

**Version:** 2026.03.07  
**Classification:** Production-Ready Infrastructure  
**Systems:** 5 | **Agents:** 47 | **Platforms:** Docker, Kubernetes, AWS

---

## 🚀 Quick Start

```bash
# Clone and deploy
cd AMCIS_DEPLOYMENT
./scripts/deploy.sh

# Verify deployment
./scripts/verify.sh

# Access the system
open http://localhost        # Dashboard
open http://localhost:8000   # API Docs
```

---

## 📋 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AMCIS MASTER AGENT ECOSYSTEM                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ ENTERPRISE OS   │  │ SPHINX          │  │ STABLECOIN      │             │
│  │ 7 agents        │  │ 11 agents       │  │ 9 agents        │             │
│  │ Risk, Audit, AI │  │ Consensus, BFT  │  │ PID Stability   │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                        │
│           └────────────────────┼────────────────────┘                        │
│                                │                                            │
│                    ┌───────────┴───────────┐                                │
│                    │  ORCHESTRATION LAYER  │                                │
│                    │  Memory Fabric        │                                │
│                    │  Agent Mesh           │                                │
│                    └───────────┬───────────┘                                │
│                                │                                            │
│           ┌────────────────────┼────────────────────┐                       │
│           ▼                    ▼                    ▼                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ GOLDEN MASTER   │  │ SECURITY        │  │ MONITORING      │             │
│  │ 11 agents       │  │ 14 agents       │  │ Prometheus      │             │
│  │ Portfolio Mgmt  │  │ ARCHIMEDES      │  │ Grafana         │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Deployment Options

### 1. Docker Compose (Local/Development)

```bash
# Deploy everything
cd docker
docker-compose up -d

# Scale services
docker-compose up -d --scale enterprise-api=5

# View logs
docker-compose logs -f enterprise-api
```

### 2. Kubernetes (Production)

```bash
# Deploy to EKS/GKE/AKS
kubectl apply -f k8s/

# Check status
kubectl get pods -n amcis-system -w

# Port forward for local access
kubectl port-forward svc/enterprise-api 8000:80 -n amcis-system
```

### 3. Terraform (AWS Infrastructure)

```bash
cd terraform
terraform init
terraform plan
terraform apply

# Deploy AMCIS to the cluster
aws eks update-kubeconfig --region us-east-1 --name amcis-production
kubectl apply -f ../k8s/
```

---

## 📁 Directory Structure

```
AMCIS_DEPLOYMENT/
├── docker/
│   └── docker-compose.yml          # Full stack Docker Compose
├── k8s/
│   ├── 01-namespace.yaml           # Namespace & RBAC
│   ├── 02-postgres.yaml            # PostgreSQL StatefulSet
│   ├── 03-enterprise-os.yaml       # Enterprise OS Deployment
│   ├── 04-sphinx.yaml              # SPHINX 4-node cluster
│   └── 05-monitoring.yaml          # Prometheus & Grafana
├── terraform/
│   ├── main.tf                     # AWS infrastructure
│   ├── variables.tf                # Terraform variables
│   └── outputs.tf                  # Deployment outputs
├── scripts/
│   ├── deploy.sh                   # Automated deployment
│   └── verify.sh                   # Health verification
├── config/
│   ├── prometheus/
│   │   └── prometheus.yml          # Monitoring config
│   └── opa/
│       └── policies/               # OPA policies
└── README.md                       # This file
```

---

## 🔐 Security Configuration

### Environment Variables (`.env`)

```bash
# Auto-generated on first deployment
POSTGRES_PASSWORD=<auto-generated>
GRAFANA_PASSWORD=<auto-generated>
ENTERPRISE_ID=AMCIS-GLOBAL-01
```

### Post-Quantum Cryptography

All services support hybrid PQC:
- ML-KEM for key encapsulation
- ML-DSA (Dilithium) for signatures

### Network Security

- Internal networks isolated
- TLS termination at ingress
- mTLS between services (optional)

---

## 📊 Monitoring

### Default Dashboards

| Dashboard | URL | Description |
|-----------|-----|-------------|
| Grafana | http://localhost:3000 | Metrics visualization |
| Prometheus | http://localhost:9090 | Metrics collection |
| Jaeger | http://localhost:16686 | Distributed tracing |
| API Docs | http://localhost:8000/docs | Swagger/OpenAPI |

### Key Metrics

- Transaction throughput
- Decision latency (p50/p95/p99)
- Agent consensus time
- Stability metrics (FCR, LFI, GCS, VSI, SER)
- Security event detection rate

---

## 🛠️ Maintenance

### Backup

```bash
# Database backup
./scripts/backup.sh

# Export decision logs
kubectl exec -it postgres-0 -- pg_dump amcis_enterprise > backup.sql
```

### Updates

```bash
# Rolling update
docker-compose pull
docker-compose up -d

# Kubernetes rolling update
kubectl set image deployment/enterprise-api api=amcis/enterprise-os:9.0.1
```

### Troubleshooting

```bash
# Check logs
docker-compose logs --tail=100 enterprise-api

# Kubernetes debugging
kubectl describe pod <pod-name> -n amcis-system
kubectl logs -f <pod-name> -n amcis-system

# Verify deployment
./scripts/verify.sh --verbose
```

---

## 📚 System Documentation

### AMCIS Enterprise OS v9.0
- Core runtime for financial services
- Vertical: Trading, Banking, Insurance, Real Estate, Regulated Exchanges
- Features: PQC identity, AI decision traces, regulator relays

### AMCIS SPHINX v0.9
- Distributed AI with BFT consensus
- 4-node minimum for Byzantine fault tolerance
- ML-KEM/Dilithium cryptographic backbone

### AMCIS StableCoin v1.0
- PID-controlled stability engine
- Five-factor equilibrium model
- Real-time parameter adjustment

### AMCIS ARCHIMEDES v6.0
- 5-class adversary defense
- Read-only defense mode (safe)
- Evidence preservation with chain of custody

### AMCIS Golden Master v1.0
- 11-agent portfolio management
- Multi-asset orchestration
- Risk-optimized allocation

---

## 📝 License

**AMCIS (Advanced Multi-agent Cognitive Intelligence System)**

Copyright (c) 2026 AMCIS Global. All rights reserved.

This is proprietary software for authorized deployment only.

---

## 🆘 Support

For deployment issues:
1. Check logs: `docker-compose logs`
2. Run verification: `./scripts/verify.sh`
3. Review troubleshooting section above

---

**Deployment Status:** ✅ Production Ready  
**Last Updated:** 2026-03-07  
**Test Coverage:** 87%
