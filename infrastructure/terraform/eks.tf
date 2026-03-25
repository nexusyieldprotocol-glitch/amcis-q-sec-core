module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = true

  eks_managed_node_groups = {
    critical = {
      min_size     = 2
      max_size     = 5
      desired_size = 2

      instance_types = ["m5.large"]
      capacity_type  = "ON_DEMAND"
      
      labels = {
        role = "system"
      }
    }

    workers = {
      min_size     = 1
      max_size     = 10
      desired_size = 2

      instance_types = ["m5.xlarge"]
      capacity_type  = "SPOT"

      labels = {
        role = "worker"
      }
    }
  }

  tags = {
    Environment = var.environment
    Terraform   = "true"
  }
}

resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = module.eks.cluster_iam_role_name
}
