from app.database import Base
from sqlalchemy import Column,Date, Integer,JSON,Time,  Numeric,String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, func, text, CheckConstraint
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text)
from datetime import datetime, timezone
from sqlalchemy.orm import relationship

def utcnow():
    return datetime.now(timezone.utc)


class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="admin", nullable=False) #superadmin, admin
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    clinic = relationship("Clinic", back_populates="admins", lazy="joined")
    
class Clinic(Base):
    __tablename__ = "clinics"
    id = Column(Integer , primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("clinics.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False , index=True)
    code = Column(String(100), unique=True, nullable=True , index=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    status = Column(String, default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    admins = relationship("Admin", back_populates="clinic", cascade="all, delete-orphan")
    doctors = relationship("Doctor", back_populates="clinic", cascade="all, delete-orphan")
    receptionists = relationship("Receptionist", back_populates="clinic", cascade="all, delete-orphan")
    patients = relationship("Patient", back_populates="clinic", cascade="all, delete-orphan")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)

    allowed_doctors = Column(Integer, nullable=False, default=10)
    allowed_receptionists = Column(Integer, nullable=False, default=5)
    allowed_branches = Column(Integer, nullable=False, default=1)
    max_appointments_per_day = Column(Integer, nullable=False, default=100)
    validity_days = Column(Integer, nullable=False, default=30)
    price = Column(Numeric(12, 2), nullable=False, default=0.0)

    status = Column(String(50), nullable=False, default="active")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)



   
class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False , index=True)
    specialization = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    fee = Column( Numeric(10,2), nullable=False , default=0.00)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    
    max_concurrent_bookings = Column(Integer, nullable=False, default=1)
    status = Column(String, default="active", nullable=False) #active, inactive
    
    preferences = Column(JSON, nullable=True) # JSON string for preferences
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    clinic = relationship("Clinic", back_populates="doctors", lazy="joined")
    plan = relationship("Plan",  lazy="joined")
    
    
class Receptionist(Base):
    __tablename__ = "receptionists"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    
    status = Column(String, default="active", nullable=False) #active, inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    clinic = relationship("Clinic", back_populates="receptionists", lazy="joined")
    
    
class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False)
    cnic = Column(String(50), unique=True, index=True, nullable=True)
    phone = Column(String(20), nullable=True , index=True)
    gender = Column(String(10), nullable=True)
    age = Column(Integer, nullable=True)
    city = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="active")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    clinic = relationship("Clinic", back_populates="patients", lazy="joined")

class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    
    day_of_week = Column(String(20), nullable=False)  # Monday, Sunday
    start_time = Column(Time , nullable=False)
    end_time = Column(Time , nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
     
     
    doctor = relationship("Doctor", backref="availability")
    clinic = relationship("Clinic")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)

    receptionist_id = Column(Integer, ForeignKey("receptionists.id", ondelete="SET NULL"), nullable=True)

    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=False)
    fee = Column(Numeric(12, 2), nullable=False, default=0.0)
    discount = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0.0)

    payment_status = Column(String(50), nullable=False, default="pending")  # pending, paid, failed
    status = Column(String(50), nullable=False, default="booked")  # booked, checked-in, completed, cancelled
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patient = relationship("Patient", lazy="joined")
    doctor = relationship("Doctor", lazy="joined")
    clinic = relationship("Clinic", lazy="joined")
    receptionist = relationship("Receptionist", lazy="joined")
    
class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)
    receptionist_id = Column(Integer, ForeignKey("receptionists.id", ondelete="SET NULL"), nullable=True)

    amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    discount = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0.0)

    payment_method = Column(String(50), nullable=False)  # cash, card, online
    payment_status = Column(String(50), nullable=False, default="success")  # success, failed, pending

    remarks = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    appointment = relationship("Appointment", lazy="joined")
    patient = relationship("Patient", lazy="joined")
    
    
class SystemPreference(Base):
    __tablename__ = "system_preferences"
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(100), nullable=False, index=True)
    value = Column(String(255), nullable=False)
    
    updated_by = Column(Integer, nullable=True)  # admin id who updated
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    clinic = relationship("Clinic")

class User(Base):
    __tablename__ = "users"


    id = Column(Integer, primary_key=True, index=True)


    name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(String(50), nullable=False)  # admin / doctor / receptionist

    active = Column(Boolean, default=True)

    password_hash = Column(Text, nullable=False)

   
    # Doctor
    specialization = Column(String(255), nullable=True)

    # Receptionist
    phone = Column(String(50), nullable=True)

  
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    last_login_at = Column(DateTime(timezone=True), nullable=True)

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)

    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payment_transactions.id", ondelete="CASCADE"), nullable=False)

    invoice_number = Column(String(100), unique=True, index=True, nullable=False)

    amount = Column(Numeric(12, 2), nullable=False)
    discount = Column(Numeric(12, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    appointment = relationship("Appointment", lazy="joined")
    payment = relationship("PaymentTransaction", lazy="joined")
