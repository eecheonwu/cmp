"""
CMP Auth Pydantic Schemas.

Request and response models for authentication endpoints.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from models.user import UserRole


def _clean_phone(v: str) -> str:
    if isinstance(v, str):
        return re.sub(r"[\s\-\(\)]", "", v.strip())
    return v


class PatientRegisterRequest(BaseModel):
    """Request schema for patient registration."""

    phone_number: str = Field(..., min_length=10, max_length=15, description="Phone number")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full legal name")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD format)")
    gender: Optional[str] = Field(None, max_length=10, description="Gender identity")
    emergency_contact: Optional[str] = Field(None, max_length=255, description="Emergency contact")

    @field_validator("phone_number", mode="before")
    @classmethod
    def sanitize_phone(cls, v: str) -> str:
        return _clean_phone(v)


class PatientEmailRegisterRequest(BaseModel):
    """Request schema for email-based patient registration (ADR-005)."""

    email: EmailStr = Field(..., description="Patient email address")
    phone_number: str = Field(..., min_length=10, max_length=15, description="Primary contact phone number")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full legal name")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD format)")
    gender: Optional[str] = Field(None, max_length=10, description="Gender identity")
    emergency_contact: Optional[str] = Field(None, max_length=255, description="Emergency contact")

    @field_validator("phone_number", mode="before")
    @classmethod
    def sanitize_phone(cls, v: str) -> str:
        return _clean_phone(v)


class PatientVerifyEmailRequest(BaseModel):
    """Request schema for email verification + password creation (ADR-005)."""

    token: str = Field(..., min_length=1, description="Raw email verification token from URL")
    password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Password confirmation")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce ADR-005 password complexity: min 8, upper, lower, digit, special."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', v):
            raise ValueError("Password must contain at least one special character.")
        return v


class ResendVerificationRequest(BaseModel):
    """Request schema for resending patient email verification link (ADR-005)."""

    email: EmailStr = Field(..., description="Patient email address")


class VerifyRequestRequest(BaseModel):
    """Request schema for OTP verification request."""

    phone_number: str = Field(..., min_length=10, max_length=15, description="Phone number to verify")

    @field_validator("phone_number", mode="before")
    @classmethod
    def sanitize_phone(cls, v: str) -> str:
        return _clean_phone(v)


class VerifyCodeRequest(BaseModel):
    """Request schema for OTP code verification."""

    phone_number: str = Field(..., min_length=10, max_length=15, description="Phone number")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    registration_token: Optional[str] = Field(None, description="Optional pending registration token")
    registration_data: Optional[dict] = Field(None, description="Optional pending registration payload")

    @field_validator("phone_number", mode="before")
    @classmethod
    def sanitize_phone(cls, v: str) -> str:
        return _clean_phone(v)


class StaffLoginRequest(BaseModel):
    """Request schema for staff login."""

    email: EmailStr = Field(..., description="Staff email address")
    password: str = Field(..., min_length=1, description="Password")


class PatientLoginRequest(BaseModel):
    """Request schema for patient login with email and password (ADR-005)."""

    email: EmailStr = Field(..., description="Patient email address")
    password: str = Field(..., min_length=1, description="Password")


class TokenResponse(BaseModel):
    """Response schema for JWT tokens."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: str = Field(..., description="User UUID")
    phone_number: str = Field(..., description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    role: UserRole = Field(..., description="User role")
    is_verified: bool = Field(..., description="Phone verification status")

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Response schema for authentication operations."""

    user: Optional[UserResponse] = Field(None, description="User data")
    tokens: Optional[TokenResponse] = Field(None, description="JWT tokens")
    registration_token: Optional[str] = Field(None, description="Pending registration JWT token")
    message: Optional[str] = Field(None, description="Status or guidance message")
    otp: Optional[str] = Field(None, description="OTP code (only in development mode for testing)")


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for client handling")