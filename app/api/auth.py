from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user

from sqlalchemy import select,func
from app.database import get_db
from app.auth import security
from app.dto.auth import (
    AdminRegisterRequest, LoginRequest , AdminResponse,
    UserLoginResponse,
    ReceptionistRegisterRequest, ReceptionistResponse,
    DoctorRegisterRequest, DoctorResponse,
    LogoutResponse
)
from app.models.schema import Admin, Receptionist, Doctor , Clinic
from datetime import timedelta
from app.auth.security import create_access_token , get_password_hash ,verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------- Admin ---------------- #
@router.post("/admin/register", response_model=AdminResponse)
async def register_admin(data: AdminRegisterRequest, db: AsyncSession = Depends(get_db)):
    # Normalize email
    email = data.email.strip().lower()

    # Check duplicate email
    result = await db.execute(
        select(Admin).filter(func.lower(Admin.email) == email)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Extract clinic_id correctly (Pydantic model → attribute)
    clinic_id = data.clinic_id

    # If clinic_id provided → validate it
    if clinic_id is not None:
        res = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
        if not res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Clinic does not exist")
    else:
        clinic_id = None  # admin can be created without clinic

    hashed_pw = get_password_hash(data.password)

    admin = Admin(
        name=data.name,
        email=email,
        password_hash=hashed_pw,
        role="admin",
        clinic_id=clinic_id,
        status="active"
    )

    db.add(admin)

    try:
        await db.commit()
        await db.refresh(admin)
    except Exception as e:
        await db.rollback()
        print("DB Error:", e)
        raise HTTPException(status_code=500, detail="Database error")

    return admin


@router.post("/admin/login", response_model=UserLoginResponse)
async def admin_login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = data.email.strip().lower()

    # get admin by email
    result = await db.execute(
        select(Admin).filter(func.lower(Admin.email) == email)
    )
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # verify password
    if not verify_password(data.password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # generate token
    access_token = create_access_token({"sub": str(admin.id),
    "role": "admin"})

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": admin.id,
            "name": admin.name,
            "email": admin.email,
            "role": "admin",
            "clinic_id": admin.clinic_id,
            "status": admin.status
        }
    }


# ---------------- Receptionist ---------------- #
@router.post("/receptionist/register", response_model=ReceptionistResponse)
async def register_receptionist(data: ReceptionistRegisterRequest, db: AsyncSession = Depends(get_db)):

    email = data.email.strip().lower()

    # Check duplicate email
    result = await db.execute(
        select(Receptionist).filter(func.lower(Receptionist.email) == email)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate clinic
    res = await db.execute(select(Clinic).where(Clinic.id == data.clinic_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Clinic does not exist")

    hashed_pw = get_password_hash(data.password)

    receptionist = Receptionist(
        name=data.name,
        email=email,
        password_hash=hashed_pw,
        phone=data.phone,
        clinic_id=data.clinic_id,
        status="active"
    )

    db.add(receptionist)

    try:
        await db.commit()
        await db.refresh(receptionist)
    except:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error")

    return receptionist


@router.post("/receptionist/login", response_model=UserLoginResponse)
async def receptionist_login(data: LoginRequest, db: AsyncSession = Depends(get_db)):

    email = data.email.strip().lower()

    result = await db.execute(select(Receptionist).filter(func.lower(Receptionist.email) == email))
    receptionist = result.scalar_one_or_none()

    if not receptionist or not verify_password(data.password, receptionist.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    token = create_access_token({"sub": receptionist.id, "role": "receptionist"})

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": receptionist.id,
            "name": receptionist.name,
            "email": receptionist.email,
            "role": "receptionist",
            "clinic_id": receptionist.clinic_id,
            "phone": receptionist.phone,
            "status": receptionist.status
        }
    }

# ---------------- Doctor ---------------- #
@router.post("/doctor/register", response_model=DoctorResponse)
async def register_doctor(data: DoctorRegisterRequest, db: AsyncSession = Depends(get_db)):

    email = data.email.strip().lower()

    # Check duplicate email
    result = await db.execute(
        select(Doctor).filter(func.lower(Doctor.email) == email)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate clinic
    res = await db.execute(select(Clinic).where(Clinic.id == data.clinic_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Clinic does not exist")

    hashed_pw = get_password_hash(data.password)

    doctor = Doctor(
        name=data.name,
        email=email,
        password_hash=hashed_pw,
        specialization=data.specialization,
        phone=data.phone,
        clinic_id=data.clinic_id,
        fee=data.fee,
        plan_id=data.plan_id,
        status="active",
    )

    db.add(doctor)

    try:
        await db.commit()
        await db.refresh(doctor)
    except:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error")

    return doctor


@router.post("/doctor/login", response_model=UserLoginResponse)
async def doctor_login(data: LoginRequest, db: AsyncSession = Depends(get_db)):

    email = data.email.strip().lower()

    result = await db.execute(select(Doctor).filter(func.lower(Doctor.email) == email))
    doctor = result.scalar_one_or_none()

    if not doctor or not verify_password(data.password, doctor.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    token = create_access_token({"sub": doctor.id, "role": "doctor"})

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": doctor.id,
            "name": doctor.name,
            "email": doctor.email,
            "role": "doctor",
            "clinic_id": doctor.clinic_id,
            "specialization": doctor.specialization,
            "phone": doctor.phone,
            "fee": doctor.fee,
            "status": doctor.status
        }
    }



#--------------logout-----------------#
@router.post("/logout", response_model=LogoutResponse)
async def logout(current_user=Depends(get_current_user)):
    return LogoutResponse(message="Logged out successfully")
