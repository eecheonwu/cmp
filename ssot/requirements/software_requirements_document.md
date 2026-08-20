# Clinic Modernization Platform (CMP) — Software Requirements Document

**Author**: Antigravity (AI Architect)
**Reviewers**: Clinic Owner, Senior Stakeholders
**Status**: Approved
**Version**: 1.3
**Date**: 2026-06-04
**Project Type**: Hybrid

---

## 1. Executive Summary

The Clinic Modernization Platform (CMP) is a scalable, cloud-hosted clinic management system designed to transition a chain of three private healthcare clinics (scaling to 10–15 branches) from manual paper-and-chat workflows to digital operations. The platform provides patients with self-service mobile booking, Receptionists with desktop check-in and scheduling tools, and Doctors with tablet-optimized clinical records. The system utilizes automated WhatsApp and SMS reminders to dramatically reduce patient no-show rates, while ensuring strict data privacy in compliance with Nigeria's Data Protection Regulation (NDPR). It is architected to allow the seamless introduction of an AI scheduling chatbot and online payments in subsequent phases.

---

## 2. Project Goals

### 2.1 Business Goals
- **BG-001**: Reduce receptionist time spent on manual appointment scheduling by 70% within 6 months of deployment.
- **BG-002**: Reduce patient appointment no-show rates by 25–30% within 6 months using automated notifications.
- **BG-003**: Digitise 100% of new patient registration and clinical consultation records at all active branches.
- **BG-004**: Eliminate schedule conflicts and double-bookings for permanent and rotating doctors across all branches.
- **BG-005**: Provide real-time, consolidated operational performance dashboards to management, eliminating manual report compilation.

### 2.2 User Goals
- **UG-001 (Patients)**: Book, view, reschedule, or cancel clinic appointments via a responsive mobile portal and receive timely text reminders.
- **UG-002 (Receptionists)**: Register new patients, manage appointment check-ins, view doctor timetables, and handle phone/walk-in bookings quickly.
- **UG-003 (Doctors)**: Access patient clinical history, record consultation notes, input diagnoses/treatments, and view daily schedules from a tablet or desktop.
- **UG-004 (Branch Managers)**: Monitor patient attendance, doctor utilization, and operational reports for their assigned clinic location.
- **UG-005 (Senior Management)**: Review consolidated aggregated metrics across all clinic branches in real-time.

### 2.3 Non-Goals
- **NG-001**: The system SHALL NOT provide clinical medical diagnoses or treatment suggestions via AI.
- **NG-002**: Digitisation or back-entry of historical paper patient files created prior to system deployment is out of scope for the initial release.
- **NG-003**: Native Android or iOS mobile applications are out of scope (responsive web client is mandatory).
- **NG-004**: Integrated real-time video/audio telemedicine consultations are excluded from Phase 1.
- **NG-005**: Financial billing and online payment processing gates are excluded from Phase 1 (supported in DB design only).

---

## 3. Stakeholders & Users

| Role | Description | Interaction Type |
|---|---|---|
| **Patient** | Registers, books appointments, views active prescriptions and released test results on mobile. | Direct / Mobile Responsive Portal |
| **Receptionist** | Handles front-desk check-in, edits patient profile data, records offline/phone bookings. | Direct / Desktop UI |
| **Doctor** | Views personal timetable, inputs consultation logs, views unified clinical histories. | Direct / Tablet & Desktop UI |
| **Branch Manager** | Monitors single-branch operational dashboard and staff attendance metrics. | Direct / Laptop Web UI |
| **Senior Manager** | Evaluates aggregated cross-clinic dashboards, utilization rates, and trends. | Direct / Laptop Web UI |
| **System Administrator**| Configures clinic settings, manages branches, adjusts user roles and permissions. | Direct / Admin Console |
| **WhatsApp Gateway** | Outbound messaging channel for reminders and status updates. | REST API / Webhook |
| **SMS Gateway** | Failover outbound messaging channel for critical communications. | REST API |

---

## 4. Assumptions & Constraints

### 4.1 Assumptions

