"""CMP Notification Providers.

Concrete notification provider adapters implementing the NotificationService
Strategy Pattern interface (ADR-004, ADR-005).

Available providers:
- EmailClient: Email delivery (SMTP, console/mock, SendGrid/SES placeholder)
- WhatsAppCloudAPIClient: WhatsApp Business Cloud API (primary)
- TermiiSMSClient: Termii SMS with Nigerian DND-bypass (SMS fallback)
- InfobipSMSClient: Infobip international SMS (secondary SMS fallback)
"""

from services.notification.providers.email_provider import EmailClient

__all__ = ["EmailClient"]
