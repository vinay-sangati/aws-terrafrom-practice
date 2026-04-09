# IAM policy: app publishes to SQS + SNS; optional Secrets Manager + S3 (matches Python app)

data "aws_iam_policy_document" "ecs_task_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "api_messaging" {
  statement {
    sid    = "SQSUserCreated"
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
    ]
    resources = [aws_sqs_queue.user_created.arn]
  }

  statement {
    sid    = "SNSUserCreated"
    effect = "Allow"
    actions = [
      "sns:Publish",
    ]
    resources = [aws_sns_topic.user_created.arn]
  }

  dynamic "statement" {
    for_each = length(var.secretsmanager_secret_arns) > 0 ? [1] : []
    content {
      sid    = "SecretsManagerRead"
      effect = "Allow"
      actions = [
        "secretsmanager:GetSecretValue",
      ]
      resources = var.secretsmanager_secret_arns
    }
  }

  dynamic "statement" {
    for_each = var.s3_bucket_arn != null && var.s3_bucket_arn != "" ? [1] : []
    content {
      sid    = "S3UserCreatedObjects"
      effect = "Allow"
      actions = [
        "s3:PutObject",
        "s3:DeleteObject",
      ]
      resources = ["${var.s3_bucket_arn}/*"]
    }
  }
}

resource "aws_iam_policy" "api_messaging" {
  name        = "${local.base_name}-api-messaging"
  description = "SQS/SNS for user.created; optional Secrets Manager + S3"
  policy      = data.aws_iam_policy_document.api_messaging.json
}

resource "aws_iam_role" "ecs_api_task" {
  count              = var.create_ecs_task_role ? 1 : 0
  name               = "${local.base_name}-api-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_api_messaging" {
  count      = var.create_ecs_task_role ? 1 : 0
  role       = aws_iam_role.ecs_api_task[0].name
  policy_arn = aws_iam_policy.api_messaging.arn
}
