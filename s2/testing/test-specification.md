# Test Specification

## 1. Introduction
- **Purpose**: To define the testing approach, methodologies, and test cases required to validate the Clinic Modernization Platform (CMP) against its functional and non-functional requirements.
- **Scope**: In-scope testing includes Patient Account & Authentication, Scheduling & Appointment Engine, Clinical Records, Front Desk Operations, Management Dashboards, and Integrations (Notifications). Out-of-scope for Phase 1 includes native mobile app testing, video telemedicine, and payment gateway processing.
- **Reference Documents**: 
  - [Software Requirements Document](file:///C:/Users/DELL/Documents/GitHub/cmp/software_requirements_document.md)
  - [Technical Specification](file:///C:/Users/DELL/Documents/GitHub/cmp/technical_specification.md)
  - [C4 Architecture Models](file:///C:/Users/DELL/Documents/GitHub/cmp/c4_architecture_models.md)
  - [UML Diagrams](file:///C:/Users/DELL/Documents/GitHub/cmp/uml_diagrams.md)

## 2. Test Strategy
- **Testing Levels**:
  - **Unit Testing**: Core business logic such as Cancellation Penalty Engine, OTP Rate Limiting, and Booking Validation.
  - **Integration Testing**: Database pessimistic locking (PostgreSQL), API Gateway routes, AWS KMS integrations, and Pluggable Notification Service (Redis/Celery workers).
  - **End-to-End (E2E) Testing**: Critical user journeys via the React PWA frontend (Patient self-service booking, Doctor clinical logging, Receptionist check-in).
  - **System/Non-Functional Testing**: Offline resiliency (Service Worker caching), search latency, load speed, and NDPR compliance security testing.
- **Test Environments**:
  - **DEV**: Local environments for unit and early integration tests.
  - **STAGING**: Cloud-hosted environment identical to production for E2E, performance, and security testing.
  - **PROD**: Post-deployment smoke testing only.
- **Tools & Frameworks**:
  - **Unit/Integration**: `pytest` (FastAPI backend), `vitest` / `Jest` (React frontend).
  - **E2E Testing**: `Cypress` or `Playwright`.
  - **Load Testing**: `k6` or `Locust`.

## 3. Test Scenarios & Cases

### 3.1 Patient Account & Authentication
- **TC-01: Patient Registration and OTP Verification (WhatsApp-First Fallback)**
  - **Type**: Integration / E2E
  - **Preconditions**: Patient has an active Nigerian phone number.
  - **Steps**: Patient submits registration details -> OTP is sent via WhatsApp -> (Simulate WhatsApp failure) -> OTP sent via Termii SMS -> Patient verifies OTP.
  - **Expected Result**: System creates patient profile and logs verification routing channels correctly.
  - **Artifact Traceability**: FR-001, OQ-002, INT-004

### 3.2 Patient Scheduling & Appointment Engine
- **TC-02: Concurrent Booking with Pessimistic Locking**
  - **Type**: Integration (Concurrency)
  - **Preconditions**: Doctor has an available shift block.
  - **Steps**: Two separate API clients send a POST request simultaneously to book the same doctor for the same time slot.
  - **Expected Result**: First request acquires the lock and succeeds (HTTP 201). Second request fails with HTTP 409 Conflict.
  - **Artifact Traceability**: FR-019, G-001, Technical Specification (4.2 Data Model)

- **TC-03: Progressive Cancellation Penalty Engine**
  - **Type**: Unit / E2E
  - **Preconditions**: Patient is registered and has 3 previous late cancellations (Tier 2 Soft Flag).
  - **Steps**: Patient attempts to cancel a 4th appointment < 2 hours before start. Patient attempts to book a new appointment.
  - **Expected Result**: The cancellation is logged. Patient tier updates to Tier 3 (Restricted). Self-service booking is blocked requiring manual override.
  - **Artifact Traceability**: FR-012, FR-013, FR-014

- **TC-04: Emergency Schedule Override**
  - **Type**: E2E
  - **Preconditions**: User has 'Manager' role. Doctor has no active shift.
  - **Steps**: Manager selects "Schedule Override" and books an appointment outside normal shifts.
  - **Expected Result**: Appointment is booked successfully. An audit log is generated detailing the override.
  - **Artifact Traceability**: FR-020

### 3.3 Clinical Records & Doctor Workspace
- **TC-05: Application-Level Column Encryption (NDPR Compliance)**
  - **Type**: Integration / Security
  - **Preconditions**: Doctor logs a clinical consultation with notes and diagnosis.
  - **Steps**: Doctor submits form. System requests KMS DEK. System encrypts data and saves to DB. Verify raw database columns.
  - **Expected Result**: `encrypted_notes` and `encrypted_diagnosis` columns contain ciphertexts. Plaintext is inaccessible without KMS decryption key.
  - **Artifact Traceability**: FR-006, NFR-006, ADR-003

- **TC-06: Cross-Branch Record Access Audit Logging**
  - **Type**: E2E / Security
  - **Preconditions**: Patient registered at Branch A visits Branch B.
  - **Steps**: Doctor at Branch B accesses patient's historical records.
  - **Expected Result**: Medical history is displayed. A security audit log tagged "Emergency Cross-Branch Access" is created.
  - **Artifact Traceability**: FR-007, NFR-007

### 3.4 Front Desk Operations
- **TC-07: Walk-In Check-In Workflow**
  - **Type**: E2E
  - **Preconditions**: Patient has an upcoming booked appointment for today.
  - **Steps**: Receptionist clicks "Check In".
  - **Expected Result**: Appointment status changes to "Checked In". Doctor's dashboard is notified.
  - **Artifact Traceability**: FR-010

## 4. Non-Functional Testing
- **Performance & Load Testing**:
  - **NFR-001 (Search Latency)**: Execute 100 concurrent search queries on the database. Ensure 95th percentile response time is < 2.0 seconds.
  - **NFR-002 (Page Load Speed)**: Throttle network to 3G speeds. Verify critical pages load in < 3.0 seconds leveraging PWA caching.
- **Availability & Resilience**:
  - **NFR-004 (Offline Caching)**: Turn off internet connection on the client browser. Verify that the receptionist and doctor dashboards can still load the current day's cached schedule (read-only) from IndexedDB.
- **Security Testing**:
  - **NFR-008 (Separation of Clinical Data)**: Login as a System Administrator. Attempt to access `GET /api/v1/clinical-records`. Ensure HTTP 403 Forbidden is returned.

## 5. Risk Assessment & Mitigation
- **Risk**: AWS KMS unavailability causing clinical record save failures.
  - **Mitigation**: Implement robust retry logic and circuit breakers. Fail gracefully, allowing doctors to draft notes locally (PWA cache) until KMS is reachable.
- **Risk**: Local internet outages interrupting clinic operations.
  - **Mitigation**: Thoroughly test the PWA Service Worker offline caching functionality across multiple browsers (Chrome, Safari, Edge) to ensure read-only schedules remain accessible.
- **Risk**: High SMS costs due to aggressive retry logic.
  - **Mitigation**: Test the Pluggable Notification Failover carefully to ensure WhatsApp-first delivery is prioritized and SMS fallbacks do not loop infinitely.
