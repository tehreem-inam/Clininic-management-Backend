from pydantic import BaseModel, Field, ConfigDict
from datetime import date, time
from decimal import Decimal

class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    date: date
    time: time
    fee: Decimal = 0
    discount: Decimal = 0


class AppointmentUpdateStatus(BaseModel):
    status: str = Field(..., description="booked / checked-in / completed / cancelled")


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    clinic_id: int
    date: date
    time: time
    fee: Decimal
    discount: Decimal
    total_amount: Decimal
    payment_status: str
    status: str

    model_config = ConfigDict(from_attributes=True)
