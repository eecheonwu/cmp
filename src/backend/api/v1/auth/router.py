"""
CMP Auth API Router.

Implements authentication endpoints:
- POST /api/v1/auth/register - Patient registration
- POST /api/v1/auth/verify-request - Request OTP (rate limited)
- POST /api/v1/auth/verify-code - Verify OTP and issue JWT
- POST /api/v1/auth/login - Staff login
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import RoleChecker
from db.session import get_db
from models.user import User, UserRole
from services.auth_service import AuthService
from api.v1.auth.schemas import (
    PatientRegisterRequest,
    PatientEmailRegisterRequest,
    PatientVerifyEmailRequest,
    PatientLoginRequest,
    ResendVerificationRequest,
    VerifyRequestRequest,
    VerifyCodeRequest,
    StaffLoginRequest,
    TokenResponse,
    UserResponse,
    AuthResponse,
)

logger = logging.getLogger(__name__)

# Import Celery task for OTP & Email delivery
try:
    from workers.tasks import send_otp_task, send_auth_email
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

# Create router
router = APIRouter()


# ── Helper Functions ───────────────────────────────────────────────────

def _add_deprecation_headers(response: Response) -> None:
    """Add standard deprecation headers for legacy OTP endpoints (ADR-005)."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Mon, 01 Feb 2027 00:00:00 GMT"

def create_token_response(user: User) -> TokenResponse:
    """Create token response for a user."""
    auth_service = AuthService(None)  # Not using db for this
    # Ensure role is a UserRole enum (it may come as a string from DB)
    role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
    access_token = auth_service.create_access_token(user.id, role)
    refresh_token = auth_service.create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def create_user_response(user: User) -> UserResponse:
    """Create user response for a user."""
    return UserResponse(
        id=str(user.id),
        phone_number=user.phone_number,
        email=user.email,
        role=user.role,
        is_verified=False,  # Will be updated after OTP verification
    )


async def _send_otp_notification(db: AsyncSession, otp_id: str, phone_number: str, otp_code: str) -> None:
    """
    Send OTP via notification service with proper error handling.

    Uses Celery if available, otherwise falls back to synchronous delivery.
    Logs all failures so they are visible in monitoring.
    """
    try:
        if CELERY_AVAILABLE:
            send_otp_task.delay(otp_id, otp_code)
            logger.info(
                "OTP delivery enqueued via Celery for %s (otp_id=%s)",
                phone_number,
                otp_id,
            )
        else:
            from services.notification_service import NotificationOrchestrator
            orchestrator = NotificationOrchestrator(db)
            success, error, provider = await orchestrator.send_otp(
                phone_number,
                otp_code,
            )
            if success:
                logger.info(
                    "OTP delivered via %s to %s (otp_id=%s)",
                    provider,
                    phone_number,
                    otp_id,
                )
            else:
                logger.error(
                    "OTP delivery FAILED for %s via %s: %s (otp_id=%s). "
                    "OTP is stored in DB but was not delivered.",
                    phone_number,
                    provider,
                    error,
                    otp_id,
                )
    except Exception as e:
        logger.error(
            "OTP delivery exception for %s (otp_id=%s): %s",
            phone_number,
            otp_id,
            e,
            exc_info=True,
        )


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/auth/patient/register", status_code=status.HTTP_200_OK)
async def register_patient_email(
    request: PatientEmailRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a patient with email and phone (ADR-005).

    Validates email format and uniqueness, validates phone number uniqueness,
    creates unverified patient user record, generates 60-min TTL verification token,
    and enqueues an authentication email containing password creation link.
    """
    auth_service = AuthService(db)

    try:
        user, raw_token = await auth_service.register_patient_with_email(
            email=request.email,
            phone_number=request.phone_number,
            full_name=request.full_name,
            date_of_birth=request.date_of_birth,
            gender=request.gender,
            emergency_contact=request.emergency_contact,
        )
        await db.commit()
    except ValueError as e:
        err_msg = str(e)
        if "already exists" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=err_msg,
            )
        elif "rate limit" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=err_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg,
            )

    # Enqueue auth email dispatch via Celery task if available
    try:
        if CELERY_AVAILABLE:
            send_auth_email.delay(request.email, raw_token, request.full_name)
            logger.info("Enqueued auth email task for %s", request.email)
        else:
            from services.notification.providers.email_provider import EmailClient
            client = EmailClient(db)
            verification_url = f"{settings.EMAIL_VERIFICATION_BASE_URL}?token={raw_token}"
            await client.send_email(
                to_email=request.email,
                subject="Verify Your Email - Clinic Modernization Platform",
                html_body=f"<p>Hello {request.full_name}, click link: {verification_url}</p>",
                text_body=f"Hello {request.full_name}, visit {verification_url}",
                template_name="auth_email",
            )
    except Exception as e:
        logger.error("Failed to dispatch auth email to %s: %s", request.email, e, exc_info=True)

    return {
        "message": "Verification email sent. Please check your inbox to create your password."
    }


@router.post("/auth/patient/verify-email", status_code=status.HTTP_200_OK)
async def verify_email_and_create_password(
    request: PatientVerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify email token and create patient password (ADR-005).

    Validates token, enforces password policy, sets password hash,
    marks email as verified, and issues JWT with aud: "patient".
    """
    # Validate password match
    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    auth_service = AuthService(db)

    try:
        user, access_token, refresh_token = await auth_service.verify_email_token(
            raw_token=request.token,
            password=request.password,
        )
        await db.commit()
    except ValueError as e:
        err_msg = str(e)
        if err_msg == "TOKEN_ALREADY_USED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This verification link has already been used. Please log in or request a new link.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value if isinstance(user.role, UserRole) else user.role,
            "is_email_verified": user.is_email_verified,
        },
    }


