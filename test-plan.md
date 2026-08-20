# Clinic Modernization Platform (CMP) — Master Test Plan

**Document Owner**: Senior Software Test Quality Engineer (STQE)  
**Project**: Clinic Modernization Platform (CMP) Phase 1 MVP  
**Date**: 2026-06-04  

---

## 1. Introduction

This document outlines the comprehensive Test Plan for the Clinic Modernization Platform (CMP). It defines the testing strategy, automation framework, critical test scenarios, CI/CD integration, and quality metrics required to ensure a highly reliable, secure, and performant release. The system's critical constraints—such as strict NDPR data privacy, concurrent booking race conditions, and offline resiliency—dictate a rigorous, multi-layered testing approach.

---

## 2. Test Strategy

The testing strategy follows the Testing Pyramid, ensuring fast feedback loops and high confidence in system stability.

### 2.1 Unit Testing Layer
*   **Backend (FastAPI)**: Focus on isolated business logic.
    *   *Targets*: Cancellation Penalty Engine (90-day rolling window logic), OTP generation and rate-limiting, RBAC permission validators, and Notification Strategy selection.
    *   *Mocking*: Database sessions, Redis queues, and external API clients (AWS KMS, WhatsApp, Termii) must be mocked.
*   **Frontend (React/Vite)**: Focus on component rendering and state management.
    *   *Targets*: Form validations, penalty warning banners, and Dexie.js (IndexedDB) wrapper functions.

### 2.2 Integration Testing Layer
*   **Database & Concurrency**: Validate PostgreSQL pessimistic locking (`SELECT ... FOR UPDATE`) using real database instances (via Testcontainers) to ensure race conditions are prevented.
*   **Security & Encryption**: Verify that the `ClinicalService` correctly encrypts/decrypts data using a mocked AWS KMS (e.g., LocalStack) and that raw database queries return ciphertext.
*   **Async Workers**: Validate the Celery/Redis task queue for the Pluggable Notification Service, ensuring the failover chain (WhatsApp -> Termii -> Infobip) executes correctly on simulated timeouts.

### 2.3 End-to-End (E2E) Testing Layer
*   **Critical User Journeys**: Automate full workflows from the browser to the database.
    *   *Targets*: Patient self-service booking, Doctor clinical logging, Receptionist check-in, and Admin schedule overrides.
*   **Offline Resiliency**: Utilize browser automation to simulate network drops and verify Service Worker and IndexedDB read-only fallbacks.

### 2.4 Non-Functional Testing
*   **Performance**: Load testing API endpoints to ensure sub-2.0s search latency under 100 concurrent users.
*   **Security**: Automated dynamic application security testing (DAST) for RBAC bypass and data leakage.

---

## 3. Automation Framework & Setup

To enable coding agents and developers to execute tests seamlessly, we will use a modern, JavaScript/Python-based automation stack.

### 3.1 Toolchain Selection
*   **Backend Unit/Integration**: `pytest`, `pytest-asyncio`, `httpx` (for FastAPI testing), `testcontainers` (for isolated PostgreSQL/Redis).
*   **Frontend Unit**: `vitest`, `React Testing Library`.
*   **E2E Testing**: `Playwright` (Chosen over Cypress for superior multi-tab concurrency testing and native offline network emulation).
*   **Performance Testing**: `k6` (JavaScript-based load testing).

### 3.2 Setup Instructions for Coding Agents

**Backend Setup (`/backend`)**
```bash
# Install testing dependencies
pip install pytest pytest-asyncio pytest-cov httpx testcontainers responses

# Run backend tests with coverage
pytest tests/ --cov=app --cov-report=term-missing
```

**Frontend Setup (`/frontend`)**
```bash
# Install testing dependencies
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom

# Run frontend unit tests
npm run test
```

**E2E Setup (`/e2e`)**
```bash
# Install Playwright
npm init playwright@latest

# Run E2E tests (ensure local dev servers are running)
npx playwright test
```

### 3.3 Directory Structure
```text
/tests
  /backend
    /unit           # Isolated Python logic tests
    /integration    # DB locks, KMS, Redis workers
  /frontend
    /unit           # React components, Dexie.js logic
  /e2e
    /journeys       # Playwright full-stack tests
    /offline        # Playwright network-emulation tests
  /performance
    load_test.js    # k6 scripts
```

---

## 4. Critical Test Cases & Edge Cases

### 4.1 Scheduling & Concurrency (FR-004, FR-019)
| ID | Scenario | Type | Steps / Edge Case Focus | Expected Result |
|:---|:---|:---|:---|:---|
| **TC-01** | Concurrent Booking Lock | Integration | Fire 3 simultaneous `POST /appointments` requests for the exact same Doctor/Time slot. | 1 request succeeds (HTTP 201). 2 requests fail (HTTP 409 Conflict). No deadlocks occur. |
| **TC-02** | Shift Boundary Booking | Unit/Int | Attempt to book an appointment that ends exactly at the minute the doctor's shift ends. | Booking succeeds. |
| **TC-03** | Cross-Branch Conflict | E2E | Doctor scheduled at Branch A (9AM-1PM). Receptionist attempts to book Doctor at Branch B at 12:30 PM. | Booking is rejected with a cross-branch conflict error. |

