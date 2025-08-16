"""
Base AI agent class with common processing patterns.

This module provides the foundation for all AI agents in the MESH system,
including common patterns for LLM interaction, error handling, and processing workflows.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from contextlib import asynccontextmanager

from config.config import settings

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class ProcessingStatus(str, Enum):
    """AI processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class AIRequest:
    """AI processing request."""
    id: str
    prompt: str
    model: str
    provider: AIProvider
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    max_retries: int = 3
    timeout: int = 30


@dataclass
class AIResponse:
    """AI processing response."""
    request_id: str
    content: str
    status: ProcessingStatus
    provider: AIProvider
    model: str
    usage: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class AIProcessingError(Exception):
    """Base exception for AI processing errors."""
    pass


class AIProviderError(AIProcessingError):
    """Error from AI provider."""
    pass


class AITimeoutError(AIProcessingError):
    """AI processing timeout."""
    pass


class AIRateLimitError(AIProcessingError):
    """AI provider rate limit exceeded."""
    pass


class BaseAIAgent(ABC):
    """
    Base class for all AI agents in the MESH system.

    Provides common functionality for:
    - LLM interaction patterns
    - Error handling and retries
    - Rate limiting
    - Logging and monitoring
    - Processing workflows
    """

    def __init__(
        self,
        name: str,
        provider: AIProvider = None,
        model: str = None,
        max_retries: int = None,
        timeout: int = None
    ):
        """Initialize the AI agent."""
        self.name = name
        self.provider = provider or AIProvider(settings.DEFAULT_LLM_PROVIDER)
        self.model = model or settings.DEFAULT_CHAT_MODEL
        self.max_retries = max_retries or settings.AI_MAX_RETRIES
        self.timeout = timeout or settings.AI_REQUEST_TIMEOUT

        # Processing statistics
        self.stats = {
            'requests_processed': 0,
            'requests_failed': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0
        }

        logger.info(
            f"Initialized AI agent '{name}' with provider {self.provider} and model {self.model}")

    @abstractmethod
    async def process(self, input_data: Any, **kwargs) -> Any:
        """
        Process input data using AI.

        This method must be implemented by subclasses to define
        the specific processing logic for each agent type.
        """
        pass

    async def process_with_retry(
        self,
        input_data: Any,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Process input with automatic retry logic.

        Args:
            input_data: Data to process
            max_retries: Override default max retries
            **kwargs: Additional arguments for processing

        Returns:
            Processing result

        Raises:
            AIProcessingError: If processing fails after all retries
        """
        max_retries = max_retries or self.max_retries
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                start_time = datetime.utcnow()
                result = await self.process(input_data, **kwargs)

                # Update statistics
                processing_time = (datetime.utcnow() -
                                   start_time).total_seconds()
                self._update_stats(processing_time, success=True)

                logger.debug(
                    f"AI agent '{self.name}' processed request successfully "
                    f"in {processing_time:.2f}s (attempt {attempt + 1})"
                )

                return result

            except AIRateLimitError as e:
                last_error = e
                if attempt < max_retries:
                    # Exponential backoff for rate limits
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Rate limit hit for agent '{self.name}', "
                        f"waiting {wait_time}s before retry {attempt + 1}/{max_retries}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    break

            except AITimeoutError as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        f"Timeout for agent '{self.name}', "
                        f"retry {attempt + 1}/{max_retries}"
                    )
                    continue
                else:
                    break

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        f"Error in agent '{self.name}': {e}, "
                        f"retry {attempt + 1}/{max_retries}"
                    )
                    await asyncio.sleep(1)  # Brief pause before retry
                    continue
                else:
                    break

        # All retries exhausted
        self._update_stats(0, success=False)
        logger.error(
            f"AI agent '{self.name}' failed after {max_retries + 1} attempts: {last_error}"
        )
        raise AIProcessingError(
            f"Processing failed after {max_retries + 1} attempts: {last_error}")

    async def process_batch(
        self,
        input_batch: List[Any],
        batch_size: Optional[int] = None,
        **kwargs
    ) -> List[Any]:
        """
        Process a batch of inputs with concurrency control.

        Args:
            input_batch: List of inputs to process
            batch_size: Maximum concurrent processing (default from settings)
            **kwargs: Additional arguments for processing

        Returns:
            List of processing results in the same order as inputs
        """
        batch_size = batch_size or settings.AI_BATCH_SIZE
        results = []

        logger.info(
            f"Processing batch of {len(input_batch)} items with "
            f"batch size {batch_size} using agent '{self.name}'"
        )

        # Process in chunks to control concurrency
        for i in range(0, len(input_batch), batch_size):
            chunk = input_batch[i:i + batch_size]

            # Process chunk concurrently
            tasks = [
                self.process_with_retry(item, **kwargs)
                for item in chunk
            ]

            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(chunk_results)

            logger.debug(
                f"Processed chunk {i//batch_size + 1}/{(len(input_batch) + batch_size - 1)//batch_size}"
            )

        return results

    def _update_stats(self, processing_time: float, success: bool) -> None:
        """Update processing statistics."""
        if success:
            self.stats['requests_processed'] += 1
            self.stats['total_processing_time'] += processing_time

            # Update average
            if self.stats['requests_processed'] > 0:
                self.stats['average_processing_time'] = (
                    self.stats['total_processing_time'] /
                    self.stats['requests_processed']
                )
        else:
            self.stats['requests_failed'] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            **self.stats,
            'success_rate': (
                self.stats['requests_processed'] /
                (self.stats['requests_processed'] +
                 self.stats['requests_failed'])
                if (self.stats['requests_processed'] + self.stats['requests_failed']) > 0
                else 0.0
            ),
            'agent_name': self.name,
            'provider': self.provider.value,
            'model': self.model
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the AI agent."""
        try:
            # Simple test request
            test_result = await self.process("Health check test", timeout=5)

            return {
                'status': 'healthy',
                'agent_name': self.name,
                'provider': self.provider.value,
                'model': self.model,
                'stats': self.get_stats(),
                'test_successful': True
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'agent_name': self.name,
                'provider': self.provider.value,
                'model': self.model,
                'error': str(e),
                'stats': self.get_stats(),
                'test_successful': False
            }

    @abstractmethod
    def _build_prompt(self, input_data: Any, **kwargs) -> str:
        """
        Build the prompt for the AI model.

        This method must be implemented by subclasses to define
        how to construct prompts for their specific use case.
        """
        pass

    def _validate_input(self, input_data: Any) -> bool:
        """
        Validate input data before processing.

        Override in subclasses for specific validation logic.
        """
        return input_data is not None

    def _post_process_response(self, response: str, input_data: Any) -> Any:
        """
        Post-process the AI response.

        Override in subclasses for specific post-processing logic.
        """
        return response.strip()


class AIAgentRegistry:
    """Registry for managing AI agents."""

    def __init__(self):
        self._agents: Dict[str, BaseAIAgent] = {}

    def register(self, agent: BaseAIAgent) -> None:
        """Register an AI agent."""
        self._agents[agent.name] = agent
        logger.info(f"Registered AI agent: {agent.name}")

    def get(self, name: str) -> Optional[BaseAIAgent]:
        """Get an AI agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    async def health_check_all(self) -> Dict[str, Any]:
        """Perform health check on all registered agents."""
        results = {}

        for name, agent in self._agents.items():
            try:
                results[name] = await agent.health_check()
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'error': str(e),
                    'agent_name': name
                }

        return {
            'overall_status': 'healthy' if all(
                r.get('status') == 'healthy' for r in results.values()
            ) else 'degraded',
            'agent_count': len(self._agents),
            'agents': results
        }


# Global agent registry
agent_registry = AIAgentRegistry()


def get_agent_registry() -> AIAgentRegistry:
    """Get the global agent registry."""
    return agent_registry
