# Scaling Runbook

**Classification:** Internal Use Only  
**Last Updated:** 2026-03-12  
**Version:** 1.0.0

---

## Overview

This runbook provides procedures for horizontally and vertically scaling AMCIS Q-Sec-Core infrastructure.

## Scaling Triggers

| Metric | Scale Out Threshold | Scale In Threshold |
|--------|--------------------|--------------------|
| CPU Usage | > 70% for 5 min | < 30% for 10 min |
| Memory Usage | > 80% for 5 min | < 40% for 10 min |
| Request Latency | > 500ms p95 | < 100ms p95 |
| Queue Depth | > 1000 messages | < 100 messages |
| Error Rate | > 1% | < 0.1% |

---

## 1. Horizontal Pod Autoscaling

### Check Current Status
```bash
# View current HPA status
kubectl get hpa -n amcis

# View detailed metrics
kubectl describe hpa amcis-core

# Check current pods
kubectl get pods -n amcis -l app=amcis-core
```

### Manual Scale Out
```bash
# Scale to specific replica count
kubectl scale deployment amcis-core --replicas=10 -n amcis

# Verify scaling
kubectl get pods -n amcis -l app=amcis-core -w
```

### Configure HPA
```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: amcis-core
  namespace: amcis
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: amcis-core
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

Apply:
```bash
kubectl apply -f hpa.yaml
```

---

## 2. Vertical Pod Scaling

### Adjust Resource Requests/Limits

```bash
# Patch deployment with new resources
kubectl patch deployment amcis-core -n amcis --type strategic -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "amcis-core",
          "resources": {
            "requests": {
              "cpu": "1000m",
              "memory": "2Gi"
            },
            "limits": {
              "cpu": "2000m",
              "memory": "4Gi"
            }
          }
        }]
      }
    }
  }
}'
```

### Rolling Update with New Resources
```bash
# Edit deployment
kubectl edit deployment amcis-core -n amcis

# Or apply from file
kubectl apply -f deployment-scaled.yaml

# Monitor rollout
kubectl rollout status deployment/amcis-core -n amcis
```

---

## 3. Database Scaling

### Read Replica Scaling

```bash
# Add read replica
aws rds create-db-instance-read-replica \
  --db-instance-identifier amcis-replica-2 \
  --source-db-instance-identifier amcis-primary \
  --db-instance-class db.r5.xlarge

# Update application to use reader endpoint
kubectl set env deployment/amcis-core \
  DATABASE_URL="postgresql://amcis:amcis@amcis-cluster.cluster-ro-xxx.us-east-1.rds.amazonaws.com:5432/amcis"
```

### PostgreSQL Connection Pool Scaling
```bash
# Scale PgBouncer
kubectl scale deployment pgbouncer --replicas=5 -n amcis

# Update max connections
kubectl exec -it pgbouncer-xxx -n amcis -- \
  psql -p 5432 pgbouncer -c "RELOAD;"
```

---

## 4. Cache Scaling

### Redis Cluster Scaling
```bash
# Add Redis nodes
kubectl exec -it redis-cluster-0 -n amcis -- \
  redis-cli --cluster add-node \
  new-redis-node:6379 \
  redis-cluster-0.redis-cluster:6379

# Reshard cluster
kubectl exec -it redis-cluster-0 -n amcis -- \
  redis-cli --cluster reshard \
  redis-cluster-0.redis-cluster:6379 \
  --cluster-from all \
  --cluster-to new-node-id \
  --cluster-slots 4096 \
  --cluster-yes
```

### Redis Memory Scaling
```bash
# Vertical scaling - increase memory
kubectl patch statefulset redis -n amcis --type strategic -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "redis",
          "resources": {
            "requests": {
              "memory": "4Gi"
            },
            "limits": {
              "memory": "8Gi"
            }
          }
        }]
      }
    }
  }
}'
```

---

## 5. Load Balancer Scaling

### AWS ALB Scaling
```bash
# Check current ALB settings
aws elbv2 describe-load-balancers \
  --names amcis-alb \
  --query 'LoadBalancers[0].[LoadBalancerName,Scheme,State]'

# Request pre-warming for traffic spike
aws support create-case \
  --subject "ALB Pre-warming Request" \
  --service-code "elastic-load-balancing" \
  --severity-code "normal" \
  --body "Requesting pre-warming for AMCIS ALB. Expected traffic: 10000 RPS."
