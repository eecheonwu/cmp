# Clinic Modernization Platform (CMP) — Exhaustive Task Plan

This document outlines the chronological, actionable development tasks required to implement the Clinic Modernization Platform (CMP) based on the provided architecture, ADRs, and technical specifications. 

---

## Phase 1: Foundation & Infrastructure Setup

Establish the base repositories, container orchestration, and foundational configurations for both backend and frontend.

- [ ] **Task 1.1: Initialize Monorepo & Version Control**
  - Create root directory structure (`/backend`, `/frontend`, `/infrastructure`).
  - Initialize Git repository and `.gitignore`.
  - *Files:* `.gitignore`, `README.md`
- [ ] **Task 1.2: Setup Local Docker Environment**
  - Configure `docker-compose.yml` to spin up PostgreSQL 16+ and Redis.
  - Configure environment variables for local development.
  - *Files:* `docker-compose.yml`, `.env.example`
- [ ] **Task 1.3: Initialize FastAPI Backend**
  - Setup Python environment (e.g., Poetry or pip).
  - Install core dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `redis`, `celery`, `boto3`, `cryptography`.
  - Create base FastAPI application instance and health check endpoint.
  - *Files:* `backend/pyproject.toml` (or `requirements.txt`), `backend/app/main.py`, `backend/app/core/config.py`
- [ ] **Task 1.4: Initialize React + Vite Frontend**
  - Scaffold React app using Vite (`npm create vite@latest frontend --template react-ts`).
  - Install core dependencies: `react-router-dom`, `axios`, `dexie`, `workbox-window`, `tailwindcss`, `lucide-react`.
  - Setup Tailwind CSS configuration.
  - *Files:* `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.js`, `frontend/src/main.tsx`

---

## Phase 2: Database & Data Models

Implement the PostgreSQL schema using SQLAlchemy/SQLModel and configure Alembic for migrations.

- [ ] **Task 2.1: Configure Database Connection**
  - Setup SQLAlchemy async engine and session maker.
  - *Files:* `backend/app/db/session.py`, `backend/app/db/base_class.py`
- [ ] **Task 2.2: Define PostgreSQL Enums**
  - Create SQLAlchemy Enum types for `UserRole`, `AppointmentStatus`, and `PaymentStatus`.
  - *Files:* `backend/app/models/enums.py`
- [ ] **Task 2.3: Implement User & Profile Models**
  - Create `User` model (id, phone, email, password_hash, role).
  - Create `PatientProfile` model with foreign key to `User`.
  - *Files:* `backend/app/models/user.py`, `backend/app/models/patient.py`
- [ ] **Task 2.4: Implement Scheduling Models**
  - Create `DoctorAvailability` model with time-bound constraints (`start_datetime < end_datetime`).
  - Create `Appointment` model with status, payment state, and booking source.
  - *Files:* `backend/app/models/scheduling.py`
- [ ] **Task 2.5: Implement Clinical & Security Models**
  - Create `ClinicalRecord` model with `encrypted_notes`, `encrypted_diagnosis`, `encrypted_prescriptions`, and `kms_key_version`.
  - Create `SecurityAuditLog` model (immutable audit trail).
  - Create `VerificationOTP` model for channel-agnostic verification.
  - *Files:* `backend/app/models/clinical.py`, `backend/app/models/security.py`
- [ ] **Task 2.6: Generate Initial Alembic Migration**
  - Initialize Alembic (`alembic init alembic`).
  - Configure `env.py` to load models.
  - Generate and apply the first migration.
  - *Files:* `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/001_initial_schema.py`

---

## Phase 3: Security, Cryptography & Core Services

Implement RBAC, AWS KMS envelope encryption, and the OTP generation engine.

- [ ] **Task 3.1: Implement JWT Authentication & RBAC**
  - Create password hashing utilities (bcrypt).
  - Implement JWT token generation and validation.
  - Create FastAPI dependency `get_current_user` and `RoleChecker` for RBAC enforcement.
  - *Files:* `backend/app/core/security.py`, `backend/app/api/deps.py`
- [ ] **Task 3.2: Implement AWS KMS Envelope Encryption**
  - Create `KMSEncryptor` service using `boto3`.
  - Implement `generate_data_key` and `decrypt_data_key`.
  - Implement AES-256-GCM encryption/decryption logic for clinical text.
  - *Files:* `backend/app/services/kms_service.py`, `backend/app/services/crypto_service.py`
  - *Code Snippet (Crypto Service):*
    ```python
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import os

    def encrypt_clinical_text(plaintext: str, plaintext_dek: bytes) -> bytes:
        aesgcm = AESGCM(plaintext_dek)
        nonce = os.urandom(12) # Probabilistic encryption (IV)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return nonce + ciphertext # Prepend nonce for decryption

    def decrypt_clinical_text(encrypted_data: bytes, plaintext_dek: bytes) -> str:
        aesgcm = AESGCM(plaintext_dek)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
    ```
