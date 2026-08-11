"""
CMP Appointments API Module.

Provides endpoints for appointment booking, cancellation, and rescheduling.
"""

from api.v1.appointments.router import router

__all__ = ["router"]
