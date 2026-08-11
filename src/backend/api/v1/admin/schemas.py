"""
CMP Admin Pydantic Schemas.

Implements Task 5.4 — Admin Console:
- Branch request/response models
- User request/response models
- Availability request/response models
- System settings models
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Branch Schemas ───────────────────────────────────────────────────────────

class BranchResponse(BaseModel):
    """Response schema for branch data."""

    id: str = Field(..., description="Branch identifier")
    name: str = Field(..., description="Branch name")
    address: str = Field(..., description="Branch address")
    phone: str = Field(..., description="Branch phone number")
    email: str = Field(..., description="Branch email address")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class CreateBranchRequest(BaseModel):
    """Request schema for creating a branch."""

    name: str = Field(..., description="Branch name")
    address: str = Field(..., description="Branch address")
    phone: str = Field(..., description="Branch phone number")
    email: str = Field(..., description="Branch email address")


class UpdateBranchRequest(BaseModel):
    """Request schema for updating a branch."""

    name: Optional[str] = Field(None, description="Branch name")
    address: Optional[str] = Field(None, description="Branch address")
    phone: Optional[str] = Field(None, description="Branch phone number")
    email: Optional[str] = Field(None, description="Branch email address")


# ── User Schemas ───────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Response schema for user data."""

    id: str = Field(..., description="User identifier")
    phoneNumber: str = Field(..., description="User phone number")
    email: Optional[str] = Field(None, description="User email address")
    role: str = Field(..., description="User role")
    isVerified: bool = Field(..., description="Whether user is verified")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class UpdateUserRoleRequest(BaseModel):
    """Request schema for updating user role."""

    role: str = Field(..., description="New role for the user")


# ── Availability Schemas ─────────────────────────────────────────────────────

class AvailabilityResponse(BaseModel):
    """Response schema for doctor availability data."""

    id: str = Field(..., description="Availability slot identifier")
    doctorId: str = Field(..., description="Doctor user ID")
    branchId: str = Field(..., description="Branch identifier")
    startDatetime: datetime = Field(..., description="Shift start time (UTC)")
    endDatetime: datetime = Field(..., description="Shift end time (UTC)")
    isCancelled: bool = Field(..., description="Whether this shift is cancelled")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class CreateAvailabilityRequest(BaseModel):
    """Request schema for creating availability slot."""

    doctorId: str = Field(..., description="Doctor user ID")
    branchId: str = Field(..., description="Branch identifier")
    startDatetime: datetime = Field(..., description="Shift start time (UTC)")
    endDatetime: datetime = Field(..., description="Shift end time (UTC)")


class UpdateAvailabilityRequest(BaseModel):
    """Request schema for updating availability slot."""

    startDatetime: Optional[datetime] = Field(None, description="Shift start time (UTC)")
    endDatetime: Optional[datetime] = Field(None, description="Shift end time (UTC)")
    isCancelled: Optional[bool] = Field(None, description="Whether this shift is cancelled")


# ── System Settings Schemas ─────────────────────────────────────────────────

class SystemSettingsResponse(BaseModel):
    """Response schema for system settings."""

    id: str = Field(..., description="Settings record identifier")
    key: str = Field(..., description="Settings key")
    value: str = Field(..., description="Settings value")
    description: str = Field(..., description="Settings description")
    updatedAt: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
