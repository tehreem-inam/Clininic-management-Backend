from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SystemPreferenceBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=0, max_length=255)

class SystemPreferenceCreate(SystemPreferenceBase):
    clinic_id: int

class SystemPreferenceUpdate(BaseModel):
    key: Optional[str] = Field(None, min_length=1, max_length=100)
    value: Optional[str] = Field(None, min_length=0, max_length=255)

class SystemPreferenceRead(SystemPreferenceBase):
    id: int
    clinic_id: int
    updated_by: Optional[int] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
