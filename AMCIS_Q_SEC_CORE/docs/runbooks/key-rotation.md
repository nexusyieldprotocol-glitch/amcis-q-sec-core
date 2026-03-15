# Key Rotation Runbook

**Classification:** Internal Use Only  
**Last Updated:** 2026-03-12  
**Version:** 1.0.0

---

## Overview

This runbook provides procedures for cryptographic key rotation in AMCIS Q-Sec-Core. Regular key rotation is essential for maintaining security posture and complying with regulatory requirements.

## Rotation Schedule

| Key Type | Rotation Frequency | Max Age |
|----------|-------------------|---------|
| **API Keys** | 90 days | 180 days |
| **Encryption Keys** | 1 year | 2 years |
| **Signing Keys** | 1 year | 2 years |
| **TLS Certificates** | 90 days | 397 days |
| **Service Accounts** | 180 days | 365 days |

---

## Pre-Rotation Checklist

- [ ] Verify current key usage metrics
- [ ] Notify stakeholders of maintenance window
- [ ] Confirm backup of current keys (for decryption)
- [ ] Verify new key storage is ready
- [ ] Schedule rotation during low-traffic period

---

## 1. Automated Key Rotation

### Step 1: Check Key Status
```bash
# List keys approaching expiration
python -c "
from amcis_q_sec_core.crypto import KeyManager
km = KeyManager()
expiring = km.get_expiring_keys(days=30)
for key in expiring:
    print(f'{key.key_id}: expires {key.expires_at}')
"
```

### Step 2: Initiate Rotation
```bash
# Rotate specific key
curl -X POST http://localhost:8080/api/v1/keys/{key_id}/rotate \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{
    "retain_old_key_days": 30,
    "notify_dependent_services": true
  }'
```

### Step 3: Verify Rotation
```bash
# Check new key is active
python -c "
from amcis_q_sec_core.crypto import KeyManager
km = KeyManager()
new_key = km.get_key('{new_key_id}')
print(f'Status: {new_key.status}')
print(f'Created: {new_key.created_at}')
"
```

---

## 2. Manual Key Rotation (Emergency)

### Scenario: Immediate Rotation Required

#### Step 1: Generate New Key
```bash
# Generate new encryption key
python -c "
from amcis_q_sec_core.crypto import KeyManager, KeyType
km = KeyManager()
new_key = km.generate_key(
    key_type=KeyType.AES_256_GCM,
    purpose='data_encryption',
    auto_rotate=False
)
print(f'New key ID: {new_key.key_id}')
"
```

#### Step 2: Re-encrypt Data
```bash
# Re-encrypt sensitive data with new key
python -c "
from amcis_q_sec_core.crypto import KeyManager
km = KeyManager()
km.reencrypt_all(
    old_key_id='{old_key_id}',
    new_key_id='{new_key_id}',
    batch_size=1000
)
"
```

#### Step 3: Update Service Configuration
```bash
# Update services to use new key
kubectl set env deployment/amcis-core \
  ENCRYPTION_KEY_ID={new_key_id}

# Rolling restart
kubectl rollout restart deployment/amcis-core
kubectl rollout status deployment/amcis-core
```

#### Step 4: Revoke Old Key
```bash
# Mark old key as deprecated (don't delete yet)
python -c "
from amcis_q_sec_core.crypto import KeyManager
km = KeyManager()
km.deprecate_key('{old_key_id}', grace_period_days=7)
"
```

---

## 3. Certificate Rotation

### TLS Certificate Rotation

#### Step 1: Generate CSR
```bash
# Generate new private key and CSR
openssl req -new -newkey rsa:4096 -nodes \
  -keyout amcis-new.key \
  -out amcis-new.csr \
  -subj "/C=US/ST=State/L=City/O=AMCIS/CN=api.amcis.io"
```

#### Step 2: Submit to CA
```bash
# Submit CSR to internal CA
curl -X POST https://ca.amcis.internal/sign \
  -F "csr=@amcis-new.csr" \
  -F "validity_days=90" \
  -o amcis-new.crt
```

#### Step 3: Install Certificate
```bash
# Create Kubernetes secret
kubectl create secret tls amcis-tls-new \
  --cert=amcis-new.crt \
  --key=amcis-new.key \
  --dry-run=client -o yaml | kubectl apply -f -

# Update ingress
kubectl patch ingress amcis-ingress \
  --type merge \
  -p '{"spec":{"tls":[{"secretName":"amcis-tls-new"}]}}'
```