### 4.2 Notification Failover Engine (INT-001 to INT-004)
| ID | Scenario | Type | Steps / Edge Case Focus | Expected Result |
|:---|:---|:---|:---|:---|
| **TC-04** | WhatsApp Timeout Fallback | Integration | Trigger OTP. Mock WhatsApp API to delay response by 16 seconds (Timeout is 15s). | Worker catches timeout, aborts WhatsApp, successfully routes to Termii SMS. DB logs `delivery_channel='sms_termii'`. |
| **TC-05** | Total Gateway Failure | Integration | Mock WhatsApp, Termii, and Infobip to all return HTTP 500. | System logs critical failure, updates OTP status to `failed`, does not crash the main API thread. |

### 4.3 Cancellation Penalty Engine (FR-012 to FR-014)
| ID | Scenario | Type | Steps / Edge Case Focus | Expected Result |
|:---|:---|:---|:---|:---|
| **TC-06** | Rolling 90-Day Expiration | Unit | Patient has 3 late cancellations. The 1st cancellation occurred 91 days ago. Patient cancels again today. | Total active incidents = 3. Patient remains in Tier 2 (Soft Flag), NOT Tier 3. |
| **TC-07** | Admin Override Tier 3 | E2E | Patient is Tier 3 (Restricted). Patient tries to book online (Blocked). Admin logs in and books for them using "Override". | Admin booking succeeds. Audit log records the Admin ID and override action. |

### 4.4 Clinical Records & Encryption (NFR-006, NFR-008)
| ID | Scenario | Type | Steps / Edge Case Focus | Expected Result |
|:---|:---|:---|:---|:---|
| **TC-08** | KMS Encryption Verification | Integration | Doctor saves clinical note. Query the PostgreSQL DB directly bypassing the ORM. | `encrypted_notes` column contains AES-256-GCM ciphertext. Plaintext is nowhere in the DB. |
| **TC-09** | KMS Unavailability | Integration | Mock AWS KMS to return HTTP 503. Doctor attempts to save a note. | API returns HTTP 503. Note is NOT saved in plaintext. Transaction rolls back safely. |
| **TC-10** | Admin Data Separation | E2E | Login as System Admin. Attempt to navigate to a patient's clinical history URL or hit the API. | HTTP 403 Forbidden. UI shows access denied. |

### 4.5 Offline Resiliency (NFR-004)
| ID | Scenario | Type | Steps / Edge Case Focus | Expected Result |
|:---|:---|:---|:---|:---|
| **TC-11** | PWA Offline Read-Only | E2E | Load Receptionist dashboard. Use Playwright to set `context.setOffline(true)`. Refresh page. | Page loads via Service Worker. Schedule populates from IndexedDB. UI shows "Offline Mode - Read Only" banner. |
| **TC-12** | Offline Write Prevention | E2E | While offline, attempt to check-in a patient or book a slot. | UI disables action buttons or intercepts request to show "Action unavailable offline" toast. |

---

## 5. CI/CD Pipeline Integration Strategy

The testing framework will be integrated into GitHub Actions (or GitLab CI) to enforce quality gates on every Pull Request (PR) and merge to the `main` branch.

### 5.1 Pipeline Stages
1.  **Lint & Format**: `ruff` (Python), `eslint` & `prettier` (React). Fails fast on syntax issues.
2.  **Security Scan**: `bandit` (Python), `npm audit`, and `trivy` (Container scanning).
3.  **Unit Tests**: Run backend and frontend unit tests in parallel.
4.  **Integration Tests**: Spin up Docker services (`postgres`, `redis`, `localstack`) via GitHub Actions services. Run backend integration tests.
5.  **E2E Tests**: Build the Vite frontend, start the FastAPI server, and run Playwright tests in headless Chromium/WebKit browsers.
6.  **Quality Gate**: SonarQube or Codecov checks if coverage metrics are met.

### 5.2 CI/CD Rules
*   **PR Blocking**: A PR cannot be merged unless all pipeline stages pass and the Quality Gate is green.
*   **Database Migrations**: CI must run `alembic upgrade head` on an empty database before integration tests to ensure migration scripts are valid.

---

## 6. Target STQE Metrics

To objectively measure the quality of the CMP MVP, the following metrics are established as hard targets for the engineering and QA agents:

| Metric | Target | Description |
|:---|:---|:---|
| **Backend Code Coverage** | **≥ 85%** | Minimum line coverage for FastAPI backend, strictly enforced on `Scheduler` and `ClinicalService` modules. |
| **Frontend Code Coverage** | **≥ 80%** | Minimum line coverage for React components, focusing on state management and Dexie.js logic. |
| **Test Pass Rate** | **100%** | No flaky tests permitted in the `main` branch. 100% pass rate required for deployment. |
| **API Response Time (p95)** | **< 2.0s** | 95th percentile of database search and booking queries must resolve in under 2 seconds (NFR-001). |
| **UI Load Time (3G)** | **< 3.0s** | Time to Interactive (TTI) for the PWA shell over simulated 3G network (NFR-002). |
| **Defect Density** | **< 0.5 / KLOC** | Less than 0.5 critical/high bugs per 1000 lines of code discovered in Staging. |
| **Zero-Trust Compliance** | **Pass** | 0 instances of plaintext clinical data found in database dumps during security audits. |