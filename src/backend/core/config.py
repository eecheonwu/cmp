"""
CMP Application Configuration.

Loads configuration from environment variables using pydantic-settings.
Supports dev, staging, and production environments.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Clinic Modernization Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # dev, staging, production
    DEBUG: bool = True

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "CMP API"

# CORS Configuration
    # CloudFront domain(s) allowed to access the API
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"  # Comma-separated list

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Database (AWS RDS PostgreSQL 16+)
    DATABASE_URL: Optional[str] = None
    DB_ECHO: bool = False  # Set to True for SQL query logging in dev

    # Redis (for Celery and rate limiting)
    REDIS_URL: str = "redis://localhost:6379/0"

    # AWS KMS Configuration
    AWS_REGION: str = "af-south-1"  # Cape Town region for Nigeria
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    KMS_KEY_ID: Optional[str] = None  # KMS Key ARN or Alias

    # JWT Configuration
    JWT_SECRET_KEY: str = "change-me-in-production-use-strong-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OTP Configuration
    OTP_LENGTH: int = 6
    OTP_TTL_SECONDS: int = 600  # 10 minutes
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RATE_LIMIT_REQUESTS: int = 3
    OTP_RATE_LIMIT_WINDOW_SECONDS: int = 900  # 15 minutes

    # Notification Provider Configuration
    WHATSAPP_API_URL: Optional[str] = None
    WHATSAPP_API_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None

    TERMII_API_KEY: Optional[str] = None
    TERMII_SENDER_ID: Optional[str] = None
    TERMII_API_URL: str = "https://api.termii.com/api"

    INFOBIP_API_KEY: Optional[str] = None
    INFOBIP_API_URL: str = "https://api.infobip.com"
    INFOBIP_BASE_URL: Optional[str] = None

    # Email Provider Configuration
    EMAIL_PROVIDER: str = "console"  # console, smtp, sendgrid, ses, mock
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = False
    SENDGRID_API_KEY: Optional[str] = None
    AWS_SES_REGION: Optional[str] = None
    EMAIL_FROM_ADDRESS: str = "noreply@clinic.ng"
    EMAIL_FROM_NAME: str = "Clinic Modernization Platform"
    EMAIL_VERIFICATION_BASE_URL: str = "http://localhost:5173/patient/create-password"
    EMAIL_VERIFICATION_TOKEN_TTL_MINUTES: int = 60

    # Notification Timeouts
    NOTIFICATION_TIMEOUT_SECONDS: int = 15
    NOTIFICATION_MAX_RETRIES: int = 3

    # Transaction & Lock Timeouts
    DB_TRANSACTION_TIMEOUT_SECONDS: int = 3  # Max lock wait time

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "json"  # json or text

    # Correlation ID
    CORRELATION_ID_HEADER: str = "X-Correlation-ID"

    @property
    def database_url_async(self) -> str:
        """Return async database URL (asyncpg driver)."""
        if self.DATABASE_URL:
            # Replace postgresql:// with postgresql+asyncpg://
            return self.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
        # Default local development URL
        return "postgresql+asyncpg://cmp_user:cmp_password@localhost:5432/cmp_db"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT in ("dev", "development")


# Global settings instance
settings = Settings()
