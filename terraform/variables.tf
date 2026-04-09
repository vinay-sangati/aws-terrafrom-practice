variable "aws_region" {
  type        = string
  description = "AWS region (e.g. us-east-1)"
  default     = "us-east-1"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource names (e.g. commerce-api)"
  default     = "commerce-api"
}

variable "environment" {
  type        = string
  description = "Environment tag (e.g. dev, prod)"
  default     = "dev"
}

variable "sqs_visibility_timeout_seconds" {
  type        = number
  description = "SQS visibility timeout (seconds)"
  default     = 60
}

variable "sqs_message_retention_seconds" {
  type        = number
  description = "SQS message retention (seconds)"
  default     = 345600 # 4 days
}

variable "tags" {
  type        = map(string)
  description = "Extra tags for all resources"
  default     = {}
}

# --- IAM ---

variable "create_ecs_task_role" {
  type        = bool
  description = "Create an IAM role for ECS tasks (taskRoleArn) with SQS/SNS (+ optional S3/Secrets) permissions"
  default     = true
}

variable "secretsmanager_secret_arns" {
  type        = list(string)
  description = "Secrets Manager secret ARNs for GetSecretValue (e.g. RDS master secret)"
  default     = []
}

variable "s3_bucket_arn" {
  type        = string
  description = "S3 bucket ARN for user-created JSON (s3:PutObject/DeleteObject on bucket/*). Set null to skip."
  default     = null
}

# --- App Runner ---

variable "create_apprunner" {
  type        = bool
  description = "Create ECR repo (always) + App Runner service + roles. Set false to only manage messaging IAM/SQS/SNS."
  default     = true
}

variable "apprunner_image_tag" {
  type        = string
  description = "ECR image tag the service runs (push this tag before first successful deploy)"
  default     = "latest"
}

variable "apprunner_cpu" {
  type        = string
  description = "App Runner vCPU (e.g. 1024 = 1 vCPU)"
  default     = "1024"
}

variable "apprunner_memory" {
  type        = string
  description = "App Runner memory in MB (e.g. 2048)"
  default     = "2048"
}

variable "apprunner_auto_deployments_enabled" {
  type        = bool
  description = "Auto-deploy when new images are pushed to ECR"
  default     = true
}

variable "apprunner_rds_host" {
  type        = string
  description = "Aurora/RDS writer endpoint (no port). If null, set DB via apprunner_runtime_environment_variables."
  default     = null
}

variable "apprunner_rds_secret_id" {
  type        = string
  description = "Secrets Manager secret id or ARN for DB password (same as config password_secret_id). If null, set via apprunner_runtime_environment_variables."
  default     = null
}

variable "apprunner_postgres_user" {
  type    = string
  default = "postgres"
}

variable "apprunner_postgres_db" {
  type    = string
  default = "appdb"
}

variable "apprunner_runtime_environment_variables" {
  type        = map(string)
  description = "Extra env vars merged into App Runner (override or add keys)"
  default     = {}
}
