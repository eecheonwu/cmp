# Clinic Modernization Platform (CMP) — Comprehensive Security Plan

**Document Owner:** Principal Security Architect  
**Target Audience:** Engineering Teams, Clinic Stakeholders, Compliance Officers  
**Project:** Clinic Modernization Platform (Phase 1 MVP)  

---

## 1. Executive Summary

The Clinic Modernization Platform (CMP) handles highly sensitive patient medical records, scheduling data, and operational metrics across multiple clinic branches. This Security Plan outlines the architectural safeguards, cryptographic strategies, and secure coding practices required to protect the platform against external attacks and insider threats. The strategy is heavily driven by the **Nigeria Data Protection Regulation (NDPR)** and the architectural decisions outlined in the system's Technical Specification (ADR-001 through ADR-004).

---

## 2. Regulatory & Compliance Constraints

The system must strictly adhere to the **Nigeria Data Protection Regulation (NDPR)**. While HIPAA is not the primary regulatory framework for this jurisdiction, the platform adopts HIPAA-equivalent technical safeguards as a baseline for medical data protection.

### 2.1 Data Classification
All data within the CMP is classified into three tiers, dictating its handling and storage:
* **Confidential (PII):** Patient profile details, phone numbers, email addresses. Protected via standard database access controls and disk-level encryption.
* **Restricted (PHI/Medical):** Consultation logs, diagnostic images, prescriptions, diagnoses. Protected via **Application-Level Column Encryption** (AES-256-GCM).
* **Internal:** Operational performance reports, branch utilization metrics. Protected via Role-Based Access Control (RBAC).

### 2.2 Separation of Duties (NFR-008)
System administrators, database administrators, and cloud infrastructure engineers **must not** have access to plaintext clinical records. Cryptographic access is strictly scoped to authenticated clinical roles (Doctors) during active sessions.

---

## 3. Threat Modeling & Vulnerability Management

Based on the system architecture (FastAPI, React PWA, PostgreSQL, Redis), the following primary threat vectors have been identified and mitigated:

| Threat Vector | Description | Architectural Mitigation |
| :--- | :--- | :--- |
| **Insider Threat (DB Compromise)** | A rogue DB admin or leaked database snapshot exposes patient medical histories. | **App-Level Encryption (ADR-003):** Clinical columns are encrypted via AES-256-GCM before hitting the DB. Keys are managed by AWS KMS; DB admins lack IAM decrypt permissions. |
| **OTP Brute-Forcing / Toll Fraud** | Attackers spam the OTP endpoint to brute-force verification codes or incur SMS/WhatsApp gateway costs. | **Rate Limiting & Expiry:** Max 3 requests per 15 mins per IP/Phone. OTPs expire in 10 minutes. Max 5 validation attempts per code before hard lock. |
| **Concurrent Booking Race Conditions** | Malicious or accidental concurrent requests double-book a doctor, causing operational chaos. | **Pessimistic Locking (ADR-001):** Database-level `SELECT ... FOR UPDATE` locks the doctor's availability row during the transaction, ensuring atomic bookings. |
| **Offline Cache Data Leakage** | A shared clinic workstation is compromised, exposing the local IndexedDB schedule cache. | **Volatile Storage Management:** The PWA clears sensitive IndexedDB data upon explicit logout or JWT expiration. Cache is strictly limited to the *current day's* schedule. |
| **API Abuse & DDoS** | Volumetric attacks against the FastAPI backend. | **Edge Protection:** AWS CloudFront and API Gateway provide baseline DDoS protection, WAF rules, and IP rate-limiting before traffic reaches the application container. |

---

## 4. Authentication & Authorization Strategy

### 4.1 Authentication (AuthN)
* **Primary Authentication:** Users authenticate using their registered Phone Number/Email and a strongly hashed password (using `bcrypt` or `Argon2id`).
* **Multi-Channel Verification:** New device logins and registrations require OTP verification routed via a hierarchical failover engine (WhatsApp primary $\rightarrow$ Termii SMS $\rightarrow$ Infobip SMS).
* **Session Management:** The backend issues short-lived **JSON Web Tokens (JWT)** signed with an asymmetric key (RS256). 
  * **Access Tokens:** 15-minute lifespan.
  * **Refresh Tokens:** 7-day lifespan, stored in `HttpOnly`, `Secure`, `SameSite=Strict` cookies to prevent XSS exfiltration.

### 4.2 Authorization (AuthZ)
Authorization is enforced via **Role-Based Access Control (RBAC)** using FastAPI Security Scopes.
* **Roles Defined:** `PATIENT`, `RECEPTIONIST`, `DOCTOR`, `MANAGER`, `ADMIN`, `EXECUTIVE`.
* **Enforcement:** Every API endpoint explicitly declares required scopes. 
  * *Example:* `POST /api/v1/clinical-records` requires the `doctor` scope.
  * *Example:* `POST /api/v1/appointments` requires `patient`, `receptionist`, or `manager` scopes.
