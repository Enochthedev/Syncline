"""
Test script for embedding service implementation.

Validates:
- Module imports work correctly
- Classes and functions are properly defined
- Service initialization works
- Key methods are available
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test all modules can be imported."""
    print("Testing imports...")
    try:
        from services.ai.embeddings import (
            EmbeddingService,
            get_embedding_service,
        )
        from services.ai.semantic_search import (
            SearchFilter,
            SearchResponse,
            SearchResultItem,
            SemanticSearchEngine,
            get_semantic_search_engine,
        )

        print("  ✓ All imports successful")
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_embedding_service_structure():
    """Test EmbeddingService class structure."""
    print("Testing EmbeddingService structure...")
    try:
        from services.ai.embeddings import EmbeddingService

        # Check required methods exist
        required_methods = [
            "generate_embedding",
            "generate_embeddings_batch",
            "embed_message",
            "embed_messages_batch",
            "get_embedding",
            "delete_embedding",
            "process_unembedded_messages",
            "health_check",
        ]

        for method in required_methods:
            assert hasattr(EmbeddingService, method), f"Missing method: {method}"

        print("  ✓ EmbeddingService has all required methods")
        return True
    except Exception as e:
        print(f"  ✗ EmbeddingService structure test failed: {e}")
        return False


def test_semantic_search_structure():
    """Test SemanticSearchEngine class structure."""
    print("Testing SemanticSearchEngine structure...")
    try:
        from services.ai.semantic_search import SemanticSearchEngine

        # Check required methods exist
        required_methods = [
            "search",
            "find_similar_messages",
            "search_by_thread",
            "search_by_platform",
        ]

        for method in required_methods:
            assert hasattr(SemanticSearchEngine, method), f"Missing method: {method}"

        print("  ✓ SemanticSearchEngine has all required methods")
        return True
    except Exception as e:
        print(f"  ✗ SemanticSearchEngine structure test failed: {e}")
        return False


def test_pydantic_models():
    """Test Pydantic models are properly defined."""
    print("Testing Pydantic models...")
    try:
        from services.ai.semantic_search import (
            SearchFilter,
            SearchResponse,
            SearchResultItem,
        )

        # Test SearchFilter
        filter_obj = SearchFilter(platforms=["gmail", "slack"])
        assert filter_obj.platforms == ["gmail", "slack"]

        # Test SearchResultItem
        from datetime import datetime
        from uuid import uuid4

        result_item = SearchResultItem(
            message_id=uuid4(),
            platform="gmail",
            content="Test content",
            timestamp=datetime.now(),
            similarity_score=0.95,
        )
        assert result_item.similarity_score == 0.95

        # Test SearchResponse
        response = SearchResponse(
            query="test query",
            results=[],
            total_results=0,
            search_time_ms=10.5,
        )
        assert response.query == "test query"

        print("  ✓ All Pydantic models work correctly")
        return True
    except Exception as e:
        print(f"  ✗ Pydantic models test failed: {e}")
        return False


def test_factory_functions():
    """Test factory functions work."""
    print("Testing factory functions...")
    try:
        from services.ai.embeddings import get_embedding_service
        from services.ai.semantic_search import get_semantic_search_engine

        # Test embedding service factory
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        assert service1 is service2, "Factory should return singleton"

        # Test search engine factory
        engine1 = get_semantic_search_engine()
        engine2 = get_semantic_search_engine()
        assert engine1 is engine2, "Factory should return singleton"

        print("  ✓ Factory functions work correctly")
        return True
    except Exception as e:
        print(f"  ✗ Factory functions test failed: {e}")
        return False


def test_service_initialization():
    """Test services can be initialized."""
    print("Testing service initialization...")
    try:
        from services.ai.embeddings import EmbeddingService
        from services.ai.semantic_search import SemanticSearchEngine

        # Test EmbeddingService initialization
        embedding_service = EmbeddingService(batch_size=5)
        assert embedding_service.batch_size == 5

        # Test SemanticSearchEngine initialization
        search_engine = SemanticSearchEngine(default_limit=20)
        assert search_engine.default_limit == 20

        print("  ✓ Services can be initialized with custom parameters")
        return True
    except Exception as e:
        print(f"  ✗ Service initialization test failed: {e}")
        return False


def test_integration_with_dependencies():
    """Test integration with existing services."""
    print("Testing integration with dependencies...")
    try:
        from services.ai.embeddings import EmbeddingService
        from services.ai.providers import get_llm_provider
        from services.vector_db.chroma_client import get_chroma_client

        # Test that EmbeddingService can use existing services
        llm_provider = get_llm_provider()
        chroma_client = get_chroma_client()

        service = EmbeddingService(
            llm_provider=llm_provider,
            chroma_client=chroma_client,
        )

        assert service.llm_provider is not None
        assert service.chroma_client is not None

        print("  ✓ Services integrate correctly with dependencies")
        return True
    except Exception as e:
        print(f"  ✗ Integration test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Embedding Service Test Suite")
    print("=" * 60)

    tests = [
        test_imports,
        test_embedding_service_structure,
        test_semantic_search_structure,
        test_pydantic_models,
        test_factory_functions,
        test_service_initialization,
        test_integration_with_dependencies,
    ]

    results = [test() for test in tests]

    print("\n" + "=" * 60)
    print(f"Passed: {sum(results)}/{len(results)}")

    if sum(results) == len(results):
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {len(results) - sum(results)} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
