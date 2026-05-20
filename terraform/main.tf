terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  bucket_name = "${var.project_name}-${var.bucket_suffix}"
  common_tags = {
    Project     = var.project_name
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# ── S3: Data Lake ─────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "data_lake" {
  bucket = local.bucket_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket                  = aws_s3_bucket.data_lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "archive-old-results"
    status = "Enabled"
    filter { prefix = "results/" }
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# ── IAM: Rol para Glue ────────────────────────────────────────────────────────
resource "aws_iam_role" "glue_role" {
  name = "${var.project_name}-glue-role"
  tags = local.common_tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3" {
  name = "${var.project_name}-glue-s3-policy"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/*",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:/aws-glue/*"
      }
    ]
  })
}

# ── IAM: Rol para EC2 (backend FastAPI) ───────────────────────────────────────
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-ec2-role"
  tags = local.common_tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

resource "aws_iam_role_policy" "ec2_permissions" {
  name = "${var.project_name}-ec2-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/*",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["glue:StartJobRun", "glue:GetJobRun", "glue:GetJob"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData", "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "*"
      }
    ]
  })
}

# ── CloudWatch: Log groups ────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "api" {
  name              = "/chernovia/api"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "glue" {
  name              = "/aws-glue/jobs/${var.glue_job_name}"
  retention_in_days = 30
  tags              = local.common_tags
}

# ── AWS Glue: Job de clasificación ────────────────────────────────────────────
resource "aws_glue_job" "clasificacion" {
  name         = var.glue_job_name
  role_arn     = aws_iam_role.glue_role.arn
  max_capacity = var.glue_max_capacity
  glue_version = "4.0"
  tags         = local.common_tags

  command {
    name            = "glueetl"
    script_location = "s3://${local.bucket_name}/scripts/glue_job.py"
    python_version  = "3"
  }

  default_arguments = {
    "--BUCKET"                       = local.bucket_name
    "--RAW_PREFIX"                   = "raw"
    "--RESULTS_KEY"                  = "results/resultado_clasificacion.parquet"
    "--job-language"                 = "python"
    "--continuous-log-logGroup"      = aws_cloudwatch_log_group.glue.name
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-metrics"               = "true"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "bucket_name" {
  description = "Nombre del bucket S3"
  value       = aws_s3_bucket.data_lake.id
}

output "glue_job_name" {
  description = "Nombre del Glue job"
  value       = aws_glue_job.clasificacion.name
}

output "ec2_instance_profile" {
  description = "Instance profile para el EC2 del backend"
  value       = aws_iam_instance_profile.ec2_profile.name
}