* **Hierarchical Overrides:** Authorized staff (Managers/Admins) can bypass patient penalty restrictions (Tier 3) via explicit override flags, which trigger mandatory audit logging.

---

## 5. Data Protection Mechanisms

### 5.1 Encryption in Transit
* **Protocol:** All client-to-server and server-to-server communication is strictly enforced over **TLS 1.3**.
* **Edge Termination:** TLS is terminated at AWS CloudFront and AWS API Gateway.
* **Internal Routing:** Traffic between the API Gateway, FastAPI containers, and PostgreSQL/Redis utilizes internal AWS VPC encryption.

### 5.2 Encryption at Rest
* **Infrastructure Level:** The PostgreSQL database (AWS RDS) utilizes AWS-managed Transparent Data Encryption (TDE) to encrypt the underlying EBS volumes, protecting against physical drive theft.
* **Application Level (Envelope Encryption):** To satisfy NFR-008, Restricted Medical Data (`encrypted_notes`, `encrypted_diagnosis`, `encrypted_prescriptions`) is encrypted inside the FastAPI application memory.
  1. FastAPI requests a Data Encryption Key (DEK) from AWS KMS.
  2. Data is encrypted using **AES-256-GCM** (probabilistic encryption with a unique IV per write).
  3. The ciphertext, IV, Auth Tag, and `kms_key_version` are stored in PostgreSQL.
  4. The plaintext DEK is immediately wiped from application memory.

---

## 6. Secure Coding Guidelines

To maintain the security posture during development, the engineering team must adhere to the following framework-specific guidelines:

### 6.1 FastAPI (Backend) Guidelines
* **Input Validation:** Strictly use **Pydantic V2** models for all incoming request payloads. Never access raw `request.body()` without validation.
* **SQL Injection Prevention:** All database interactions must use **SQLAlchemy/SQLModel** ORM paradigms. Raw SQL strings are strictly prohibited unless parameterized via SQLAlchemy's `text()` construct with bound parameters.
* **CORS Configuration:** Configure the FastAPI CORS middleware to explicitly allow only the production CloudFront domain. `allow_origins=["*"]` is strictly forbidden in production.
* **Error Handling:** Never leak stack traces or database schema details in HTTP 500 responses. Use generic error messages for unhandled exceptions.

### 6.2 React + Vite PWA (Frontend) Guidelines
* **XSS Prevention:** React natively escapes variables, but developers must strictly avoid the use of `dangerouslySetInnerHTML`. Any rich-text rendering for clinical notes must pass through a strict HTML sanitizer (e.g., `DOMPurify`).
* **Secure Offline Storage:** Data stored in `Dexie.js` (IndexedDB) for offline resiliency (NFR-004) must be treated as volatile. Implement a global state listener that purges the IndexedDB database immediately upon JWT expiration or user logout.
* **Dependency Management:** Regularly audit npm packages using `npm audit`. Pin dependency versions to prevent supply chain attacks.

---

## 7. Audit & Monitoring

### 7.1 Immutable Security Audit Log (NFR-007)
A dedicated `security_audit_logs` table tracks all sensitive actions.
* **Trigger Events:** Reading clinical records, writing clinical records, emergency cross-branch access, and administrative booking overrides.
* **Data Captured:** `user_id`, `action_type`, `patient_id`, `ip_address`, `timestamp`, and `action_details`.
* **Atomicity:** Audit logs are written in the **same database transaction** as the action itself. If the audit log insert fails, the entire transaction rolls back.

### 7.2 Observability
* **Structured Logging:** All FastAPI logs must be output in JSON format, including a `correlation_id` to trace requests across the API, Redis queue, and Celery workers.
* **Alerting:** CloudWatch/Datadog alerts must be configured for:
  * Repeated 401/403 errors from a single IP (potential brute force).
  * AWS KMS `AccessDeniedException` errors (potential IAM misconfiguration or insider threat attempt).
  * Database lock timeouts exceeding 3.0 seconds.

---

## 8. Incident Response & Recovery

* **KMS Key Compromise:** In the event of a suspected key compromise, AWS KMS automatic key rotation will be accelerated, and the compromised CMK will be disabled. The application will utilize the `kms_key_version` column to seamlessly transition to the new key for future writes.
* **Gateway Failures:** If the primary WhatsApp API or Termii SMS gateway is compromised or goes offline, the Pluggable Notification Service (ADR-004) automatically routes traffic to the Infobip fallback, ensuring zero disruption to patient communications.