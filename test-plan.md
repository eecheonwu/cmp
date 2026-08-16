# Clinic Modernization Platform (CMP) — Master Test Plan

**Author**: Senior Software Test Quality Engineer (STQE)
**Project**: Clinic Modernization Platform (Phase 1 MVP)
**Date**: 2026-06-04

This document outlines the comprehensive testing strategy, automation framework, critical test cases, CI/CD integration, and quality metrics for the CMP. It is designed to be consumed by both human engineers and autonomous coding agents to ensure the delivery of a highly reliable, secure, and performant system.

---

## 1. Test Strategy

The testing strategy follows the **Test Pyramid** approach, ensuring fast feedback loops and high confidence in the system's core business logic, concurrency handling, and offline capabilities.

### 1.1 Unit Testing Layer
*   **Backend (FastAPI)**: Focus on isolated business logic. Mock the database, Redis, and external APIs (AWS KMS, WhatsApp, Termii).
    *   *Targets*: Penalty tier calculations, OTP generation logic, RBAC validation, encryption/decryption utility functions.
*   **Frontend (React/Vite)**: Focus on component rendering, form validation, and state management.
    *   *Targets*: UI components, custom hooks, Dexie.js (IndexedDB) wrapper logic (mocked).

### 1.2 Integration Testing Layer
*   **Backend**: Test the integration between FastAPI, PostgreSQL, and Redis. **Do not mock the database here.** Use ephemeral databases (e.g., Testcontainers) to validate SQL queries, ORM models, and most importantly, **pessimistic locking (`SELECT ... FOR UPDATE`)**.
*   **External Services**: Use WireMock or `responses`/`httpx-mock` to simulate AWS KMS, WhatsApp Cloud API, and SMS gateways to validate the failover strategy and timeout handling.

### 1.3 End-to-End (E2E) Testing Layer
*   **Full Stack**: Test the compiled Vite PWA against a fully running FastAPI backend and PostgreSQL instance.
*   **Browser Automation**: Simulate real user journeys (Patient booking, Doctor consultation logging).
*   **Network Simulation**: Intercept and drop network requests to validate the **2-hour offline read-only mode** and Service Worker caching.

---

## 2. Automation Framework & Setup

### 2.1 Backend Automation Stack
*   **Framework**: `pytest` (with `pytest-asyncio` for async endpoints).
*   **HTTP Client**: `httpx` (using `AsyncClient` for FastAPI testing).
*   **Database Testing**: `testcontainers-python` (spins up isolated PostgreSQL and Redis Docker containers per test session).
*   **Mocking**: `pytest-mock`, `respx` (for mocking external HTTP calls to WhatsApp/Termii/KMS).

**Setup Instructions (Backend Agent):**
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx testcontainers respx pytest-mock

# Run tests with coverage
pytest --cov=app --cov-report=term-missing tests/
```

### 2.2 Frontend Automation Stack
*   **Unit/Component Framework**: `Vitest` + `React Testing Library`.
*   **E2E Framework**: `Playwright` (Chosen for its superior handling of offline mode simulation, Service Workers, and mobile viewports).

**Setup Instructions (Frontend Agent):**
```bash
# Install unit test dependencies
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom

# Install E2E dependencies
npm install -D @playwright/test
npx playwright install

