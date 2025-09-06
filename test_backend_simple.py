#!/usr/bin/env python3
"""
Simple Backend API Test
Tests the core FastAPI functionality without all dependencies
"""

import sys
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_basic_fastapi():
    """Test basic FastAPI functionality"""
    print("🧪 Testing basic FastAPI setup...")

    # Create a simple FastAPI app
    app = FastAPI(title="R.E.M.I Test API")

    @app.get("/")
    def root():
        return {"message": "R.E.M.I Test API is running", "status": "healthy"}

    @app.get("/health")
    def health():
        return {"status": "healthy", "service": "remi-backend"}

    # Test with TestClient
    client = TestClient(app)

    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ Root endpoint test passed")

    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ Health endpoint test passed")

    print("✅ Basic FastAPI test completed successfully!")
    return True


def test_imports():
    """Test if we can import key modules"""
    print("🧪 Testing module imports...")

    try:
        import fastapi
        print(f"✅ FastAPI version: {fastapi.__version__}")
    except ImportError as e:
        print(f"❌ FastAPI import failed: {e}")
        return False

    try:
        import uvicorn
        print(f"✅ Uvicorn available")
    except ImportError as e:
        print(f"❌ Uvicorn import failed: {e}")
        return False

    try:
        import pydantic
        print(f"✅ Pydantic version: {pydantic.__version__}")
    except ImportError as e:
        print(f"❌ Pydantic import failed: {e}")
        return False

    # Test optional imports
    optional_modules = [
        ("sqlalchemy", "SQLAlchemy"),
        ("redis", "Redis"),
        ("asyncpg", "AsyncPG"),
        ("anthropic", "Anthropic"),
        ("openai", "OpenAI")
    ]

    for module_name, display_name in optional_modules:
        try:
            __import__(module_name)
            print(f"✅ {display_name} available")
        except ImportError:
            print(f"⚠️  {display_name} not available (optional)")

    return True


def test_config():
    """Test configuration loading"""
    print("🧪 Testing configuration...")

    try:
        from config.config import settings
        print(f"✅ Configuration loaded")
        print(f"   Environment: {getattr(settings, 'ENVIRONMENT', 'unknown')}")
        print(f"   Debug mode: {getattr(settings, 'DEBUG', 'unknown')}")
        return True
    except Exception as e:
        print(f"⚠️  Configuration loading failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Starting R.E.M.I Backend Tests")
    print("=" * 50)

    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("Basic FastAPI", test_basic_fastapi),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} test FAILED with exception: {e}")

    print(f"\n📊 Test Summary:")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    print(f"   Total:  {passed + failed}")

    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
