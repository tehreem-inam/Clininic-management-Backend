from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import datetime, time, timedelta, date as date_cls

from app.database import get_db
from app.models.schema import Doctor, DoctorAvailability, Appointment
from app.dto.schedule import (
    AvailabilityCreate, AvailabilityRead, AvailabilityUpdate,
    SlotItem
)

router = APIRouter(prefix="/schedule", tags=["schedule"])


def parse_hm(s: str) -> time:
    """Parse HH:MM or HH:MM:SS -> time"""
    try:
        return datetime.strptime(s, "%H:%M").time()
    except ValueError:
        try:
            return datetime.strptime(s, "%H:%M:%S").time()
        except ValueError:
            raise ValueError("Invalid time format, expected HH:MM")


def weekday_name_for_date(d: date_cls) -> str:
    # monday, tuesday, ...
    return d.strftime("%A").lower()


def time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def minutes_to_time(m: int) -> time:
    h = m // 60
    mm = m % 60
    return time(hour=h, minute=mm)



async def get_doctor_breaks(db: AsyncSession, doctor: Doctor) -> dict:
    """
    Expecting doctor.preferences to be JSON like:
    {"breaks": {"monday": [{"start":"13:00","end":"14:00"}], ...}}
    Returns dict: { "monday":[(time,start),(time,end), ...], ... }
    """
    prefs = {}
    if not doctor or not getattr(doctor, "preferences", None):
        return prefs
    try:
        prefs = doctor.preferences or {}
    except Exception:
        return {}

    breaks = {}
    raw = prefs.get("breaks", {}) if isinstance(prefs, dict) else {}
    for day, items in raw.items():
        parsed = []
        for it in items:
            try:
                parsed.append((
                    parse_hm(it["start"]),
                    parse_hm(it["end"])
                ))
            except Exception:
                # ignore malformed
                continue
        breaks[day.lower()] = parsed
    return breaks
async def check_overlap(db, doctor_id: int, day: str, start: time, end: time, exclude_id: Optional[int] = None):
    query = select(DoctorAvailability).where(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.day_of_week == day,
        DoctorAvailability.start_time < end,
        DoctorAvailability.end_time > start
    )
    if exclude_id:
        query = query.where(DoctorAvailability.id != exclude_id)

    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Overlapping availability exists"
        )

VALID_DAYS = [
    "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday"
]

@router.post("/doctors/{doctor_id}", response_model=AvailabilityRead, status_code=201)
async def create_availability(doctor_id: int, payload: AvailabilityCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    st = payload.start_time
    et = payload.end_time

    if et <= st:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    #  OVERLAP CHECK
    await check_overlap(
        db,
        doctor_id=doctor_id,
        day=payload.day_of_week.lower(),
        start=st,
        end=et
    )
    day = payload.day_of_week.lower()
    if day not in VALID_DAYS:
     raise HTTPException(400, "Invalid day_of_week")

    av = DoctorAvailability(
        doctor_id=doctor_id,
        clinic_id=payload.clinic_id,
        day_of_week=day,
        start_time=st,
        end_time=et,
        active=payload.active
    )

    db.add(av)
    try:
        await db.commit()
        await db.refresh(av)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="DB error: " + str(e))

    return av


@router.get("/doctors/{doctor_id}", response_model=List[AvailabilityRead])
async def list_availability(doctor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DoctorAvailability).where(DoctorAvailability.doctor_id == doctor_id))
    rows = result.scalars().all()
    return rows


