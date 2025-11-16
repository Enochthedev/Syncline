"""
PII Detection and Redaction Service

Detects and optionally redacts Personally Identifiable Information (PII) using Presidio:
- Email addresses
- Phone numbers
- Credit card numbers
- Social security numbers
- Names
- Addresses
- IP addresses
- Configurable confidence thresholds
- Optional redaction with custom placeholders
- Batch processing support
"""

import asyncio
import logging
from enum import Enum
from typing import Optional

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import settings
from db.models.message import Message

logger = logging.getLogger(__name__)


class PIIEntityType(str, Enum):
    """Types of PII entities that can be detected."""
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    PHONE_NUMBER = "PHONE_NUMBER"
    CREDIT_CARD = "CREDIT_CARD"
    CRYPTO = "CRYPTO"
    DATE_TIME = "DATE_TIME"
    IBAN_CODE = "IBAN_CODE"
    IP_ADDRESS = "IP_ADDRESS"
    NRP = "NRP"  # National Registry of Persons
    LOCATION = "LOCATION"
    PERSON = "PERSON"
    US_BANK_NUMBER = "US_BANK_NUMBER"
    US_DRIVER_LICENSE = "US_DRIVER_LICENSE"
    US_ITIN = "US_ITIN"  # Individual Taxpayer Identification Number
    US_PASSPORT = "US_PASSPORT"
    US_SSN = "US_SSN"  # Social Security Number
    UK_NHS = "UK_NHS"  # National Health Service number
    URL = "URL"
    MEDICAL_LICENSE = "MEDICAL_LICENSE"
    
    # Custom entity types
    ADDRESS = "ADDRESS"
    AGE = "AGE"


class DetectedPII:
    """
    Represents a detected PII entity.
    
    Attributes:
        text: Original PII text
        entity_type: Type of PII entity
        start_pos: Start position in text
        end_pos: End position in text
        confidence: Confidence score (0.0 to 1.0)
        recognition_metadata: Additional metadata from recognizer
    """
    
    def __init__(
        self,
        text: str,
        entity_type: str,
        start_pos: int,
        end_pos: int,
        confidence: float,
        recognition_metadata: Optional[dict] = None,
    ):
        self.text = text
        self.entity_type = entity_type
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.confidence = confidence
        self.recognition_metadata = recognition_metadata or {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "text": self.text,
            "entity_type": self.entity_type,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "confidence": self.confidence,
            "recognition_metadata": self.recognition_metadata,
        }