@router.post("/auth/patient/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification_email_endpoint(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Resend email verification link to patient (ADR-005).

    Invalidates existing active tokens, generates a new token,
    and enqueues verification email dispatch.
    """
    auth_service = AuthService(db)

    try:
        user, raw_token = await auth_service.resend_verification_email(request.email)
        await db.commit()
    except ValueError as e:
        err_msg = str(e)
        if err_msg == "EMAIL_ALREADY_VERIFIED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email address is already verified.",
            )
        elif "rate limit" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=err_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg,
            )

    # Dispatch email if user was found
    if user and raw_token:
        try:
            profile_name = user.email
            if CELERY_AVAILABLE:
                send_auth_email.delay(user.email, raw_token, profile_name)
                logger.info("Enqueued resend auth email task for %s", user.email)
            else:
                from services.notification.providers.email_provider import EmailClient
                client = EmailClient(db)
                verification_url = f"{settings.EMAIL_VERIFICATION_BASE_URL}?token={raw_token}"
                await client.send_email(
                    to_email=user.email,
                    subject="Verify Your Email - Clinic Modernization Platform",
                    html_body=f"<p>Hello, click link: {verification_url}</p>",
                    text_body=f"Hello, visit {verification_url}",
                    template_name="auth_email",
                )
        except Exception as e:
            logger.error("Failed to dispatch resend auth email to %s: %s", user.email, e, exc_info=True)

    return {
        "message": "Verification email sent. Please check your inbox to create your password."
    }


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(
    request: PatientRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate patient registration (DEPRECATED - Use /auth/patient/register).

    Validates that the phone number is not already registered,
    generates and sends an OTP code to the target phone number,
    and returns a signed registration token. Patient data is NOT
    persisted to the database until OTP verification completes.
    """
    _add_deprecation_headers(response)
    auth_service = AuthService(db)

    # Check if user already exists
    existing_user = await auth_service.get_user_by_phone(request.phone_number)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this phone number already exists",
        )

    # Generate OTP
    try:
        otp, otp_code = await auth_service.create_otp(request.phone_number)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )

    # Send OTP via notification service (with proper error logging)
    await _send_otp_notification(db, str(otp.id), otp.phone_number, otp_code)

    # Create signed registration token with pending details
    reg_token = auth_service.create_registration_token({
        "phone_number": request.phone_number,
        "full_name": request.full_name,
        "date_of_birth": request.date_of_birth,
        "gender": request.gender,
        "emergency_contact": request.emergency_contact,
    })

    # In development, include the OTP code in the response for testing
    if settings.is_development:
        return AuthResponse(
            message="OTP code generated and sent to target phone number. Verify OTP to complete registration.",
            registration_token=reg_token,
            otp=otp_code,  # Return actual OTP code in development for testing
        )

    return AuthResponse(
        message="OTP code generated and sent to target phone number. Verify OTP to complete registration.",
        registration_token=reg_token,
    )


