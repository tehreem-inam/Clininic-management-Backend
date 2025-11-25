# app/auth/security.py
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta , timezone
import os
from typing import Optional , Dict, Any

# Config / secrets (use env or settings)
from app.settings import settings

# Try to read from settings, fallback to env
SECRET_KEY = getattr(settings, "JWT_SECRET_KEY", None) or os.getenv("JWT_SECRET_KEY", "change-me-in-prod")
ALGORITHM = getattr(settings, "JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))  # default 1 day

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    data: a dict of claims, e.g. {"sub": "8", "role": "admin"}
    DO NOT stringify the dict. sub must be stringable.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp())
    })
    # Ensure subject is a string
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise e

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise
