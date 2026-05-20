variable "project_name" {
  description = "Nombre del proyecto (usado como prefijo en los recursos)"
  type        = string
  default     = "chernovia-health"
}

variable "aws_region" {
  description = "Región AWS"
  type        = string
  default     = "us-east-1"
}

variable "bucket_suffix" {
  description = "Sufijo único para el bucket S3 (ej: ID de cuenta AWS)"
  type        = string
}

variable "glue_job_name" {
  description = "Nombre del AWS Glue job"
  type        = string
  default     = "chernovia-clasificacion-batch"
}

variable "glue_max_capacity" {
  description = "DPUs máximos para el Glue job"
  type        = number
  default     = 8
}
