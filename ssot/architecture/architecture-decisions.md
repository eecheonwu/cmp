# Architecture Decision Records

## ADR-001: Frontend Framework Selection for Clinical Management Platform
**Status:** Accepted  
**Deciders:** Engineering Team, Product Stakeholders

### Context
The frontend must be a React PWA (per ADR-002) consuming the FastAPI backend via REST/JSON, supporting patient registration, appointment booking, clinical record viewing, and notification receipt. It must pass ESLint and run in a Node container with Nginx per NFR-009 and NFR-008.

### Decision
React (Vite + Tailwind CSS) — mandated by SRD tech stack and ADR-002; best fit for React PWA requirement and existing frontend codebase.

### Rationale
Matches existing SRD tech stack and ADR-002 PWA decision; Vite provides fast HMR and optimized builds; Tailwind enables rapid, consistent UI development; large ecosystem for healthcare UI components; easy integration with REST/JSON APIs.

### Options Considered
| Option | Pros | Cons | Estimated Effort |
|---|---|---|---|
| React (Vite + Tailwind CSS) | Matches existing SRD tech stack and ADR-002 PWA decision; Vite provides fast HMR and optimized builds; Tailwind enables rapid, consistent UI development; large ecosystem for healthcare UI components; easy integration with REST/JSON APIs. | Requires careful state management for complex clinical workflows; PWA offline capabilities need additional service worker configuration; bundle size can grow without strict code splitting. | Low (aligned with existing stack) |
| Vue.js (Vite + Pinia) | Gentle learning curve; excellent documentation; Vite compatibility; reactive data model suits form-heavy clinical interfaces. | Deviates from mandated React stack; smaller ecosystem for specialized healthcare components; team retraining required. | Medium (requires team retraining and stack deviation) |
| Angular | Opinionated structure; built-in HTTP client and form validation; strong typing out of the box. | Heavier bundle size; steeper learning curve; inconsistent with existing React-based frontend and ADR-002. | High (heavier bundle, steeper learning curve, inconsistent with existing codebase) |

### Consequences
- Frontend remains consistent with ADR-002 PWA requirement and SRD-mandated React stack.
- Requires careful state management for complex clinical workflows and additional service worker configuration for PWA offline capabilities.
- Bundle size must be monitored with strict code splitting to prevent growth.

## ADR-002: Backend API Framework Selection
**Status:** Accepted  
**Deciders:** Engineering Team, Architecture Review Board

### Context
Backend API must be FastAPI (Python 3.12) with Uvicorn ASGI server, SQLAlchemy/asyncpg ORM, Alembic migrations, python-jose/passlib/bcrypt authentication, cryptography for application-level encryption, structlog structured logging, and httpx/aiohttp HTTP clients. Must satisfy FR-001 through FR-012 and NFR-001, NFR-006, NFR-007, NFR-008.

### Decision
FastAPI (Python 3.12) — mandated by SRD; best satisfies async performance, OpenAPI generation, and Python 3.12 container constraint.

### Rationale
Explicitly mandated in SRD; native async/await support with asyncpg; automatic OpenAPI/Swagger docs; high performance (Starlette/Pydantic); strong dependency injection for auth/JWT middleware; aligns with NFR-001 p95 200ms latency target.

### Options Considered
| Option | Pros | Cons | Estimated Effort |
|---|---|---|---|
| FastAPI (Python 3.12) | Explicitly mandated in SRD; native async/await support with asyncpg; automatic OpenAPI/Swagger docs; high performance (Starlette/Pydantic); strong dependency injection for auth/JWT middleware; aligns with NFR-001 p95 200ms latency target. | Smaller ecosystem than Django for built-in admin; requires manual assembly of auth, migrations, and encryption components; async learning curve for team. | Low (mandated, existing codebase alignment) |
| Django REST Framework (Python 3.12) | Batteries-included admin, ORM, and authentication; mature ecosystem; robust security defaults. | Not in SRD stack; synchronous by default (requires async adapters); heavier than FastAPI; migration from existing FastAPI codebase would be costly. | High (migration from FastAPI, not in SRD stack) |
| Flask (Python 3.12) | Lightweight and flexible; easy to learn. | Lacks built-in async support and validation; requires many extensions to match FastAPI features; not aligned with SRD. | Medium (requires many extensions, lacks built-in async) |

### Consequences
- Backend aligns with SRD-mandated Python 3.12 and FastAPI stack.
- Requires manual assembly of auth, migrations, and encryption components; team must manage async learning curve.
- Smaller built-in admin ecosystem compared to Django; custom tooling may be needed.

## ADR-003: Asynchronous Task Queue Selection
**Status:** Accepted  
**Deciders:** Engineering Team, DevOps

### Context
Asynchronous task processing via Celery/Redis for notification delivery (email/OTP), booking confirmations, and retryable tasks with exponential backoff per NFR-003. Redis 7 required for broker and rate limiting. LocalStack emulates AWS services in dev/CI.

### Decision
Celery + Redis 7 — mandated by SRD; best supports notification failover retries, exponential backoff, and existing LocalStack/CI configuration.

### Rationale
Explicitly mandated in SRD (Celery 5.3.6, Redis 7); mature Python task queue; supports retries, exponential backoff, chords, and periodic tasks; broad community and operational tooling; integrates cleanly with FastAPI and asyncpg.

