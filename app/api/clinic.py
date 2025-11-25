from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.schema import Clinic
from app.models.schema import Doctor , Receptionist , User
from app.database import get_db

from app.dto.clinic import (
    ClinicCreate, ClinicUpdate, ClinicRead, ClinicBranch
)

router = APIRouter(prefix="/clinic", tags=["Clinic"])
@router.post("/", response_model=ClinicRead, status_code=201)
async def create_clinic(payload: ClinicCreate, db: AsyncSession = Depends(get_db)):
    
    clinic = Clinic(**payload.model_dump())
    db.add(clinic)
    await db.commit()
    await db.refresh(clinic)

    # load branches
    branches = await db.execute(
        select(Clinic).where(Clinic.parent_id == clinic.id)
    )
    
    clinic.branches = branches.scalars().all()

    return clinic

@router.put("/{clinic_id}", response_model=ClinicRead)
async def update_clinic(clinic_id: int, payload: ClinicUpdate, db: AsyncSession = Depends(get_db)):

    q = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = q.scalar_one_or_none()

    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(clinic, field, value)

    await db.commit()
    await db.refresh(clinic)

    branches = await db.execute(
        select(Clinic).where(Clinic.parent_id == clinic.id)
    )
    clinic.branches = branches.scalars().all()

    return clinic
@router.get("/{clinic_id}", response_model=ClinicRead)
async def get_clinic_by_id(clinic_id: int, db: AsyncSession = Depends(get_db)):

    q = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = q.scalar_one_or_none()

    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    branches = await db.execute(
        select(Clinic).where(Clinic.parent_id == clinic.id)
    )
    clinic.branches = branches.scalars().all()

    return clinic
@router.get("/", response_model=list[ClinicRead])
async def get_all_clinics(db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(Clinic))
    clinics = result.scalars().all()

    clinic_map = {c.id: c for c in clinics}

    # Attach branches
    for clinic in clinics:
        if clinic.parent_id:
            parent = clinic_map.get(clinic.parent_id)
            if parent:
                if not hasattr(parent, "branches"):
                    parent.branches = []
                parent.branches.append(clinic)

    # Only return parent/root clinics
    return [c for c in clinics if c.parent_id is None]
@router.delete("/{clinic_id}", status_code=204)
async def delete_clinic(clinic_id: int, db: AsyncSession = Depends(get_db)):

    q = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = q.scalar_one_or_none()

    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    await db.delete(clinic)
    await db.commit()

    return None
@router.put("/{clinic_id}/assign-doctor/{doctor_id}", status_code=200)
async def assign_doctor_to_clinic(
    clinic_id: int,
    doctor_id: int,
    db: AsyncSession = Depends(get_db)
):

    # 1. Check clinic exists
    clinic = await db.scalar(select(Clinic).where(Clinic.id == clinic_id))
    if not clinic:
        raise HTTPException(404, "Clinic not found")

    # 2. Check doctor exists
    doctor = await db.scalar(select(Doctor).where(Doctor.id == doctor_id))
    if not doctor:
        raise HTTPException(404, "Doctor not found")

    # 3. Assign
    doctor.clinic_id = clinic_id
    await db.commit()
    await db.refresh(doctor)

    return {
        "message": "Doctor assigned successfully",
        "doctor_id": doctor.id,
        "clinic_id": clinic.id
    }

@router.put("/{clinic_id}/assign-receptionist/{receptionist_id}", status_code=200)
async def assign_receptionist(
    clinic_id: int,
    receptionist_id: int,
    db: AsyncSession = Depends(get_db)
):
    # --- Check clinic ---
    clinic_result = await db.execute(
        select(Clinic).where(Clinic.id == clinic_id)
    )
    clinic = clinic_result.scalar_one_or_none()
    if clinic is None:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # --- Check receptionist ---
    rec_result = await db.execute(
        select(Receptionist).where(Receptionist.id == receptionist_id)
    )
    receptionist = rec_result.scalar_one_or_none()

    if receptionist is None:
        raise HTTPException(status_code=404, detail="Receptionist not found")

    # --- Assign receptionist ---
    receptionist.clinic_id = clinic_id

    try:
        await db.commit()
        await db.refresh(receptionist)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {
        "message": "Receptionist assigned successfully",
        "clinic_id": clinic_id,
        "receptionist_id": receptionist_id
    }
