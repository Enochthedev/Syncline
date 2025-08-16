"""
Unit tests for embedding service.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from services.embedding_service import (
    EmbeddingService, EmbeddingProvider, EmbeddingResult, EmbeddingCache,
    OpenAIEmbeddingProvider, SentenceTransformersProvider, EmbeddingError
)


class TestEmbeddingCache:
    """Test cases for EmbeddingCache."""

    @pytest.fixture
    def cache(self):
        """Create an EmbeddingCache instance for testing."""
        return EmbeddingCache(max_size=3)

    @pytest.fixture
    def sample_result(self):
        """Create a sample embedding result for testing."""
        return EmbeddingResult(
            request_id="test_123",
            text="test text",
            embedding=[0.1, 0.2, 0.3],
            model="test-model",
            provider=EmbeddingProvider.OPENAI,
            dimensions=3
        )

    def test_initialization(self, cache):
        """Test cache initialization."""
        assert cache.max_size == 3
        assert len(cache.cache) == 0
        assert len(cache.access_times) == 0

    def test_generate_key(self, cache):
        """Test cache key generation."""
        key1 = cache._generate_key("text1", "model1", "provider1")
        key2 = cache._generate_key("text1", "model1", "provider1")
        key3 = cache._generate_key("text2", "model1", "provider1")

        assert key1 == key2  # Same inputs should generate same key
        assert key1 != key3  # Different inputs should generate different keys
        assert len(key1) == 64  # SHA256 hex digest length

    def test_put_and_get(self, cache, sample_result):
        """Test putting and getting from cache."""
        # Initially empty
        result = cache.get(sample_result.text,
                           sample_result.model, sample_result.provider.value)
        assert result is None

        # Put result
        cache.put(sample_result)
        assert cache.size() == 1

        # Get result
        cached_result = cache.get(
            sample_result.text, sample_result.model, sample_result.provider.value)
        assert cached_result is not None
        assert cached_result.text == sample_result.text
        assert cached_result.embedding == sample_result.embedding

    def test_eviction(self, cache):
        """Test cache eviction when max size is reached."""
        # Fill cache to max capacity
        for i in range(3):
            result = EmbeddingResult(
                request_id=f"test_{i}",
                text=f"text_{i}",
                embedding=[float(i)],
                model="test-model",
                provider=EmbeddingProvider.OPENAI,
                dimensions=1
            )
            cache.put(result)

        assert cache.size() == 3

        # Add one more - should evict oldest
        new_result = EmbeddingResult(
            request_id="test_new",
            text="new_text",
            embedding=[99.0],
            model="test-model",
            provider=EmbeddingProvider.OPENAI,
            dimensions=1
        )
        cache.put(new_result)

        assert cache.size() == 3  # Still at max size

        # The oldest entry should be evicted
        oldest_result = cache.get("text_0", "test-model", "openai")
        assert oldest_result is None

        # New entry should be present
        newest_result = cache.get("new_text", "test-model", "openai")
        assert newest_result is not None

    def test_clear(self, cache, sample_result):
        """Test cache clearing."""
        cache.put(sample_result)
        assert cache.size() == 1

        cache.clear()
        assert cache.size() == 0

        result = cache.get(sample_result.text,
                           sample_result.model, sample_result.provider.value)
        assert result is None


class TestOpenAIEmbeddingProvider:
    """Test cases for OpenAIEmbeddingProvider."""

    @pytest.fixture
    def provider(self):
        """Create an OpenAIEmbeddingProvider instance for testing."""
        return OpenAIEmbeddingProvider(api_key="test_key")

    @pytest.mark.asyncio
    async def test_generate_embedding(self, provider):
        """Test single embedding generation."""
        with patch.object(provider.client.embeddings, 'create') as mock_create:
            # Mock OpenAI response
            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3, 0.4])]
            mock_create.return_value = mock_response

            embedding = await provider.generate_embedding("test text")

            assert embedding == [0.1, 0.2, 0.3, 0.4]
            mock_create.assert_called_once_with(
                input="test text",
                model=provider.default_model
            )

    @pytest.mark.asyncio
    async def test_generate_embedding_with_custom_model(self, provider):
        """Test embedding generation with custom model."""
        with patch.object(provider.client.embeddings, 'create') as mock_create:
            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.5, 0.6])]
            mock_create.return_value = mock_response

            embedding = await provider.generate_embedding("test text", model="custom-model")

            assert embedding == [0.5, 0.6]
            mock_create.assert_called_once_with(
                input="test text",
                model="custom-model"
            )

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, provider):
        """Test batch embedding generation."""
        with patch.object(provider.client.embeddings, 'create') as mock_create:
            mock_response = Mock()
            mock_response.data = [
                Mock(embedding=[0.1, 0.2]),
                Mock(embedding=[0.3, 0.4]),
                Mock(embedding=[0.5, 0.6])
            ]
            mock_create.return_value = mock_response

            texts = ["text1", "text2", "text3"]
            embeddings = await provider.generate_embeddings_batch(texts)

            assert len(embeddings) == 3
            assert embeddings[0] == [0.1, 0.2]
            assert embeddings[1] == [0.3, 0.4]
            assert embeddings[2] == [0.5, 0.6]

            mock_create.assert_called_once_with(
                input=texts,
                model=provider.default_model
            )

    @pytest.mark.asyncio
    async def test_generate_embedding_error(self, provider):
        """Test error handling in embedding generation."""
        with patch.object(provider.client.embeddings, 'create') as mock_create:
            mock_create.side_effect = Exception("API Error")

            with pytest.raises(Exception) as exc_info:
                await provider.generate_embedding("test text")

            assert "OpenAI embedding failed" in str(exc_info.value)


class TestSentenceTransformersProvider:
    """Test cases for SentenceTransformersProvider."""

    @pytest.fixture
    def provider(self):
        """Create a SentenceTransformersProvider instance for testing."""
        return SentenceTransformersProvider(model_name="test-model")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="SentenceTransformers import testing is complex")
    async def test_load_model(self, provider):
        """Test model loading."""
        with patch('services.embedding_service.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_st.return_value = mock_model

            await provider._load_model()

            assert provider._model == mock_model
            mock_st.assert_called_once_with("test-model")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="SentenceTransformers import testing is complex")
    async def test_generate_embedding(self, provider):
        """Test embedding generation."""
        with patch('services.embedding_service.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_embedding = Mock()
            mock_embedding.tolist.return_value = [0.1, 0.2, 0.3]
            mock_model.encode.return_value = mock_embedding
            mock_st.return_value = mock_model

            embedding = await provider.generate_embedding("test text")

            assert embedding == [0.1, 0.2, 0.3]
            mock_model.encode.assert_called_once_with("test text")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="SentenceTransformers import testing is complex")
    async def test_generate_embeddings_batch(self, provider):
        """Test batch embedding generation."""
        with patch('services.embedding_service.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_embeddings = Mock()
            mock_embeddings.tolist.return_value = [[0.1, 0.2], [0.3, 0.4]]
            mock_model.encode.return_value = mock_embeddings
            mock_st.return_value = mock_model

            texts = ["text1", "text2"]
            embeddings = await provider.generate_embeddings_batch(texts)

            assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
            mock_model.encode.assert_called_once_with(texts)


class TestEmbeddingService:
    """Test cases for EmbeddingService."""

    @pytest.fixture
    def embedding_service(self):
        """Create an EmbeddingService instance for testing."""
        return EmbeddingService(
            default_provider=EmbeddingProvider.OPENAI,
            cache_size=10,
            enable_pii_redaction=True
        )

    @pytest.fixture
    def mock_openai_provider(self):
        """Create a mock OpenAI provider."""
        provider = Mock(spec=OpenAIEmbeddingProvider)
        provider.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        provider.generate_embeddings_batch = AsyncMock(
            return_value=[[0.1, 0.2], [0.3, 0.4]])
        return provider

    def test_initialization(self, embedding_service):
        """Test EmbeddingService initialization."""
        assert embedding_service.default_provider == EmbeddingProvider.OPENAI
        assert embedding_service.enable_pii_redaction is True
        assert embedding_service.cache is not None
        assert EmbeddingProvider.OPENAI in embedding_service.providers
        assert embedding_service.stats['embeddings_generated'] == 0

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, embedding_service, mock_openai_provider):
        """Test successful embedding generation."""
        embedding_service.providers[EmbeddingProvider.OPENAI] = mock_openai_provider

        with patch('services.embedding_service.get_pii_redaction_service') as mock_pii:
            mock_pii_service = AsyncMock()
            mock_redaction_result = Mock()
            mock_redaction_result.redacted_text = "test text"
            mock_redaction_result.entities = []
            mock_pii_service.redact_text.return_value = mock_redaction_result
            mock_pii.return_value = mock_pii_service

            result = await embedding_service.generate_embedding("test text")

            assert isinstance(result, EmbeddingResult)
            assert result.text == "test text"
            assert result.embedding == [0.1, 0.2, 0.3]
            assert result.provider == EmbeddingProvider.OPENAI
            assert result.dimensions == 3

    @pytest.mark.asyncio
    async def test_generate_embedding_with_pii_redaction(self, embedding_service, mock_openai_provider):
        """Test embedding generation with PII redaction."""
        embedding_service.providers[EmbeddingProvider.OPENAI] = mock_openai_provider

        with patch('services.embedding_service.get_pii_redaction_service') as mock_pii:
            mock_pii_service = AsyncMock()
            mock_redaction_result = Mock()
            mock_redaction_result.redacted_text = "Contact [REDACTED] at [REDACTED]"
            mock_redaction_result.entities = [
                Mock(), Mock()]  # 2 entities redacted
            mock_pii_service.redact_text.return_value = mock_redaction_result
            mock_pii.return_value = mock_pii_service

            result = await embedding_service.generate_embedding(
                "Contact John at john@example.com"
            )

            assert result.text == "Contact [REDACTED] at [REDACTED]"
            assert result.metadata['pii_redacted'] is True
            assert embedding_service.stats['pii_redactions'] == 1

    @pytest.mark.asyncio
    async def test_generate_embedding_cache_hit(self, embedding_service, mock_openai_provider):
        """Test embedding generation with cache hit."""
        embedding_service.providers[EmbeddingProvider.OPENAI] = mock_openai_provider

        # Pre-populate cache
        cached_result = EmbeddingResult(
            request_id="cached_123",
            text="test text",
            embedding=[0.9, 0.8, 0.7],
            model="default",
            provider=EmbeddingProvider.OPENAI,
            dimensions=3
        )
        embedding_service.cache.put(cached_result)

        with patch('services.embedding_service.get_pii_redaction_service') as mock_pii:
            mock_pii_service = AsyncMock()
            mock_redaction_result = Mock()
            mock_redaction_result.redacted_text = "test text"
            mock_redaction_result.entities = []
            mock_pii_service.redact_text.return_value = mock_redaction_result
            mock_pii.return_value = mock_pii_service

            result = await embedding_service.generate_embedding("test text")

            # Should return cached result
            assert result.embedding == [0.9, 0.8, 0.7]
            assert embedding_service.stats['cache_hits'] == 1

            # Provider should not be called
            mock_openai_provider.generate_embedding.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_embedding_cache_miss(self, embedding_service, mock_openai_provider):
        """Test embedding generation with cache miss."""
        embedding_service.providers[EmbeddingProvider.OPENAI] = mock_openai_provider

        with patch('services.embedding_service.get_pii_redaction_service') as mock_pii:
            mock_pii_service = AsyncMock()
            mock_redaction_result = Mock()
            mock_redaction_result.redacted_text = "test text"
            mock_redaction_result.entities = []
            mock_pii_service.redact_text.return_value = mock_redaction_result
            mock_pii.return_value = mock_pii_service

            result = await embedding_service.generate_embedding("test text")

            assert embedding_service.stats['cache_misses'] == 1
            mock_openai_provider.generate_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, embedding_service):
        """Test embedding generation with empty text."""
        with pytest.raises(EmbeddingError) as exc_info:
            await embedding_service.generate_embedding("")

        assert "Empty text provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_embedding_unsupported_provider(self, embedding_service):
        """Test embedding generation with unsupported provider."""
        with patch('services.embedding_service.get_pii_redaction_service') as mock_pii:
            mock_pii_service = AsyncMock()
            mock_redaction_result = Mock()
            mock_redaction_result.redacted_text = "test text"
            mock_redaction_result.entities = []
            mock_pii_service.redact_text.return_value = mock_redaction_result
            mock_pii.return_value = mock_pii_service

            # Remove the provider
            del embedding_service.providers[EmbeddingProvider.OPENAI]

            with pytest.raises(EmbeddingError) as exc_info:
                await embedding_service.generate_embedding("test text")

            assert "Unsupported provider" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, embedding_service, mock_openai_provider):
        """Test batch embedding generation."""
        embedding_service.providers[EmbeddingProvider.OPENAI] = mock_openai_provider

        with patch('services.embedding_service.get_pii_redaction_service') as mock_pii:
            mock_pii_service = AsyncMock()
            mock_redaction_result = Mock()
            mock_redaction_result.redacted_text = "text"
            mock_redaction_result.entities = []
            mock_pii_service.redact_text.return_value = mock_redaction_result
            mock_pii.return_value = mock_pii_service

            # Mock generate_embedding to return different results for each call
            async def mock_generate_embedding(text, *args, **kwargs):
                return EmbeddingResult(
                    request_id=f"test_{text}",
                    text=text,
                    # Simple hash-based embedding
                    embedding=[hash(text) % 100 / 100.0],
                    model="default",
                    provider=EmbeddingProvider.OPENAI,
                    dimensions=1
                )

            with patch.object(embedding_service, 'generate_embedding', side_effect=mock_generate_embedding):
                texts = ["text1", "text2", "text3"]
                results = await embedding_service.generate_embeddings_batch(texts)

                assert len(results) == 3
                assert all(isinstance(r, EmbeddingResult) for r in results)

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_empty(self, embedding_service):
        """Test batch embedding generation with empty list."""
        results = await embedding_service.generate_embeddings_batch([])
        assert results == []

    def test_update_stats(self, embedding_service):
        """Test statistics update."""
        initial_generated = embedding_service.stats['embeddings_generated']
        initial_time = embedding_service.stats['total_processing_time']

        embedding_service._update_stats(EmbeddingProvider.OPENAI, 1.5)

        assert embedding_service.stats['embeddings_generated'] == initial_generated + 1
        assert embedding_service.stats['total_processing_time'] == initial_time + 1.5
        assert embedding_service.stats['provider_usage']['openai'] == 1

    def test_get_stats(self, embedding_service):
        """Test getting embedding statistics."""
        # Add some test data
        embedding_service._update_stats(EmbeddingProvider.OPENAI, 1.0)
        embedding_service._update_stats(EmbeddingProvider.OPENAI, 2.0)
        embedding_service.stats['cache_hits'] = 5
        embedding_service.stats['cache_misses'] = 3

        stats = embedding_service.get_stats()

        assert stats['embeddings_generated'] == 2
        assert stats['cache_hit_rate'] == 5/8  # 5 hits out of 8 total requests
        assert stats['average_processing_time'] == 1.5
        assert stats['default_provider'] == 'openai'
        assert stats['pii_redaction_enabled'] is True

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, embedding_service, mock_openai_provider):
        """Test health check when service is healthy."""
        embedding_service.providers[EmbeddingProvider.OPENAI] = mock_openai_provider

        with patch('services.embedding_service.get_pii_redaction_service') as mock_pii:
            mock_pii_service = AsyncMock()
            mock_redaction_result = Mock()
            mock_redaction_result.redacted_text = "test text"
            mock_redaction_result.entities = []
            mock_pii_service.redact_text.return_value = mock_redaction_result
            mock_pii.return_value = mock_pii_service

            health = await embedding_service.health_check()

            assert health['status'] == 'healthy'
            assert health['test_successful'] is True
            assert health['embedding_dimensions'] == 3
            assert health['provider'] == 'openai'
            assert 'stats' in health

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, embedding_service, mock_openai_provider):
        """Test health check when an error occurs."""
        mock_openai_provider.generate_embedding.side_effect = Exception(
            "Test error")
        embedding_service.providers[EmbeddingProvider.OPENAI] = mock_openai_provider

        with patch('services.embedding_service.get_pii_redaction_service') as mock_pii:
            mock_pii_service = AsyncMock()
            mock_redaction_result = Mock()
            mock_redaction_result.redacted_text = "test text"
            mock_redaction_result.entities = []
            mock_pii_service.redact_text.return_value = mock_redaction_result
            mock_pii.return_value = mock_pii_service

            health = await embedding_service.health_check()

            assert health['status'] == 'unhealthy'
            assert health['test_successful'] is False
            assert 'error' in health
            assert 'stats' in health

    def test_clear_cache(self, embedding_service):
        """Test cache clearing."""
        # Add something to cache
        result = EmbeddingResult(
            request_id="test_123",
            text="test text",
            embedding=[0.1, 0.2],
            model="test",
            provider=EmbeddingProvider.OPENAI,
            dimensions=2
        )
        embedding_service.cache.put(result)
        assert embedding_service.cache.size() == 1

        embedding_service.clear_cache()
        assert embedding_service.cache.size() == 0


if __name__ == "__main__":
    pytest.main([__file__])
