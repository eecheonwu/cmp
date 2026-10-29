# Software Requirements Document

## 1. Executive Summary
The CMP (Clinical Management Platform) is a brownfield healthcare appointment and clinical records management system. It provides patient authentication, appointment booking/scheduling, clinical record management with application-level column encryption, multi-channel notifications (email/OTP), and audit logging. The system is designed as a decoupled backend/frontend architecture with asynchronous task processing via Celery/Redis and local AWS service emulation via LocalStack for development and testing.\n\nTech Stack Summary:\n- Backend API: FastAPI (Python) 0.109.0\n- ASGI Server: Uvicorn 0.27.0\n- Database: PostgreSQL 15\n- ORM / Migrations: SQLAlchemy / Alembic 2.0.25 / 1.13.1\n- Async DB Driver: asyncpg 0.29.0\n- Cache / Broker: Redis 7\n- Task Queue: Celery 5.3.6\n- Frontend: React (Vite + Tailwind)\\n- Authentication: python-jose, passlib/bcrypt 3.3.0 / 4.1.2\n- Encryption: cryptography 41.0.7\n- AWS Integration: boto3 / botocore 1.34.25\n- HTTP Client: httpx / aiohttp 0.26.0 / 3.9.3\n- Logging: structlog 23.3.0\n- Testing: pytest, pytest-asyncio 7.4.4 / 0.23.3\n- Linting / Typing: ruff, mypy 0.1.14 / 1.8.0\n\nDomain Overview: The system operates in the clinical/healthcare domain. Core domain concepts include Users / Patients, Appointments / Booking, Clinical Records, Notifications, and Security & Audit.

## 2. Project Goals
### 2.1 Business Goals
- **BG-001**: Enable patients to self-register, verify email, and authenticate into a clinical portal.
- **BG-002**: Allow patients to book, view, and manage appointments with concurrency-safe scheduling.
- **BG-003**: Persist clinical records with application-level column-level encryption for sensitive health data.
- **BG-004**: Provide reliable, multi-channel notifications (email, OTP) with failover capability.
- **BG-005**: Maintain immutable security audit trails for access and data changes.
- **BG-006**: Support local development and CI/CD via Docker Compose with PostgreSQL, Redis, and LocalStack (AWS KMS/Secrets/STS mocking).

### 2.2 User Goals
- **UG-001**: Patient: Register account, verify email, log in securely, book appointments, view clinical records, receive OTP/email notifications.
- **UG-002**: Clinician / Staff: (Inferred) Access patient appointments and clinical records, manage scheduling.
- **UG-003**: System Administrator: Monitor audit logs, manage notification providers, configure encryption/KMS integration.

### 2.3 Non-Goals
- Payment processing or insurance billing (no evidence in migrations or dependencies).
- Multi-tenancy or organization-level isolation (single `cmp_db` database implied).
- Real-time video telehealth (no WebRTC or video dependencies detected).
- Mobile native applications (frontend is a React PWA per ADR-002).

## 3. Stakeholders & Users
| Role | Description | Interaction |
|---|---|---|
| Patient | End user | Registration, authentication, appointment booking, clinical record access, notification receipt |
| Clinical Staff | End user | Appointment management, clinical record viewing, scheduling |
| System Administrator | Operator | Database migrations, Redis/Celery monitoring, LocalStack/KMS configuration, audit log review |
| Developer / QA | Engineering | Test suite execution (`pytest`), Docker Compose environments, Alembic migrations, CI/CD pipelines |
| Product Owner | Business | Feature prioritization, semantic versioning compliance, SLA adherence |