| # | Assumption | Impact if Wrong |
|---|---|---|
| **A-001** | Patients have active mobile data/network access to load a lightweight mobile portal. | Patient self-service booking drops; reception workload remains high. |
| **A-002** | WhatsApp Business Cloud API provides reliable delivery of templated notifications in Nigeria. | Failures trigger SMS fallback, increasing platform SMS operating costs. |
| **A-003** | Local power outages in branches are mitigated by local clinic generators/UPS systems. | Branch workstations lose access to system; local cache access is required. |
| **A-004** | Medical staff are willing to enter digital notes instead of writing on paper. | Data completeness drops; business metrics cannot be generated. |

### 4.2 Constraints

| Type | Constraint |
|---|---|
| **Timeline** | MVP (Phase 1) MUST be fully deployed and operational within 4 months from project kick-off. |
| **Budget** | Initial deployment costs must utilize cost-effective cloud services to align with business budget. |
| **Platform** | Hosted in public cloud (AWS preferred). Responsive web platform only (no native app stores). |
| **Regulatory** | MUST comply with Nigerian Data Protection Act (NDPR). Sensitive health data must be encrypted. |
| **Technology** | On-premise server installations are prohibited. System must operate purely on cloud instances. |

---

## 5. Functional Requirements

### 5.1 Patient Account & Authentication
- **FR-001 (Must)**: Patient Registration. The system SHALL allow patients to register an account.
  * *Acceptance Criteria*: Given a new patient visits the registration page, When they submit their full name, active Nigerian phone number, email, and password, Then the system creates their profile, sends a verification code, and requests login.
- **FR-002 (Must)**: Role-Based Access Control (RBAC). The system SHALL enforce strict role assignments (Patient, Receptionist, Doctor, Manager, Administrator, Executive).
  * *Acceptance Criteria*: Given a logged-in user with "Patient" role, When they attempt to access the Doctor clinical notes URL, Then the system denies access and logs a security exception.

### 5.2 Patient Scheduling & Appointment Engine
- **FR-003 (Must)**: Appointment Booking. The system SHALL allow patients and receptionists to book appointments.
  * *Acceptance Criteria*: Given a patient selecting a branch, doctor, and date, When they choose an available time slot and submit, Then the system reserves the slot, marks it as "Booked / Unpaid", and sends a confirmation trigger.
- **FR-004 (Must)**: Cross-Branch Schedule Conflict Check. The system SHALL prevent double-booking a doctor across different branches by verifying scheduling availability globally before slot confirmation.
  * *Acceptance Criteria*: Given Dr. X is scheduled to work at Branch A on Monday 9 AM - 1 PM, When a receptionist attempts to book Dr. X at Branch B for Monday 10 AM, Then the system blocks the booking and displays a scheduling error.
- **FR-005 (Must)**: Rescheduling & Cancellation. The system SHALL allow patients to reschedule or cancel appointments up to 2 hours before the scheduled time.
  * *Acceptance Criteria*: Given a patient with an appointment in 3 hours, When they click "Cancel" on the portal, Then the system updates the appointment state to "Cancelled", releases the time slot, and schedules a cancellation notification.
- **FR-012 (Must)**: Progressive Cancellation Warning (Tier 1). The system SHALL trigger a warning and log a penalty incident if a patient cancels an appointment less than 2 hours before the scheduled start time.
  * *Acceptance Criteria*: Given a patient with an appointment in 1.5 hours, When they click "Cancel" on the portal, Then the system displays a late-cancellation warning message, logs the incident against their profile, and updates the appointment state to "Cancelled" without blocking the action.
- **FR-013 (Must)**: Booking Soft Flagging (Tier 2). The system SHALL apply a "Soft Flag" on patients who accumulate 2 to 3 late cancellations or no-shows within a rolling 90-day window.
  * *Acceptance Criteria*: Given a patient with 2 previous late cancellations, When they or a receptionist attempt to create a new booking, Then the system displays a visual warning flag on their profile status, requiring confirmation before finalizing.
