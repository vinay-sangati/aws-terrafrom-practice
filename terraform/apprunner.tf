# ECR repository (push an image before App Runner can start successfully)
resource "aws_ecr_repository" "api" {
  name                 = "${local.base_name}-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# --- App Runner: ECR pull role ---
data "aws_iam_policy_document" "apprunner_ecr_access_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_ecr_access" {
  count              = var.create_apprunner ? 1 : 0
  name               = "${local.base_name}-apprunner-ecr-access"
  assume_role_policy = data.aws_iam_policy_document.apprunner_ecr_access_assume.json
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  count      = var.create_apprunner ? 1 : 0
  role       = aws_iam_role.apprunner_ecr_access[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# --- App Runner: instance role (runtime — same SQS/SNS/Secrets/S3 policy) ---
data "aws_iam_policy_document" "apprunner_instance_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["tasks.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_instance" {
  count              = var.create_apprunner ? 1 : 0
  name               = "${local.base_name}-apprunner-instance"
  assume_role_policy = data.aws_iam_policy_document.apprunner_instance_assume.json
}

resource "aws_iam_role_policy_attachment" "apprunner_instance_messaging" {
  count      = var.create_apprunner ? 1 : 0
  role       = aws_iam_role.apprunner_instance[0].name
  policy_arn = aws_iam_policy.api_messaging.arn
}

locals {
  apprunner_image = "${aws_ecr_repository.api.repository_url}:${var.apprunner_image_tag}"

  apprunner_env = merge(
    {
      AWS_REGION                        = var.aws_region
      POSTGRES_SSL_MODE                 = "require"
      POSTGRES_PASSWORD_SECRET_JSON_KEY = "password"
      POSTGRES_PORT                     = "5432"
      SQS_USER_CREATED_QUEUE_URL        = aws_sqs_queue.user_created.url
      SNS_USER_CREATED_TOPIC_ARN        = aws_sns_topic.user_created.arn
    },
    var.apprunner_rds_host != null && var.apprunner_rds_secret_id != null ? {
      POSTGRES_HOST               = var.apprunner_rds_host
      POSTGRES_PASSWORD_SECRET_ID = var.apprunner_rds_secret_id
      POSTGRES_USER               = var.apprunner_postgres_user
      POSTGRES_DB                 = var.apprunner_postgres_db
    } : {},
    var.s3_bucket_arn != null && var.s3_bucket_arn != "" ? {
      S3_USER_CREATED_BUCKET = replace(var.s3_bucket_arn, "arn:aws:s3:::", "")
      S3_USER_CREATED_PREFIX = "user-created"
    } : {},
    var.apprunner_runtime_environment_variables
  )
}

resource "aws_apprunner_service" "api" {
  count = var.create_apprunner ? 1 : 0

  service_name = "${local.base_name}-api"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access[0].arn
    }

    image_repository {
      image_identifier          = local.apprunner_image
      image_repository_type     = "ECR"
      image_configuration {
        port                          = "8000"
        runtime_environment_variables = local.apprunner_env
      }
    }

    auto_deployments_enabled = var.apprunner_auto_deployments_enabled
  }

  instance_configuration {
    cpu               = var.apprunner_cpu
    memory            = var.apprunner_memory
    instance_role_arn = aws_iam_role.apprunner_instance[0].arn
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  depends_on = [
    aws_iam_role_policy_attachment.apprunner_ecr_access,
    aws_iam_role_policy_attachment.apprunner_instance_messaging,
  ]
}
