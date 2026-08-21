"""Create users, patient_profiles, verification_otps tables + enums

Implements Task 1.2 — Auth & RBAC user schema:

- user_role enum: patient, receptionist, doctor, manager, admin, executive
- users table with phone/email unique, password_hash, role
- patient_profiles table (one-to-one with users)
- verification_otps table for OTP-based phone verification
- Indexes on phone_number, email

Revision ID: 0002_auth_schema
Revises: 0001_initial_empty
Create Date: 2026-07-07 22:30:00.000000+01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0002_auth_schema"
down_revision: Union[str, None] = "0001_initial_empty"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_role enum, users, patient_profiles, verification_otps."""
    # ── Enum: user_role ──────────────────────────────────────────────
    # Create enum type if it doesn't exist (using raw SQL for reliability)
    # Use a try-catch block to handle the case where type already exists
    op.execute("""
        CREATE TYPE user_role AS ENUM ('patient', 'receptionist', 'doctor', 'manager', 'admin', 'executive');
    """)
    
    # Use a text column with check constraint instead of enum type
    # This avoids the issue with enum type creation during table creation
    user_role_enum = sa.String(50)
    
    # Add check constraint for user_role values
    user_role_check = sa.CheckConstraint(
        "role IN ('patient', 'receptionist', 'doctor', 'manager', 'admin', 'executive')",
        name="ck_users_role_valid",
    )

    # ── Table: users ─────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key (UUID v4)",
        ),
        sa.Column(
            "phone_number",
            sa.String(15),
            unique=True,
            nullable=False,
            comment="Primary contact phone number (unique)",
        ),
        sa.Column(
            "email",
            sa.String(255),
            unique=True,
            nullable=True,
            comment="Email address (unique, optional for patients)",
        ),
        sa.Column(
            "password_hash",
            sa.String(255),
            nullable=False,
            comment="bcrypt hash of the user's password",
        ),
        sa.Column(
            "role",
            user_role_enum,
            nullable=False,
            comment="RBAC role assignment",
        ),
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
        user_role_check,
    )

    # Indexes on users
    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True, postgresql_where=sa.text("email IS NOT NULL"))

    # ── Table: patient_profiles ──────────────────────────────────────
    op.create_table(
        "patient_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key (UUID v4)",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
            comment="FK → users.id (one-to-one with patient user)",
        ),
        sa.Column(
            "full_name",
            sa.String(255),
            nullable=False,
            comment="Patient's full legal name",
        ),
        sa.Column(
            "date_of_birth",
            sa.Date(),
            nullable=True,
            comment="Patient date of birth",
        ),
        sa.Column(
            "gender",
            sa.String(10),
            nullable=True,
            comment="Patient gender identity",
        ),
        sa.Column(
            "emergency_contact",
            sa.String(255),
            nullable=True,
            comment="Emergency contact name and phone number",
        ),
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

    # ── Table: verification_otps ─────────────────────────────────────
    op.create_table(
        "verification_otps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key (UUID v4)",
        ),
        sa.Column(
            "phone_number",
            sa.String(15),
            nullable=False,
            comment="Target phone number for OTP delivery",
        ),
        sa.Column(
            "hashed_otp",
            sa.String(255),
            nullable=False,
            comment="bcrypt hash of the 6-digit OTP code",
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="Incorrect attempt count (max 5)",
        ),
        sa.Column(
            "is_used",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="Whether this OTP has already been consumed",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="OTP expiry timestamp (10-minute TTL from creation)",
        ),
        sa.Column(
            "delivery_channel",
            sa.String(20),
            nullable=True,
            comment="Delivery channel used: 'whatsapp' or 'sms'",
        ),
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

    # Index on verification_otps.phone_number for rate-limit queries
    op.create_index(
        "ix_verification_otps_phone_number",
        "verification_otps",
        ["phone_number"],
    )


def downgrade() -> None:
    """Drop tables and the user_role enum (in reverse order)."""
    # Drop tables (respect FK dependencies: patient_profiles → users)
    op.drop_table("verification_otps")
    op.drop_table("patient_profiles")
    op.drop_table("users")

    # Drop the user_role enum
    op.execute("DROP TYPE IF EXISTS user_role CASCADE")