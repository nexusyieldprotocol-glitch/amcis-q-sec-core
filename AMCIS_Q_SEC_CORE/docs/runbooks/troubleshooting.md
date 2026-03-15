# Troubleshooting Runbook

**Classification:** Internal Use Only  
**Last Updated:** 2026-03-12  
**Version:** 1.0.0

---

## Overview

This runbook provides diagnostic procedures and solutions for common issues in AMCIS Q-Sec-Core.

## Quick Diagnostics

```bash
# System health check
curl http://localhost:8080/health/live
curl http://localhost:8080/health/ready

# Check all pods
kubectl get pods -n amcis

# Check recent events
kubectl get events -n amcis --sort-by='.lastTimestamp' | tail -20

# Check logs
kubectl logs -n amcis -l app=amcis-core --tail=100
```

---

## 1. Service Won't Start

### Symptoms
- Pod stuck in `CrashLoopBackOff`
- Pod stuck in `Pending`
- Container exits immediately

### Diagnostics
```bash
# Check pod status
kubectl describe pod amcis-core-xxx -n amcis

# View container logs
kubectl logs -n amcis amcis-core-xxx --previous

# Check for OOM kills
kubectl get pod amcis-core-xxx -n amcis -o yaml | grep -A5 "lastState"
```

### Solutions

#### Issue: Out of Memory
```bash
# Increase memory limit
kubectl patch deployment amcis-core -n amcis --type strategic -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "amcis-core",
          "resources": {
            "limits": {
              "memory": "4Gi"
            }
          }
        }]
      }
    }
  }
}'
```

#### Issue: Missing Config
```bash
# Check configmap exists
kubectl get configmap amcis-config -n amcis

# Recreate if missing
kubectl apply -f config/amcis-config.yaml

# Restart pod
kubectl delete pod -n amcis -l app=amcis-core
```

#### Issue: Database Connection Failed
```bash
# Test database connectivity
kubectl exec -it amcis-core-xxx -n amcis -- \
  nc -zv postgres 5432

# Check database credentials
kubectl get secret postgres-credentials -n amcis -o jsonpath='{.data.password}' | base64 -d
```

---

## 2. High Latency

### Symptoms
- API response times > 500ms
- Timeouts occurring
- Slow user experience

### Diagnostics
```bash
# Check resource usage
kubectl top pods -n amcis -l app=amcis-core

# Check database performance
kubectl exec -it postgres-0 -n amcis -- psql -U amcis -c "
SELECT pid, state, query_start, query 
FROM pg_stat_activity 
WHERE state = 'active' 
ORDER BY query_start;
"

# Check Redis latency
kubectl exec -it redis-0 -n amcis -- redis-cli --latency

# Analyze slow queries
kubectl exec -it postgres-0 -n amcis -- psql -U amcis -c "
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"
```

### Solutions

#### Database Connection Pool Exhausted
```bash
# Increase pool size
kubectl set env deployment/amcis-core -n amcis \
  DATABASE_POOL_SIZE=50 \
  DATABASE_MAX_OVERFLOW=20

# Check active connections
kubectl exec -it postgres-0 -n amcis -- psql -U amcis -c "
SELECT count(*), state 
FROM pg_stat_activity 
GROUP BY state;
"
```

#### Slow Database Queries
```bash
# Add missing index
kubectl exec -it postgres-0 -n amcis -- psql -U amcis -c "
CREATE INDEX CONCURRENTLY idx_api_requests_timestamp 
ON api_requests(timestamp);
"

# Analyze tables
kubectl exec -it postgres-0 -n amcis -- psql -U amcis -c "
ANALYZE api_requests;
ANALYZE patterns;
"
```

#### Redis Cache Issues
```bash
# Check cache hit rate
kubectl exec -it redis-0 -n amcis -- redis-cli INFO stats | grep keyspace

# Flush cache if corrupted
kubectl exec -it redis-0 -n amcis -- redis-cli FLUSHDB

# Scale Redis
kubectl scale deployment redis --replicas=3 -n amcis
```

---

## 3. Authentication Failures

### Symptoms
- 401/403 errors
- "Invalid token" messages
- Users cannot log in

### Diagnostics
```bash
# Check JWT validation
kubectl logs -n amcis -l app=amcis-core | grep -i "auth\|jwt\|token"

# Verify Vault status
kubectl exec -it vault-0 -n amcis -- vault status

# Check API key validity
python -c "
import jwt
try:
    jwt.decode('test-token', 'secret', algorithms=['HS256'])
except Exception as e:
    print(f'JWT error: {e}')
"
```

### Solutions

#### Vault Seal
```bash
# Check seal status
kubectl exec -it vault-0 -n amcis -- vault status

# Unseal if necessary
kubectl exec -it vault-0 -n amcis -- vault operator unseal $UNSEAL_KEY_1
kubectl exec -it vault-0 -n amcis -- vault operator unseal $UNSEAL_KEY_2
kubectl exec -it vault-0 -n amcis -- vault operator unseal $UNSEAL_KEY_3
```

#### Token Expired
```bash
# Generate new service token
kubectl exec -it vault-0 -n amcis -- vault token create \
  -policy=amcis-policy \
  -ttl=768h \
  -display-name=amcis-core

# Update Kubernetes secret
kubectl create secret generic vault-token \
  --from-literal=token=$NEW_TOKEN \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods
kubectl delete pod -n amcis -l app=amcis-core
```

---

## 4. Memory Leaks

### Symptoms
- Memory usage growing over time
- OOM kills
- Performance degrading

