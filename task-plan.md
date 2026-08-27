# Clinic Modernization Platform (CMP) — Exhaustive Task Plan

This document provides a chronological, actionable development plan to implement the CMP based on the provided architecture, ADRs, and technical specifications. 

---

## Phase 1: Foundation & Infrastructure Setup

Establish the monorepo structure, local development environment, and core dependencies.

- [ ] **Task 1.1: Initialize Monorepo & Version Control**
  - Initialize Git repository and define folder structure (`/backend`, `/frontend`, `/infrastructure`).
  - **Files**: `.gitignore`, `README.md`
- [ ] **Task 1.2: Setup Local Infrastructure (Docker Compose)**
  - Configure PostgreSQL 16+ and Redis for local development.
  - **Files**: `docker-compose.yml`
- [ ] **Task 1.3: Backend Project Initialization (FastAPI)**
  - Setup Python 3.12 environment, install FastAPI, Uvicorn, SQLAlchemy, Alembic, Celery, Redis, and Boto3 (for AWS KMS).
  - **Files**: `backend/pyproject.toml` or `backend/requirements.txt`, `backend/main.py`
- [ ] **Task 1.4: Frontend Project Initialization (Vite + React)**
  - Scaffold React app using Vite. Install TailwindCSS, React Router, Dexie.js, Axios, and Workbox.
  - **Files**: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.js`

---

## Phase 2: Database, ORM & Cryptography (Backend)

Implement the database schema, application-level encryption (ADR-003), and Alembic migrations.

- [ ] **Task 2.1: Implement KMS Envelope Encryption Utility**
  - Create a utility to interface with AWS KMS (`GenerateDataKey`, `Decrypt`) and perform AES-256-GCM encryption/decryption.
  - **Files**: `backend/core/security/kms_client.py`, `backend/core/security/crypto.py`
  - *Security*: Ensure the KMS client uses IAM roles and never hardcodes credentials.
- [ ] **Task 2.2: Create Custom SQLAlchemy Encrypted Column Type**
  - Implement a custom SQLAlchemy TypeDecorator that automatically encrypts data on `INSERT`/`UPDATE` and decrypts on `SELECT`.
  - **Files**: `backend/db/types/encrypted_string.py`
  <details><summary>Code Snippet: Encrypted Type</summary>
  
  ```python
  from sqlalchemy.types import TypeDecorator, String
  from backend.core.security.crypto import encrypt_data, decrypt_data

  class EncryptedString(TypeDecorator):
      impl = String
      cache_ok = True

      def process_bind_param(self, value, dialect):
          if value is not None:
              return encrypt_data(value) # Returns ciphertext + IV + Tag
          return value

      def process_result_value(self, value, dialect):
          if value is not None:
              return decrypt_data(value)
          return value
  ```
  </details>

- [ ] **Task 2.3: Define Core Database Models**
  - Create SQLAlchemy models for `User`, `PatientProfile`, `DoctorAvailability`, `Appointment`, `VerificationOTP`, and `SecurityAuditLog`.
  - **Files**: `backend/models/user.py`, `backend/models/scheduling.py`, `backend/models/audit.py`
- [ ] **Task 2.4: Define Clinical Record Model with Encryption**
  - Create the `ClinicalRecord` model utilizing the `EncryptedString` type for `notes`, `diagnosis`, and `prescriptions`.
  - **Files**: `backend/models/clinical.py`
- [ ] **Task 2.5: Generate and Apply Database Migrations**
  - Configure Alembic and generate the initial migration script. Apply to local PostgreSQL.
  - **Files**: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/001_initial_schema.py`

---

## Phase 3: Core Services & Background Workers (Backend)

Implement the business logic services, including the pluggable notification failover (ADR-004) and OTP generation.

- [ ] **Task 3.1: Implement Authentication & RBAC Service**
  - Create JWT generation/validation logic. Implement FastAPI dependencies for role-based access control (RBAC).
  - **Files**: `backend/core/security/jwt.py`, `backend/api/dependencies/auth.py`
  - *Security*: Define strict scopes (`patient`, `receptionist`, `doctor`, `manager`, `admin`).
