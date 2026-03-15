# AMCIS Q-SEC CORE - Commercial Distribution Guide

**Version:** 1.0.0-Commercial  
**Date:** February 26, 2026  
**Classification:** COMMERCIAL CONFIDENTIAL

---

## Quick Start for Commercial Distribution

### 1. Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Verify environment
python -c "import commercial.licensing; print('Commercial module OK')"
```

### 2. Generate License for Customer

```bash
# Enterprise license for 50,000 endpoints
python -m commercial.license_generator \
    --tier ENTERPRISE \
    --customer "Fortune 100 Bank" \
    --endpoints 50000 \
    --years 3 \
    --all-modules \
    --output ./licenses/
```

### 3. Build Secure Package

```bash
# Build watermarked, encrypted package
python -m commercial.package_builder \
    --customer "Fortune 100 Bank" \
    --tier ENTERPRISE \
    --output ./dist/ \
    --source .
```

### 4. Distribute to Customer

1. **Secure Transfer:** Use encrypted email or secure file sharing
2. **License File:** Deliver `LICENSE.dat` separately
3. **Signature:** Provide `.sig` file for verification
4. **Documentation:** Include `COMMERCIAL_LICENSE.md`

---

## License Tiers

| Tier | Max Endpoints | Annual Price | Key Features |
|------|---------------|--------------|--------------|
| **EVALUATION** | 100 | Free (30 days) | Full access, limited time |
| **STARTER** | 5,000 | $150K-$500K | Core + EDR + WAF |
| **PROFESSIONAL** | 25,000 | $500K-$2M | + PQC Crypto + DLP + Compliance |
| **ENTERPRISE** | 100,000 | $2M-$8M | All modules + 24/7 support |
| **STRATEGIC** | Unlimited | $8M-$50M | + Source code + custom dev |
| **GOVERNMENT** | Unlimited | Custom | Air-gapped + classified |

---

## Security Features

### Hardware Binding
Each license is cryptographically bound to the customer's hardware:
- Device fingerprinting (SHA3-256)
- Hardware tamper detection
- Automatic lock on hardware change

### Source Code Watermarking
Every file contains invisible forensic watermarks:
- Customer ID embedding
- Distribution tracing
- Leak detection capability

### License Validation
Runtime license enforcement:
- Signature verification (HMAC-SHA3-256)
- Expiration checking
- Module access control
- Endpoint counting

### Package Security
Distribution packages include:
- AES-256-GCM encryption
- Tamper-evident signatures
- Integrity manifest
- Anti-debugging measures

---

## File Structure

```
AMCIS_Q_SEC_CORE/
├── commercial/               # Commercial tools
│   ├── __init__.py
│   ├── licensing.py         # License management
│   ├── license_generator.py # CLI license tool
│   ├── watermark.py         # Source watermarking
│   └── package_builder.py   # Distribution builder
├── .VAULT_MASTER            # Master credentials (RESTRICTED)
├── .access_control          # Access configuration
├── COMMERCIAL_LICENSE.md    # License agreement
├── COMMERCIAL_README.md     # This file
└── MARKET_ANALYSIS.md       # Pricing & targets
```

---

## Customer Onboarding Checklist

- [ ] Customer signed license agreement
- [ ] Payment received/PO approved
- [ ] License generated for correct tier
- [ ] Source code watermarked with customer ID
- [ ] Package built and signed
- [ ] Secure delivery to customer
- [ ] Customer installed license
- [ ] Validation successful
- [ ] Support handoff complete

---

## Emergency Procedures

### Key Compromise
```bash
# Rotate signing key
python -m commercial.admin rotate-keys --key LSK-001

# Notify all customers
python -m commercial.admin notify --severity critical
```

### License Revocation
```bash
# Revoke specific license
python -m commercial.admin revoke --license AMC-A1B2C3D4

# Add to CRL
python -m commercial.admin update-crl
```

### Source Code Leak
1. Identify watermarked copy
2. Revoke associated licenses
3. Legal review
4. Public disclosure if required

---

## Support Contacts

| Type | Contact | Response |
|------|---------|----------|
| **Sales** | sales@amcis-security.com | 24h |
| **Technical** | support@amcis-security.com | 4h (Enterprise+) |
| **Security** | security@amcis-security.com | 1h |
| **Legal** | legal@amcis-security.com | 24h |

---

## Revenue Targets

| Quarter | Target | Key Accounts |
|---------|--------|--------------|
| Q1 2026 | $5M | Anduril, Palantir |
| Q2 2026 | $15M | + Cloudflare, Moderna |
| Q3 2026 | $35M | + JPMorgan, Goldman |
| Q4 2026 | $60M | + AWS Partnership |
| **2027** | **$200M** | Market expansion |

---

## Legal Notices

**Copyright © 2026 AMCIS Security Corporation. All rights reserved.**

The AMCIS Q-SEC CORE software and associated documentation are protected by
copyright, trade secret, and patent laws. Unauthorized reproduction,
distribution, or disclosure is strictly prohibited.

**Patents Pending:** US Patent App. 63/XXX,XXX; 63/XXX,XXX

**Trademarks:** AMCIS™, Q-SEC CORE™, and associated logos are trademarks of
AMCIS Security Corporation.

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-26  
**Next Review:** 2026-03-26
