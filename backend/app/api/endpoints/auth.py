"""
Auth endpoints - register, login, and profile updates.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_required
from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import (
    create_user,
    get_user_by_email,
    get_user_by_username,
    verify_password,
    create_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_MIN_PASSWORD_LENGTH = 6
_MIN_USERNAME_LENGTH = 3


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UpdateEmailNotificationsRequest(BaseModel):
    email_notifications_enabled: bool


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "email_notifications_enabled": getattr(user, "email_notifications_enabled", False),
    }


def _issue_token_response(user: User) -> TokenResponse:
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token, user=_serialize_user(user))


@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    if get_user_by_email(db, request.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if get_user_by_username(db, request.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    if len(request.password) < _MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {_MIN_PASSWORD_LENGTH} characters",
        )
    if len(request.username) < _MIN_USERNAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Username must be at least {_MIN_USERNAME_LENGTH} characters",
        )

    user = create_user(db, request.email, request.username, request.password)
    return _issue_token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return a JWT access token."""
    user = get_user_by_email(db, request.email)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return _issue_token_response(user)


@router.patch("/me")
def update_profile(
    request: UpdateEmailNotificationsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Update user preferences (currently only the email-notifications toggle)."""
    user.email_notifications_enabled = request.email_notifications_enabled
    db.commit()
    db.refresh(user)
    return _serialize_user(user)