```

### Nginx Ingress Scaling
```bash
# Scale ingress controllers
kubectl scale deployment nginx-ingress-controller --replicas=5 -n ingress-nginx

# Update configmap for higher capacity
kubectl patch configmap nginx-configuration -n ingress-nginx --type merge -p '{
  "data": {
    "worker-processes": "auto",
    "worker-connections": "16384",
    "keep-alive": "75",
    "keep-alive-requests": "10000"
  }
}'
```

---

## 6. Storage Scaling

### PVC Expansion
```bash
# Expand PostgreSQL storage
kubectl patch pvc postgres-data -n amcis --type merge -p '{
  "spec": {
    "resources": {
      "requests": {
        "storage": "500Gi"
      }
    }
  }
}'

# Verify expansion
kubectl get pvc postgres-data -n amcis
```

### EBS Volume Scaling
```bash
# Modify EBS volume size
aws ec2 modify-volume \
  --volume-id vol-xxxxxxxx \
  --size 500

# Extend filesystem
kubectl exec -it postgres-0 -n amcis -- \
  resize2fs /dev/xvdf
```

---

## 7. Pre-Planned Scaling (Events)

### Pre-Scale for Expected Traffic
```bash
#!/bin/bash
# preevent-scale.sh

EVENT="Black Friday"
SCALE_UP_TIME="2026-11-28T00:00:00Z"
SCALE_DOWN_TIME="2026-11-29T00:00:00Z"

echo "Scheduling pre-event scaling for $EVENT"

# Scale up 24 hours before
at "$SCALE_UP_TIME" << EOF
kubectl scale deployment amcis-core --replicas=20 -n amcis
kubectl scale deployment pgbouncer --replicas=10 -n amcis
aws rds modify-db-instance \
  --db-instance-identifier amcis-primary \
  --db-instance-class db.r5.4xlarge \
  --apply-immediately
EOF

# Scale down after event
at "$SCALE_DOWN_TIME" << EOF
kubectl scale deployment amcis-core --replicas=3 -n amcis
kubectl scale deployment pgbouncer --replicas=3 -n amcis
aws rds modify-db-instance \
  --db-instance-identifier amcis-primary \
  --db-instance-class db.r5.xlarge \
  --apply-immediately
EOF

echo "Scaling scheduled"
```

---

## 8. Emergency Scaling

### Rapid Scale-Up
```bash
# Emergency scale - bypass HPA
kubectl scale deployment amcis-core --replicas=50 -n amcis

# Verify
kubectl get pods -n amcis -l app=amcis-core

# Check node capacity
kubectl top nodes
```

### Cluster Autoscaler
```bash
# Check if cluster autoscaler can add nodes
kubectl get nodes

# Check pending pods
kubectl get pods -n amcis --field-selector status.phase=Pending

# Manually add nodes if needed
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name amcis-worker-nodes \
  --desired-capacity 20
```

---

## 9. Scaling Verification

### Performance Testing
```bash
# Run load test
kubectl run -it --rm load-test --image=loadimpact/k6 --restart=Never -- \
  k6 run --vus 1000 --duration 5m - <<EOF
import http from 'k6/http';
export default function () {
  http.get('http://amcis-core.amcis.svc.cluster.local:8080/health/live');
}
EOF
```

### Verify Metrics
```bash
# Check response times
curl http://localhost:9090/api/v1/query?query='histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))'

# Check error rates
curl http://localhost:9090/api/v1/query?query='rate(http_requests_total{status=~"5.."}[5m])'

# Check resource usage
kubectl top pods -n amcis -l app=amcis-core
```

---

## 10. Cost Optimization

### Scale Down After Hours
```bash
# Development environment scaling
crontab << EOF
# Scale down at 8 PM
0 20 * * 1-5 kubectl scale deployment amcis-core --replicas=1 -n amcis --context dev

# Scale up at 7 AM
0 7 * * 1-5 kubectl scale deployment amcis-core --replicas=3 -n amcis --context dev
EOF
```

### Right-Sizing
```bash
# Analyze resource usage
kubectl top pods -n amcis --containers

# Check for over-provisioning
kubectl describe pod amcis-core-xxx -n amcis | grep -A5 "Requests"
```
