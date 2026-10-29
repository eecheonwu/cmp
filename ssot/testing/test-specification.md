# Test Specification

## 1. Purpose
Define an end-to-end test specification for the Clinical Management Platform (CMP), tracing test scenarios and cases to functional, non-functional, integration, and business requirements from the Software Requirements Document and Technical Specification.

## 2. Scope
Covers patient registration, email verification, JWT authentication with patient/staff login separation, OTP delivery, concurrency-safe appointment booking, clinical record creation and retrieval with application-level column encryption, multi-channel notification delivery with failover, security audit logging, database migrations, health and readiness checks, and infrastructure reliability across local Docker Compose and CI environments using PostgreSQL 15, Redis 7, Celery, and LocalStack AWS service emulation.

## 3. Reference Documents
- Software Requirements Document (SRD)
- Technical Specification (Tech Spec)
- ADR-002 React PWA Frontend
- ADR-003 Application-Level Encryption
- ADR-004 Pluggable Notification Failover
- Alembic Migrations 0001 through 0011
- docker-compose.yml
- docker-compose.prod.yml
- test_jwt_audience.py
- test_login_separation.py
- test_otp_delivery.py
- test_otp_delivery_fix.py
- test_scheduling_concurrency.py
- test_concurrency.py
- test_clinical_encryption.py
- test_notification.py
- test_email_provider.py
- test_load_performance.py

## 4. Testing Levels
Component, integration, and end-to-end testing executed via pytest and pytest-asyncio against the FastAPI backend, React PWA frontend, PostgreSQL 15 database, Redis 7 cache and broker, Celery workers, and LocalStack AWS KMS/Secrets Manager/STS emulation.

## 5. Test Environments
Local development and CI via Docker Compose with postgres:15-alpine, Redis 7, LocalStack, FastAPI backend on Python 3.12-slim, React PWA frontend on Node with Nginx; production-like validation using docker-compose.prod.yml with real AWS KMS/Secrets Manager/STS.

## 6. Tools & Frameworks
pytest, pytest-asyncio, FastAPI, SQLAlchemy, asyncpg, Alembic, python-jose, passlib/bcrypt, cryptography, boto3/botocore, Celery, Redis, structlog, ruff, mypy, Docker Compose, LocalStack, React Vite, Tailwind, Nginx.

## 7. Test Scenarios

### Patient Registration and Email Verification
| ID | Title | Status | Type | Preconditions | Steps | Expected Result | Traceability |
|---|---|---|---|---|---|---|---|
| TC-001 | Successful patient registration queues verification email | Draft | Functional | Docker Compose environment is running; PostgreSQL 15, Redis 7, and LocalStack are healthy; Alembic migrations 0001 through 0011 have been applied; FastAPI backend is accepting requests. | 1. Send POST /auth/register with valid unique email and strong password.<br>2. Assert HTTP 202 Accepted is returned.<br>3. Query users table to confirm a user record exists with is_verified=false.<br>4. Query email_verification_tokens table to confirm a token exists for the user with expires_at in the future.<br>5. Verify a notification task was enqueued in Redis for send_verification_email. | A user record is created in the users table, an email verification token is generated, and a verification email is queued for delivery via Celery/Redis. | FR-001, UG-001, BG-001, 0007_email_verification_tokens.py, 0008_add_email_verification_to_users.py |
| TC-002 | Registration with duplicate email is rejected | Draft | Functional | A verified user already exists in the users table with email patient@example.com. | 1. Send POST /auth/register with email patient@example.com and a valid password.<br>2. Assert HTTP 400 or 409 Conflict is returned.<br>3. Confirm no duplicate user record was created. | The system rejects duplicate registration and does not create a second user record. | FR-001, users table unique email constraint |
| TC-003 | Valid email verification token marks user as verified | Draft | Functional | A user exists with is_verified=false and a valid, unexpired email verification token exists in email_verification_tokens. | 1. Send GET /auth/verify-email?token=<valid_token>.<br>2. Assert HTTP 200 OK is returned.<br>3. Query users table to confirm is_verified=true for the user.<br>4. Query email_verification_tokens to confirm used_at is populated. | The user's email is marked as verified, the verification token is invalidated, and the user gains access to authenticated endpoints. | FR-002, 0009_make_email_not_null_in_users.py, UG-001 |
| TC-004 | Expired or invalid email verification token is rejected | Draft | Functional | An email verification token exists with expires_at in the past, or a random invalid token string is used. | 1. Send GET /auth/verify-email?token=<expired_or_invalid_token>.<br>2. Assert HTTP 400 or 410 is returned.<br>3. Confirm the user's is_verified remains false. | The system returns an error and does not mark the email as verified. | FR-002 |

