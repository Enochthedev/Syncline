"""
Local-first AI processing engine for the MESH system.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import uuid

from config.config import settings
from services.message_schema import NormalizedMessage
from .providers import get_provider
from .detector import get_ai_detector, auto_configure_ai
from .pii_redaction import get_pii_redaction_service

logger = logging.getLogger(__name__)


class ProcessingType(str, Enum):
    """Types of AI processing."""
    SUMMARIZATION = "summarization"
    ENTITY_EXTRACTION = "entity_extraction"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    CUSTOM = "custom"


@dataclass
class ProcessingResult:
    """AI processing result."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: ProcessingType = ProcessingType.CUSTOM
    input_text: str = ""
    result: Any = None
    processing_time: float = 0.0
    model_used: str = ""
    provider_used: str = ""
    pii_redacted: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class AIProcessingEngine:
    """
    Local-first AI processing engine.

    Designed to work primarily with local models (Ollama) while supporting
    cloud providers as fallback options.
    """

    def __init__(self):
        """Initialize the AI processing engine."""
        self.provider_name = settings.DEFAULT_LLM_PROVIDER
        self.chat_model = settings.DEFAULT_CHAT_MODEL
        self.embedding_model = settings.DEFAULT_EMBEDDING_MODEL

        self.provider = None
        self.stats = {
            'requests_processed': 0,
            'requests_failed': 0,
            'total_processing_time': 0.0,
            'processing_by_type': {},
            'models_used': {}
        }

        logger.info(
            f"AI Engine initialized with provider: {self.provider_name}")

    async def initialize(self) -> Dict[str, Any]:
        """Initialize the AI provider with smart detection and fallback."""
        logger.info("Initializing AI engine with smart provider detection...")

        try:
            # Auto-configure based on available providers
            config_result = await auto_configure_ai()
            setup_info = config_result["setup_info"]

            # Update our configuration with detected best options
            config_updates = config_result["config_updates"]
            if "DEFAULT_LLM_PROVIDER" in config_updates:
                self.provider_name = config_updates["DEFAULT_LLM_PROVIDER"]
            if "DEFAULT_CHAT_MODEL" in config_updates:
                self.chat_model = config_updates["DEFAULT_CHAT_MODEL"]
                logger.info(f"Using available chat model: {self.chat_model}")
            if "DEFAULT_EMBEDDING_MODEL" in config_updates:
                self.embedding_model = config_updates["DEFAULT_EMBEDDING_MODEL"]
                logger.info(
                    f"Using available embedding model: {self.embedding_model}")

            # Initialize the best available provider
            detector = await get_ai_detector()
            chat_provider_status = await detector.get_best_provider("chat")

            if not chat_provider_status:
                return {
                    "status": "error",
                    "message": "No AI providers available",
                    "setup_info": setup_info
                }

            # Initialize the provider
            self.provider_name = chat_provider_status.name
            try:
                self.provider = get_provider(self.provider_name)
            except Exception as e:
                logger.error(
                    f"Failed to initialize provider {self.provider_name}: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to initialize {self.provider_name}: {e}",
                    "setup_info": setup_info
                }

            logger.info(
                f"AI engine initialized with {self.provider_name} provider")

            return {
                "status": "ready",
                "message": f"AI engine ready with {self.provider_name}",
                "provider": self.provider_name,
                "models": {
                    "chat": self.chat_model,
                    "embedding": self.embedding_model
                },
                "setup_info": setup_info,
                "providers_detected": len(config_result["providers"])
            }

        except Exception as e:
            logger.error(f"Failed to initialize AI engine: {e}")
            return {
                "status": "error",
                "message": str(e),
                "setup_info": {"recommendations": ["Check AI provider setup"]}
            }

    async def process_text(
        self,
        text: str,
        processing_type: ProcessingType = ProcessingType.SUMMARIZATION,
        custom_prompt: Optional[str] = None,
        model: Optional[str] = None,
        redact_pii: bool = True
    ) -> ProcessingResult:
        """Process text with AI."""
        start_time = datetime.utcnow()
        result = ProcessingResult(
            type=processing_type,
            input_text=text,
            model_used=model or self.chat_model,
            provider_used=self.provider_name
        )

        try:
            # Initialize provider if needed
            if not self.provider:
                await self.initialize()
                if not self.provider:
                    raise Exception("AI provider not available")

            # Apply PII redaction if enabled
            processed_text = text
            if redact_pii:
                pii_service = await get_pii_redaction_service()
                redaction_result = await pii_service.redact_text(text)
                processed_text = redaction_result.redacted_text
                result.pii_redacted = len(redaction_result.entities) > 0

            # Build prompt
            if custom_prompt:
                prompt = f"{custom_prompt}\n\nText to process:\n{processed_text}"
            else:
                prompt = self._build_prompt(processed_text, processing_type)

            # Generate AI response
            ai_response = await self.provider.generate_completion(
                prompt=prompt,
                model=result.model_used,
                max_tokens=settings.AI_MAX_TOKENS,
                temperature=settings.AI_TEMPERATURE
            )

            result.result = ai_response
            result.processing_time = (
                datetime.utcnow() - start_time).total_seconds()

            # Update stats
            self._update_stats(
                processing_type, result.model_used, result.processing_time, True)

            logger.debug(
                f"Processed text with {processing_type.value} in {result.processing_time:.2f}s")

        except Exception as e:
            result.error = str(e)
            result.processing_time = (
                datetime.utcnow() - start_time).total_seconds()
            self._update_stats(processing_type, result.model_used,
                               result.processing_time, False)
            logger.error(f"AI processing failed: {e}")

        return result

    async def process_message(
        self,
        message: NormalizedMessage,
        processing_types: List[ProcessingType] = None,
        **kwargs
    ) -> Dict[str, ProcessingResult]:
        """Process a normalized message with multiple AI processing types."""
        if not processing_types:
            processing_types = [ProcessingType.SUMMARIZATION]

        # Get message content
        content = message.content.get_primary_content()
        if not content:
            return {"error": ProcessingResult(error="No content to process")}

        results = {}

        for processing_type in processing_types:
            try:
                result = await self.process_text(
                    content, processing_type, **kwargs
                )

                # Add message context to metadata
                result.metadata.update({
                    'message_id': message.id,
                    'platform': message.platform.value,
                    'sender': message.sender.get_identifier(),
                    'timestamp': message.timestamp.isoformat()
                })

                results[processing_type.value] = result

            except Exception as e:
                results[processing_type.value] = ProcessingResult(
                    type=processing_type,
                    error=str(e),
                    metadata={'message_id': message.id}
                )

        return results

    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        redact_pii: bool = True
    ) -> ProcessingResult:
        """Generate embedding for text."""
        start_time = datetime.utcnow()
        result = ProcessingResult(
            type=ProcessingType.EMBEDDING,
            input_text=text,
            model_used=model or self.embedding_model,
            provider_used=self.provider_name
        )

        try:
            # Initialize provider if needed
            if not self.provider:
                await self.initialize()
                if not self.provider:
                    raise Exception("AI provider not available")

            # Apply PII redaction if enabled
            processed_text = text
            if redact_pii:
                pii_service = await get_pii_redaction_service()
                redaction_result = await pii_service.redact_text(text)
                processed_text = redaction_result.redacted_text
                result.pii_redacted = len(redaction_result.entities) > 0

            # Generate embedding
            embedding = await self.provider.generate_embedding(
                processed_text, result.model_used
            )

            result.result = {
                'embedding': embedding,
                'dimensions': len(embedding)
            }
            result.processing_time = (
                datetime.utcnow() - start_time).total_seconds()

            # Update stats
            self._update_stats(ProcessingType.EMBEDDING,
                               result.model_used, result.processing_time, True)

        except Exception as e:
            result.error = str(e)
            result.processing_time = (
                datetime.utcnow() - start_time).total_seconds()
            self._update_stats(ProcessingType.EMBEDDING,
                               result.model_used, result.processing_time, False)
            logger.error(f"Embedding generation failed: {e}")

        return result

    def _build_prompt(self, text: str, processing_type: ProcessingType) -> str:
        """Build prompt for different processing types."""
        prompts = {
            ProcessingType.SUMMARIZATION: f"""
Please provide a concise summary of the following text:

{text}

Summary:""",

            ProcessingType.ENTITY_EXTRACTION: f"""
Extract important entities (people, organizations, locations, dates, topics) from the following text.
Return the result as a JSON object with entity types as keys and lists of entities as values.

Text: {text}

Entities (JSON):""",

            ProcessingType.SENTIMENT_ANALYSIS: f"""
Analyze the sentiment of the following text. Classify it as positive, negative, or neutral.
Provide a brief explanation for your classification.

Text: {text}

Sentiment Analysis:""",

            ProcessingType.CLASSIFICATION: f"""
Classify the following text into one of these categories: business, personal, urgent, informational.
Provide the category and a brief explanation.

Text: {text}

Classification:"""
        }

        return prompts.get(processing_type, f"Analyze the following text:\n\n{text}\n\nAnalysis:")

    def _update_stats(self, processing_type: ProcessingType, model: str, processing_time: float, success: bool):
        """Update processing statistics."""
        if success:
            self.stats['requests_processed'] += 1
            self.stats['total_processing_time'] += processing_time
        else:
            self.stats['requests_failed'] += 1

        # Update per-type stats
        type_key = processing_type.value
        if type_key not in self.stats['processing_by_type']:
            self.stats['processing_by_type'][type_key] = {
                'processed': 0, 'failed': 0, 'total_time': 0.0}

        if success:
            self.stats['processing_by_type'][type_key]['processed'] += 1
            self.stats['processing_by_type'][type_key]['total_time'] += processing_time
        else:
            self.stats['processing_by_type'][type_key]['failed'] += 1

        # Update model usage stats
        if model not in self.stats['models_used']:
            self.stats['models_used'][model] = 0
        self.stats['models_used'][model] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        total_requests = self.stats['requests_processed'] + \
            self.stats['requests_failed']

        return {
            **self.stats,
            'success_rate': (
                self.stats['requests_processed'] / total_requests
                if total_requests > 0 else 0.0
            ),
            'average_processing_time': (
                self.stats['total_processing_time'] /
                self.stats['requests_processed']
                if self.stats['requests_processed'] > 0 else 0.0
            ),
            'provider': self.provider_name,
            'chat_model': self.chat_model,
            'embedding_model': self.embedding_model
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the AI processing engine."""
        try:
            # Test basic functionality
            test_result = await self.process_text(
                "This is a test message for health check",
                ProcessingType.SUMMARIZATION
            )

            return {
                'status': 'healthy' if not test_result.error else 'unhealthy',
                'provider': self.provider_name,
                'models': {
                    'chat': self.chat_model,
                    'embedding': self.embedding_model
                },
                'test_successful': test_result.error is None,
                'test_processing_time': test_result.processing_time,
                'stats': self.get_stats()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'provider': self.provider_name,
                'stats': self.get_stats()
            }

    async def close(self):
        """Close the AI provider connections."""
        if self.provider and hasattr(self.provider, 'close'):
            await self.provider.close()


# Global AI processing engine instance
_ai_engine = None


async def get_ai_processing_engine() -> AIProcessingEngine:
    """Get the global AI processing engine instance."""
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = AIProcessingEngine()
        await _ai_engine.initialize()
    return _ai_engine


# Alias for backward compatibility
get_ai_engine = get_ai_processing_engine
