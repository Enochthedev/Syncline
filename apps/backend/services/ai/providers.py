"""
LLM Provider Abstraction

Provides a unified interface for different LLM providers:
- Ollama (local-first, default)
- OpenAI (cloud fallback)
- Anthropic (cloud fallback)

Supports model management, text generation, and embeddings.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

import aiohttp
from pydantic import BaseModel, Field

from config.config import settings

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Types of AI models."""
    CHAT = "chat"
    EMBEDDING = "embedding"
    COMPLETION = "completion"


class ModelInfo(BaseModel):
    """Information about an AI model."""
    name: str
    type: ModelType
    size: Optional[str] = None
    parameters: Optional[str] = None
    quantization: Optional[str] = None
    family: Optional[str] = None
    available: bool = True


class GenerationConfig(BaseModel):
    """Configuration for text generation."""
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=0)
    stop: Optional[list[str]] = None
    stream: bool = False


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Defines the interface that all LLM providers must implement.
    """
    
    def __init__(self, base_url: str, timeout: int = 120, max_retries: int = 3):
        """
        Initialize the LLM provider.
        
        Args:
            base_url: Base URL for the provider API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Input prompt
            model: Model name (uses default if not specified)
            config: Generation configuration
            
        Returns:
            Generated text
        """
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> str:
        """
        Generate a chat response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (uses default if not specified)
            config: Generation configuration
            
        Returns:
            Generated response
        """
        pass
    
    @abstractmethod
    async def embed(
        self,
        text: str | list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """
        Generate embeddings for text.
        
        Args:
            text: Single text or list of texts
            model: Embedding model name (uses default if not specified)
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """
        List available models.
        
        Returns:
            List of model information
        """
        pass
    
    @abstractmethod
    async def pull_model(self, model: str) -> bool:
        """
        Download/pull a model.
        
        Args:
            model: Model name to download
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible.
        
        Returns:
            True if healthy
        """
        pass


class OllamaProvider(LLMProvider):
    """
    Ollama LLM provider implementation.
    
    Provides local-first AI inference using Ollama.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        default_chat_model: Optional[str] = None,
        default_embedding_model: Optional[str] = None,
    ):
        """
        Initialize Ollama provider.
        
        Args:
            base_url: Ollama API base URL
            timeout: Request timeout
            max_retries: Max retry attempts
            default_chat_model: Default chat model
            default_embedding_model: Default embedding model
        """
        super().__init__(
            base_url=base_url or settings.OLLAMA_BASE_URL,
            timeout=timeout or settings.OLLAMA_TIMEOUT,
            max_retries=max_retries or settings.OLLAMA_MAX_RETRIES,
        )
        self.default_chat_model = default_chat_model or settings.DEFAULT_CHAT_MODEL
        self.default_embedding_model = (
            default_embedding_model or settings.DEFAULT_EMBEDDING_MODEL
        )
        logger.info(
            f"Initialized Ollama provider at {self.base_url} "
            f"(chat: {self.default_chat_model}, embed: {self.default_embedding_model})"
        )
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        stream: bool = False,
    ) -> Any:
        """
        Make an HTTP request to Ollama API with retries.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            json_data: JSON request body
            stream: Whether to stream the response
            
        Returns:
            Response data
        """
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.max_retries):
            try:
                async with session.request(
                    method,
                    url,
                    json=json_data,
                ) as response:
                    response.raise_for_status()
                    
                    if stream:
                        # For streaming responses, return the response object
                        return response
                    
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Ollama request failed after {self.max_retries} attempts: {e}")
                    raise
                
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.warning(f"Ollama request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
        
        raise RuntimeError("Max retries exceeded")
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> str:
        """Generate text from a prompt using Ollama."""
        model = model or self.default_chat_model
        config = config or GenerationConfig()
        
        request_data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
            }
        }
        
        if config.stop:
            request_data["options"]["stop"] = config.stop
        
        logger.debug(f"Generating text with model {model}")
        response = await self._request("POST", "/api/generate", request_data)
        
        return response.get("response", "")
    
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> str:
        """Generate a chat response using Ollama."""
        model = model or self.default_chat_model
        config = config or GenerationConfig()
        
        request_data = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
            }
        }
        
        if config.stop:
            request_data["options"]["stop"] = config.stop
        
        logger.debug(f"Generating chat response with model {model}")
        response = await self._request("POST", "/api/chat", request_data)
        
        message = response.get("message", {})
        return message.get("content", "")
    
    async def embed(
        self,
        text: str | list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """Generate embeddings using Ollama."""
        model = model or self.default_embedding_model
        
        # Convert single text to list
        texts = [text] if isinstance(text, str) else text
        
        embeddings = []
        for txt in texts:
            request_data = {
                "model": model,
                "prompt": txt,
            }
            
            logger.debug(f"Generating embedding with model {model}")
            response = await self._request("POST", "/api/embeddings", request_data)
            
            embedding = response.get("embedding", [])
            embeddings.append(embedding)
        
        return embeddings
    
    async def list_models(self) -> list[ModelInfo]:
        """List available Ollama models."""
        try:
            response = await self._request("GET", "/api/tags")
            models_data = response.get("models", [])
            
            models = []
            for model_data in models_data:
                model_info = ModelInfo(
                    name=model_data.get("name", ""),
                    type=ModelType.CHAT,  # Default to chat, could be refined
                    size=model_data.get("size"),
                    parameters=model_data.get("details", {}).get("parameter_size"),
                    quantization=model_data.get("details", {}).get("quantization_level"),
                    family=model_data.get("details", {}).get("family"),
                    available=True,
                )
                models.append(model_info)
            
            logger.info(f"Found {len(models)} Ollama models")
            return models
            
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []
    
    async def pull_model(self, model: str) -> bool:
        """
        Pull/download an Ollama model.
        
        Note: This is a long-running operation that streams progress.
        """
        try:
            request_data = {"name": model, "stream": False}
            
            logger.info(f"Pulling Ollama model: {model}")
            await self._request("POST", "/api/pull", request_data)
            
            logger.info(f"Successfully pulled model: {model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if Ollama is accessible."""
        try:
            # Try to list models as a health check
            await self._request("GET", "/api/tags")
            logger.debug("Ollama health check passed")
            return True
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False


# Factory function to get the appropriate provider
def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """
    Get an LLM provider instance.
    
    Args:
        provider_name: Provider name ('ollama', 'openai', 'anthropic')
                      Uses DEFAULT_LLM_PROVIDER from settings if not specified
    
    Returns:
        LLM provider instance
    
    Raises:
        ValueError: If provider name is not supported
    """
    provider_name = provider_name or settings.DEFAULT_LLM_PROVIDER
    provider_name = provider_name.lower()
    
    if provider_name == "ollama":
        return OllamaProvider()
    elif provider_name == "openai":
        # TODO: Implement OpenAI provider
        raise NotImplementedError("OpenAI provider not yet implemented")
    elif provider_name == "anthropic":
        # TODO: Implement Anthropic provider
        raise NotImplementedError("Anthropic provider not yet implemented")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")


__all__ = [
    "LLMProvider",
    "OllamaProvider",
    "ModelType",
    "ModelInfo",
    "GenerationConfig",
    "get_llm_provider",
]
