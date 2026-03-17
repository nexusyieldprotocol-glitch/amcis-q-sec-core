# AMCIS Administrator Handbook
## Complete Guide for System Administrators

**Version:** 1.0.0  
**Audience:** System Administrators, DevOps Engineers, Security Engineers

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Installation & Deployment](#installation--deployment)
3. [Configuration Management](#configuration-management)
4. [User Management](#user-management)
5. [Security Policies](#security-policies)
6. [Monitoring & Alerting](#monitoring--alerting)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance Tasks](#maintenance-tasks)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        LOAD BALANCER                         │
│                     (NGINX/HAProxy/ALB)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──────┐┌────▼──────┐┌────▼──────┐
│ AMCIS API    ││ AMCIS API ││ AMCIS API │
│ Instance 1   ││ Instance 2││ Instance 3│
└───────┬──────┘└────┬──────┘└────┬──────┘
        │            │            │
        └────────────┼────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼────┐    ┌────▼────┐    ┌─────▼────┐
│PostgreSQL│    │  Redis   │    │   Vault   │
│  (HA)   │    │ (Cluster)│    │   (HA)    │
└─────────┘    └─────────┘    └───────────┘
```

### Data Flow

1. **Ingestion Layer:** Security events → Normalization → Enrichment
2. **Processing Layer:** AI Detection → Risk Scoring → Correlation
3. **Storage Layer:** PostgreSQL (structured) + Redis (cache) + Vault (secrets)
4. **Presentation Layer:** API → Dashboard → Alerts

---

## Installation & Deployment

### Production Deployment Checklist

- [ ] Provision infrastructure (CPU/RAM/Disk)
- [ ] Configure network security groups
- [ ] Set up DNS records
- [ ] Install Docker & Docker Compose
- [ ] Configure TLS certificates
- [ ] Set up monitoring stack
- [ ] Configure backup storage
- [ ] Deploy AMCIS stack
- [ ] Run smoke tests
- [ ] Configure alerting

### Docker Compose Production

```yaml
version: "3.8"

services:
  amcis-api:
    image: amcis/amcis-q-sec-core:v1.0.0
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    environment:
      - AMCIS_ENV=production
      - DATABASE_URL=postgresql://amcis:${DB_PASS}@postgres:5432/amcis
      - REDIS_URL=redis://redis:6379/0
      - VAULT_ADDR=https://vault:8200
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: amcis-api
  namespace: amcis-production
spec:
  replicas: 5
  strategy:
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: amcis
        image: amcis/amcis-q-sec-core:v1.0.0
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## Configuration Management

### Configuration Files

| File | Purpose | Reload Method |
|------|---------|---------------|
| `config/amcis.yaml` | Core settings | API call |
| `config/auth.yaml` | Authentication | Restart |
| `config/crypto.yaml` | Cryptography | API call |
| `config/alerts.yaml` | Alerting rules | API call |
| `config/compliance.yaml` | Compliance | API call |

### Environment Variables

```bash
# Required
export AMCIS_ENV=production
export DATABASE_URL=postgresql://...
export REDIS_URL=redis://...
export VAULT_ADDR=https://...

# Optional
export AMCIS_LOG_LEVEL=INFO
export AMCIS_WORKERS=4
export AMCIS_TIMEOUT=30
```

### Secret Management

```bash
# Store secret in Vault
vault kv put secret/amcis/api-key \
  value="sk-amcis-12345"

# Retrieve in application
vault kv get -field=value secret/amcis/api-key
```

---

## User Management

### Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| **Super Admin** | Full system access |
| **Admin** | Manage users, policies, reports |
| **Analyst** | View data, create reports |
| **Operator** | Run scans, view alerts |
| **Read-Only** | View-only access |

### Creating Users

```bash
# Create user with role
python scripts/create_user.py \
  --username jane.doe \
  --email jane@company.com \
  --role analyst \
  --mfa-required true

# Bulk user creation
python scripts/bulk_import_users.py users.csv
```

### API Key Management

```bash
# Generate API key
python scripts/generate_api_key.py \
  --user-id jane.doe \
  --role analyst \
  --expiry 90d

# Revoke API key
python scripts/revoke_api_key.py \
  --key-id key-abc123
```

---

## Security Policies

### Default Security Policies

```yaml
# config/security.yaml
password_policy:
  min_length: 12
  require_uppercase: true
  require_lowercase: true
  require_numbers: true
  require_special: true
  expiry_days: 90
  history_count: 5

session_policy:
  timeout_minutes: 30
  max_concurrent: 3
  require_mfa: true
  ip_restriction: []

api_policy:
  rate_limit: 1000  # requests per hour
  burst_limit: 100
  require_https: true
```

### Network Security

```yaml
# Firewall rules
allowed_cidr:
  - 10.0.0.0/8
  - 172.16.0.0/12
  - 192.168.0.0/16

denied_cidr:
  - 0.0.0.0/0  # Default deny all

port_rules:
  - port: 8080
    protocol: tcp
    source: internal
  - port: 5432
    protocol: tcp
    source: internal
```

---

## Monitoring & Alerting

### Key Metrics

| Metric | Warning | Critical |
|--------|---------|----------|
| CPU Usage | >70% | >90% |
| Memory Usage | >80% | >95% |
| Disk Usage | >80% | >90% |
| API Latency (p99) | >100ms | >500ms |
| Error Rate | >1% | >5% |
| Queue Depth | >1000 | >5000 |

### Alert Configuration

```yaml
alerts:
  - name: high_cpu
    condition: cpu_usage > 90%
    duration: 5m
    severity: critical
    channels:
      - pagerduty
      - slack
      - email

  - name: api_errors
    condition: error_rate > 5%
    duration: 2m
    severity: critical
    channels:
      - pagerduty
      - slack
```

---

## Backup & Recovery

### Backup Strategy

| Type | Frequency | Retention |
|------|-----------|-----------|
| Database Full | Daily | 30 days |
| Database Incremental | Hourly | 7 days |
| Configuration | On change | 90 days |
| Logs | Continuous | 90 days |

### Backup Commands

```bash
# Manual backup
python scripts/backup.py --full --destination s3://amcis-backups/

# Scheduled backup (cron)
0 2 * * * /opt/amcis/scripts/backup.py --full
0 * * * * /opt/amcis/scripts/backup.py --incremental

# Verify backup
python scripts/verify_backup.py --backup-id backup-20260317
```

### Recovery Procedures

```bash
# Full system recovery
python scripts/restore.py \
  --backup-id backup-20260317 \
  --target-environment production

# Point-in-time recovery
python scripts/restore.py \
  --timestamp "2026-03-17 14:30:00" \
  --database-only
```

---

## Troubleshooting

### Common Issues

#### High Memory Usage
```bash
# Check memory usage
python scripts/diagnostics.py --check memory

# Restart services
docker-compose restart amcis-api

# Scale horizontally
docker-compose up -d --scale amcis-api=5
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready

# View connection count
docker-compose exec postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Restart database (careful!)
docker-compose restart postgres
```

#### Slow API Response
```bash
# Check query performance
python scripts/analyze_queries.py --slow-threshold 100ms

# Clear Redis cache
redis-cli FLUSHDB

# Restart API with more workers
AMCIS_WORKERS=8 docker-compose up -d amcis-api
```

---

## Maintenance Tasks

### Daily
- [ ] Check system health dashboard
- [ ] Review critical alerts
- [ ] Verify backup completion
- [ ] Check disk space

### Weekly
- [ ] Review security logs
- [ ] Update threat intelligence feeds
- [ ] Run compliance checks
- [ ] Update documentation

### Monthly
- [ ] Performance review
- [ ] Security patch review
- [ ] Capacity planning
- [ ] Disaster recovery test

### Quarterly
- [ ] Full security audit
- [ ] Penetration testing
- [ ] Compliance certification review
- [ ] Architecture review

---

## Support Contacts

| Issue Type | Contact | SLA |
|------------|---------|-----|
| Critical (System Down) | +1 (555) AMCIS-911 | 15 min |
| High (Major Feature Broken) | priority@amcis-security.com | 2 hours |
| Medium (Minor Issues) | support@amcis-security.com | 24 hours |
| Low (Questions) | community@amcis-security.com | 48 hours |

---

**Document Control:**
- Version: 1.0.0
- Last Reviewed: 2026-03-17
- Next Review: 2026-06-17
- Owner: AMCIS Customer Success Team
