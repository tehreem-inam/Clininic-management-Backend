from app.database import Base
from sqlalchemy import (
    Column,
    Date,
    Integer,
    Time,
    Numeric,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    func,
    text,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
from sqlalchemy.orm import relationship


def utcnow():
    return datetime.now(timezone.utc)


class AuditMixin:
    """Mixin to add standard audit columns to models."""
    created_at = Column(
        DateTime(timezone=True),
        server_default=text("TIMEZONE('UTC', NOW())"),
        default=utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=text("TIMEZONE('UTC', NOW())"),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)


# -- RBAC: roles / permissions
class Role(AuditMixin, Base):
    __tablename__ = "tbl_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    users = relationship("User", back_populates="role_obj")


class Permission(AuditMixin, Base):
    __tablename__ = "tbl_permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)


class RolePermission(AuditMixin, Base):
    __tablename__ = "tbl_role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("tbl_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("tbl_permissions.id", ondelete="CASCADE"), nullable=False, index=True)


class UserRole(AuditMixin, Base):
    __tablename__ = "tbl_user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("tbl_roles.id", ondelete="CASCADE"), nullable=False, index=True)


# -- Core tables (existing + refined)
class Clinic(AuditMixin, Base):
    __tablename__ = "tbl_clinics"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(100), unique=True, nullable=True, index=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    clinic_type = Column(String(50), nullable=True)  # Clinic/Hospital/Lab
    logo_url = Column(String(1024), nullable=True)
    contact_person = Column(String(255), nullable=True)
    status = Column(String, default="active", server_default=text("'active'"), nullable=False)

    admins = relationship("Admin", back_populates="clinic")
    doctors = relationship("Doctor", back_populates="clinic")
    receptionists = relationship("Receptionist", back_populates="clinic")
    patients = relationship("Patient", back_populates="clinic")


class User(AuditMixin, Base):
    __tablename__ = "tbl_users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    phone = Column(String(50), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Role FK
    role_id = Column(Integer, ForeignKey("tbl_roles.id", ondelete="SET NULL"), nullable=True, index=True)
    role_obj = relationship("Role", back_populates="users", lazy="joined")

    # user may have multiple roles via tbl_user_roles
    roles = relationship("UserRole", backref="user")


class Admin(AuditMixin, Base):
    __tablename__ = "tbl_admins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String, default="active", server_default=text("'active'"), nullable=False)

    clinic = relationship("Clinic", back_populates="admins")


class Plan(AuditMixin, Base):
    __tablename__ = "tbl_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    allowed_doctors = Column(Integer, nullable=False, default=10)
    allowed_receptionists = Column(Integer, nullable=False, default=5)
    allowed_branches = Column(Integer, nullable=False, default=1)
    max_appointments_per_day = Column(Integer, nullable=False, default=100)
    validity_days = Column(Integer, nullable=False, default=30)
    price = Column(Numeric(12, 2), nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="active", server_default=text("'active'"))


class Doctor(AuditMixin, Base):
    __tablename__ = "tbl_doctors"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    specialization = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    fee = Column(Numeric(10, 2), nullable=False, default=0.00)
    plan_id = Column(Integer, ForeignKey("tbl_plans.id", ondelete="SET NULL"), nullable=True)
    max_concurrent_bookings = Column(Integer, nullable=False, default=1)
    status = Column(String, default="active", server_default=text("'active'"), nullable=False)
    preferences = Column(JSONB, nullable=True)
    medical_registration_number = Column(String(100), nullable=True, index=True)

    clinic = relationship("Clinic", back_populates="doctors")
    plan = relationship("Plan")


class Receptionist(AuditMixin, Base):
    __tablename__ = "tbl_receptionists"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    status = Column(String, default="active", server_default=text("'active'"), nullable=False)

    clinic = relationship("Clinic", back_populates="receptionists")


class Patient(AuditMixin, Base):
    __tablename__ = "tbl_patients"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    medical_record_number = Column(String(100), nullable=True, index=True)
    cnic = Column(String(50), unique=True, index=True, nullable=True)
    phone = Column(String(20), nullable=True, index=True)
    gender = Column(String(10), nullable=True)
    age = Column(Integer, nullable=True)
    city = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="active", server_default=text("'active'"))

    clinic = relationship("Clinic", back_populates="patients")


