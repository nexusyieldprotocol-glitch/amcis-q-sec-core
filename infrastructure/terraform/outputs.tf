output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "EKS Cluster Name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS Cluster Endpoint"
  value       = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  description = "RDS Endpoint"
  value       = module.rds.cluster_endpoint
}

output "redis_endpoint" {
  description = "Redis Endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}
