# Schema & Software Relationships — Clinic Management Backend

This document is the canonical reference for the database models declared in `app/models/schema.py`. It lists every table, required fields, relations, constraints, indexing and practical usage patterns for application code and migrations.

**Conventions**

- `tbl_` prefix for application tables.
- `AuditMixin` provides `created_at`, `updated_at`, `deleted_at` (UTC-aware).
- Tenant scoping: include `clinic_id` on all clinic-specific/transactional tables.
- Prefer Postgres `ENUM` (or small lookup tables) for `status` values and `JSONB` for flexible structured data.
- Deterministic constraint names via `naming_convention` in SQLAlchemy `MetaData`.

## Tables — definitions, required fields, relations and usage

Each table below notes purpose, required (non-optional) fields, important indexes/constraints, relations and short usage notes.

### tbl_roles

- Purpose: role definitions for RBAC.
- Required fields: `id`, `name` (unique).
- Relations: roles ⇄ users (via `role_id` on `tbl_users` and `tbl_user_roles`).
- Notes: consider `clinic_id` if roles vary by clinic and `is_system` boolean for global roles.

### tbl_permissions

- Purpose: permission tokens (e.g., `appointments:create`).
- Required fields: `id`, `name` (unique).

### tbl_role_permissions

- Purpose: many-to-many mapping between roles and permissions.
- Required fields: `role_id`, `permission_id`.
- Constraints: add unique constraint on (`role_id`, `permission_id`).

### tbl_user_roles

- Purpose: many-to-many mapping between users and roles.
- Required fields: `user_id`, `role_id`.
- Constraints: unique (`user_id`, `role_id`).

### tbl_clinics

- Purpose: tenancy unit (clinic/branch).
- Required fields: `id`, `name`, `status`.
- Strongly recommended required additions: `timezone` (CRITICAL for scheduling), `currency`.
- Relations: clinic → admins, doctors, receptionists, patients, inventory.
- Indexes: `code` (unique) and `name` for lookup.

### tbl_users

- Purpose: authentication and identity record.
- Required fields: `id`, `email` (unique), `password_hash`.
- Recommended: `username` or `external_id`, `is_verified`, `email_verified_at`.
- Relations: may link to `tbl_admins`, `tbl_doctors`, `tbl_receptionists` via `user_id`.

### tbl_admins

- Purpose: staff-level metadata for administrative users.
- Required fields: `id`, `name`, `email`.
- Relations: `clinic_id` → `tbl_clinics.id`, `user_id` (optional link to `tbl_users`).

### tbl_plans

- Purpose: subscription plans and limits.
- Required fields: `id`, `name`, `price`, `validity_days`.
- Recommended: `billing_cycle`, `features` JSONB.

### tbl_doctors

- Purpose: doctor profile used for scheduling and billing.
- Required fields: `id`, `clinic_id`, `name`, `email`, `password_hash`, `fee`.
- High-priority added: `medical_registration_number` (license), index this column.
- Relations: `clinic_id` → `tbl_clinics`, `plan_id` → `tbl_plans`.

### tbl_receptionists

- Purpose: reception staff profile.
- Required fields: `id`, `clinic_id`, `name`, `email`, `password_hash`.

### tbl_patients

- Purpose: patient demographics and identifiers.
- Required fields: `id`, `clinic_id`, `name`.
- High-priority added: `date_of_birth`, `medical_record_number` (MRN). Enforce `(clinic_id, medical_record_number)` uniqueness.
- Recommended: emergency contact fields, `insurance_id`.

### tbl_doctor_availability

- Purpose: store regular availability slots.
- Required fields: `id`, `doctor_id`, `clinic_id`, `day_of_week`, `start_time`, `end_time`.
- Recommended: `slot_duration_minutes`, recurrence rules.

### tbl_appointments

- Purpose: bookings between patients and doctors.
- Required fields: `id`, `patient_id`, `doctor_id`, `clinic_id`, `date`, `time`.
- High-priority added: `duration_minutes`, `booking_reference` (public unique id), `created_by`, `source` (walk-in/online/phone), `canceled_by`, `canceled_at`, `cancel_reason`, `no_show`.
- Indexes: composite on (`clinic_id`, `date`, `time`) to support calendar queries.
- Usage: compute `start_datetime`/`end_datetime` with `clinic.timezone` for conflict checks.

### tbl_payment_transactions

- Purpose: record of payments related to appointments/invoices.
- Required fields: `id`, `appointment_id`, `amount`, `payment_method`, `payment_status`.
- High-priority added: `transaction_reference` (gateway id), `paid_at`, `currency`, `payment_provider`.
- Usage: use `transaction_reference` + `payment_provider` for webhook idempotency.

### tbl_system_preferences

- Purpose: key/value settings per clinic.
- Required fields: `clinic_id`, `key`, `value`.

### tbl_invoices

- Purpose: invoice document for billing.
- Required fields: `id`, `invoice_number` (unique), `appointment_id`, `payment_id`.
- High-priority added: `clinic_id`, `invoice_date`, `due_date`, `status`, `tax_amount`, `currency`, `issued_by`, `pdf_s3_key`.

