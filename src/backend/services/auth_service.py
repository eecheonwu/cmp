"""
CMP Authentication Service.

Implements:
- JWT token generation and validation
- OTP generation, verification, and rate limiting
- Patient registration with phone verification
- Staff login with email/password authentication
- Role-based access control
"""

import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.user import User, UserRole, PatientProfile, VerificationOTP, EmailVerificationToken


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def hash_otp(otp: str) -> str:
    """Hash an OTP code for storage."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(otp.encode('utf-8'), salt).decode('utf-8')


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """Verify an OTP code against its hash."""
    return bcrypt.checkpw(plain_otp.encode('utf-8'), hashed_otp.encode('utf-8'))


class AuthService:
    """
    Authentication service for CMP.

    Handles user registration, OTP verification, login, and JWT management.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Password Operations ───────────────────────────────────────────────

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return hash_password(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return verify_password(plain_password, hashed_password)

    # ── JWT Operations ────────────────────────────────────────────────────

    def create_access_token(self, user_id: str, role: UserRole) -> str:
        """Create a JWT access token for a user."""
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        # Determine audience claim per ADR-005
        audience = "patient" if role == UserRole.PATIENT else "staff"
        payload = {
            "sub": str(user_id),
            "role": role.value,
            "aud": audience,
            "type": "access",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    def create_refresh_token(self, user_id: str) -> str:
        """Create a JWT refresh token for a user."""
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    def decode_token(self, token: str) -> dict:
        """Decode and validate a JWT token."""
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )

    def create_registration_token(self, registration_data: dict) -> str:
        """Create a temporary JWT token holding pending registration data."""
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        payload = {
            **registration_data,
            "type": "registration_pending",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    def decode_registration_token(self, token: str) -> dict:
        """Decode and validate a registration token."""
        payload = self.decode_token(token)
        if payload.get("type") != "registration_pending":
            raise ValueError("Invalid registration token type")
        return payload

    # ── OTP Operations ────────────────────────────────────────────────────

    @staticmethod
    def generate_otp() -> str:
        """Generate a 6-digit OTP code."""
        return str(secrets.randbelow(1000000)).zfill(6)

    @staticmethod
    def hash_otp(otp: str) -> str:
        """Hash an OTP code for storage."""
        return hash_otp(otp)

    @staticmethod
    def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
        """Verify an OTP code against its hash."""
        return verify_otp(plain_otp, hashed_otp)

    async def check_rate_limit(self, phone_number: str) -> int:
        """
        Check OTP request rate limit for a phone number.

        Returns the count of requests in the last 15 minutes.
        Returns 0 if the database query fails (e.g., table not yet created).
        """
        window_start = datetime.now(timezone.utc) - timedelta(
            seconds=settings.OTP_RATE_LIMIT_WINDOW_SECONDS
        )
        try:
            result = await self.db.execute(
                select(func.count(VerificationOTP.id))
                .where(VerificationOTP.phone_number == phone_number)
                .where(VerificationOTP.created_at >= window_start)
            )
            return result.scalar_one()
        except Exception:
            # If the query fails (e.g., table doesn't exist yet),
            # return 0 to allow registration to proceed
            return 0

    async def get_active_otp(self, phone_number: str) -> Optional[VerificationOTP]:
        """Get the active (unused, not expired) OTP for a phone number."""
        result = await self.db.execute(
            select(VerificationOTP)
            .where(VerificationOTP.phone_number == phone_number)
            .where(VerificationOTP.is_used == False)
            .where(VerificationOTP.expires_at > datetime.now(timezone.utc))
            .order_by(VerificationOTP.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def create_otp(
        self,
        phone_number: str,
        delivery_channel: str = "whatsapp",
    ) -> tuple[VerificationOTP, str]:
        """
        Create a new OTP for a phone number.

        Rate limits: max 3 requests per phone per 15 minutes.
        
        Returns:
            tuple: (VerificationOTP record, plain_text_otp_code)
        """
        # Check rate limit
        request_count = await self.check_rate_limit(phone_number)
        if request_count >= settings.OTP_RATE_LIMIT_REQUESTS:
            raise ValueError("Rate limit exceeded. Please try again later.")

        # Generate and hash OTP
        otp_code = self.generate_otp()
        hashed_otp = self.hash_otp(otp_code)

        # Create OTP record
        otp = VerificationOTP(
            phone_number=phone_number,
            hashed_otp=hashed_otp,
            expires_at=datetime.now(timezone.utc) + timedelta(
                seconds=settings.OTP_TTL_SECONDS
            ),
            delivery_channel=delivery_channel,
        )
        self.db.add(otp)
        await self.db.flush()

        return otp, otp_code

    async def verify_otp_code(
        self,
        phone_number: str,
        otp_code: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Verify an OTP code for a phone number.

        Returns:
            tuple: (success, error_message)
        """
        # Get active OTP
        otp = await self.get_active_otp(phone_number)
        if not otp:
            return False, "No active OTP found. Please request a new code."

        # Check attempts
        if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            return False, "Maximum attempts exceeded. Please request a new code."

        # Verify OTP
        if not self.verify_otp(otp_code, otp.hashed_otp):
            otp.attempts += 1
            await self.db.flush()
            return False, "Invalid OTP code."

        # Mark OTP as used
        otp.is_used = True
        await self.db.flush()

        return True, None

    # ── User Operations ───────────────────────────────────────────────────

    async def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """Get a user by phone number."""
        result = await self.db.execute(
            select(User).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def register_patient(
        self,
        phone_number: str,
        full_name: str,
        date_of_birth: Optional[date | str] = None,
        gender: Optional[str] = None,
        emergency_contact: Optional[str] = None,
    ) -> User:
        """
        Register a new patient user.

        Creates a user with role=patient and associated patient profile.
        """
        # Check if user already exists
        existing_user = await self.get_user_by_phone(phone_number)
        if existing_user:
            raise ValueError("User with this phone number already exists.")

        # Generate a random password for patient (they'll verify via OTP)
        temp_password = secrets.token_urlsafe(16)
        password_hash = self.hash_password(temp_password)

        # Create user
        user = User(
            phone_number=phone_number,
            password_hash=password_hash,
            role=UserRole.PATIENT,
        )
        self.db.add(user)
        await self.db.flush()

        # Convert date_of_birth to date if provided
        parsed_date_of_birth = None
        if date_of_birth:
            if isinstance(date_of_birth, str):
                try:
                    parsed_date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
                except ValueError:
                    # If parsing fails, pass None
                    pass
            elif isinstance(date_of_birth, datetime):
                parsed_date_of_birth = date_of_birth.date()
            elif isinstance(date_of_birth, date):
                parsed_date_of_birth = date_of_birth

        # Create patient profile
        profile = PatientProfile(
            user_id=user.id,
            full_name=full_name,
            date_of_birth=parsed_date_of_birth,
            gender=gender,
            emergency_contact=emergency_contact,
        )
        self.db.add(profile)
        await self.db.flush()

        return user

    # ── Email Verification Operations ───────────────────────────────────

    async def check_email_rate_limit(self, email: str) -> int:
        """
        Check email verification request rate limit for an email address.
        Max 3 requests per email per 15 minutes (900 seconds).
        """
        window_start = datetime.now(timezone.utc) - timedelta(minutes=15)
        try:
            result = await self.db.execute(
                select(func.count(EmailVerificationToken.id))
                .where(EmailVerificationToken.email == email)
                .where(EmailVerificationToken.created_at >= window_start)
            )
            return result.scalar_one()
        except Exception:
            return 0

    async def create_email_verification_token(self, email: str) -> tuple[EmailVerificationToken, str]:
        """
        Create a new single-use 60-min email verification token for a patient.
        Rate limited to max 3 per 15 minutes per email address.
        Invalidates any prior active tokens for this email.
        """
        count = await self.check_email_rate_limit(email)
        if count >= 3:
            raise ValueError("Rate limit exceeded. Maximum 3 email verification requests per 15 minutes allowed.")

        # Invalidate prior active tokens
        prior_tokens = await self.db.execute(
            select(EmailVerificationToken)
            .where(EmailVerificationToken.email == email)
            .where(EmailVerificationToken.is_used == False)
            .where(EmailVerificationToken.is_expired == False)
        )
        for token_record in prior_tokens.scalars():
            token_record.is_expired = True

        raw_token = secrets.token_urlsafe(32)
        token_hash = self.hash_password(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=60)

        token_record = EmailVerificationToken(
            email=email,
            token_hash=token_hash,
            expires_at=expires_at,
            is_used=False,
            is_expired=False,
            attempts=0,
        )
        self.db.add(token_record)
        await self.db.flush()

        return token_record, raw_token

    async def register_patient_with_email(
        self,
        email: str,
        phone_number: str,
        full_name: str,
        date_of_birth: Optional[date | str] = None,
        gender: Optional[str] = None,
        emergency_contact: Optional[str] = None,
    ) -> tuple[User, str]:
        """
        Register a patient using email + phone (ADR-005).
        Creates user with is_email_verified=False and enqueues auth email token.
        """
        # Check email uniqueness
        existing_email = await self.get_user_by_email(email)
        if existing_email:
            raise ValueError("User with this email already exists.")

        # Check phone uniqueness
        existing_phone = await self.get_user_by_phone(phone_number)
        if existing_phone:
            raise ValueError("User with this phone number already exists.")

        # Create user with temp password and unverified email
        temp_password = secrets.token_urlsafe(16)
        password_hash = self.hash_password(temp_password)

        user = User(
            email=email,
            phone_number=phone_number,
            password_hash=password_hash,
            role=UserRole.PATIENT,
            is_email_verified=False,
        )
        self.db.add(user)
        await self.db.flush()

        # Parse date_of_birth
        parsed_date_of_birth = None
        if date_of_birth:
            if isinstance(date_of_birth, str):
                try:
                    parsed_date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
                except ValueError:
                    pass
            elif isinstance(date_of_birth, datetime):
                parsed_date_of_birth = date_of_birth.date()
            elif isinstance(date_of_birth, date):
                parsed_date_of_birth = date_of_birth

        profile = PatientProfile(
            user_id=user.id,
            full_name=full_name,
            date_of_birth=parsed_date_of_birth,
            gender=gender,
            emergency_contact=emergency_contact,
        )
        self.db.add(profile)
        await self.db.flush()

        token_record, raw_token = await self.create_email_verification_token(email)

        return user, raw_token

    async def verify_email_token(
        self,
        raw_token: str,
        password: str,
    ) -> tuple[User, str, str]:
        """
        Verify an email verification token and set the patient's password (ADR-005).

        Finds the matching token by iterating active tokens, verifying bcrypt hash.
        Marks token as used, sets user password, marks email as verified.
        Issues JWT access and refresh tokens with aud: "patient".

        Returns:
            tuple: (user, access_token, refresh_token)

        Raises:
            ValueError: If token is invalid, expired, or already used.
        """
        # Find all active (not used, not expired) tokens
        result = await self.db.execute(
            select(EmailVerificationToken)
            .where(EmailVerificationToken.is_used == False)
            .where(EmailVerificationToken.is_expired == False)
            .where(EmailVerificationToken.expires_at > datetime.now(timezone.utc))
        )
        active_tokens = result.scalars().all()

        # Iterate and bcrypt-verify raw token against each hash
        matched_token = None
        for token_record in active_tokens:
            if self.verify_password(raw_token, token_record.token_hash):
                matched_token = token_record
                break

        if matched_token is None:
            # Check if the token was already used (for 409 response)
            all_tokens_result = await self.db.execute(
                select(EmailVerificationToken)
                .where(EmailVerificationToken.is_used == True)
            )
            used_tokens = all_tokens_result.scalars().all()
            for token_record in used_tokens:
                if self.verify_password(raw_token, token_record.token_hash):
                    raise ValueError("TOKEN_ALREADY_USED")

            raise ValueError("Invalid or expired verification token.")

        # Mark token as used
        matched_token.is_used = True

        # Get user by email and update password + verification status
        user = await self.get_user_by_email(matched_token.email)
        if not user:
            raise ValueError("User not found for this verification token.")

        user.password_hash = self.hash_password(password)
        user.is_email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)

        await self.db.flush()

        # Issue JWT tokens with aud: "patient"
        access_token = self.create_access_token(str(user.id), UserRole.PATIENT)
        refresh_token = self.create_refresh_token(str(user.id))
        return user, access_token, refresh_token

    async def resend_verification_email(
        self,
        email: str,
    ) -> tuple[Optional[User], Optional[str]]:
        """
        Resend email verification token to patient (ADR-005).

        Invalidates existing active tokens for the email, generates a new token,
        and enqueues verification email.

        Returns:
            tuple: (user, raw_token) or (None, None) if user not found.

        Raises:
            ValueError: If rate limit exceeded or email is already verified.
        """
        # 1. Enforce rate limit (3 requests per 15 minutes)
        count = await self.check_email_rate_limit(email)
        if count >= 3:
            raise ValueError("Rate limit exceeded. Maximum 3 email verification requests per 15 minutes allowed.")

        # 2. Find user by email
        user = await self.get_user_by_email(email)
        if not user:
            return None, None

        if user.is_email_verified:
            raise ValueError("EMAIL_ALREADY_VERIFIED")

        # 3. Invalidate prior active tokens
        result = await self.db.execute(
            select(EmailVerificationToken)
            .where(EmailVerificationToken.email == email)
            .where(EmailVerificationToken.is_used == False)
            .where(EmailVerificationToken.is_expired == False)
        )
        active_tokens = result.scalars().all()
        for token_record in active_tokens:
            token_record.is_expired = True

        # 4. Generate new verification token
        token_record, raw_token = await self.create_email_verification_token(email)

        return user, raw_token

    async def authenticate_staff(
        self,
        email: str,
        password: str,
    ) -> Optional[User]:
        """
        Authenticate a staff user with email and password.

        Returns the user if authentication succeeds, None otherwise.
        """
        user = await self.get_user_by_email(email)
        if not user:
            return None

        # Check if user is staff (not patient)
        if user.role == UserRole.PATIENT:
            return None

        # Verify password
        if not self.verify_password(password, user.password_hash):
            return None

        return user

    async def authenticate_patient(
        self,
        email: str,
        password: str,
    ) -> tuple[Optional[User], Optional[str]]:
        """
        Authenticate a patient user with email and password (ADR-005).

        Returns:
            tuple: (user, error_reason)
            - (user, None) on success
            - (None, "INVALID_CREDENTIALS") if email/password wrong or not a patient
            - (None, "EMAIL_NOT_VERIFIED") if patient exists but email not verified
        """
        user = await self.get_user_by_email(email)
        if not user:
            return None, "INVALID_CREDENTIALS"

        # Must be a patient
        user_role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
        if user_role != UserRole.PATIENT:
            return None, "INVALID_CREDENTIALS"

        # Verify password
        if not self.verify_password(password, user.password_hash):
            return None, "INVALID_CREDENTIALS"

        # Check email verification status
        if not user.is_email_verified:
            return None, "EMAIL_NOT_VERIFIED"

        return user, None

    async def get_user_verification_status(self, user_id: str) -> bool:
        """Check if user's phone is verified (has used an OTP)."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        # Check if user has any used OTPs
        result = await self.db.execute(
            select(func.count(VerificationOTP.id))
            .where(VerificationOTP.phone_number == user.phone_number)
            .where(VerificationOTP.is_used == True)
        )
        return result.scalar_one() > 0
