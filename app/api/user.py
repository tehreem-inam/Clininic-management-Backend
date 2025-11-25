from fastapi import APIRouter, Depends, HTTPException , Query , status
from sqlalchemy.ext.asyncio import AsyncSession 
from app.database import get_db
from app.auth.security import verify_password, get_password_hash
from app.auth.dependencies import get_current_user
from app.models.schema import Admin, Doctor , Receptionist , User
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import Optional

from sqlalchemy import select , or_
from app.dto.user import (
    UserMeRead,
    UserRead,
    UserCreate,
    DoctorCreate,
    AdminCreate,
    ReceptionistCreate,
    UserMeUpdate,
    UserChangePassword,
 
    UserUpdate
)

router = APIRouter(prefix="/user", tags=["User"])
ROLE_MODELS = {
    "admin": Admin,
    "doctor": Doctor,
    "receptionist": Receptionist,
}

async def get_role_instance(db: AsyncSession, role: str, user_id: int):
    """Return role-specific DB object or None"""
    model = ROLE_MODELS.get(role)
    if not model:
        return None
    res = await db.execute(select(model).where(model.id == user_id))
    return res.scalar_one_or_none()



# 1) GET MY PROFILE

@router.get("/me", response_model=UserMeRead)
async def get_my_profile(current_user = Depends(get_current_user)):
    
    return current_user



