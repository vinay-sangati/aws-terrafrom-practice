import json
import logging
from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)


def _sqs_client():
    kwargs: dict = {"region_name": settings.aws_region}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client("sqs", **kwargs)


def publish_user_created(user: "User") -> None:
    queue_url = settings.sqs_user_created_queue_url.strip()
    if not queue_url:
        raise ValueError("SQS_USER_CREATED_QUEUE_URL is not configured")

    body = json.dumps(
        {
            "event": "user.created",
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        default=str,
    )
    client = _sqs_client()
    try:
        client.send_message(QueueUrl=queue_url, MessageBody=body)
    except (ClientError, BotoCoreError):
        logger.exception("Failed to publish user.created to SQS")
        raise
