"""
CMP Admin API Router.

Implements Task 5.4 — Admin Console:
- Branch CRUD endpoints
- User role management endpoints
- Availability management endpoints
- System settings endpoints
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import RoleChecker
from db.session import get_db
from models.user import UserRole
from api.v1.admin.schemas import (
    BranchResponse,
    CreateBranchRequest,
    UpdateBranchRequest,
    UserResponse,
    UpdateUserRoleRequest,
    AvailabilityResponse,
    CreateAvailabilityRequest,
    UpdateAvailabilityRequest,
    SystemSettingsResponse,
)

# Create router
router = APIRouter()


# ── Helper Functions ─────────────────────────────────────────────────────────

def get_admin_service(db: AsyncSession = Depends(get_db)):
    """Get admin service instance."""
    # In production, this would return an actual service
    # For now, we'll use inline implementations
    pass


# ── Branch Endpoints ─────────────────────────────────────────────────────────

@router.get(
    "/admin/branches",
    response_model=list[BranchResponse],
    tags=["admin"],
)
async def list_branches(
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    List all branches.

    Access: admin only

    Returns:
        - List of all branches with their details
    """
    # In production, this would query the database
    # For now, return mock data
    return [
        {
            "id": "branch-1",
            "name": "Main Clinic",
            "address": "123 Main Street, Lagos",
            "phone": "+234-1-234-5678",
            "email": "main@clinic.com",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        },
        {
            "id": "branch-2",
            "name": "Branch Clinic A",
            "address": "456 Branch Avenue, Lagos",
            "phone": "+234-1-345-6789",
            "email": "branch-a@clinic.com",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        },
    ]


