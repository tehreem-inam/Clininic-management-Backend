from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List

from app.models import Patient , Appointment , Doctor
from app.dto.patient import PatientCreate, PatientResponse , PatientHistoryResponse
from app.database import get_db
from app.auth.dependencies import require_admin_or_receptionist, UserContext


router = APIRouter(prefix="/patients", tags=["Patients"])


# -------------------- CREATE PATIENT --------------------
@router.post("/", response_model=PatientResponse)
async def create_patient(
    payload: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(require_admin_or_receptionist),
):
    """
    Create a new patient for the current clinic
    """

    # CNIC must be unique per clinic
    if payload.cnic:
        query = select(Patient).where(
            Patient.cnic == payload.cnic,
            Patient.clinic_id == current_user.clinic_id
        )
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="This CNIC is already registered"
            )

    # Phone must be unique per clinic
    if payload.phone:
        query = select(Patient).where(
            Patient.phone == payload.phone,
            Patient.clinic_id == current_user.clinic_id
        )
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="This phone number is already registered"
            )

    # Create patient
    new_patient = Patient(
        name=payload.name,
        phone=payload.phone,
        cnic=payload.cnic,
        gender=payload.gender,
        age=payload.age,
        city=payload.city,
        status=payload.status,
        clinic_id=current_user.clinic_id,
    )

    db.add(new_patient)
    await db.commit()
    await db.refresh(new_patient)

    return new_patient


# -------------------- GET PATIENTS LIST --------------------
@router.get("/", response_model=List[PatientResponse])
async def get_patients(
    search: str = Query(None, description="name / phone / cnic"),
    status: str = Query(None, description="active / inactive"),
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(require_admin_or_receptionist),
):
    """
    List + Search Patients for the current clinic
    """

    query = select(Patient).where(Patient.clinic_id == current_user.clinic_id)

    # Filter by status
    if status:
        query = query.where(Patient.status == status)

    # Search by name / phone / cnic
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Patient.name.ilike(pattern),
                Patient.phone.ilike(pattern),
                Patient.cnic.ilike(pattern)
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    return result.scalars().all()
#-------------get patient by cnic ---------------
@router.get("/by-cnic/{cnic}", response_model=PatientResponse)
async def get_patient_by_cnic(
    cnic: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(require_admin_or_receptionist),
):
    """
    Get a single patient by CNIC (clinic restricted)
    """

    query = select(Patient).where(
        Patient.cnic == cnic,
        Patient.clinic_id == current_user.clinic_id
    )

    result = await db.execute(query)
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient

#------------ patient history ---------------
@router.get("/{patient_id}/history", response_model=PatientHistoryResponse)
async def get_patient_history(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_or_receptionist),
):
    """
    Returns full visit history for a patient inside the same clinic.
    """

    # 1. Ensure patient exists & belongs to same clinic
    patient_q = select(Patient).where(
        Patient.id == patient_id,
        Patient.clinic_id == current_user.clinic_id
    )
    result = await db.execute(patient_q)
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # 2. Fetch appointments + doctor info
    stmt = (
        select(
            Appointment.id,
            Appointment.date,
            Appointment.time,
            Appointment.status,
            Appointment.reason,
            Doctor.id.label("doctor_id"),
            Doctor.name.label("doctor_name")
        )
        .join(Doctor, Doctor.id == Appointment.doctor_id)
        .where(Appointment.patient_id == patient_id)
        .order_by(Appointment.date.desc(), Appointment.time.desc())
    )

    res = await db.execute(stmt)
    rows = res.fetchall()

    visits = [
        {
            "appointment_id": r.id,
            "doctor_id": r.doctor_id,
            "doctor_name": r.doctor_name,
            "date": r.date,
            "time": r.time,
            "status": r.status,
            "reason": r.reason,
        }
        for r in rows
    ]

    return {
        "patient_id": patient.id,
        "patient_name": patient.name,
        "total_visits": len(visits),
        "visits": visits,
    }