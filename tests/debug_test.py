"""Debug script to identify the exact error in test_setup.py"""
import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Debug: Testing imports and configuration")
print("=" * 60)
print()

try:
    print("[1] Importing config...")
    from src.backend.core.config import settings
    print(f"    [OK] Config loaded: {settings.APP_NAME}")
except Exception as e:
    print(f"    [FAIL] Config import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[2] Importing FastAPI app...")
    from src.backend.main import app
    print(f"    [OK] App imported: {app.title}")
except Exception as e:
    print(f"    [FAIL] App import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[3] Testing FastAPI app...")
    assert app is not None
    assert hasattr(app, 'title')
    assert app.title == settings.APP_NAME
    print(f"    [OK] App validated")
except Exception as e:
    print(f"    [FAIL] App validation failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[4] Testing health check endpoint...")
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/health")
    print(f"    Status: {response.status_code}")
    print(f"    Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print(f"    [OK] Health check passed")
except Exception as e:
    print(f"    [FAIL] Health check failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[5] Testing root endpoint...")
    response = client.get("/")
    print(f"    Status: {response.status_code}")
    print(f"    Response: {response.json()}")
    assert response.status_code == 200
    assert "message" in response.json()
    print(f"    [OK] Root endpoint passed")
except Exception as e:
    print(f"    [FAIL] Root endpoint failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[6] Testing CORS middleware...")
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    print(f"    Status: {response.status_code}")
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    print(f"    [OK] CORS middleware passed")
except Exception as e:
    print(f"    [FAIL] CORS middleware failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[7] Testing middleware stack...")
    response = client.get("/health")
    assert settings.CORRELATION_ID_HEADER in response.headers
    correlation_id = response.headers[settings.CORRELATION_ID_HEADER]
    print(f"    Correlation ID: {correlation_id[:20]}...")
    import uuid
    uuid.UUID(correlation_id)
    print(f"    [OK] Middleware stack passed")
except Exception as e:
    print(f"    [FAIL] Middleware stack failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("SUCCESS: All tests passed")
print("=" * 60)