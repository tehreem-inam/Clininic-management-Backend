from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session , joinedload
from app.database import get_db
from app.models.schema import Appointment , PaymentTransaction , Invoice 
from app.dto.payment import PaymentCreate, PaymentResponse , InvoiceCreateDTO , InvoiceResponseDTO
import uuid
from datetime import datetime

router = APIRouter(prefix="/payments", tags=["Payments"])


# ---------------------------
#  Create Payment
# ---------------------------
@router.post("/", response_model=PaymentResponse)
async def create_payment(data: PaymentCreate, db: AsyncSession = Depends(get_db)):

    # 1. Verify appointment exists
    stmt = select(Appointment).where(Appointment.id == data.appointment_id)
    result = await db.execute(stmt)
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # 2. Prevent duplicate payments
    stmt = select(PaymentTransaction).where(PaymentTransaction.appointment_id == data.appointment_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already exists for this appointment"
        )
    if appointment.status not in ("booked", "completed"):
        raise HTTPException(
            status_code=400,
            detail="Payment can only be created for booked or completed appointments",
        )
    # 3. Calculate billing
    base_amount = appointment.fee if hasattr(appointment, "fee") else 0

    if base_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment has no valid fee"
        )

    if data.discount > base_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount cannot exceed amount"
        )

    total_amount = base_amount - data.discount

    # 4. Create payment entry
    payment = PaymentTransaction(
        appointment_id=appointment.id,
        patient_id=appointment.patient_id,
        clinic_id=appointment.clinic_id,
        doctor_id=appointment.doctor_id,
        receptionist_id=appointment.receptionist_id,

        amount=base_amount,
        discount=data.discount,
        total_amount=total_amount,

        payment_method=data.payment_method,
        payment_status="success",
        remarks=data.remarks
    )

    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return payment


# ---------------------------
#  Get Single Payment
# ---------------------------
@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(PaymentTransaction).where(PaymentTransaction.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    return payment


# ---------------------------
# Payment History (by patient or clinic or doctor)
# ---------------------------
@router.get("/", response_model=list[PaymentResponse])
async def payment_history(
    db: AsyncSession = Depends(get_db),
    patient_id: int | None = None,
    clinic_id: int | None = None,
    doctor_id: int | None = None
):
    stmt = select(PaymentTransaction)

    if patient_id:
        stmt = stmt.where(PaymentTransaction.patient_id == patient_id)

    if clinic_id:
        stmt = stmt.where(PaymentTransaction.clinic_id == clinic_id)

    if doctor_id:
        stmt = stmt.where(PaymentTransaction.doctor_id == doctor_id)

    result = await db.execute(stmt)
    payments = result.scalars().all()

    return payments





@router.get("/invoice/{appointment_id}", response_model=InvoiceResponseDTO, status_code=200)
async def generate_invoice(
    appointment_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Fetch appointment with related data using joins to avoid lazy loading
    appointment_query = await db.execute(
        select(Appointment)
        .options(joinedload(Appointment.patient))
        .options(joinedload(Appointment.doctor))
        .options(joinedload(Appointment.clinic))
        .where(Appointment.id == appointment_id)
    )
    appointment = appointment_query.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Fetch payment for this appointment
    payment_query = await db.execute(
        select(PaymentTransaction).where(
            PaymentTransaction.appointment_id == appointment_id
        )
    )
    payment = payment_query.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found for this appointment"
        )

    # Check if invoice already exists to avoid duplicates
    existing_invoice_query = await db.execute(
        select(Invoice).where(Invoice.appointment_id == appointment_id)
    )
    existing_invoice = existing_invoice_query.scalar_one_or_none()

    if not existing_invoice:
        # Generate a unique invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create invoice entry with all required fields
        invoice = Invoice(
            appointment_id=appointment_id,
            payment_id=payment.id,  # This is required
            invoice_number=invoice_number,  # This is required
            amount=appointment.fee,  # Base fee from appointment
            discount=payment.discount,  # Discount from payment
            total_amount=payment.total_amount,  # Final amount after discount
        )
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)
    else:
        # Use existing invoice
        invoice = existing_invoice

    # Build invoice response
    invoice_data = InvoiceResponseDTO(
        appointment_id=appointment.id,
        patient_name=appointment.patient.name,
        doctor_name=appointment.doctor.name,
        clinic_name=appointment.clinic.name,
        date=appointment.date,
        time=appointment.time,
        fee=float(appointment.fee),
        discount=float(payment.discount),
        total_amount=float(payment.total_amount),
        payment_method=payment.payment_method,
        payment_status=payment.payment_status,
        remarks=payment.remarks
    )

    return invoice_data