# 2) UPDATE PROFILE
@router.put("/update", response_model=UserMeRead)
async def update_profile(
    data: UserMeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Update profile for logged-in user.
    Applies updates to BOTH:
      - central User row
      - role-specific row (Admin / Doctor / Receptionist)
    """

    # FETCH CENTRAL USER ENTRY
    q = await db.execute(select(User).where(User.id == current_user.id))
    user_row = q.scalar_one_or_none()

    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    # EMAIL UNIQUE VALIDATION
    if data.email and data.email != user_row.email:
        r = await db.execute(
            select(User).where(User.email == data.email, User.id != user_row.id)
        )
        if r.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")

    # UPDATE CENTRAL USER FIELDS
    if data.name is not None:
        user_row.name = data.name

    if data.email is not None:
        user_row.email = data.email

    if data.active is not None:
        user_row.active = data.active

    if data.last_login_at is not None:
        user_row.last_login_at = data.last_login_at

    if data.deleted_at is not None:
        user_row.deleted_at = data.deleted_at

    # FETCH / CREATE ROLE-SPECIFIC ROW
    role = current_user.role
    role_model = ROLE_MODELS.get(role)

    role_row = None
    if role_model:
        role_row = await get_role_instance(db, role, current_user.id)

    # AUTO CREATE ROLE ROW IF MISSING
    if not role_row:
        pw = user_row.password_hash or ""

        if role == "doctor":
            role_row = Doctor(
                id=user_row.id,
                clinic_id=data.clinic_id or getattr(user_row, "clinic_id", None),
                name=user_row.name,
                email=user_row.email,
                password_hash=pw,
                specialization=data.specialization,
                phone=data.phone,
                fee=data.fee,
                max_concurrent_bookings=data.max_concurrent_bookings or 1,
                status="active"
            )
            db.add(role_row)

        elif role == "receptionist":
            role_row = Receptionist(
                id=user_row.id,
                clinic_id=getattr(user_row, "clinic_id", None),
                name=user_row.name,
                email=user_row.email,
                password_hash=pw,
                phone=data.phone,
                status="active",
            )
            db.add(role_row)

        elif role == "admin":
            role_row = Admin(
                id=user_row.id,
                clinic_id=data.clinic_id or getattr(user_row, "clinic_id", None),
                name=user_row.name,
                email=user_row.email,
                password_hash=pw,
                status="active"
            )
            db.add(role_row)

    # APPLY ROLE-SPECIFIC UPDATES
    if role == "doctor":
        if data.specialization is not None:
            role_row.specialization = data.specialization
        if data.phone is not None:
            role_row.phone = data.phone
        if data.fee is not None:
            role_row.fee = data.fee
        if data.max_concurrent_bookings is not None:
            role_row.max_concurrent_bookings = data.max_concurrent_bookings

    elif role == "receptionist":
        if data.phone is not None:
            role_row.phone = data.phone

    # HANDLE CLINIC ID CHANGE
    if data.clinic_id is not None:

        if role == "receptionist":
            raise HTTPException(status_code=403, detail="Receptionist cannot change clinic")

        # doctor and admin can change clinic
        if hasattr(user_row, "clinic_id"):
            user_row.clinic_id = data.clinic_id

        if hasattr(role_row, "clinic_id"):
            role_row.clinic_id = data.clinic_id

    # SAVE CHANGES
    try:
        await db.commit()
        await db.refresh(role_row)
        return role_row

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")


# 3) CHANGE PASSWORD
@router.put("/change-password")
async def change_password(
    data: UserChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Load actual model (Admin / Doctor / Receptionist)
    model_map = {"admin": Admin, "doctor": Doctor, "receptionist": Receptionist}
    model = model_map[current_user.role]

    # Fetch real DB user (with password_hash)
    stmt = select(model).where(model.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one()

    # Verify old password
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    # Set new password
    user.password_hash = get_password_hash(data.new_password)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating password: {str(e)}")

    return {"message": "Password changed successfully"}

@router.post("/create", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: DoctorCreate | ReceptionistCreate | AdminCreate,
    # Accepts role-specific extras via the DTO
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Create a user (admin only). This creates:
      - a User row (canonical identity)
      - a corresponding role-specific row (Admin/Doctor/Receptionist) with the SAME id
    """
    # Admin guard
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create users")

    if not getattr(data, "role", None):
        raise HTTPException(status_code=400, detail="Role is required")

    role = data.role.lower()
    if role not in ROLE_MODELS:
        raise HTTPException(status_code=400, detail="Invalid role; must be admin/doctor/receptionist")

    # Email unique check in User table
    check = await db.execute(select(User).where(User.email == data.email))
    if check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Build central user
    pw_hash = get_password_hash(data.password)
    new_user = User(
        name=data.name,
        email=data.email,
        role=role,
        active=data.active if data.active is not None else True,
        password_hash=pw_hash,
        last_login_at=getattr(data, "last_login_at", None),
        created_at=getattr(data, "created_at", None),
        updated_at=getattr(data, "updated_at", None),
        deleted_at=getattr(data, "deleted_at", None),
    )

    db.add(new_user)

    # flush so we get new_user.id before creating role row
    try:
        await db.flush()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

    # create role-specific row with same id
    try:
        if role == "doctor":
            doc = Doctor(
                 id=new_user.id,
                clinic_id=data.clinic_id,
                name=data.name,
                email=data.email,
                phone=data.phone,
                specialization=data.specialization,
                fee=data.fee,
                max_concurrent_bookings=data.max_concurrent_bookings or 1,
                status=data.status or "active",
                password_hash=pw_hash,
            )
            db.add(doc)

        elif role == "receptionist":
            rec = Receptionist(
               id=new_user.id,
                clinic_id=data.clinic_id,
                name=data.name,
                email=data.email,
                phone=data.phone,
                password_hash=pw_hash,
                status=data.status or "active",
            )
            db.add(rec)

        elif role == "admin":
            adm = Admin(
                id=new_user.id,
                clinic_id=getattr(data, "clinic_id", None) or None,
                name=data.name or "",
                email=data.email,
                password_hash=pw_hash,
                status= "active"
             
            )
            db.add(adm)

        # Final commit
        await db.commit()
        await db.refresh(new_user)
    except Exception as e:
        await db.rollback()
        # Attempt to clean up partial role row if necessary is handled by DB cascade on rollback
        raise HTTPException(status_code=500, detail=f"Error creating role record: {str(e)}")

    return UserRead.model_validate(new_user)



@router.get("/list", response_model=list[UserRead])
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role: admin/doctor/receptionist"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can list users")

    stmt = select(User)

    if role:
        stmt = stmt.where(User.role == role.lower())
    if active is not None:
        stmt = stmt.where(User.active == active)
    if search:
        q = f"%{search.lower()}%"
        stmt = stmt.where(or_(User.name.ilike(q), User.email.ilike(q)))

    stmt = stmt.limit(limit).offset(offset)
    res = await db.execute(stmt)
    return res.scalars().all()


