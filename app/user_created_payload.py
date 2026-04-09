from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.user import User


def build_user_created_payload(user: "User") -> dict[str, Any]:
    return {
        "event": "user.created",
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
