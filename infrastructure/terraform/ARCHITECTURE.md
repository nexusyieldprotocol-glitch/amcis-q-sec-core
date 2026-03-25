# 🏗️ AWS TERRAFORM ARCHITECTURE (G2)

**Version:** 1.0.0  
**Status:** DRAFT  
**Owner:** Gemini (Antigravity IDE)

---

## ☁️ CLOUD PROVIDER: AWS
- **Region:** `us-east-1` (Primary), `us-west-2` (DR)
- **Framework:** Terraform 1.5+

---

## 🛡️ NETWORKING (VPC)
- **VPC CIDR:** `10.0.0.0/16`
- **Subnets:**
  - **Public (2x):** Managed NAT Gateways, ALB/GLB
  - **Private (2x):** EKS Worker Nodes, RDS, ElastiCache
- **High Availability:** Multi-AZ deployment (2 AZs minimum)
- **Security:** Security Groups for least-privilege access

---

## 🚢 COMPUTE (EKS)
- **Cluster Name:** `amcis-qsec-core`
- **Kubernetes Version:** `1.28`
- **Node Groups:**
  - **System Nodes:** Managed Node Group (m5.large, 3 nodes)
  - **Worker Nodes:** Spot instances where appropriate (m5.xlarge)
- **Add-ons:**
  - `vpc-cni`
  - `kube-proxy`
  - `coredns`
  - `aws-ebs-csi-driver`

---

## 🗄️ DATA STORES
### RDS (PostgreSQL)
- **Engine:** Aurora PostgreSQL (Serverless v2)
- **Instance Type:** `db.serverless`
- **Multi-AZ:** Yes
- **Encryption:** KMS-managed (AES-256)
- **Backup:** Automated snapshots (7 days retention)

### ElastiCache (Redis)
- **Engine:** Redis (Self-managed on Private Subnet or AWS Managed)
- **Replication:** Multi-AZ with Automatic Failover
- **Purpose:** Session data, caching, real-time metrics

---

## 🔐 SECURITY & COMPLIANCE
- **Secrets Management:** Integrated with HashiCorp Vault (already implemented by Kimi)
- **IAM:** OIDC Federation for EKS Service Accounts (IRSA)
- **Compliance:** NIST CSF 2.0 alignment (Automated auditing checks)
- **Monitoring:** CloudWatch Logs + Prometheus/Grafana

---

## 🛣️ DEPLOYMENT STRATEGY
- **Infrastructure as Code (IaC):** Automated via GitHub Actions
- **State Management:** S3 Backend with DynamoDB Locking
- **Environments:** `dev`, `staging`, `prod` (Workspaces)

---

## 📈 COST ESTIMATE (ESTIMATED)
| Resource | Count | Monthly Cost (Est) |
|----------|-------|--------------------|
| VPC/NAT  | 1 | $35 |
| EKS Control Plane | 1 | $73 |
| EKS Nodes (System) | 3 | $200 |
| RDS Aurora v2 | 1 | $150 |
| ElastiCache | 1 | $45 |
| **TOTAL** | | **$503/mo** |

---

## 📝 HANDOFF NOTES FOR KIMI
1. Implement `providers.tf` with S3 backend support.
2. Ensure VPC subnets are tagged for EKS (`kubernetes.io/role/internal-elb` and `kubernetes.io/role/elb`).
3. Use IRSA for all pod-to-AWS communication.
4. Integrate with the existing Vault secret manager.
