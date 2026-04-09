import logging

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.s3_events import delete_user_created_json, put_user_created_json
from app.security import hash_password
from app.sns_events import publish_user_created as publish_user_created_sns
from app.sqs_events import publish_user_created

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    s3_key: str | None = None
    try:
        s3_key = put_user_created_json(user)
    except ValueError:
        logger.warning("user create rolled back: S3 bucket not configured user_id=%s", user.id)
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3_USER_CREATED_BUCKET is not configured",
        )
    except (ClientError, BotoCoreError):
        logger.warning("user create rolled back: S3 upload failed user_id=%s", user.id)
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User was not created: failed to save event to S3",
        )
    try:
        publish_user_created(user)
    except ValueError:
        logger.warning("user create rolled back: SQS queue URL not configured user_id=%s", user.id)
        delete_user_created_json(s3_key)
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SQS_USER_CREATED_QUEUE_URL is not configured",
        )
    except (ClientError, BotoCoreError):
        logger.warning("user create rolled back: SQS publish failed user_id=%s", user.id)
        delete_user_created_json(s3_key)
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User was not created: failed to publish event to SQS",
        )
    try:
        publish_user_created_sns(user)
    except ValueError:
        logger.warning("user create rolled back: SNS topic ARN not configured user_id=%s", user.id)
        delete_user_created_json(s3_key)
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SNS_USER_CREATED_TOPIC_ARN is not configured",
        )
    except (ClientError, BotoCoreError):
        logger.warning("user create rolled back: SNS publish failed user_id=%s", user.id)
        delete_user_created_json(s3_key)
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User was not created: failed to publish event to SNS",
        )
    logger.info("user created id=%s", user.id)
    return user


@router.get("", response_model=list[UserRead])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).offset(skip).limit(limit)).all())


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        data["hashed_password"] = hash_password(data.pop("password"))
    if "email" in data:
        other = db.scalar(select(User).where(User.email == data["email"], User.id != user_id))
        if other:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    logger.info("user deleted id=%s", user_id)
    db.delete(user)
    db.commit()