class DoctorAvailability(AuditMixin, Base):
    __tablename__ = "tbl_doctor_availability"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("tbl_doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="RESTRICT"), nullable=False, index=True)
    day_of_week = Column(String(20), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    doctor = relationship("Doctor", backref="availability")
    clinic = relationship("Clinic")


class Appointment(AuditMixin, Base):
    __tablename__ = "tbl_appointments"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("tbl_patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("tbl_doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="RESTRICT"), nullable=False, index=True)
    receptionist_id = Column(Integer, ForeignKey("tbl_receptionists.id", ondelete="SET NULL"), nullable=True, index=True)
    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=15)
    booking_reference = Column(String(100), unique=True, nullable=True, index=True)
    source = Column(String(50), nullable=True)  # walk-in/online/phone
    created_by = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True, index=True)
    canceled_by = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, nullable=True)
    no_show = Column(Boolean, default=False, nullable=False)
    fee = Column(Numeric(12, 2), nullable=False, default=0.0)
    discount = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    payment_status = Column(String(50), nullable=False, default="pending", server_default=text("'pending'"))
    status = Column(String(50), nullable=False, default="booked", server_default=text("'booked'"))

    patient = relationship("Patient")
    doctor = relationship("Doctor")
    clinic = relationship("Clinic")
    receptionist = relationship("Receptionist")


class PaymentTransaction(AuditMixin, Base):
    __tablename__ = "tbl_payment_transactions"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("tbl_appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("tbl_patients.id", ondelete="CASCADE"), nullable=True, index=True)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="CASCADE"), nullable=True, index=True)
    doctor_id = Column(Integer, ForeignKey("tbl_doctors.id", ondelete="SET NULL"), nullable=True, index=True)
    receptionist_id = Column(Integer, ForeignKey("tbl_receptionists.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    discount = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    payment_method = Column(String(50), nullable=False)
    transaction_reference = Column(String(255), nullable=True, index=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    currency = Column(String(10), nullable=True, default='PKR')
    payment_provider = Column(String(100), nullable=True)
    payment_status = Column(String(50), nullable=False, default="success", server_default=text("'success'"))
    remarks = Column(Text, nullable=True)

    appointment = relationship("Appointment")
    patient = relationship("Patient")


class SystemPreference(AuditMixin, Base):
    __tablename__ = "tbl_system_preferences"
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(100), nullable=False, index=True)
    value = Column(String(255), nullable=False)
    updated_by = Column(Integer, nullable=True)
    clinic = relationship("Clinic")


class Invoice(AuditMixin, Base):
    __tablename__ = "tbl_invoices"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("tbl_appointments.id", ondelete="CASCADE"), nullable=False)
    payment_id = Column(Integer, ForeignKey("tbl_payment_transactions.id", ondelete="CASCADE"), nullable=False)
    invoice_number = Column(String(100), unique=True, index=True, nullable=False)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(String(50), nullable=False, default='unpaid', server_default=text("'unpaid'"))
    tax_amount = Column(Numeric(12,2), nullable=True, default=0.0)
    currency = Column(String(10), nullable=True, default='PKR')
    issued_by = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True)
    pdf_s3_key = Column(String(2048), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    discount = Column(Numeric(12, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    appointment = relationship("Appointment")
    payment = relationship("PaymentTransaction")


# -- Medicines / prescriptions / vitals / notifications / inventory / billing
class Medicine(AuditMixin, Base):
    __tablename__ = "tbl_medicines"
    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String(255), nullable=False, index=True)
    generic_name = Column(String(255), nullable=True, index=True)
    form = Column(String(50), nullable=True)
    strength = Column(String(50), nullable=True)
    unit = Column(String(50), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    pack_size = Column(String(50), nullable=True)
    default_price = Column(Numeric(12, 2), nullable=True, default=0.0)
    controlled = Column(Boolean, default=False)
    metadata_json = Column(JSONB, nullable=True)


class MedicineRequest(AuditMixin, Base):
    __tablename__ = "tbl_medicine_requests"
    id = Column(Integer, primary_key=True, index=True)
    requested_by_doctor_id = Column(Integer, ForeignKey("tbl_doctors.id", ondelete="SET NULL"), nullable=True, index=True)
    medicine_name = Column(String(255), nullable=False)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending", server_default=text("'pending'"))
    reviewed_by = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


class Prescription(AuditMixin, Base):
    __tablename__ = "tbl_prescriptions"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("tbl_appointments.id", ondelete="SET NULL"), nullable=True, index=True)
    patient_id = Column(Integer, ForeignKey("tbl_patients.id", ondelete="SET NULL"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("tbl_doctors.id", ondelete="SET NULL"), nullable=False, index=True)
    chief_complaint = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    findings = Column(JSONB, nullable=True)
    notes_for_patient = Column(Text, nullable=True)
    prescription_number = Column(String(100), unique=True, nullable=True, index=True)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="SET NULL"), nullable=True, index=True)
    issued_by_user_id = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True)
    signature_hash = Column(String(512), nullable=True)
    status = Column(String(50), nullable=False, default="draft", server_default=text("'draft'"))
    issued_at = Column(DateTime(timezone=True), nullable=True)


class PrescriptionMedicine(AuditMixin, Base):
    __tablename__ = "tbl_prescription_medicines"
    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("tbl_prescriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("tbl_medicines.id", ondelete="SET NULL"), nullable=True, index=True)
    dosage = Column(String(100), nullable=True)
    route = Column(String(50), nullable=True)
    frequency = Column(String(50), nullable=True)
    duration = Column(String(50), nullable=True)
    quantity = Column(Integer, nullable=True)
    instructions = Column(Text, nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=True)
    total_price = Column(Numeric(12, 2), nullable=True)
    dispensed_quantity = Column(Integer, nullable=True)
    dispensed_at = Column(DateTime(timezone=True), nullable=True)
    dispensed_by = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True)


class PatientVital(AuditMixin, Base):
    __tablename__ = "tbl_patient_vitals"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("tbl_appointments.id", ondelete="SET NULL"), nullable=True, index=True)
    patient_id = Column(Integer, ForeignKey("tbl_patients.id", ondelete="SET NULL"), nullable=False, index=True)
    bp_systolic = Column(Integer, nullable=True)
    bp_diastolic = Column(Integer, nullable=True)
    blood_sugar = Column(Numeric(8, 2), nullable=True)
    temperature = Column(Numeric(5, 2), nullable=True)
    pulse = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    spo2 = Column(Numeric(5, 2), nullable=True)
    height_cm = Column(Numeric(6, 2), nullable=True)
    weight_kg = Column(Numeric(6, 2), nullable=True)
    bmi = Column(Numeric(6, 2), nullable=True)
    notes = Column(Text, nullable=True)
    taken_by = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True)
    taken_at = Column(DateTime(timezone=True), nullable=True)