### Diagnostics
```bash
# Check memory usage trend
kubectl top pod amcis-core-xxx -n amcis --containers

# Get memory profile
kubectl exec -it amcis-core-xxx -n amcis -- \
  python -c "
import tracemalloc
tracemalloc.start()
# ... run operations
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
"

# Check for memory leaks in Python
kubectl logs -n amcis -l app=amcis-core | grep -i "memory\|gc\|leak"
```

### Solutions

#### Restart Service
```bash
# Rolling restart
kubectl rollout restart deployment/amcis-core -n amcis

# Monitor restart
kubectl rollout status deployment/amcis-core -n amcis
```

#### Adjust GC Settings
```bash
# Increase GC threshold
kubectl set env deployment/amcis-core -n amcis \
  PYTHONGC=1 \
  GC_THRESHOLD=700,10,10
```

---

## 5. Disk Space Issues

### Symptoms
- "No space left on device" errors
- Cannot write logs
- Database operations fail

### Diagnostics
```bash
# Check disk usage
kubectl exec -it amcis-core-xxx -n amcis -- df -h

# Check PostgreSQL size
kubectl exec -it postgres-0 -n amcis -- psql -U amcis -c "
SELECT pg_size_pretty(pg_database_size('amcis'));
"

# Check log sizes
kubectl exec -it amcis-core-xxx -n amcis -- \
  du -sh /var/log/amcis/*
```

### Solutions

#### Clean Up Logs
```bash
# Rotate and compress logs
kubectl exec -it amcis-core-xxx -n amcis -- \
  logrotate -f /etc/logrotate.d/amcis

# Delete old logs
kubectl exec -it amcis-core-xxx -n amcis -- \
  find /var/log/amcis -name '*.log.*' -mtime +7 -delete
```

#### Clean Up Database
```bash
# Vacuum and analyze
kubectl exec -it postgres-0 -n amcis -- psql -U amcis -c "
VACUUM ANALYZE;
"

# Clean up old audit logs
kubectl exec -it postgres-0 -n amcis -- psql -U amcis -c "
DELETE FROM api_requests 
WHERE timestamp < NOW() - INTERVAL '1 year';
"
```

#### Expand PVC
```bash
# Expand persistent volume
kubectl patch pvc amcis-data -n amcis --type merge -p '{
  "spec": {
    "resources": {
      "requests": {
        "storage": "100Gi"
      }
    }
  }
}'
```

---

## 6. Network Connectivity

### Symptoms
- Connection timeouts
- DNS resolution failures
- Cannot reach external services

### Diagnostics
```bash
# Test DNS resolution
kubectl exec -it amcis-core-xxx -n amcis -- \
  nslookup postgres.amcis.svc.cluster.local

# Test network connectivity
kubectl exec -it amcis-core-xxx -n amcis -- \
  nc -zv postgres 5432

# Check network policies
kubectl get networkpolicies -n amcis
```

### Solutions

#### DNS Issues
```bash
# Restart CoreDNS
kubectl delete pod -n kube-system -l k8s-app=kube-dns

# Check CoreDNS config
kubectl get configmap coredns -n kube-system -o yaml
```

#### Network Policy Blocking
```bash
# Temporarily allow all traffic
kubectl delete networkpolicy amcis-restrict -n amcis

# Or update policy
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-postgres
  namespace: amcis
spec:
  podSelector:
    matchLabels:
      app: amcis-core
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
EOF
```

---

## 7. High Error Rates

### Symptoms
- 500 errors increasing
- Error rate > 1%
- Service degradation

### Diagnostics
```bash
# Check error logs
kubectl logs -n amcis -l app=amcis-core | grep -i error | tail -50

# Check metrics
curl http://localhost:9090/api/v1/query?query='
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
'

# Trace request
kubectl exec -it amcis-core-xxx -n amcis -- \
  curl -v http://localhost:8080/api/v1/health
```

### Solutions

#### Database Connection Issues
```bash
# Restart database connection pool
kubectl delete pod -n amcis -l app=pgbouncer

# Check for deadlocks
kubectl exec -it postgres-0 -n amcis -- psql -U amcis -c "
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
"
```

#### Circuit Breaker Tripped
```bash
# Reset circuit breaker
kubectl exec -it amcis-core-xxx -n amcis -- \
  curl -X POST http://localhost:8080/admin/circuit-breaker/reset

# Or restart service
kubectl rollout restart deployment/amcis-core -n amcis
```

---

## 8. Vault Issues

### Symptoms
- Cannot read secrets
- "Permission denied" errors
- Vault sealed

### Solutions

#### Vault Not Initialized
```bash
# Initialize Vault
kubectl exec -it vault-0 -n amcis -- vault operator init \
  -key-shares=5 \
  -key-threshold=3

# Save unseal keys securely!
```

#### Vault Sealed
```bash
# Check status
kubectl exec -it vault-0 -n amcis -- vault status

# Unseal
for key in $UNSEAL_KEY_1 $UNSEAL_KEY_2 $UNSEAL_KEY_3; do
  kubectl exec -it vault-0 -n amcis -- vault operator unseal $key
done
```

#### Token Expired
```bash
# Generate new token
kubectl exec -it vault-0 -n amcis -- vault token create \
  -ttl=768h \
  -policy=amcis-policy

# Update secret
kubectl create secret generic vault-token \
  --from-literal=token=$NEW_TOKEN \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## Emergency Contacts

| Issue Type | Contact | Escalation |
|------------|---------|------------|
| Infrastructure | infrastructure@amcis.internal | +30 min |
| Security | security@amcis.internal | +15 min |
| Database | dba@amcis.internal | +30 min |
| On-call Engineer | oncall@amcis.internal | Immediate |