class PIIRedactionService:
    """
    Service for detecting and redacting PII in text.
    
    Uses Microsoft Presidio for:
    - PII detection with confidence scoring
    - Optional redaction with custom placeholders
    - Support for multiple entity types
    - Batch processing
    - Configurable thresholds
    """
    
    def __init__(
        self,
        confidence_threshold: Optional[float] = None,
        redaction_placeholder: Optional[str] = None,
        enabled: Optional[bool] = None,
        language: str = "en",
    ):
        """
        Initialize PII redaction service.
        
        Args:
            confidence_threshold: Minimum confidence for PII detection
            redaction_placeholder: Placeholder text for redacted PII
            enabled: Enable/disable PII redaction
            language: Language for NLP processing
        """
        self.confidence_threshold = confidence_threshold or settings.PII_CONFIDENCE_THRESHOLD
        self.redaction_placeholder = redaction_placeholder or settings.PII_REDACTION_PLACEHOLDER
        self.enabled = enabled if enabled is not None else settings.PII_REDACTION_ENABLED
        self.language = language
        
        # Initialize Presidio engines lazily
        self._analyzer: Optional[AnalyzerEngine] = None
        self._anonymizer: Optional[AnonymizerEngine] = None
        
        logger.info(
            f"Initialized PIIRedactionService with threshold={self.confidence_threshold}, "
            f"enabled={self.enabled}, language={self.language}"
        )
    
    def _get_analyzer(self) -> AnalyzerEngine:
        """
        Get or create Presidio analyzer engine.
        
        Returns:
            AnalyzerEngine instance
        """
        if self._analyzer is None:
            try:
                # Create NLP engine provider
                nlp_configuration = {
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": self.language, "model_name": "en_core_web_sm"}],
                }
                
                provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
                nlp_engine = provider.create_engine()
                
                # Create analyzer with NLP engine
                self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
                
                logger.info("Successfully initialized Presidio AnalyzerEngine")
            except Exception as e:
                logger.error(f"Failed to initialize Presidio AnalyzerEngine: {e}")
                # Create analyzer without NLP engine as fallback
                self._analyzer = AnalyzerEngine()
                logger.warning("Using Presidio AnalyzerEngine without NLP engine")
        
        return self._analyzer
    
    def _get_anonymizer(self) -> AnonymizerEngine:
        """
        Get or create Presidio anonymizer engine.
        
        Returns:
            AnonymizerEngine instance
        """
        if self._anonymizer is None:
            self._anonymizer = AnonymizerEngine()
            logger.info("Successfully initialized Presidio AnonymizerEngine")
        
        return self._anonymizer
    
    def detect_pii(
        self,
        text: str,
        entity_types: Optional[list[str]] = None,
        language: Optional[str] = None,
    ) -> list[DetectedPII]:
        """
        Detect PII entities in text.
        
        Args:
            text: Text to analyze
            entity_types: Specific entity types to detect (None = all)
            language: Language code (uses default if not specified)
            
        Returns:
            List of detected PII entities
        """
        if not text or not text.strip():
            return []
        
        if not self.enabled:
            logger.debug("PII detection is disabled")
            return []
        
        try:
            analyzer = self._get_analyzer()
            lang = language or self.language
            
            # Analyze text for PII
            results: list[RecognizerResult] = analyzer.analyze(
                text=text,
                language=lang,
                entities=entity_types,
                score_threshold=self.confidence_threshold,
            )
            
            # Convert to DetectedPII objects
            detected_pii = []
            for result in results:
                pii = DetectedPII(
                    text=text[result.start:result.end],
                    entity_type=result.entity_type,
                    start_pos=result.start,
                    end_pos=result.end,
                    confidence=result.score,
                    recognition_metadata={
                        "recognizer": result.recognition_metadata.get("recognizer_name", "unknown")
                        if result.recognition_metadata else "unknown",
                    }
                )
                detected_pii.append(pii)
            
            logger.debug(f"Detected {len(detected_pii)} PII entities in text")
            return detected_pii
            
        except Exception as e:
            logger.error(f"Failed to detect PII: {e}")
            return []
    
    def detect_pii_batch(
        self,
        texts: list[str],
        entity_types: Optional[list[str]] = None,
        language: Optional[str] = None,
    ) -> list[list[DetectedPII]]:
        """
        Detect PII entities in multiple texts.
        
        Args:
            texts: List of texts to analyze
            entity_types: Specific entity types to detect (None = all)
            language: Language code (uses default if not specified)
            
        Returns:
            List of PII entity lists (one per text)
        """
        if not texts:
            return []
        
        if not self.enabled:
            logger.debug("PII detection is disabled")
            return [[] for _ in texts]
        
        try:
            results = []
            for text in texts:
                detected = self.detect_pii(text, entity_types, language)
                results.append(detected)
            
            logger.info(f"Detected PII in {len(texts)} texts")
            return results
            
        except Exception as e:
            logger.error(f"Failed to detect PII in batch: {e}")
            return [[] for _ in texts]
    
    def redact_pii(
        self,
        text: str,
        entity_types: Optional[list[str]] = None,
        placeholder: Optional[str] = None,
        language: Optional[str] = None,
    ) -> tuple[str, list[DetectedPII]]:
        """
        Detect and redact PII in text.
        
        Args:
            text: Text to redact
            entity_types: Specific entity types to redact (None = all)
            placeholder: Custom placeholder (uses default if not specified)
            language: Language code (uses default if not specified)
            
        Returns:
            Tuple of (redacted_text, detected_pii_list)
        """
        if not text or not text.strip():
            return text, []
        
        if not self.enabled:
            logger.debug("PII redaction is disabled")
            return text, []
        
        try:
            analyzer = self._get_analyzer()
            anonymizer = self._get_anonymizer()
            lang = language or self.language
            redaction_text = placeholder or self.redaction_placeholder
            
            # Analyze text for PII
            analyzer_results = analyzer.analyze(
                text=text,
                language=lang,
                entities=entity_types,
                score_threshold=self.confidence_threshold,
            )
            
            if not analyzer_results:
                logger.debug("No PII detected for redaction")
                return text, []
            
            # Create operator config for redaction
            operators = {
                entity_type: OperatorConfig("replace", {"new_value": redaction_text})
                for entity_type in set(result.entity_type for result in analyzer_results)
            }
            
            # Anonymize text
            anonymized_result = anonymizer.anonymize(
                text=text,
                analyzer_results=analyzer_results,
                operators=operators,
            )
            
            # Convert results to DetectedPII objects
            detected_pii = []
            for result in analyzer_results:
                pii = DetectedPII(
                    text=text[result.start:result.end],
                    entity_type=result.entity_type,
                    start_pos=result.start,
                    end_pos=result.end,
                    confidence=result.score,
                    recognition_metadata={
                        "recognizer": result.recognition_metadata.get("recognizer_name", "unknown")
                        if result.recognition_metadata else "unknown",
                    }
                )
                detected_pii.append(pii)
            
            logger.debug(
                f"Redacted {len(detected_pii)} PII entities from text "
                f"(original length: {len(text)}, redacted length: {len(anonymized_result.text)})"
            )
            
            return anonymized_result.text, detected_pii
            
        except Exception as e:
            logger.error(f"Failed to redact PII: {e}")
            return text, []
    
    def redact_pii_batch(
        self,
        texts: list[str],
        entity_types: Optional[list[str]] = None,
        placeholder: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list[tuple[str, list[DetectedPII]]]:
        """
        Detect and redact PII in multiple texts.
        
        Args:
            texts: List of texts to redact
            entity_types: Specific entity types to redact (None = all)
            placeholder: Custom placeholder (uses default if not specified)
            language: Language code (uses default if not specified)
            
        Returns:
            List of (redacted_text, detected_pii_list) tuples
        """
        if not texts:
            return []
        
        if not self.enabled:
            logger.debug("PII redaction is disabled")
            return [(text, []) for text in texts]
        
        try:
            results = []
            for text in texts:
                redacted_text, detected_pii = self.redact_pii(
                    text, entity_types, placeholder, language
                )
                results.append((redacted_text, detected_pii))
            
            total_pii = sum(len(pii_list) for _, pii_list in results)
            logger.info(
                f"Redacted {total_pii} PII entities from {len(texts)} texts"
            )
            return results
            
        except Exception as e:
            logger.error(f"Failed to redact PII in batch: {e}")
            return [(text, []) for text in texts]
    
    async def detect_pii_in_message(
        self,
        message: Message,
        entity_types: Optional[list[str]] = None,
    ) -> list[DetectedPII]:
        """
        Detect PII in a message.
        
        Args:
            message: Message to analyze
            entity_types: Specific entity types to detect (None = all)
            
        Returns:
            List of detected PII entities
        """
        try:
            # Extract text from message
            text = self._extract_text_from_message(message)
            
            if not text:
                logger.warning(f"No text content in message {message.id}")
                return []
            
            # Detect PII
            detected_pii = self.detect_pii(text, entity_types)
            
            logger.info(
                f"Detected {len(detected_pii)} PII entities in message {message.id}"
            )
            return detected_pii
            
        except Exception as e:
            logger.error(f"Failed to detect PII in message {message.id}: {e}")
            return []
    
    async def redact_pii_in_message(
        self,
        message: Message,
        db: AsyncSession,
        entity_types: Optional[list[str]] = None,
        placeholder: Optional[str] = None,
        store_original: bool = True,
    ) -> tuple[str, list[DetectedPII]]:
        """
        Detect and redact PII in a message.
        
        Args:
            message: Message to redact
            db: Database session
            entity_types: Specific entity types to redact (None = all)
            placeholder: Custom placeholder (uses default if not specified)
            store_original: Store original text in metadata before redaction
            
        Returns:
            Tuple of (redacted_text, detected_pii_list)
        """
        try:
            # Extract text from message
            text = self._extract_text_from_message(message)
            
            if not text:
                logger.warning(f"No text content in message {message.id}")
                return text, []
            
            # Redact PII
            redacted_text, detected_pii = self.redact_pii(
                text, entity_types, placeholder
            )
            
            if detected_pii and store_original:
                # Store original text in metadata
                if message.message_metadata is None:
                    message.message_metadata = {}
                
                message.message_metadata["original_text_before_redaction"] = text
                message.message_metadata["pii_redacted"] = True
                message.message_metadata["pii_entities_count"] = len(detected_pii)
                
                # Update message content with redacted text
                if isinstance(message.content, dict):
                    message.content["text"] = redacted_text
                else:
                    message.content = redacted_text
                
                # Commit changes
                await db.commit()
                await db.refresh(message)
                
                logger.info(
                    f"Redacted {len(detected_pii)} PII entities in message {message.id}"
                )
            
            return redacted_text, detected_pii
            
        except Exception as e:
            logger.error(f"Failed to redact PII in message {message.id}: {e}")
            await db.rollback()
            return text, []
    
    async def detect_pii_in_messages_batch(
        self,
        messages: list[Message],
        entity_types: Optional[list[str]] = None,
    ) -> list[list[DetectedPII]]:
        """
        Detect PII in multiple messages.
        
        Args:
            messages: List of messages to analyze
            entity_types: Specific entity types to detect (None = all)
            
        Returns:
            List of PII entity lists (one per message)
        """
        try:
            # Extract texts from messages
            texts = [self._extract_text_from_message(msg) for msg in messages]
            
            # Filter out empty texts
            valid_indices = [i for i, text in enumerate(texts) if text]
            valid_texts = [texts[i] for i in valid_indices]
            
            if not valid_texts:
                logger.warning("No valid texts to analyze for PII")
                return [[] for _ in messages]
            
            # Detect PII in batch
            detected_batch = self.detect_pii_batch(valid_texts, entity_types)
            
            # Map results back to original messages
            results = [[] for _ in messages]
            for i, detected in zip(valid_indices, detected_batch):
                results[i] = detected
            
            total_pii = sum(len(pii_list) for pii_list in results)
            logger.info(
                f"Detected {total_pii} PII entities in {len(messages)} messages"
            )
            return results
            
        except Exception as e:
            logger.error(f"Failed to detect PII in messages batch: {e}")
            return [[] for _ in messages]
    
    def _extract_text_from_message(self, message: Message) -> str:
        """
        Extract text content from message for PII detection.
        
        Args:
            message: Message object
            
        Returns:
            Text content
        """
        try:
            content = message.content
            
            # Try to get text content
            if isinstance(content, dict):
                text = content.get("text", "")
                
                # If no plain text, try HTML (strip tags)
                if not text:
                    html = content.get("html", "")
                    if html:
                        # Simple HTML tag removal
                        import re
                        text = re.sub(r'<[^>]+>', '', html)
                
                return text.strip()
            
            # If content is a string, use it directly
            if isinstance(content, str):
                return content.strip()
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to extract text from message {message.id}: {e}")
            return ""
    
    def get_supported_entity_types(self) -> list[str]:
        """
        Get list of supported PII entity types.
        
        Returns:
            List of entity type names
        """
        try:
            analyzer = self._get_analyzer()
            return analyzer.get_supported_entities()
        except Exception as e:
            logger.error(f"Failed to get supported entity types: {e}")
            return []
    
    def health_check(self) -> bool:
        """
        Check health of PII redaction service.
        
        Returns:
            True if healthy
        """
        try:
            # Try to initialize engines
            analyzer = self._get_analyzer()
            anonymizer = self._get_anonymizer()
            
            # Test with simple text
            test_text = "My email is test@example.com"
            results = analyzer.analyze(
                text=test_text,
                language=self.language,
                score_threshold=self.confidence_threshold,
            )
            
            logger.debug("PII redaction service health check passed")
            return True
            
        except Exception as e:
            logger.error(f"PII redaction service health check failed: {e}")
            return False


# Global service instance
_pii_redaction_service: Optional[PIIRedactionService] = None


def get_pii_redaction_service(
    confidence_threshold: Optional[float] = None,
    redaction_placeholder: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> PIIRedactionService:
    """
    Get the global PII redaction service instance.
    
    Args:
        confidence_threshold: Minimum confidence for PII detection
        redaction_placeholder: Placeholder text for redacted PII
        enabled: Enable/disable PII redaction
    
    Returns:
        PII redaction service
    """
    global _pii_redaction_service
    
    if _pii_redaction_service is None:
        _pii_redaction_service = PIIRedactionService(
            confidence_threshold=confidence_threshold,
            redaction_placeholder=redaction_placeholder,
            enabled=enabled,
        )
    
    return _pii_redaction_service


__all__ = [
    "PIIRedactionService",
    "PIIEntityType",
    "DetectedPII",
    "get_pii_redaction_service",
]
