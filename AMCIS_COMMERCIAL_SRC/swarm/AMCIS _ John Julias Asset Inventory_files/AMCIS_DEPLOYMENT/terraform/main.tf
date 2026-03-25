################################################################################
# AMCIS TERRAFORM INFRASTRUCTURE
# Version: 2026.03.07
# Description: Production infrastructure for AMCIS ecosystem
################################################################################

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
  
  backend "s3" {
    bucket         = "amcis-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "amcis-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "AMCIS"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Version     = "2026.03.07"
    }
  }
}

################################################################################
# VPC & NETWORKING
################################################################################

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.1.0"
  
  name = "amcis-${var.environment}-vpc"
  cidr = var.vpc_cidr
  
  azs             = var.availability_zones
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs
  
  enable_nat_gateway     = true
  single_nat_gateway     = var.environment != "production"
  enable_dns_hostnames   = true
  enable_dns_support     = true
  
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
    Type                     = "Public"
  }
  
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    Type                              = "Private"
  }
  
  tags = {
    Name = "amcis-${var.environment}-vpc"
  }
}

################################################################################
# EKS CLUSTER
################################################################################

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.17.0"
  
  cluster_name    = "amcis-${var.environment}"
  cluster_version = "1.28"
  
  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  control_plane_subnet_ids       = module.vpc.private_subnets
  
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true
  
  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  
  # EKS Managed Node Groups
  eks_managed_node_groups = {
    general = {
      name           = "general-workloads"
      instance_types = ["m6i.xlarge"]
      
      min_size     = 3
      max_size     = 10
      desired_size = 3
      
      capacity_type = "ON_DEMAND"
      
      labels = {
        workload = "general"
      }
      
      update_config = {
        max_unavailable_percentage = 25
      }
      
      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = 100
            volume_type           = "gp3"
            iops                  = 3000
            throughput            = 125
            encrypted             = true
            delete_on_termination = true
          }
        }
      }
    }
    
    compute = {
      name           = "compute-intensive"
      instance_types = ["c6i.2xlarge"]
      
      min_size     = 2
      max_size     = 8
      desired_size = 2
      
      capacity_type = "ON_DEMAND"
      
      labels = {
        workload = "compute"
      }
      
      taints = [{
        key    = "dedicated"
        value  = "compute"
        effect = "NO_SCHEDULE"
      }]
    }
    
    spot = {
      name           = "spot-workloads"
      instance_types = ["m6i.large", "m5.large", "m5a.large"]
      
      min_size     = 0
      max_size     = 10
      desired_size = 2
      
      capacity_type = "SPOT"
      
      labels = {
        workload = "spot"
      }
      
      taints = [{
        key    = "spot"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }
  
  # Fargate Profiles for serverless workloads
  fargate_profiles = {
    monitoring = {
      name = "monitoring"
      selectors = [
        { namespace = "amcis-monitoring" }
      ]
      subnet_ids = module.vpc.private_subnets
    }
  }
  
  # Add-ons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
    amazon-cloudwatch-observability = {
      most_recent = true
    }
  }
  
  tags = {
    Name = "amcis-${var.environment}-eks"
  }
}

################################################################################
# RDS POSTGRESQL
################################################################################

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "6.3.0"
  
  identifier = "amcis-${var.environment}-postgres"
  
  engine               = "postgres"
  engine_version       = "15.4"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = var.db_instance_class
  
  allocated_storage     = 100
  max_allocated_storage = 500
  storage_encrypted     = true
  
  db_name  = "amcis_enterprise"
  username = "amcis_admin"
  port     = 5432
  
  multi_az               = var.environment == "production"
  db_subnet_group_name   = module.vpc.database_subnet_group
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  maintenance_window = "Mon:03:00-Mon:04:00"
  backup_window      = "04:00-05:00"
  backup_retention_period = var.environment == "production" ? 30 : 7
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  create_cloudwatch_log_group     = true
  
  skip_final_snapshot = var.environment != "production"
  deletion_protection = var.environment == "production"
  
  performance_insights_enabled    = true
  performance_insights_retention_period = 7
  
  tags = {
    Name = "amcis-${var.environment}-postgres"
  }
}

################################################################################
# ELASTICACHE REDIS
################################################################################

module "elasticache" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "1.0.0"
  
  cluster_id = "amcis-${var.environment}-redis"
  
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.redis_node_type
  num_cache_nodes      = var.environment == "production" ? 3 : 1
  
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled          = var.environment == "production"
  
  snapshot_retention_limit = var.environment == "production" ? 7 : 1
  snapshot_window         = "05:00-06:00"
  maintenance_window      = "sun:03:00-sun:04:00"
  
  tags = {
    Name = "amcis-${var.environment}-redis"
  }
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "amcis-${var.environment}-redis-subnet"
  subnet_ids = module.vpc.private_subnets
}

################################################################################
# SECURITY GROUPS
################################################################################

resource "aws_security_group" "rds" {
  name_prefix = "amcis-${var.environment}-rds-"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "PostgreSQL from VPC"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "amcis-${var.environment}-rds"
  }
}

resource "aws_security_group" "redis" {
  name_prefix = "amcis-${var.environment}-redis-"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Redis from VPC"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "amcis-${var.environment}-redis"
  }
}

################################################################################
# S3 BUCKETS
################################################################################

resource "aws_s3_bucket" "amcis_assets" {
  bucket = "amcis-${var.environment}-assets-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "amcis_assets" {
  bucket = aws_s3_bucket.amcis_assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "amcis_assets" {
  bucket = aws_s3_bucket.amcis_assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "amcis_assets" {
  bucket = aws_s3_bucket.amcis_assets.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

################################################################################
# IAM ROLES
################################################################################

resource "aws_iam_role" "amcis_service" {
  name = "amcis-${var.environment}-service-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "amcis_service_policies" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
  ])
  
  policy_arn = each.value
  role       = aws_iam_role.amcis_service.name
}

################################################################################
# DATA SOURCES
################################################################################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
