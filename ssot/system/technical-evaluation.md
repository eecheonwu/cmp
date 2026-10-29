# Technical Evaluation

## Executive Summary
This Technical Evaluation assesses frontend, backend, task queue, database/storage, and AI framework options for the Clinical Management Platform (CMP), a brownfield healthcare appointment and clinical records system. The evaluation aligns with the Software Requirements Document, which mandates Python 3.12, FastAPI, PostgreSQL 15, Redis 7, Celery, React (Vite + Tailwind), application-level column encryption, JWT authentication, and immutable audit logging. No AI/ML capabilities are required per requirement AI-001.

## Frontend Framework
**Requirement:** The frontend must be a React PWA (per ADR-002) consuming the FastAPI backend via REST/JSON, supporting patient registration, appointment booking, clinical record viewing, and notification receipt. It must pass ESLint and run in a Node container with Nginx per NFR-009 and NFR-008.

### Options Considered
#### React (Vite + Tailwind CSS)
- **Pros:** Matches existing SRD tech stack and ADR-002 PWA decision; Vite provides fast HMR and optimized builds; Tailwind enables rapid, consistent UI development; large ecosystem for healthcare UI components; easy integration with REST/JSON APIs.
- **Cons:** Requires careful state management for complex clinical workflows; PWA offline capabilities need additional service worker configuration; bundle size can grow without strict code splitting.
#### Vue.js (Vite + Pinia)
- **Pros:** Gentle learning curve; excellent documentation; Vite compatibility; reactive data model suits form-heavy clinical interfaces.
- **Cons:** Deviates from mandated React stack; smaller ecosystem for specialized healthcare components; team retraining required.
#### Angular
- **Pros:** Opinionated structure; built-in HTTP client and form validation; strong typing out of the box.
- **Cons:** Heavier bundle size; steeper learning curve; inconsistent with existing React-based frontend and ADR-002.

### Decision
React (Vite + Tailwind CSS) — mandated by SRD tech stack and ADR-002; best fit for React PWA requirement and existing frontend codebase.

## Backend API
**Requirement:** Backend API must be FastAPI (Python 3.12) with Uvicorn ASGI server, SQLAlchemy/asyncpg ORM, Alembic migrations, python-jose/passlib/bcrypt authentication, cryptography for application-level encryption, structlog structured logging, and httpx/aiohttp HTTP clients. Must satisfy FR-001 through FR-012 and NFR-001, NFR-006, NFR-007, NFR-008.

### Options Considered
#### FastAPI (Python 3.12)
- **Pros:** Explicitly mandated in SRD; native async/await support with asyncpg; automatic OpenAPI/Swagger docs; high performance (Starlette/Pydantic); strong dependency injection for auth/JWT middleware; aligns with NFR-001 p95 200ms latency target.
- **Cons:** Smaller ecosystem than Django for built-in admin; requires manual assembly of auth, migrations, and encryption components; async learning curve for team.
#### Django REST Framework (Python 3.12)
- **Pros:** Batteries-included admin, ORM, and authentication; mature ecosystem; robust security defaults.
- **Cons:** Not in SRD stack; synchronous by default (requires async adapters); heavier than FastAPI; migration from existing FastAPI codebase would be costly.
#### Flask (Python 3.12)
- **Pros:** Lightweight and flexible; easy to learn.
- **Cons:** Lacks built-in async support and validation; requires many extensions to match FastAPI features; not aligned with SRD.

### Decision
FastAPI (Python 3.12) — mandated by SRD; best satisfies async performance, OpenAPI generation, and Python 3.12 container constraint.

## Async Task Queue
**Requirement:** Asynchronous task processing via Celery/Redis for notification delivery (email/OTP), booking confirmations, and retryable tasks with exponential backoff per NFR-003. Redis 7 required for broker and rate limiting. LocalStack emulates AWS services in dev/CI.

### Options Considered
#### Celery + Redis 7
- **Pros:** Explicitly mandated in SRD (Celery 5.3.6, Redis 7); mature Python task queue; supports retries, exponential backoff, chords, and periodic tasks; broad community and operational tooling; integrates cleanly with FastAPI and asyncpg.
- **Cons:** Operational overhead of managing workers and beat scheduler; visibility requires Flower or custom monitoring; result backend configuration needed for task state tracking.
#### Redis Queue (RQ) + Redis 7
- **Pros:** Simpler API and lower operational complexity than Celery; Python-native; easy to inspect queues via redis-cli.
- **Cons:** Fewer advanced workflow primitives (chords, chains, scheduling); less mature retry/backoff semantics; deviates from SRD-mandated Celery.
#### Dramatiq + Redis 7
- **Pros:** Focus on simplicity and reliability; low latency; predictable message processing.
- **Cons:** Smaller ecosystem; fewer integrations; not aligned with SRD tech stack.

### Decision
Celery + Redis 7 — mandated by SRD; best supports notification failover retries, exponential backoff, and existing LocalStack/CI configuration.

## Database & Storage
**Requirement:** PostgreSQL 15 (postgres:15-alpine) as the single-tenant cmp_db database, accessed via SQLAlchemy/asyncpg with Alembic migrations (0001 through 0011). Application-level column-level encryption for sensitive clinical record fields using cryptography 41.0.7 and AWS KMS (LocalStack in dev, AWS KMS in prod) per NFR-004 and FR-008. Must support concurrency-safe scheduling (FR-007) and health checks (FR-012, NFR-002).

### Options Considered
#### PostgreSQL 15 + SQLAlchemy/asyncpg + Alembic
- **Pros:** Explicitly mandated in SRD; native JSONB and advanced indexing for clinical records; strong concurrency control via row-level locking and advisory locks for booking concurrency (FR-007); proven encryption integration with application-layer cryptography; Alembic supports schema versioning (FR-011).
- **Cons:** Application-level encryption adds key management complexity and query limitations on encrypted columns; no built-in zero-downtime migration strategy evidenced in SRD.
#### MySQL 8.0 + SQLAlchemy
- **Pros:** Wide adoption; good performance; mature replication.
- **Cons:** Not in SRD stack; deviates from PostgreSQL 15 constraint; encryption and JSON handling differ from PostgreSQL.
#### MongoDB + Motor
- **Pros:** Flexible schema for evolving clinical records; horizontal scaling.
- **Cons:** Not relational; weaker ACID guarantees for financial/clinical consistency; not in SRD stack; conflicts with PostgreSQL 15 constraint.

### Decision
PostgreSQL 15 + SQLAlchemy/asyncpg + Alembic — mandated by SRD; best satisfies relational integrity, concurrency-safe scheduling, and application-level encryption requirements.

## AI Agent Framework
**Requirement:** No AI/ML frameworks, models, or inference endpoints were detected in the dependency manifests or codebase profile (AI-001). Evaluation is included for completeness only; no AI agent functionality is required for CMP.

### Options Considered
#### null / Not Applicable
- **Pros:** No additional dependencies, technical debt, or security surface area; aligns with SRD AI-001; reduces compliance scope for healthcare data.
- **Cons:** null applicable.
#### LangChain
- **Pros:** Popular orchestration for LLM-based agents if future AI features are added.
- **Cons:** Unnecessary for current requirements; introduces model governance and data privacy risks in a healthcare context; not in SRD stack.
#### LlamaIndex
- **Pros:** Useful for RAG over clinical documents if future requirements emerge.
- **Cons:** Not required per AI-001; adds operational complexity and PHI exposure considerations.

### Decision
null / Not Applicable — SRD requirement AI-001 explicitly states no AI/ML frameworks are detected or required.