- [ ] **Task 3.3: Implement OTP Verification Engine**
  - Create logic to generate 6-digit OTPs.
  - Hash OTPs before saving to `VerificationOTP` table.
  - Implement rate-limiting (max 3 requests / 15 mins) and expiry validation (10 mins).
  - *Files:* `backend/app/services/otp_service.py`

---

## Phase 4: Backend API & Business Logic

Develop the REST API endpoints, enforcing transactional locks and business rules.

- [ ] **Task 4.1: Auth & Verification Router**
  - `POST /api/v1/auth/register`: Create user, trigger OTP.
  - `POST /api/v1/auth/verify-request`: Generate and enqueue OTP task.
  - `POST /api/v1/auth/verify`: Validate hashed OTP, mark `is_used = True`.
  - `POST /api/v1/auth/login`: Return JWT token.
  - *Files:* `backend/app/api/routers/auth.py`
- [ ] **Task 4.2: Scheduling Engine (Pessimistic Locking)**
  - `POST /api/v1/appointments`: Implement concurrent booking protection using `SELECT ... FOR UPDATE`.
  - *Files:* `backend/app/api/routers/appointments.py`, `backend/app/services/scheduling_service.py`
  - *Code Snippet (Locking Logic):*
    ```python
    async with db.begin():
        # Lock doctor availability shift
        shift = await db.execute(
            select(DoctorAvailability)
            .filter(DoctorAvailability.doctor_id == req.doctor_id, ...)
            .with_for_update()
        )
        if not shift.first(): raise HTTPException(400, "Doctor unavailable")
        
        # Lock conflicting appointments
        conflict = await db.execute(
            select(Appointment)
            .filter(Appointment.doctor_id == req.doctor_id, Appointment.status == 'booked', ...)
            .with_for_update()
        )
        if conflict.first(): raise HTTPException(409, "Slot no longer available")
        
        # Insert appointment
    ```
- [ ] **Task 4.3: Cancellation Penalty Engine**
  - `POST /api/v1/appointments/{id}/cancel`: Implement cancellation logic.
  - Calculate time difference. If < 2 hours and not emergency, increment penalty count.
  - Implement Tier 1 (Warning), Tier 2 (Soft Flag), Tier 3 (Restricted) logic based on rolling 90-day window.
  - *Files:* `backend/app/services/penalty_service.py`
- [ ] **Task 4.4: Clinical Records Router**
  - `POST /api/v1/clinical-records`: Enforce `doctor` role. Fetch KMS DEK, encrypt notes/diagnosis, insert record, and insert `SecurityAuditLog` in the same transaction.
  - `GET /api/v1/clinical-records/patient/{id}`: Enforce `doctor` role. Fetch encrypted data, decrypt via KMS DEK, insert `SecurityAuditLog` (Emergency Cross-Branch Access).
  - *Files:* `backend/app/api/routers/clinical.py`
- [ ] **Task 4.5: Front Desk & Management Routers**
  - `POST /api/v1/appointments/{id}/check-in`: Update status to `Checked In`.
  - `GET /api/v1/reports/daily`: Aggregate daily stats for Branch Managers.
  - *Files:* `backend/app/api/routers/reception.py`, `backend/app/api/routers/reports.py`

---

## Phase 5: Background Workers & Integrations

Implement the asynchronous task queue and the pluggable notification failover system.

- [ ] **Task 5.1: Setup Celery & Redis**
  - Configure Celery app with Redis as broker and backend.
  - *Files:* `backend/app/worker/celery_app.py`
- [ ] **Task 5.2: Implement Notification Strategy Interface**
  - Define `NotificationService` abstract base class with `send_message` method.
  - *Files:* `backend/app/services/notifications/base.py`
- [ ] **Task 5.3: Implement Provider Adapters**
  - Create `WhatsAppCloudAPIClient` (Primary).
  - Create `TermiiSMSClient` (Fallback 1).
  - Create `InfobipSMSClient` (Fallback 2).
  - *Files:* `backend/app/services/notifications/whatsapp.py`, `backend/app/services/notifications/termii.py`, `backend/app/services/notifications/infobip.py`
- [ ] **Task 5.4: Implement Failover Task Logic**
  - Create Celery task `deliver_notification_task`.
  - Implement try/except block: Try WhatsApp -> on timeout/error (15s) -> Try Termii -> on error -> Try Infobip.
  - Update `VerificationOTP` delivery channel status in DB.
  - *Files:* `backend/app/worker/tasks.py`

---

