# Backup & Restore Runbook

**Classification:** Internal Use Only  
**Last Updated:** 2026-03-12  
**Version:** 1.0.0

---

## Overview

This runbook provides procedures for backing up and restoring AMCIS Q-Sec-Core data and configuration.

## Backup Types

| Type | Frequency | Retention | Scope |
|------|-----------|-----------|-------|
| **Full** | Daily | 30 days | All data |
| **Incremental** | Every 6 hours | 7 days | Changed data |
| **Configuration** | On change | 90 days | Config files |
| **Disaster Recovery** | Weekly | 90 days | Cross-region |

---

## 1. Automated Backup Verification

### Check Last Backup Status
```bash
# Check PostgreSQL backup
psql -h localhost -U amcis -c "
SELECT 
  backup_label,
  backup_type,
  started_at,
  completed_at,
  status
FROM pg_backup_history
ORDER BY started_at DESC
LIMIT 5;
"

# Check backup file sizes
ls -lah /backups/amcis/postgres/
```

### Verify Backup Integrity
```bash
# Verify PostgreSQL backup
pg_verifybackup /backups/amcis/postgres/latest/

# Check Redis backup
redis-check-rdb /backups/amcis/redis/latest/dump.rdb
```

---

## 2. Manual Full Backup

### Step 1: Database Backup
```bash
#!/bin/bash
# full-backup.sh

BACKUP_DIR="/backups/amcis/postgres/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# PostgreSQL full backup
pg_basebackup \
  -h localhost \
  -U backup_user \
  -D "$BACKUP_DIR" \
  -Ft \
  -z \
  -P \
  -X stream \
  -l "Full backup $(date)"

# Verify backup
if [ $? -eq 0 ]; then
  echo "Backup successful: $BACKUP_DIR"
  echo "$BACKUP_DIR" > /backups/amcis/postgres/latest_link
else
  echo "Backup failed!"
  exit 1
fi
```

### Step 2: Redis Backup
```bash
# Trigger Redis BGSAVE
redis-cli BGSAVE

# Wait for completion
while redis-cli LASTSAVE | grep -q "ERR"; do
  sleep 1
done

# Copy to backup location
cp /var/lib/redis/dump.rdb "/backups/amcis/redis/redis-$(date +%Y%m%d_%H%M%S).rdb"
```

### Step 3: Configuration Backup
```bash
# Backup configuration files
tar -czf "/backups/amcis/config/config-$(date +%Y%m%d_%H%M%S).tar.gz" \
  /etc/amcis/ \
  /opt/amcis/config/ \
  /var/lib/amcis/settings/

# Backup Kubernetes manifests
kubectl get all -n amcis -o yaml > "/backups/amcis/config/k8s-manifests-$(date +%Y%m%d_%H%M%S).yaml"
```

### Step 4: Vault Secrets Backup
```bash
# Export Vault data (requires root token)
vault operator raft snapshot save "/backups/amcis/vault/vault-$(date +%Y%m%d_%H%M%S).snap"

# Verify snapshot
vault operator raft snapshot inspect "/backups/amcis/vault/vault-$(date +%Y%m%d_%H%M%S).snap"
```

---

## 3. Point-in-Time Recovery

### Restore PostgreSQL to Specific Time

#### Step 1: Stop Application
```bash
# Stop AMCIS services
kubectl scale deployment amcis-core --replicas=0

# Wait for termination
kubectl wait --for=delete pod -l app=amcis-core --timeout=60s
```

#### Step 2: Prepare Restore Environment
```bash
# Create recovery directory
mkdir -p /var/lib/postgresql/recovery
cd /var/lib/postgresql/recovery

# Extract base backup
tar -xzf /backups/amcis/postgres/20260312_000000/base.tar.gz
```

#### Step 3: Configure Recovery
```bash
# Create recovery.conf
cat > /var/lib/postgresql/recovery/recovery.conf << EOF
restore_command = 'cp /backups/amcis/postgres/wal/%f %p'
recovery_target_time = '2026-03-12 10:00:00'
recovery_target_action = 'pause'
EOF
```

#### Step 4: Start Recovery
```bash
# Start PostgreSQL in recovery mode
docker run -d \
  -v /var/lib/postgresql/recovery:/var/lib/postgresql/data \
  -e POSTGRES_USER=amcis \
  -e POSTGRES_PASSWORD=amcis \
  postgres:15 \
  postgres -c config_file=/var/lib/postgresql/data/postgresql.conf

# Monitor recovery
psql -c "SELECT pg_last_xact_replay_timestamp();"
```

