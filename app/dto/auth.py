from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


#-------------- auth dto ----------------#
class LoginRequest(BaseModel):
    email: EmailStr
    password: str  # min_length=6 enforced in validation logic

class UserLoginResponse(BaseModel):
    message: str
    access_token: str
    token_type: str
    user: dict
class LogoutResponse(BaseModel):
    message: str

## ------------- admin auth dto ------------- ##
class AdminRegisterRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    clinic_id: Optional[int] = None # Admin may or may not be associated with a clinic at registration
    role: str = "admin"  # Default role is admin
    

    
class AdminResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    clinic_id: Optional[int] = None
    status: str
    
    class Config:
        from_attributes = True
        
 # ------------- receptionist auth dto ----------------- ##
class ReceptionistRegisterRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone: Optional[str] = None
    clinic_id: int
    

    
class ReceptionistResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    clinic_id : int
    phone: Optional[str] = None
    status: str
    
    class Config:
        from_attributes = True
        
# ------------- doctor auth dto ----------------- ##
class DoctorRegisterRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    specialization: Optional[str] = None
    phone: Optional[str] = None
    clinic_id: int
    fee: Optional[float] = 0.0
    plan_id: Optional[int] = None
    

class DoctorResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    specialization: Optional[str] = None
    phone: Optional[str] = None
    clinic_id: int
    fee: Optional[float] = 0.0
    plan_id: Optional[int] = None
    status: str
    
    class Config:
        from_attributes = True
     