### tbl_medicines

- Purpose: medicines catalog.
- Required fields: `id`, `brand_name`.
- Recommended: `atc_code`, `barcode/gtin`, `default_unit_of_measure`, `reorder_level`.

### tbl_medicine_requests

- Purpose: internal requests for medicine procurement.
- Required fields: `id`, `requested_by_doctor_id`, `medicine_name`.
- High-priority added: `clinic_id`.

### tbl_prescriptions

- Purpose: prescriptions issued by doctors.
- Required fields: `id`, `patient_id`, `doctor_id`.
- High-priority added: `prescription_number` (unique per clinic), `clinic_id`, `issued_by_user_id`, `signature_hash`.

### tbl_prescription_medicines

- Purpose: prescription line items.
- Required fields: `prescription_id`, `dosage`.
- High-priority added: `unit_price`, `total_price`, `dispensed_quantity`, `dispensed_at`, `dispensed_by`.

### tbl_patient_vitals

- Purpose: store vitals recorded during visits.
- Required fields: `id`, `patient_id`.
- Recommended: make `taken_by` non-null when entered via UI; add `device_id` for device uploads.

### tbl_notifications

- Purpose: queued/sent notifications (whatsapp/sms/email/push).
- Required fields: `id`, `channel` and a recipient reference.
- Recommended: `recipient_phone` and `sent_at`.

### tbl_inventory_stock

- Purpose: per-clinic inventory records.
- Required fields: `id`, `clinic_id`, `medicine_id`, `quantity_on_hand`.
- Recommended: `supplier_id`, `purchase_date`, `lot_cost`, `is_quarantined`.

### tbl_inventory_movements

- Purpose: movement ledger for stock.
- Required fields: `id`, `stock_id`, `movement_type`, `quantity`.
- Recommended: `performed_by`, `performed_at`, `cost_at_time`.

### tbl_service_codes

- Purpose: catalog of billable services.
- Required fields: `id`, `code`, `price`.
- Recommended: `clinic_id`, `tax_category`, `gl_account_code`.

### tbl_appointment_services

- Purpose: service line-items for appointments.
- Required fields: `appointment_id`, `service_code_id`, `quantity`.
- Recommended: `unit_price`, `total_price`, `discount_percent`.

### tbl_audit_logs / tbl_audit_deletions

- Purpose: record structured audit events and exported deletions for compliance.
- Required fields: `actor_id`, `action`, `table_name`/`row_ids`.
- Usage: store `before`/`after` snapshots for sensitive operations.

### tbl_attachments

- Purpose: file metadata storage for S3/local storage.
- Required fields: `owner_table`, `owner_id`, `filename`, `s3_key`.
- Recommended: `owner_clinic_id`, `checksum`, `virus_scan_status`, `is_public`.

## Relationships (ER summary)

- Clinic 1→\* Doctors, Receptionists, Admins, Patients, InventoryStock
- User 1→\* Admins (optional); User may map to staff records
- Doctor 1→* DoctorAvailability, 1→* Appointments
- Patient 1→* Appointments, 1→* PatientVitals
- Appointment 1→* PaymentTransactions, 1→* AppointmentServices, 0..1→ Invoice
- Prescription 1→\* PrescriptionMedicines

## Indexes, constraints and implementation guidance

- Add composite unique constraints where needed (e.g., `(clinic_id, medical_record_number)`).
- Use Postgres ENUMs for `status`-like fields or lightweight lookup tables to avoid free-text drift.
- Create GIN indexes on JSONB columns used in WHERE/GIN searches.
- Always index FK columns and frequently filtered columns (clinic_id, date, time).
- Consider adding `uuid` public-id columns for external references and keeping `id` (int) as PK.

## Common usage patterns (example snippets)

- Upcoming appointments (SQLAlchemy):

```python
from sqlalchemy import select
from datetime import date, timedelta

start = date.today()
end = start + timedelta(days=7)
q = select(Appointment).where(
    Appointment.clinic_id == clinic_id,
    Appointment.date.between(start, end),
    Appointment.deleted_at.is_(None)
)
```

- Payment webhook idempotency: check `(transaction_reference, payment_provider)` before insert.

## Migrations & deployment

- Disable app auto-creation of tables during Alembic `autogenerate` runs; use Alembic as the source of truth.
- Workflow: `alembic revision --autogenerate -m "message"` → inspect → `alembic upgrade head`.
- If DB was created by the app prior to Alembic, use `alembic stamp head` after validating parity, or write idempotent SQL in migrations.

## Security & compliance

- Protect PII: limit access to columns like `cnic`, `medical_record_number` and `email` via RBAC.
- Store `medical_registration_number` and `signature_hash` for traceability.
- Use encryption-at-rest for attachments that contain sensitive data; scan uploaded files for malware.

## Prioritized next steps (suggested)

1. Add `timezone` and `currency` to `tbl_clinics` and update code that builds appointment datetimes.
2. Enforce `(clinic_id, medical_record_number)` uniqueness and add indexes.
3. Create Alembic revisions for fields recently added to models and run on a staging db.
4. Convert free-text `status` columns to ENUMs or lookup tables.

---
