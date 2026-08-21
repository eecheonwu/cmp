"""
CMP Security Utilities.

Provides security dependencies and utilities for authentication and authorization.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import get_db
from models.user import User, UserRole
from services.auth_service import AuthService, hash_password, verify_password

# OAuth2 scheme for JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def RoleChecker(required_roles: list[UserRole], required_audience: Optional[str] = None):
    """
    Dependency factory for role-based access control with audience enforcement.

    Usage:
        # Staff-only endpoint (validates aud: "staff")
        @router.get("/admin/reports")
        async def reports(user = Depends(RoleChecker([UserRole.ADMIN], required_audience="staff"))):
            ...

        # Patient-only endpoint (validates aud: "patient")
        @router.get("/patient/appointments")
        async def my_appts(user = Depends(RoleChecker([UserRole.PATIENT], required_audience="patient"))):
            ...

        # Any-audience endpoint (no audience restriction)
        @router.get("/me")
        async def me(user = Depends(RoleChecker([UserRole.PATIENT, UserRole.DOCTOR]))):
            ...

    Args:
        required_roles: List of UserRole values that are allowed to access the endpoint.
        required_audience: Optional audience claim to validate ('patient' or 'staff').
            If provided, the JWT 'aud' claim must match exactly, otherwise 403 is returned.

    Returns:
        A dependency that validates the JWT token, checks the user's role, and
        optionally enforces audience-based access control per ADR-005.
    """

    async def role_checker(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        # Verify token
        try:
            payload = AuthService(db).decode_token(token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Check token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        # Enforce audience claim if required (ADR-005)
        if required_audience is not None:
            token_audience = payload.get("aud")
            if token_audience != required_audience:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. This endpoint requires '{required_audience}' audience.",
                )

        # Get user
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # Check role
        user_role = payload.get("role")
        if user_role not in [r.value for r in required_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return user

    return role_checker

