# Clinic Modernization Platform (CMP) — UML Design Models

This document presents the formal UML design models for the Clinic Modernization Platform (CMP). The diagrams are structured in **Mermaid** syntax, aligned with the platform's Software Requirements Document (SRD), Technical Specification, and Architecture Decision Records (ADRs).

***

## 1. Class Diagram (Static Entity Domain Model)

This diagram represents the database schema and system entities specified in **Section 4.2 (Data Model)** of the [Technical Specification](file:///C:/Users/DELL/Documents/Project/clinic_app_ase/technical_specification.md) and **DR-004** of the [Software Requirements Document](file:///C:/Users/DELL/Documents/Project/clinic_app_ase/software_requirements_document.md).

```mermaid
classDiagram
    direction TB
    class UserRole {
        <<enumeration>>
        PATIENT
        RECEPTIONIST
        DOCTOR
        MANAGER
        ADMIN
        EXECUTIVE
    }

    class AppointmentStatus {
        <<enumeration>>
        BOOKED
        CANCELLED
        COMPLETED
        NO_SHOW
    }

    class PaymentStatus {
        <<enumeration>>
        PENDING
        DEPOSIT_PAID
        FULLY_PAID
        WAIVED
        REFUNDED
    }

    class User {
        +UUID id
        +String phone_number
        +String email
        +String password_hash
        +UserRole role
        +DateTime created_at
        +DateTime updated_at
    }

    class PatientProfile {
        +UUID id
        +UUID user_id
        +String full_name
        +Date date_of_birth
        +String gender
        +String emergency_contact
        +DateTime created_at
    }

    class DoctorAvailability {
        +UUID id
        +UUID doctor_id
        +String branch_id
        +DateTime start_datetime
        +DateTime end_datetime
        +Boolean is_cancelled
        +DateTime created_at
        +check_dates()
    }

    class Appointment {
        +UUID id
        +UUID doctor_id
        +UUID patient_id
        +String branch_id
        +DateTime start_datetime
        +DateTime end_datetime
        +AppointmentStatus status
        +PaymentStatus payment_state
        +String booking_source
        +DateTime created_at
        +DateTime updated_at
        +check_app_dates()
    }

    class ClinicalRecord {
        +UUID id
        +UUID appointment_id
        +UUID patient_id
        +UUID doctor_id
        +String encrypted_notes
        +String encrypted_diagnosis
        +String encrypted_prescriptions
        +String kms_key_version
        +DateTime created_at
    }

    class VerificationOTP {
        +UUID id
        +String phone_number
        +String hashed_otp
        +Integer attempts
        +Boolean is_used
        +DateTime expires_at
        +String delivery_channel
        +DateTime created_at
    }

    class SecurityAuditLog {
        +UUID id
        +UUID user_id
        +String action_type
        +UUID patient_id
        +String ip_address
        +DateTime timestamp
        +String action_details
    }

    UserRole <-- User : role type
    AppointmentStatus <-- Appointment : status type
    PaymentStatus <-- Appointment : payment_state type

    User "1" -- "0..1" PatientProfile : owns
    User "1" -- "*" DoctorAvailability : schedules shifts
    User "1" -- "*" Appointment : books as doctor or patient
    Appointment "1" -- "0..1" ClinicalRecord : references
    User "1" -- "*" ClinicalRecord : authors/subject of
```

***

## 2. Component Diagram (FastAPI Backend Architecture)

Decomposes the logical architecture of the **FastAPI Container** based on **Level 3 Component Diagram** of the [C4 Architecture Models](file:///C:/Users/DELL/Documents/Project/clinic_app_ase/c4_architecture_models.md) and design choices in [ADR-003](file:///C:/Users/DELL/Documents/Project/clinic_app_ase/adr-003-application-level-column-encryption.md) and [ADR-004](file:///C:/Users/DELL/Documents/Project/clinic_app_ase/adr-004-pluggable-notification-failover.md).

```mermaid
graph TB
    subgraph Client [Client Tier]
        PWA[React PWA Client]
    end

    subgraph API [FastAPI Backend Container]
        subgraph Routers [API Route Controllers]
            AuthRouter[Auth & Verification Router]
            BookingRouter[Appointment Booking Router]
            ClinicalRouter[Clinical Records Router]
            ReportRouter[Operational Reports Router]
        end

        subgraph Services [Business Logic & Services]
            AuthService[Authentication & RBAC Manager]
            Scheduler[Scheduling Engine]
            ClinicalService[Clinical Record Service]
            OTPService[OTP Verification Engine]
            NotificationService[Pluggable Notification Service]
        end

        subgraph Security [Security & Cryptography]
            KMSEngryptor[KMS Envelope Encryptor]
        end
    end

    subgraph Database [Storage & Queue Tier]
        PostgreSQL[(PostgreSQL DB)]
        RedisQueue[Redis Task Queue]
    end

    subgraph External [External Services]
        AWSKMS[AWS KMS]
        WhatsAppAPI[WhatsApp Business Cloud API]
        TermiiAPI[Termii Gateway API]
        InfobipAPI[Infobip Gateway API]
    end

    PWA -->|HTTPS REST API Requests| Routers

    AuthRouter --> AuthService
    AuthRouter --> OTPService
    BookingRouter --> Scheduler
    BookingRouter --> NotificationService
    ClinicalRouter --> ClinicalService
    ClinicalRouter --> AuthService
    ReportRouter --> AuthService

    Scheduler -->|Pessimistic Row-level Locks| PostgreSQL
    ClinicalService -->|Read/Write Encrypted Columns| PostgreSQL
    ClinicalService --> KMSEngryptor
    KMSEngryptor -->|GenerateDEK / Decrypt| AWSKMS
    OTPService -->|Manage OTP sessions| PostgreSQL
    NotificationService -->|Push tasks| RedisQueue

    subgraph Background [Background Processing]
        Workers[Celery Background Workers]
    end

    RedisQueue --> Workers
    Workers --> WhatsAppAPI
    Workers --> TermiiAPI
    Workers --> InfobipAPI
```

***

## 3. Behavioral Sequence Diagrams

### 3.1 Doctor Shift Validation & Concurrent Booking (Pessimistic Locking)

Illustrates how the database pessimistic locking mechanism (**FR-019**, **NFR-001**) handles two concurrent requests trying to book the exact same doctor time-slot.

```mermaid
sequenceDiagram
    autonumber
    actor PatientA as Patient A Client
    actor PatientB as Patient B Client
    participant API as FastAPI Backend
    participant DB as PostgreSQL DB

    Note over PatientA, DB: Concurrent booking requests for Dr. X at Monday 9:00 AM
    PatientA->>API: POST /api/v1/appointments (Dr. X, 9:00 AM)
    PatientB->>API: POST /api/v1/appointments (Dr. X, 9:00 AM)

    critical Transaction A starts
        API->>DB: BEGIN Transaction A
        API->>DB: SELECT DoctorAvailability with_for_update() (Dr. X, Monday 9 AM - 9:30 AM)
        activate DB
        Note over DB: Lock acquired for Transaction A on DoctorAvailability row
    and Transaction B starts
        API->>DB: BEGIN Transaction B
        API->>DB: SELECT DoctorAvailability with_for_update() (Dr. X, Monday 9 AM - 9:30 AM)
        Note over DB: Transaction B BLOCKED, waiting for Lock on DoctorAvailability row
    end

    API->>DB: SELECT Appointments with_for_update() (Dr. X, Monday 9:00 AM)
    DB-->>API: No conflicting appointments found
    API->>DB: INSERT INTO appointments (Dr. X, Patient A, booked)
    API->>DB: COMMIT Transaction A
    deactivate DB
    Note over DB: Lock released. Transaction A committed.

    activate DB
    Note over DB: Transaction B unblocks, lock acquired by Transaction B
    DB-->>API: Returns DoctorAvailability shift data
    API->>DB: SELECT Appointments with_for_update() (Dr. X, Monday 9:00 AM)
    DB-->>API: Conflict found (Appointment for Patient A exists)
    API->>DB: ROLLBACK Transaction B
    deactivate DB
    Note over DB: Lock released. Transaction B rolled back.
    API-->>PatientA: HTTP 201 Created (Appointment ID)
    API-->>PatientB: HTTP 409 Conflict ("Slot is no longer available")
```

### 3.2 Hierarchical Verification & OTP Delivery Flow (WhatsApp-First, SMS Fallback)

Visualizes the multi-gateway verification flow (**OQ-002**, **INT-004**) attempting delivery via WhatsApp, falling back to local Termii SMS, and backing up to Infobip.

```mermaid
sequenceDiagram
    autonumber
    actor Patient as Patient Browser
    participant API as FastAPI Backend
    participant DB as PostgreSQL DB
    participant MQ as Task Queue (Celery/Redis)
    participant WA as WhatsApp API
    participant Termii as Termii SMS API
    participant Infobip as Infobip SMS API

    Patient->>API: POST /api/v1/auth/verify-request (phone_number)
    API->>DB: UPDATE verification_otps SET is_used = TRUE (invalidate existing active OTPs)
    API->>DB: INSERT INTO verification_otps (phone_number, hashed_otp, expires_at, status=Pending)
    API->>MQ: Enqueue Notification Failover Task (delivery_id)
    API-->>Patient: HTTP 200 OK {"message": "Verification code sent"}

    Note over MQ, WA: Primary Routing: WhatsApp Cloud API
    MQ->>WA: POST /v1/messages (Send OTP Template)
    
    alt WhatsApp Success
        WA-->>MQ: HTTP 200 OK (Status: Acknowledged)
        MQ->>DB: UPDATE verification_otps SET delivery_channel='whatsapp'
    else WhatsApp Fails (Timeout 15s or API Error)
        Note over MQ, Termii: Fallback Routing: Termii SMS Gateway
        MQ->>Termii: POST /api/sms/send (Primary SMS)
        alt Termii Success
            Termii-->>MQ: HTTP 200 OK (Sent)
            MQ->>DB: UPDATE verification_otps SET delivery_channel='sms_termii'
        else Termii Fails (Gateway Error / Timeout)
            Note over MQ, Infobip: Secondary Fallback Routing: Infobip SMS Gateway
            MQ->>Infobip: POST /sms/2/text/advanced (Secondary SMS)
            alt Infobip Success
                Infobip-->>MQ: HTTP 200 OK (Sent)
                MQ->>DB: UPDATE verification_otps SET delivery_channel='sms_infobip'
            else Infobip Fails
                Infobip-->>MQ: Connection Error
                MQ->>DB: UPDATE verification_otps SET delivery_status='failed'
            end
        end
    end
```

### 3.3 Clinical Consultation Logging & Audited Record Access

Represents the cryptographic workflow (**FR-006**, **FR-007**, **NFR-006**, **NFR-007**, **NFR-008**) for writing encrypted records and logging emergency overrides.

```mermaid
sequenceDiagram
    autonumber
    actor Doc as Doctor Client
    participant API as FastAPI Backend
    participant KMS as AWS KMS
    participant DB as PostgreSQL DB

    Note over Doc, DB: Clinical Record Writing Flow (FR-006, NFR-006)
    Doc->>API: POST /api/v1/clinical-records (appointment_id, notes, diagnosis)
    API->>API: Verify User Role is 'doctor' (RBAC Enforcement)
    API->>KMS: Request GenerateDataKey (kms_key_version)
    KMS-->>API: Plaintext DEK & Encrypted DEK
    API->>API: Encrypt notes & diagnosis with Plaintext DEK via AES-256-GCM
    API->>DB: BEGIN Transaction
    API->>DB: INSERT INTO clinical_records (encrypted_notes, encrypted_diagnosis, kms_key_version)
    API->>DB: INSERT INTO security_audit_logs (action_type='WRITE_CLINICAL_RECORD', doctor_id)
    API->>DB: COMMIT Transaction
    DB-->>API: Success
    API-->>Doc: HTTP 201 Created

    Note over Doc, DB: Emergency Cross-Branch Record Access Flow (FR-007, NFR-008)
    Doc->>API: GET /api/v1/clinical-records/patient/{id}
    API->>API: Verify User Role is 'doctor'
    API->>DB: SELECT encrypted_notes, kms_key_version FROM clinical_records WHERE patient_id = {id}
    DB-->>API: Return Encrypted Data & kms_key_version
    API->>KMS: Decrypt Encrypted DEK (kms_key_version)
    KMS-->>API: Plaintext DEK
    API->>API: Decrypt notes with Plaintext DEK
    API->>DB: BEGIN Transaction (Log access)
    API->>DB: INSERT INTO security_audit_logs (action_type='READ_CLINICAL_RECORD', details='Emergency Cross-Branch Access')
    API->>DB: COMMIT Transaction
    API-->>Doc: Return Plaintext Patient clinical history
```

***

## 4. Entity Lifecycle State Diagrams

### 4.1 Appointment & Payment State Machine

Maps out status and payment transitions for the main scheduling unit (**DR-004**, **INT-005**).

```mermaid
stateDiagram-v2
    [*] --> Booked_Pending : Patient/Staff Books Appointment
    
    state Booked_Pending {
        [*] --> Status_Booked
        [*] --> Payment_Pending
    }

    state Cancelled {
        [*] --> Status_Cancelled
        state "Payment Processed / Waived" as Pay_Proc
    }

    state Completed {
        [*] --> Status_Completed
        state "Fully Paid / Waived" as Pay_Done
    }

    state NoShow {
        [*] --> Status_NoShow
        state "Late/No-Show Penalty Applied" as Pen_App
    }

    Booked_Pending --> Cancelled : Cancelled > 2h before (Normal Cancellation)
    Booked_Pending --> Cancelled : Cancelled < 2h before (Late Cancellation - Penalty logged)
    Booked_Pending --> Completed : Doctor submits consultation log (FR-006)
    Booked_Pending --> NoShow : Patient fails to arrive (No-show - Penalty logged)

    Completed --> [*]
    Cancelled --> [*]
    NoShow --> [*]
```

### 4.2 Patient Penalty & Booking Restriction Lifecycle

Shows how late cancellations and no-shows affect patient booking permissions in rolling 90-day windows (**FR-012**, **FR-013**, **FR-014**).

```mermaid
stateDiagram-v2
    [*] --> Normal : New Patient Account Registered
    
    Normal --> Tier1_Warning : 1st Late Cancel / No-show
    Tier1_Warning --> Tier2_SoftFlag : 2nd-3rd Late Cancel / No-show
    Tier2_SoftFlag --> Tier3_Restricted : >= 4th Late Cancel / No-show

    Tier3_Restricted --> Tier2_SoftFlag : rolling 90 days elapse for older incidents
    Tier2_SoftFlag --> Tier1_Warning : rolling 90 days elapse for older incidents
    Tier1_Warning --> Normal : rolling 90 days elapse for older incidents

    state Normal {
        Note: Full self-service online booking enabled
    }
    state Tier1_Warning {
        Note: Warning banner shown on booking/cancellation screen
    }
    state Tier2_SoftFlag {
        Note: Soft flag on profile; requires confirmation to schedule
    }
    state Tier3_Restricted {
        Note: Online booking BLOCKED. Requires receptionist manual override.
    }
```

***

## 5. Activity Control Flow Diagrams

### 5.1 Booking Request & Restriction Validation Flow

Details the step-by-step control logic executed by the scheduling engine when a booking request arrives (**FR-003**, **FR-015**, **FR-019**).

```mermaid
flowchart TD
    Start([Start Booking Flow]) --> SelectDetails[Select Branch, Doctor, Date & Time]
    SelectDetails --> CheckTier{Check Patient Penalty Tier}
    
    CheckTier -->|Tier 3: Restricted| IsStaff{Is Requester Clinic Staff?}
    IsStaff -->|Yes| OverrideChecked{Override Option Selected?}
    OverrideChecked -->|Yes| LogOverride[Log Admin Override to Audit Trail] --> VerifyShift
    OverrideChecked -->|No| BlockBooking[Show Error: Override Required] --> EndBooking([End])
    IsStaff -->|No| BlockSelfService[Block Online Booking. Prompt contact clinic] --> EndBooking
    
    CheckTier -->|Tier 2: Soft Flag| WarnSoft[Display Warning Flag] --> ConfirmBooking{Confirm Booking?}
    ConfirmBooking -->|Yes| VerifyShift
    ConfirmBooking -->|No| CancelRequest[Cancel Request] --> EndBooking

    CheckTier -->|Normal / Tier 1| VerifyShift{Doctor has Availability Shift?}
    
    VerifyShift -->|No| BlockAvailability[Show Error: Doctor Unavailable] --> EndBooking
    VerifyShift -->|Yes| AcquireLock[Acquire Pessimistic DB Lock on Shift & Slots]
    
    AcquireLock --> CheckConflict{Conflicting Appointment Exists?}
    CheckConflict -->|Yes| BlockConflict[Show Error: Slot No Longer Available] --> EndBooking
    CheckConflict -->|No| CreateAppt[Create Appointment with status='booked']
    
    CreateAppt --> EnqueueAlert[Enqueue Notification Task in Redis]
    EnqueueAlert --> SuccessBooking[Display Confirmation] --> EndBooking
```

### 5.2 Cancellation Penalty Engine Control Flow

Details the business rules processed by the system when an appointment is cancelled (**FR-012** to **FR-017**).

```mermaid
flowchart TD
    Start([Start Cancellation Request]) --> IdentifyRequester{Who Initiated Cancellation?}
    
    IdentifyRequester -->|Clinic / Doctor| ClinicExempt[Mark as Clinic-Initiated Exemption] --> DoCancel[Cancel Appointment & Release Slot]
    IdentifyRequester -->|Patient| CheckTime{Time until Appointment Starts}
    
    CheckTime -->|>= 2 Hours| DoCancel
    CheckTime -->|< 2 Hours| CheckEmergency{Marked as Emergency?}
    
    CheckEmergency -->|Yes| LogEmergency[Log Emergency Exemption] --> DoCancel
    CheckEmergency -->|No| LogPenalty[Log Late Cancellation Incident on Patient Profile]
    
    LogPenalty --> CountIncidents[Count Late Cancel/No-show incidents in rolling 90 days]
    CountIncidents --> UpdateTier{Update Patient Penalty Tier}
    
    UpdateTier -->|1 Incident| SetTier1[Set Penalty Tier = Tier 1 Warning] --> DoCancel
    UpdateTier -->|2-3 Incidents| SetTier2[Set Penalty Tier = Tier 2 Soft Flag] --> DoCancel
    UpdateTier -->|>= 4 Incidents| SetTier3[Set Penalty Tier = Tier 3 Restricted] --> DoCancel
    
    DoCancel --> EnqueueNotification[Enqueue Cancellation Alert to Task Queue]
    EnqueueNotification --> Success([End])
```