# Run tests
npm run test:unit    # Executes Vitest
npm run test:e2e     # Executes Playwright
```

---

## 3. Critical Test Cases & Edge Cases

### 3.1 Scheduling & Concurrency (FR-019, NFR-001)
*   **TC-01: Concurrent Booking Race Condition (Critical)**
    *   *Scenario*: Two users attempt to book the exact same doctor time slot at the exact same millisecond.
    *   *Action*: Fire two concurrent asynchronous `POST /api/v1/appointments` requests using `asyncio.gather`.
    *   *Expected Result*: The database pessimistic lock (`with_for_update()`) queues the transactions. One request returns `201 Created`. The second request returns `409 Conflict` ("Slot is no longer available").
*   **TC-02: Cross-Branch Double Booking (FR-004)**
    *   *Scenario*: Doctor is scheduled at Branch A. Receptionist tries to book them at Branch B for the same time.
    *   *Expected Result*: System rejects with `400 Bad Request` (Doctor unavailable at this branch).

### 3.2 Notification Failover Engine (INT-004)
*   **TC-03: WhatsApp Timeout to SMS Fallback**
    *   *Scenario*: Patient requests OTP. WhatsApp API takes > 15 seconds to respond or returns a 500 error.
    *   *Action*: Mock WhatsApp API to delay response by 16 seconds.
    *   *Expected Result*: Celery/Redis worker catches the timeout, updates `delivery_channel` to `sms_termii`, and successfully fires the Termii SMS API mock.
*   **TC-04: Complete Notification Gateway Failure**
    *   *Scenario*: WhatsApp, Termii, and Infobip all return 500 errors.
    *   *Expected Result*: Task is marked as `failed` in `NotificationLog`, and an alert is logged for system admins. System does not crash.

### 3.3 Offline Resiliency (NFR-004)
*   **TC-05: PWA Offline Read-Only Mode**
    *   *Scenario*: Receptionist is viewing the daily schedule. Internet connection drops.
    *   *Action*: Use Playwright to set `context.setOffline(true)`. Reload the page.
    *   *Expected Result*: Page loads instantly via Service Worker. Schedule data is populated from IndexedDB (Dexie.js). UI displays "Offline Mode - Read Only" banner. Attempting to create a new booking disables the submit button or shows a network error.

### 3.4 Cancellation Penalty Engine (FR-012 - FR-014)
*   **TC-06: Tier 3 Booking Restriction**
    *   *Scenario*: Patient has 3 late cancellations in the last 90 days. They attempt a 4th late cancellation.
    *   *Expected Result*: Status updates to `Cancelled`. Patient profile tier updates to `Tier 3`.
    *   *Follow-up Action*: Patient attempts to book a new appointment online.
    *   *Expected Result*: Booking blocked. UI prompts user to contact the clinic.
*   **TC-07: Admin Override of Tier 3 (FR-015)**
    *   *Scenario*: Receptionist attempts to book an appointment for the Tier 3 patient from TC-06.
    *   *Expected Result*: Receptionist sees a warning but can click "Override Restriction". Booking succeeds, and `security_audit_logs` records the override.

### 3.5 Security & Encryption (NFR-006, NFR-008)
*   **TC-08: Application-Level Column Encryption**
    *   *Scenario*: Doctor saves a clinical note.
    *   *Action*: Bypass the API and query the PostgreSQL database directly using a raw SQL client.
    *   *Expected Result*: The `encrypted_notes` and `encrypted_diagnosis` columns contain AES-256-GCM ciphertext. No plaintext medical data is visible.
*   **TC-09: RBAC Clinical Data Access**
    *   *Scenario*: User with `receptionist` role attempts to `GET /api/v1/clinical-records/patient/{id}`.
    *   *Expected Result*: API returns `403 Forbidden`.

---

## 4. CI/CD Pipeline Integration Strategy

The testing suite will be integrated into a standard CI/CD pipeline (e.g., GitHub Actions) to enforce quality gates on every Pull Request (PR) and merge to `main`.

### Pipeline Stages:
1.  **Code Quality & Linting**:
    *   Backend: `ruff` (linting/formatting), `mypy` (type checking).
    *   Frontend: `eslint`, `prettier`, `tsc` (TypeScript compiler check).
2.  **Security Scanning (Shift-Left)**:
    *   Backend: `bandit` (Python security vulnerabilities).
    *   Dependencies: `npm audit` and `pip-audit`.
3.  **Unit & Integration Testing**:
    *   Spin up PostgreSQL and Redis service containers in the CI runner.
    *   Execute `pytest` and `vitest`.
    *   *Gate*: Fail pipeline if tests fail or coverage drops below target.
4.  **E2E Testing**:
    *   Build the Vite frontend and start the FastAPI server in the background.
    *   Run Playwright tests against the local build.
    *   Upload Playwright HTML reports and trace files as CI artifacts on failure.

**Example GitHub Actions Job Snippet (Backend Integration):**
```yaml
test-backend:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:16
      env:
        POSTGRES_USER: test_user
        POSTGRES_PASSWORD: test_password
        POSTGRES_DB: cmp_test_db
      ports:
        - 5432:5432
    redis:
      image: redis:7
      ports:
        - 6379:6379
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - run: pip install -r requirements-test.txt
    - run: pytest --cov=app --cov-fail-under=85
```

---

## 5. Target STQE Metrics

To ensure the MVP meets production-grade standards, the following Quality Engineering metrics must be achieved before the Phase 1 release:

| Metric Category | Target Threshold | Description |
| :--- | :--- | :--- |
| **Code Coverage (Backend)** | **≥ 85%** overall<br>**100%** for core logic | 100% coverage required for `Scheduling Engine`, `Encryption Service`, and `Penalty Engine`. |
| **Code Coverage (Frontend)** | **≥ 80%** | Focus on state management, offline caching logic, and form validations. |
| **Test Pass Rate** | **100%** | No flaky tests permitted in the `main` branch. Flaky tests must be quarantined and fixed. |
| **API Latency (NFR-001)** | **< 2.0s** (p95) | 95th percentile of search/booking API requests must complete in under 2 seconds under 100 CCU load. |
| **PWA Load Time (NFR-002)** | **< 3.0s** | First Contentful Paint (FCP) and Time to Interactive (TTI) must be under 3 seconds on simulated 3G networks (via Lighthouse/Playwright). |
| **Security Vulnerabilities** | **0 Critical/High** | Zero known critical or high vulnerabilities in application code or dependencies (via Bandit/Snyk). |