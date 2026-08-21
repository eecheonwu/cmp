"""
CMP Reports API Router Package.

Implements Task 3.4 — Reports & Dashboards:
- GET /reports/branch/daily (manager)
- GET /reports/organization/summary (executive)
"""

from .router import router

__all__ = ["router"]
