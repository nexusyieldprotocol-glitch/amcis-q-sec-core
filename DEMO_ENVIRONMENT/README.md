# AMCIS Demo Environment
## Interactive Prospect Demonstration Platform

**Version:** 1.0.0-demo  
**Last Updated:** 2026-03-14  
**Status:** Production Ready

---

## 🚀 Quick Start

### Option 1: Local Docker (Recommended for Testing)

```bash
# Navigate to demo directory
cd DEMO_ENVIRONMENT

# Deploy locally
./deploy.sh local

# Access demo
open http://localhost:8080
```

### Option 2: Render.com (Free Cloud Hosting)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

Or manually:
1. Create account at [render.com](https://render.com)
2. Click "New Web Service"
3. Connect your repository
4. Deploy

### Option 3: Railway (Alternative Cloud)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

---

## 📋 What's Included

### Interactive Demo Features:

| Feature | Description | Module |
|---------|-------------|--------|
| **PQC Key Generation** | Generate ML-KEM-768 quantum-safe keys | Crypto |
| **Message Encryption** | Encrypt with post-quantum algorithms | Crypto |
| **AI Prompt Analysis** | Detect LLM injection attacks | AI Security |
| **Threat Detection** | AI-powered threat identification | EDR/XDR |
| **Compliance Check** | NIST CSF 2.0 compliance validation | Compliance |
| **Port Scanning** | Network security scanning | Network |
| **DNS Tunnel Detection** | Identify data exfiltration attempts | Network |

### Auto-Generated Credentials:

Each demo deployment generates unique credentials:
- **Admin Access:** Full control, expires in 24 hours
- **Read-Only Access:** View-only, expires in 24 hours
- **API Keys:** For programmatic access

---

## 🔐 Security Notes

### Demo Environment Safeguards:

- ✅ **Isolated Environment** - No connection to production
- ✅ **Auto-Expiring Credentials** - 24-hour maximum lifetime
- ✅ **No Persistent Data** - All data reset on restart
- ✅ **Rate Limited** - Prevents abuse
- ✅ **Read-Only File System** - Container security
- ✅ **Non-Root User** - Principle of least privilege

### What Prospects Can Do:

- Generate quantum-safe encryption keys
- Test AI security agent capabilities
- Run compliance checks
- Scan ports and detect threats
- View all dashboard features

### What Prospects CANNOT Do:

- Access real production data
- Modify system configurations
- Execute arbitrary code
- Access underlying infrastructure
- Exceed rate limits

---

## 🌐 Access URLs

After deployment, the demo is accessible at:

| Endpoint | Purpose |
|----------|---------|
| `http://localhost:8080` | Main Dashboard |
| `http://localhost:8080/health` | Health Check |
| `http://localhost:8080/api/demo/credentials` | Get Credentials |
| `http://localhost:8080/api/demo/metrics` | System Metrics |

---

## 📊 Demo Capabilities

### 1. Post-Quantum Cryptography Demo

**What it shows:**
- ML-KEM-768 key generation (NIST FIPS 203)
- Quantum-safe message encryption
- Hybrid classical/post-quantum approaches

**Value proposition:**
- Demonstrates 2-3 year lead over competitors
- Shows NIST compliance readiness
- Proves quantum threat mitigation

### 2. AI Security Agents Demo

**What it shows:**
- Real-time prompt injection detection
- Autonomous threat response
- Multi-agent coordination

**Value proposition:**
- 35+ specialized AI agents
- Memory Fabric knowledge sharing
- Human-in-the-loop escalation

### 3. Compliance Automation Demo

**What it shows:**
- NIST CSF 2.0 control mapping
- Automated compliance scoring
- Report generation

**Value proposition:**
- Reduces audit prep from months to days
- 108 controls automatically checked
- Immutable audit trails

### 4. Network Security Demo

**What it shows:**
- DNS tunnel detection
- Port scanning and service discovery
- Microsegmentation visualization

**Value proposition:**
- Detects sophisticated exfiltration
- Zero-trust network architecture
- OT/IT convergence security

---

## 🛠️ Customization

### Environment Variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AMCIS_DEMO_MODE` | `true` | Enable demo features |
| `DEMO_SESSION_TIMEOUT` | `24h` | Credential expiration |
| `ADMIN_USERNAME` | `demo_admin` | Admin username |
| `ADMIN_PASSWORD` | (random) | Admin password |
| `API_KEY` | (random) | API access key |

### Custom Branding:

Edit `src/demo_app.py` to customize:
- Company logo
- Color scheme
- Feature highlights
- Contact information

---

## 📈 Usage Analytics

The demo tracks (anonymously):
- Feature usage frequency
- Session duration
- Geographic location
- Company size (if provided)

This helps prioritize feature development and sales focus.

---

## 🔄 Updating the Demo

```bash
# Pull latest changes
git pull origin main

# Rebuild and redeploy
docker-compose down
docker-compose up -d --build

# Or for Render: automatic on git push
```

---

## 🆘 Troubleshooting

### Demo Won't Start:

```bash
# Check Docker is running
docker ps

# Check logs
docker-compose logs

# Rebuild clean
docker-compose down -v
docker-compose up -d --build
```

### Credentials Not Working:

- Credentials expire after 24 hours
- Check `credentials/` folder for new credentials
- Restart demo to generate fresh credentials

### Port Already in Use:

```bash
# Find process using port 8080
lsof -i :8080

# Kill it or change port in docker-compose.yml
```

---

## 📞 Support

**Technical Issues:** demo-support@amcis.local  
**Sales Inquiries:** sales@amcis-security.com  
**Documentation:** https://docs.amcis-security.com/demo

---

## 📄 License

This demo is provided for evaluation purposes only.  
Full licensing terms apply for production use.

---

*AMCIS Q-SEC CORE - Quantum-Secure Cybersecurity Platform*  
*© 2026 Global Compliance Agency / AMCIS*
