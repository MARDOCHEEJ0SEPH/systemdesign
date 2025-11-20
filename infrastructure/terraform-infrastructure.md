# Terraform Infrastructure as Code

## Infrastructure Overview

This document describes the complete infrastructure provisioning using Terraform for the Quantum Financial System.

## Directory Structure

```
terraform/
├── environments/
│   ├── production/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   ├── staging/
│   └── development/
├── modules/
│   ├── eks-cluster/
│   ├── rds-database/
│   ├── elasticache/
│   ├── vpc/
│   ├── security-groups/
│   ├── load-balancer/
│   └── monitoring/
└── global/
    ├── iam/
    ├── route53/
    └── kms/
```

## VPC Module

### modules/vpc/main.tf

```hcl
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-qfs-vpc"
    }
  )
}

resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone = var.availability_zones[count.index]

  tags = merge(
    var.common_tags,
    {
      Name                              = "${var.environment}-private-${var.availability_zones[count.index]}"
      "kubernetes.io/role/internal-elb" = "1"
      "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    }
  )
}

resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index + length(var.availability_zones))
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(
    var.common_tags,
    {
      Name                                        = "${var.environment}-public-${var.availability_zones[count.index]}"
      "kubernetes.io/role/elb"                    = "1"
      "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    }
  )
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-igw"
    }
  )
}

resource "aws_eip" "nat" {
  count  = length(var.availability_zones)
  domain = "vpc"

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-nat-eip-${count.index + 1}"
    }
  )
}

resource "aws_nat_gateway" "main" {
  count         = length(var.availability_zones)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-nat-${count.index + 1}"
    }
  )

  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-private-rt-${count.index + 1}"
    }
  )
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-public-rt"
    }
  )
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
```

## EKS Cluster Module

### modules/eks-cluster/main.tf

```hcl
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.cluster_endpoint_public_access_cidrs
    security_group_ids      = [aws_security_group.cluster.id]
  }

  encryption_config {
    provider {
      key_arn = var.kms_key_arn
    }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  tags = merge(
    var.common_tags,
    {
      Name = var.cluster_name
    }
  )

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
    aws_iam_role_policy_attachment.cluster_AmazonEKSVPCResourceController,
  ]
}

# Node Groups
resource "aws_eks_node_group" "trading_engine" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "trading-engine"
  node_role_arn   = aws_iam_role.node_group.arn
  subnet_ids      = var.private_subnet_ids

  instance_types = ["c5.4xlarge"]

  scaling_config {
    desired_size = 10
    max_size     = 100
    min_size     = 10
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    workload    = "trading"
    performance = "ultra-high"
  }

  taint {
    key    = "workload"
    value  = "trading"
    effect = "NO_SCHEDULE"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.cluster_name}-trading-engine-ng"
    }
  )

  depends_on = [
    aws_iam_role_policy_attachment.node_group_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.node_group_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.node_group_AmazonEC2ContainerRegistryReadOnly,
  ]
}

resource "aws_eks_node_group" "quantum_services" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "quantum-services"
  node_role_arn   = aws_iam_role.node_group.arn
  subnet_ids      = var.private_subnet_ids

  instance_types = ["m5.2xlarge"]

  scaling_config {
    desired_size = 5
    max_size     = 50
    min_size     = 5
  }

  labels = {
    workload    = "quantum"
    performance = "high"
  }

  taint {
    key    = "workload"
    value  = "quantum"
    effect = "NO_SCHEDULE"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.cluster_name}-quantum-services-ng"
    }
  )
}

resource "aws_eks_node_group" "general_services" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "general-services"
  node_role_arn   = aws_iam_role.node_group.arn
  subnet_ids      = var.private_subnet_ids

  instance_types = ["m5.xlarge"]

  scaling_config {
    desired_size = 20
    max_size     = 200
    min_size     = 20
  }

  labels = {
    workload    = "general"
    performance = "standard"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.cluster_name}-general-services-ng"
    }
  )
}

# Cluster Autoscaler
resource "aws_iam_policy" "cluster_autoscaler" {
  name        = "${var.cluster_name}-cluster-autoscaler"
  description = "IAM policy for cluster autoscaler"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeScalingActivities",
          "autoscaling:DescribeTags",
          "ec2:DescribeInstanceTypes",
          "ec2:DescribeLaunchTemplateVersions"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "autoscaling:SetDesiredCapacity",
          "autoscaling:TerminateInstanceInAutoScalingGroup",
          "ec2:DescribeImages",
          "ec2:GetInstanceTypesFromInstanceRequirements",
          "eks:DescribeNodegroup"
        ]
        Resource = "*"
      }
    ]
  })
}
```

## RDS Database Module

### modules/rds-database/main.tf

