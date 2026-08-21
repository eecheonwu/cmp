"""
CMP Migration 0005 — Clinical Records Table.

Creates the clinical_records table for encrypted medical data storage.
Implements ADR-003: Application-Level AES-256-GCM Column Encryption + AWS KMS
envelope encryption.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_clinical_records"
down_revision: Union[str, None] = "0004_scheduling_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create clinical_records table with encrypted medical fields.

    All medical fields (encrypted_notes, encrypted_diagnosis,
    encrypted_prescriptions) are stored as TEXT ciphertext.
    Decryption occurs only in application memory for doctor role users.
    """
    op.create_table(
        "clinical_records",

        # Primary Key (inherited from BaseModel)
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key (UUID v4)",
        ),

        # Foreign Keys
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="RESTRICT"),
            unique=True,
            nullable=False,
            comment="FK → appointments.id (one-to-one with appointment)",
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            comment="FK → users.id (patient)",
        ),
        sa.Column(
            "doctor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            comment="FK → users.id (doctor who created the record)",
        ),

# Encrypted Clinical Fields (AES-256-GCM ciphertext + IV + tag as JSON)
        sa.Column(
            "encrypted_notes",
            sa.Text(),
            nullable=False,
            comment="AES-256-GCM encrypted clinical notes (ciphertext + IV + tag as JSON)",
        ),
        sa.Column(
            "encrypted_diagnosis",
            sa.Text(),
            nullable=False,
            comment="AES-256-GCM encrypted diagnosis (ciphertext + IV + tag as JSON)",
        ),
        sa.Column(
            "encrypted_prescriptions",
            sa.Text(),
            nullable=False,
            comment="AES-256-GCM encrypted prescriptions (ciphertext + IV + tag as JSON)",
        ),

        # KMS Envelope Encryption Key
        sa.Column(
            "kms_key_version",
            sa.String(500),
            nullable=False,
            comment="Encrypted KMS data key (Base64) used for envelope encryption",
        ),

        # Timestamps (inherited from BaseModel)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="Record creation timestamp (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
            comment="Record last update timestamp (UTC)",
        ),
    )

    # Create index on patient_id for efficient patient record lookups
    op.create_index(
        "ix_clinical_records_patient_id",
        "clinical_records",
        ["patient_id"],
    )

    # Create index on appointment_id for efficient joins
    op.create_index(
        "ix_clinical_records_appointment_id",
        "clinical_records",
        ["appointment_id"],
    )


def downgrade() -> None:
    """Drop clinical_records table."""
    op.drop_index("ix_clinical_records_appointment_id", table_name="clinical_records")
    op.drop_index("ix_clinical_records_patient_id", table_name="clinical_records")
    op.drop_table("clinical_records")