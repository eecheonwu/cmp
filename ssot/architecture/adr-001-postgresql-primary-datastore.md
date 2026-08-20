# ADR-001: Choice of PostgreSQL as the Primary Datastore

**Status**: Accepted
**Date**: 2026-06-04
**Deciders**: Antigravity (AI Architect), Clinic Owner, Engineering Lead

## Context

The Clinic Modernization Platform (CMP) manages scheduling, availability shifts, and medical records across a growing chain of clinic branches. The system has critical requirements around scheduling consistency:
1. **FR-004** (Cross-Branch Schedule Conflict Check): Prevent double-booking a doctor across different branches.
2. **FR-019** (Server-Side Booking Validation & Locking): Prevent concurrent booking race conditions when multiple users select the same slot.
3. **NFR-001** (Database Search Latency): Search queries for patient records and doctor schedules must return in less than 2.0 seconds under 100 concurrent users.

Additionally, the future Phase 2 requires:
1. Support for AI scheduling chatbots which will benefit from semantic search or vectorized lookups.
2. Financial billing tables designed to prevent future schema rewrites (INT-005).

## Decision

We will use **PostgreSQL** (version 16+) as the primary relational database, deployed as a managed database instance (e.g., AWS RDS or Supabase). All database access from the backend will go through an ORM (SQLAlchemy or SQLModel) for structured model definitions, but concurrent booking checks will utilize direct raw/ORM-backed database-level pessimistic locking (`SELECT ... FOR UPDATE`).

## Options Considered

### Option 1: PostgreSQL (Relational DB with Transactional Locks) — Chosen

A robust SQL database with full ACID compliance, powerful query optimization, explicit transaction isolation levels, and native support for row-level locking.

* **Pros**:
  * Native support for `SELECT ... FOR UPDATE` locks row entries during booking evaluations, completely eliminating scheduling race conditions.
  * Fully relational structure fits the normalized scheduling schema (Doctor, Patient, Branch, Shift, Appointment) perfectly.
  * Extensible with `pgvector` for Phase 2 semantic search.
  * Supported by AWS RDS, providing automated backups, replication, and multi-AZ failovers out of the box.
* **Cons**:
  * Schema migrations must be planned and executed carefully to avoid lock contention or downtime on large tables.
  * Requires active database connection pool management.
* **Estimated effort**: Low. Relational schemas are standard, and setup on AWS RDS is fully automated.

### Option 2: MongoDB (NoSQL Document DB) — Rejected

A document-based database where schedules and appointments are stored as collections of JSON-like documents.

* **Pros**:
  * Flexible schemas allow easy changes to patient profiles and consultation log structures.
  * High horizontal write throughput.
* **Cons**:
  * Lacks native database-level transactional locks across multiple separate collections (e.g., locking a doctor's availability block in one collection while booking an appointment in another) without complex, low-performance multi-document transactions.
  * High risk of concurrent booking race conditions, forcing reliance on fragile application-level mutexes or locks.
* **Estimated effort**: Medium. Implementing safe concurrency checks would require custom locking collections or distributed lock managers (like Redis Redlock), increasing system complexity.

## Rationale

PostgreSQL was chosen because the scheduling engine's integrity is the core operational requirement of this system. Ensuring that a doctor cannot be double-booked is a hard constraint (BG-004, FR-004). PostgreSQL provides native, bulletproof transaction controls at the database tier. MongoDB would require building a complex distributed lock manager at the application tier, which is an over-engineered risk for a 4-month MVP. Furthermore, PostgreSQL's maturity, indexing power, and compatibility with `pgvector` fit the system's current and future goals perfectly.

## Consequences

* **Schema Rigidity**: We must define schemas for doctors, shifts, patients, and appointments up front. Any schema changes will require SQL migrations.
* **Lock Management**: Pessimistic locks (`SELECT ... FOR UPDATE`) must be time-bound and applied only on narrow transactional blocks to avoid deadlocks or blocking standard search queries.
* **NDPR Compliance**: PostgreSQL supports robust access controls, SSL connections, and column-level access privileges, simplifying our security and regulatory compliance path.

## References

* [Clinic Modernization Platform SRD](file:///C:/Users/DELL/Documents/Project/clinic_app/software_requirements_document.md)
* [PostgreSQL Locking Documentation](https://www.postgresql.org/docs/current/explicit-locking.html)
