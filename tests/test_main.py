"""
Test suite for Task 6.1: Main Application and Admin Router Tests.

Tests:
- Main application endpoints (health, root)
- Admin router endpoints
"""

import sys
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


# ── Main Application Tests ─────────────────────────────────────────────────

class TestMainApplication:
    """Tests for main application endpoints."""

    def test_health_endpoint(self, test_client):
        """Test /health endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "application" in data
        assert "version" in data

    def test_root_endpoint(self, test_client):
        """Test / endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data

    def test_app_has_middleware(self):
        """Test that middleware is configured."""
        from src.backend.main import app

        # Check that middleware exists
        assert len(app.user_middleware) > 0


# ── Admin Router Tests ────────────────────────────────────────────────────

class TestAdminRouter:
    """Tests for admin router endpoints."""

    def test_admin_router_included(self):
        """Test that admin router is included in main app."""
        from src.backend.main import app

        routes = [r.path for r in app.routes]
        admin_routes = [r for r in routes if "/admin" in r]

        assert len(admin_routes) > 0

    def test_create_branch_endpoint(self, test_client):
        """Test POST /api/v1/admin/branches endpoint exists."""
        response = test_client.post(
            "/api/v1/admin/branches",
            json={
                "name": "Test Branch",
                "address": "123 Test St",
            },
        )
        assert response.status_code in [401, 201, 500]

    def test_list_branches_endpoint(self, test_client):
        """Test GET /api/v1/admin/branches endpoint exists."""
        response = test_client.get("/api/v1/admin/branches")
        assert response.status_code in [401, 200, 500]

    def test_update_user_role_endpoint(self, test_client):
        """Test PATCH /api/v1/admin/users/{user_id}/role endpoint exists."""
        response = test_client.patch(
            "/api/v1/admin/users/test-user-id/role",
            json={
                "role": "DOCTOR",
            },
        )
        assert response.status_code in [401, 200, 500]

    def test_list_users_endpoint(self, test_client):
        """Test GET /api/v1/admin/users endpoint exists."""
        response = test_client.get("/api/v1/admin/users")
        assert response.status_code in [401, 200, 500]