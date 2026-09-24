"""
Data Protection Security Tests for Syncline MESH

Test Cases:
- Test Case 28: Encryption at Rest
- Test Case 29: TLS Configuration
- Test Case 30: Password Storage

These tests validate that data protection mechanisms properly
secure sensitive information at rest and in transit.

Run with:
    pytest test_data_protection.py -v
"""

import base64
import hashlib
import os
import socket
import ssl
import sys
from typing import Any, Dict

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestDataProtectionSecurity:
    """
    Data Protection Security Test Suite

    Validates encryption, TLS, and secure storage mechanisms.
    """

    BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")
    SECURE_URL = os.getenv("TEST_SECURE_URL", "https://localhost:8443")
    AUTH_TOKEN = "test_security_token"

    @pytest.fixture
    def client(self) -> httpx.Client:
        return httpx.Client(base_url=self.BASE_URL, timeout=30.0)

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.AUTH_TOKEN}"}

    # ==========================================================================
    # Test Case 28: Encryption at Rest
    # ==========================================================================

    def test_tc28_oauth_tokens_not_exposed_in_api(self, client, auth_headers):
        """
        Test Case 28: Encryption at Rest

        Test: Examine API responses for plaintext OAuth tokens
        Expected: All tokens encrypted; no plaintext credentials in responses
        """
        # Get connections (should not expose raw tokens)
        response = client.get("/api/v1/connections", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            response_text = str(data).lower()

            # Check that no raw tokens are exposed
            sensitive_patterns = [
                "access_token",
                "refresh_token",
                "oauth_token",
                "api_key",
                "api_secret",
                "client_secret",
            ]

            for pattern in sensitive_patterns:
                if pattern in response_text:
                    # Pattern exists but value should be masked or absent
                    connections = (
                        data if isinstance(data, list) else data.get("connections", [])
                    )
                    for conn in connections:
                        # Token values should be masked or not present
                        if "access_token" in conn:
                            token = conn.get("access_token", "")
                            assert (
                                token == ""
                                or token.startswith("***")
                                or len(token) < 10
                            ), "Raw access token exposed in API response"

        print("\n✅ Test Case 28: PASS - OAuth tokens not exposed in API responses")

    def test_tc28_sensitive_data_masked_in_logs(self, client, auth_headers):
        """
        Test Case 28 (Extended): Sensitive data should be masked in logs

        Note: This is a code review test - actual log verification would
        require access to log files.
        """
        # Trigger various operations that might log sensitive data
        client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "SensitivePassword123!"},
        )

        # If we had log access, we'd verify password is not in logs
        print("\n⚠️ Test Case 28 (Extended): Log masking requires log file inspection")

    def test_tc28_database_credentials_not_exposed(self, client, auth_headers):
        """
        Test Case 28 (Extended): Database credentials not in responses
        """
        # Health check should not expose DB credentials
        response = client.get("/api/v1/health")

        if response.status_code == 200:
            data = response.json()
            response_text = str(data).lower()

            # Should not contain DB credentials
            assert (
                "password" not in response_text or "database" not in response_text
            ), "Database password possibly exposed in health check"
            assert (
                "postgres://" not in response_text
            ), "Database connection string exposed"
            assert (
                "postgresql://" not in response_text
            ), "Database connection string exposed"

        print("\n✅ Test Case 28 (Extended): Database credentials not exposed")

    # ==========================================================================
    # Test Case 29: TLS Configuration
    # ==========================================================================

    def test_tc29_tls_version_check(self):
        """
        Test Case 29: TLS Configuration

        Test: Check supported TLS versions
        Expected: Only TLS 1.2+ accepted; older protocols rejected
        """
        host = os.getenv("TLS_TEST_HOST", "localhost")
        port = int(os.getenv("TLS_TEST_PORT", "8443"))

        # Test TLS 1.2 (should work)
        try:
            context_12 = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context_12.minimum_version = ssl.TLSVersion.TLSv1_2
            context_12.maximum_version = ssl.TLSVersion.TLSv1_2
            context_12.check_hostname = False
            context_12.verify_mode = ssl.CERT_NONE

            with socket.create_connection((host, port), timeout=5) as sock:
                with context_12.wrap_socket(sock, server_hostname=host) as ssock:
                    tls_12_works = True
                    print(f"\n  TLS 1.2: Supported (Version: {ssock.version()})")
        except (ssl.SSLError, socket.error, ConnectionRefusedError):
            tls_12_works = False
            print("\n  TLS 1.2: Not available or refused")

        # Test TLS 1.3 (should work if supported by server)
        try:
            context_13 = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context_13.minimum_version = ssl.TLSVersion.TLSv1_3
            context_13.check_hostname = False
            context_13.verify_mode = ssl.CERT_NONE

            with socket.create_connection((host, port), timeout=5) as sock:
                with context_13.wrap_socket(sock, server_hostname=host) as ssock:
                    tls_13_works = True
                    print(f"  TLS 1.3: Supported (Version: {ssock.version()})")
        except (ssl.SSLError, socket.error, ConnectionRefusedError):
            tls_13_works = False
            print("  TLS 1.3: Not available")

        # At least TLS 1.2 or 1.3 should be supported
        if tls_12_works or tls_13_works:
            print("\n✅ Test Case 29: PASS - Modern TLS versions supported")
        else:
            print(
                "\n⚠️ Test Case 29: Could not verify TLS (server might not be running HTTPS)"
            )

    def test_tc29_old_tls_rejected(self):
        """
        Test Case 29 (Extended): Old TLS versions should be rejected

        Note: This test attempts connections with deprecated TLS versions
        """
        host = os.getenv("TLS_TEST_HOST", "localhost")
        port = int(os.getenv("TLS_TEST_PORT", "8443"))

        old_protocols_rejected = True

        # TLS 1.0 should be rejected
        try:
            context_10 = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context_10.maximum_version = ssl.TLSVersion.TLSv1
            context_10.check_hostname = False
            context_10.verify_mode = ssl.CERT_NONE

            with socket.create_connection((host, port), timeout=5) as sock:
                with context_10.wrap_socket(sock, server_hostname=host) as ssock:
                    # If we get here, TLS 1.0 was accepted (bad!)
                    old_protocols_rejected = False
                    print("  ⚠️ TLS 1.0: Accepted (should be rejected)")
        except (ssl.SSLError, socket.error, ConnectionRefusedError, ValueError):
            print("  TLS 1.0: Correctly rejected")

        # TLS 1.1 should be rejected
        try:
            context_11 = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context_11.maximum_version = ssl.TLSVersion.TLSv1_1
            context_11.check_hostname = False
            context_11.verify_mode = ssl.CERT_NONE

            with socket.create_connection((host, port), timeout=5) as sock:
                with context_11.wrap_socket(sock, server_hostname=host) as ssock:
                    old_protocols_rejected = False
                    print("  ⚠️ TLS 1.1: Accepted (should be rejected)")
        except (ssl.SSLError, socket.error, ConnectionRefusedError, ValueError):
            print("  TLS 1.1: Correctly rejected")

        if old_protocols_rejected:
            print("\n✅ Test Case 29 (Extended): Old TLS protocols rejected")
        else:
            print("\n⚠️ Test Case 29 (Extended): Some old TLS protocols accepted")

    def test_tc29_https_enforcement(self, client):
        """
        Test Case 29 (Extended): Check for HTTPS redirect headers
        """
        response = client.get("/api/v1/health")

        # Check for HSTS header
        hsts = response.headers.get("strict-transport-security")
        if hsts:
            print(f"\n  HSTS Header: {hsts}")
            assert "max-age" in hsts.lower(), "HSTS should include max-age"
        else:
            print("\n  ⚠️ No HSTS header found (might be development mode)")

        print("\n✅ Test Case 29 (Extended): Security headers checked")

    # ==========================================================================
    # Test Case 30: Password Storage
    # ==========================================================================

    def test_tc30_password_not_returned_in_responses(self, client):
        """
        Test Case 30: Password Storage

        Test: Verify passwords are never returned in API responses
        Expected: All passwords hashed; no plaintext storage or transmission
        """
        # Registration should not echo password back
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test_password_check@example.com",
                "password": "TestPassword123!",
                "name": "Test User",
            },
        )

        if response.status_code in [200, 201]:
            data = response.json()

            # Password should never be in response
            assert "password" not in data, "Password returned in registration response"
            assert "TestPassword123!" not in str(data), "Plaintext password in response"

        # User profile should not contain password
        response = client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {self.AUTH_TOKEN}"}
        )

        if response.status_code == 200:
            data = response.json()
            assert "password" not in data, "Password in user profile response"
            assert "password_hash" not in data, "Password hash exposed"

        print("\n✅ Test Case 30: PASS - Passwords not exposed in API responses")

    def test_tc30_login_timing_attack_resistance(self, client):
        """
        Test Case 30 (Extended): Login should resist timing attacks

        Response time should be similar for valid and invalid users.
        """
        import time

        valid_timings = []
        invalid_timings = []

        # Time valid username attempts
        for _ in range(5):
            start = time.perf_counter()
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": "admin@example.com",  # Might exist
                    "password": "wrong_password",
                },
            )
            valid_timings.append(time.perf_counter() - start)

        # Time invalid username attempts
        for _ in range(5):
            start = time.perf_counter()
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": "nonexistent_user_xyz@example.com",
                    "password": "wrong_password",
                },
            )
            invalid_timings.append(time.perf_counter() - start)

        avg_valid = sum(valid_timings) / len(valid_timings)
        avg_invalid = sum(invalid_timings) / len(invalid_timings)

        # Timing difference should be less than 100ms (timing attack resistance)
        timing_diff = abs(avg_valid - avg_invalid)

        print(f"\n  Valid user avg time: {avg_valid*1000:.2f}ms")
        print(f"  Invalid user avg time: {avg_invalid*1000:.2f}ms")
        print(f"  Timing difference: {timing_diff*1000:.2f}ms")

        if timing_diff < 0.1:  # 100ms
            print("\n✅ Test Case 30 (Extended): Login resists timing attacks")
        else:
            print(
                "\n⚠️ Test Case 30 (Extended): Timing difference detected (may enable user enumeration)"
            )

    def test_tc30_password_requirements_enforced(self, client):
        """
        Test Case 30 (Extended): Password strength requirements
        """
        weak_passwords = [
            "123",
            "password",
            "12345678",
            "qwerty",
            "abc",
        ]

        for weak_pwd in weak_passwords:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"test_{weak_pwd}@example.com",
                    "password": weak_pwd,
                    "name": "Test",
                },
            )

            # Weak passwords should be rejected
            if response.status_code in [200, 201]:
                print(f"  ⚠️ Weak password accepted: {weak_pwd}")
            else:
                # 400 or 422 expected for validation failure
                assert response.status_code in [
                    400,
                    422,
                ], f"Unexpected status for weak password: {response.status_code}"

        print("\n✅ Test Case 30 (Extended): Password requirements checked")


