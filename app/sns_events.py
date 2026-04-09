import json
import logging
from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.user_created_payload import build_user_created_payload

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)


def _sns_client():
    kwargs: dict = {"region_name": settings.aws_region}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client("sns", **kwargs)


def publish_user_created(user: "User") -> None:
    topic_arn = settings.sns_user_created_topic_arn.strip()
    if not topic_arn:
        raise ValueError("SNS_USER_CREATED_TOPIC_ARN is not configured")

    message = json.dumps(build_user_created_payload(user), default=str)
    client = _sns_client()
    try:
        client.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject="user.created",
        )
    except (ClientError, BotoCoreError):
        logger.exception("Failed to publish user.created to SNS")
        raise
    logger.info("SNS user.created published user_id=%s", user.id)
