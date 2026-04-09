provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      {
        Project     = var.name_prefix
        Environment = var.environment
        ManagedBy   = "terraform"
      },
      var.tags
    )
  }
}

locals {
  base_name = "${var.name_prefix}-${var.environment}"
}

# --- SQS: user.created queue (app sends via SendMessage) ---
resource "aws_sqs_queue" "user_created" {
  name                       = "${local.base_name}-user-created"
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds
  message_retention_seconds  = var.sqs_message_retention_seconds
  receive_wait_time_seconds  = 0

  sqs_managed_sse_enabled = true
}

# --- SNS: user.created topic (app publishes JSON) ---
resource "aws_sns_topic" "user_created" {
  name = "${local.base_name}-user-created"
}