- [ ] **Task 3.2: Implement Pluggable Notification Strategy (ADR-004)**
  - Define the `NotificationService` interface and concrete adapters for WhatsApp, Termii, and Infobip.
  - **Files**: `backend/services/notifications/base.py`, `backend/services/notifications/whatsapp.py`, `backend/services/notifications/termii.py`, `backend/services/notifications/infobip.py`
- [ ] **Task 3.3: Setup Celery Workers for Notification Failover**
  - Configure Celery with Redis broker. Create the async task that attempts WhatsApp -> Termii -> Infobip.
  - **Files**: `backend/worker/celery_app.py`, `backend/worker/tasks/notifications.py`
  <details><summary>Code Snippet: Failover Task</summary>
  
  ```python
  @celery_app.task(bind=True, max_retries=3)
  def send_notification_with_failover(self, phone, message):
      try:
          WhatsAppClient().send(phone, message)
      except WhatsAppDeliveryError:
          try:
              TermiiClient().send(phone, message)
          except TermiiDeliveryError:
              InfobipClient().send(phone, message)
  ```
  </details>

- [ ] **Task 3.4: Implement OTP Verification Engine**
  - Build logic to generate 6-digit OTPs, hash them before DB storage, and enqueue the delivery task.
  - **Files**: `backend/services/otp_service.py`
- [ ] **Task 3.5: Implement Immutable Audit Logging Service**
  - Create a service that writes to `security_audit_logs` within the current database session.
  - **Files**: `backend/services/audit_service.py`

---

## Phase 4: API Routers & Business Logic (Backend)

Expose the REST API endpoints and implement the complex scheduling engine.

- [ ] **Task 4.1: Auth & Verification Router**
  - Implement `POST /api/v1/auth/verify-request` and `POST /api/v1/auth/login`.
  - **Files**: `backend/api/routers/auth.py`
- [ ] **Task 4.2: Scheduling Engine - Pessimistic Locking (FR-019)**
  - Implement `POST /api/v1/appointments`. Use `with_for_update()` to lock doctor availability and prevent double-booking.
  - **Files**: `backend/api/routers/appointments.py`, `backend/services/scheduling_service.py`
  <details><summary>Code Snippet: Pessimistic Lock</summary>
  
  ```python
  async def create_booking(db: AsyncSession, data: BookingCreate):
      async with db.begin():
          # Lock shift
          shift = await db.execute(
              select(DoctorAvailability)
              .filter(DoctorAvailability.doctor_id == data.doctor_id)
              .with_for_update()
          )
          # Check conflicts
          conflict = await db.execute(
              select(Appointment)
              .filter(Appointment.doctor_id == data.doctor_id, Appointment.status == 'booked')
              .filter(Appointment.start_datetime < data.end_datetime)
              .filter(Appointment.end_datetime > data.start_datetime)
              .with_for_update()
          )
          if conflict.first():
              raise HTTPException(409, "Slot is no longer available.")
          # Insert & Commit
  ```
  </details>

- [ ] **Task 4.3: Scheduling Engine - Penalty & Cancellation Logic**
  - Implement `POST /api/v1/appointments/{id}/cancel`. Add logic to calculate time difference, apply Tier 1/2/3 penalties, and update patient profiles.
  - **Files**: `backend/services/penalty_engine.py`
- [ ] **Task 4.4: Clinical Records Router (FR-006, FR-007)**
  - Implement `POST /api/v1/clinical-records` (Doctor only). Ensure audit logs are generated for cross-branch access.
  - **Files**: `backend/api/routers/clinical.py`
  - *Security*: Enforce `@require_role('doctor')` dependency.
- [ ] **Task 4.5: Operational Reports Router**
  - Implement `GET /api/v1/reports/daily-stats` for Branch Managers.
  - **Files**: `backend/api/routers/reports.py`

---

## Phase 5: Frontend Foundation & Offline PWA (React)

Set up the client-side architecture, routing, and offline IndexedDB caching (ADR-002).

- [ ] **Task 5.1: Configure Vite PWA & Service Workers**
  - Setup `vite-plugin-pwa` to cache static assets and intercept API requests for offline fallback.
  - **Files**: `frontend/vite.config.ts`, `frontend/public/sw.js`
