# AMCIS Q-SEC CORE Hardened Configuration Guide

## Overview

This document provides security hardening guidelines for deploying AMCIS_Q_SEC_CORE in production environments.

## System Requirements

### Hardware
- CPU: 2+ cores (x86_64 or ARM64)
- RAM: 2GB minimum, 4GB recommended
- Storage: 10GB minimum for logs and forensics
- TPM 2.0 (optional but recommended)

### Software
- Python 3.12+
- Linux kernel 5.4+ (for BPF support)
- iptables/nftables (for microsegmentation)
- auditd (for syscall monitoring)

## Installation

### 1. System Preparation

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install dependencies
apt-get install -y python3.12 python3.12-venv python3-pip \
    libffi-dev libssl-dev iptables auditd

# Create AMCIS user
useradd -r -s /sbin/nologin -M amcis

# Create directories
mkdir -p /var/lib/amcis/{keys,logs,certs,forensics,provenance,integrity}
mkdir -p /etc/amcis
mkdir -p /var/log/amcis
chown -R amcis:amcis /var/lib/amcis /var/log/amcis
chmod 750 /var/lib/amcis
chmod 750 /var/log/amcis
```

### 2. Python Environment

```bash
# Create virtual environment
python3.12 -m venv /opt/amcis/venv
source /opt/amcis/venv/bin/activate

# Install AMCIS
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configuration

Create `/etc/amcis/kernel.conf`:

```ini
[amcis]
log_level = INFO
enable_tpm = false
dry_run = false

[crypto]
key_storage = file
auto_rotate = true
rotation_days = 90

[monitoring]
integrity_scan_interval = 300
process_scan_interval = 5
file_scan_interval = 60

[network]
enable_microsegmentation = true
default_deny = true
```

### 4. SELinux/AppArmor (if applicable)

```bash
# AppArmor profile
cp deployment/apparmor-profile /etc/apparmor.d/amcis
apparmor_parser -r /etc/apparmor.d/amcis
```

## Security Hardening

### 1. File Permissions

```bash
# Set restrictive permissions
chmod 700 /var/lib/amcis/keys
chmod 600 /etc/amcis/kernel.conf
chmod 755 /opt/amcis/venv/bin/amcis

# Enable immutable attribute on critical files
chattr +i /etc/amcis/kernel.conf
```

### 2. Kernel Parameters

Add to `/etc/sysctl.d/99-amcis.conf`:

```bash
# Disable core dumps
fs.suid_dumpable = 0

# Increase entropy pool
kernel.random.poolsize = 4096

# Network hardening
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1

# Memory protection
kernel.exec-shield = 1
kernel.randomize_va_space = 2
```

Apply with: `sysctl -p /etc/sysctl.d/99-amcis.conf`

### 3. Firewall Configuration

```bash
# Default deny
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Allow DNS
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

# Allow HTTPS
iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT
```

### 4. Audit Rules

Create `/etc/audit/rules.d/amcis.rules`:

```
# Monitor AMCIS files
-w /var/lib/amcis/ -p wa -k amcis_data
-w /etc/amcis/ -p wa -k amcis_config
-w /opt/amcis/ -p wa -k amcis_binaries

# Monitor key operations
-a always,exit -F arch=b64 -S openat -F exit=-EACCES -k access_denied
-a always,exit -F arch=b64 -S ptrace -k process_tracing

# Monitor privilege escalation
-a always,exit -F arch=b64 -S setuid -S setgid -S setreuid -S setregid -k privilege_escalation
```

Restart auditd: `systemctl restart auditd`

### 5. Resource Limits

Add to `/etc/security/limits.d/amcis.conf`:

```
amcis soft nofile 65536
amcis hard nofile 65536
amcis soft nproc 4096
amcis hard nproc 4096
amcis soft fsize 1048576
amcis hard fsize 1048576
```

## Operational Security

### 1. Log Management

```bash
# Configure logrotate
cat > /etc/logrotate.d/amcis << 'EOF'
/var/log/amcis/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0600 amcis amcis
}
EOF
```

### 2. Backup

```bash
# Backup script
cat > /opt/amcis/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/amcis/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

tar czf "$BACKUP_DIR/config.tar.gz" /etc/amcis/
tar czf "$BACKUP_DIR/data.tar.gz" /var/lib/amcis/

# Encrypt backup
gpg --encrypt --recipient security@amcis.local "$BACKUP_DIR/data.tar.gz"
rm "$BACKUP_DIR/data.tar.gz"
EOF
chmod +x /opt/amcis/backup.sh
```

### 3. Health Monitoring

```bash
# Create health check script
cat > /opt/amcis/health-check.sh << 'EOF'
#!/bin/bash
if ! python -m cli.amcis_main trust-report > /dev/null 2>&1; then
    echo "AMCIS health check failed" | logger -t amcis-health -p err
    exit 1
fi
exit 0
EOF
chmod +x /opt/amcis/health-check.sh

# Add to crontab
echo "*/5 * * * * /opt/amcis/health-check.sh" | crontab -
```

## Compliance Mapping

### NIST SP 800-53

| Control | AMCIS Implementation |
|---------|---------------------|
| AC-2 | Account Management via Trust Engine |
| AU-6 | Audit Record Analysis via Anomaly Engine |
| CM-5 | Access Restrictions for Change via Signature Enforcer |
| IR-4 | Incident Handling via Response Engine |
| SC-7 | Boundary Protection via Microsegmentation |
| SI-3 | Malicious Code Protection via EDR |
| SI-7 | Software Integrity via File Integrity Monitor |

### FIPS 140-3

- Key Manager uses FIPS-approved algorithms
- Crypto module can be backed by certified HSM
- Secure key destruction implemented

## Incident Response

### Forensic Collection

```bash
# Export forensic bundle
python -m cli.amcis_main forensic-export -o /forensics/$(date +%Y%m%d_%H%M%S).tar.gz
```

### Emergency Lockdown

```bash
# Enable kernel lockdown
python -c "import asyncio; from AMCIS_Q_SEC_CORE.core.amcis_kernel import AMCISKernel; k = AMCISKernel(); asyncio.run(k.enter_lockdown())"
```

## Maintenance

### Daily
- Review logs for anomalies
- Check disk space
- Verify health check status

### Weekly
- Rotate logs
- Review security alerts
- Check for updates

### Monthly
- Full backup
- Key rotation review
- Compliance audit

## Support

For issues or questions:
- Documentation: /opt/amcis/docs/
- Logs: /var/log/amcis/
- Status: `python -m cli.amcis_main trust-report`
