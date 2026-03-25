module "rds" {
  source  = "terraform-aws-modules/rds-aurora/aws"
  version = "~> 8.0"

  name           = "amcis-db-${var.environment}"
  engine         = "aurora-postgresql"
  engine_version = "15.3"
  instance_class = "db.serverless"

  instances = {
    one = {}
    two = {}
  }

  vpc_id               = module.vpc.vpc_id
  db_subnet_group_name = module.vpc.database_subnet_group_name
  security_group_rules = {
    ex_in = {
      type        = "ingress"
      from_port   = 5432
      to_port     = 5432
      protocol    = "tcp"
      cidr_blocks = [module.vpc.vpc_cidr_block]
    }
  }

  storage_encrypted = true
  apply_immediately = true
  monitoring_interval = 10

  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = {
    Environment = var.environment
    Terraform   = "true"
  }
}