- **FR-014 (Must)**: Booking Restrictions (Tier 3). The system SHALL restrict self-service booking privileges for patients who accumulate 4 or more late cancellations or no-shows within a rolling 90-day window.
  * *Acceptance Criteria*: Given a patient with 4 previous late cancellations, When they attempt to book an appointment online, Then the system blocks the self-service booking flow, displays a message instructing them to contact the clinic directly, and requires receptionist/manager manual approval.
- **FR-015 (Must)**: Administrative Override for Booking Restrictions. The system SHALL allow authorized staff (Receptionists, Doctors, Managers) to manually override any patient booking restriction or soft flag during walk-in or phone registration.
  * *Acceptance Criteria*: Given a receptionist booking for a patient with Tier 3 restrictions, When they select "Override Restriction", Then the system permits the booking and logs the override with the receptionist's ID.
- **FR-016 (Must)**: Emergency Exemption. The system SHALL allow patients or staff to flag a late cancellation as an "Emergency", exempting the patient from penalty counting.
  * *Acceptance Criteria*: Given a patient cancelling an appointment in 1 hour, When they select "Emergency Cancellation", Then the system logs the cancellation for analytical tracking, but does not increment their late cancellation penalty count.
- **FR-017 (Must)**: Clinic-Initiated Cancellation Exemption. The system SHALL NOT penalize patients for cancellations initiated by the clinic or doctor.
  * *Acceptance Criteria*: Given a clinic-initiated schedule adjustment, When the administrator cancels the patient's appointment, Then the system does not apply a late cancellation count and marks the patient record for priority rescheduling.
- **FR-018 (Must)**: Time-Bound Availability Shifts. The system SHALL support scheduling doctors in branch-specific time-bound availability blocks rather than assigning a doctor statically to a single branch.
  * *Acceptance Criteria*: Given a doctor who works at Branch A on Monday mornings and Branch B on Monday afternoons, When availability is configured, Then the system saves separate time-bound shift blocks mapping the doctor to Branch A (09:00 - 13:00) and Branch B (14:00 - 18:00) respectively.
- **FR-019 (Must)**: Server-Side Booking Validation & Locking. The system scheduling engine SHALL validate bookings against the doctor's availability blocks and active appointments using database-level transactional locks to prevent race conditions during concurrent bookings.
  * *Acceptance Criteria*: Given two users attempting to book the exact same slot concurrently, When both requests hit the server, Then the database executes a transactional block locking the doctor schedule, registers the first request, and rejects the second request with a "Slot no longer available" error.
- **FR-020 (Must)**: Emergency Schedule Override. The system SHALL allow senior authorized users (Administrators, Managers) to manually override standard availability blocks to book emergency appointments, creating a linked audit log.
  * *Acceptance Criteria*: Given a manager booking an urgent walk-in appointment outside a doctor's scheduled shift, When they click "Schedule Override", Then the system creates the appointment and generates a detailed audit record containing the manager's ID, override reason, and timestamp.
- **FR-021 (Must)**: Doctor Shift Change Revalidation. The system SHALL automatically scan active appointments and flag conflicts when a doctor availability block is cancelled or reassigned.
  * *Acceptance Criteria*: Given a doctor shift is cancelled, When the scheduler updates the shift status, Then the system flags all affected appointments, alerts the branch manager, and triggers automated rescheduling notifications to the patients.

### 5.3 Clinical Records & Doctor Workspace
- **FR-006 (Must)**: Clinical Consultation Logging. The system SHALL allow doctors to record patient visit notes, diagnoses, and prescriptions.
  * *Acceptance Criteria*: Given a doctor in a session with a checked-in patient, When they submit the consultation form, Then the system updates the patient history record, encrypts the note, and marks the visit as "Completed".
- **FR-007 (Must)**: Emergency Cross-Branch Record Access. The system SHALL allow a licensed doctor to access a patient's historical records regardless of the registration branch.
  * *Acceptance Criteria*: Given a patient registered at Branch A visiting Branch B, When the attending doctor at Branch B requests access to the patient's record, Then the system displays the medical history and creates an audit log entry tagged with "Emergency Cross-Branch Access" containing the doctor's credentials and timestamp.