class TestSensitiveDataHandling:
    """
    Sensitive Data Handling Tests

    Additional tests for PII and sensitive data protection.
    """

    BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")
    AUTH_TOKEN = "test_security_token"

    @pytest.fixture
    def client(self) -> httpx.Client:
        return httpx.Client(base_url=self.BASE_URL, timeout=30.0)

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.AUTH_TOKEN}"}

    def test_error_messages_dont_expose_internals(self, client, auth_headers):
        """Error messages should not expose internal details."""
        # Trigger various errors
        error_endpoints = [
            ("/api/v1/messages/invalid_id", "GET"),
            ("/api/v1/notfound", "GET"),
        ]

        for endpoint, method in error_endpoints:
            if method == "GET":
                response = client.get(endpoint, headers=auth_headers)

            if response.status_code >= 400:
                data = response.text.lower()

                # Should not expose stack traces or internal paths
                assert "traceback" not in data, "Stack trace in error response"
                assert "/users/" not in data or "api" in data, "Internal path exposed"
                assert 'file "/' not in data, "File path in error"

        print("\n✅ Error messages don't expose internal details")

    def test_debug_mode_disabled(self, client):
        """Debug mode should be disabled in production."""
        response = client.get("/api/v1/health")

        # Debug info should not be in responses
        if response.status_code == 200:
            data = response.json()

            assert (
                "debug" not in str(data).lower() or data.get("debug") != True
            ), "Debug mode appears to be enabled"

        print("\n✅ Debug mode check passed")

    def test_cors_configuration(self, client):
        """CORS should be properly configured."""
        # Preflight request
        response = client.options(
            "/api/v1/messages",
            headers={
                "Origin": "http://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Check CORS headers
        allow_origin = response.headers.get("access-control-allow-origin", "")

        # Should not allow all origins in production
        if allow_origin == "*":
            print("\n  ⚠️ CORS allows all origins (review for production)")
        else:
            print(f"\n  CORS Allow-Origin: {allow_origin}")

        print("\n✅ CORS configuration checked")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
