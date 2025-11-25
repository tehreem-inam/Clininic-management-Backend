# app/core/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.settings import settings
from app.services import auth_cache
from app.models.schema import Admin, Doctor, Receptionist


from passlib.context import CryptContext
from datetime import datetime, timedelta
import os

# Config / secrets (use env or settings)


security = HTTPBearer()

# Cache helpers
_get_cached_token = auth_cache.get_cached_token
_set_cached_token = auth_cache.set_cached_token
_get_cached_user = auth_cache.get_cached_user
_set_cached_user = auth_cache.set_cached_user

ACCESS_TOKEN_EXPIRE_MINUTES = int(getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))  # default 1 day
SECRET_KEY = getattr(settings, "JWT_SECRET_KEY", None) or os.getenv("JWT_SECRET_KEY", "change-me-in-prod")
ALGORITHM = getattr(settings, "JWT_ALGORITHM", "HS256")
# ------------------ USER CONTEXT ------------------ #
class UserContext(BaseModel):
    name: Optional[str]
    id: int
    email: Optional[str] = None
    role: str
    clinic_id: Optional[int] = None
    active: bool

    class Config:
        from_attributes = True




# ------------------ TOKEN VERIFICATION ------------------ #
def verify_token(token: str) -> dict:
    """Decode JWT with caching support."""

    # --- Cached token ---
    try:
        cached = _get_cached_token(token)
        if cached:
            return cached
    except:
        pass

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        _set_cached_token(token, payload)
        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def validate_and_decode(credentials: HTTPAuthorizationCredentials) -> dict:
    """Full validation for exp + required claims."""
    payload = verify_token(credentials.credentials)

    exp = payload.get("exp")
    if not exp:
        raise HTTPException(401, "Token missing expiration")

    if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(401, "Token expired")

    if not payload.get("sub"):
        raise HTTPException(401, "Invalid token: Missing subject")

    return payload


# ------------------ GET CURRENT USER ------------------ #
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    payload =  validate_and_decode(credentials)
    user_id = int(payload["sub"])
    role = payload["role"]

    model_map = {"admin": Admin, "doctor": Doctor, "receptionist": Receptionist}
    model = model_map.get(role)
    if model is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid role in token")

    stmt = select(model).where(model.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if getattr(user, "status", "active") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account inactive")

    ctx = UserContext(
        name=user.name,
        id=user.id,
        email=getattr(user, "email", None),
        role=role,
        clinic_id=getattr(user, "clinic_id", None),
        active=True
    )
    return ctx


# ------------------ ROLE GUARDS ------------------ #
def require_admin(user: UserContext = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

def require_doctor(user: UserContext = Depends(get_current_user)):
    if user.role != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor access required")
    return user

def require_receptionist(user: UserContext = Depends(get_current_user)):
    if user.role != "receptionist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Receptionist access required")
    return user

def require_admin_or_receptionist(user: UserContext = Depends(get_current_user)):
    if user.role not in ["admin", "receptionist"]:
        raise HTTPException(
            status_code=403,
            detail="Only admins or receptionists are allowed"
        )
    return user
