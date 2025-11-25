from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update as sql_update
from typing import List, Optional

from app.database import get_db
from app.models import SystemPreference, Clinic
from app.dto.systemPreferences import (
    SystemPreferenceCreate,
    SystemPreferenceUpdate,
    SystemPreferenceRead,
)
from app.auth.dependencies import get_current_user, require_admin
from app.auth.dependencies import UserContext  # if you use it; otherwise current_user is fine

router = APIRouter(prefix="/preferences", tags=["System Preferences"])

# ---------------- Create ----------------
@router.post("/", response_model=SystemPreferenceRead, status_code=201)
async def create_preference(
    payload: SystemPreferenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),  
):
    # validate clinic exists
    clinic_res = await db.execute(select(Clinic).where(Clinic.id == payload.clinic_id))
    clinic = clinic_res.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # check duplicate key per clinic
    q = select(SystemPreference).where(
        SystemPreference.clinic_id == payload.clinic_id,
        SystemPreference.key == payload.key
    )
    res = await db.execute(q)
    existing = res.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Preference key already exists for this clinic")

    pref = SystemPreference(
        clinic_id=payload.clinic_id,
        key=payload.key,
        value=payload.value,
        updated_by=getattr(current_user, "id", None)
    )

    db.add(pref)
    try:
        await db.commit()
        await db.refresh(pref)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error: " + str(e))

    return pref

# ---------------- List by clinic ----------------
@router.get("/", response_model=List[SystemPreferenceRead])
async def list_preferences(
    clinic_id: Optional[int] = Query(None, description="Clinic id (defaults to current admin's clinic)"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    # default to admin's clinic if not provided
    cid = clinic_id if clinic_id is not None else getattr(current_user, "clinic_id", None)
    if cid is None:
        raise HTTPException(status_code=400, detail="clinic_id required")

    q = select(SystemPreference).where(SystemPreference.clinic_id == cid)
    res = await db.execute(q)
    rows = res.scalars().all()
    return rows

# ---------------- Get by id ----------------
@router.get("/{pref_id}", response_model=SystemPreferenceRead)
async def get_preference(pref_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_admin)):
    res = await db.execute(select(SystemPreference).where(SystemPreference.id == pref_id))
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Preference not found")
    # ensure same clinic as admin (recommended)
    if getattr(current_user, "clinic_id", None) is not None and row.clinic_id != current_user.clinic_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return row

# ---------------- Get by key (single) ----------------
@router.get("/by-key/{key}", response_model=SystemPreferenceRead)
async def get_preference_by_key(key: str, clinic_id: Optional[int] = Query(None), db: AsyncSession = Depends(get_db), current_user=Depends(require_admin)):
    cid = clinic_id if clinic_id is not None else getattr(current_user, "clinic_id", None)
    if cid is None:
        raise HTTPException(status_code=400, detail="clinic_id required")

    res = await db.execute(
        select(SystemPreference).where(
            SystemPreference.clinic_id == cid,
            SystemPreference.key == key
        )
    )
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Preference not found")
    return row

# ---------------- Update ----------------
@router.put("/{pref_id}", response_model=SystemPreferenceRead)
async def update_preference(
    pref_id: int,
    payload: SystemPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    res = await db.execute(select(SystemPreference).where(SystemPreference.id == pref_id))
    pref = res.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    # ensure same clinic as admin
    if getattr(current_user, "clinic_id", None) is not None and pref.clinic_id != current_user.clinic_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # if updating key, ensure it doesn't collide with another pref for same clinic
    if payload.key and payload.key != pref.key:
        check_q = select(SystemPreference).where(
            SystemPreference.clinic_id == pref.clinic_id,
            SystemPreference.key == payload.key,
            SystemPreference.id != pref_id
        )
        chk = await db.execute(check_q)
        if chk.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Another preference with this key exists for the clinic")

    if payload.key is not None:
        pref.key = payload.key
    if payload.value is not None:
        pref.value = payload.value

    pref.updated_by = getattr(current_user, "id", None)

    try:
        await db.commit()
        await db.refresh(pref)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error: " + str(e))

    return pref

# ---------------- Delete ----------------
@router.delete("/{pref_id}", status_code=204)
async def delete_preference(pref_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_admin)):
    res = await db.execute(select(SystemPreference).where(SystemPreference.id == pref_id))
    pref = res.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    if getattr(current_user, "clinic_id", None) is not None and pref.clinic_id != current_user.clinic_id:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(pref)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error: " + str(e))
    return None