## Phase 6: Frontend Foundation & Offline Caching

Setup the PWA shell, API clients, and local IndexedDB storage for offline resilience.

- [ ] **Task 6.1: Configure Vite PWA Plugin**
  - Setup `vite-plugin-pwa` for Service Worker generation.
  - Configure caching strategies for static assets (HTML, CSS, JS, Fonts).
  - *Files:* `frontend/vite.config.ts`, `frontend/public/manifest.json`
- [ ] **Task 6.2: Setup Dexie.js (IndexedDB)**
  - Initialize Dexie database `ClinicOfflineDB`.
  - Define schema for caching `appointments` and `doctor_shifts`.
  - *Files:* `frontend/src/db/offlineDb.ts`
- [ ] **Task 6.3: Implement API Client & Interceptors**
  - Setup Axios instance.
  - Add request interceptor to attach JWT token.
  - Add response interceptor to handle 401 Unauthorized (logout).
  - *Files:* `frontend/src/api/client.ts`
- [ ] **Task 6.4: Implement Offline Sync Hook**
  - Create a React hook `useOfflineSync` that fetches the current day's schedule and writes it to Dexie.js.
  - Listen for `window.addEventListener('offline')` and toggle global offline state.
  - *Files:* `frontend/src/hooks/useOfflineSync.ts`, `frontend/src/context/NetworkContext.tsx`

---

## Phase 7: Frontend Features & UI

Build the user interfaces for Patients, Doctors, and Receptionists.

- [ ] **Task 7.1: Authentication UI**
  - Build Login, Registration, and OTP Verification screens.
  - Handle channel-agnostic messaging ("We've sent a code to your phone").
  - *Files:* `frontend/src/pages/auth/Login.tsx`, `frontend/src/pages/auth/Register.tsx`, `frontend/src/pages/auth/VerifyOTP.tsx`
- [ ] **Task 7.2: Patient Dashboard & Booking Flow**
  - Build Branch, Doctor, and Time-slot selection UI.
  - Implement Tier 1/Tier 2 warning banners on the booking/cancellation screens.
  - Implement Tier 3 block screen ("Please contact clinic").
  - *Files:* `frontend/src/pages/patient/Dashboard.tsx`, `frontend/src/pages/patient/BookAppointment.tsx`
- [ ] **Task 7.3: Doctor Workspace**
  - Build daily schedule view.
  - Build Clinical Consultation Form (Notes, Diagnosis, Prescriptions).
  - *Files:* `frontend/src/pages/doctor/Schedule.tsx`, `frontend/src/pages/doctor/ConsultationForm.tsx`
- [ ] **Task 7.4: Receptionist Dashboard**
  - Build daily appointment list with "Check-In" buttons.
  - Build Walk-in registration and Admin Override booking flow.
  - *Files:* `frontend/src/pages/reception/Dashboard.tsx`, `frontend/src/pages/reception/WalkInBooking.tsx`
- [ ] **Task 7.5: Offline Mode UI**
  - Build a global "Offline Mode - Read Only" warning banner.
  - Modify Receptionist/Doctor dashboards to query Dexie.js instead of Axios when offline.
  - *Files:* `frontend/src/components/OfflineBanner.tsx`, `frontend/src/pages/doctor/Schedule.tsx` (update logic)

---

## Phase 8: Testing & QA

Execute automated tests to validate concurrency, security, and offline capabilities.

- [ ] **Task 8.1: Backend Unit & Integration Tests**
  - Write `pytest` for Cancellation Penalty Engine (verify Tier transitions).
  - Write `pytest` for Concurrent Booking (simulate concurrent requests to verify HTTP 409).
  - Write `pytest` for KMS Encryption (verify DB stores ciphertext, not plaintext).
  - *Files:* `backend/tests/test_penalty_engine.py`, `backend/tests/test_concurrency.py`, `backend/tests/test_crypto.py`
- [ ] **Task 8.2: Background Worker Tests**
  - Mock WhatsApp and Termii APIs.
  - Test Celery failover chain ensures Termii is called if WhatsApp fails.
  - *Files:* `backend/tests/test_notifications.py`
- [ ] **Task 8.3: Frontend E2E & Offline Tests**
  - Write Cypress/Playwright tests for Patient Booking flow.
  - Write test to simulate network disconnect and verify Dexie.js loads cached schedule.
  - *Files:* `frontend/cypress/e2e/booking.cy.ts`, `frontend/cypress/e2e/offline.cy.ts`
- [ ] **Task 8.4: Security & Compliance Checks**
  - Verify `SecurityAuditLog` entries are created on clinical record reads/writes.
  - Verify System Admin role receives HTTP 403 on `/api/v1/clinical-records`.
  - *Files:* `backend/tests/test_security_audit.py`