- [ ] **Task 5.2: Setup Dexie.js for Offline Caching (NFR-004)**
  - Define the IndexedDB schema for caching the daily appointment list.
  - **Files**: `frontend/src/db/database.ts`
  <details><summary>Code Snippet: Dexie Setup</summary>
  
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
        appointments: 'id, time, status' // Primary key and indexed props
      });
    }
  }
  export const db = new ClinicDB();
  ```
  </details>

- [ ] **Task 5.3: Axios Interceptors & Auth State**
  - Configure Axios to attach JWT tokens. Implement a sync mechanism that writes fetched schedules to Dexie.js.
  - **Files**: `frontend/src/api/axios.ts`, `frontend/src/context/AuthContext.tsx`
- [ ] **Task 5.4: Offline UI Banner & Network Hook**
  - Create a custom hook `useNetworkStatus` and a global UI banner that displays "Offline Mode - Read Only" when disconnected.
  - **Files**: `frontend/src/hooks/useNetworkStatus.ts`, `frontend/src/components/OfflineBanner.tsx`

---

## Phase 6: Frontend Features & UI Implementation

Build the role-specific dashboards and user interfaces.

- [ ] **Task 6.1: Authentication & Registration UI**
  - Build Login, Registration, and OTP Verification screens.
  - **Files**: `frontend/src/pages/auth/Login.tsx`, `frontend/src/pages/auth/Register.tsx`, `frontend/src/pages/auth/VerifyOTP.tsx`
- [ ] **Task 6.2: Patient Portal (Mobile Responsive)**
  - Build the self-service booking flow (Select Branch -> Doctor -> Date -> Time). Implement cancellation with penalty warnings.
  - **Files**: `frontend/src/pages/patient/Dashboard.tsx`, `frontend/src/pages/patient/BookAppointment.tsx`
- [ ] **Task 6.3: Receptionist Dashboard (Desktop)**
  - Build the daily schedule view, walk-in registration form, and check-in toggle. Implement the "Override Restriction" button for Tier 3 patients.
  - **Files**: `frontend/src/pages/reception/Dashboard.tsx`, `frontend/src/pages/reception/WalkIn.tsx`
- [ ] **Task 6.4: Doctor Workspace (Tablet/Desktop)**
  - Build the consultation form (Notes, Diagnosis, Prescriptions). Ensure it reads from/writes to the encrypted API endpoints.
  - **Files**: `frontend/src/pages/doctor/Schedule.tsx`, `frontend/src/pages/doctor/ConsultationForm.tsx`
- [ ] **Task 6.5: Manager Operational Dashboard**
  - Build charts/tables displaying daily appointments, utilization, and no-show rates.
  - **Files**: `frontend/src/pages/manager/Reports.tsx`

---

## Phase 7: Testing, Security & Deployment

Validate the system against the Test Specification and prepare for cloud deployment.

- [ ] **Task 7.1: Backend Unit & Integration Tests**
  - Write `pytest` cases for the Penalty Engine, OTP Rate Limiting, and Pessimistic Locking (simulate concurrent requests).
  - **Files**: `backend/tests/test_scheduling.py`, `backend/tests/test_penalty_engine.py`
- [ ] **Task 7.2: Security & Compliance Tests (NDPR)**
  - Write tests verifying that `clinical_records` DB queries return ciphertext, and that Admin JWTs receive HTTP 403 on clinical endpoints.
  - **Files**: `backend/tests/test_security.py`
- [ ] **Task 7.3: Frontend E2E Tests**
  - Write Cypress/Playwright tests for the Patient Booking flow and Receptionist Check-in flow.
  - **Files**: `frontend/cypress/e2e/booking.cy.ts`, `frontend/cypress/e2e/checkin.cy.ts`
- [ ] **Task 7.4: Offline Resiliency Testing**
  - Write a test (or manual test script) to disable network in the browser and verify Dexie.js loads the read-only schedule.
  - **Files**: `frontend/cypress/e2e/offline.cy.ts`
- [ ] **Task 7.5: CI/CD Pipeline Setup**
  - Create GitHub Actions (or similar) to run tests, build the Vite PWA, and deploy static assets to AWS S3/CloudFront. Deploy FastAPI to AWS ECS/AppRunner.
  - **Files**: `.github/workflows/deploy.yml`, `infrastructure/main.tf` (if using Terraform)