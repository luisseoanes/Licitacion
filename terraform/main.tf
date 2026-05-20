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

# ── EC2: Servidor de API + módulos diferenciales ─────────────────────────────

resource "aws_security_group" "api" {
  name        = "${var.project_name}-api-sg"
  description = "Acceso publico al dashboard/API (:8000) y SSH para administracion"
  tags        = local.common_tags

  ingress {
    description = "FastAPI / Dashboard React"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH administracion"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role_policy_attachment" "ec2_ssm" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_instance" "api" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids = [aws_security_group.api.id]
  tags                   = merge(local.common_tags, { Name = "${var.project_name}-api" })

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 8
    delete_on_termination = true
  }

  # Bootstrap: instala dependencias, descarga artefactos de S3 y levanta el servicio
  user_data = <<-EOF
    #!/bin/bash
    set -e
    yum update -y
    yum install -y python3 python3-pip

    pip3 install --quiet \
      "fastapi==0.111.0" \
      "uvicorn==0.29.0" \
      "boto3==1.34.0" \
      "pandas==2.2.0" \
      "pyarrow==15.0.0" \
      "scikit-learn==1.4.0" \
      "reportlab==4.1.0"

    mkdir -p /opt/chernovia/static/assets

    BUCKET="${local.bucket_name}"
    REGION="${var.aws_region}"

    for f in main.py clasificador.py clasificador_ml.py detector_anomalias.py generador_reporte.py; do
      aws s3 cp "s3://$BUCKET/deploy/$f" "/opt/chernovia/$f" --region "$REGION"
    done
    aws s3 sync "s3://$BUCKET/deploy/static/" "/opt/chernovia/static/" --region "$REGION"

    cat > /etc/systemd/system/chernovia.service <<UNIT
    [Unit]
    Description=Chernovia Health API
    After=network.target

    [Service]
    User=ec2-user
    WorkingDirectory=/opt/chernovia
    ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    UNIT

    systemctl daemon-reload
    systemctl enable chernovia
    systemctl start chernovia
  EOF
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

