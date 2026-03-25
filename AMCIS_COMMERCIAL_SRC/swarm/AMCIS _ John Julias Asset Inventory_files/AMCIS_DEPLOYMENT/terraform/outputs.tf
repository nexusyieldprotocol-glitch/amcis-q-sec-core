################################################################################
# AMCIS TERRAFORM OUTPUTS
# Version: 2026.03.07
################################################################################

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = false
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = false
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.elasticache.cluster_endpoint
  sensitive   = false
}

output "s3_bucket" {
  description = "AMCIS assets S3 bucket"
  value       = aws_s3_bucket.amcis_assets.bucket
}

output "kubeconfig_command" {
  description = "Command to update kubeconfig"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "deployment_summary" {
  description = "Deployment summary"
  value = <<EOF
================================================================================
AMCIS INFRASTRUCTURE DEPLOYMENT COMPLETE
================================================================================

Cluster:        ${module.eks.cluster_name}
Endpoint:       ${module.eks.cluster_endpoint}
Region:         ${var.aws_region}
Environment:    ${var.environment}

Database:       ${module.rds.db_instance_endpoint}
Cache:          ${module.elasticache.cluster_endpoint}
Storage:        ${aws_s3_bucket.amcis_assets.bucket}

To access the cluster:
  ${"aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"}

To deploy AMCIS:
  kubectl apply -f ../k8s/

================================================================================
EOF
}