### Options Considered
| Option | Pros | Cons | Estimated Effort |
|---|---|---|---|
| Celery + Redis 7 | Explicitly mandated in SRD (Celery 5.3.6, Redis 7); mature Python task queue; supports retries, exponential backoff, chords, and periodic tasks; broad community and operational tooling; integrates cleanly with FastAPI and asyncpg. | Operational overhead of managing workers and beat scheduler; visibility requires Flower or custom monitoring; result backend configuration needed for task state tracking. | Low (mandated, existing CI configuration) |
| Redis Queue (RQ) + Redis 7 | Simpler API and lower operational complexity than Celery; Python-native; easy to inspect queues via redis-cli. | Fewer advanced workflow primitives (chords, chains, scheduling); less mature retry/backoff semantics; deviates from SRD-mandated Celery. | Medium (simpler but deviates from SRD) |
| Dramatiq + Redis 7 | Focus on simplicity and reliability; low latency; predictable message processing. | Smaller ecosystem; fewer integrations; not aligned with SRD tech stack. | Medium (smaller ecosystem, not aligned with SRD) |

### Consequences
- Supports notification failover retries, exponential backoff, and existing LocalStack/CI configuration.
- Introduces operational overhead of managing workers and beat scheduler.
- Requires Flower or custom monitoring for task visibility.

## ADR-004: Database and Storage Selection
**Status:** Accepted  
**Deciders:** Engineering Team, Database Administrators

### Context
PostgreSQL 15 (postgres:15-alpine) as the single-tenant cmp_db database, accessed via SQLAlchemy/asyncpg with Alembic migrations (0001 through 0011). Application-level column-level encryption for sensitive clinical record fields using cryptography 41.0.7 and AWS KMS (LocalStack in dev, AWS KMS in prod) per NFR-004 and FR-008. Must support concurrency-safe scheduling (FR-007) and health checks (FR-012, NFR-002).

### Decision
PostgreSQL 15 + SQLAlchemy/asyncpg + Alembic — mandated by SRD; best satisfies relational integrity, concurrency-safe scheduling, and application-level encryption requirements.

### Rationale
Explicitly mandated in SRD; native JSONB and advanced indexing for clinical records; strong concurrency control via row-level locking and advisory locks for booking concurrency (FR-007); proven encryption integration with application-layer cryptography; Alembic supports schema versioning (FR-011).

### Options Considered
| Option | Pros | Cons | Estimated Effort |
|---|---|---|---|
| PostgreSQL 15 + SQLAlchemy/asyncpg + Alembic | Explicitly mandated in SRD; native JSONB and advanced indexing for clinical records; strong concurrency control via row-level locking and advisory locks for booking concurrency (FR-007); proven encryption integration with application-layer cryptography; Alembic supports schema versioning (FR-011). | Application-level encryption adds key management complexity and query limitations on encrypted columns; no built-in zero-downtime migration strategy evidenced in SRD. | Low (mandated, existing stack) |
| MySQL 8.0 + SQLAlchemy | Wide adoption; good performance; mature replication. | Not in SRD stack; deviates from PostgreSQL 15 constraint; encryption and JSON handling differ from PostgreSQL. | High (deviates from SRD stack) |
| MongoDB + Motor | Flexible schema for evolving clinical records; horizontal scaling. | Not relational; weaker ACID guarantees for financial/clinical consistency; not in SRD stack; conflicts with PostgreSQL 15 constraint. | High (not relational, conflicts with SRD) |

### Consequences
- Satisfies relational integrity, concurrency-safe scheduling, and application-level encryption requirements.
- Application-level encryption adds key management complexity and query limitations on encrypted columns.
- No built-in zero-downtime migration strategy evidenced in SRD; must be addressed in operational planning.

## ADR-005: AI Agent Framework Selection
**Status:** Accepted  
**Deciders:** Engineering Team, Compliance

### Context
No AI/ML frameworks, models, or inference endpoints were detected in the dependency manifests or codebase profile (AI-001). Evaluation is included for completeness only; no AI agent functionality is required for CMP.

### Decision
null / Not Applicable — SRD requirement AI-001 explicitly states no AI/ML frameworks are detected or required.

### Rationale
No additional dependencies, technical debt, or security surface area; aligns with SRD AI-001; reduces compliance scope for healthcare data.

### Options Considered
| Option | Pros | Cons | Estimated Effort |
|---|---|---|---|
| null / Not Applicable | No additional dependencies, technical debt, or security surface area; aligns with SRD AI-001; reduces compliance scope for healthcare data. | null applicable. | null |
| LangChain | Popular orchestration for LLM-based agents if future AI features are added. | Unnecessary for current requirements; introduces model governance and data privacy risks in a healthcare context; not in SRD stack. | Medium (unnecessary, adds PHI exposure considerations) |
| LlamaIndex | Useful for RAG over clinical documents if future requirements emerge. | Not required per AI-001; adds operational complexity and PHI exposure considerations. | Medium (not required, adds operational complexity) |

### Consequences
- No AI/ML dependencies introduced; reduced compliance scope for healthcare data.
- No model governance or PHI exposure risks from AI frameworks.
- Future AI features would require a new ADR and compliance review.