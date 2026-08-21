"""
CMP User, PatientProfile & VerificationOTP models.

Implements:
- user_role enum: patient, receptionist, doctor, manager, admin, executive
- users table with phone/email unique, password_hash, role
- patient_profiles table with FK to users
- verification_otps table for OTP-based phone verification
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

import enum


class UserRole(str, enum.Enum):
    """RBAC roles for CMP users."""

    PATIENT = "patient"
    RECEPTIONIST = "receptionist"
    DOCTOR = "doctor"
    MANAGER = "manager"
    ADMIN = "admin"
    EXECUTIVE = "executive"


class User(BaseModel):
    """
    Core user entity for authentication and authorization.

    Stores credentials, role assignment, and contact information.
    Passwords are stored as bcrypt hashes; raw passwords are never persisted.
    """

    __tablename__ = "users"

    phone_number: Mapped[str] = mapped_column(
        String(15),
        unique=True,
        nullable=False,
        comment="Primary contact phone number (unique)",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        comment="Email address (unique, optional for patients)",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt hash of the user's password",
    )
    role: Mapped[UserRole] = mapped_column(
        String(50),
        nullable=False,
        comment="RBAC role assignment",
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=func.text("false"),
        nullable=False,
        comment="Whether patient email address is verified",
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when email was verified",
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('patient', 'receptionist', 'doctor', 'manager', 'admin', 'executive')",
            name="ck_users_role_valid",
        ),
    )

    # Relationships
    patient_profile: Mapped["PatientProfile | None"] = relationship(
        "PatientProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, phone={self.phone_number}, role={self.role.value})>"


class PatientProfile(BaseModel):
    """
    Patient demographic and contact details.

    Linked one-to-one with a User who has role=patient.
    """

    __tablename__ = "patient_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="FK → users.id (one-to-one with patient user)",
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Patient's full legal name",
    )
    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Patient date of birth",
    )
    gender: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Patient gender identity",
    )
    emergency_contact: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Emergency contact name and phone number",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="patient_profile")

    def __repr__(self) -> str:
        return f"<PatientProfile(id={self.id}, user_id={self.user_id}, name={self.full_name})>"


class VerificationOTP(BaseModel):
    """
    One-time password for phone number verification.

    Supports OTP delivery via WhatsApp or SMS with rate limiting,
    expiry, and single-use semantics.
    """

    __tablename__ = "verification_otps"

    phone_number: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        index=True,
        comment="Target phone number for OTP delivery",
    )
    hashed_otp: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt hash of the 6-digit OTP code",
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Incorrect attempt count (max 5)",
    )
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this OTP has already been consumed",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="OTP expiry timestamp (10-minute TTL from creation)",
    )
    delivery_channel: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Delivery channel used: 'whatsapp' or 'sms'",
    )

    def __repr__(self) -> str:
        return (
            f"<VerificationOTP(id={self.id}, phone={self.phone_number}, "
            f"used={self.is_used}, expires_at={self.expires_at})>"
        )


class EmailVerificationToken(BaseModel):
    """
    Email verification token for patient registration & password creation.

    Stores bcrypt hash of single-use URL verification token with 60-min TTL.
    """

    __tablename__ = "email_verification_tokens"

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Target patient email address",
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt hash of the raw verification token",
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Incorrect verification attempt count (max 5)",
    )
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether token has been consumed for password creation",
    )
    is_expired: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether token has been manually expired/superseded",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Token expiry timestamp (60-minute TTL from creation)",
    )

    def __repr__(self) -> str:
        return (
            f"<EmailVerificationToken(id={self.id}, email={self.email}, "
            f"used={self.is_used}, expired={self.is_expired}, expires_at={self.expires_at})>"
        )

