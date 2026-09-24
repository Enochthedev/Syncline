"""
Pytest Configuration and Fixtures

Provides test fixtures and configuration for API testing,
including performance and security test suites.
"""

import asyncio
import os
from typing import AsyncGenerator, Optional

import httpx
import pytest
import pytest_asyncio

# Try to import app, but allow tests to run without it. Catch everything:
# importing main pulls in settings validation and every router, so a failure
# here is as likely to be a config error as a missing module — and swallowing
# the reason is how these tests ended up silently talking to localhost:8000.
try:
    from main import app

    APP_AVAILABLE = True
    APP_IMPORT_ERROR: Optional[BaseException] = None
except Exception as exc:  # noqa: BLE001 - reported below, not hidden
    APP_AVAILABLE = False
    APP_IMPORT_ERROR = exc
    app = None


# ==============================================================================
# PYTEST CONFIGURATION
# ==============================================================================


def pytest_configure(config):
    """Configure custom markers for test categorization."""
    config.addinivalue_line("markers", "security: mark test as a security test")
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line(
        "markers", "slow: mark test as slow (excluded from normal runs)"
    )
    config.addinivalue_line("markers", "stress: mark test as a stress test")
    config.addinivalue_line("markers", "benchmark: mark test as a benchmark")


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their location, and skip what needs a server.

    The security and performance suites talk to a running instance over HTTP
    (``TEST_URL``, default http://localhost:8000). With nothing listening they
    do not fail meaningfully — every one of them reports a connection error —
    so they are skipped unless TEST_URL is set explicitly.
    """
    needs_server = os.getenv("TEST_URL") is None
    skip_no_server = pytest.mark.skip(
        reason="needs a running instance: set TEST_URL to the base URL"
    )

    for item in items:
        # Auto-mark security tests
        if "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
            if needs_server:
                item.add_marker(skip_no_server)

        # Auto-mark performance tests
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            if needs_server:
                item.add_marker(skip_no_server)


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


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async client bound to the app in-process, or to TEST_URL if set.

    This has to be a ``pytest_asyncio.fixture``: under pytest-asyncio's strict
    mode a plain ``pytest.fixture`` hands the test the async generator itself,
    which is why every test using it failed with "'async_generator' object has
    no attribute 'get'".
    """
    if APP_AVAILABLE and app:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
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
        "timestamp": "2026-01-05T00:00:00Z",
    }


@pytest.fixture
def sample_contact() -> dict:
    """Sample contact for testing."""
    return {
        "id": "test_contact_001",
        "name": "Test Contact",
        "email": "test@example.com",
        "phone": "+1234567890",
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
    reason="Live server tests disabled",
)

skip_if_no_auth = pytest.mark.skipif(
    not os.getenv("TEST_AUTH_TOKEN"), reason="No authentication token provided"
)
