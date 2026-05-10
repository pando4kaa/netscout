"""
Auth service - JWT tokens, password hashing, user management.
"""

from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.db.models import User
from src.config.settings import JWT_SECRET

if not JWT_SECRET:
    # Fail fast at import time so we never sign tokens with an empty key.
    raise RuntimeError("JWT_SECRET is not set; refusing to start auth service.")

SECRET_KEY: str = JWT_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# bcrypt rejects passwords longer than 72 bytes; truncate consistently.
_BCRYPT_PASSWORD_LIMIT = 72


def _truncate_password(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_PASSWORD_LIMIT]


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_truncate_password(plain), hashed.encode("utf-8"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(_truncate_password(password), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, email: str, username: str, password: str) -> User:
    user = User(email=email, username=username, hashed_password=get_password_hash(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
