"""
AI provider implementations for local and cloud-based models.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import aiohttp
import json

from config.config import settings

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Base class for AI providers."""

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 4000,
        temperature: float = 0.1,
        **kwargs
    ) -> str:
        """Generate text completion."""
        pass

    @abstractmethod
    async def generate_embedding(
        self,
        text: str,
        model: str,
        **kwargs
    ) -> List[float]:
        """Generate text embedding."""
        pass


class OllamaProvider(AIProvider):
    """Ollama local AI provider."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.session = None

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def generate_completion(
        self,
        prompt: str,
        model: str = "llama3.2:3b",
        max_tokens: int = 4000,
        temperature: float = 0.1,
        **kwargs
    ) -> str:
        """Generate completion using Ollama API."""
        session = await self._get_session()

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                **kwargs
            }
        }

        try:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(
                    total=max(settings.AI_REQUEST_TIMEOUT, 60))
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Ollama API error {response.status}: {error_text}")

                result = await response.json()
                return result.get("response", "").strip()

        except asyncio.TimeoutError:
            raise Exception("Ollama request timed out")
        except Exception as e:
            logger.error(f"Ollama completion failed: {e}")
            raise Exception(f"Ollama completion failed: {e}")

    async def generate_embedding(
        self,
        text: str,
        model: str = "nomic-embed-text",
        **kwargs
    ) -> List[float]:
        """Generate embedding using Ollama API."""
        session = await self._get_session()

        payload = {
            "model": model,
            "prompt": text
        }

        try:
            async with session.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=aiohttp.ClientTimeout(
                    total=max(settings.AI_REQUEST_TIMEOUT, 60))
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Ollama embedding API error {response.status}: {error_text}")

                result = await response.json()
                return result.get("embedding", [])

        except asyncio.TimeoutError:
            raise Exception("Ollama embedding request timed out")
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            raise Exception(f"Ollama embedding failed: {e}")

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available Ollama models."""
        session = await self._get_session()

        try:
            async with session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("models", [])
                return []
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def pull_model(self, model: str) -> bool:
        """Pull/download a model in Ollama."""
        session = await self._get_session()

        payload = {"name": model}

        try:
            async with session.post(
                f"{self.base_url}/api/pull",
                json=payload,
                # 5 minutes for model download
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                if response.status == 200:
                    # Stream the response to track progress
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode())
                                if data.get("status"):
                                    logger.info(
                                        f"Pulling {model}: {data['status']}")
                            except json.JSONDecodeError:
                                continue
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False

    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    def __del__(self):
        """Cleanup on deletion."""
        if self.session and not self.session.closed:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.session.close())
                else:
                    loop.run_until_complete(self.session.close())
            except:
                pass


class OpenAIProvider(AIProvider):
    """OpenAI provider (optional, requires API key)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        if not self.api_key or self.api_key.startswith("your_"):
            raise ValueError(
                "OpenAI API key is required and must be configured")

        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package is required for OpenAI provider")

    async def generate_completion(
        self,
        prompt: str,
        model: str = "gpt-4",
        max_tokens: int = 4000,
        temperature: float = 0.1,
        **kwargs
    ) -> str:
        """Generate completion using OpenAI API."""
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI completion failed: {e}")
            raise Exception(f"OpenAI completion failed: {e}")

    async def generate_embedding(
        self,
        text: str,
        model: str = "text-embedding-ada-002",
        **kwargs
    ) -> List[float]:
        """Generate embedding using OpenAI API."""
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise Exception(f"OpenAI embedding failed: {e}")


# Provider registry
_providers = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
}


def get_provider(provider_name: str, **kwargs) -> AIProvider:
    """Get an AI provider instance."""
    if provider_name not in _providers:
        raise ValueError(f"Unknown provider: {provider_name}")

    return _providers[provider_name](**kwargs)


async def check_ollama_connection() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
    except Exception:
        return False


async def setup_local_models() -> Dict[str, Any]:
    """Setup and verify local models are available."""
    setup_info = {
        "ollama_running": False,
        "models_available": [],
        "models_needed": [],
        "setup_commands": []
    }

    # Check if Ollama is running
    setup_info["ollama_running"] = await check_ollama_connection()

    if not setup_info["ollama_running"]:
        setup_info["setup_commands"].append(
            "Install and start Ollama: https://ollama.ai/download"
        )
        return setup_info

    # Check available models
    provider = OllamaProvider()
    try:
        models = await provider.list_models()
        setup_info["models_available"] = [m["name"] for m in models]

        # Check for required models
        required_models = [
            settings.DEFAULT_CHAT_MODEL,
            settings.DEFAULT_EMBEDDING_MODEL
        ]

        for model in required_models:
            if model not in setup_info["models_available"]:
                setup_info["models_needed"].append(model)
                setup_info["setup_commands"].append(f"ollama pull {model}")

    except Exception as e:
        logger.error(f"Failed to check Ollama models: {e}")
    finally:
        await provider.close()

    return setup_info
