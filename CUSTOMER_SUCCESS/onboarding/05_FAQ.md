# AMCIS Frequently Asked Questions (FAQ)

**Last Updated:** 2026-03-17  
**Version:** 1.0.0

---

## 🚀 Getting Started

### Q: What is AMCIS?
**A:** AMCIS (Adaptive Multi-Context Intelligent Security) is a production-grade, quantum-secure cybersecurity platform featuring 22 integrated security modules, post-quantum cryptography, AI-powered threat detection, and automated compliance.

### Q: How long does installation take?
**A:** 
- Docker Compose: 15 minutes
- Kubernetes: 30-60 minutes
- Native installation: 1-2 hours

### Q: What are the system requirements?
**A:**
- **Minimum:** 4 CPU cores, 8GB RAM, 50GB storage
- **Recommended:** 8+ CPU cores, 16GB RAM, 100GB SSD storage
- **OS:** Linux (Ubuntu 22.04+), Windows Server 2019+, macOS 13+

### Q: Do you offer a free trial?
**A:** Yes! We offer:
- 30-day free trial with full features
- Interactive demo environment
- Sandbox for testing

---

## 💰 Pricing & Licensing

### Q: How much does AMCIS cost?
**A:** We offer multiple tiers:
- **Bronze:** $499 (Personal/Educational)
- **Silver:** $2,499 (Commercial, 1 developer)
- **Gold:** $9,999 (Enterprise, 10 developers)
- **Sapphire/Empire:** $199,999 (Full IP transfer)

### Q: What's included in each tier?
**A:** See our detailed comparison:
- Bronze: 5 modules, personal use
- Silver: 12 modules, commercial use
- Gold: All 22 modules, enterprise features
- Empire: Full IP ownership

### Q: Can I upgrade later?
**A:** Yes! Your purchase price counts toward higher tiers. Upgrade anytime by paying the difference.

### Q: Is there a payment plan?
**A:** Yes, for Gold tier and above:
- Gold: 3 payments of $3,499
- Empire: Custom payment schedule available

### Q: What's your refund policy?
**A:**
- Bronze/Silver: 30-day money-back guarantee
- Gold: 60-day money-back guarantee
- Empire: Case-by-case basis

---

## 🔒 Security & Compliance

### Q: Is AMCIS really quantum-safe?
**A:** Yes! AMCIS implements NIST-approved post-quantum algorithms:
- ML-KEM for key encapsulation
- ML-DSA for digital signatures
- AES-256-GCM for symmetric encryption

### Q: What compliance frameworks do you support?
**A:** We support:
- NIST CSF 2.0
- CMMC 2.0
- FedRAMP
- PCI-DSS 4.0
- HIPAA
- SOC 2
- ISO 27001
- NERC CIP

### Q: Has AMCIS been penetration tested?
**A:** Yes! We conduct:
- Quarterly internal penetration tests
- Annual third-party assessments
- Continuous vulnerability scanning
- Bug bounty program

### Q: Where is my data stored?
**A:** You control your data:
- Self-hosted deployment
- Your choice of cloud provider
- Bring your own database
- Data never leaves your infrastructure

### Q: Do you have access to my data?
**A:** No! AMCIS is self-hosted. We have zero access to your:
- Security data
- API keys
- Customer information
- System configurations

---

## ⚙️ Technical Questions

### Q: What programming languages do you support?
**A:** AMCIS is written in Python, but we provide SDKs for:
- Python
- JavaScript/Node.js
- Go
- Rust
- Java

### Q: Can I integrate AMCIS with my existing tools?
**A:** Yes! We offer integrations with:
- SIEM: Splunk, ELK, QRadar
- SOAR: Phantom, XSOAR
- Ticketing: ServiceNow, Jira
- Cloud: AWS, Azure, GCP
- IDP: Okta, Azure AD, Auth0

### Q: How do I update AMCIS?
**A:** Updates are simple:
```bash
# Docker Compose
docker-compose pull
docker-compose up -d

# Kubernetes
kubectl set image deployment/amcis amcis=amcis/amcis:v1.1.0
```