#### Step 4: Verify Installation
```bash
# Check certificate
echo | openssl s_client -connect api.amcis.io:443 2>/dev/null | \
  openssl x509 -noout -dates -subject

# Verify expiration
echo | openssl s_client -connect api.amcis.io:443 2>/dev/null | \
  openssl x509 -noout -enddate
```

---

## 4. API Key Rotation

### Step 1: Generate New API Key
```bash
# Create new API key
curl -X POST http://localhost:8080/api/v1/auth/api-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "Production API Key (Rotated)",
    "permissions": ["read", "write"],
    "expires_days": 90
  }'
```

### Step 2: Update Client Applications
```bash
# Notify clients of new key
cat > api-key-rotation-notice.txt << EOF
Subject: API Key Rotation Notice

Your API key has been rotated.

Old Key: ****...{old_key_last4}
New Key: ****...{new_key_last4}

Please update your applications within 7 days.
The old key will expire on {expiration_date}.
EOF
```

### Step 3: Monitor Old Key Usage
```bash
# Check old key usage
curl "http://localhost:8080/api/v1/logs?event_type=api_access&api_key={old_key_id}"

# Alert if still in use after grace period
python -c "
from amcis_q_sec_core.monitoring import AlertManager
am = AlertManager()
if am.check_api_key_usage('{old_key_id}'):
    am.send_alert('Old API key still in use: {old_key_id}')
"
```

### Step 4: Revoke Old Key
```bash
# Revoke after grace period
curl -X DELETE http://localhost:8080/api/v1/auth/api-keys/{old_key_id} \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 5. Bulk Key Rotation

### Rotating All Keys in Environment

```bash
#!/bin/bash
# bulk-rotate.sh

ENVIRONMENT="production"
GRACE_PERIOD=7

# Get all keys needing rotation
python -c "
from amcis_q_sec_core.crypto import KeyManager
km = KeyManager()
keys = km.get_keys_for_rotation()
print('\n'.join([k.key_id for k in keys]))
" > keys-to-rotate.txt

# Rotate each key
for key_id in $(cat keys-to-rotate.txt); do
  echo "Rotating key: $key_id"
  
  curl -X POST http://localhost:8080/api/v1/keys/$key_id/rotate \
    -H "Authorization: Bearer $API_TOKEN" \
    -d "{\"retain_old_key_days\": $GRACE_PERIOD}"
  
  sleep 5
done

echo "Bulk rotation complete"
```

---

## 6. Verification Procedures

### Post-Rotation Verification

```bash
# Test encryption with new key
python -c "
from amcis_q_sec_core.crypto import KeyManager
km = KeyManager()

# Encrypt test data
ciphertext = km.encrypt('test-data', key_id='{new_key_id}')
plaintext = km.decrypt(ciphertext, key_id='{new_key_id}')

assert plaintext == 'test-data'
print('Encryption/Decryption: OK')
"

# Verify no old key usage
python -c "
from amcis_q_sec_core.monitoring import MetricsCollector
mc = MetricsCollector()
usage = mc.get_key_usage('{old_key_id}', hours=1)
print(f'Old key usage (last hour): {usage}')
assert usage == 0, 'Old key still in use!'
print('Old key usage: OK (none)')
"
```

---

## Rollback Procedures

### If New Key Fails

```bash
# Reactivate old key
python -c "
from amcis_q_sec_core.crypto import KeyManager
km = KeyManager()

# Reactivate old key
km.activate_key('{old_key_id}')

# Deprecate new key
km.deprecate_key('{new_key_id}')

# Update services
km.update_service_config(default_key='{old_key_id}')
"

# Restart services
kubectl rollout restart deployment/amcis-core
```

---

## Monitoring & Alerts

### Key Expiration Alerts

```yaml
# alerts/key-expiration.yml
groups:
  - name: key_rotation
    rules:
      - alert: KeyExpiringSoon
        expr: key_days_until_expiration < 30
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Key {{ $labels.key_id }} expires in {{ $value }} days"
      
      - alert: KeyExpired
        expr: key_days_until_expiration <= 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Key {{ $labels.key_id }} has expired"
```

---

## Compliance Documentation

### Rotation Evidence

```bash
# Generate rotation report
python -c "
from amcis_q_sec_core.compliance import ComplianceReporter
cr = ComplianceReporter()
report = cr.generate_key_rotation_report(
    start_date='2026-01-01',
    end_date='2026-03-31'
)
report.save('/compliance/key-rotation-q1-2026.pdf')
"
```
