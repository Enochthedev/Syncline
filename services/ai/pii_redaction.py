"""
PII redaction service for privacy-preserving AI processing.

This service identifies and redacts personally identifiable information (PII)
from text content before it's processed by AI models, ensuring privacy compliance.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import hashlib

from config.config import settings

logger = logging.getLogger(__name__)


class PIIType(str, Enum):
    """Types of PII that can be detected and redacted."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    URL = "url"
    PERSON_NAME = "person_name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    CUSTOM = "custom"


@dataclass
class PIIEntity:
    """Detected PII entity."""
    type: PIIType
    text: str
    start: int
    end: int
    confidence: float
    replacement: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RedactionResult:
    """Result of PII redaction process."""
    original_text: str
    redacted_text: str
    entities: List[PIIEntity]
    redaction_map: Dict[str, str] = field(default_factory=dict)
    processing_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


class PIIRedactionError(Exception):
    """Base exception for PII redaction errors."""
    pass


class PIIDetector:
    """PII detection using regex patterns and rules."""

    def __init__(self):
        """Initialize PII detector with patterns."""
        self.patterns = self._build_patterns()
        self.confidence_threshold = settings.PII_CONFIDENCE_THRESHOLD

    def _build_patterns(self) -> Dict[PIIType, List[Tuple[re.Pattern, float]]]:
        """Build regex patterns for PII detection."""
        patterns = {}

        # Email patterns
        patterns[PIIType.EMAIL] = [
            (re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), 0.95),
        ]

        # Phone patterns (various formats)
        patterns[PIIType.PHONE] = [
            # US phone numbers
            (re.compile(
                r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'), 0.90),
            # International format
            (re.compile(r'\b\+[1-9]\d{1,14}\b'), 0.85),
            # Generic phone pattern
            (re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'), 0.80),
        ]

        # SSN patterns
        patterns[PIIType.SSN] = [
            (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), 0.95),
            (re.compile(r'\b\d{3}\s\d{2}\s\d{4}\b'), 0.90),
            # Lower confidence for 9 digits (below threshold)
            (re.compile(r'\b\d{9}\b'), 0.65),
        ]

        # Credit card patterns
        patterns[PIIType.CREDIT_CARD] = [
            # Visa, MasterCard, etc. (without word boundaries for hyphenated numbers)
            (re.compile(
                r'(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})'), 0.90),
            # Generic 16-digit pattern with separators
            (re.compile(r'\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}'), 0.85),
            # Generic 16-digit pattern without separators
            (re.compile(r'\b\d{16}\b'), 0.80),
        ]

        # IP address patterns
        patterns[PIIType.IP_ADDRESS] = [
            # IPv4
            (re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'), 0.85),
            # IPv6 (simplified)
            (re.compile(
                r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'), 0.90),
        ]

        # URL patterns
        patterns[PIIType.URL] = [
            (re.compile(
                r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'), 0.95),
            (re.compile(
                r'www\.(?:[-\w.])+\.(?:[a-zA-Z]{2,})(?:/(?:[\w/_.])*)?'), 0.85),
        ]

        # Date of birth patterns
        patterns[PIIType.DATE_OF_BIRTH] = [
            (re.compile(
                r'\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12][0-9]|3[01])/(?:19|20)\d{2}\b'), 0.80),
            (re.compile(
                r'\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])\b'), 0.85),
        ]

        return patterns

    def detect(self, text: str) -> List[PIIEntity]:
        """Detect PII entities in text."""
        entities = []

        for pii_type, pattern_list in self.patterns.items():
            for pattern, confidence in pattern_list:
                for match in pattern.finditer(text):
                    if confidence >= self.confidence_threshold:
                        entity = PIIEntity(
                            type=pii_type,
                            text=match.group(),
                            start=match.start(),
                            end=match.end(),
                            confidence=confidence,
                            metadata={'pattern_used': pattern.pattern}
                        )
                        entities.append(entity)

        # Remove overlapping entities (keep highest confidence)
        entities = self._remove_overlaps(entities)

        return entities

    def _remove_overlaps(self, entities: List[PIIEntity]) -> List[PIIEntity]:
        """Remove overlapping entities, keeping the highest confidence ones."""
        if not entities:
            return entities

        # Sort by start position, then by confidence (descending)
        entities.sort(key=lambda e: (e.start, -e.confidence))

        filtered = []
        for entity in entities:
            # Check if this entity overlaps with any already accepted entity
            overlaps = False
            for accepted in filtered:
                if (entity.start < accepted.end and entity.end > accepted.start):
                    overlaps = True
                    break

            if not overlaps:
                filtered.append(entity)

        return filtered


class PIIRedactionService:
    """
    Service for detecting and redacting PII from text content.

    Provides privacy-preserving text processing for AI workflows.
    """

    def __init__(self, detector: Optional[PIIDetector] = None):
        """Initialize the PII redaction service."""
        self.detector = detector or PIIDetector()
        self.enabled = settings.PII_REDACTION_ENABLED
        self.placeholder = settings.PII_REDACTION_PLACEHOLDER

        # Statistics
        self.stats = {
            'texts_processed': 0,
            'entities_redacted': 0,
            'redaction_by_type': {},
            'total_processing_time': 0.0
        }

        logger.info(
            f"PII redaction service initialized (enabled: {self.enabled})")

    async def redact_text(
        self,
        text: str,
        preserve_format: bool = True,
        custom_placeholder: Optional[str] = None
    ) -> RedactionResult:
        """
        Redact PII from text content.

        Args:
            text: Text to redact
            preserve_format: Whether to preserve original text formatting
            custom_placeholder: Custom placeholder for redacted content

        Returns:
            RedactionResult with original text, redacted text, and detected entities
        """
        start_time = datetime.utcnow()

        if not self.enabled:
            # Return original text if redaction is disabled
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                entities=[],
                processing_time=0.0
            )

        if not text or not text.strip():
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                entities=[],
                processing_time=0.0
            )

        try:
            # Detect PII entities
            entities = self.detector.detect(text)

            # Generate redacted text
            redacted_text = self._apply_redactions(
                text, entities, custom_placeholder or self.placeholder, preserve_format
            )

            # Create redaction map for potential restoration
            redaction_map = self._create_redaction_map(entities)

            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_stats(entities, processing_time)

            result = RedactionResult(
                original_text=text,
                redacted_text=redacted_text,
                entities=entities,
                redaction_map=redaction_map,
                processing_time=processing_time
            )

            logger.debug(
                f"Redacted {len(entities)} PII entities from text "
                f"({len(text)} -> {len(redacted_text)} chars) in {processing_time:.3f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Error during PII redaction: {e}")
            raise PIIRedactionError(f"PII redaction failed: {e}")

    async def redact_batch(
        self,
        texts: List[str],
        preserve_format: bool = True,
        custom_placeholder: Optional[str] = None
    ) -> List[RedactionResult]:
        """Redact PII from a batch of texts."""
        results = []

        for text in texts:
            result = await self.redact_text(text, preserve_format, custom_placeholder)
            results.append(result)

        return results

    def _apply_redactions(
        self,
        text: str,
        entities: List[PIIEntity],
        placeholder: str,
        preserve_format: bool
    ) -> str:
        """Apply redactions to text."""
        if not entities:
            return text

        # Sort entities by start position (descending) to avoid index shifting
        entities_sorted = sorted(entities, key=lambda e: e.start, reverse=True)

        redacted_text = text

        for entity in entities_sorted:
            if preserve_format:
                # Create placeholder that preserves length and some structure
                replacement = self._create_format_preserving_placeholder(
                    entity.text, entity.type, placeholder
                )
            else:
                replacement = f"{placeholder}_{entity.type.value.upper()}"

            entity.replacement = replacement
            redacted_text = (
                redacted_text[:entity.start] +
                replacement +
                redacted_text[entity.end:]
            )

        return redacted_text

    def _create_format_preserving_placeholder(
        self,
        original: str,
        pii_type: PIIType,
        placeholder: str
    ) -> str:
        """Create a placeholder that preserves some formatting characteristics."""
        if pii_type == PIIType.EMAIL:
            return f"{placeholder}@{placeholder}.com"
        elif pii_type == PIIType.PHONE:
            if '-' in original:
                return f"{placeholder}-{placeholder}-{placeholder}"
            elif '.' in original:
                return f"{placeholder}.{placeholder}.{placeholder}"
            elif ' ' in original:
                return f"{placeholder} {placeholder} {placeholder}"
            else:
                return placeholder
        elif pii_type == PIIType.URL:
            return f"https://{placeholder}.com"
        elif pii_type == PIIType.SSN:
            if '-' in original:
                return f"{placeholder}-{placeholder}-{placeholder}"
            elif ' ' in original:
                return f"{placeholder} {placeholder} {placeholder}"
            else:
                return placeholder
        else:
            # For other types, try to preserve length
            if len(original) > len(placeholder):
                return placeholder + "X" * (len(original) - len(placeholder))
            else:
                return placeholder[:len(original)]

    def _create_redaction_map(self, entities: List[PIIEntity]) -> Dict[str, str]:
        """Create a mapping of redacted content to original content."""
        redaction_map = {}

        for entity in entities:
            # Create a hash-based key for the redacted content
            key = hashlib.sha256(entity.text.encode()).hexdigest()[:16]
            redaction_map[key] = {
                'original': entity.text,
                'type': entity.type.value,
                'confidence': entity.confidence,
                'replacement': entity.replacement
            }

        return redaction_map

    def _update_stats(self, entities: List[PIIEntity], processing_time: float) -> None:
        """Update processing statistics."""
        self.stats['texts_processed'] += 1
        self.stats['entities_redacted'] += len(entities)
        self.stats['total_processing_time'] += processing_time

        # Update per-type statistics
        for entity in entities:
            pii_type = entity.type.value
            if pii_type not in self.stats['redaction_by_type']:
                self.stats['redaction_by_type'][pii_type] = 0
            self.stats['redaction_by_type'][pii_type] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get redaction statistics."""
        return {
            **self.stats,
            'average_processing_time': (
                self.stats['total_processing_time'] /
                self.stats['texts_processed']
                if self.stats['texts_processed'] > 0 else 0.0
            ),
            'enabled': self.enabled,
            'placeholder': self.placeholder
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the PII redaction service."""
        try:
            # Test redaction with sample text
            test_text = "Contact John Doe at john.doe@example.com or call 555-123-4567"
            result = await self.redact_text(test_text)

            return {
                'status': 'healthy',
                'enabled': self.enabled,
                'test_successful': len(result.entities) > 0,
                'entities_detected': len(result.entities),
                'stats': self.get_stats()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'enabled': self.enabled,
                'error': str(e),
                'test_successful': False,
                'stats': self.get_stats()
            }


# Global PII redaction service instance
pii_redaction_service = PIIRedactionService()


async def get_pii_redaction_service() -> PIIRedactionService:
    """Get the global PII redaction service instance."""
    return pii_redaction_service