# -----------------------
# 6) GET USER BY ID
# -----------------------
@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # Admin can view any user; others can view only themselves
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You are not allowed to view this user's data")

    res = await db.execute(select(User).where(User.id == user_id))
    user_row = res.scalar_one_or_none()
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")
    return user_row


# -----------------------
# 7) UPDATE USER BY ID (ADMIN)
# -----------------------
@router.put("/{user_id}", response_model=UserRead)
async def update_user_by_id(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # Only admin can update arbitrary users
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update users")

    res = await db.execute(select(User).where(User.id == user_id))
    user_row = res.scalar_one_or_none()
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = data.dict(exclude_unset=True)

    if "email" in update_data:
        chk = await db.execute(select(User).where(User.email == update_data["email"], User.id != user_id))
        if chk.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")

    # If role is changing, handle role-row swap
    new_role = update_data.get("role")
    old_role = user_row.role

    # update central fields
    for key, value in update_data.items():
        # avoid overwriting password here — separate endpoint exists
        if key == "password":
            continue
        setattr(user_row, key, value)

    user_row.updated_at = datetime.now(timezone.utc)

    # handle role transition
    try:
        if new_role and new_role != old_role:
            new_role = new_role.lower()
            if new_role not in ROLE_MODELS:
                raise HTTPException(status_code=400, detail="Invalid new role")

            # delete old role row (if exists)
            old_model = ROLE_MODELS.get(old_role)
            if old_model:
                old_row = await get_role_instance(db, old_role, user_id)
                if old_row:
                    await db.delete(old_row)

            # create new role row with basic fields (and same id)
            if new_role == "doctor":
                doctor = Doctor(
                    id=user_row.id,
                    clinic_id=getattr(user_row, "clinic_id", None),
                    name=user_row.name or "",
                    email=user_row.email,
                    password_hash=user_row.password_hash or "",
                    specialization=getattr(data, "specialization", None),
                )
                db.add(doctor)
            elif new_role == "receptionist":
                rec = Receptionist(
                    id=user_row.id,
                    clinic_id=getattr(user_row, "clinic_id", None),
                    name=user_row.name or "",
                    email=user_row.email,
                    password_hash=user_row.password_hash or "",
                    phone=getattr(data, "phone", None),
                )
                db.add(rec)
            elif new_role == "admin":
                adm = Admin(
                    id=user_row.id,
                    clinic_id=getattr(user_row, "clinic_id", None),
                    name=user_row.name or "",
                    email=user_row.email,
                    password_hash=user_row.password_hash or "",
                )
                db.add(adm)

            user_row.role = new_role

        # otherwise if role unchanged, apply any role-specific updates (specialization/phone)
        else:
            role_row = await get_role_instance(db, old_role, user_id)
            if role_row:
                if old_role == "doctor" and getattr(data, "specialization", None) is not None:
                    role_row.specialization = data.specialization
                if old_role == "receptionist" and getattr(data, "phone", None) is not None:
                    role_row.phone = data.phone
                if getattr(data, "clinic_id", None) is not None and hasattr(role_row, "clinic_id"):
                    role_row.clinic_id = data.clinic_id

        await db.commit()
        await db.refresh(user_row)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")

    return user_row


# -----------------------
# 8) DELETE USER (ADMIN)
# -----------------------
@router.delete("/{user_id}", status_code=202)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete users")

    res = await db.execute(select(User).where(User.id == user_id))
    user_row = res.scalar_one_or_none()
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    # delete role-specific row if exists
    try:
        role_row = await get_role_instance(db, user_row.role, user_id)
        if role_row:
            await db.delete(role_row)

        await db.delete(user_row)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")

    return {"status": "success", "message": "User deleted"}