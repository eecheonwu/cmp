"""
Re-export EmailClient provider for convenient module imports.
"""

from services.notification.providers.email_provider import EmailClient

__all__ = ["EmailClient"]
