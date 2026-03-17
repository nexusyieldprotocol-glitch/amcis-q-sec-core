# AMCIS Troubleshooting Playbook
## Step-by-Step Solutions for Common Issues

**Version:** 1.0.0  
**Audience:** System Administrators, Support Engineers

---

## 🔴 CRITICAL ISSUES

### Issue 1: System Completely Down

**Symptoms:**
- Cannot access dashboard
- API returns 503 errors
- Health check fails

**Diagnosis:**
```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs --tail=100 amcis-api

# Check resource usage
docker stats
```

**Resolution:**
```bash
# 1. Restart services
docker-compose restart

# 2. If still down, check database
docker-compose exec postgres pg_isready

# 3. Check disk space
df -h

# 4. Full reset (last resort)
docker-compose down
docker-compose up -d
```

---

### Issue 2: Database Corruption

**Symptoms:**
- PostgreSQL errors in logs
- Data inconsistencies
- Query failures

**Diagnosis:**
```bash
# Check PostgreSQL logs
docker-compose logs postgres | grep ERROR

# Run integrity check
docker-compose exec postgres psql -c "CHECKPOINT;"
docker-compose exec postgres psql -c "SELECT pg_database.datname, pg_database_size(pg_database.datname) FROM pg_database WHERE datname='amcis';"
```

**Resolution:**
```bash
# 1. Restore from backup
python scripts/restore.py --backup-id $(ls -t backups/ | head -1)

# 2. If no backup, attempt repair
docker-compose exec postgres psql -c "REINDEX DATABASE amcis;"
```

---

## 🟠 HIGH PRIORITY ISSUES

### Issue 3: High CPU Usage

**Symptoms:**
- CPU > 90%
- Slow response times
- Timeouts

**Diagnosis:**
```bash
# Find CPU-intensive processes
top -o %CPU

# Check specific AMCIS processes
ps aux | grep amcis

# Analyze query performance
python scripts/analyze_queries.py --slow-threshold 1000
```

**Resolution:**
```bash
# 1. Scale horizontally
docker-compose up -d --scale amcis-api=5

# 2. Restart problematic service
docker-compose restart amcis-api

# 3. Clear cache
redis-cli FLUSHDB

# 4. Enable query caching
python scripts/enable_query_cache.py
```

---

### Issue 4: Memory Exhaustion

**Symptoms:**
- OOM errors
- Container restarts
- Slow performance

**Diagnosis:**
```bash
# Check memory usage
free -h
docker stats --no-stream

# Check for memory leaks
python scripts/check_memory_leaks.py
```

**Resolution:**
```bash
# 1. Increase memory limits
# Edit docker-compose.yml
services:
  amcis-api:
    deploy:
      resources:
        limits:
          memory: 8G

# 2. Restart with new limits
docker-compose up -d

# 3. Clear old data
python scripts/cleanup_old_data.py --days 30
```

---

### Issue 5: Network Connectivity Issues

**Symptoms:**
- Cannot reach external APIs
- DNS resolution failures
- Intermittent timeouts

**Diagnosis:**
```bash
# Test connectivity
docker-compose exec amcis-api curl -v https://api.external-service.com

# Check DNS
docker-compose exec amcis-api nslookup api.amcis-security.com

# Check network configuration
docker network inspect amcis-network
```

**Resolution:**
```bash
# 1. Restart network
docker-compose down
docker network prune
docker-compose up -d

# 2. Check firewall rules
iptables -L | grep 8080

# 3. Update DNS settings
# Edit /etc/docker/daemon.json
{
  "dns": ["8.8.8.8", "1.1.1.1"]
}
```

---

## 🟡 MEDIUM PRIORITY ISSUES

### Issue 6: Slow API Response Times

**Symptoms:**
- p95 latency > 500ms
- User complaints
- Timeouts

**Diagnosis:**
```bash
# Check latency distribution
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8080/health

# Analyze slow queries
python scripts/analyze_queries.py --slow-threshold 100

# Check Redis cache hit rate
redis-cli INFO stats | grep keyspace
```

**Resolution:**
```bash
# 1. Enable query caching
python scripts/enable_query_cache.py

# 2. Optimize database
python scripts/optimize_database.py

# 3. Scale API instances
docker-compose up -d --scale amcis-api=5

# 4. Enable CDN for static assets
# Update config/cdn.yaml
```

---

### Issue 7: Authentication Failures

**Symptoms:**
- 401 Unauthorized errors
- Cannot log in
- API key rejected

