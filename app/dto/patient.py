from pydantic import BaseModel
from typing import Optional
from datetime import datetime , date , time

class PatientBase(BaseModel):
    name: str
    phone: Optional[str] = None
    cnic: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    city: Optional[str] = None
    status: Optional[str] = "active"

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: int
    clinic_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
class PatientVisitItem(BaseModel):
    appointment_id: int
    doctor_id: int
    doctor_name: str
    date: date
    time: time
    status: str
    reason: Optional[str] = None

    class Config:
        orm_mode = True


class PatientHistoryResponse(BaseModel):
    patient_id: int
    patient_name: str
    total_visits: int
    visits: list[PatientVisitItem]
    
