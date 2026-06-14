import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request

from app.core.auth import hash_password, verify_password, create_access_token
from app.models.account_models import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
)
from app.models.user_model import PasswordReset, User
from app.utils import build_api_response, raise_http

router = APIRouter()

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _validate_username(username: str) -> None:
    if len(username) < 4 or len(username) > 30:
        raise_http(400, "A001", "Username must be 4–30 characters")
    if not _USERNAME_RE.match(username):
        raise_http(400, "A002", "Username may only contain letters, numbers, and underscores")


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise_http(400, "A003", "Password must be at least 8 characters")
    if password.isdigit():
        raise_http(400, "A004", "Password cannot be numbers only")


@router.post("/signup/", status_code=201)
async def signup(body: SignupRequest, request: Request):
    db = request.state.db

    _validate_username(body.username)
    _validate_password(body.password)

    if not _EMAIL_RE.match(body.email):
        raise_http(400, "A005", "Invalid email address")

    if db.query(User).filter(User.username == body.username).first():
        raise_http(409, "A101", "Username already exists")

    if db.query(User).filter(User.email == body.email).first():
        raise_http(409, "A102", "Email already registered")

    user = User(
        username=body.username,
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.flush()

    return build_api_response(
        201, "A001", "Account created successfully",
        data={"user_id": user.id, "username": user.username},
    )


@router.post("/login/")
async def login(body: LoginRequest, request: Request):
    db = request.state.db

    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise_http(401, "A201", "Invalid username or password")

    if not user.is_active:
        raise_http(403, "A202", "Account is inactive")

    token = create_access_token(user.id)

    return build_api_response(
        200, "A001", "Login successful",
        data={"access_token": token, "user_id": user.id, "username": user.username, "role": user.role},
    )


@router.post("/forgot-password/")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    db = request.state.db

    user = db.query(User).filter(User.email == body.email).first()

    # Always return success to prevent email enumeration
    if not user:
        return build_api_response(200, "A001", "If that email exists, a reset link has been sent")

    # Remove any existing reset tokens for this user
    db.query(PasswordReset).filter(PasswordReset.user_id == user.id).delete()

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    db.add(PasswordReset(user_id=user.id, token=token, expires_at=expires_at))

    reset_link = f"http://localhost:3000/reset-password?uid={user.id}&token={token}"
    print(f"\n[PASSWORD RESET] {reset_link}\n")

    return build_api_response(200, "A001", "If that email exists, a reset link has been sent")


@router.post("/reset-password/")
async def reset_password(body: ResetPasswordRequest, request: Request):
    db = request.state.db

    _validate_password(body.password)

    reset = db.query(PasswordReset).filter(
        PasswordReset.user_id == body.uid,
        PasswordReset.token == body.token,
    ).first()

    if not reset:
        raise_http(400, "A301", "Invalid reset token")

    expires_at = reset.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        db.delete(reset)
        raise_http(400, "A302", "Reset token has expired")

    user = db.query(User).filter(User.id == body.uid).first()
    if not user:
        raise_http(404, "A303", "User not found")

    user.hashed_password = hash_password(body.password)
    db.delete(reset)

    return build_api_response(200, "A001", "Password has been reset successfully")
