from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# ============================================================
# SHARED BASE DTO FOR ALL ROLES
# ============================================================

class UserBase(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    active: Optional[bool] = True
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    role: str


class UserCreate(UserBase):
    email: EmailStr
    password: str


class UserUpdate(UserBase):
    specialization: Optional[str] = None
    phone: Optional[str] = None
    clinic_id: Optional[int] = None
    fee: Optional[float] = None
    max_concurrent_bookings: Optional[int] = None
    pass


class UserRead(UserBase):
    id: int
    specialization: Optional[str] = None
    phone: Optional[str] = None
    clinic_id: Optional[int] = None
    fee: Optional[float] = None
    max_concurrent_bookings: Optional[int] = None
    role: str
    model_config = {"from_attributes": True}

class UserMeRead(UserRead):
    pass


class UserMeUpdate(UserUpdate):
    specialization: Optional[str] = None
    phone: Optional[str] = None
    pass


# ============================================================
# UNIVERSAL AUTH DTOs
# ============================================================



class UserChangePassword(BaseModel):
    old_password: str
    new_password: str


# ============================================================
# ROLE-SPECIFIC EXTRA FIELDS (OPTIONAL)
# ============================================================

class DoctorExtra(BaseModel):
    clinic_id: int
    specialization: Optional[str] = None
    phone: Optional[str] = None
    fee: Optional[float] = None
    status: Optional[str] = "active"
    max_concurrent_bookings: int
class ReceptionistExtra(BaseModel):
    phone: Optional[str] = None
class DoctorCreate(UserCreate, DoctorExtra):
    pass

class ReceptionistCreate(UserCreate, ReceptionistExtra):
    pass
class AdminCreate(UserCreate):
    pass
