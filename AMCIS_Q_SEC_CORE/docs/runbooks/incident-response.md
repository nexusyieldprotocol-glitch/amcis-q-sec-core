# Incident Response Runbook

**Classification:** Internal Use Only  
**Last Updated:** 2026-03-12  
**Version:** 1.0.0

---

## Overview

This runbook provides step-by-step procedures for responding to security incidents in the AMCIS Q-Sec-Core environment.

## Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| **Critical** | Active breach, data exfiltration | 15 minutes | Ransomware, APT compromise |
| **High** | Confirmed intrusion, lateral movement | 1 hour | Malware outbreak, credential theft |
| **Medium** | Suspicious activity, policy violation | 4 hours | Port scanning, failed auth spikes |
| **Low** | Anomaly detected, no confirmed threat | 24 hours | Unusual traffic patterns |

---

## 1. Initial Detection & Triage

### Step 1: Acknowledge Alert
```bash
# Acknowledge alert in system
curl -X POST http://localhost:8080/api/v1/alerts/{alert_id}/acknowledge \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{"analyst": "your.name@amcis.internal"}'
```

### Step 2: Gather Initial Context
```bash
# Get alert details
curl http://localhost:8080/api/v1/alerts/{alert_id}

# Check related logs
curl "http://localhost:8080/api/v1/logs?start_time=2026-03-12T00:00:00Z&event_type=security"
```

### Step 3: Classify Severity
- Review threat intelligence
- Check affected systems
- Assess potential impact
- Determine severity level

---

## 2. Containment

### Immediate Actions (Critical/High)

#### 2.1 Isolate Affected System
```bash
# Network isolation via microsegmentation
curl -X POST http://localhost:8080/api/v1/threats/{threat_id}/respond \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{
    "action": "isolate",
    "target": "10.0.1.100",
    "reason": "Suspected compromise"
  }'
```

#### 2.2 Revoke Compromised Credentials
```bash
# Revoke API keys
python -c "
from amcis_q_sec_core.secrets_mgr import SecretsManager
sm = SecretsManager()
sm.revoke_key('compromised-key-id')
"
```

#### 2.3 Enable Enhanced Monitoring
```bash
# Increase log verbosity
kubectl set env deployment/amcis-core AMCIS_LOG_LEVEL=DEBUG

# Enable packet capture
kubectl exec -it amcis-core -- tcpdump -i any -w /tmp/incident-$(date +%s).pcap
```

---

## 3. Investigation

### Step 1: Collect Evidence
```bash
# Export audit logs
curl -X POST http://localhost:8080/api/v1/logs/export \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{
    "start_time": "2026-03-12T00:00:00Z",
    "end_time": "2026-03-12T23:59:59Z",
    "format": "json"
  }' > incident-evidence.json
```

### Step 2: Analyze Timeline
```bash
# Generate forensic timeline
python -c "
from amcis_q_sec_core.forensics import TimelineAnalyzer
ta = TimelineAnalyzer()
timeline = ta.generate('10.0.1.100', '2026-03-12')
timeline.export('/tmp/timeline.html')
"
```

### Step 3: Check Indicators of Compromise
```bash
# Search for IOCs
for ioc in $(cat ioc-list.txt); do
  grep -r "$ioc" /var/log/amcis/
done
```

---

## 4. Eradication

### Step 1: Remove Malware/Threats
```bash
# Run malware scan
clamscan -r /var/lib/amcis/data

# Remove infected files (after backup)
find /var/lib/amcis/data -name "*.infected" -exec rm -f {} \;
```

### Step 2: Patch Vulnerabilities
```bash
# Check for available patches
apt list --upgradable | grep -E "openssl|openssh|python"

# Apply security updates
apt update && apt upgrade -y

# Restart services
systemctl restart amcis-core
```

### Step 3: Reset Compromised Accounts
```bash
# Force password reset
python -c "
from amcis_q_sec_core.identity import IdentityManager
im = IdentityManager()
im.force_password_reset('compromised-user')
"
```

---

## 5. Recovery

### Step 1: Restore from Clean Backup
```bash
# Identify clean backup point
ls -la /backups/amcis/ | grep "2026-03-11"

# Restore data
./scripts/restore.sh --backup-point 2026-03-11 --verify
```

### Step 2: Re-enable Services
```bash
# Gradually re-enable network access
curl -X POST http://localhost:8080/api/v1/threats/{threat_id}/respond \
  -d '{"action": "restore_network", "target": "10.0.1.100"}'

# Monitor for recurrence
watch -n 30 'curl http://localhost:8080/api/v1/threats?status=active'
```

### Step 3: Verify System Integrity
```bash
# Run integrity checks
python -c "
from amcis_q_sec_core.integrity import IntegrityChecker
ic = IntegrityChecker()
result = ic.verify_all()
print(f'Integrity: {result.passed}/{result.total} checks passed')
"
```

---

## 6. Post-Incident Activities

### Step 1: Document Timeline
```bash
# Generate incident report
cat > incident-report-$(date +%Y%m%d).md << EOF
# Incident Report: INC-$(date +%Y%m%d)-001

## Summary
- Detection Time: 
- Containment Time: 
- Resolution Time: 

## Root Cause
[To be determined]

## Impact
- Systems Affected: 
- Data Compromised: 
- Downtime: 

## Actions Taken
1. 
2. 
3. 

## Lessons Learned
- 

## Follow-up Actions
- [ ] 
EOF
```

### Step 2: Update Detection Rules
```bash
# Add new IOCs to threat detection
python -c "
from amcis_q_sec_core.threat_intel import ThreatIntelManager
tim = ThreatIntelManager()
tim.add_ioc('malicious-domain.com', 'c2_server')
tim.add_ioc('192.168.1.100', 'malicious_ip')
"
```

### Step 3: Conduct Post-Mortem
- Schedule within 48 hours
- Include all responders
- Document root cause
- Identify process improvements

---

## Contact Information

| Role | Contact | Escalation |
|------|---------|------------|
| On-call Security | security-oncall@amcis.internal | +15 min |
| Incident Commander | ic@amcis.internal | +30 min |
| CISO | ciso@amcis.internal | +1 hour |
| Legal | legal@amcis.internal | Data breach |
| PR | pr@amcis.internal | Public incident |

---

## Quick Reference Commands

```bash
# View active alerts
curl http://localhost:8080/api/v1/alerts?status=firing

# Check system health
curl http://localhost:8080/health/ready

# Generate compliance report
curl http://localhost:8080/api/v1/compliance/report?format=pdf

# Export logs for analysis
curl -X POST http://localhost:8080/api/v1/logs/export \
  -d '{"start_time": "2026-03-12T00:00:00Z", "format": "json"}'
```
