import jwt
from fastapi import Depends, Request

from app.core.auth import decode_access_token
from app.models.user_model import User
from app.utils import raise_http


async def get_current_user(request: Request) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise_http(401, "A401", "Authentication required")
    token = auth.split(" ", 1)[1]
    try:
        user_id = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise_http(401, "A401", "Token has expired")
    except Exception:
        raise_http(401, "A401", "Invalid token")

    db = request.state.db
    if db is None:
        raise_http(500, "DB_ERROR", "Database not available")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise_http(401, "A401", "User not found or inactive")
    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise_http(403, "A403", "Admin access required")
    return user
