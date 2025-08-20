"""
Load tests for AI processing pipeline and search performance.

This module tests AI processing performance under high load conditions.
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch
import random
import string

from services.ai.engine import AIProcessingEngine
from services.ai.search.agent import HybridSearchAgent
from services.ai.entity.extractor import EntityExtractor
from services.ai.summary.agent import SummaryGenerationAgent
from services.ai.memory.agent import ProactiveMemoryAgent
from services.ai.embeddings import EmbeddingService
from services.message_schema import RawMessage, NormalizedMessage, MessageContent, Participant
from api.auth.models import User


@pytest.fixture
def ai_test_user():
    """Create a test user for AI load tests."""
    return User(
        id="ai-load-test-user",
        username="ai_load_user",
        email="ai_load@example.com",
        full_name="AI Load Test User",
        is_active=True,
        tenant_id="ai-load-tenant"
    )


@pytest.fixture
def mock_fast_ai_engine():
    """Fast mock AI engine for load testing."""
    engine = AsyncMock(spec=AIProcessingEngine)

    # Fast responses with realistic delays
    async def mock_extract_entities(*args, **kwargs):
        await asyncio.sleep(0.05)  # 50ms delay
        return [
            {"type": "person", "value": "John Doe", "confidence": 0.9},
            {"type": "organization", "value": "Acme Corp", "confidence": 0.85},
            {"type": "date", "value": "2024-01-15", "confidence": 0.95}
        ]

    async def mock_generate_summary(*args, **kwargs):
        await asyncio.sleep(0.1)  # 100ms delay
        return {
            "content": "AI-generated summary of the conversation",
            "key_points": ["Important point 1", "Important point 2"],
            "action_items": ["Follow up on proposal", "Schedule meeting"]
        }

    async def mock_generate_embedding(*args, **kwargs):
        await asyncio.sleep(0.02)  # 20ms delay
        return [random.random() for _ in range(1536)]

    engine.extract_entities.side_effect = mock_extract_entities
    engine.generate_summary.side_effect = mock_generate_summary
    engine.generate_embedding.side_effect = mock_generate_embedding

    return engine


def generate_test_content(length: int = 100) -> str:
    """Generate test content of specified length."""
    templates = [
        "Meeting with {person} from {company} about {topic} scheduled for {date}.",
        "Follow up on {topic} project with {person}. Need to review {document}.",
        "Important update regarding {topic}. Please contact {person} at {company}.",
        "Proposal for {topic} submitted to {company}. Waiting for feedback from {person}.",
        "Conference call with {person} and team about {topic} on {date}."
    ]

    entities = {
        "person": ["John Smith", "Sarah Johnson", "Mike Wilson", "Lisa Chen", "David Brown"],
        "company": ["Acme Corp", "TechStart Inc", "Global Solutions", "Innovation Labs", "Future Systems"],
        "topic": ["quarterly review", "budget planning", "product launch", "market analysis", "team restructuring"],
        "date": ["Monday", "next week", "January 15th", "end of month", "Q2 2024"],
        "document": ["proposal.pdf", "budget_report.xlsx", "project_plan.docx", "analysis.pptx", "summary.pdf"]
    }

    content = random.choice(templates).format(
        person=random.choice(entities["person"]),
        company=random.choice(entities["company"]),
        topic=random.choice(entities["topic"]),
        date=random.choice(entities["date"]),
        document=random.choice(entities.get("document", ["document"]))
    )

    # Extend content to reach desired length
    while len(content) < length:
        content += " " + random.choice([
            "Additional context about the situation.",
            "More details will be provided later.",
            "Please review and provide feedback.",
            "This is an important business matter.",
            "Urgent attention required for this item."
        ])

    return content[:length]


class TestAIProcessingLoad:
    """Test AI processing under high load conditions."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_high_volume_entity_extraction(self, mock_fast_ai_engine):
        """Test entity extraction with high volume of messages."""

        # Generate test messages
        message_count = 200
        test_messages = [generate_test_content(
            200) for _ in range(message_count)]

        with patch('services.ai.engine.AIProcessingEngine', return_value=mock_fast_ai_engine):
            start_time = time.time()

            # Process messages in batches for better performance
            batch_size = 25
            all_results = []

            for i in range(0, message_count, batch_size):
                batch = test_messages[i:i + batch_size]

                # Process batch concurrently
                tasks = [mock_fast_ai_engine.extract_entities(
                    msg) for msg in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter successful results
                successful_results = [
                    r for r in batch_results if not isinstance(r, Exception)]
                all_results.extend(successful_results)

            end_time = time.time()
            total_time = end_time - start_time

            # Performance metrics
            success_rate = len(all_results) / message_count
            throughput = message_count / total_time
            avg_processing_time = total_time / message_count

            # Assertions
            assert success_rate > 0.95, f"Entity extraction success rate {success_rate:.2%} below 95%"
            assert throughput > 20, f"Throughput {throughput:.1f} messages/sec below minimum"
            assert avg_processing_time < 0.2, f"Average processing time {avg_processing_time:.3f}s too slow"

            print(f"Entity Extraction Load Test Results:")
            print(f"  Messages processed: {len(all_results)}/{message_count}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Throughput: {throughput:.1f} messages/second")
            print(f"  Success rate: {success_rate:.2%}")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_summary_generation(self, mock_fast_ai_engine):
        """Test concurrent summary generation performance."""

        # Generate conversation threads
        thread_count = 50
        conversations = []

        for i in range(thread_count):
            # Each conversation has 5-15 messages
            message_count = random.randint(5, 15)
            conversation = []

            for j in range(message_count):
                message_content = generate_test_content(150)
                conversation.append(message_content)

            conversations.append(" ".join(conversation))

        with patch('services.ai.engine.AIProcessingEngine', return_value=mock_fast_ai_engine):
            start_time = time.time()

            # Generate summaries concurrently
            tasks = [mock_fast_ai_engine.generate_summary(
                conv) for conv in conversations]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            total_time = end_time - start_time

            # Analyze results
            successful_summaries = [
                r for r in results if not isinstance(r, Exception)]
            success_rate = len(successful_summaries) / thread_count
            throughput = thread_count / total_time

            # Assertions
            assert success_rate > 0.90, f"Summary generation success rate {success_rate:.2%} below 90%"
            assert throughput > 5, f"Summary throughput {throughput:.1f} summaries/sec too low"
            assert total_time < 30, f"Total summary generation time {total_time:.2f}s too long"

            print(f"Summary Generation Load Test Results:")
            print(
                f"  Summaries generated: {len(successful_summaries)}/{thread_count}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Throughput: {throughput:.1f} summaries/second")
            print(f"  Success rate: {success_rate:.2%}")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_embedding_generation_load(self, mock_fast_ai_engine):
        """Test embedding generation under load."""

        # Generate various text lengths
        text_samples = []
        for _ in range(300):
            length = random.randint(50, 500)
            text_samples.append(generate_test_content(length))

        with patch('services.ai.engine.AIProcessingEngine', return_value=mock_fast_ai_engine):
            start_time = time.time()

            # Process embeddings in batches
            batch_size = 50
            all_embeddings = []

            for i in range(0, len(text_samples), batch_size):
                batch = text_samples[i:i + batch_size]

                tasks = [mock_fast_ai_engine.generate_embedding(
                    text) for text in batch]
                batch_embeddings = await asyncio.gather(*tasks, return_exceptions=True)

                successful_embeddings = [
                    e for e in batch_embeddings if not isinstance(e, Exception)]
                all_embeddings.extend(successful_embeddings)

            end_time = time.time()
            total_time = end_time - start_time

            # Performance metrics
            success_rate = len(all_embeddings) / len(text_samples)
            throughput = len(text_samples) / total_time

            # Verify embedding dimensions
            if all_embeddings:
                embedding_dims = [len(emb) for emb in all_embeddings]
                assert all(
                    dim == 1536 for dim in embedding_dims), "Invalid embedding dimensions"

            # Assertions
            assert success_rate > 0.95, f"Embedding success rate {success_rate:.2%} below 95%"
            assert throughput > 30, f"Embedding throughput {throughput:.1f} embeddings/sec too low"

            print(f"Embedding Generation Load Test Results:")
            print(
                f"  Embeddings generated: {len(all_embeddings)}/{len(text_samples)}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Throughput: {throughput:.1f} embeddings/second")
            print(f"  Success rate: {success_rate:.2%}")


class TestSearchPerformanceLoad:
    """Test search performance under load conditions."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_search_queries(self, ai_test_user):
        """Test concurrent search query performance."""

        # Mock search agent with realistic performance
        mock_search_agent = AsyncMock(spec=HybridSearchAgent)

        async def mock_search_with_delay(query, *args, **kwargs):
            # Simulate search processing time based on query complexity
            query_length = len(query.split())
            # Base 50ms + 10ms per word
            processing_time = 0.05 + (query_length * 0.01)
            await asyncio.sleep(processing_time)

            # Generate mock results
            result_count = random.randint(1, 20)
            mock_result = AsyncMock()
            mock_result.results = [
                AsyncMock(
                    id=f"result_{i}",
                    title=f"Result {i} for query: {query[:30]}...",
                    content=generate_test_content(100),
                    platform=random.choice(["gmail", "slack", "discord"]),
                    score=random.uniform(0.7, 1.0),
                    timestamp=datetime.utcnow()
                ) for i in range(result_count)
            ]
            mock_result.stats = AsyncMock()
            mock_result.stats.total_results = result_count
            mock_result.stats.processing_time_ms = processing_time * 1000
            mock_result.query = AsyncMock()
            mock_result.suggestions = []
            mock_result.facets = {}

            return mock_result

        mock_search_agent.search.side_effect = mock_search_with_delay

        # Generate diverse search queries
        search_queries = [
            "meeting with John about project",
            "budget planning Q2 2024",
            "proposal from Acme Corp",
            "follow up email Sarah",
            "conference call schedule",
            "document review feedback",
            "team restructuring plan",
            "quarterly review results",
            "product launch timeline",
            "market analysis report"
        ] * 10  # 100 total queries

        with patch('services.ai.search.agent.HybridSearchAgent', return_value=mock_search_agent):
            start_time = time.time()

            # Execute searches with controlled concurrency
            semaphore = asyncio.Semaphore(20)  # Limit concurrent searches

            async def limited_search(query):
                async with semaphore:
                    return await mock_search_agent.search(query)

            # Run concurrent searches
            tasks = [limited_search(query) for query in search_queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            total_time = end_time - start_time

            # Analyze results
            successful_searches = [
                r for r in results if not isinstance(r, Exception)]
            success_rate = len(successful_searches) / len(search_queries)
            throughput = len(search_queries) / total_time

            # Calculate response time statistics
            if successful_searches:
                response_times = [r.stats.processing_time_ms /
                                  1000 for r in successful_searches]
                avg_response_time = statistics.mean(response_times)
                p95_response_time = statistics.quantiles(response_times, n=20)[
                    18]  # 95th percentile
            else:
                avg_response_time = 0
                p95_response_time = 0

            # Assertions
            assert success_rate > 0.95, f"Search success rate {success_rate:.2%} below 95%"
            assert throughput > 10, f"Search throughput {throughput:.1f} searches/sec too low"
            assert avg_response_time < 1.0, f"Average response time {avg_response_time:.3f}s too slow"
            assert p95_response_time < 2.0, f"95th percentile response time {p95_response_time:.3f}s too slow"

            print(f"Search Performance Load Test Results:")
            print(
                f"  Searches completed: {len(successful_searches)}/{len(search_queries)}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Throughput: {throughput:.1f} searches/second")
            print(f"  Average response time: {avg_response_time:.3f}s")
            print(f"  95th percentile response time: {p95_response_time:.3f}s")
            print(f"  Success rate: {success_rate:.2%}")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_search_with_large_result_sets(self, ai_test_user):
        """Test search performance with large result sets."""

        mock_search_agent = AsyncMock(spec=HybridSearchAgent)

        async def mock_large_result_search(query, limit=10, *args, **kwargs):
            # Simulate processing time for large result sets
            result_count = min(limit, 1000)  # Cap at 1000 results
            # 100ms base + 1ms per result
            processing_time = 0.1 + (result_count * 0.001)
            await asyncio.sleep(processing_time)

            mock_result = AsyncMock()
            mock_result.results = [
                AsyncMock(
                    id=f"large_result_{i}",
                    title=f"Large Result {i}",
                    content=generate_test_content(200),
                    platform=random.choice(["gmail", "slack", "discord"]),
                    score=random.uniform(0.5, 1.0),
                    timestamp=datetime.utcnow()
                ) for i in range(result_count)
            ]
            mock_result.stats = AsyncMock()
            mock_result.stats.total_results = result_count
            mock_result.stats.processing_time_ms = processing_time * 1000

            return mock_result

        mock_search_agent.search.side_effect = mock_large_result_search

        # Test with various result set sizes
        test_cases = [
            ("small", 10),
            ("medium", 50),
            ("large", 100),
            ("very_large", 500)
        ]

        with patch('services.ai.search.agent.HybridSearchAgent', return_value=mock_search_agent):

            for case_name, limit in test_cases:
                start_time = time.time()

                # Run multiple searches with this limit
                tasks = [
                    mock_search_agent.search(f"test query {i}", limit=limit)
                    for i in range(10)
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                end_time = time.time()
                total_time = end_time - start_time

                successful_results = [
                    r for r in results if not isinstance(r, Exception)]
                avg_time = total_time / len(tasks)

                # Assertions based on result set size
                max_time_per_search = {
                    "small": 0.5,
                    "medium": 1.0,
                    "large": 2.0,
                    "very_large": 5.0
                }

                assert len(successful_results) == len(
                    tasks), f"Not all {case_name} searches succeeded"
                assert avg_time < max_time_per_search[case_name], \
                    f"{case_name} search avg time {avg_time:.3f}s exceeds {max_time_per_search[case_name]}s"

                print(f"{case_name.title()} Result Set Test (limit={limit}):")
                print(f"  Average time per search: {avg_time:.3f}s")
                print(f"  Total time for 10 searches: {total_time:.2f}s")


class TestAIMemoryLoad:
    """Test AI memory and context management under load."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_proactive_memory_load(self, ai_test_user, mock_fast_ai_engine):
        """Test proactive memory agent under load."""

        # Mock proactive memory agent
        mock_memory_agent = AsyncMock(spec=ProactiveMemoryAgent)

        async def mock_process_memory(*args, **kwargs):
            await asyncio.sleep(0.08)  # 80ms processing time
            return {
                "commitments": [
                    {"description": "Follow up on proposal",
                        "due_date": "2024-01-20", "priority": "high"}
                ],
                "contacts": [
                    {"name": "John Doe", "last_interaction": "2024-01-15",
                        "relationship": "colleague"}
                ],
                "files": [
                    {"name": "proposal.pdf", "shared_with": "John Doe",
                        "date": "2024-01-15"}
                ],
                "nudges": [
                    {"type": "follow_up", "message": "Remember to follow up with John",
                        "priority": "medium"}
                ]
            }

        mock_memory_agent.process_message_for_memory.side_effect = mock_process_memory

        # Generate test messages for memory processing
        message_count = 100
        test_messages = []

        for i in range(message_count):
            message = NormalizedMessage(
                platform="gmail",
                platform_message_id=f"memory_test_{i}",
                platform_thread_id=f"memory_thread_{i % 20}",
                content=MessageContent(text=generate_test_content(200)),
                participants=[
                    Participant(
                        platform="gmail",
                        platform_user_id=f"user{i % 10}@example.com",
                        display_name=f"User {i % 10}",
                        email=f"user{i % 10}@example.com"
                    )
                ],
                timestamp=datetime.utcnow(),
                raw_data={}
            )
            test_messages.append(message)

        with patch('services.ai.memory.agent.ProactiveMemoryAgent', return_value=mock_memory_agent):
            start_time = time.time()

            # Process messages for memory in batches
            batch_size = 20
            all_memory_results = []

            for i in range(0, message_count, batch_size):
                batch = test_messages[i:i + batch_size]

                tasks = [mock_memory_agent.process_message_for_memory(
                    msg) for msg in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                successful_results = [
                    r for r in batch_results if not isinstance(r, Exception)]
                all_memory_results.extend(successful_results)

            end_time = time.time()
            total_time = end_time - start_time

            # Performance metrics
            success_rate = len(all_memory_results) / message_count
            throughput = message_count / total_time

            # Assertions
            assert success_rate > 0.90, f"Memory processing success rate {success_rate:.2%} below 90%"
            assert throughput > 10, f"Memory processing throughput {throughput:.1f} messages/sec too low"
            assert total_time < 15, f"Total memory processing time {total_time:.2f}s too long"

            print(f"Proactive Memory Load Test Results:")
            print(
                f"  Messages processed: {len(all_memory_results)}/{message_count}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Throughput: {throughput:.1f} messages/second")
            print(f"  Success rate: {success_rate:.2%}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
