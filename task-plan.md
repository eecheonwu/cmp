# Clinic Modernization Platform (CMP) — Exhaustive Task Plan

As the Senior Lead Developer, I have synthesized the Architecture Decision Records (ADRs), C4 models, and Technical Specifications into a comprehensive, chronological development plan. 

This plan is broken down into discrete, actionable tasks with specific file paths and architectural code snippets to guide the engineering team from foundation to deployment.

---

## Phase 1: Project Foundation & Infrastructure Setup

Establish the monorepo structure, local development environment, and core dependencies.

- [ ] **Task 1.1: Initialize Monorepo & Version Control**
  - Create the base repository structure.
  - Files to create: `.gitignore`, `README.md`, `docker-compose.yml`
- [ ] **Task 1.2: Setup Local Docker Infrastructure**
  - Configure local PostgreSQL (16+) and Redis containers for development.
  - Files to modify: `docker-compose.yml`
- [ ] **Task 1.3: Initialize FastAPI Backend**
  - Setup Python 3.12 virtual environment, install FastAPI, Uvicorn, SQLAlchemy, Alembic, Celery, Redis, and Boto3.
  - Files to create: `backend/requirements.txt`, `backend/app/main.py`, `backend/app/core/config.py`
- [ ] **Task 1.4: Initialize React + Vite PWA Frontend**
  - Scaffold Vite React project, install TailwindCSS, Radix UI, Lucide Icons, Workbox, and Dexie.js.
  - Files to create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.js`

---

## Phase 2: Database & ORM Foundation (PostgreSQL)

Implement the database schema, enums, and Alembic migrations based on the ERD.

- [ ] **Task 2.1: Define Database Enums & Base Model**
  - Create SQLAlchemy base and enums (`UserRole`, `AppointmentStatus`, `PaymentStatus`).
  - Files to create: `backend/app/db/base.py`, `backend/app/models/enums.py`
- [ ] **Task 2.2: Implement Core User & Profile Models**
  - Create `User` and `PatientProfile` models.
  - Files to create: `backend/app/models/user.py`, `backend/app/models/patient.py`
- [ ] **Task 2.3: Implement Scheduling Models**
  - Create `DoctorAvailability` and `Appointment` models with constraints.
  - Files to create: `backend/app/models/scheduling.py`
- [ ] **Task 2.4: Implement Security & Audit Models**
  - Create `ClinicalRecord`, `SecurityAuditLog`, and `VerificationOTP` models.
  - Files to create: `backend/app/models/clinical.py`, `backend/app/models/security.py`
- [ ] **Task 2.5: Configure Alembic & Generate Initial Migration**
  - Setup Alembic environment and generate the first migration script.
  - Files to modify: `backend/alembic.ini`, `backend/alembic/env.py`

---

## Phase 3: Core Backend Services & Security

Implement authentication, RBAC, KMS envelope encryption, and immutable audit logging.

- [ ] **Task 3.1: Authentication & RBAC Service**
  - Implement JWT generation, password hashing, and FastAPI dependency for role-based access control.
  - Files to create: `backend/app/core/security.py`, `backend/app/api/dependencies/auth.py`
- [ ] **Task 3.2: AWS KMS Envelope Encryption Service (ADR-003)**
  - Implement the KMS client to generate Data Encryption Keys (DEK) and perform AES-256-GCM encryption/decryption for clinical records.
  - Files to create: `backend/app/services/encryption_service.py`
  - *Code Snippet (Encryption Service Concept)*:
    ```python
    import boto3
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import os

    class KMSEnvelopeEncryptor:
        def __init__(self, kms_key_id: str):
            self.kms = boto3.client('kms')
            self.kms_key_id = kms_key_id

        def encrypt_data(self, plaintext: str) -> dict:
            # Generate DEK
            response = self.kms.generate_data_key(KeyId=self.kms_key_id, KeySpec='AES_256')
            plaintext_dek = response['Plaintext']
            encrypted_dek = response['CiphertextBlob']
            
            # Encrypt data with AES-GCM
            aesgcm = AESGCM(plaintext_dek)
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
            
            return {
                "ciphertext": ciphertext.hex(),
                "nonce": nonce.hex(),
                "encrypted_dek": encrypted_dek.hex()
            }
    ```
- [ ] **Task 3.3: Immutable Audit Logging Middleware**
  - Create a service to automatically log sensitive actions (e.g., cross-branch access, overrides) to `security_audit_logs`.
  - Files to create: `backend/app/services/audit_service.py`

---

## Phase 4: Business Logic & Background Workers

Implement the scheduling engine, OTP verification, and pluggable notification failover.

- [ ] **Task 4.1: Pluggable Notification Service (ADR-004)**
  - Implement the Strategy pattern interface and concrete adapters for WhatsApp, Termii, and Infobip.
  - Files to create: `backend/app/services/notifications/base.py`, `backend/app/services/notifications/whatsapp.py`, `backend/app/services/notifications/termii.py`
- [ ] **Task 4.2: Celery Worker & Failover Queue**
  - Configure Celery to handle async tasks and implement the failover logic (WhatsApp -> Termii -> Infobip).
  - Files to create: `backend/app/worker/celery_app.py`, `backend/app/worker/tasks.py`
- [ ] **Task 4.3: OTP Verification Engine**
  - Implement channel-agnostic OTP generation, hashing, and validation logic.
  - Files to create: `backend/app/services/otp_service.py`
- [ ] **Task 4.4: Scheduling Engine & Pessimistic Locking (FR-019)**
  - Implement the booking logic using `SELECT ... FOR UPDATE` to prevent race conditions.
  - Files to create: `backend/app/services/scheduling_service.py`
  - *Code Snippet (Pessimistic Lock)*:
    ```python
    async def create_booking(db: AsyncSession, booking_data: AppointmentCreate):
        async with db.begin():
            # Lock doctor availability
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

            # Lock conflicting appointments
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

            # Insert appointment
            new_appt = Appointment(**booking_data.dict())
            db.add(new_appt)
            return new_appt
    ```
- [ ] **Task 4.5: Patient Penalty Engine (FR-012 to FR-014)**
  - Implement logic to calculate rolling 90-day late cancellations and apply Tier 1, 2, or 3 restrictions.
  - Files to create: `backend/app/services/penalty_service.py`

---

## Phase 5: API Route Controllers

Expose the business logic via FastAPI REST endpoints.

- [ ] **Task 5.1: Auth & Verification Router**
  - Endpoints: `POST /api/v1/auth/verify-request`, `POST /api/v1/auth/login`, `POST /api/v1/auth/register`
  - Files to create: `backend/app/api/v1/endpoints/auth.py`
- [ ] **Task 5.2: Appointment Booking Router**
  - Endpoints: `POST /api/v1/appointments`, `GET /api/v1/appointments`, `PATCH /api/v1/appointments/{id}/cancel`
  - Files to create: `backend/app/api/v1/endpoints/appointments.py`
- [ ] **Task 5.3: Clinical Records Router**
  - Endpoints: `POST /api/v1/clinical-records`, `GET /api/v1/clinical-records/patient/{id}` (with emergency override logging).
  - Files to create: `backend/app/api/v1/endpoints/clinical.py`
- [ ] **Task 5.4: Operational Reports Router**
  - Endpoints: `GET /api/v1/reports/daily-stats`
  - Files to create: `backend/app/api/v1/endpoints/reports.py`

---

## Phase 6: Frontend Foundation & Offline PWA (ADR-002)

Setup the React SPA, Vite PWA plugin, and Dexie.js for offline capabilities.

- [ ] **Task 6.1: Configure Vite PWA & Workbox**
  - Setup manifest and service worker strategies for caching static assets and API GET requests.
  - Files to modify: `frontend/vite.config.ts`, `frontend/public/manifest.json`
- [ ] **Task 6.2: Initialize Dexie.js Local Database**
  - Define the local IndexedDB schema for caching daily schedules.
  - Files to create: `frontend/src/db/db.ts`
  - *Code Snippet (Dexie Schema)*:
    ```typescript
    import Dexie, { Table } from 'dexie';

    export interface LocalAppointment {
      id: string;
      doctor_id: string;
      patient_name: string;
      start_datetime: string;
      status: string;
    }

    export class ClinicDB extends Dexie {
      appointments!: Table<LocalAppointment>;

      constructor() {
        super('ClinicOfflineDB');
        this.version(1).stores({
          appointments: 'id, doctor_id, start_datetime' // Primary key and indexed props
        });
      }
    }
    export const db = new ClinicDB();
    ```
- [ ] **Task 6.3: API Client & Axios Interceptors**
  - Setup Axios instance with JWT injection, error handling, and offline detection.
  - Files to create: `frontend/src/api/client.ts`
- [ ] **Task 6.4: Offline Sync & State Management**
  - Create a React context/hook to fetch daily schedules and sync them to Dexie.js. Implement the "Offline Mode - Read Only" banner.
  - Files to create: `frontend/src/hooks/useOfflineSync.ts`, `frontend/src/components/OfflineBanner.tsx`

---

## Phase 7: Frontend UI Implementation

Build the role-specific interfaces using Tailwind and Radix UI.

- [ ] **Task 7.1: Shared UI Components**
  - Build reusable components (Buttons, Modals, Inputs, Data Tables) using Radix UI primitives.
  - Files to create: `frontend/src/components/ui/*`
- [ ] **Task 7.2: Authentication & Registration Flows**
  - Build Login, OTP Verification, and Patient Registration screens.
  - Files to create: `frontend/src/pages/auth/*`
- [ ] **Task 7.3: Patient Mobile Portal**
  - Build responsive self-service booking flow, appointment history, and penalty warning banners.
  - Files to create: `frontend/src/pages/patient/*`
- [ ] **Task 7.4: Receptionist Desktop Dashboard**
  - Build daily schedule view, walk-in registration, check-in toggles, and restriction override modals.
  - Files to create: `frontend/src/pages/receptionist/*`
- [ ] **Task 7.5: Doctor Tablet Workspace**
  - Build clinical consultation form (notes, diagnosis), patient history viewer, and emergency cross-branch access flow.
  - Files to create: `frontend/src/pages/doctor/*`
- [ ] **Task 7.6: Manager Operational Dashboard**
  - Build real-time statistics view (utilization, no-shows).
  - Files to create: `frontend/src/pages/manager/*`

---

## Phase 8: Testing & QA

Ensure system reliability, concurrency safety, and offline resilience.

- [ ] **Task 8.1: Backend Unit & Integration Tests**
  - Write Pytest suites for OTP generation, RBAC enforcement, and KMS encryption mocking.
  - Files to create: `backend/tests/test_auth.py`, `backend/tests/test_encryption.py`
- [ ] **Task 8.2: Concurrency & Locking Tests**
  - Write async integration tests simulating concurrent booking requests to verify `HTTP 409 Conflict` responses.
  - Files to create: `backend/tests/test_scheduling_concurrency.py`
- [ ] **Task 8.3: Frontend Offline Testing**
  - Write tests (using Vitest/React Testing Library) to verify Dexie.js read operations when `navigator.onLine` is false.
  - Files to create: `frontend/src/__tests__/OfflineSync.test.tsx`

---

## Phase 9: Deployment & CI/CD

Prepare the application for AWS cloud hosting.

- [ ] **Task 9.1: CI/CD Pipeline Setup**
  - Create GitHub Actions workflows for linting, testing, and building Docker images.
  - Files to create: `.github/workflows/ci.yml`
- [ ] **Task 9.2: Infrastructure as Code (Terraform/Pulumi) - Optional/Recommended**
  - Define AWS RDS (PostgreSQL), ElastiCache (Redis), KMS Keys, and S3/CloudFront distributions.
  - Files to create: `infrastructure/main.tf`
- [ ] **Task 9.3: Backend Deployment Configuration**
  - Create production Dockerfiles and ECS/EKS deployment manifests.
  - Files to create: `backend/Dockerfile.prod`
- [ ] **Task 9.4: Frontend Static Deployment**
  - Configure Vite build script for production and AWS S3 sync commands.
  - Files to modify: `frontend/package.json`