### User Authentication and Login Separation
| ID | Title | Status | Type | Preconditions | Steps | Expected Result | Traceability |
|---|---|---|---|---|---|---|---|
| TC-005 | Verified user logs in and receives JWT with audience claim | Draft | Functional | A verified user exists with a bcrypt-hashed password. | 1. Send POST /auth/login with valid email and password.<br>2. Assert HTTP 200 OK is returned with an access_token.<br>3. Decode the JWT and assert it contains the expected audience claim and expiration.<br>4. Use the token in an Authorization header for a subsequent authenticated request and assert success. | A JWT access token is issued with audience enforcement and expiration checks, and the token is required for subsequent authenticated requests. | FR-003, NFR-006, python-jose, test_jwt_audience.py |
| TC-006 | Login with invalid credentials is rejected | Draft | Functional | A user exists in the system. | 1. Send POST /auth/login with valid email and incorrect password.<br>2. Assert HTTP 401 Unauthorized is returned.<br>3. Confirm no JWT is issued. | Invalid credentials result in authentication failure with no token issued. | FR-003, NFR-005 |
| TC-007 | Patient login path prevents staff role escalation | Draft | Functional | A staff user exists with role=clinician or role=staff. | 1. Send POST /auth/login using the patient login endpoint with staff credentials.<br>2. Assert HTTP 403 Forbidden or 401 Unauthorized is returned.<br>3. Confirm no JWT with staff privileges is issued via the patient path. | The system enforces separation between patient and staff login contexts, preventing role escalation via the patient login path. | FR-004, test_login_separation.py, UG-001, UG-002 |
| TC-008 | Passwords are hashed with bcrypt and never stored plaintext | Draft | Security | A new user registers via POST /auth/register. | 1. Query the users table for the newly created user.<br>2. Assert hashed_password is not equal to the plaintext password submitted.<br>3. Assert the hash format is compatible with passlib/bcrypt. | User passwords are hashed using bcrypt via passlib and never stored in plaintext. | NFR-005, passlib/bcrypt 4.1.2 |

### OTP Delivery
| ID | Title | Status | Type | Preconditions | Steps | Expected Result | Traceability |
|---|---|---|---|---|---|---|---|
| TC-009 | OTP generation and delivery is logged | Draft | Functional | A verified user exists; notification provider is configured; Celery worker is running. | 1. Send POST /auth/otp with a valid user identifier.<br>2. Assert HTTP 202 Accepted is returned.<br>3. Confirm a time-limited OTP was generated.<br>4. Query notifications_log to confirm a delivery attempt record exists with channel=OTP.<br>5. Confirm Celery task retries with exponential backoff if provider fails. | A time-limited OTP is generated, delivered via the configured notification provider, and the OTP delivery is logged in the notifications_log. | FR-005, 0003_notifications_log.py, test_otp_delivery.py, test_otp_delivery_fix.py, BG-004 |

### Appointment Booking and Concurrency Control
| ID | Title | Status | Type | Preconditions | Steps | Expected Result | Traceability |
|---|---|---|---|---|---|---|---|
| TC-010 | Authenticated patient books an available appointment slot | Draft | Functional | A verified patient is authenticated with a valid JWT; a clinician and time slot are available. | 1. Send POST /appointments with valid clinician_id, starts_at, and ends_at using a Bearer JWT.<br>2. Assert HTTP 201 Created is returned with appointment_id.<br>3. Query appointments table to confirm the record exists with status=scheduled.<br>4. Confirm a booking confirmation notification task was enqueued. | An appointment record is created, the slot is marked as reserved, and a booking confirmation is queued as a notification. | FR-006, booking.py, booking_service.py, booking_repository.py, BG-002 |
| TC-011 | Concurrent duplicate booking results in single success and conflict error | Draft | Functional | Two authenticated requests are prepared simultaneously for the same patient, clinician, and overlapping time range. | 1. Send two concurrent POST /appointments requests with identical scheduling parameters.<br>2. Assert exactly one request receives HTTP 201 Created.<br>3. Assert the second request receives HTTP 409 Conflict.<br>4. Query appointments table to confirm only one appointment record exists for the slot. | Only one booking succeeds; the second request receives a conflict error. No partial or duplicate bookings persist. | FR-007, test_scheduling_concurrency.py, test_concurrency.py, no_overlap exclusion constraint |
| TC-012 | Unauthenticated appointment booking is rejected | Draft | Security | No JWT is provided. | 1. Send POST /appointments without an Authorization header.<br>2. Assert HTTP 401 Unauthorized is returned. | Authenticated endpoints require a valid JWT; unauthenticated requests are rejected. | FR-006, NFR-006 |