#### Step 5: Promote to Primary
```bash
# When recovery target reached
psql -c "SELECT pg_wal_replay_pause();"
psql -c "SELECT pg_promote();"
```

---

## 4. Complete Disaster Recovery

### Scenario: Total Data Loss

#### Step 1: Provision New Infrastructure
```bash
# Apply Terraform configuration
cd infrastructure/terraform
terraform init
terraform apply -var="environment=recovery"
```

#### Step 2: Restore PostgreSQL
```bash
# Create new PostgreSQL instance
kubectl apply -f k8s/postgres.yaml

# Wait for readiness
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s

# Restore from backup
kubectl exec -it postgres-0 -- pg_restore \
  -h localhost \
  -U amcis \
  -d amcis \
  /backups/amcis/postgres/latest/backup.dump
```

#### Step 3: Restore Redis
```bash
# Copy backup to Redis pod
kubectl cp /backups/amcis/redis/latest/dump.rdb redis-0:/data/dump.rdb

# Restart Redis
kubectl delete pod redis-0
```

#### Step 4: Restore Vault
```bash
# Restore Vault snapshot
kubectl exec -it vault-0 -- vault operator raft snapshot restore \
  /backups/amcis/vault/latest.snap

# Unseal Vault
kubectl exec -it vault-0 -- vault operator unseal $UNSEAL_KEY_1
kubectl exec -it vault-0 -- vault operator unseal $UNSEAL_KEY_2
kubectl exec -it vault-0 -- vault operator unseal $UNSEAL_KEY_3
```

#### Step 5: Restore Application
```bash
# Deploy AMCIS
kubectl apply -f k8s/amcis-core.yaml

# Verify restoration
kubectl wait --for=condition=ready pod -l app=amcis-core --timeout=300s

# Run health checks
curl http://localhost:8080/health/ready
```

---

## 5. Cross-Region DR Failover

### Failover to DR Region

```bash
#!/bin/bash
# dr-failover.sh

DR_REGION="us-west-2"
PRIMARY_REGION="us-east-1"

echo "Initiating failover to $DR_REGION..."

# 1. Promote DR database
echo "Promoting DR database..."
aws rds promote-read-replica \
  --db-instance-identifier amcis-dr \
  --region $DR_REGION

# 2. Update DNS
echo "Updating DNS..."
aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.amcis.io",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{"Value": "api-dr.amcis.io"}]
      }
    }]
  }'

# 3. Scale up DR services
echo "Scaling up DR services..."
kubectl --context dr config use-context dr
kubectl scale deployment amcis-core --replicas=5

echo "Failover complete"
```

---

## 6. Backup Testing

### Monthly Backup Restore Test

```bash
#!/bin/bash
# backup-test.sh

TEST_DIR="/tmp/backup-test-$(date +%s)"
mkdir -p "$TEST_DIR"

echo "=== Backup Restore Test ==="

# 1. Select random backup
BACKUP=$(ls /backups/amcis/postgres/ | shuf -n 1)
echo "Testing backup: $BACKUP"

# 2. Restore to test instance
docker run -d \
  --name postgres-test \
  -v "$TEST_DIR":/var/lib/postgresql/data \
  postgres:15

# Extract and restore
tar -xzf "/backups/amcis/postgres/$BACKUP/base.tar.gz" -C "$TEST_DIR"

# 3. Verify data integrity
docker exec postgres-test psql -U amcis -c "SELECT COUNT(*) FROM users;"
docker exec postgres-test psql -U amcis -c "SELECT pg_verify_checksums();"

# 4. Cleanup
docker stop postgres-test
docker rm postgres-test
rm -rf "$TEST_DIR"

echo "=== Backup test complete ==="
```

---

## Storage Management

### Cleanup Old Backups

```bash
# Remove backups older than retention period
find /backups/amcis/postgres/ -type d -mtime +30 -exec rm -rf {} \;
find /backups/amcis/redis/ -type f -mtime +7 -exec rm -f {} \;
find /backups/amcis/vault/ -type f -mtime +90 -exec rm -f {} \;

# Verify storage usage
df -h /backups/
du -sh /backups/amcis/*
```

---

## Quick Reference

```bash
# List available backups
ls -lt /backups/amcis/postgres/ | head -10

# Check backup size
du -sh /backups/amcis/postgres/latest/

# Quick database backup
pg_dump -h localhost -U amcis amcis > backup-$(date +%Y%m%d).sql

# Quick restore
psql -h localhost -U amcis amcis < backup-20260312.sql

# Check replication status
psql -c "SELECT * FROM pg_stat_replication;"
```