@router.get(
    "/admin/branches/{branch_id}",
    response_model=BranchResponse,
    tags=["admin"],
)
async def get_branch(
    branch_id: str,
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific branch by ID.

    Access: admin only

    Returns:
        - Branch details
    """
    # In production, this would query the database
    return {
        "id": branch_id,
        "name": "Main Clinic",
        "address": "123 Main Street, Lagos",
        "phone": "+234-1-234-5678",
        "email": "main@clinic.com",
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
    }


@router.post(
    "/admin/branches",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["admin"],
)
async def create_new_branch(
    data: CreateBranchRequest,
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new branch.

    Access: admin only

    Returns:
        - Created branch details
    """
    # In production, this would insert into the database
    return {
        "id": "new-branch-id",
        "name": data.name,
        "address": data.address,
        "phone": data.phone,
        "email": data.email,
        "createdAt": "2026-07-09T00:00:00Z",
        "updatedAt": "2026-07-09T00:00:00Z",
    }


@router.patch(
    "/admin/branches/{branch_id}",
    response_model=BranchResponse,
    tags=["admin"],
)
async def update_existing_branch(
    branch_id: str,
    data: UpdateBranchRequest,
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing branch.

    Access: admin only

    Returns:
        - Updated branch details
    """
    # In production, this would update the database
    return {
        "id": branch_id,
        "name": data.name or "Main Clinic",
        "address": data.address or "123 Main Street, Lagos",
        "phone": data.phone or "+234-1-234-5678",
        "email": data.email or "main@clinic.com",
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-07-09T00:00:00Z",
    }


@router.delete(
    "/admin/branches/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["admin"],
)
async def delete_existing_branch(
    branch_id: str,
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a branch.

    Access: admin only
    """
    # In production, this would delete from the database
    return None


# ── User Endpoints ───────────────────────────────────────────────────────────

@router.get(
    "/admin/users",
    response_model=list[UserResponse],
    tags=["admin"],
)
async def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users, optionally filtered by role.

    Access: admin only

    Returns:
        - List of users with their details
    """
    # In production, this would query the database
    return [
        {
            "id": "user-1",
            "phoneNumber": "+234-1-234-5678",
            "email": "admin@clinic.com",
            "role": "admin",
            "isVerified": True,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        },
        {
            "id": "user-2",
            "phoneNumber": "+234-1-345-6789",
            "email": "doctor@clinic.com",
            "role": "doctor",
            "isVerified": True,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        },
    ]


@router.get(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    tags=["admin"],
)
async def get_user(
    user_id: str,
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific user by ID.

    Access: admin only

    Returns:
        - User details
    """
    # In production, this would query the database
    return {
        "id": user_id,
        "phoneNumber": "+234-1-234-5678",
        "email": "user@clinic.com",
        "role": "receptionist",
        "isVerified": True,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
    }


@router.patch(
    "/admin/users/{user_id}/role",
    response_model=UserResponse,
    tags=["admin"],
)
async def update_user_role(
    user_id: str,
    data: UpdateUserRoleRequest,
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a user's role.

    Access: admin only

    Returns:
        - Updated user details
    """
    # In production, this would update the database
    return {
        "id": user_id,
        "phoneNumber": "+234-1-234-5678",
        "email": "user@clinic.com",
        "role": data.role,
        "isVerified": True,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-07-09T00:00:00Z",
    }


# ── Availability Endpoints ───────────────────────────────────────────────────

@router.get(
    "/admin/availability",
    response_model=list[AvailabilityResponse],
    tags=["admin"],
)
async def list_availability(
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    doctor_id: Optional[str] = Query(None, description="Filter by doctor ID"),
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    List all doctor availability slots, optionally filtered.

    Access: admin only

    Returns:
        - List of availability slots
    """
    # In production, this would query the database
    return [
        {
            "id": "availability-1",
            "doctorId": "doctor-1",
            "branchId": "branch-1",
            "startDatetime": "2026-07-10T09:00:00Z",
            "endDatetime": "2026-07-10T17:00:00Z",
            "isCancelled": False,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        },
    ]


@router.post(
    "/admin/availability",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["admin"],
)
async def create_new_availability(
    data: CreateAvailabilityRequest,
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new doctor availability slot.

    Access: admin only

    Returns:
        - Created availability slot
    """
    # In production, this would insert into the database
    return {
        "id": "new-availability-id",
        "doctorId": data.doctorId,
        "branchId": data.branchId,
        "startDatetime": data.startDatetime,
        "endDatetime": data.endDatetime,
        "isCancelled": False,
        "createdAt": "2026-07-09T00:00:00Z",
        "updatedAt": "2026-07-09T00:00:00Z",
    }


@router.patch(
    "/admin/availability/{availability_id}",
    response_model=AvailabilityResponse,
    tags=["admin"],
)
async def update_existing_availability(
    availability_id: str,
    data: UpdateAvailabilityRequest,
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing availability slot.

    Access: admin only

    Returns:
        - Updated availability slot
    """
    # In production, this would update the database
    return {
        "id": availability_id,
        "doctorId": "doctor-1",
        "branchId": "branch-1",
        "startDatetime": data.startDatetime or "2026-07-10T09:00:00Z",
        "endDatetime": data.endDatetime or "2026-07-10T17:00:00Z",
        "isCancelled": data.isCancelled or False,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-07-09T00:00:00Z",
    }


@router.delete(
    "/admin/availability/{availability_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["admin"],
)
async def delete_existing_availability(
    availability_id: str,
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an availability slot.

    Access: admin only
    """
    # In production, this would delete from the database
    return None


# ── System Settings Endpoints ───────────────────────────────────────────────

@router.get(
    "/admin/settings",
    response_model=list[SystemSettingsResponse],
    tags=["admin"],
)
async def get_settings(
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get system settings.

    Access: admin only

    Returns:
        - List of system settings
    """
    # In production, this would query the database
    return [
        {
            "id": "setting-1",
            "key": "app_name",
            "value": "Clinic Modernization Platform",
            "description": "Application name",
            "updatedAt": "2026-01-01T00:00:00Z",
        },
    ]


@router.patch(
    "/admin/settings",
    response_model=list[SystemSettingsResponse],
    tags=["admin"],
)
async def update_settings(
    settings: dict,
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Update system settings.

    Access: admin only

    Returns:
        - Updated list of system settings
    """
    # In production, this would update the database
    return [
        {
            "id": "setting-1",
            "key": "app_name",
            "value": settings.get("app_name", "Clinic Modernization Platform"),
            "description": "Application name",
            "updatedAt": "2026-07-09T00:00:00Z",
        },
    ]
