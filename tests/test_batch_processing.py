"""
Integration tests for batch processing pipelines.

Tests the complete batch processing system including:
- Digest generation accuracy and performance
- Entity graph building with relationship analysis
- Memory optimization effectiveness
- Data retention policy compliance
- Scheduler functionality and job management
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from services.batch_processing import (
    BatchScheduler,
    DigestGenerator,
    EntityGraphBuilder,
    MemoryOptimizer,
    RetentionManager
)
from services.batch_processing.types import (
    BatchJob,
    BatchJobType,
    BatchJobStatus,
    DigestType,
    EntityGraphScope,
    MemoryOptimizationType,
    RetentionPolicy,
    ScheduleConfig
)
from db.models.message import Message
from db.models.summary import Summary
from db.models.entity import Entity
from db.models.user import User
from db.models.tenant import Tenant


class TestBatchScheduler:
    """Test batch job scheduling and execution."""

    @pytest.fixture
    async def scheduler(self):
        """Create a batch scheduler for testing."""
        scheduler = BatchScheduler()
        yield scheduler
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self, scheduler):
        """Test scheduler initializes correctly."""
        assert not scheduler._running
        assert len(scheduler._jobs) == 0
        assert len(scheduler._schedules) == 0
        assert scheduler.max_concurrent_jobs > 0

    @pytest.mark.asyncio
    async def test_job_scheduling(self, scheduler):
        """Test basic job scheduling."""
        job = BatchJob(
            type=BatchJobType.DAILY_DIGEST,
            tenant_id="test-tenant",
            parameters={'test': 'value'}
        )

        job_id = await scheduler.schedule_job(job)

        assert job_id == job.id
        assert job_id in scheduler._jobs
        assert scheduler._jobs[job_id].status == BatchJobStatus.PENDING

    @pytest.mark.asyncio
    async def test_job_cancellation(self, scheduler):
        """Test job cancellation."""
        job = BatchJob(
            type=BatchJobType.DAILY_DIGEST,
            tenant_id="test-tenant"
        )

        job_id = await scheduler.schedule_job(job)
        success = await scheduler.cancel_job(job_id)

        assert success
        assert scheduler._jobs[job_id].status == BatchJobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_schedule_configuration(self, scheduler):
        """Test schedule configuration."""
        schedule = ScheduleConfig(
            job_type=BatchJobType.DAILY_DIGEST,
            cron_expression="0 6 * * *",
            name="Test Daily Digest",
            description="Test schedule"
        )

        scheduler.add_schedule(schedule)

        assert len(scheduler._schedules) == 1

    @pytest.mark.asyncio
    async def test_job_execution_mock(self, scheduler):
        """Test job execution with mock handler."""
        # Register mock handler
        mock_handler = AsyncMock(return_value="success")
        scheduler.register_job_handler(BatchJobType.DAILY_DIGEST, mock_handler)

        job = BatchJob(
            type=BatchJobType.DAILY_DIGEST,
            tenant_id="test-tenant",
            scheduled_at=datetime.utcnow() - timedelta(minutes=1)
        )

        await scheduler.schedule_job(job)
        await scheduler._execute_pending_jobs()

        # Check job was executed
        assert job.status in [BatchJobStatus.RUNNING, BatchJobStatus.COMPLETED]
        mock_handler.assert_called_once()


class TestDigestGenerator:
    """Test digest generation functionality."""

    @pytest.fixture
    def digest_generator(self):
        """Create a digest generator for testing."""
        return DigestGenerator()

    @pytest.mark.asyncio
    async def test_daily_digest_generation(self, digest_generator):
        """Test daily digest generation."""
        job = BatchJob(
            type=BatchJobType.DAILY_DIGEST,
            tenant_id="test-tenant",
            parameters={
                'digest_types': [DigestType.DAILY_PERSONAL],
                'start_date': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                'end_date': datetime.utcnow().isoformat()
            }
        )

        with patch('services.batch_processing.digest_generator.get_async_session') as mock_session:
            # Mock database session and queries
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            # Mock the _get_tenant_users method
            with patch.object(digest_generator, '_get_tenant_users', return_value=[]):
                result = await digest_generator.generate_daily_digest(job)

        assert result.success
        assert result.job_id == job.id
        assert "digest" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_weekly_digest_generation(self, digest_generator):
        """Test weekly digest generation."""
        job = BatchJob(
            type=BatchJobType.WEEKLY_DIGEST,
            tenant_id="test-tenant",
            parameters={
                'digest_types': [DigestType.WEEKLY_OVERVIEW],
                'start_date': (datetime.utcnow() - timedelta(weeks=1)).isoformat(),
                'end_date': datetime.utcnow().isoformat()
            }
        )

        with patch('services.batch_processing.digest_generator.get_async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            with patch.object(digest_generator, '_get_tenant_users', return_value=[]):
                result = await digest_generator.generate_weekly_digest(job)

        assert result.success
        assert result.job_id == job.id

    @pytest.mark.asyncio
    async def test_digest_storage(self, digest_generator):
        """Test digest storage in database."""
        from services.batch_processing.types import DigestSummary

        digest = DigestSummary(
            digest_type=DigestType.DAILY_PERSONAL,
            tenant_id="test-tenant",
            scope_id="test-user",
            title="Test Digest",
            summary="Test summary content",
            message_count=10
        )

        with patch('services.batch_processing.digest_generator.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            await digest_generator._store_digests(mock_session_instance, [digest])

            # Verify session.add was called
            mock_session_instance.add.assert_called()
            mock_session_instance.commit.assert_called_once()


class TestEntityGraphBuilder:
    """Test entity graph building functionality."""

    @pytest.fixture
    def graph_builder(self):
        """Create an entity graph builder for testing."""
        return EntityGraphBuilder()

    @pytest.mark.asyncio
    async def test_entity_graph_building(self, graph_builder):
        """Test entity graph building."""
        job = BatchJob(
            type=BatchJobType.ENTITY_GRAPH_BUILD,
            tenant_id="test-tenant",
            parameters={
                'scope': EntityGraphScope.TENANT,
                'include_relationships': True,
                'min_confidence': 0.5
            }
        )

        with patch('services.batch_processing.entity_graph_builder.get_async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            # Mock the _get_scope_data method to return empty data
            with patch.object(graph_builder, '_get_scope_data', return_value=([], [])):
                result = await graph_builder.build_entity_graph(job)

        assert result.success
        assert result.job_id == job.id

    @pytest.mark.asyncio
    async def test_relationship_building(self, graph_builder):
        """Test entity relationship building."""
        # Create mock entities and messages
        entities = [
            Mock(id="entity1", type="person", confidence=0.8),
            Mock(id="entity2", type="organization", confidence=0.9)
        ]

        messages = [
            Mock(id="msg1", timestamp=datetime.utcnow())
        ]

        with patch('services.batch_processing.entity_graph_builder.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock the query results
            mock_session_instance.execute.return_value.scalars.return_value.all.return_value = []

            relationships = await graph_builder._build_relationships(
                mock_session_instance, entities, messages, 0.5
            )

            # Should return empty list with no associations
            assert isinstance(relationships, list)

    @pytest.mark.asyncio
    async def test_community_detection(self, graph_builder):
        """Test community detection in entity graphs."""
        from services.batch_processing.types import EntityGraph

        entity_graph = EntityGraph(
            scope=EntityGraphScope.TENANT,
            scope_id="test-tenant",
            entities=["entity1", "entity2", "entity3"],
            relationships=[]
        )

        communities = await graph_builder._detect_communities(entity_graph)

        assert isinstance(communities, dict)
        assert len(communities) > 0

    @pytest.mark.asyncio
    async def test_centrality_calculation(self, graph_builder):
        """Test centrality calculation."""
        from services.batch_processing.types import EntityGraph

        entity_graph = EntityGraph(
            scope=EntityGraphScope.TENANT,
            scope_id="test-tenant",
            entities=["entity1", "entity2"],
            relationships=[]
        )

        centrality = await graph_builder._calculate_centrality(entity_graph)

        assert isinstance(centrality, dict)
        assert len(centrality) == len(entity_graph.entities)


class TestMemoryOptimizer:
    """Test memory optimization functionality."""

    @pytest.fixture
    def memory_optimizer(self):
        """Create a memory optimizer for testing."""
        return MemoryOptimizer()

    @pytest.mark.asyncio
    async def test_memory_optimization(self, memory_optimizer):
        """Test memory optimization process."""
        job = BatchJob(
            type=BatchJobType.MEMORY_OPTIMIZATION,
            tenant_id="test-tenant",
            parameters={
                'optimization_types': [MemoryOptimizationType.CONSOLIDATE_SUMMARIES],
                'dry_run': True
            }
        )

        with patch('services.batch_processing.memory_optimizer.get_async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            result = await memory_optimizer.optimize_memory(job)

        assert result.success
        assert result.job_id == job.id

    @pytest.mark.asyncio
    async def test_summary_consolidation(self, memory_optimizer):
        """Test summary consolidation."""
        with patch('services.batch_processing.memory_optimizer.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock query results
            mock_session_instance.execute.return_value.scalars.return_value.all.return_value = []

            result = await memory_optimizer._consolidate_summaries(
                mock_session_instance, "test-tenant", True, True
            )

            assert result.optimization_type == MemoryOptimizationType.CONSOLIDATE_SUMMARIES
            assert result.tenant_id == "test-tenant"

    @pytest.mark.asyncio
    async def test_duplicate_cleanup(self, memory_optimizer):
        """Test duplicate record cleanup."""
        with patch('services.batch_processing.memory_optimizer.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock query results
            mock_session_instance.execute.return_value.fetchall.return_value = []

            result = await memory_optimizer._cleanup_duplicates(
                mock_session_instance, "test-tenant", True, True
            )

            assert result.optimization_type == MemoryOptimizationType.CLEANUP_DUPLICATES


class TestRetentionManager:
    """Test data retention functionality."""

    @pytest.fixture
    def retention_manager(self):
        """Create a retention manager for testing."""
        return RetentionManager()

    @pytest.mark.asyncio
    async def test_retention_policy_application(self, retention_manager):
        """Test retention policy application."""
        job = BatchJob(
            type=BatchJobType.DATA_RETENTION,
            tenant_id="test-tenant",
            parameters={
                'policies': [RetentionPolicy.MESSAGES_90_DAYS],
                'dry_run': True
            }
        )

        with patch('services.batch_processing.retention_manager.get_async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            result = await retention_manager.apply_retention_policy(job)

        assert result.success
        assert result.job_id == job.id

    @pytest.mark.asyncio
    async def test_message_retention(self, retention_manager):
        """Test message retention policy."""
        with patch('services.batch_processing.retention_manager.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock query results
            mock_session_instance.execute.return_value.scalars.return_value.all.return_value = []

            result = await retention_manager._apply_message_retention(
                mock_session_instance, "test-tenant", RetentionPolicy.MESSAGES_90_DAYS, True, True, False
            )

            assert result.policy == RetentionPolicy.MESSAGES_90_DAYS
            assert result.tenant_id == "test-tenant"
            assert result.dry_run

    @pytest.mark.asyncio
    async def test_backup_creation(self, retention_manager):
        """Test backup creation before deletion."""
        messages = [Mock(id="msg1", content_text="test")]

        backup_location = await retention_manager._create_message_backup(messages, "test-tenant")

        assert isinstance(backup_location, str)
        assert "backup" in backup_location.lower()

    def test_retention_policy_info(self, retention_manager):
        """Test retention policy information retrieval."""
        info = retention_manager.get_retention_policy_info(
            RetentionPolicy.MESSAGES_90_DAYS)

        assert info['policy'] == RetentionPolicy.MESSAGES_90_DAYS.value
        assert info['retention_days'] == 90
        assert 'description' in info


class TestBatchProcessingIntegration:
    """Integration tests for the complete batch processing system."""

    @pytest.mark.asyncio
    async def test_end_to_end_daily_digest_flow(self):
        """Test complete daily digest generation flow."""
        scheduler = BatchScheduler()

        try:
            # Start scheduler
            await scheduler.start()

            # Create and schedule a daily digest job
            job = BatchJob(
                type=BatchJobType.DAILY_DIGEST,
                tenant_id="test-tenant",
                parameters={
                    'digest_types': [DigestType.DAILY_PERSONAL],
                    'start_date': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    'end_date': datetime.utcnow().isoformat()
                }
            )

            job_id = await scheduler.schedule_job(job)

            # Wait a moment for processing
            await asyncio.sleep(0.1)

            # Check job status
            job_status = scheduler.get_job_status(job_id)
            assert job_status is not None
            assert job_status.type == BatchJobType.DAILY_DIGEST

        finally:
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self):
        """Test batch processing performance with multiple jobs."""
        scheduler = BatchScheduler()

        try:
            await scheduler.start()

            # Schedule multiple jobs
            job_ids = []
            for i in range(5):
                job = BatchJob(
                    type=BatchJobType.DAILY_DIGEST,
                    tenant_id=f"tenant-{i}",
                    parameters={'test': f'job-{i}'}
                )
                job_id = await scheduler.schedule_job(job)
                job_ids.append(job_id)

            # Check all jobs were scheduled
            assert len(job_ids) == 5

            # Verify scheduler stats
            stats = scheduler.get_scheduler_stats()
            assert stats['jobs_scheduled'] >= 5
            assert stats['total_jobs'] >= 5

        finally:
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling and job recovery."""
        scheduler = BatchScheduler()

        # Register a handler that fails
        async def failing_handler(job):
            raise Exception("Simulated failure")

        scheduler.register_job_handler(
            BatchJobType.DAILY_DIGEST, failing_handler)

        try:
            await scheduler.start()

            job = BatchJob(
                type=BatchJobType.DAILY_DIGEST,
                tenant_id="test-tenant",
                max_retries=1
            )

            job_id = await scheduler.schedule_job(job)

            # Execute the job (should fail)
            await scheduler._execute_job(scheduler._jobs[job_id])

            # Check job failed
            failed_job = scheduler.get_job_status(job_id)
            assert failed_job.status == BatchJobStatus.FAILED
            assert failed_job.error_message is not None

        finally:
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_concurrent_job_execution(self):
        """Test concurrent execution of multiple job types."""
        scheduler = BatchScheduler()
        scheduler.max_concurrent_jobs = 3

        # Register mock handlers
        async def mock_digest_handler(job):
            await asyncio.sleep(0.1)
            return "digest_complete"

        async def mock_graph_handler(job):
            await asyncio.sleep(0.1)
            return "graph_complete"

        scheduler.register_job_handler(
            BatchJobType.DAILY_DIGEST, mock_digest_handler)
        scheduler.register_job_handler(
            BatchJobType.ENTITY_GRAPH_BUILD, mock_graph_handler)

        try:
            await scheduler.start()

            # Schedule jobs of different types
            jobs = [
                BatchJob(type=BatchJobType.DAILY_DIGEST, tenant_id="tenant-1"),
                BatchJob(type=BatchJobType.ENTITY_GRAPH_BUILD,
                         tenant_id="tenant-1"),
                BatchJob(type=BatchJobType.DAILY_DIGEST, tenant_id="tenant-2"),
            ]

            job_ids = []
            for job in jobs:
                job_id = await scheduler.schedule_job(job)
                job_ids.append(job_id)

            # Execute pending jobs
            await scheduler._execute_pending_jobs()

            # Wait for completion
            await asyncio.sleep(0.2)

            # Check jobs were processed
            stats = scheduler.get_scheduler_stats()
            assert stats['jobs_scheduled'] >= 3

        finally:
            await scheduler.stop()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
