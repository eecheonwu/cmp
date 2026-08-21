# Clinic Modernization Platform (CMP) — Exhaustive Task Plan

This document outlines the chronological, actionable development tasks required to implement the Clinic Modernization Platform (CMP) based on the provided architecture, ADRs, and technical specifications.

---

## Phase 1: Foundation & Infrastructure Setup

Establish the core repository, environment variables, and external service connections (Redis, PostgreSQL, AWS KMS).

- [ ] **Task 1.1: Initialize Monorepo Structure**
  - Create the base directory structure for `backend/` and `frontend/`.
  - Initialize Git repository and `.gitignore`.
  - **Files**: `.gitignore`, `README.md`
- [ ] **Task 1.2: Setup Backend Environment & Dependencies**
  - Initialize Python 3.12 environment (e.g., using `Poetry` or `venv`).
  - Install core dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `redis`, `celery`, `boto3` (for AWS KMS), `cryptography`, `pyjwt`, `pydantic-settings`.
  - **Files**: `backend/pyproject.toml` or `backend/requirements.txt`, `backend/core/config.py`
- [ ] **Task 1.3: Configure Docker Compose for Local Development**
  - Set up local PostgreSQL 16, Redis, and a mock AWS KMS container (e.g., LocalStack) for local testing.
  - **Files**: `docker-compose.yml`, `backend/.env.example`
- [ ] **Task 1.4: Setup Frontend Environment & Dependencies**
  - Initialize Vite + React project with TypeScript.
  - Install dependencies: `react-router-dom`, `dexie`, `workbox-window`, `vite-plugin-pwa`, `tailwindcss`, `axios`.
  - **Files**: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.js`

---

## Phase 2: Database & ORM Layer (ADR-001)

Implement the PostgreSQL schema, SQLAlchemy models, and Alembic migrations.

- [ ] **Task 2.1: Initialize Alembic & Database Connection**
  - Configure SQLAlchemy async engine and session maker.
  - Initialize Alembic for schema migrations.
  - **Files**: `backend/db/session.py`, `backend/alembic.ini`, `backend/alembic/env.py`
- [ ] **Task 2.2: Create Base Enums & User Models**
  - Define `UserRole`, `AppointmentStatus`, `PaymentStatus` enums.
  - Create `User` and `PatientProfile` SQLAlchemy models.
  - **Files**: `backend/models/enums.py`, `backend/models/user.py`
- [ ] **Task 2.3: Create Scheduling Models**
  - Create `DoctorAvailability` model with `start_datetime` and `end_datetime` constraints.
  - Create `Appointment` model with foreign keys to `User` (doctor and patient).
  - **Files**: `backend/models/scheduling.py`
- [ ] **Task 2.4: Create Clinical & Security Models**
  - Create `ClinicalRecord` model with `encrypted_notes`, `encrypted_diagnosis`, `encrypted_prescriptions`, and `kms_key_version`.
  - Create `SecurityAuditLog` model for immutable tracking (NFR-007).
  - Create `VerificationOTP` model for channel-agnostic verification.
  - **Files**: `backend/models/clinical.py`, `backend/models/security.py`
- [ ] **Task 2.5: Generate and Apply Initial Migration**
  - Run Alembic to generate the initial schema migration script and apply it to the local database.
  - **Files**: `backend/alembic/versions/001_initial_schema.py`

---

## Phase 3: Backend Core & Security (ADR-003)

Implement Authentication, RBAC, and Application-Level Column Encryption.

- [ ] **Task 3.1: Implement JWT Authentication & RBAC Middleware**
  - Create utility for hashing passwords (bcrypt) and generating JWTs.
  - Implement FastAPI dependency `get_current_user` and `RoleChecker` to enforce RBAC (Patient, Receptionist, Doctor, Manager, Admin).
  - **Files**: `backend/core/security.py`, `backend/api/dependencies/auth.py`
- [ ] **Task 3.2: Implement AWS KMS Envelope Encryption Utility**
  - Create a service to fetch Data Encryption Keys (DEK) from AWS KMS.
  - Implement AES-256-GCM encryption/decryption logic for clinical records.
  - **Files**: `backend/services/encryption_service.py`
  - *Code Snippet Reference*:
    ```python
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import boto3
    import os

    class KMSEncryptor:
        def __init__(self):
            self.kms = boto3.client('kms')
            self.master_key_id = os.getenv("KMS_MASTER_KEY_ID")

        def encrypt_clinical_data(self, plaintext: str) -> dict:
            # Generate DEK
            response = self.kms.generate_data_key(KeyId=self.master_key_id, KeySpec='AES_256')
            plaintext_dek = response['Plaintext']
            encrypted_dek = response['CiphertextBlob']
            
            # Encrypt data with AES-GCM
            aesgcm = AESGCM(plaintext_dek)
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
            
            return {
                "ciphertext": nonce + ciphertext, # Prepend nonce for storage
                "kms_key_version": encrypted_dek.hex()
            }
    ```
- [ ] **Task 3.3: Implement Immutable Audit Logging Service**
  - Create a utility function to write to `SecurityAuditLog` within the same DB transaction as clinical reads/writes.
  - **Files**: `backend/services/audit_service.py`

---

## Phase 4: Business Logic & Services (ADR-004)

Implement the core engines: Scheduling (with pessimistic locking), Notifications, and OTP.

- [ ] **Task 4.1: Implement Pluggable Notification Strategy (ADR-004)**
  - Define `NotificationService` interface.
  - Implement `WhatsAppCloudAPIClient`, `TermiiSMSClient`, and `InfobipSMSClient`.
  - **Files**: `backend/services/notifications/base.py`, `backend/services/notifications/providers.py`
- [ ] **Task 4.2: Configure Celery/Redis Background Workers**
  - Setup Celery app and configure Redis as the broker.
  - Create the failover task: Try WhatsApp -> wait/catch error -> Try Termii -> Try Infobip.
  - **Files**: `backend/worker/celery_app.py`, `backend/worker/tasks.py`
- [ ] **Task 4.3: Implement OTP Verification Engine**
  - Create logic to generate 6-digit OTP, invalidate old OTPs, and enqueue the delivery task via Celery.
  - Implement rate-limiting (max 3 requests/15 mins).
  - **Files**: `backend/services/otp_service.py`
- [ ] **Task 4.4: Implement Scheduling Engine & Pessimistic Locking**
  - Create the booking validation logic using `SELECT ... FOR UPDATE`.
  - **Files**: `backend/services/scheduling_service.py`
  - *Code Snippet Reference*:
    ```python
    async def create_booking(db: AsyncSession, booking_data: AppointmentCreate, user_id: UUID):
        async with db.begin():
            # 1. Lock Doctor Availability
            shift = await db.execute(
                select(DoctorAvailability)
                .filter(
                    DoctorAvailability.doctor_id == booking_data.doctor_id,
                    DoctorAvailability.start_datetime <= booking_data.start_datetime,
                    DoctorAvailability.end_datetime >= booking_data.end_datetime,
                    DoctorAvailability.is_cancelled == False
                ).with_for_update()
            )
            if not shift.scalars().first():
                raise HTTPException(status_code=400, detail="Doctor unavailable.")

            # 2. Lock Conflicting Appointments
            conflict = await db.execute(
                select(Appointment)
                .filter(
                    Appointment.doctor_id == booking_data.doctor_id,
                    Appointment.status == 'booked',
                    Appointment.start_datetime < booking_data.end_datetime,
                    Appointment.end_datetime > booking_data.start_datetime
                ).with_for_update()
            )
            if conflict.scalars().first():
                raise HTTPException(status_code=409, detail="Slot no longer available.")

            # 3. Insert Appointment
            new_appt = Appointment(**booking_data.dict(), patient_id=user_id)
            db.add(new_appt)
            return new_appt
    ```
- [ ] **Task 4.5: Implement Progressive Cancellation Penalty Engine**
  - Create logic to check time until appointment. If < 2 hours, log penalty.
  - Calculate rolling 90-day incidents and update patient tier (Tier 1, 2, 3).
  - **Files**: `backend/services/penalty_service.py`

---

## Phase 5: API Routers & Controllers

Expose the business logic via FastAPI endpoints.

- [ ] **Task 5.1: Auth & Verification Router**
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/verify-request`
  - `POST /api/v1/auth/login`
  - **Files**: `backend/api/routers/auth.py`
