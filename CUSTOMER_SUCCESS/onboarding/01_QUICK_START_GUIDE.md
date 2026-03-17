# AMCIS Q-SEC CORE - Quick Start Guide
## Get Up and Running in 15 Minutes

**Version:** 1.0.0  
**Last Updated:** 2026-03-17  
**Audience:** New Customers & Administrators

---

## 🚀 5-Minute Quick Start

### Step 1: Download and Extract

```bash
# Download AMCIS package
wget https://amcis-security.com/releases/amcis-q-sec-core-v1.0.0.zip

# Extract
unzip amcis-q-sec-core-v1.0.0.zip
cd amcis-q-sec-core/
```

### Step 2: Run with Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Verify installation
curl http://localhost:8080/health
```

**Expected Output:**
```json
{"status": "healthy", "version": "1.0.0"}
```

### Step 3: Access Dashboard

Open your browser: **http://localhost:8080**

Default credentials:
- Username: `admin`
- Password: (auto-generated, check `logs/setup.log`)

---

## 📋 System Requirements

### Minimum Requirements
- **CPU:** 4 cores
- **RAM:** 8 GB
- **Storage:** 50 GB SSD
- **OS:** Linux (Ubuntu 22.04+), Windows Server 2019+, macOS 13+

### Recommended Production
- **CPU:** 8+ cores
- **RAM:** 16+ GB
- **Storage:** 100+ GB SSD
- **Network:** 1 Gbps

### Supported Browsers
- Chrome 110+
- Firefox 110+
- Safari 16+
- Edge 110+

---

## 🔧 Installation Options

### Option A: Docker Compose (Easiest)

```bash
# Clone repository
git clone https://github.com/nexusyieldprotocol-glitch/amcis-q-sec-core.git
cd amcis-q-sec-core

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### Option B: Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/vault.yaml
kubectl apply -f k8s/amcis-core.yaml

# Verify
kubectl get pods -n amcis
```

### Option C: Native Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies (for dashboard)
cd dashboard && npm install

# Initialize database
python scripts/init_db.py

# Start services
python -m amcis_core.server
```

---

## ⚙️ Initial Configuration

### 1. Configure API Keys

```bash
# Generate admin API key
python scripts/generate_api_key.py --role admin --name "Initial Admin"

# Save the key securely
```

### 2. Set Up Authentication

Edit `config/auth.yaml`:
```yaml
authentication:
  jwt_secret: "your-secure-secret-here"
  token_expiry: 3600  # 1 hour
  refresh_token_expiry: 86400  # 24 hours
  
  oauth2:
    enabled: true
    providers:
      - google
      - github
      - azure_ad
```

### 3. Configure Email Notifications

Edit `config/notifications.yaml`:
```yaml
email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  username: ${SMTP_USER}
  password: ${SMTP_PASS}
  from_address: alerts@yourcompany.com
  
alerts:
  critical:
    - email
    - slack
    - pagerduty
  high:
    - email
    - slack
  medium:
    - email
```

### 4. Set Up Backups

```bash
# Configure backup schedule
python scripts/setup_backups.py \
  --s3-bucket your-backup-bucket \
  --schedule "0 2 * * *"  # Daily at 2 AM
```

---

## 🎯 First Tasks

### Task 1: Verify Installation (2 minutes)

```bash
# Run health checks
./scripts/health-check.sh

# Run diagnostic
python scripts/diagnose.py
```

### Task 2: Create First User (2 minutes)

```bash
# Create admin user
python scripts/create_user.py \
  --username john.doe \
  --email john@company.com \
  --role admin
```

### Task 3: Test Cryptography (3 minutes)

```python
# Test PQC encryption
from amcis import CryptoEngine

engine = CryptoEngine()
key = engine.generate_key(algorithm="ML-KEM-768")

plaintext = "Test message"
ciphertext = engine.encrypt(plaintext, key)

decrypted = engine.decrypt(ciphertext, key)
assert decrypted == plaintext
print("✓ Cryptography working")
```

### Task 4: Run First Compliance Check (3 minutes)

```bash
# Run NIST CSF assessment
python scripts/compliance_check.py --framework NIST-CSF-2.0

# View results
cat reports/compliance_nist_csf_$(date +%Y%m%d).json
```

### Task 5: Configure First Alert (5 minutes)

1. Go to Dashboard → Alerts → Rules
2. Click "Create Rule"
3. Select "High Severity Threat"
4. Set action: "Send Email + Slack"
5. Test with sample event

---

## 🧪 Testing Your Setup

### Run Integration Tests

```bash
# Run full test suite
pytest tests/integration/ -v

# Run security tests
pytest tests/security/ -v

# Run performance tests
pytest tests/performance/ -v
```

### Verify All Services

| Service | Check Command | Expected Result |
|---------|---------------|-----------------|
| API | `curl localhost:8080/health` | `{"status":"healthy"}` |
| Database | `pg_isready -h localhost` | `accepting connections` |
| Redis | `redis-cli ping` | `PONG` |
| Vault | `vault status` | `Sealed: false` |

---

## 🛠️ Troubleshooting

### Issue: Port 8080 already in use

```bash
# Find process using port
lsof -i :8080

# Kill process or change port
# Edit docker-compose.yml, change "8080:8080" to "8081:8080"
```

### Issue: Database connection failed

```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
python scripts/init_db.py
```

### Issue: Vault not initializing

```bash
# Check Vault logs
docker-compose logs vault

# Manually unseal
export VAULT_ADDR=http://localhost:8200
vault operator unseal <unseal-key>
```

### Issue: Low disk space

```bash
# Clean up Docker
docker system prune -a

# Clean up logs
python scripts/rotate_logs.py --keep-days 7
```

---

## 📚 Next Steps

### Immediate (Today)
- [ ] Complete initial configuration
- [ ] Create admin users
- [ ] Set up alerting
- [ ] Run first compliance check

### Short-term (This Week)
- [ ] Configure SSO integration
- [ ] Set up backup schedules
- [ ] Import existing security policies
- [ ] Train team members

### Long-term (This Month)
- [ ] Full security audit
- [ ] Performance tuning
- [ ] Disaster recovery testing
- [ ] Compliance certification

---

## 📞 Support Resources

- **Documentation:** https://docs.amcis-security.com
- **Support Portal:** https://support.amcis-security.com
- **Community Forum:** https://community.amcis-security.com
- **Email:** support@amcis-security.com
- **Phone:** +1 (555) AMCIS-HELP

---

## ✅ Quick Reference Card

```
Start:     docker-compose up -d
Stop:      docker-compose down
Logs:      docker-compose logs -f
Update:    docker-compose pull && docker-compose up -d
Backup:    python scripts/backup.py
Restore:   python scripts/restore.py <backup-file>
Health:    curl localhost:8080/health
```

---

**Welcome to AMCIS! Your quantum-secure cybersecurity journey starts now.** 🚀
