"""
AI provider detection and automatic fallback system.

This module automatically detects available AI providers and chooses the best option
based on local availability, API keys, and user preferences.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import aiohttp

from config.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ProviderStatus:
    """Status information for an AI provider."""
    name: str
    available: bool
    local: bool
    models: List[str]
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    capabilities: List[str] = None  # ['chat', 'embeddings', 'vision', etc.]


class AIProviderDetector:
    """
    Detects and manages available AI providers with automatic fallback.

    Priority order:
    1. Local providers (Ollama) - fastest, private, no API costs
    2. External APIs with keys configured - reliable, full-featured
    3. Fallback to basic local models if available
    """

    def __init__(self):
        self.providers: Dict[str, ProviderStatus] = {}
        self.detection_cache_ttl = 300  # 5 minutes
        self.last_detection = 0

    async def detect_all_providers(self, force_refresh: bool = False) -> Dict[str, ProviderStatus]:
        """Detect all available AI providers."""
        import time

        # Use cache if recent and not forcing refresh
        if not force_refresh and (time.time() - self.last_detection) < self.detection_cache_ttl:
            return self.providers

        logger.info("Detecting available AI providers...")

        # Detect providers in parallel
        detection_tasks = [
            self._detect_ollama(),
            self._detect_openai(),
            self._detect_anthropic(),
            self._detect_huggingface(),
        ]

        results = await asyncio.gather(*detection_tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, ProviderStatus):
                self.providers[result.name] = result
            elif isinstance(result, Exception):
                logger.error(f"Provider detection failed: {result}")

        self.last_detection = time.time()

        # Log detection results
        available_providers = [
            name for name, status in self.providers.items() if status.available]
        logger.info(f"Available providers: {available_providers}")

        return self.providers

    async def _detect_ollama(self) -> ProviderStatus:
        """Detect Ollama local installation."""
        status = ProviderStatus(
            name="ollama",
            available=False,
            local=True,
            models=[],
            capabilities=['chat', 'embeddings']
        )

        try:
            start_time = asyncio.get_event_loop().time()

            async with aiohttp.ClientSession() as session:
                # Check if Ollama is running
                async with session.get(
                    f"{settings.OLLAMA_BASE_URL}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        status.available = True
                        status.latency_ms = (
                            asyncio.get_event_loop().time() - start_time) * 1000

                        # Get available models
                        data = await response.json()
                        status.models = [model["name"]
                                         for model in data.get("models", [])]

                        logger.info(
                            f"Ollama detected with {len(status.models)} models")
                    else:
                        status.error = f"Ollama responded with status {response.status}"

        except asyncio.TimeoutError:
            status.error = "Ollama connection timeout"
        except aiohttp.ClientConnectorError:
            status.error = "Ollama not running or not accessible"
        except Exception as e:
            status.error = f"Ollama detection error: {e}"

        return status

    async def _detect_openai(self) -> ProviderStatus:
        """Detect OpenAI API availability."""
        status = ProviderStatus(
            name="openai",
            available=False,
            local=False,
            models=[],
            capabilities=['chat', 'embeddings', 'vision', 'audio']
        )

        # Check if API key is configured
        if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("your_"):
            status.error = "OpenAI API key not configured"
            return status

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            start_time = asyncio.get_event_loop().time()

            # Test API with a simple request
            models = await client.models.list()

            status.available = True
            status.latency_ms = (
                asyncio.get_event_loop().time() - start_time) * 1000
            status.models = [
                model.id for model in models.data if 'gpt' in model.id or 'embedding' in model.id]

            logger.info(
                f"OpenAI API detected with {len(status.models)} models")

        except ImportError:
            status.error = "OpenAI package not installed"
        except Exception as e:
            status.error = f"OpenAI API error: {e}"

        return status

    async def _detect_anthropic(self) -> ProviderStatus:
        """Detect Anthropic Claude API availability."""
        status = ProviderStatus(
            name="anthropic",
            available=False,
            local=False,
            models=[],
            capabilities=['chat']
        )

        # Check if API key is configured
        if not hasattr(settings, 'ANTHROPIC_API_KEY') or not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY.startswith("your_"):
            status.error = "Anthropic API key not configured"
            return status

        try:
            import anthropic
            client = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY)

            start_time = asyncio.get_event_loop().time()

            # Test API with a simple request (Anthropic doesn't have a models endpoint)
            # We'll just try to make a minimal completion request
            await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}]
            )

            status.available = True
            status.latency_ms = (
                asyncio.get_event_loop().time() - start_time) * 1000
            status.models = [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-3-5-sonnet-20241022"
            ]

            logger.info("Anthropic Claude API detected")

        except ImportError:
            status.error = "Anthropic package not installed"
        except Exception as e:
            status.error = f"Anthropic API error: {e}"

        return status

    async def _detect_huggingface(self) -> ProviderStatus:
        """Detect Hugging Face local models (sentence-transformers)."""
        status = ProviderStatus(
            name="huggingface",
            available=False,
            local=True,
            models=[],
            capabilities=['embeddings']
        )

        try:
            from sentence_transformers import SentenceTransformer

            # Test with a small model
            start_time = asyncio.get_event_loop().time()

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, SentenceTransformer, "all-MiniLM-L6-v2")

            status.available = True
            status.latency_ms = (
                asyncio.get_event_loop().time() - start_time) * 1000
            status.models = [
                "all-MiniLM-L6-v2",
                "all-mpnet-base-v2",
                "paraphrase-MiniLM-L6-v2"
            ]

            logger.info("Hugging Face sentence-transformers detected")

        except ImportError:
            status.error = "sentence-transformers package not installed"
        except Exception as e:
            status.error = f"Hugging Face detection error: {e}"

        return status

    async def get_best_provider(
        self,
        capability: str = "chat",
        prefer_local: bool = True,
        force_refresh: bool = False
    ) -> Optional[ProviderStatus]:
        """
        Get the best available provider for a specific capability.

        Args:
            capability: Required capability ('chat', 'embeddings', 'vision', etc.)
            prefer_local: Whether to prefer local providers over APIs
            force_refresh: Force re-detection of providers
        """
        await self.detect_all_providers(force_refresh)

        # Filter providers by capability and availability
        suitable_providers = [
            status for status in self.providers.values()
            if status.available and capability in (status.capabilities or [])
        ]

        if not suitable_providers:
            logger.warning(
                f"No providers available for capability: {capability}")
            return None

        # Sort by preference: local first if preferred, then by latency
        def sort_key(provider: ProviderStatus) -> Tuple[int, float]:
            # Priority: local preference, then latency
            local_priority = 0 if (prefer_local and provider.local) else 1
            latency = provider.latency_ms or 9999
            return (local_priority, latency)

        suitable_providers.sort(key=sort_key)
        best_provider = suitable_providers[0]

        logger.info(
            f"Selected {best_provider.name} for {capability} (local: {best_provider.local})")
        return best_provider

    async def get_recommended_models(self) -> Dict[str, str]:
        """Get recommended models for different tasks based on available providers."""
        await self.detect_all_providers()

        recommendations = {}

        # Chat model recommendation
        chat_provider = await self.get_best_provider("chat")
        if chat_provider:
            if chat_provider.name == "ollama":
                # First check if the configured model is available
                from config.config import settings
                configured_model = settings.DEFAULT_CHAT_MODEL

                if configured_model in chat_provider.models:
                    recommendations["chat"] = configured_model
                else:
                    # Smart model matching - prefer exact match, then similar models
                    preferred_models = [
                        "llama3.2:3b", "llama3.2:1b", "llama3.2:latest", "llama3:instruct", "tinyllama:latest"]

                    for preferred in preferred_models:
                        if preferred in chat_provider.models:
                            recommendations["chat"] = preferred
                            break
                    else:
                        # Fallback to any available model
                        if chat_provider.models:
                            recommendations["chat"] = chat_provider.models[0]

            elif chat_provider.name == "openai":
                # Cost-effective option
                recommendations["chat"] = "gpt-4o-mini"
            elif chat_provider.name == "anthropic":
                # Fast option
                recommendations["chat"] = "claude-3-haiku-20240307"

        # Embedding model recommendation
        embedding_provider = await self.get_best_provider("embeddings")
        if embedding_provider:
            if embedding_provider.name == "ollama":
                # Smart embedding model matching
                preferred_embeddings = [
                    "nomic-embed-text", "nomic-embed-text:latest"]

                for preferred in preferred_embeddings:
                    if preferred in embedding_provider.models:
                        recommendations["embedding"] = preferred
                        break
                else:
                    # Look for any embedding model
                    embedding_models = [
                        m for m in embedding_provider.models if "embed" in m.lower()]
                    if embedding_models:
                        recommendations["embedding"] = embedding_models[0]

            elif embedding_provider.name == "openai":
                # Cost-effective
                recommendations["embedding"] = "text-embedding-3-small"
            elif embedding_provider.name == "huggingface":
                recommendations["embedding"] = "all-MiniLM-L6-v2"

        return recommendations

    async def setup_instructions(self) -> Dict[str, Any]:
        """Generate setup instructions for missing providers."""
        await self.detect_all_providers()

        instructions = {
            "status": "checking",
            "local_available": False,
            "api_available": False,
            "recommendations": [],
            "setup_commands": [],
            "missing_models": []
        }

        # Check local providers
        ollama_status = self.providers.get("ollama")
        if ollama_status and ollama_status.available:
            instructions["local_available"] = True

            # Check for recommended models
            recommended_models = ["llama3.2:3b", "nomic-embed-text"]
            for model in recommended_models:
                if model not in ollama_status.models:
                    instructions["missing_models"].append(model)
                    instructions["setup_commands"].append(
                        f"ollama pull {model}")
        else:
            instructions["setup_commands"].extend([
                "# Install Ollama for local AI processing:",
                "# Visit: https://ollama.ai/download",
                "# Then run: ollama pull llama3.2:3b",
                "# And: ollama pull nomic-embed-text"
            ])

        # Check API providers
        api_providers = ["openai", "anthropic"]
        available_apis = [
            name for name in api_providers
            if self.providers.get(name) and self.providers[name].available
        ]

        if available_apis:
            instructions["api_available"] = True

        # Generate recommendations
        if instructions["local_available"] and not instructions["missing_models"]:
            instructions["recommendations"].append(
                "✅ Local AI ready - fast and private processing")
        elif instructions["local_available"] and instructions["missing_models"]:
            instructions["recommendations"].append(
                "🔄 Local AI available with fallback models - some preferred models missing")
        elif instructions["api_available"]:
            instructions["recommendations"].append(
                "✅ API access available - full-featured processing")
        else:
            instructions["recommendations"].append(
                "⚠️  No AI providers available - setup required")

        if instructions["local_available"] and instructions["api_available"]:
            instructions["recommendations"].append(
                "🎯 Hybrid setup detected - will use local first, API as fallback")

        return instructions


# Global detector instance
_detector = None


async def get_ai_detector() -> AIProviderDetector:
    """Get the global AI provider detector."""
    global _detector
    if _detector is None:
        _detector = AIProviderDetector()
    return _detector


async def auto_configure_ai() -> Dict[str, Any]:
    """Automatically configure AI settings based on available providers."""
    detector = await get_ai_detector()
    setup_info = await detector.setup_instructions()

    # Update settings based on detection
    recommendations = await detector.get_recommended_models()

    config_updates = {}
    if "chat" in recommendations:
        config_updates["DEFAULT_CHAT_MODEL"] = recommendations["chat"]
    if "embedding" in recommendations:
        config_updates["DEFAULT_EMBEDDING_MODEL"] = recommendations["embedding"]

    # Determine best provider
    chat_provider = await detector.get_best_provider("chat")
    if chat_provider:
        config_updates["DEFAULT_LLM_PROVIDER"] = chat_provider.name

    return {
        "setup_info": setup_info,
        "config_updates": config_updates,
        "providers": detector.providers
    }