@router.post("/verify-request", status_code=status.HTTP_202_ACCEPTED)
async def verify_request(
    request: VerifyRequestRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Request an OTP for phone verification (DEPRECATED - Use email verification flow).

    Rate limited: max 3 requests per phone per 15 minutes.
    In production, this would enqueue a task to send OTP via WhatsApp/SMS.
    """
    _add_deprecation_headers(response)
    auth_service = AuthService(db)

    # Check if user exists
    user = await auth_service.get_user_by_phone(request.phone_number)
    if not user:
        # Don't reveal if phone exists - return success anyway
        return {"message": "If the phone number is registered, an OTP will be sent."}

    # Check rate limit
    try:
        otp, otp_code = await auth_service.create_otp(request.phone_number)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )

    # Send OTP via notification service (with proper error logging)
    await _send_otp_notification(db, str(otp.id), otp.phone_number, otp_code)

    # In development, return the OTP for testing
    if settings.is_development:
        return {
            "message": "OTP sent successfully",
            "otp": otp_code,  # Return actual OTP code in development for testing
        }

    return {"message": "OTP sent successfully"}


@router.post("/verify-code", response_model=TokenResponse)
async def verify_code(
    request: VerifyCodeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify an OTP code and issue JWT tokens (DEPRECATED - Use email verification flow).

    Validates the OTP and creates patient record in DB if registering, returning fresh tokens.
    """
    _add_deprecation_headers(response)
    auth_service = AuthService(db)

    # 1. Verify OTP code
    success, error = await auth_service.verify_otp_code(
        request.phone_number,
        request.otp_code,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Invalid OTP code",
        )

    # 2. Get existing user or finalize patient registration upon valid OTP
    user = await auth_service.get_user_by_phone(request.phone_number)
    if not user:
        reg_payload = None
        if request.registration_token:
            try:
                reg_payload = auth_service.decode_registration_token(request.registration_token)
            except Exception:
                pass

        if not reg_payload and request.registration_data:
            reg_payload = request.registration_data

        if not reg_payload:
            reg_payload = {
                "phone_number": request.phone_number,
                "full_name": f"Patient {request.phone_number[-4:]}",
            }

        try:
            user = await auth_service.register_patient(
                phone_number=request.phone_number,
                full_name=reg_payload.get("full_name", f"Patient {request.phone_number[-4:]}"),
                date_of_birth=reg_payload.get("date_of_birth"),
                gender=reg_payload.get("gender"),
                emergency_contact=reg_payload.get("emergency_contact"),
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    # Create tokens
    tokens = create_token_response(user)

    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    request: StaffLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Staff login with email and password.

    Only staff users (receptionist, doctor, manager, admin, executive) can login.
    """
    auth_service = AuthService(db)

    # Authenticate staff
    user = await auth_service.authenticate_staff(
        email=request.email,
        password=request.password,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create tokens
    tokens = create_token_response(user)

    return tokens


# ── Protected Endpoint Example ───────────────────────────────────────

@router.post("/auth/patient/login", response_model=TokenResponse)
async def patient_login(
    request: PatientLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Patient login with email and password (ADR-005).

    Validates email + password for patient role users.
    Requires is_email_verified=True (returns 403 if unverified).
    Returns JWT with aud: "patient".
    """
    auth_service = AuthService(db)

    user, error_reason = await auth_service.authenticate_patient(
        email=request.email,
        password=request.password,
    )

    if error_reason == "EMAIL_NOT_VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address not verified. Please verify your email before logging in.",
        )

    if error_reason == "INVALID_CREDENTIALS" or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create tokens (create_access_token already adds aud: "patient" for patient role)
    tokens = create_token_response(user)

    return tokens

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(RoleChecker([UserRole.PATIENT, UserRole.DOCTOR, UserRole.RECEPTIONIST, UserRole.MANAGER, UserRole.ADMIN, UserRole.EXECUTIVE])),
):
    """
    Get current authenticated user's information.

    Requires any valid role.
    """
    return create_user_response(current_user)
