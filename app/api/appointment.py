from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import time , date 

from app.models import Appointment, Patient, Doctor ,  DoctorAvailability
from app.database import get_db
from app.dto.appointment import (
    AppointmentCreate,
    AppointmentUpdateStatus,
    AppointmentResponse
)

from app.auth.dependencies import (
    get_current_user,
    require_admin,
    require_receptionist,
    require_doctor,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


def normalize_time(t: time) -> time:
    """Remove seconds & microseconds to avoid mismatches."""
    return time(t.hour, t.minute)


def time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def weekday_name_for_date(date_obj: date):
    names = ["monday", "tuesday", "wednesday", "thursday",
             "friday", "saturday", "sunday"]
    return names[date_obj.weekday()]


async def get_doctor_breaks(db, doctor):
    prefs = doctor.preferences or {}
    # {"breaks": {"monday": [(start, end),...]}}
    return prefs.get("breaks", {})


# -------------------- CREATE APPOINTMENT --------------------

@router.post("/", response_model=AppointmentResponse)
async def create_appointment(
    payload: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):

    # ---------------- ROLE CHECK ----------------
    if user.role not in ("receptionist", "admin"):
        raise HTTPException(status_code=403, detail="Not allowed")

    # ---------------- PATIENT VALIDATION ----------------
    result = await db.execute(
        select(Patient).where(
            Patient.id == payload.patient_id,
            Patient.clinic_id == user.clinic_id
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found in your clinic")

    # ---------------- DOCTOR VALIDATION ----------------
    result = await db.execute(
        select(Doctor).where(
            Doctor.id == payload.doctor_id,
            Doctor.clinic_id == user.clinic_id
        )
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found in your clinic")

    doctor_fee = float(doctor.fee or 0)

    # ---------------- DATE VALIDATION ----------------
    try:
        appt_date = date.fromisoformat(str(payload.date))
    except:
        raise HTTPException(status_code=400, detail="Invalid date format")

    appt_weekday = weekday_name_for_date(appt_date)

    # ---------------- TIME NORMALIZATION ----------------
    appt_time = normalize_time(payload.time)
    appt_time_minutes = time_to_minutes(appt_time)

    # ---------------- LOAD AVAILABILITY ----------------
    av_res = await db.execute(
        select(DoctorAvailability).where(
            DoctorAvailability.doctor_id == doctor.id,
            DoctorAvailability.day_of_week == appt_weekday,
            DoctorAvailability.active == True
        )
    )
    availability_list = av_res.scalars().all()

    if not availability_list:
        raise HTTPException(status_code=400, detail="Doctor is not available on this day")

    # ---------------- CHECK TIME INSIDE AVAILABILITY ----------------
    inside_availability = False
    for av in availability_list:
        start_min = time_to_minutes(normalize_time(av.start_time))
        end_min = time_to_minutes(normalize_time(av.end_time))

        if start_min <= appt_time_minutes < end_min:
            inside_availability = True
            break

    if not inside_availability:
        raise HTTPException(status_code=400, detail="Selected time is outside doctor's availability")

    # ---------------- CHECK BREAKS ----------------
    breaks_by_day = await get_doctor_breaks(db, doctor)
    doctor_breaks = breaks_by_day.get(appt_weekday, [])

    for bstart, bend in doctor_breaks:
        bstart_m = time_to_minutes(bstart)
        bend_m = time_to_minutes(bend)

        if bstart_m <= appt_time_minutes < bend_m:
            raise HTTPException(status_code=400, detail="Selected time falls in doctor's break")

    # ---------------- OVERLAPPING APPOINTMENT CHECK ----------------
    overlap_q = select(func.count(Appointment.id)).where(
        Appointment.doctor_id == payload.doctor_id,
        Appointment.date == appt_date,
        Appointment.time == appt_time,
        Appointment.status != "cancelled"
    )
    result = await db.execute(overlap_q)
    overlapping = result.scalar_one()

    if overlapping >= doctor.max_concurrent_bookings:
        raise HTTPException(status_code=409, detail="Slot is fully booked")

    # ---------------- CALCULATE FEE ----------------
    total_amount = doctor_fee - float(payload.discount or 0)

    # ---------------- CREATE APPOINTMENT ----------------
    appt = Appointment(
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        clinic_id=user.clinic_id,
        receptionist_id=user.id if user.role == "receptionist" else None,
        date=appt_date,
        time=appt_time,
        fee=doctor_fee,
        discount=payload.discount,
        total_amount=total_amount,
        payment_status="pending",
        status="booked"
    )

    db.add(appt)
    await db.commit()
    await db.refresh(appt)

    return appt

@router.get("/", response_model=List[AppointmentResponse])
async def list_appointments(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    if user.role not in ("admin", "receptionist"):
        raise HTTPException(status_code=403, detail="Not allowed")

    q = select(Appointment).where(Appointment.clinic_id == user.clinic_id)
    result = await db.execute(q)
    return result.scalars().all()

@router.get("/doctor/me", response_model=List[AppointmentResponse])
async def my_doctor_appointments(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_doctor)
):
    q = select(Appointment).where(Appointment.doctor_id == user.id)
    result = await db.execute(q)
    return result.scalars().all()

@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    payload: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):

    # ---------------- ROLE CHECK ----------------
    if user.role not in ("receptionist", "admin"):
        raise HTTPException(status_code=403, detail="Not allowed")

    # ---------------- LOAD APPOINTMENT ----------------
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.clinic_id == user.clinic_id
        )
    )
    appt = result.scalar_one_or_none()

    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appt.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot modify a cancelled appointment")

    # ---------------- PATIENT VALIDATION ----------------
    result = await db.execute(
        select(Patient).where(
            Patient.id == payload.patient_id,
            Patient.clinic_id == user.clinic_id
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found in your clinic")

    # ---------------- DOCTOR VALIDATION ----------------
    result = await db.execute(
        select(Doctor).where(
            Doctor.id == payload.doctor_id,
            Doctor.clinic_id == user.clinic_id
        )
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found in your clinic")

    doctor_fee = float(doctor.fee or 0)

    # ---------------- DATE VALIDATION ----------------
    try:
        appt_date = date.fromisoformat(str(payload.date))
    except:
        raise HTTPException(status_code=400, detail="Invalid date format")

    appt_weekday = weekday_name_for_date(appt_date)

    # ---------------- TIME NORMALIZATION ----------------
    appt_time = normalize_time(payload.time)
    appt_time_minutes = time_to_minutes(appt_time)

    # ---------------- LOAD AVAILABILITY ----------------
    av_res = await db.execute(
        select(DoctorAvailability).where(
            DoctorAvailability.doctor_id == doctor.id,
            DoctorAvailability.day_of_week == appt_weekday,
            DoctorAvailability.active == True
        )
    )
    availability_list = av_res.scalars().all()

    if not availability_list:
        raise HTTPException(status_code=400, detail="Doctor is not available on this day")

    # ---------------- CHECK TIME INSIDE AVAILABILITY ----------------
    inside_availability = False
    for av in availability_list:
        start_min = time_to_minutes(normalize_time(av.start_time))
        end_min = time_to_minutes(normalize_time(av.end_time))

        if start_min <= appt_time_minutes < end_min:
            inside_availability = True
            break

    if not inside_availability:
        raise HTTPException(status_code=400, detail="Selected time is outside doctor's availability")

    # ---------------- CHECK BREAKS ----------------
    breaks_by_day = await get_doctor_breaks(db, doctor)
    doctor_breaks = breaks_by_day.get(appt_weekday, [])

    for bstart, bend in doctor_breaks:
        bstart_m = time_to_minutes(bstart)
        bend_m = time_to_minutes(bend)

        if bstart_m <= appt_time_minutes < bend_m:
            raise HTTPException(status_code=400, detail="Selected time falls in doctor's break")

    # ---------------- OVERLAPPING APPOINTMENT CHECK ----------------
    overlap_q = select(func.count(Appointment.id)).where(
        Appointment.doctor_id == payload.doctor_id,
        Appointment.date == appt_date,
        Appointment.time == appt_time,
        Appointment.id != appointment_id,
        Appointment.status != "cancelled"
    )
    result = await db.execute(overlap_q)
    overlapping = result.scalar_one()

    if overlapping >= doctor.max_concurrent_bookings:
        raise HTTPException(status_code=409, detail="Slot is fully booked")

    # ---------------- CALCULATE FEE ----------------
    total_amount = doctor_fee - float(payload.discount or 0)

    # ---------------- UPDATE APPOINTMENT ----------------
    appt.patient_id = payload.patient_id
    appt.doctor_id = payload.doctor_id
    appt.date = appt_date
    appt.time = appt_time
    appt.fee = doctor_fee
    appt.discount = payload.discount
    appt.total_amount = total_amount

    await db.commit()
    await db.refresh(appt)

    return appt

@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):

    # ---------------- ROLE CHECK ----------------
    if user.role not in ("receptionist", "admin"):
        raise HTTPException(status_code=403, detail="Not allowed")

    # ---------------- FETCH APPOINTMENT ----------------
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.clinic_id == user.clinic_id
        )
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # ---------------- CHECK STATUS ----------------
    if appointment.status == "cancelled":
        raise HTTPException(status_code=400, detail="Appointment already cancelled")

    # ---------------- ONLY FUTURE APPOINTMENTS CAN BE CANCELLED ----------------
    from datetime import datetime
    appt_datetime = datetime.combine(appointment.date, appointment.time)

    if appt_datetime < datetime.now():
        raise HTTPException(status_code=400, detail="Cannot cancel past appointments")

    # ---------------- CLEAR SLOT (MARK CANCELLED) ----------------
    appointment.status = "cancelled"

    # Optional: free payment status
    appointment.payment_status = "refunded"

    # No need to manually "clear" the slot in database.
    # The slot is free because overlapping checks ignore cancelled appointments.

    await db.commit()
    await db.refresh(appointment)

    return appointment
1