# Clinic Modernization Platform (CMP) — C4 Architecture Models

This document presents the architecture of the Clinic Modernization Platform (CMP) using the **C4 Model** (System Context, Container, Component, and Database Entity-Relationship views) to detail the system boundaries and data flows.

---

## Level 1: System Context Diagram

The System Context diagram shows how the Clinic Modernization Platform (CMP) interacts with users (patients, clinic staff, managers) and external services (messaging gateways, encryption services).

```mermaid
graph TB
    %% Users
    Patient[Patient<br/>Registers, books, cancels appointments]
    Doctor[Doctor<br/>Views schedule, records clinical notes]
    Receptionist[Receptionist<br/>Registers walk-ins, checks in patients]
    Manager[Branch / Senior Manager<br/>Views utilization dashboards]
    Admin[System Administrator<br/>Configures system settings]

    %% Main System
    CMP[Clinic Modernization Platform<br/>CMP Web App & Database]

    %% External Systems
    WhatsApp[WhatsApp Cloud API<br/>Transactional templates & reminders]
    Termii[Termii API Gateway<br/>Primary Nigerian SMS sender]
    Infobip[Infobip API Gateway<br/>Secondary fallback SMS sender]
    KMS[AWS KMS<br/>Clinical record encryption keys]

    %% Relationships
    Patient -->|Uses mobile portal| CMP
    Doctor -->|Uses clinical portal on tablet/PC| CMP
    Receptionist -->|Uses desktop scheduling portal| CMP
    Manager -->|Monitors operations| CMP
    Admin -->|Manages configurations| CMP

    CMP -->|Sends confirmations & alerts| WhatsApp
    CMP -->|Sends fallback SMS alerts| Termii
    CMP -->|Sends secondary fallback SMS| Infobip
    CMP -->|Requests key operations| KMS
```

---

## Level 2: Container Diagram

The Container diagram decomposes the CMP into its runtime containers: the static **React PWA** frontend, the **FastAPI** backend API, the **PostgreSQL** database, and the **Redis/Celery** async queue.

```mermaid
graph TB
    subgraph Client Tier [Client Tier - Browser]
        PWA[React PWA Container<br/>Single Page App - Vite / React / Dexie.js<br/>Serves UI, handles local IndexedDB cache]
    end

    subgraph Hosting & Network [Edge Tier - AWS Infrastructure]
        CDN[CloudFront CDN<br/>Serves PWA static assets]
        Gateway[AWS API Gateway<br/>Routes API traffic, applies rate-limits]
    end

    subgraph Application Tier [Backend Application Tier]
        FastAPI[FastAPI Application Server<br/>Async Python 3.12 REST API<br/>Processes requests, enforces RBAC & locks]
        Workers[Celery Worker Instances<br/>Async task processors]
        Redis[Redis Queue<br/>In-memory broker for background tasks]
    end

    subgraph Data Tier [Storage & Encryption Tier]
        PostgreSQL[(PostgreSQL Database<br/>ACID scheduling database & audit log)]
        KMS[AWS KMS<br/>Manages Master Keys]
    end

    subgraph External Integrations [External Integration API Tier]
        WhatsAppAPI[WhatsApp Business Cloud API]
        TermiiAPI[Termii Gateway API]
        InfobipAPI[Infobip Gateway API]
    end

    %% Client and Edge connections
    PWA -->|Downloads static shell| CDN
    PWA -->|HTTPS API Requests / TLS 1.3| Gateway
    Gateway -->|Forwards requests| FastAPI

    %% Application Server connections
    FastAPI -->|Reads / Writes / Transaction Locks| PostgreSQL
    FastAPI -->|Requests Encryption/Decryption| KMS
    FastAPI -->|Publishes async events| Redis
    Redis -->|Feeds tasks| Workers

    %% Background worker connections
    Workers -->|Sends templates| WhatsAppAPI
    Workers -->|Sends local SMS| TermiiAPI
    Workers -->|Sends failover SMS| InfobipAPI
```

---

## Level 3: Component Diagram (FastAPI Backend)

This diagram details the internal modules of the **FastAPI Container** and how they interact to serve requests and execute business logic.

```mermaid
graph TB
    %% Gateway entry
    APIRequest[Incoming REST API Requests]

    subgraph FastAPI Container [FastAPI Backend Modules]
        Router[API Route Controllers<br/>FastAPI APIRouters<br/>Parses URLs & requests]
        
        Auth[Authentication & RBAC Manager<br/>FastAPI Security Scopes<br/>Validates JWTs & user permissions]
        
        Scheduler[Scheduling Engine<br/>Doctor shift & slot validator<br/>Executes pessimistic locks]
        
        ClinicalService[Clinical Record Service<br/>Column-level encryptor/decryptor<br/>Handles KMS integrations]
        
        OTPService[OTP Verification Engine<br/>Channel-agnostic logic<br/>Rate-limiting & code validation]
        
        NotificationPublisher[Notification Service Abstraction<br/>Enqueues async alert dispatches]
    end

    %% Storage & Queue Connections
    Router --> Auth
    Auth --> Router
    
    Router --> Scheduler
    Router --> ClinicalService
    Router --> OTPService
    Router --> NotificationPublisher

    Scheduler -->|Pessimistic transactions| PostgreSQL[(PostgreSQL DB)]
    ClinicalService -->|Envelope Encryption| AWSKMS[AWS KMS]
    ClinicalService -->|Write encrypted records| PostgreSQL
    OTPService -->|Write OTP sessions| PostgreSQL
    NotificationPublisher -->|Push async tasks| RedisQueue[Redis Task Queue]
```

---

## Level 4: Code Diagram (Database Entity-Relationship)

The Database ERD maps the relational structure of the data layer, including constraints and primary/foreign key connections.

```mermaid
erDiagram
    users {
        uuid id PK
        varchar phone_number UK
        varchar email UK
        varchar password_hash
        user_role role
        timestamp created_at
    }

    patient_profiles {
        uuid id PK
        uuid user_id FK
        varchar full_name
        date date_of_birth
        varchar gender
        varchar emergency_contact
    }

    doctor_availability {
        uuid id PK
        uuid doctor_id FK
        varchar branch_id
        timestamp start_datetime
        timestamp end_datetime
        boolean is_cancelled
    }

    appointments {
        uuid id PK
        uuid doctor_id FK
        uuid patient_id FK
        varchar branch_id
        timestamp start_datetime
        timestamp end_datetime
        appointment_status status
        payment_status payment_state
        varchar booking_source
    }

    clinical_records {
        uuid id PK
        uuid appointment_id FK
        uuid patient_id FK
        uuid doctor_id FK
        text encrypted_notes
        text encrypted_diagnosis
        text encrypted_prescriptions
        varchar kms_key_version
        timestamp created_at
    }

    verification_otps {
        uuid id PK
        varchar phone_number
        varchar hashed_otp
        integer attempts
        boolean is_used
        timestamp expires_at
        varchar delivery_channel
        timestamp created_at
    }

    security_audit_logs {
        uuid id PK
        uuid user_id
        varchar action_type
        uuid patient_id
        varchar ip_address
        timestamp timestamp
        text action_details
    }

    %% Relationships
    users ||--o| patient_profiles : "has profile"
    users ||--o{ doctor_availability : "schedules shifts"
    users ||--o{ appointments : "books as doctor/patient"
    appointments ||--o| clinical_records : "records findings"
    users ||--o{ clinical_records : "author/subject of"
```
