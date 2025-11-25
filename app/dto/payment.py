from pydantic import BaseModel, Field , ConfigDict
from typing import Optional
from datetime import datetime , date , time
from decimal import Decimal

class PaymentCreate(BaseModel):
    appointment_id: int
    discount: float = Field(default=0, ge=0)

    payment_method: str = Field(..., pattern="^(cash|card|online)$")
    remarks: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    appointment_id: int
    patient_id: int
    doctor_id: int
    clinic_id: int
    receptionist_id: Optional[int]

    amount: float
    discount: float
    total_amount: float

    payment_method: str
    payment_status: str
    remarks: Optional[str]

    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class InvoiceCreateDTO(BaseModel):
    appointment_id: int = Field(..., gt=0, description="Appointment ID for invoice generation")

class InvoiceResponseDTO(BaseModel):
    appointment_id: int
    patient_name: str
    doctor_name: str
    clinic_name: str
    date: date
    time: time
    fee: float
    discount: float
    total_amount: float
    payment_method: str
    payment_status: str
    remarks: Optional[str]

    model_config = ConfigDict(from_attributes=True)