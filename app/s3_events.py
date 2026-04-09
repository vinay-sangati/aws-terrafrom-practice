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


def _s3_client():
    kwargs: dict = {"region_name": settings.aws_region}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client("s3", **kwargs)


def _user_created_object_key(user_id: int) -> str:
    prefix = settings.s3_user_created_prefix.strip().strip("/")
    if not prefix:
        prefix = "user-created"
    return f"{prefix}/{user_id}.json"


def put_user_created_json(user: "User") -> str:
    bucket = settings.s3_user_created_bucket.strip()
    if not bucket:
        raise ValueError("S3_USER_CREATED_BUCKET is not configured")

    key = _user_created_object_key(user.id)
    payload = build_user_created_payload(user)
    body = json.dumps(payload, indent=2, default=str).encode("utf-8")
    client = _s3_client()
    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json; charset=utf-8",
        )
    except (ClientError, BotoCoreError):
        logger.exception("Failed to upload user.created JSON to S3 user_id=%s", user.id)
        raise
    logger.info("S3 user.created object written bucket=%s key=%s", bucket, key)
    return key


def delete_user_created_json(key: str) -> None:
    bucket = settings.s3_user_created_bucket.strip()
    if not bucket or not key:
        return
    client = _s3_client()
    try:
        client.delete_object(Bucket=bucket, Key=key)
        logger.info("S3 user.created object removed key=%s (rollback)", key)
    except (ClientError, BotoCoreError):
        logger.exception("Failed to delete S3 object during rollback key=%s", key)