- **FR-008 (Must)**: Controlled Release of Lab Results. The system SHALL hide newly uploaded laboratory or diagnostic files from the patient until marked "Released" by a doctor.
  * *Acceptance Criteria*: Given a newly uploaded laboratory PDF, When the patient checks their portal before doctor review, Then the PDF is hidden. When the doctor marks the file status as "Released to Patient", Then the PDF becomes immediately visible on the patient's portal dashboard.

### 5.4 Check-in & Front Desk Operations
- **FR-009 (Must)**: Walk-In Registration. The system SHALL allow receptionists to register patients and book appointments.
  * *Acceptance Criteria*: Given a receptionist at the front desk, When they enter a walk-in patient's basic details and select an immediate vacant doctor slot, Then the system creates the profile and marks the appointment as "Booked - In Clinic".
- **FR-010 (Must)**: Patient Check-In. The system SHALL allow receptionists to mark patient arrival.
  * *Acceptance Criteria*: Given an upcoming appointment for the day, When the receptionist clicks "Check In" upon patient arrival, Then the system changes the appointment status to "Checked In" and notifies the assigned doctor's dashboard.

### 5.5 Management dashboards
- **FR-011 (Must)**: Real-time Operational Reports. The system SHALL display operational reports to authorized Managers and Senior Management.
  * *Acceptance Criteria*: Given a logged-in Branch Manager, When they load the dashboard, Then the system displays real-time statistics for daily appointments, doctor utilization, and no-shows for their assigned branch only.

---

## 6. Non-Functional Requirements

### 6.1 Performance
- **NFR-001**: **Database Search Latency**. Search queries for patient records or doctor schedules SHALL return results in less than 2.0 seconds under a baseline load of 100 concurrent users.
- **NFR-002**: **Page Load Speed**. Key web portal landing pages SHALL load in less than 3.0 seconds when accessed over a standard 3G/4G network connection in Nigeria.

### 6.2 Availability & Reliability
- **NFR-003**: **Core Service Availability**. The system SHALL maintain ≥ 99.9% uptime monthly during standard clinic operating hours (Monday to Saturday, 7:00 AM to 8:00 PM WAT).
- **NFR-004**: **Offline Resiliency (Caching)**. The receptionist and doctor scheduling dashboards SHALL cache the current day's appointment lists locally on the browser client, allowing read-only access for at least 2 hours in the event of local internet failure.

### 6.3 Security & Compliance
- **NFR-005**: **Data Protection Compliance (NDPR)**. The system SHALL store and process all patient data in compliance with the Nigeria Data Protection Regulation (NDPR).
- **NFR-006**: **Data Encryption**. Patient clinical notes, medical histories, and diagnoses SHALL be encrypted at rest using AES-256 and in transit using TLS 1.3.
- **NFR-007**: **Immutable Security Audit Log**. The system SHALL write a permanent, immutable audit entry for every read, write, modification, or clinical override of patient medical records, recording the user ID, timestamp, patient ID, IP address, and details of the action.
- **NFR-008**: **Separation of Clinical Data**. System administrators SHALL NOT have access to read patient clinical records, consultation notes, or diagnostic images.

---

## 7. AI / Intelligent System Requirements

*Note: Phase 1 establishes the API endpoints and scheduling logic to support the Phase 2 AI WhatsApp chatbot. The chatbot itself is a Phase 2 requirement.*

| ID | Requirement | Priority | Detail / Acceptance Criteria |
|---|---|---|---|
| **AI-001** | AI Safety Refusal | High (Phase 2) | The AI scheduling chatbot SHALL refuse to answer questions about medical diagnoses, clinical symptoms, or drug recommendations, and SHALL reply with a standard disclaimer directing the user to book a doctor consultation. |
| **AI-002** | Fallback to Rule-Based Menu | High (Phase 2) | If the AI NLP/LLM endpoint experiences a timeout (> 5.0 seconds) or is offline, the WhatsApp interface SHALL fall back to a structured, button-based interactive menu to allow basic booking functions. |
| **AI-003** | Transparency Notification | High (Phase 2) | The AI chatbot SHALL inform the patient in its first interaction that they are communicating with an automated system and not a human receptionist. |
| **AI-004** | Hand-off to Human | High (Phase 2) | If a patient asks to speak to a receptionist, or if the chatbot fails to resolve a request after three turns, the system SHALL route the conversation to the clinic's front-desk queue. |

