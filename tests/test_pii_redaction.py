"""
Unit tests for PII redaction service.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from services.pii_redaction import (
    PIIRedactionService, PIIDetector, PIIType, PIIEntity, RedactionResult
)


class TestPIIDetector:
    """Test cases for PIIDetector."""

    @pytest.fixture
    def detector(self):
        """Create a PIIDetector instance for testing."""
        return PIIDetector()

    def test_initialization(self, detector):
        """Test PIIDetector initialization."""
        assert detector.patterns is not None
        assert len(detector.patterns) > 0
        assert PIIType.EMAIL in detector.patterns
        assert PIIType.PHONE in detector.patterns
        assert PIIType.SSN in detector.patterns

    def test_detect_email(self, detector):
        """Test email detection."""
        text = "Contact me at john.doe@example.com for more information."
        entities = detector.detect(text)

        email_entities = [e for e in entities if e.type == PIIType.EMAIL]
        assert len(email_entities) == 1
        assert email_entities[0].text == "john.doe@example.com"
        assert email_entities[0].confidence >= 0.9

    def test_detect_phone(self, detector):
        """Test phone number detection."""
        test_cases = [
            "Call me at 555-123-4567",
            "My number is (555) 123-4567",
            "Phone: 555.123.4567",
            "Contact: +1-555-123-4567"
        ]

        for text in test_cases:
            entities = detector.detect(text)
            phone_entities = [e for e in entities if e.type == PIIType.PHONE]
            assert len(
                phone_entities) >= 1, f"Failed to detect phone in: {text}"

    def test_detect_ssn(self, detector):
        """Test SSN detection."""
        # High confidence cases that should be detected
        high_confidence_cases = [
            "SSN: 123-45-6789",
            "Social Security: 123 45 6789",
        ]

        for text in high_confidence_cases:
            entities = detector.detect(text)
            ssn_entities = [e for e in entities if e.type == PIIType.SSN]
            assert len(ssn_entities) >= 1, f"Failed to detect SSN in: {text}"

        # Low confidence case that should NOT be detected (below threshold)
        low_confidence_text = "ID: 123456789"
        entities = detector.detect(low_confidence_text)
        ssn_entities = [e for e in entities if e.type == PIIType.SSN]
        assert len(
            ssn_entities) == 0, f"Should not detect low-confidence SSN in: {low_confidence_text}"

    def test_detect_credit_card(self, detector):
        """Test credit card detection."""
        test_cases = [
            "Card: 4111-1111-1111-1111",
            "Credit card: 4111 1111 1111 1111",
            "Payment: 4111111111111111"
        ]

        for text in test_cases:
            entities = detector.detect(text)
            cc_entities = [
                e for e in entities if e.type == PIIType.CREDIT_CARD]
            assert len(
                cc_entities) >= 1, f"Failed to detect credit card in: {text}"

    def test_detect_ip_address(self, detector):
        """Test IP address detection."""
        test_cases = [
            "Server IP: 192.168.1.1",
            "Connect to 10.0.0.1",
            "Address: 172.16.254.1"
        ]

        for text in test_cases:
            entities = detector.detect(text)
            ip_entities = [e for e in entities if e.type == PIIType.IP_ADDRESS]
            assert len(ip_entities) >= 1, f"Failed to detect IP in: {text}"

    def test_detect_url(self, detector):
        """Test URL detection."""
        test_cases = [
            "Visit https://example.com",
            "Check out http://test.org/page",
            "Go to www.example.com"
        ]

        for text in test_cases:
            entities = detector.detect(text)
            url_entities = [e for e in entities if e.type == PIIType.URL]
            assert len(url_entities) >= 1, f"Failed to detect URL in: {text}"

    def test_detect_date_of_birth(self, detector):
        """Test date of birth detection."""
        test_cases = [
            "Born on 01/15/1990",
            "DOB: 1990-01-15"
        ]

        for text in test_cases:
            entities = detector.detect(text)
            dob_entities = [e for e in entities if e.type ==
                            PIIType.DATE_OF_BIRTH]
            assert len(dob_entities) >= 1, f"Failed to detect DOB in: {text}"

    def test_detect_multiple_entities(self, detector):
        """Test detection of multiple PII entities in one text."""
        text = "Contact John Doe at john.doe@example.com or call 555-123-4567. SSN: 123-45-6789"
        entities = detector.detect(text)

        # Should detect email, phone, and SSN
        entity_types = {e.type for e in entities}
        assert PIIType.EMAIL in entity_types
        assert PIIType.PHONE in entity_types
        assert PIIType.SSN in entity_types
        assert len(entities) >= 3

    def test_confidence_threshold(self, detector):
        """Test confidence threshold filtering."""
        # Set a high confidence threshold
        detector.confidence_threshold = 0.95

        # This should detect high-confidence email but not low-confidence patterns
        text = "Email: test@example.com and some numbers: 123456789"
        entities = detector.detect(text)

        # Should detect email (high confidence) but maybe not the 9-digit number (lower confidence)
        email_entities = [e for e in entities if e.type == PIIType.EMAIL]
        assert len(email_entities) == 1
        assert email_entities[0].confidence >= 0.95

    def test_remove_overlaps(self, detector):
        """Test removal of overlapping entities."""
        # Create overlapping entities manually
        entities = [
            PIIEntity(PIIType.EMAIL, "test@example.com", 0, 16, 0.95),
            PIIEntity(PIIType.URL, "test@example.com",
                      0, 16, 0.85),  # Overlapping
            PIIEntity(PIIType.PHONE, "555-123-4567", 20, 32, 0.90)
        ]

        filtered = detector._remove_overlaps(entities)

        # Should keep the email (higher confidence) and phone (no overlap)
        assert len(filtered) == 2
        types = {e.type for e in filtered}
        assert PIIType.EMAIL in types
        assert PIIType.PHONE in types
        assert PIIType.URL not in types


class TestPIIRedactionService:
    """Test cases for PIIRedactionService."""

    @pytest.fixture
    def redaction_service(self):
        """Create a PIIRedactionService instance for testing."""
        return PIIRedactionService()

    @pytest.fixture
    def mock_detector(self):
        """Create a mock PIIDetector for testing."""
        detector = Mock(spec=PIIDetector)
        detector.detect.return_value = [
            PIIEntity(PIIType.EMAIL, "test@example.com", 10, 26, 0.95),
            PIIEntity(PIIType.PHONE, "555-123-4567", 30, 42, 0.90)
        ]
        return detector

    def test_initialization(self, redaction_service):
        """Test PIIRedactionService initialization."""
        assert redaction_service.detector is not None
        assert redaction_service.enabled is True  # Assuming default config
        # Assuming default config
        assert redaction_service.placeholder == "[REDACTED]"
        assert redaction_service.stats['texts_processed'] == 0

    @pytest.mark.asyncio
    async def test_redact_text_enabled(self, mock_detector):
        """Test text redaction when enabled."""
        service = PIIRedactionService(detector=mock_detector)
        service.enabled = True

        text = "Contact me at test@example.com or call 555-123-4567"
        result = await service.redact_text(text)

        assert isinstance(result, RedactionResult)
        assert result.original_text == text
        assert len(result.entities) == 2
        assert "test@example.com" not in result.redacted_text
        assert "555-123-4567" not in result.redacted_text
        assert "[REDACTED]" in result.redacted_text

    @pytest.mark.asyncio
    async def test_redact_text_disabled(self, mock_detector):
        """Test text redaction when disabled."""
        service = PIIRedactionService(detector=mock_detector)
        service.enabled = False

        text = "Contact me at test@example.com"
        result = await service.redact_text(text)

        assert result.original_text == text
        assert result.redacted_text == text  # Should be unchanged
        assert len(result.entities) == 0
        assert result.processing_time == 0.0

    @pytest.mark.asyncio
    async def test_redact_empty_text(self, redaction_service):
        """Test redaction of empty or whitespace text."""
        test_cases = ["", "   ", "\n\t"]

        for text in test_cases:
            result = await redaction_service.redact_text(text)
            assert result.original_text == text
            assert result.redacted_text == text
            assert len(result.entities) == 0

    @pytest.mark.asyncio
    async def test_redact_text_preserve_format(self, mock_detector):
        """Test text redaction with format preservation."""
        service = PIIRedactionService(detector=mock_detector)

        text = "Email: test@example.com, Phone: 555-123-4567"
        result = await service.redact_text(text, preserve_format=True)

        # Should preserve some formatting structure
        assert "@" in result.redacted_text  # Email format preserved
        assert "-" in result.redacted_text  # Phone format preserved

    @pytest.mark.asyncio
    async def test_redact_text_custom_placeholder(self, mock_detector):
        """Test text redaction with custom placeholder."""
        service = PIIRedactionService(detector=mock_detector)
        custom_placeholder = "[HIDDEN]"

        text = "Contact: test@example.com"
        result = await service.redact_text(text, custom_placeholder=custom_placeholder)

        assert custom_placeholder in result.redacted_text
        assert "[REDACTED]" not in result.redacted_text

    @pytest.mark.asyncio
    async def test_redact_batch(self, mock_detector):
        """Test batch redaction."""
        service = PIIRedactionService(detector=mock_detector)

        texts = [
            "Email: test1@example.com",
            "Phone: 555-123-4567",
            "Contact: test2@example.com and 555-987-6543"
        ]

        results = await service.redact_batch(texts)

        assert len(results) == 3
        assert all(isinstance(r, RedactionResult) for r in results)
        assert all(len(r.entities) > 0 for r in results)

    def test_create_format_preserving_placeholder(self, redaction_service):
        """Test format-preserving placeholder creation."""
        placeholder = "[REDACTED]"

        # Test email
        result = redaction_service._create_format_preserving_placeholder(
            "test@example.com", PIIType.EMAIL, placeholder
        )
        assert "@" in result
        assert ".com" in result

        # Test phone with dashes
        result = redaction_service._create_format_preserving_placeholder(
            "555-123-4567", PIIType.PHONE, placeholder
        )
        assert "-" in result

        # Test phone with dots
        result = redaction_service._create_format_preserving_placeholder(
            "555.123.4567", PIIType.PHONE, placeholder
        )
        assert "." in result

        # Test URL
        result = redaction_service._create_format_preserving_placeholder(
            "https://example.com", PIIType.URL, placeholder
        )
        assert "https://" in result
        assert ".com" in result

    def test_create_redaction_map(self, redaction_service):
        """Test redaction map creation."""
        entities = [
            PIIEntity(PIIType.EMAIL, "test@example.com", 0, 16,
                      0.95, replacement="[REDACTED]@[REDACTED].com"),
            PIIEntity(PIIType.PHONE, "555-123-4567", 20, 32, 0.90,
                      replacement="[REDACTED]-[REDACTED]-[REDACTED]")
        ]

        redaction_map = redaction_service._create_redaction_map(entities)

        assert len(redaction_map) == 2
        # Check that map contains original values and metadata
        for key, value in redaction_map.items():
            assert 'original' in value
            assert 'type' in value
            assert 'confidence' in value
            assert 'replacement' in value

    def test_update_stats(self, redaction_service):
        """Test statistics update."""
        entities = [
            PIIEntity(PIIType.EMAIL, "test@example.com", 0, 16, 0.95),
            PIIEntity(PIIType.PHONE, "555-123-4567", 20, 32, 0.90)
        ]

        initial_processed = redaction_service.stats['texts_processed']
        initial_redacted = redaction_service.stats['entities_redacted']

        redaction_service._update_stats(entities, 1.5)

        assert redaction_service.stats['texts_processed'] == initial_processed + 1
        assert redaction_service.stats['entities_redacted'] == initial_redacted + 2
        assert redaction_service.stats['total_processing_time'] == 1.5
        assert redaction_service.stats['redaction_by_type']['email'] == 1
        assert redaction_service.stats['redaction_by_type']['phone'] == 1

    def test_get_stats(self, redaction_service):
        """Test getting redaction statistics."""
        # Add some test data
        entities = [PIIEntity(PIIType.EMAIL, "test@example.com", 0, 16, 0.95)]
        redaction_service._update_stats(entities, 2.0)
        redaction_service._update_stats([], 1.0)  # No entities

        stats = redaction_service.get_stats()

        assert stats['texts_processed'] == 2
        assert stats['entities_redacted'] == 1
        assert stats['average_processing_time'] == 1.5
        assert stats['enabled'] == redaction_service.enabled
        assert stats['placeholder'] == redaction_service.placeholder

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, redaction_service):
        """Test health check when service is healthy."""
        health = await redaction_service.health_check()

        assert health['status'] == 'healthy'
        assert health['enabled'] == redaction_service.enabled
        assert health['test_successful'] is True
        # Should detect entities in test text
        assert health['entities_detected'] > 0
        assert 'stats' in health

    @pytest.mark.asyncio
    async def test_health_check_with_error(self, mock_detector):
        """Test health check when an error occurs."""
        mock_detector.detect.side_effect = Exception("Test error")
        service = PIIRedactionService(detector=mock_detector)

        health = await service.health_check()

        assert health['status'] == 'unhealthy'
        assert health['test_successful'] is False
        assert 'error' in health
        assert 'stats' in health

    @pytest.mark.asyncio
    async def test_redaction_with_real_detector(self):
        """Integration test with real PIIDetector."""
        service = PIIRedactionService()

        text = "Contact John Doe at john.doe@example.com or call 555-123-4567. SSN: 123-45-6789"
        result = await service.redact_text(text)

        assert result.original_text == text
        assert len(result.entities) > 0
        assert "john.doe@example.com" not in result.redacted_text
        assert "555-123-4567" not in result.redacted_text
        assert "123-45-6789" not in result.redacted_text
        assert result.processing_time > 0


if __name__ == "__main__":
    pytest.main([__file__])