```hcl
resource "aws_db_subnet_group" "main" {
  name       = "${var.identifier}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(
    var.common_tags,
    {
      Name = "${var.identifier}-subnet-group"
    }
  )
}

resource "aws_db_parameter_group" "main" {
  name   = "${var.identifier}-params"
  family = "postgres15"

  parameter {
    name  = "max_connections"
    value = "1000"
  }

  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/4096}"
  }

  parameter {
    name  = "effective_cache_size"
    value = "{DBInstanceClassMemory/2048}"
  }

  parameter {
    name  = "maintenance_work_mem"
    value = "2097152"  # 2GB
  }

  parameter {
    name  = "random_page_cost"
    value = "1.1"
  }

  parameter {
    name  = "work_mem"
    value = "20971"  # 20MB
  }

  tags = var.common_tags
}

resource "aws_db_instance" "main" {
  identifier     = var.identifier
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "io2"
  iops                  = var.iops
  storage_encrypted     = true
  kms_key_id            = var.kms_key_arn

  db_name  = var.database_name
  username = var.master_username
  password = var.master_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  parameter_group_name   = aws_db_parameter_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  multi_az               = true
  publicly_accessible    = false
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  performance_insights_enabled    = true
  performance_insights_kms_key_id = var.kms_key_arn
  performance_insights_retention_period = 7

  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "${var.identifier}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  tags = merge(
    var.common_tags,
    {
      Name = var.identifier
    }
  )
}

# Read Replica
resource "aws_db_instance" "replica" {
  count              = var.create_read_replica ? var.read_replica_count : 0
  identifier         = "${var.identifier}-replica-${count.index + 1}"
  replicate_source_db = aws_db_instance.main.identifier
  instance_class     = var.replica_instance_class

  storage_encrypted = true
  kms_key_id        = var.kms_key_arn

  publicly_accessible = false
  multi_az            = false

  performance_insights_enabled = true
  performance_insights_kms_key_id = var.kms_key_arn

  tags = merge(
    var.common_tags,
    {
      Name = "${var.identifier}-replica-${count.index + 1}"
    }
  )
}
```

## ElastiCache Redis Module

### modules/elasticache/main.tf

```hcl
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.cluster_id}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = var.common_tags
}

resource "aws_elasticache_parameter_group" "main" {
  name   = "${var.cluster_id}-params"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  parameter {
    name  = "tcp-keepalive"
    value = "300"
  }
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = var.cluster_id
  replication_group_description = "Redis cluster for QFS"
  engine                     = "redis"
  engine_version             = "7.0"
  node_type                  = var.node_type
  port                       = 6379
  parameter_group_name       = aws_elasticache_parameter_group.main.name

  num_cache_clusters         = var.num_cache_nodes
  automatic_failover_enabled = true
  multi_az_enabled           = true

  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled         = true
  auth_token                 = var.auth_token
  kms_key_id                 = var.kms_key_arn

  snapshot_retention_limit = 7
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:07:00"

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_engine_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }

  tags = merge(
    var.common_tags,
    {
      Name = var.cluster_id
    }
  )
}
```

## Production Environment

### environments/production/main.tf

```hcl
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
  }

  backend "s3" {
    bucket         = "qfs-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:us-east-1:ACCOUNT:key/KEY_ID"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "production"
      Project     = "QFS"
      ManagedBy   = "Terraform"
    }
  }
}

# VPC
module "vpc" {
  source = "../../modules/vpc"

  environment        = "production"
  vpc_cidr           = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
  cluster_name       = "qfs-production"
  common_tags        = local.common_tags
}

# EKS Cluster
module "eks" {
  source = "../../modules/eks-cluster"

  cluster_name                          = "qfs-production"
  kubernetes_version                    = "1.28"
  subnet_ids                            = module.vpc.private_subnet_ids
  private_subnet_ids                    = module.vpc.private_subnet_ids
  cluster_endpoint_public_access_cidrs  = var.allowed_cidr_blocks
  kms_key_arn                           = module.kms.key_arn
  common_tags                           = local.common_tags
}

# RDS - Trading Database
module "trading_db" {
  source = "../../modules/rds-database"

  identifier           = "qfs-trading-prod"
  instance_class       = "db.r6g.4xlarge"
  allocated_storage    = 1000
  max_allocated_storage = 5000
  iops                 = 16000
  database_name        = "trading"
  master_username      = "trading_admin"
  master_password      = var.db_master_password
  subnet_ids           = module.vpc.private_subnet_ids
  kms_key_arn          = module.kms.key_arn
  create_read_replica  = true
  read_replica_count   = 3
  replica_instance_class = "db.r6g.2xlarge"
  common_tags          = local.common_tags
}

# ElastiCache Redis
module "redis" {
  source = "../../modules/elasticache"

  cluster_id       = "qfs-redis-prod"
  node_type        = "cache.r6g.2xlarge"
  num_cache_nodes  = 3
  subnet_ids       = module.vpc.private_subnet_ids
  auth_token       = var.redis_auth_token
  kms_key_arn      = module.kms.key_arn
  common_tags      = local.common_tags
}

locals {
  common_tags = {
    Environment = "production"
    Project     = "QFS"
    ManagedBy   = "Terraform"
  }
}
```

### environments/production/variables.tf

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access EKS API"
  type        = list(string)
}

variable "db_master_password" {
  description = "Master password for RDS"
  type        = string
  sensitive   = true
}

variable "redis_auth_token" {
  description = "Auth token for Redis"
  type        = string
  sensitive   = true
}
```

### environments/production/terraform.tfvars

```hcl
aws_region = "us-east-1"

allowed_cidr_blocks = [
  "10.0.0.0/8",      # Internal
  "203.0.113.0/24"   # Office IP
]
```

## Outputs

### environments/production/outputs.tf

```hcl
output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "trading_db_endpoint" {
  description = "Trading database endpoint"
  value       = module.trading_db.db_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = module.redis.redis_endpoint
  sensitive   = true
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}
```

## Deployment Commands

```bash
# Initialize Terraform
terraform init

# Plan infrastructure changes
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan

# Destroy infrastructure (use with caution)
terraform destroy
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-20
