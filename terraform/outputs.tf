output "sqs_user_created_queue_url" {
  description = "Set as sqs_user_created_queue_url in config.yaml"
  value       = aws_sqs_queue.user_created.url
}

output "sqs_user_created_queue_arn" {
  value = aws_sqs_queue.user_created.arn
}

output "sns_user_created_topic_arn" {
  description = "Set as sns_user_created_topic_arn in config.yaml"
  value       = aws_sns_topic.user_created.arn
}

output "sns_user_created_topic_name" {
  value = aws_sns_topic.user_created.name
}

# --- IAM ---

output "iam_policy_api_messaging_arn" {
  description = "Standalone policy ARN (attach to another role if not using ecs_api_task_role)"
  value       = aws_iam_policy.api_messaging.arn
}

output "ecs_api_task_role_arn" {
  description = "ECS task role ARN — set as taskRoleArn in the ECS task definition"
  value       = var.create_ecs_task_role ? aws_iam_role.ecs_api_task[0].arn : null
}

output "ecs_api_task_role_name" {
  value = var.create_ecs_task_role ? aws_iam_role.ecs_api_task[0].name : null
}

# --- App Runner / ECR ---

output "ecr_repository_url" {
  description = "docker build -t <this>:latest . && docker push"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_repository_name" {
  value = aws_ecr_repository.api.name
}

output "apprunner_service_id" {
  value       = var.create_apprunner ? aws_apprunner_service.api[0].service_id : null
  description = "App Runner service id"
}

output "apprunner_service_arn" {
  value = var.create_apprunner ? aws_apprunner_service.api[0].arn : null
}

output "apprunner_service_url" {
  description = "Public HTTPS URL of the API"
  value       = var.create_apprunner ? "https://${aws_apprunner_service.api[0].service_url}" : null
}

output "apprunner_ecr_access_role_arn" {
  value = var.create_apprunner ? aws_iam_role.apprunner_ecr_access[0].arn : null
}

output "apprunner_instance_role_arn" {
  value = var.create_apprunner ? aws_iam_role.apprunner_instance[0].arn : null
}
