# Clinic Modernization Platform (CMP) — Comprehensive Master Test Plan

**Document Owner:** Senior Software Test Quality Engineer (STQE)  
**Project:** Clinic Modernization Platform (CMP) Phase 1 MVP  
**Date:** 2026-06-04  

---

## 1. Executive Summary

This Master Test Plan defines the quality assurance strategy for the Clinic Modernization Platform (CMP). Given the critical nature of healthcare operations, strict NDPR compliance, and the unique infrastructural challenges in Nigeria (network instability, DND SMS restrictions), this plan outlines a robust testing architecture. It covers Unit, Integration, End-to-End (E2E), and Non-Functional testing, ensuring the system meets all functional requirements (FRs) and non-functional requirements (NFRs) defined in the SRD and Technical Specifications.

---

## 2. Test Strategy

The testing strategy follows the **Test Pyramid** model, heavily emphasizing fast, deterministic unit and integration tests, supported by critical E2E user journeys and specialized non-functional tests.

### 2.1 Unit Testing Layer
*   **Scope**: Core business logic, utility functions, and state machines isolated from external dependencies.
*   **Key Areas**:
    *   **Penalty Engine**: Calculation of rolling 90-day windows and tier transitions (Normal -> Tier 1 -> Tier 2 -> Tier 3).
    *   **OTP State Machine**: Expiry logic (10 mins), retry limits (max 5), and rate limiting.
    *   **RBAC Middleware**: Verification of JWT scopes against user roles (`patient`, `doctor`, `receptionist`, `admin`).
*   **Approach**: Mock all database calls, external APIs, and KMS interactions.

### 2.2 Integration Testing Layer
*   **Scope**: Interactions between the FastAPI backend, PostgreSQL database, Redis task queues, and external service adapters.
*   **Key Areas**:
    *   **Pessimistic Locking (FR-019)**: Validating `SELECT ... FOR UPDATE` behavior during concurrent booking requests.
    *   **Application-Level Encryption (ADR-003)**: Verifying AES-256-GCM encryption/decryption cycles using mocked AWS KMS endpoints.
    *   **Notification Failover (ADR-004)**: Testing the Celery/Redis worker chain (WhatsApp -> Termii -> Infobip) under simulated timeout conditions.
*   **Approach**: Use ephemeral Docker containers (Testcontainers) for PostgreSQL and Redis to ensure a clean state per test suite.

### 2.3 End-to-End (E2E) Testing Layer
*   **Scope**: Full user journeys from the React PWA frontend through the API gateway to the database.
*   **Key Areas**:
    *   Patient self-service booking and cancellation.
    *   Doctor clinical logging and emergency cross-branch access.
    *   Receptionist walk-in check-in workflows.
    *   **Offline Resiliency (NFR-004)**: Simulating network drops to verify Service Worker and IndexedDB (Dexie.js) read-only caching.
*   **Approach**: Automated browser testing using multiple browser contexts and simulated network conditions.

### 2.4 Non-Functional Testing
*   **Performance**: Load testing API endpoints to ensure DB search latency < 2.0s (NFR-001) under 100 concurrent users.
*   **Security**: Penetration testing, vulnerability scanning, and strict validation of NFR-008 (Admin lockout from clinical records).

---

## 3. Automation Framework & Setup

### 3.1 Toolchain Selection
*   **Backend (Python/FastAPI)**: `pytest`, `pytest-asyncio`, `httpx` (API client), `testcontainers` (DB/Redis), `moto` (AWS KMS mocking).
*   **Frontend (React/Vite)**: `vitest`, `React Testing Library`.
*   **E2E (Browser)**: `Playwright` (chosen for its native ability to simulate offline network conditions and multi-tab concurrency).
*   **Performance**: `k6` (scriptable load testing).

### 3.2 Framework Setup Instructions

**1. Backend Automation Setup**
```bash
# Navigate to backend directory
cd backend
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx testcontainers moto factory_boy

# Run tests with coverage
pytest --cov=app --cov-report=html tests/
```

