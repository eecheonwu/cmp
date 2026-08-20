# ADR-004: Pluggable Notification Service with Multi-Provider Failover

**Status**: Accepted
**Date**: 2026-06-04
**Deciders**: Antigravity (AI Architect), Clinic Owner, Integration Engineer

## Context

The Clinic Modernization Platform (CMP) relies heavily on notifications to achieve **BG-002** (reducing patient no-shows by 25–30%). The system must send transactional notifications (booking confirmations, reminders, cancellation alerts) across WhatsApp and SMS.

In Nigeria, mobile network carrier routing is highly unstable, and strict Do-Not-Disturb (DND) policies often block transactional SMS messages unless routed through licensed domestic gateways with DND-override capabilities. The system requirements specify:
1. **INT-001**: Integrate WhatsApp Business Cloud API.
2. **INT-002**: Utilize Termii as the primary local SMS provider to bypass DND across Nigerian carriers (MTN, Airtel, Glo, 9mobile).
3. **INT-003**: Integrate Infobip as a secondary fallback SMS provider.
4. **INT-004**: Implement a pluggable `NotificationService` layer that abstracts SMS, WhatsApp, and Email integrations to avoid vendor lock-in and handle failovers automatically.

## Decision

We will design a unified, pluggable **Notification Abstraction Layer** using the Strategy Pattern. The system will define a generic `NotificationService` interface. Concrete adapter classes will implement this interface for each vendor (e.g., `WhatsAppCloudAPIClient`, `TermiiSMSClient`, `InfobipSMSClient`). 

The application will route notification tasks to an async worker queue (e.g., Celery or FastAPI Background Tasks) executing a failover chain:
1. Attempt delivery via WhatsApp Business Cloud API.
2. If WhatsApp fails (network error, account issue, or user phone has no WhatsApp), failover to SMS via Termii.
3. If Termii SMS delivery fails (timeout or gateway error), failover to SMS via Infobip.

## Options Considered

### Option 1: Pluggable Notification Service (Strategy Pattern + Async Workers) — Chosen

The application uses an interface with concrete adapters. Delivery attempts are wrapped in an async background worker that executes the failover logic in sequence.

* **Pros**:
  * Prevents vendor lock-in (**INT-004**). We can add or swap SMS providers (e.g., Twilio or Africa's Talking) by creating a new class implementing the interface.
  * Maximum delivery reliability: Ensures patients receive critical reminders even if a primary gateway goes offline.
  * Offloading execution to background tasks prevents HTTP request latency on booking confirmation pages.
* **Cons**:
  * Slightly higher codebase complexity to manage and maintain three provider integrations.
  * Risk of duplicate messages if a gateway registers a timeout but eventually delivers the message (mitigated by strict idempotency tracking in the audit logs).
* **Estimated effort**: Low to Medium. Straightforward OOP design and async task pattern.

### Option 2: Single Notification Provider (e.g., Infobip Only) — Rejected

Using a single global provider like Infobip or Twilio for both WhatsApp and SMS communications.

* **Pros**:
  * Single codebase integration, single billing entity, and simplified dashboard.
* **Cons**:
  * Vulnerable to single point of failure (if the gateway goes down, all patient reminders stop).
  * High risk of DND blocking. Global providers often struggle to bypass Nigerian DND rules as reliably as domestic specialized gateways like Termii.
  * Does not comply with the explicit requirements (**INT-002**, **INT-004**).
* **Estimated effort**: Low.

## Rationale

Nigeria's telecom environment requires local expertise for SMS delivery. Termii specializes in DND-bypass for Nigerian mobile numbers, making it the ideal primary provider for SMS. However, relying on a single provider represents an operational risk. The Strategy Pattern decouples the backend logic from the external API shapes, allowing the system to switch providers on-the-fly. Wrapping this in an async failover queue ensures high-reliability message delivery without slowing down user interactions on the booking screen.

## Consequences

* **Async Queue Infrastructure**: We must configure a task queue (such as Redis with FastAPI BackgroundTasks, or Celery) to execute notifications out-of-band.
* **Notification Tracking Database Table**: We must maintain a `NotificationLog` table to log attempts, provider used, status (pending, sent, delivered, failed), and error codes. This is critical for billing audits and optimizing failover rules.
* **Cost Management**: WhatsApp templates have distinct business-initiated conversation charges, while SMS providers charge per unit. The failover sequence prioritizes WhatsApp (cheaper/preferred for rich media) then Termii (cheaper local SMS) and then Infobip (backup).

## References

* [Clinic Modernization Platform SRD](file:///C:/Users/DELL/Documents/Project/clinic_app/software_requirements_document.md)
* [Termii SMS API Documentation](https://developers.termii.com/)
* [WhatsApp Business Cloud API Getting Started](https://developers.facebook.com/docs/whatsapp/cloud-api)
