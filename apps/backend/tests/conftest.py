"""
Pytest Configuration and Fixtures

Provides test fixtures and configuration for API testing,
including performance and security test suites.
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator

import httpx

# Try to import app, but allow tests to run without it
try:
    from main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False
    app = None


# ==============================================================================
# PYTEST CONFIGURATION
# ==============================================================================

def pytest_configure(config):
    """Configure custom markers for test categorization."""
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (excluded from normal runs)"
    )
    config.addinivalue_line(
        "markers", "stress: mark test as a stress test"
    )
    config.addinivalue_line(
        "markers", "benchmark: mark test as a benchmark"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their location."""
    for item in items:
        # Auto-mark security tests
        if "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        
        # Auto-mark performance tests
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)


# ==============================================================================
# EVENT LOOP FIXTURE
# ==============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==============================================================================
# HTTP CLIENT FIXTURES
# ==============================================================================

@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async test client with app (for unit testing)."""
    if APP_AVAILABLE and app:
        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    else:
        # Fall back to external client
        base_url = os.getenv("TEST_URL", "http://localhost:8000")
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as ac:
            yield ac


@pytest.fixture
def sync_client() -> httpx.Client:
    """Create synchronous HTTP client for testing."""
    base_url = os.getenv("TEST_URL", "http://localhost:8000")
    return httpx.Client(base_url=base_url, timeout=30.0)


@pytest.fixture
def auth_token() -> str:
    """Get test authentication token."""
    return os.getenv("TEST_AUTH_TOKEN", "test_token_for_testing")


@pytest.fixture
def auth_headers(auth_token) -> dict:
    """Get authentication headers for testing."""
    return {"Authorization": f"Bearer {auth_token}"}


# ==============================================================================
# TEST DATA FIXTURES
# ==============================================================================

@pytest.fixture
def sample_message() -> dict:
    """Sample message for testing."""
    return {
        "id": "test_msg_001",
        "content": "This is a test message for testing purposes.",
        "sender_id": "test_sender",
        "platform": "test",
        "timestamp": "2026-01-05T00:00:00Z"
    }


@pytest.fixture
def sample_contact() -> dict:
    """Sample contact for testing."""
    return {
        "id": "test_contact_001",
        "name": "Test Contact",
        "email": "test@example.com",
        "phone": "+1234567890"
    }


@pytest.fixture
def sql_injection_payloads() -> list:
    """Common SQL injection payloads for security testing."""
    return [
        "'; DROP TABLE messages; --",
        "1' OR '1'='1",
        "1 UNION SELECT * FROM users --",
        "admin'--",
        "' OR 1=1--",
        "1; SELECT * FROM users",
    ]


@pytest.fixture
def xss_payloads() -> list:
    """Common XSS payloads for security testing."""
    return [
        "<script>alert('XSS')</script>",
        "<img src='x' onerror='alert(1)'>",
        "<svg onload='alert(1)'>",
        "javascript:alert('XSS')",
        "<iframe src='javascript:alert(1)'></iframe>",
    ]


# ==============================================================================
# RESULTS DIRECTORY FIXTURE
# ==============================================================================

@pytest.fixture(scope="session")
def results_dir(tmp_path_factory) -> str:
    """Create and return results directory for test outputs."""
    results = tmp_path_factory.mktemp("results")
    return str(results)


# ==============================================================================
# SKIP CONDITIONS
# ==============================================================================

skip_if_no_server = pytest.mark.skipif(
    os.getenv("SKIP_LIVE_TESTS", "false").lower() == "true",
    reason="Live server tests disabled"
)

skip_if_no_auth = pytest.mark.skipif(
    not os.getenv("TEST_AUTH_TOKEN"),
    reason="No authentication token provided"
)