### Clinical Record Management and Encryption
| ID | Title | Status | Type | Preconditions | Steps | Expected Result | Traceability |
|---|---|---|---|---|---|---|---|
| TC-013 | Clinical record creation encrypts sensitive fields at application layer | Draft | Security | An authorized clinician is authenticated; LocalStack KMS or AWS KMS is accessible; encryption key is available. | 1. Send POST /clinical-records with patient_id, encounter_date, diagnosis, treatment_plan, and notes using a Bearer JWT.<br>2. Assert HTTP 201 Created is returned with record_id.<br>3. Query clinical_records table and assert diagnosis_encrypted, treatment_plan_encrypted, and notes_encrypted are stored as BYTEA ciphertext, not plaintext.<br>4. Confirm encryption_key_id references the KMS key.<br>5. Confirm a security_audit_logs entry exists for CREATE_CLINICAL_RECORD. | Sensitive fields are encrypted at the application level before storage, and only authorized roles can decrypt/view them. | FR-008, NFR-004, 0005_clinical_records.py, ADR-003, test_clinical_encryption.py, BG-003 |
| TC-014 | Authorized role retrieves and decrypts clinical record | Draft | Functional | A clinical record exists with encrypted sensitive fields; the requesting user has an authorized role. | 1. Send GET /clinical-records/{id} with a valid Bearer JWT for an authorized role.<br>2. Assert HTTP 200 OK is returned.<br>3. Assert the response contains decrypted diagnosis, treatment_plan, and notes.<br>4. Confirm a security_audit_logs entry exists for READ_CLINICAL_RECORD. | Authorized roles can decrypt and view sensitive clinical record fields; access is audited. | FR-008, security_audit_logs |
| TC-015 | Unauthorized role cannot decrypt clinical record | Draft | Security | A clinical record exists; the requesting user has an unauthorized role (e.g., patient attempting to view another patient's record without authorization). | 1. Send GET /clinical-records/{id} with a Bearer JWT for an unauthorized role.<br>2. Assert HTTP 403 Forbidden is returned.<br>3. Confirm no plaintext sensitive data is returned. | Only authorized roles can decrypt/view sensitive clinical record fields. | FR-008, NFR-004 |

### Notification Delivery and Failover
| ID | Title | Status | Type | Preconditions | Steps | Expected Result | Traceability |
|---|---|---|---|---|---|---|---|
| TC-016 | Primary provider failure triggers failover to secondary provider | Draft | Functional | Primary and secondary notification providers are configured per ADR-004; primary provider is simulated as unavailable. | 1. Trigger a notification task (e.g., booking confirmation or verification email).<br>2. Confirm the primary provider attempt fails.<br>3. Confirm the system fails over to the secondary provider.<br>4. Query notifications_log to confirm both delivery attempts are logged with status and provider.<br>5. Confirm final delivery status reflects success or failure after failover. | The system fails over to a secondary provider, and the delivery attempt is logged in notifications_log. | FR-009, ADR-004, test_notification.py, test_email_provider.py, 0003_notifications_log.py |
| TC-017 | Notification task retries with exponential backoff when Redis is unavailable | Draft | Reliability | Redis broker is temporarily stopped; Celery workers are running. | 1. Enqueue a notification task.<br>2. Stop Redis.<br>3. Confirm the task is not lost and is retried with exponential backoff once Redis recovers.<br>4. Restart Redis and confirm task processing resumes. | If Redis is unavailable, notification tasks are retried with exponential backoff once Redis recovers. | NFR-003, Celery 5.3.6, Redis 7 |

### Security Audit Logging
| ID | Title | Status | Type | Preconditions | Steps | Expected Result | Traceability |
|---|---|---|---|---|---|---|---|
| TC-018 | Security-relevant events produce immutable audit log entries | Draft | Security | security_audit_logs table exists; application is running. | 1. Perform a login, clinical record access, and appointment booking.<br>2. Query security_audit_logs for entries corresponding to these events.<br>3. Assert each entry contains actor_id, action, timestamp, resource_type, and resource_id.<br>4. Attempt to delete or modify an audit log entry and assert the operation is prevented or not supported. | An immutable audit log entry is written for each security-relevant event containing actor, action, timestamp, and affected resource. | FR-010, 0006_security_audit_logs.py, BG-005 |

### Database Migrations and Schema Initialization
| ID | Title | Status | Type | Preconditions | Steps | Expected Result | Traceability |
|---|---|---|---|---|---|---|---|
| TC-019 | Alembic migrations advance schema to latest version without data loss | Draft | Integration | A clean database or an existing cmp_db schema; Alembic is configured. | 1. Run alembic upgrade head.<br>2. Confirm all migrations 0001_initial_empty.py through 0011_add_timestamps_to_notif_log.py are applied.<br>3. Query alembic_version table to confirm the latest version.<br>4. Confirm existing data is preserved when migrating an existing schema. | The database schema is advanced to the latest version without data loss. | FR-011, Alembic 2.0.25 / 1.13.1 |
| TC-020 | Fresh database initialization creates all required tables | Draft | Integration | An empty PostgreSQL 15 database named cmp_db. | 1. Run alembic upgrade head on the empty database.<br>2. Query information_schema.tables to confirm users, email_verification_tokens, appointments, clinical_records, notifications_log, and security_audit_logs exist.<br>3. Confirm column constraints match the data model (e.g., email UNIQUE, is_verified DEFAULT FALSE). | All required tables and constraints are created in cmp_db. | FR-011, data_model_sql |

### Health and Readiness Checks
| ID | Title | Status | Type | Preconditions | Steps | Expected Result | Traceability |
|---|---|---|---|---|---|---|---|
| TC-021 | Backend health check verifies PostgreSQL and Redis readiness | Draft | Reliability | Docker Compose is running; backend service is starting. | 1. Send GET /health.<br>2. Assert HTTP 200 OK is returned only after pg_isready and redis-cli ping succeed.<br>3. Stop PostgreSQL and confirm /health reports unhealthy or backend does not accept traffic.<br>4. Restart PostgreSQL and confirm /health recovers. | PostgreSQL and Redis are verified healthy before the backend accepts traffic. | FR-012, NFR-002, docker-compose.yml healthcheck configuration |
| TC-022 | Backend rejects traffic when database is unhealthy | Draft | Reliability | PostgreSQL is stopped or unhealthy. | 1. Attempt an authenticated API request.<br>2. Assert the request fails with a connection error or the service is not ready.<br>3. Confirm no partial transactions are persisted. | Docker Compose condition: service_healthy and health checks prevent backend from accepting traffic until the database recovers. | NFR-002 |

### Staff and Administrator Operations
| ID | Title | Status | Type | Preconditions | Steps | Expected Result | Traceability |
|---|---|---|---|---|---|---|---|
| TC-023 | Clinician or staff can view patient appointments and clinical records | Draft | Functional | A staff user with role=clinician is authenticated; appointments and clinical records exist. | 1. Send GET /appointments with a staff Bearer JWT.<br>2. Assert HTTP 200 OK is returned with appointment list.<br>3. Send GET /clinical-records/{id} with a staff Bearer JWT.<br>4. Assert HTTP 200 OK is returned with decrypted record if authorized. | Clinical staff can access patient appointments and clinical records and manage scheduling. | UG-002, FR-006, FR-008 |
| TC-024 | System administrator monitors audit logs and configures KMS integration | Draft | Functional | An administrator user is authenticated; LocalStack or AWS KMS is configured. | 1. Send GET /security-audit-logs (or equivalent admin endpoint) and assert audit entries are returned.<br>2. Verify KMS key management operations succeed via LocalStack in dev or AWS KMS in prod.<br>3. Confirm no plaintext keys appear in application logs. | System administrators can monitor audit logs and manage notification providers and encryption/KMS integration. | UG-003, FR-010, NFR-004 |

### End-to-End Patient Journey
| ID | Title | Status | Type | Preconditions | Steps | Expected Result | Traceability |
|---|---|---|---|---|---|---|---|
| TC-025 | Complete patient flow from registration to appointment confirmation | Draft | End-to-End | Full Docker Compose stack is running; frontend can reach backend API. | 1. Register a new patient via POST /auth/register.<br>2. Verify email via GET /auth/verify-email.<br>3. Log in via POST /auth/login and receive JWT.<br>4. Book an appointment via POST /appointments.<br>5. Confirm booking confirmation notification is logged in notifications_log.<br>6. Retrieve the appointment via GET /appointments/{id}.<br>7. Confirm security audit log entries exist for registration, login, and booking. | The patient can self-register, verify email, authenticate, book an appointment, and receive notification confirmation with full audit trail. | FR-001, FR-002, FR-003, FR-006, FR-009, FR-010, UG-001, BG-001, BG-002, BG-004, BG-005 |

## 8. Non-Functional Tests
| ID | Title | Description | Status |
|---|---|---|---|
| NFT-001 | API latency p95 under 200 ms | Authenticated API endpoints shall respond within 200 ms (p95) under normal load, as validated by test_load_performance.py. | Draft |
| NFT-002 | Database availability via health checks | The system shall depend on a healthy PostgreSQL instance before accepting requests, enforced via Docker Compose condition: service_healthy. | Draft |
| NFT-003 | Redis broker reliability with retry backoff | Celery workers shall connect to Redis for task distribution; if Redis is unavailable, notification tasks shall be retried with exponential backoff. | Draft |
| NFT-004 | Encryption at rest for clinical records | Sensitive clinical record columns shall be encrypted using application-level encryption prior to persistence (cryptography library, ADR-003), independent of PostgreSQL native encryption. | Draft |
| NFT-005 | Password storage with bcrypt | User passwords shall be hashed using bcrypt via passlib, never stored in plaintext. | Draft |
| NFT-006 | JWT validation with audience enforcement | JWTs shall be validated using python-jose[cryptography] with audience enforcement and expiration checks. | Draft |
| NFT-007 | Structured JSON logging | All application logs shall be emitted in structured JSON format via structlog and python-json-logger for aggregation and alerting. | Draft |
| NFT-008 | Code quality linting and type checking | Python code shall pass ruff linting and mypy static type checking; frontend code shall pass ESLint. | Draft |
| NFT-009 | Containerization and portability | The backend shall run in a Python 3.12-slim container; frontend shall run in a Node container with Nginx; orchestration via Docker Compose. | Draft |
| NFT-010 | Automated test coverage | The system shall be covered by automated tests including auth, booking flow, clinical encryption, email registration, notification, OTP delivery, concurrency, and load performance tests located in /tests/. | Draft |

## 9. Risk Assessment
| Risk | Mitigation |
|---|---|
| Primary notification provider failure | System fails over to secondary notification provider per ADR-004 pluggable failover. Delivery attempt and failover are logged in notifications_log. Celery task retries with exponential backoff if both providers fail. |
| Redis broker unavailable | Celery workers cannot distribute tasks. Notification tasks are retried with exponential backoff once Redis recovers. API remains operational for synchronous requests but async notifications are delayed. |
| PostgreSQL unhealthy or unavailable | Docker Compose condition: service_healthy and health checks (pg_isready) prevent backend from accepting traffic until database recovers. In-flight transactions are rolled back; clients receive connection errors and should retry. |
| Concurrent duplicate appointment booking | PostgreSQL exclusion constraint ensures only one booking succeeds for the same slot and time range. Second request receives HTTP 409 conflict error. No partial or duplicate bookings persist. |
| KMS key inaccessible | Application-level encryption/decryption for clinical records fails. System returns error rather than storing plaintext sensitive data. In LocalStack dev, mock KMS is used; in production, AWS KMS IAM policies and key rotation must be monitored. |