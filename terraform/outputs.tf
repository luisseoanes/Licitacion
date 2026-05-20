output "api_url" {
  description = "URL pública del dashboard y API REST"
  value       = "http://${aws_instance.api.public_ip}:8000"
}

output "ec2_instance_id" {
  description = "ID de la instancia EC2 (para SSM deploy)"
  value       = aws_instance.api.id
}

output "ec2_public_ip" {
  description = "IP pública de la instancia EC2"
  value       = aws_instance.api.public_ip
}

output "s3_bucket_name" {
  description = "Nombre del bucket S3 (data lake)"
  value       = aws_s3_bucket.data_lake.id
}

output "s3_bucket_arn" {
  description = "ARN del bucket S3"
  value       = aws_s3_bucket.data_lake.arn
}

output "glue_job_name" {
  description = "Nombre del Glue job de clasificación"
  value       = aws_glue_job.clasificacion.name
}

output "iam_role_ec2_arn" {
  description = "ARN del IAM role de EC2"
  value       = aws_iam_role.ec2_role.arn
}

output "iam_role_glue_arn" {
  description = "ARN del IAM role de Glue"
  value       = aws_iam_role.glue_role.arn
}

output "security_group_id" {
  description = "ID del Security Group de la API"
  value       = aws_security_group.api.id
}

output "deploy_command" {
  description = "Comando para redesplegar tras cambios en el código"
  value       = "bash deploy_v2.sh"
}
