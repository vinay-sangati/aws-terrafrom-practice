import logging
import os
from pathlib import Path
from urllib.parse import quote_plus, urlencode

import yaml
from pydantic import BaseModel, Field

from app.aws_secrets import get_secret_string, resolve_password_from_secret

logger = logging.getLogger(__name__)


class Settings(BaseModel):
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="")
    postgres_password_secret_id: str | None = Field(default=None)
    postgres_password_secret_json_key: str | None = Field(default=None)
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="appdb")
    postgres_ssl_mode: str | None = Field(default=None)

    aws_region: str = Field(default="us-east-1")
    aws_endpoint_url: str | None = Field(default=None)
    sqs_user_created_queue_url: str = Field(default="")
    s3_user_created_bucket: str = Field(default="")
    s3_user_created_prefix: str = Field(default="user-created")
    sns_user_created_topic_arn: str = Field(default="")

    @property
    def database_url(self) -> str:
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        base = (
            f"postgresql://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
        if self.postgres_ssl_mode:
            base = f"{base}?{urlencode({'sslmode': self.postgres_ssl_mode})}"
        return base


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_config_file() -> Path:
    root = _project_root()
    primary = root / "config.yaml"
    if primary.is_file():
        return primary
    fallback = root / "config.example.yaml"
    if fallback.is_file():
        return fallback
    raise FileNotFoundError(
        f"No config file found. Create {primary} (copy from config.example.yaml)."
    )


def _flatten_yaml(raw: dict) -> dict:
    pg = raw.get("postgresql") or raw.get("postgres") or {}
    aws = raw.get("aws") or {}
    pwd = pg.get("password")
    secret_id = pg.get("password_secret_id") or pg.get("password_secret_arn")
    if not pwd and not secret_id:
        raise ValueError(
            "Set postgresql.password (local dev) or postgresql.password_secret_id (AWS Secrets Manager)"
        )
    endpoint = aws.get("endpoint_url")
    ssl_mode = pg.get("ssl_mode") or None
    jkey = pg.get("password_secret_json_key")
    return {
        "postgres_user": pg.get("user", "postgres"),
        "postgres_password": pwd or "",
        "postgres_password_secret_id": secret_id or None,
        "postgres_password_secret_json_key": jkey if jkey else None,
        "postgres_host": pg.get("host", "localhost"),
        "postgres_port": int(pg.get("port", 5432)),
        "postgres_db": pg.get("database", "appdb"),
        "postgres_ssl_mode": ssl_mode,
        "aws_region": aws.get("region", "us-east-1"),
        "aws_endpoint_url": endpoint if endpoint else None,
        "sqs_user_created_queue_url": aws.get("sqs_user_created_queue_url") or "",
        "s3_user_created_bucket": aws.get("s3_user_created_bucket") or "",
        "s3_user_created_prefix": aws.get("s3_user_created_prefix") or "user-created",
        "sns_user_created_topic_arn": aws.get("sns_user_created_topic_arn") or "",
    }


def _apply_env_overrides(flat: dict) -> dict:
    """Docker Compose / ECS can override DB connection and Secrets Manager id."""
    if host := os.environ.get("POSTGRES_HOST"):
        flat["postgres_host"] = host
    if port := os.environ.get("POSTGRES_PORT"):
        flat["postgres_port"] = int(port)
    if ssl_mode := os.environ.get("POSTGRES_SSL_MODE"):
        flat["postgres_ssl_mode"] = ssl_mode
    if sid := os.environ.get("POSTGRES_PASSWORD_SECRET_ID"):
        flat["postgres_password_secret_id"] = sid
    if jkey := os.environ.get("POSTGRES_PASSWORD_SECRET_JSON_KEY"):
        flat["postgres_password_secret_json_key"] = jkey
    if topic := os.environ.get("SNS_USER_CREATED_TOPIC_ARN"):
        flat["sns_user_created_topic_arn"] = topic
    if v := os.environ.get("POSTGRES_USER"):
        flat["postgres_user"] = v
    if v := os.environ.get("POSTGRES_DB"):
        flat["postgres_db"] = v
    if v := os.environ.get("SQS_USER_CREATED_QUEUE_URL"):
        flat["sqs_user_created_queue_url"] = v
    if v := os.environ.get("S3_USER_CREATED_BUCKET"):
        flat["s3_user_created_bucket"] = v
    if v := os.environ.get("S3_USER_CREATED_PREFIX"):
        flat["s3_user_created_prefix"] = v
    if v := os.environ.get("AWS_REGION"):
        flat["aws_region"] = v
    return flat


def load_settings() -> Settings:
    path = _resolve_config_file()
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    flat = _flatten_yaml(raw)
    flat = _apply_env_overrides(flat)
    s = Settings.model_validate(flat)
    if s.postgres_password_secret_id:
        logger.info("Loading DB password from Secrets Manager")
        raw_secret = get_secret_string(
            s.postgres_password_secret_id,
            s.aws_region,
            s.aws_endpoint_url,
        )
        pw = resolve_password_from_secret(raw_secret, s.postgres_password_secret_json_key)
        s = s.model_copy(update={"postgres_password": pw})
    if not s.postgres_password:
        raise ValueError(
            "Database password is empty: set postgresql.password or a valid password_secret_id"
        )
    return s


settings = load_settings()