- [ ] **Task 5.2: Appointment Booking Router**
  - `POST /api/v1/appointments` (Requires Patient/Receptionist/Manager role)
  - `POST /api/v1/appointments/{id}/cancel` (Triggers penalty engine)
  - `POST /api/v1/appointments/override` (Manager only)
  - **Files**: `backend/api/routers/appointments.py`
- [ ] **Task 5.3: Clinical Records Router**
  - `POST /api/v1/clinical-records` (Doctor only, triggers KMS encryption + Audit log)
  - `GET /api/v1/clinical-records/patient/{id}` (Doctor only, triggers KMS decryption + Audit log for cross-branch)
  - **Files**: `backend/api/routers/clinical.py`
- [ ] **Task 5.4: Front Desk & Reports Router**
  - `POST /api/v1/appointments/{id}/check-in` (Receptionist only)
  - `GET /api/v1/reports/daily` (Manager/Admin only)
  - **Files**: `backend/api/routers/operations.py`
- [ ] **Task 5.5: Wire up FastAPI Application**
  - Register all routers, configure CORS (allowing CloudFront domain), and add global exception handlers.
  - **Files**: `backend/main.py`

---

## Phase 6: Frontend Foundation (React + Vite PWA) (ADR-002)

Setup the offline-capable SPA.