## 4. Requirements
### 4.1 Functional Requirements
| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-001 | User Registration | High | Given: A new user submits a valid email and password via the registration endpoint. When: The registration request is processed. Then: A user record is created in the `users` table, an email verification token is generated (`0007_email_verification_tokens.py`, `0008_add_email_verification_to_users.py`), and a verification email is queued for delivery. |
| FR-002 | Email Verification | High | Given: A registered user clicks an email verification link containing a valid token. When: The verification endpoint is invoked with a non-expired token. Then: The user's email is marked as verified (`0009_make_email_not_null_in_users.py`), the verification token is invalidated, and the user gains access to authenticated endpoints. |
| FR-003 | User Authentication (JWT) | High | Given: A verified user submits valid email and password credentials. When: The login endpoint is called. Then: A JWT access token is issued (`python-jose`, `test_jwt_audience.py`), the token includes the expected audience claim, and the token is required for subsequent authenticated requests. |
| FR-004 | Login Separation | High | Given: A user attempts to authenticate. When: The authentication flow executes. Then: The system enforces separation between patient and staff login contexts (`test_login_separation.py`), preventing role escalation via the patient login path. |
| FR-005 | OTP Delivery | High | Given: A user requests an OTP (e.g., for password reset or step-up authentication). When: The OTP generation endpoint is invoked. Then: A time-limited OTP is generated, delivered via the configured notification provider (`test_otp_delivery.py`, `test_otp_delivery_fix.py`), and the OTP delivery is logged in the notifications log (`0003_notifications_log.py`). |
| FR-006 | Appointment Booking | High | Given: An authenticated patient requests an appointment slot. When: The booking endpoint is called with valid scheduling parameters. Then: An appointment record is created (`booking.py`, `booking_service.py`, `booking_repository.py`), the slot is marked as reserved, and a booking confirmation is queued as a notification. |
| FR-007 | Scheduling Concurrency Control | High | Given: Two concurrent requests attempt to book the same appointment slot. When: Both requests are processed simultaneously. Then: Only one booking succeeds; the second request receives a conflict error (`test_scheduling_concurrency.py`, `test_concurrency.py`). |
| FR-008 | Clinical Record Management | High | Given: A clinical record is created or updated for a patient. When: The record is persisted to the database. Then: Sensitive fields are encrypted at the application level before storage (`0005_clinical_records.py`, ADR-003, `test_clinical_encryption.py`), and only authorized roles can decrypt/view them. |
| FR-009 | Notification Delivery & Failover | High | Given: A notification (email, OTP, booking confirmation) must be sent. When: The primary notification provider fails. Then: The system fails over to a secondary provider (`ADR-004 — pluggable notification failover`), and the delivery attempt is logged (`0003_notifications_log.py`, `test_notification.py`, `test_email_provider.py`). |
| FR-010 | Security Audit Logging | High | Given: A security-relevant event occurs (login, record access, permission change). When: The event is processed by the application. Then: An immutable audit log entry is written (`0006_security_audit_logs.py`) containing actor, action, timestamp, and affected resource. |
| FR-011 | Database Migrations | High | Given: The application is deployed to a new or existing environment. When: Alembic migrations are run. Then: The database schema is advanced to the latest version (`0001_initial_empty.py` through `0011_add_timestamps_to_notif_log.py`) without data loss. |
| FR-012 | Health & Readiness Checks | High | Given: The backend service starts. When: Docker Compose health checks or Kubernetes probes are executed. Then: PostgreSQL (`pg_isready`) and Redis (`redis-cli ping`) are verified healthy before the backend accepts traffic (`docker-compose.yml` healthcheck configuration). |

### 4.2 Non-Functional Requirements
| ID | Requirement | Target |
|---|---|---|
| NFR-001 | Performance (API Latency) | Authenticated API endpoints shall respond within 200 ms (p95) under normal load, as validated by `test_load_performance.py`. |
| NFR-002 | Reliability (Database Availability) | The system shall depend on a healthy PostgreSQL instance before accepting requests, enforced via Docker Compose `condition: service_healthy`. |
| NFR-003 | Reliability (Message Broker) | Celery workers shall connect to Redis for task distribution; if Redis is unavailable, notification tasks shall be retried with exponential backoff. |
| NFR-004 | Security (Encryption at Rest) | Sensitive clinical record columns shall be encrypted using application-level encryption prior to persistence (`cryptography` library, ADR-003), independent of PostgreSQL native encryption. |
| NFR-005 | Security (Password Storage) | User passwords shall be hashed using bcrypt via `passlib`, never stored in plaintext. |
| NFR-006 | Security (JWT Validation) | JWTs shall be validated using `python-jose[cryptography]` with audience enforcement (`test_jwt_audience.py`) and expiration checks. |
| NFR-007 | Observability (Structured Logging) | All application logs shall be emitted in structured JSON format via `structlog` and `python-json-logger` for aggregation and alerting. |
| NFR-008 | Maintainability (Code Quality) | Python code shall pass `ruff` linting and `mypy` static type checking; frontend code shall pass ESLint (`eslint.config.js`, `.eslintrc.json`). |
| NFR-009 | Portability (Containerization) | The backend shall run in a Python 3.12-slim container; frontend shall run in a Node container with Nginx; orchestration via Docker Compose (`docker-compose.yml`, `docker-compose.prod.yml`). |
| NFR-010 | Testability | The system shall be covered by automated tests including auth, booking flow, clinical encryption, email registration, notification, OTP delivery, concurrency, and load performance tests located in `/tests/`. |

### 4.3 AI Requirements
| ID | Requirement | Detail |
|---|---|---|
| AI-001 | Not applicable | No AI/ML frameworks, models, or inference endpoints were detected in the dependency manifests or codebase profile. |

## 5. System Interfaces & Integrations
| ID | External System | Type | Direction | Requirement |
|---|---|---|---|---|
| INT-001 | PostgreSQL | Database | Outbound | `postgresql+asyncpg: |

## 6. Data Requirements
| ID | Requirement | Detail |
|---|---|---|

## 7. Assumptions & Constraints
### 7.1 Assumptions
- The frontend is a React PWA (per ADR-002) consuming the FastAPI backend via REST/JSON.
- LocalStack is used exclusively for local development and CI; production will use real AWS KMS/Secrets Manager/STS.
- The system is single-tenant with one PostgreSQL database (`cmp_db`).
- Alembic migrations are run automatically or manually as part of deployment; no zero-downtime migration strategy is currently evidenced.

### 7.2 Constraints
- **Technology**: Python 3.12 is required (Dockerfile `FROM python:3.12-slim`).
- **Database**: PostgreSQL 15 is the minimum supported database version (`postgres:15-alpine`).
- **Cache**: Redis 7 is required for Celery and rate limiting.
- **Security**: Application-level encryption keys must be managed via KMS (LocalStack in dev, AWS KMS in prod).
- **Architecture**: No authentication middleware was explicitly visible in the provided file sample; authentication is assumed to be implemented via FastAPI dependencies/JWT middleware in `main.py` or route modules.

## 8. Open Questions
| ID | Question | Impact |
|---|---|---|