**Diagnosis:**
```bash
# Check auth service logs
docker-compose logs amcis-api | grep -i "auth\|login"

# Verify API key
python scripts/verify_api_key.py --key your-key-here

# Check Vault status
docker-compose exec vault vault status
```

**Resolution:**
```bash
# 1. Regenerate API key
python scripts/generate_api_key.py --user admin --role super_admin

# 2. Unseal Vault if needed
docker-compose exec vault vault operator unseal

# 3. Restart auth service
docker-compose restart amcis-api
```

---

### Issue 8: Backup Failures

**Symptoms:**
- Backup jobs failing
- Incomplete backups
- Storage full

**Diagnosis:**
```bash
# Check backup logs
tail -f logs/backup.log

# Check storage space
df -h /backups

# Verify S3 access
aws s3 ls s3://your-backup-bucket/
```

**Resolution:**
```bash
# 1. Clean up old backups
python scripts/cleanup_old_backups.py --keep-days 30

# 2. Test S3 credentials
aws s3 cp test.txt s3://your-backup-bucket/

# 3. Run manual backup
python scripts/backup.py --full --verbose

# 4. Check backup integrity
python scripts/verify_backup.py --latest
```

---

## 🟢 LOW PRIORITY ISSUES

### Issue 9: Warning Messages in Logs

**Symptoms:**
- Deprecation warnings
- Non-critical errors
- Info messages cluttering logs

**Resolution:**
```bash
# Adjust log level
# Edit config/logging.yaml
logging:
  level: WARNING  # Change from DEBUG

# Restart services
docker-compose restart
```

---

### Issue 10: Dashboard UI Issues

**Symptoms:**
- Charts not loading
- UI glitches
- Browser console errors

**Resolution:**
```bash
# Clear browser cache
# Hard refresh: Ctrl+Shift+R

# Check static assets
docker-compose exec amcis-api ls -la /app/static/

# Rebuild frontend
npm run build
```

---

## 📊 Diagnostic Scripts

### Full System Health Check

```bash
#!/bin/bash
# save as: health_check.sh

echo "=== AMCIS Health Check ==="
echo "Timestamp: $(date)"

# Check containers
echo -e "\n[1/7] Checking containers..."
docker-compose ps | grep -q "Up" && echo "✓ Containers running" || echo "✗ Containers down"

# Check API
echo -e "\n[2/7] Checking API..."
curl -sf http://localhost:8080/health > /dev/null && echo "✓ API healthy" || echo "✗ API unhealthy"

# Check database
echo -e "\n[3/7] Checking database..."
docker-compose exec -T postgres pg_isready -q && echo "✓ Database ready" || echo "✗ Database down"

# Check Redis
echo -e "\n[4/7] Checking Redis..."
docker-compose exec -T redis redis-cli ping | grep -q "PONG" && echo "✓ Redis ready" || echo "✗ Redis down"

# Check disk space
echo -e "\n[5/7] Checking disk space..."
USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$USAGE" -lt 80 ]; then
    echo "✓ Disk space OK ($USAGE%)"
else
    echo "⚠ Disk space warning ($USAGE%)"
fi

# Check memory
echo -e "\n[6/7] Checking memory..."
free -h | grep Mem

# Check logs for errors
echo -e "\n[7/7] Checking recent errors..."
ERROR_COUNT=$(docker-compose logs --since=1h 2>&1 | grep -i "error\|fatal" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "✓ No errors in last hour"
else
    echo "⚠ $ERROR_COUNT errors in last hour"
fi

echo -e "\n=== Health Check Complete ==="
```

---

## 🆘 Emergency Contacts

| Severity | Issue | Contact | Response Time |
|----------|-------|---------|---------------|
| 🔴 P1 | System down/production outage | emergency@amcis-security.com | 15 min |
| 🟠 P2 | Major feature broken | support@amcis-security.com | 2 hours |
| 🟡 P3 | Minor issues | community@amcis-security.com | 24 hours |
| 🟢 P4 | Questions/docs | docs@amcis-security.com | 48 hours |

---

## 📚 Related Documentation

- [Administrator Handbook](02_ADMINISTRATOR_HANDBOOK.md)
- [Developer Integration Guide](03_DEVELOPER_INTEGRATION_GUIDE.md)
- [Quick Start Guide](01_QUICK_START_GUIDE.md)

---

**Last Updated:** 2026-03-17  
**Document Owner:** AMCIS Support Team
