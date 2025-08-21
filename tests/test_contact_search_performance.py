"""
Performance tests for contact-based auto-search functionality.

Tests search response times, throughput, memory usage, and scalability
under various load conditions and dataset sizes.
"""

import pytest
import asyncio
import time
import psutil
import statistics
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor

from services.contacts.contact_auto_search import ContactAutoSearchService
from db.models.unified_contact import UnifiedContact, ContactIdentity


class TestContactSearchPerformance:
    """Performance test suite for contact search functionality."""

    @pytest.fixture
    async def performance_service(self, mock_db_session):
        """Create service optimized for performance testing."""
        service = ContactAutoSearchService(mock_db_session)
        service.query_processor = Mock()
        service.query_processor.initialize = AsyncMock()
        service.query_processor.process_query = AsyncMock()
        service.query_processor.generate_search_suggestions = Mock(
            return_value=[])
        service._initialized = True
        return service

    @pytest.fixture
    def large_contact_dataset(self):
        """Create large dataset for performance testing."""
        contacts = []
        tenant_id = uuid4()
        user_id = uuid4()

        # Create diverse contact dataset
        for i in range(10000):
            contact = UnifiedContact(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                primary_name=f"Contact {i:05d}",
                display_name=f"Contact {i:05d}",
                primary_email=f"contact{i:05d}@example.com",
                primary_phone=f"+1-555-{i:04d}",
                last_interaction=datetime.utcnow() - timedelta(days=i % 365),
                total_messages=100 + (i % 500),
                platforms=["gmail", "slack"][:(i % 2) + 1],
                relationship_strength=0.1 + (i % 10) * 0.1,
                communication_frequency=[
                    "rare", "occasional", "regular", "frequent", "daily"][i % 5],
                is_favorite=(i % 100) < 10,  # 10% favorites
                tags=[f"tag{j}" for j in range(i % 5)]
            )

            # Add identities
            contact.identities = [
                ContactIdentity(
                    id=uuid4(),
                    unified_contact_id=contact.id,
                    platform="gmail",
                    platform_user_id=f"contact{i:05d}@example.com",
                    display_name=f"Contact {i:05d}",
                    email=f"contact{i:05d}@example.com"
                )
            ]

            if i % 2 == 0:  # Add Slack identity for even contacts
                contact.identities.append(
                    ContactIdentity(
                        id=uuid4(),
                        unified_contact_id=contact.id,
                        platform="slack",
                        platform_user_id=f"U{i:08d}",
                        platform_handle=f"contact{i:05d}",
                        display_name=f"Contact {i:05d}"
                    )
                )

            contacts.append(contact)

        return {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "contacts": contacts
        }

    @pytest.mark.asyncio
    async def test_search_response_time(self, performance_service, large_contact_dataset):
        """Test search response time under normal conditions."""
        # Mock database response with realistic pagination
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = large_contact_dataset[
            "contacts"][:50]
        performance_service.db.execute.return_value = mock_result

        # Test various query types
        test_queries = [
            "John",
            "john.smith@example.com",
            "+1-555-0123",
            "Contact 00001",
            "slack_handle"
        ]

        response_times = []

        for query in test_queries:
            start_time = time.perf_counter()

            result = await performance_service.search_contacts_realtime(
                query=query,
                tenant_id=large_contact_dataset["tenant_id"],
                user_id=large_contact_dataset["user_id"],
                limit=50
            )

            end_time = time.perf_counter()
            response_time = (end_time - start_time) * \
                1000  # Convert to milliseconds
            response_times.append(response_time)

            # Verify we got results
            assert len(result["contacts"]) > 0

        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        print(f"Response time stats (ms):")
        print(f"  Average: {avg_response_time:.2f}")
        print(f"  Min: {min_response_time:.2f}")
        print(f"  Max: {max_response_time:.2f}")

        # Performance assertions (adjust thresholds as needed)
        assert avg_response_time < 100, f"Average response time too high: {avg_response_time:.2f}ms"
        assert max_response_time < 200, f"Max response time too high: {max_response_time:.2f}ms"

    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self, performance_service, large_contact_dataset):
        """Test performance under concurrent search requests."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = large_contact_dataset[
            "contacts"][:50]
        performance_service.db.execute.return_value = mock_result

        # Create concurrent search tasks
        concurrent_requests = 50
        queries = [f"Contact {i:05d}" for i in range(concurrent_requests)]

        async def single_search(query):
            start_time = time.perf_counter()
            result = await performance_service.search_contacts_realtime(
                query=query,
                tenant_id=large_contact_dataset["tenant_id"],
                user_id=large_contact_dataset["user_id"],
                limit=20
            )
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000, len(result["contacts"])

        # Execute concurrent searches
        start_time = time.perf_counter()
        tasks = [single_search(query) for query in queries]
        results = await asyncio.gather(*tasks)
        total_time = (time.perf_counter() - start_time) * 1000

        # Analyze results
        response_times = [r[0] for r in results]
        result_counts = [r[1] for r in results]

        avg_response_time = statistics.mean(response_times)
        throughput = concurrent_requests / \
            (total_time / 1000)  # requests per second

        print(f"Concurrent search performance:")
        print(f"  Concurrent requests: {concurrent_requests}")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  Throughput: {throughput:.2f} requests/second")

        # Performance assertions
        assert avg_response_time < 150, f"Concurrent average response time too high: {avg_response_time:.2f}ms"
        assert throughput > 10, f"Throughput too low: {throughput:.2f} requests/second"
        assert all(
            count > 0 for count in result_counts), "Some searches returned no results"

    @pytest.mark.asyncio
    async def test_memory_usage_during_search(self, performance_service, large_contact_dataset):
        """Test memory usage during search operations."""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Mock database response with large dataset
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = large_contact_dataset[
            "contacts"][:1000]
        performance_service.db.execute.return_value = mock_result

        memory_measurements = []

        # Perform multiple searches and measure memory
        for i in range(100):
            await performance_service.search_contacts_realtime(
                query=f"Contact {i:05d}",
                tenant_id=large_contact_dataset["tenant_id"],
                user_id=large_contact_dataset["user_id"],
                limit=100
            )

            if i % 10 == 0:  # Measure every 10 searches
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_measurements.append(current_memory)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        max_memory = max(memory_measurements)

        print(f"Memory usage during search:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")
        print(f"  Peak: {max_memory:.2f} MB")

        # Memory usage assertions (adjust thresholds as needed)
        assert memory_increase < 50, f"Memory increase too high: {memory_increase:.2f} MB"
        assert max_memory < initial_memory + \
            100, f"Peak memory usage too high: {max_memory:.2f} MB"

    @pytest.mark.asyncio
    async def test_search_scalability(self, performance_service):
        """Test search performance with increasing dataset sizes."""
        dataset_sizes = [100, 500, 1000, 5000, 10000]
        performance_results = []

        for size in dataset_sizes:
            # Create dataset of specific size
            contacts = []
            tenant_id = uuid4()
            user_id = uuid4()

            for i in range(size):
                contact = UnifiedContact(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    primary_name=f"Contact {i:05d}",
                    display_name=f"Contact {i:05d}",
                    primary_email=f"contact{i:05d}@example.com"
                )
                contacts.append(contact)

            # Mock database response
            mock_result = Mock()
            # Simulate pagination
            mock_result.scalars.return_value.all.return_value = contacts[:50]
            performance_service.db.execute.return_value = mock_result

            # Measure search performance
            start_time = time.perf_counter()

            result = await performance_service.search_contacts_realtime(
                query="Contact",
                tenant_id=tenant_id,
                user_id=user_id,
                limit=50
            )

            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000

            performance_results.append({
                "dataset_size": size,
                "response_time": response_time,
                "results_count": len(result["contacts"])
            })

            print(f"Dataset size {size}: {response_time:.2f}ms")

        # Analyze scalability
        response_times = [r["response_time"] for r in performance_results]

        # Check that response time doesn't increase dramatically with dataset size
        # (This assumes proper database indexing and pagination)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        scalability_ratio = max_response_time / min_response_time

        print(f"Scalability analysis:")
        print(f"  Min response time: {min_response_time:.2f}ms")
        print(f"  Max response time: {max_response_time:.2f}ms")
        print(f"  Scalability ratio: {scalability_ratio:.2f}")

        # Should scale reasonably well with proper indexing
        assert scalability_ratio < 5.0, f"Poor scalability: {scalability_ratio:.2f}x increase"
        assert max_response_time < 300, f"Response time too high for large dataset: {max_response_time:.2f}ms"

    @pytest.mark.asyncio
    async def test_fuzzy_search_performance(self, performance_service, large_contact_dataset):
        """Test performance of fuzzy matching algorithms."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = large_contact_dataset[
            "contacts"][:100]
        performance_service.db.execute.return_value = mock_result

        # Test fuzzy search with various query types
        fuzzy_queries = [
            ("Jon Smith", "John Smith"),      # Typo
            ("Contct 00001", "Contact 00001"),  # Missing letter
            ("J Smith", "John Smith"),        # Abbreviated
            ("smith@example", "john.smith@example.com"),  # Partial email
            ("555-0123", "+1-555-0123"),     # Partial phone
        ]

        fuzzy_performance = []

        for fuzzy_query, expected_match in fuzzy_queries:
            start_time = time.perf_counter()

            result = await performance_service.search_contacts_realtime(
                query=fuzzy_query,
                tenant_id=large_contact_dataset["tenant_id"],
                user_id=large_contact_dataset["user_id"],
                limit=50
            )

            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000

            fuzzy_performance.append({
                "query": fuzzy_query,
                "response_time": response_time,
                "results_count": len(result["contacts"])
            })

        avg_fuzzy_time = statistics.mean(
            [r["response_time"] for r in fuzzy_performance])

        print(f"Fuzzy search performance:")
        for result in fuzzy_performance:
            print(
                f"  '{result['query']}': {result['response_time']:.2f}ms ({result['results_count']} results)")
        print(f"  Average: {avg_fuzzy_time:.2f}ms")

        # Fuzzy search should still be reasonably fast
        assert avg_fuzzy_time < 150, f"Fuzzy search too slow: {avg_fuzzy_time:.2f}ms"
        assert all(r["results_count"] >
                   0 for r in fuzzy_performance), "Some fuzzy searches returned no results"

    @pytest.mark.asyncio
    async def test_suggestion_generation_performance(self, performance_service, large_contact_dataset):
        """Test performance of search suggestion generation."""
        # Mock database responses for suggestions
        name_result = Mock()
        name_result.fetchall.return_value = [
            (f"Contact {i:05d}", f"Contact {i:05d}", uuid4())
            for i in range(20)
        ]

        handle_result = Mock()
        handle_result.fetchall.return_value = [
            (f"handle{i:05d}", "slack", f"Contact {i:05d}", uuid4())
            for i in range(10)
        ]

        recent_result = Mock()
        recent_result.scalars.return_value.all.return_value = large_contact_dataset[
            "contacts"][:10]

        performance_service.db.execute.side_effect = [
            name_result, handle_result, recent_result]

        # Test suggestion generation performance
        start_time = time.perf_counter()

        suggestions = await performance_service._generate_contact_suggestions(
            query="Con",
            tenant_id=large_contact_dataset["tenant_id"],
            user_id=large_contact_dataset["user_id"],
            limit=10
        )

        end_time = time.perf_counter()
        suggestion_time = (end_time - start_time) * 1000

        print(f"Suggestion generation performance:")
        print(f"  Time: {suggestion_time:.2f}ms")
        print(f"  Suggestions count: {len(suggestions)}")

        # Suggestions should be generated quickly
        assert suggestion_time < 50, f"Suggestion generation too slow: {suggestion_time:.2f}ms"
        assert len(suggestions) > 0, "No suggestions generated"

    @pytest.mark.asyncio
    async def test_natural_language_processing_performance(self, performance_service, large_contact_dataset):
        """Test performance of natural language query processing."""
        # Mock query processor with realistic processing time
        async def mock_process_query(query):
            # Simulate AI processing time
            await asyncio.sleep(0.01)  # 10ms processing time
            return query

        performance_service.query_processor.process_query = mock_process_query

        # Mock contact search
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = large_contact_dataset[
            "contacts"][:5]
        performance_service.db.execute.return_value = mock_result

        # Test various natural language queries
        nl_queries = [
            "messages with John Smith",
            "files shared with Sarah last week",
            "what did I promise to Mike about the project",
            "conversations with team members yesterday",
            "images sent by Alice"
        ]

        nl_performance = []

        for query in nl_queries:
            start_time = time.perf_counter()

            result = await performance_service.process_natural_language_query(
                query=query,
                tenant_id=large_contact_dataset["tenant_id"],
                user_id=large_contact_dataset["user_id"]
            )

            end_time = time.perf_counter()
            processing_time = (end_time - start_time) * 1000

            nl_performance.append({
                "query": query,
                "processing_time": processing_time,
                "intent": result.get("intent", "unknown")
            })

        avg_nl_time = statistics.mean(
            [r["processing_time"] for r in nl_performance])

        print(f"Natural language processing performance:")
        for result in nl_performance:
            print(
                f"  '{result['query'][:30]}...': {result['processing_time']:.2f}ms ({result['intent']})")
        print(f"  Average: {avg_nl_time:.2f}ms")

        # NLP processing should complete within reasonable time
        assert avg_nl_time < 100, f"NLP processing too slow: {avg_nl_time:.2f}ms"

    @pytest.mark.asyncio
    async def test_cache_performance_impact(self, performance_service, large_contact_dataset):
        """Test impact of caching on search performance."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = large_contact_dataset[
            "contacts"][:50]
        performance_service.db.execute.return_value = mock_result

        query = "Contact 00001"
        tenant_id = large_contact_dataset["tenant_id"]
        user_id = large_contact_dataset["user_id"]

        # First search (cold cache)
        start_time = time.perf_counter()
        result1 = await performance_service.search_contacts_realtime(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            limit=50
        )
        cold_cache_time = (time.perf_counter() - start_time) * 1000

        # Second search (warm cache - if caching is implemented)
        start_time = time.perf_counter()
        result2 = await performance_service.search_contacts_realtime(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            limit=50
        )
        warm_cache_time = (time.perf_counter() - start_time) * 1000

        print(f"Cache performance impact:")
        print(f"  Cold cache: {cold_cache_time:.2f}ms")
        print(f"  Warm cache: {warm_cache_time:.2f}ms")
        print(
            f"  Improvement: {((cold_cache_time - warm_cache_time) / cold_cache_time * 100):.1f}%")

        # Results should be consistent
        assert len(result1["contacts"]) == len(result2["contacts"])

        # Warm cache should be at least as fast (or faster if caching is implemented)
        assert warm_cache_time <= cold_cache_time * 1.1  # Allow 10% variance

    @pytest.mark.asyncio
    async def test_database_query_optimization(self, performance_service, large_contact_dataset):
        """Test database query performance and optimization."""
        # Mock database execution tracking
        query_count = 0
        original_execute = performance_service.db.execute

        async def counting_execute(query):
            nonlocal query_count
            query_count += 1
            # Simulate database query time
            await asyncio.sleep(0.001)  # 1ms per query
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = large_contact_dataset[
                "contacts"][:50]
            return mock_result

        performance_service.db.execute = counting_execute

        # Perform search
        start_time = time.perf_counter()

        result = await performance_service.search_contacts_realtime(
            query="Contact 00001",
            tenant_id=large_contact_dataset["tenant_id"],
            user_id=large_contact_dataset["user_id"],
            limit=50,
            include_suggestions=True
        )

        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000

        print(f"Database query optimization:")
        print(f"  Total queries executed: {query_count}")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Average time per query: {total_time/query_count:.2f}ms")
        print(f"  Results returned: {len(result['contacts'])}")

        # Should minimize database queries
        assert query_count <= 5, f"Too many database queries: {query_count}"
        assert total_time < 200, f"Total query time too high: {total_time:.2f}ms"


class TestLoadTesting:
    """Load testing for contact search under stress conditions."""

    @pytest.mark.asyncio
    async def test_sustained_load(self, performance_service, large_contact_dataset):
        """Test performance under sustained load."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = large_contact_dataset[
            "contacts"][:50]
        performance_service.db.execute.return_value = mock_result

        # Sustained load parameters
        duration_seconds = 10
        requests_per_second = 20
        total_requests = duration_seconds * requests_per_second

        async def sustained_search(request_id):
            query = f"Contact {request_id % 1000:05d}"
            start_time = time.perf_counter()

            result = await performance_service.search_contacts_realtime(
                query=query,
                tenant_id=large_contact_dataset["tenant_id"],
                user_id=large_contact_dataset["user_id"],
                limit=20
            )

            end_time = time.perf_counter()
            return {
                "request_id": request_id,
                "response_time": (end_time - start_time) * 1000,
                "results_count": len(result["contacts"]),
                "timestamp": end_time
            }

        # Execute sustained load
        print(
            f"Starting sustained load test: {requests_per_second} req/s for {duration_seconds}s")

        start_time = time.perf_counter()
        tasks = []

        for i in range(total_requests):
            task = sustained_search(i)
            tasks.append(task)

            # Control request rate
            if i > 0 and i % requests_per_second == 0:
                await asyncio.sleep(1.0)

        results = await asyncio.gather(*tasks)
        total_duration = time.perf_counter() - start_time

        # Analyze results
        response_times = [r["response_time"] for r in results]
        successful_requests = len(
            [r for r in results if r["results_count"] > 0])

        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[
            18]  # 95th percentile
        actual_throughput = total_requests / total_duration

        print(f"Sustained load test results:")
        print(f"  Total requests: {total_requests}")
        print(f"  Successful requests: {successful_requests}")
        print(f"  Success rate: {successful_requests/total_requests*100:.1f}%")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  95th percentile response time: {p95_response_time:.2f}ms")
        print(f"  Actual throughput: {actual_throughput:.2f} req/s")

        # Performance assertions for sustained load
        assert successful_requests / \
            total_requests >= 0.95, "Success rate too low under sustained load"
        assert avg_response_time < 200, f"Average response time too high under load: {avg_response_time:.2f}ms"
        assert p95_response_time < 500, f"95th percentile response time too high: {p95_response_time:.2f}ms"

    @pytest.mark.asyncio
    async def test_burst_load(self, performance_service, large_contact_dataset):
        """Test performance under burst load conditions."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = large_contact_dataset[
            "contacts"][:50]
        performance_service.db.execute.return_value = mock_result

        # Burst load parameters
        burst_size = 100
        burst_queries = [f"Contact {i:05d}" for i in range(burst_size)]

        # Execute burst load
        print(f"Starting burst load test: {burst_size} concurrent requests")

        start_time = time.perf_counter()

        async def burst_search(query):
            result = await performance_service.search_contacts_realtime(
                query=query,
                tenant_id=large_contact_dataset["tenant_id"],
                user_id=large_contact_dataset["user_id"],
                limit=20
            )
            return len(result["contacts"])

        tasks = [burst_search(query) for query in burst_queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        burst_duration = (time.perf_counter() - start_time) * 1000

        # Analyze burst results
        successful_results = [
            r for r in results if not isinstance(r, Exception) and r > 0]
        failed_results = [r for r in results if isinstance(r, Exception)]

        success_rate = len(successful_results) / burst_size
        burst_throughput = burst_size / (burst_duration / 1000)

        print(f"Burst load test results:")
        print(f"  Burst size: {burst_size}")
        print(f"  Burst duration: {burst_duration:.2f}ms")
        print(f"  Successful requests: {len(successful_results)}")
        print(f"  Failed requests: {len(failed_results)}")
        print(f"  Success rate: {success_rate*100:.1f}%")
        print(f"  Burst throughput: {burst_throughput:.2f} req/s")

        # Burst load assertions
        assert success_rate >= 0.90, f"Burst success rate too low: {success_rate*100:.1f}%"
        assert burst_duration < 5000, f"Burst took too long: {burst_duration:.2f}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