**2. Frontend Automation Setup**
```bash
# Navigate to frontend directory
cd frontend
# Install test dependencies
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom

# Run unit tests
npm run test
```

**3. E2E Automation Setup (Playwright)**
```bash
# Navigate to e2e directory
mkdir e2e-tests && cd e2e-tests
npm init -y
npm install -D @playwright/test
npx playwright install

# Run E2E tests (headed mode for debugging)
npx playwright test --headed
```

**4. Directory Structure**
```text
tests/
├── backend/
│   ├── unit/                 # Isolated business logic tests
│   ├── integration/          # DB, Redis, and KMS tests
│   └── conftest.py           # Pytest fixtures (DB sessions, Testcontainers)
├── frontend/
│   ├── components/           # React component tests
│   └── hooks/                # Custom hook tests (e.g., useIndexedDB)
├── e2e/
│   ├── journeys/             # Playwright user flows
│   └── network/              # Offline & latency simulation tests
└── performance/
    └── load_tests.js         # k6 scripts
```

---

## 4. Critical Test Cases & Edge Cases

### 4.1 Core Feature: Concurrent Booking (Pessimistic Locking)
*   **Description**: Ensure no double-booking occurs when multiple users target the same doctor/time slot.
*   **Test Case**: `test_concurrent_booking_acquires_lock`
*   **Steps**:
    1. Seed a doctor availability shift (e.g., 09:00 - 09:30).
    2. Spawn 3 asynchronous `httpx` requests simultaneously targeting the exact same slot.
*   **Expected Result**: Exactly 1 request returns `201 Created`. The other 2 requests return `409 Conflict` ("Slot is no longer available").
*   **Edge Case**: Database lock timeout. If the transaction holds the lock for > 3.0s, the system must gracefully abort and return a `503` or `409` rather than deadlocking.

### 4.2 Core Feature: Application-Level Encryption (NDPR)
*   **Description**: Verify clinical records are encrypted at rest and inaccessible to admins.
*   **Test Case**: `test_clinical_record_encryption_and_admin_lockout`
*   **Steps**:
    1. Authenticate as `doctor`. POST a clinical record (notes, diagnosis).
    2. Query the PostgreSQL database directly (bypassing the ORM decryption layer).
    3. Authenticate as `admin` and attempt to GET the clinical record via API.
*   **Expected Result**:
    *   Direct DB query reveals only ciphertext in `encrypted_notes`.
    *   Admin API request returns `403 Forbidden`.
*   **Edge Case**: AWS KMS is unreachable. The system must return a `503 Service Unavailable` and **must not** fall back to saving plaintext records.

### 4.3 Core Feature: Offline Resiliency (PWA)
*   **Description**: Receptionists must view schedules during local internet outages.
*   **Test Case**: `test_pwa_offline_read_only_mode` (via Playwright)
*   **Steps**:
    1. Login as `receptionist`. Load the daily dashboard (caches data to IndexedDB).
    2. Use Playwright to sever the network: `await context.setOffline(true)`.
    3. Reload the page.
*   **Expected Result**: The page loads the PWA shell. A visual "Offline Mode - Read Only" banner appears. The daily schedule is visible. Attempting to book a new appointment shows a local error.
*   **Edge Case**: Token expiration while offline. Sensitive IndexedDB data must be purged if the JWT expires during the offline period.

### 4.4 Core Feature: Pluggable Notification Failover
*   **Description**: Ensure OTPs and reminders reach patients despite gateway failures.
*   **Test Case**: `test_notification_failover_chain`
*   **Steps**:
    1. Trigger an OTP request.
    2. Mock the WhatsApp API to return a `504 Gateway Timeout` after 15 seconds.
    3. Mock the Termii SMS API to return a `500 Internal Server Error`.
    4. Mock the Infobip SMS API to return `200 OK`.
