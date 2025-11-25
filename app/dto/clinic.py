from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ClinicBase(BaseModel):
    name: str
    parent_id: Optional[int] = None
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = "active"


class ClinicCreate(ClinicBase):
    pass


class ClinicUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None


class ClinicBranch(BaseModel):
    id: int
    name: str
    city: Optional[str]
    status: str

    model_config = {"from_attributes": True}


class ClinicRead(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    code: Optional[str]
    address: Optional[str]
    city: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    branches: List[ClinicBranch] = []

    model_config = {"from_attributes": True}
