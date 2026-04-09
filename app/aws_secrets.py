import json
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


def get_secret_string(secret_id: str, region: str, endpoint_url: str | None) -> str:
    kwargs: dict = {"region_name": region}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    client = boto3.client("secretsmanager", **kwargs)
    try:
        resp = client.get_secret_value(SecretId=secret_id)
    except (ClientError, BotoCoreError):
        logger.exception("Secrets Manager get_secret_value failed secret_id=%s", secret_id)
        raise
    out = resp.get("SecretString")
    if out is None:
        raise ValueError(f"Secret {secret_id!r} has no SecretString")
    return out


def resolve_password_from_secret(raw: str, json_key: str | None) -> str:
    """If json_key is set, parse JSON and read that key; else use the whole string."""
    raw = raw.strip()
    if not json_key:
        return raw
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and json_key in data:
            return str(data[json_key])
    except json.JSONDecodeError:
        pass
    return raw