*   **Expected Result**: The Celery worker catches the WhatsApp failure, routes to Termii, catches the Termii failure, routes to Infobip, and successfully logs the delivery channel as `sms_infobip`.
*   **Edge Case**: WhatsApp webhook confirmation is delayed by 20 seconds (past the 15s timeout). The system sends the SMS, and later receives the WhatsApp success. The audit log must record both, but the OTP remains valid.

### 4.5 Core Feature: Progressive Penalty Engine
*   **Description**: Restrict booking for repeat offenders.
*   **Test Case**: `test_tier3_booking_restriction_and_override`
*   **Steps**:
    1. Seed a patient with 3 late cancellations in the last 30 days.
    2. Patient cancels a 4th appointment 1 hour before start time.
    3. Patient attempts to book a new appointment online.
    4. Receptionist attempts to book the same appointment using "Override".
*   **Expected Result**: Patient self-service booking returns `403 Forbidden` (Tier 3 Restricted). Receptionist override succeeds and generates an audit log.
*   **Edge Case**: The 4th cancellation occurs exactly 2 hours and 1 minute before the appointment. The system must *not* penalize the patient, keeping them at Tier 2.

---

## 5. CI/CD Pipeline Testing Integration Strategy

The testing suite will be integrated into the CI/CD pipeline (e.g., GitHub Actions or GitLab CI) to enforce quality gates before deployment.

### 5.1 Pipeline Stages

1.  **Stage 1: Linting & Static Analysis (Pre-Build)**
    *   Run `flake8`, `black`, `mypy` (Backend).
    *   Run `eslint`, `prettier` (Frontend).
    *   Run `trivy` for container vulnerability scanning.
2.  **Stage 2: Unit Testing (Fast Feedback)**
    *   Execute Python and React unit tests.
    *   *Gate*: Fails if unit test coverage drops below 85%.
3.  **Stage 3: Integration Testing (Database & Services)**
    *   Spin up `docker-compose` with PostgreSQL and Redis.
    *   Run Alembic migrations (`alembic upgrade head`) to ensure schema validity.
    *   Execute backend integration tests.
4.  **Stage 4: E2E Testing (Nightly & Pre-Release)**
    *   Deploy to an ephemeral staging environment.
    *   Run Playwright E2E test suite across Chromium and WebKit.
5.  **Stage 5: Performance & Security (Pre-Release)**
    *   Run `k6` load tests against the staging API Gateway.
    *   *Gate*: Fails if p95 latency > 2.0s.

### 5.2 CI/CD Trigger Strategy
*   **On Pull Request (PR)**: Stages 1, 2, and 3.
*   **On Merge to `main`**: Stages 1, 2, 3, and 4.
*   **On Release Tag**: Stages 1 through 5.

---

## 6. Target STQE Metrics

To ensure the CMP meets its rigorous operational and clinical requirements, the QA team will track and enforce the following Quality Metrics:

| Metric Category | Target Threshold | Description / Rationale |
| :--- | :--- | :--- |
| **Code Coverage (Backend)** | **≥ 90%** | Overall line coverage. Core domains (Scheduler, Encryption, Penalty Engine) must have **100%** branch coverage. |
| **Code Coverage (Frontend)** | **≥ 80%** | Focus on state management, IndexedDB caching logic, and RBAC UI rendering. |
| **Test Pass Rate** | **100%** | No PR can be merged with failing tests. Flaky tests must be quarantined and resolved within 1 sprint. |
| **Flaky Test Rate** | **< 1%** | Measured over a 14-day rolling window in CI. High flakiness in E2E tests indicates race conditions. |
| **Performance (Search Latency)** | **p95 < 2.0s** | Under 100 concurrent users (NFR-001). Measured via `k6` in the CI pipeline. |
| **Performance (Page Load)** | **< 3.0s** | Time to Interactive (TTI) on simulated 3G network (NFR-002). |
| **Defect Density** | **< 0.5 / KLOC** | Less than 0.5 critical/high bugs per 1,000 lines of code found in Staging/UAT. |
| **MTTR (Mean Time to Resolve)** | **< 24 Hours** | For any `Severity 1` (e.g., DB lock contention, KMS failure) defects found during testing phases. |