### Q: What databases do you support?
**A:** We support:
- PostgreSQL (primary)
- MySQL
- SQLite (development only)
- Amazon RDS
- Google Cloud SQL
- Azure Database

### Q: Can I customize the code?
**A:** 
- Silver+: Full source code access
- Modify as needed
- Build custom features
- Contribute back (optional)

---

## 🛠️ Troubleshooting

### Q: AMCIS won't start. What should I do?
**A:**
1. Check logs: `docker-compose logs`
2. Verify ports are available
3. Check disk space: `df -h`
4. Try restart: `docker-compose restart`

### Q: I'm getting "Connection refused" errors
**A:**
1. Verify services are running: `docker-compose ps`
2. Check firewall rules
3. Verify network connectivity
4. Check service health: `curl localhost:8080/health`

### Q: Performance is slow. How can I improve it?
**A:**
1. Scale horizontally: `docker-compose up -d --scale amcis-api=5`
2. Enable caching
3. Optimize database queries
4. Upgrade hardware

### Q: How do I reset my admin password?
**A:**
```bash
python scripts/reset_password.py --username admin
```

### Q: Where are the logs located?
**A:**
- Docker: `docker-compose logs`
- File: `/var/log/amcis/`
- Structured: JSON format

---

## 📞 Support

### Q: How do I get support?
**A:**
- Documentation: https://docs.amcis-security.com
- Community Forum: https://community.amcis-security.com
- Email: support@amcis-security.com
- Phone: +1 (555) AMCIS-HELP

### Q: What are your support hours?
**A:**
- Bronze: Community support (24/7)
- Silver: Email support (business hours)
- Gold: Priority support (24/7)
- Empire: Dedicated support manager

### Q: Do you offer professional services?
**A:** Yes!
- Implementation services
- Custom development
- Training & certification
- Managed security services

### Q: Can you help with deployment?
**A:** Absolutely! We offer:
- Remote deployment assistance
- Architecture reviews
- Performance tuning
- Migration support

---

## 🏢 Enterprise & Custom

### Q: Do you offer custom development?
**A:** Yes, for Gold and Empire tiers:
- Custom features
- White-label solutions
- Specialized integrations

### Q: Can AMCIS be white-labeled?
**A:** Yes, Empire tier includes:
- Full white-label rights
- Custom branding
- Your own product name

### Q: Do you offer training?
**A:** Yes!
- Online video courses
- Live instructor-led training
- Certification programs
- Custom workshops

### Q: Can I become a reseller/partner?
**A:** Yes! We have:
- Reseller program
- Referral program
- MSP partnership
- Technology partnership

---

## 🔮 Roadmap & Future

### Q: What's on your roadmap?
**A:** Coming soon:
- Additional PQC algorithms
- More AI models
- Extended compliance frameworks
- Mobile app
- Enhanced dashboard

### Q: How often do you release updates?
**A:**
- Security patches: As needed
- Feature releases: Monthly
- Major versions: Quarterly

### Q: Is AMCIS open source?
**A:** Partially:
- Core: Commercial license
- Some components: Open source
- SDKs: Open source
- Documentation: Open source

### Q: Can I contribute to AMCIS?
**A:** Yes! We welcome:
- Bug reports
- Feature requests
- Documentation improvements
- Code contributions (SDKs)

---

## 🎓 Learning & Resources

### Q: Where can I learn more?
**A:** Check out:
- Documentation portal
- YouTube channel
- Blog
- Webinars
- Case studies

### Q: Do you offer certification?
**A:** Yes! AMCIS Certified Professional:
- Online exam
- Valid for 2 years
- Industry recognized
- Multiple levels available

### Q: Are there example projects?
**A:** Yes! We provide:
- Sample implementations
- Integration examples
- Code samples
- Demo applications

---

## 📋 Still Have Questions?

**Contact us:**
- 📧 Email: support@amcis-security.com
- 💬 Discord: https://discord.gg/amcis
- 🐦 Twitter: @AMCIS_Security
- 🌐 Website: https://amcis-security.com

---

**Last Updated:** 2026-03-17  
**Document Owner:** AMCIS Customer Success Team