class Notification(AuditMixin, Base):
    __tablename__ = "tbl_notifications"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("tbl_patients.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True, index=True)
    channel = Column(String(50), nullable=False)  # whatsapp, sms, email, push
    template_name = Column(String(255), nullable=True)
    payload = Column(JSONB, nullable=True)
    status = Column(String(50), nullable=False, default="pending", server_default=text("'pending'"))
    provider_response = Column(JSONB, nullable=True)
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)


class InventoryStock(AuditMixin, Base):
    __tablename__ = "tbl_inventory_stock"
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("tbl_clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("tbl_medicines.id", ondelete="SET NULL"), nullable=False, index=True)
    batch_number = Column(String(100), nullable=True)
    expiry_date = Column(Date, nullable=True)
    quantity_on_hand = Column(Numeric(12, 2), nullable=False, default=0)
    minimum_level = Column(Numeric(12, 2), nullable=True)
    cost_price = Column(Numeric(12, 2), nullable=True)
    selling_price = Column(Numeric(12, 2), nullable=True)
    location = Column(String(255), nullable=True)


class InventoryMovement(AuditMixin, Base):
    __tablename__ = "tbl_inventory_movements"
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("tbl_inventory_stock.id", ondelete="CASCADE"), nullable=False, index=True)
    movement_type = Column(String(50), nullable=False)  # received, dispensed, adjustment, returned, expired
    quantity = Column(Numeric(12, 2), nullable=False)
    reason = Column(Text, nullable=True)
    reference_table = Column(String(100), nullable=True)
    reference_id = Column(Integer, nullable=True)
    created_by = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True)


class ServiceCode(AuditMixin, Base):
    __tablename__ = "tbl_service_codes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(12, 2), nullable=False, default=0.0)
    tax_percent = Column(Numeric(5, 2), nullable=True)
    active = Column(Boolean, default=True, nullable=False)


class AppointmentService(AuditMixin, Base):
    __tablename__ = "tbl_appointment_services"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("tbl_appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    service_code_id = Column(Integer, ForeignKey("tbl_service_codes.id", ondelete="SET NULL"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=True)
    total_price = Column(Numeric(12, 2), nullable=True)


class AuditLog(AuditMixin, Base):
    __tablename__ = "tbl_audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(255), nullable=False)
    table_name = Column(String(255), nullable=True)
    row_id = Column(Integer, nullable=True)
    before = Column(JSONB, nullable=True)
    after = Column(JSONB, nullable=True)


class AuditDeletion(AuditMixin, Base):
    __tablename__ = "tbl_audit_deletions"
    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True)
    table_name = Column(String(255), nullable=False)
    row_ids = Column(JSONB, nullable=False)
    export_path = Column(String(1024), nullable=True)
    note = Column(Text, nullable=True)


class Attachment(AuditMixin, Base):
    __tablename__ = "tbl_attachments"
    id = Column(Integer, primary_key=True, index=True)
    owner_table = Column(String(255), nullable=False)
    owner_id = Column(Integer, nullable=False)
    filename = Column(String(1024), nullable=False)
    s3_key = Column(String(2048), nullable=False)
    content_type = Column(String(255), nullable=True)
    size = Column(Integer, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("tbl_users.id", ondelete="SET NULL"), nullable=True)


# Indexes and composite indexes
Index("ix_appointments_clinic_date_time", Appointment.clinic_id, Appointment.date, Appointment.time)
Index("ix_medicines_brand_strength", Medicine.brand_name, Medicine.strength)
Index("ix_inventory_stock_clinic_medicine", InventoryStock.clinic_id, InventoryStock.medicine_id)