@router.put("/{availability_id}", response_model=AvailabilityRead)
async def update_availability(
    availability_id: int,
    payload: AvailabilityUpdate,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(DoctorAvailability).where(DoctorAvailability.id == availability_id)
    )
    av = res.scalar_one_or_none()
    if not av:
        raise HTTPException(status_code=404, detail="Availability not found")

    # Update fields if provided
    if payload.day_of_week is not None:
        av.day_of_week = payload.day_of_week.lower()
    if payload.day_of_week:
      day = payload.day_of_week.lower()
    if day not in VALID_DAYS:
        raise HTTPException(400, "Invalid day_of_week")
    av.day_of_week = day

    if payload.start_time is not None:
        av.start_time = payload.start_time   # already datetime.time object

    if payload.end_time is not None:
        av.end_time = payload.end_time       # already datetime.time object

    if payload.active is not None:
        av.active = payload.active

    # Validate updated times
    if av.end_time <= av.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")
     #  OVERLAP CHECK (exclude current row)
    await check_overlap(
        db,
        doctor_id=av.doctor_id,
        day=av.day_of_week,
        start=av.start_time,
        end=av.end_time,
        exclude_id=av.id
    )
    try:
        await db.commit()
        await db.refresh(av)
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, str(e))

    return av


@router.delete("/{availability_id}", status_code=204)
async def delete_availability(availability_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(DoctorAvailability).where(DoctorAvailability.id == availability_id))
    av = res.scalar_one_or_none()
    if not av:
        raise HTTPException(status_code=404, detail="Availability not found")

    await db.delete(av)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error")
    return None


@router.get("/doctors/{doctor_id}/slots", response_model=List[SlotItem])
async def get_slots_for_date(
    doctor_id: int,
    date: str = Query(..., description="ISO date YYYY-MM-DD"),
    slot_minutes: int = Query(15, ge=5, le=120),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns available slots for a single date.
    - builds slots from DoctorAvailability entries for that weekday
    - excludes breaks stored in Doctor.preferences["breaks"]
    - enforces Doctor.max_concurrent_bookings using Appointment counts
    """
    # parse date
    try:
        target_date = date_cls.fromisoformat(date)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format; expected YYYY-MM-DD")

    weekday = weekday_name_for_date(target_date)  # monday, etc.

    # load doctor
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # get availabilities for that weekday
    av_res = await db.execute(
        select(DoctorAvailability).where(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.day_of_week == weekday,
            DoctorAvailability.active == True
        )
    )
    av_list = av_res.scalars().all()
    if not av_list:
        return []  # no availability that day

    # get breaks from preferences
    breaks_by_day = await get_doctor_breaks(db, doctor)
    breaks = breaks_by_day.get(weekday, [])

    # generate slots
    slots = []
    slot_minutes_int = int(slot_minutes)
    for av in av_list:
        start_min = time_to_minutes(av.start_time)
        end_min = time_to_minutes(av.end_time)
        cur = start_min
        while cur + slot_minutes_int <= end_min:
            slot_t = minutes_to_time(cur)
            slot_dt_time = slot_t  # time object

            # check if slot falls inside a break
            in_break = False
            for bstart, bend in breaks:
                # break intervals might not align to slot boundaries => if slot start overlaps break interval, skip
                if not (time_to_minutes(slot_dt_time) + slot_minutes_int <= time_to_minutes(bstart) or time_to_minutes(slot_dt_time) >= time_to_minutes(bend)):
                    in_break = True
                    break
            if not in_break:
                # count existing appointments for this doctor/date/time
                cnt_res = await db.execute(
                    select(func.count(Appointment.id)).where(
                        Appointment.doctor_id == doctor_id,
                        Appointment.date == target_date,
                        Appointment.time == slot_dt_time,
                        Appointment.status != "cancelled"
                    )
                )
                cnt = cnt_res.scalar_one() or 0
                max_book = int(getattr(doctor, "max_concurrent_bookings", 1))
                slots.append(SlotItem(
                    time=slot_dt_time.strftime("%H:%M"),
                    available=(cnt < max_book),
                    current_bookings=int(cnt),
                    max_bookings=max_book
                ))
            cur += slot_minutes_int

    # sort slots by time
    slots_sorted = sorted(slots, key=lambda s: s.time)
    return slots_sorted
