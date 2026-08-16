# ADR-003: Application-Level Column Encryption for Clinical Records

**Status**: Accepted
**Date**: 2026-06-04
**Deciders**: Antigravity (AI Architect), Clinic Owner, Security Officer

## Context

The Clinic Modernization Platform (CMP) processes and stores highly sensitive patient medical records. To meet strict regulatory standards and privacy guarantees:
1. **NFR-005** (NDPR Compliance): All patient data must comply with the Nigeria Data Protection Regulation.
2. **NFR-006** (Data Encryption): Patient clinical notes, histories, and diagnoses must be encrypted at rest using AES-256.
3. **NFR-008** (Separation of Clinical Data): System administrators (who manage database migrations, backups, and infrastructure) must **NOT** have access to read patient clinical records, consultation notes, or diagnostic files.

## Decision

We will implement **Application-Level Column Encryption** for all restricted medical fields (such as consultation notes, diagnoses, and prescriptions). The backend application (FastAPI) will encrypt these fields using **AES-256-GCM** before inserting them into PostgreSQL. The encryption keys will be managed and rotated via **AWS KMS (Key Management Service)**. 

Only authenticated users with clinical roles (Doctors) will have permissions that allow the application to request KMS decryption for their queries. Infrastructure and database administrators will only see encrypted ciphertext strings in the database.

## Options Considered

### Option 1: Application-Level Column Encryption (AES-256-GCM + AWS KMS) — Chosen

The application encrypts specific fields at the database boundary before saving them. Keys are managed by an external KMS with strict IAM policies.

* **Pros**:
  * Guarantees absolute compliance with **NFR-008**. Database administrators, hosting providers, or backup files contain only encrypted strings (ciphertext).
  * High security: AES-256-GCM provides both confidentiality and integrity verification (authenticated encryption), preventing data tampering.
  * Integration with AWS KMS allows auditable access logging and automated key rotation.
* **Cons**:
  * Fields that are encrypted cannot be indexed or queried using standard SQL wildcard patterns (e.g., `LIKE '%diabetes%'`).
  * Slight performance overhead due to encryption/decryption cycles on the API server.
* **Estimated effort**: Medium. Requires implementing custom SQLAlchemy/SQLModel data types that automatically handle encryption/decryption, plus KMS IAM configuration.

### Option 2: Database Transparent Data Encryption (TDE) — Rejected

Transparent Data Encryption encrypts the database files on disk (storage tier). The database engine automatically decrypts data as it is read into memory.

* **Pros**:
  * Simplest to implement; requires zero application-level changes or custom query behaviors.
  * Full text searching and SQL indexing remain fully functional.
* **Cons**:
  * Does not satisfy **NFR-008**. Because decryption is transparent to database users, any database administrator or compromised database connection can query and read patient clinical notes in plaintext.
* **Estimated effort**: Low. Turn-on checkbox on AWS RDS.

## Rationale

NDPR compliance and absolute patient privacy are critical trust foundations for the clinic chain. While Database TDE secures data against physical theft of hard drives, it fails to protect against insider threats or administrative account compromise. 

Application-level encryption ensures that the database is treated strictly as a blind storage medium for clinical records. Decryption is only possible inside the application memory space, scoped to active clinical sessions. This satisfies NFR-008 and ensures that even if the SQL database is leaked or accessed by administrators, patient health records remain entirely secure.

## Consequences

* **Search Limitations**: We cannot execute standard SQL queries scanning the text of clinical notes. Search operations must rely on metadata fields (e.g., tags, codes, or date ranges) which remain unencrypted, or we must implement a local search index on the client side (after client decryption) or use secure blind index techniques if keyword search becomes a critical clinical requirement.
* **KMS Costs and Latency**: Every encryption/decryption call introduces a network roundtrip to AWS KMS. To optimize latency, we will implement KMS envelope encryption (using a local Data Encryption Key (DEK) encrypted by a KMS Master Key and cached in application memory for short intervals).
* **Deterministic vs. Probabilistic Encryption**: We will use probabilistic encryption (AES-GCM utilizes a random Initialization Vector per write), ensuring that the same note text produces different ciphertext on every write, preventing pattern analysis.

## References

* [Clinic Modernization Platform SRD](file:///C:/Users/DELL/Documents/Project/clinic_app/software_requirements_document.md)
* [NIST Guide to Attribute-Based Encryption and Key Management](https://csrc.nist.gov/)
* [AWS KMS Envelope Encryption Concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#envelope-encryption)