---

## 8. Integration Requirements

| ID | External System | Integration Type | Direction | Requirement |
|---|---|---|---|---|
| **INT-001** | WhatsApp Business Cloud API | REST API | Outbound | The system SHALL send automated transactional templates (booking confirmations, change alerts, 24-hour and 2-hour reminders) to the patient's registered phone number. |
| **INT-002** | Termii Gateway | REST API | Outbound | The system SHALL utilize Termii as the primary local SMS provider to ensure delivery reliability, DND routing, and carrier compatibility (MTN/Airtel/Glo/9mobile) within Nigeria. |
| **INT-003** | Infobip Gateway | REST API | Outbound | The system SHALL integrate Infobip as the secondary backup SMS provider. |
| **INT-004** | Notification Abstraction Layer | Internal API | N/A | The system SHALL implement a pluggable `NotificationService` layer that abstracts SMS, WhatsApp, and Email integrations to avoid vendor lock-in and handle failovers automatically. |
| **INT-005** | Future Payment Gateway (Paystack/Flutterwave) | Webhooks / REST API | Bi-directional | The appointment engine database schemas SHALL implement payment states (`Pending`, `Deposit Paid`, `Fully Paid`, `Waived`, `Refunded`) to prevent schema rewrites in Phase 2. |

---

## 9. Data Requirements

- **DR-001 (Data Ownership)**: All medical records, clinical notes, and patient identifiers created on the platform remain the exclusive legal property of the healthcare clinic chain.
- **DR-002 (Data Retention)**: Medical records and patient files SHALL be retained on the active database for a minimum of 10 years, in accordance with national health archiving guidelines.
- **DR-003 (Data Classification)**:
  * **Confidential**: Patient profile details, phone numbers, email addresses.
  * **Restricted (Medical)**: Consultation logs, diagnostic images, prescriptions, diagnoses.
  * **Internal**: Operational performance reports, branch utilization metrics.
- **DR-004 (Scheduling Schema Entities)**:
  * **DoctorAvailability**: Represenation of doctor shifts containing `id` (UUID), `doctor_id` (UUID), `branch_id` (UUID), `start_datetime` (Timestamp), `end_datetime` (Timestamp), `status` (active/cancelled).
  * **Appointments**: Representation of individual booking states containing `id` (UUID), `doctor_id` (UUID), `patient_id` (UUID), `branch_id` (UUID), `start_datetime` (Timestamp), `end_datetime` (Timestamp), `status` (booked/cancelled/completed/no-show), `booking_source` (patient/receptionist/admin override).

---

## 10. Open Questions

| # | Question | Owner | Deadline | Impact |
|---|---|---|---|---|
| **OQ-001** | None | N/A | N/A | All initial elicitation open questions resolved. |

---

## 11. Glossary

| Term | Definition |
|---|---|
| **NDPR** | Nigeria Data Protection Regulation, governing data privacy and protection of Nigerian citizens. |
| **RBAC** | Role-Based Access Control, restricting system access to authorized users based on role definitions. |
| **WAT** | West Africa Time (UTC+1), the timezone for local clinic branch schedules. |
| **MVP** | Minimum Viable Product, the initial release containing only core mandatory features (Phase 1). |

---

## 12. Document Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-04 | Antigravity | Initial draft generated after Round 2 Elicitation. |
| 1.1 | 2026-06-04 | Antigravity | Updated with pluggable notifications, Termii integration, and progressive late cancellation penalty system. |
| 1.2 | 2026-06-04 | Antigravity | Integrated detailed scheduling engine rules, time-bound availability blocks, and transactional locking mechanics. |
| 1.3 | 2026-06-04 | Antigravity | Approved version. Status set to Approved. |