- [ ] **Task 6.1: Configure Vite PWA Plugin & Workbox**
  - Setup `vite-plugin-pwa` to generate service workers and cache static assets.
  - **Files**: `frontend/vite.config.ts`
  - *Code Snippet Reference*:
    ```typescript
    import { VitePWA } from 'vite-plugin-pwa'
    export default defineConfig({
      plugins: [
        VitePWA({
          registerType: 'autoUpdate',
          workbox: {
            globPatterns: ['**/*.{js,css,html,ico,png,svg}']
          },
          manifest: {
            name: 'Clinic Modernization Platform',
            short_name: 'CMP',
            theme_color: '#ffffff',
            display: 'standalone'
          }
        })
      ]
    })
    ```
- [ ] **Task 6.2: Setup Dexie.js for Offline Caching (NFR-004)**
  - Define IndexedDB schema for caching the daily schedule.
  - **Files**: `frontend/src/db/offlineDb.ts`
  - *Code Snippet Reference*:
    ```typescript
    import Dexie, { Table } from 'dexie';

    export interface CachedAppointment {
      id: string;
      patientName: string;
      time: string;
      status: string;
    }

    export class ClinicDB extends Dexie {
      appointments!: Table<CachedAppointment>;
      constructor() {
        super('ClinicOfflineDB');
        this.version(1).stores({
          appointments: 'id, time, status'
        });
      }
    }
    export const db = new ClinicDB();
    ```
- [ ] **Task 6.3: Implement Axios Interceptor & Network State Hook**
  - Create an Axios instance that attaches JWT tokens.
  - Create a `useNetworkStatus` hook to detect offline state and toggle the "Offline Mode - Read Only" UI banner.
  - **Files**: `frontend/src/api/axios.ts`, `frontend/src/hooks/useNetworkStatus.ts`

---

## Phase 7: Frontend Features & UI Integration

Build the user interfaces for different roles.

- [ ] **Task 7.1: Authentication & Registration UI**
  - Build Login, Registration, and OTP Verification screens.
  - Implement role-based routing (redirect Doctors to Clinical Dashboard, Receptionists to Front Desk).
  - **Files**: `frontend/src/pages/Auth/`, `frontend/src/routes/ProtectedRoute.tsx`
- [ ] **Task 7.2: Patient Self-Service Portal**
  - Build Appointment Booking wizard (Select Branch -> Doctor -> Date -> Time).
  - Implement UI logic to handle Tier 2 (Soft Flag warning) and Tier 3 (Booking Blocked) responses from the API.
  - **Files**: `frontend/src/pages/Patient/Booking.tsx`, `frontend/src/pages/Patient/Dashboard.tsx`
- [ ] **Task 7.3: Receptionist Front Desk Dashboard**
  - Build daily schedule view.
  - Implement "Check-In" button and Walk-in registration form.
  - Implement background sync: fetch daily schedule and write to Dexie.js. Fallback to Dexie if offline.
  - **Files**: `frontend/src/pages/Reception/Dashboard.tsx`
- [ ] **Task 7.4: Doctor Clinical Workspace**
  - Build UI to view checked-in patients.
  - Build Clinical Consultation Form (Notes, Diagnosis, Prescriptions).
  - **Files**: `frontend/src/pages/Doctor/Consultation.tsx`
- [ ] **Task 7.5: Manager Operational Dashboard**
  - Build charts/tables for daily appointments, utilization, and no-show rates.
  - **Files**: `frontend/src/pages/Manager/Reports.tsx`

---

## Phase 8: Testing & Deployment

Validate the system against the Test Specification and prepare for rollout.

- [ ] **Task 8.1: Write Backend Unit & Integration Tests**
  - Test pessimistic locking concurrency (TC-02).
  - Test KMS encryption/decryption logic (TC-05).
  - Test Progressive Cancellation Penalty Engine (TC-03).
  - **Files**: `backend/tests/test_scheduling.py`, `backend/tests/test_encryption.py`, `backend/tests/test_penalty.py`
- [ ] **Task 8.2: Write Frontend & E2E Tests**
  - Test offline caching behavior (NFR-004) by mocking network failure.
  - Test Patient Registration and OTP flow (TC-01).
  - **Files**: `frontend/cypress/e2e/booking.cy.ts`, `frontend/cypress/e2e/offline.cy.ts`
- [ ] **Task 8.3: Configure CI/CD Pipelines**
  - Create GitHub Actions (or similar) to run `pytest` and `vitest` on PRs.
  - Configure build step for Vite PWA and sync to AWS S3.
  - **Files**: `.github/workflows/ci.yml`, `.github/workflows/deploy-frontend.yml`
- [ ] **Task 8.4: Infrastructure as Code (AWS Setup)**
  - Provision AWS RDS (PostgreSQL), ElastiCache (Redis), KMS Keys, S3 Bucket, and CloudFront distribution.
  - Apply strict IAM policies ensuring only the backend EC2/ECS role can access the KMS `Decrypt` action.
  - **Files**: `infrastructure/main.tf` (if using Terraform) or manual runbook.