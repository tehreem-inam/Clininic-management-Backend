from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import time, date

class BreakItem(BaseModel):
    start: str  # "HH:MM"
    end: str    # "HH:MM"

class AvailabilityBase(BaseModel):
    day_of_week: str = Field(..., description="e.g. monday, tuesday, ...")
    start_time: time
    end_time: time
    active: Optional[bool] = True

class AvailabilityCreate(AvailabilityBase):
    clinic_id: int

class AvailabilityUpdate(BaseModel):
    day_of_week: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    active: Optional[bool] = None

class AvailabilityRead(AvailabilityBase):
    id: int
    doctor_id: int
    clinic_id: int

    model_config = ConfigDict(from_attributes=True)

class SlotsQuery(BaseModel):
    date: str  # YYYY-MM-DD
    slot_minutes: Optional[int] = 15  # default slot length

class SlotItem(BaseModel):
    time: str  # HH:MM
    available: bool
    current_bookings: int
    max_bookings: int
