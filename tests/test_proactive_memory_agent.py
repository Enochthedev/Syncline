"""
Unit tests for the Proactive Memory Agent.

Tests commitment tracking, contact dossier generation, file tracking,
and nudge generation functionality.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.ai.memory.agent import ProactiveMemoryAgent
from services.ai.memory.types import (
    Commitment,
    CommitmentStatus,
    CommitmentType,
    ContactDossier,
    FileReference,
    Nudge,
    NudgeType,
    NudgePriority,
    RelationshipInsight,
    MemoryContext,
    MemoryAnalysisResult
)
from services.message_schema import NormalizedMessage


class TestProactiveMemoryAgent:
    """Test suite for ProactiveMemoryAgent."""

    @pytest.fixture
    def agent(self):
        """Create a ProactiveMemoryAgent instance for testing."""
        return ProactiveMemoryAgent()

    @pytest.fixture
    def sample_message(self):
        """Create a sample normalized message for testing."""
        from services.message_schema import Participant, MessageContent, Platform

        sender = Participant(
            id=str(uuid4()),
            display_name="John Doe",
            email="john@example.com"
        )
        recipient = Participant(
            id=str(uuid4()),
            display_name="Jane Smith",
            email="jane@example.com"
        )
        content = MessageContent(
            text="I'll send you the report by tomorrow. Let me know if you need anything else."
        )

        return NormalizedMessage(
            id=str(uuid4()),
            platform=Platform.GMAIL,
            thread_id=str(uuid4()),
            sender=sender,
            recipients=[recipient],
            content=content,
            timestamp=datetime.utcnow(),
            attachments=[],
            metadata={}
        )

    @pytest.fixture
    def sample_message_with_attachment(self):
        """Create a sample message with attachments."""
        from services.message_schema import Participant, MessageContent, Attachment, Platform, AttachmentType

        sender = Participant(
            id=str(uuid4()),
            display_name="Alice Johnson"
        )
        recipient = Participant(
            id=str(uuid4()),
            display_name="Bob Wilson"
        )
        content = MessageContent(
            text="Here's the project proposal document we discussed."
        )
        attachment = Attachment(
            filename="project_proposal.pdf",
            mime_type="application/pdf",
            file_size=1024000,
            storage_url="https://example.com/files/project_proposal.pdf",
            attachment_type=AttachmentType.DOCUMENT
        )

        return NormalizedMessage(
            id=str(uuid4()),
            platform=Platform.SLACK,
            thread_id=str(uuid4()),
            sender=sender,
            recipients=[recipient],
            content=content,
            timestamp=datetime.utcnow(),
            attachments=[attachment],
            metadata={}
        )

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test that the agent initializes correctly."""
        assert agent.name == "proactive_memory_agent"
        assert agent.provider.value == "ollama"
        assert agent.model == "tinyllama:latest"
        assert isinstance(agent._commitments, dict)
        assert isinstance(agent._files, dict)
        assert isinstance(agent._dossiers, dict)
        assert isinstance(agent._nudges, dict)

    @pytest.mark.asyncio
    async def test_commitment_tracking_basic(self, agent, sample_message):
        """Test basic commitment extraction from messages."""
        with patch.object(agent, '_build_commitment_prompt') as mock_prompt, \
                patch('services.ai.memory.agent.get_provider') as mock_get_provider:

            # Mock AI provider response
            mock_provider = AsyncMock()
            mock_provider.generate_text.return_value = '''[
                {
                    "type": "task",
                    "description": "Send report by tomorrow",
                    "due_date": "tomorrow",
                    "confidence_score": 0.9
                }
            ]'''
            mock_get_provider.return_value = mock_provider
            mock_prompt.return_value = "test prompt"

            # Track commitments
            commitments = await agent.track_commitment(sample_message)

            # Verify results
            assert len(commitments) == 1
            commitment = commitments[0]
            assert commitment.type == CommitmentType.TASK
            assert "Send report by tomorrow" in commitment.description
            assert commitment.committed_by == sample_message.sender.id
            assert commitment.source_message_id == sample_message.id
            assert commitment.confidence_score == 0.9

    @pytest.mark.asyncio
    async def test_commitment_tracking_no_commitments(self, agent):
        """Test commitment tracking when no commitments are found."""
        from services.message_schema import Participant, MessageContent, Platform

        sender = Participant(
            id=str(uuid4()),
            display_name="John Doe"
        )
        content = MessageContent(
            text="Just saying hello! How are you doing?"
        )

        message = NormalizedMessage(
            id=str(uuid4()),
            platform=Platform.GMAIL,
            thread_id=str(uuid4()),
            sender=sender,
            recipients=[],
            content=content,
            timestamp=datetime.utcnow(),
            attachments=[],
            metadata={}
        )

        with patch('services.ai.memory.agent.get_provider') as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.generate_text.return_value = "[]"
            mock_get_provider.return_value = mock_provider

            commitments = await agent.track_commitment(message)
            assert len(commitments) == 0

    @pytest.mark.asyncio
    async def test_file_reference_tracking_attachments(self, agent, sample_message_with_attachment):
        """Test file reference tracking from message attachments."""
        files = await agent.track_file_reference(sample_message_with_attachment)

        assert len(files) >= 1
        file_ref = files[0]
        assert file_ref.filename == "project_proposal.pdf"
        assert file_ref.file_type == "application/pdf"
        assert file_ref.file_size == 1024000
        assert file_ref.shared_by == sample_message_with_attachment.sender.id
        assert file_ref.source_message_id == sample_message_with_attachment.id

    @pytest.mark.asyncio
    async def test_file_reference_tracking_ai_extraction(self, agent, sample_message):
        """Test AI-based file reference extraction from message content."""
        with patch.object(agent, '_extract_file_references_ai') as mock_extract:
            mock_file = FileReference(
                filename="mentioned_document.docx",
                file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                shared_by=sample_message.sender.id,
                content_summary="Document mentioned in conversation"
            )
            mock_extract.return_value = [mock_file]

            files = await agent.track_file_reference(sample_message)

            assert len(files) == 1
            assert files[0].filename == "mentioned_document.docx"
            mock_extract.assert_called_once_with(sample_message)

    @pytest.mark.asyncio
    async def test_contact_dossier_generation(self, agent):
        """Test contact dossier generation."""
        contact_id = str(uuid4())
        user_id = str(uuid4())

        with patch.object(agent, '_get_contact_info') as mock_get_contact, \
                patch.object(agent, '_generate_relationship_insights') as mock_insights, \
                patch.object(agent, '_generate_contact_summary') as mock_summary, \
                patch('services.ai.memory.agent.get_async_session'):

            # Mock contact info
            mock_get_contact.return_value = {
                'name': 'John Doe',
                'email': 'john@example.com',
                'platforms': {'email': 'john@example.com'},
                'first_interaction': datetime.utcnow() - timedelta(days=30),
                'last_interaction': datetime.utcnow() - timedelta(days=1),
                'total_messages': 25,
                'total_threads': 5
            }

            # Mock relationship insights
            mock_insights.return_value = RelationshipInsight(
                contact_id=contact_id,
                contact_name="John Doe",
                relationship_strength=0.8,
                communication_style="professional",
                common_topics=["work", "projects"]
            )

            # Mock summary
            mock_summary.return_value = "Professional contact with regular communication about work projects."

            # Generate dossier
            dossier = await agent.generate_contact_dossier(contact_id, user_id)

            # Verify results
            assert dossier.contact_id == contact_id
            assert dossier.name == "John Doe"
            assert dossier.email == "john@example.com"
            assert dossier.total_messages == 25
            assert dossier.relationship_insights.relationship_strength == 0.8
            assert "Professional contact" in dossier.summary

    @pytest.mark.asyncio
    async def test_nudge_generation_commitment_overdue(self, agent):
        """Test nudge generation for overdue commitments."""
        user_id = str(uuid4())

        # Add an overdue commitment
        overdue_commitment = Commitment(
            type=CommitmentType.TASK,
            description="Submit quarterly report",
            committed_by=user_id,
            due_date=datetime.utcnow() - timedelta(days=2),
            status=CommitmentStatus.PENDING
        )
        agent._commitments[overdue_commitment.id] = overdue_commitment

        # Generate nudges
        nudges = await agent.generate_nudges(user_id)

        # Verify overdue nudge was created
        overdue_nudges = [n for n in nudges if n.type ==
                          NudgeType.DEADLINE_REMINDER and n.priority == NudgePriority.URGENT]
        assert len(overdue_nudges) > 0

        nudge = overdue_nudges[0]
        assert "due" in nudge.message.lower()
        assert nudge.related_commitment_id == overdue_commitment.id

    @pytest.mark.asyncio
    async def test_nudge_generation_commitment_due_soon(self, agent):
        """Test nudge generation for commitments due soon."""
        user_id = str(uuid4())

        # Add a commitment due tomorrow
        due_soon_commitment = Commitment(
            type=CommitmentType.DEADLINE,
            description="Prepare presentation",
            committed_by=user_id,
            due_date=datetime.utcnow() + timedelta(days=1),
            status=CommitmentStatus.PENDING
        )
        agent._commitments[due_soon_commitment.id] = due_soon_commitment

        # Generate nudges
        nudges = await agent.generate_nudges(user_id)

        # Verify due soon nudge was created
        due_soon_nudges = [n for n in nudges if n.type ==
                           NudgeType.DEADLINE_REMINDER and n.priority == NudgePriority.HIGH]
        assert len(due_soon_nudges) > 0

        nudge = due_soon_nudges[0]
        assert "due" in nudge.message.lower()
        assert nudge.related_commitment_id == due_soon_commitment.id

    @pytest.mark.asyncio
    async def test_memory_analysis_with_message(self, agent, sample_message):
        """Test comprehensive memory analysis with a message."""
        context = MemoryContext(
            user_id=str(uuid4()),
            message_id=sample_message.id
        )

        with patch.object(agent, '_get_message') as mock_get_message, \
                patch.object(agent, 'track_commitment') as mock_track_commitment, \
                patch.object(agent, 'track_file_reference') as mock_track_file, \
                patch.object(agent, 'generate_nudges') as mock_generate_nudges, \
                patch('services.ai.memory.agent.get_async_session'):

            # Mock database message
            mock_db_message = MagicMock()
            mock_db_message.id = sample_message.id
            mock_db_message.content_text = sample_message.content.text
            mock_db_message.platform = sample_message.platform
            mock_db_message.timestamp = sample_message.timestamp
            mock_db_message.metadata = {}
            mock_get_message.return_value = mock_db_message

            # Mock tracking results
            mock_commitments = [Commitment(description="Test commitment")]
            mock_files = [FileReference(filename="test.pdf")]
            mock_nudges = [Nudge(title="Test nudge", message="Test message")]

            mock_track_commitment.return_value = mock_commitments
            mock_track_file.return_value = mock_files
            mock_generate_nudges.return_value = mock_nudges

            # Perform analysis
            result = await agent.process(context)

            # Verify results
            assert isinstance(result, MemoryAnalysisResult)
            assert result.context == context
            assert len(result.commitments) == 1
            assert len(result.files) == 1
            assert len(result.nudges) == 1

    @pytest.mark.asyncio
    async def test_storage_methods(self, agent):
        """Test storage and retrieval methods."""
        user_id = str(uuid4())
        contact_id = str(uuid4())

        # Add test data
        commitment = Commitment(
            description="Test commitment",
            committed_by=user_id,
            status=CommitmentStatus.PENDING
        )
        agent._commitments[commitment.id] = commitment

        file_ref = FileReference(
            filename="test.pdf",
            shared_by=user_id,
            shared_with=[contact_id]
        )
        agent._files[file_ref.id] = file_ref

        nudge = Nudge(
            title="Test nudge",
            message="Test message",
            is_delivered=False
        )
        agent._nudges[nudge.id] = nudge

        dossier = ContactDossier(
            contact_id=contact_id,
            name="Test Contact"
        )
        agent._dossiers[contact_id] = dossier

        # Test retrieval methods
        commitments = agent.get_commitments(user_id)
        assert len(commitments) == 1
        assert commitments[0].description == "Test commitment"

        pending_commitments = agent.get_commitments(
            user_id, CommitmentStatus.PENDING)
        assert len(pending_commitments) == 1

        files = agent.get_files(user_id)
        assert len(files) == 1
        assert files[0].filename == "test.pdf"

        contact_files = agent.get_files(user_id, contact_id)
        assert len(contact_files) == 1

        nudges = agent.get_nudges(user_id)
        assert len(nudges) == 1

        undelivered_nudges = agent.get_nudges(user_id, delivered=False)
        assert len(undelivered_nudges) == 1

        retrieved_dossier = agent.get_dossier(contact_id)
        assert retrieved_dossier is not None
        assert retrieved_dossier.name == "Test Contact"

    @pytest.mark.asyncio
    async def test_prompt_building(self, agent, sample_message):
        """Test prompt building for different scenarios."""
        # Test commitment prompt
        prompt = agent._build_commitment_prompt(sample_message)
        assert "commitments" in prompt.lower()
        assert "promises" in prompt.lower()
        assert sample_message.content.text in prompt
        assert sample_message.sender.display_name in prompt

        # Test general prompt
        general_prompt = agent._build_prompt(
            {"message": sample_message})
        assert "proactive memory" in general_prompt.lower()
        assert "commitments" in general_prompt.lower()

    @pytest.mark.asyncio
    async def test_date_parsing(self, agent):
        """Test date parsing functionality."""
        # Test tomorrow parsing
        tomorrow_date = agent._parse_date("tomorrow")
        expected_tomorrow = datetime.utcnow() + timedelta(days=1)
        assert tomorrow_date is not None
        assert abs((tomorrow_date - expected_tomorrow).total_seconds()
                   ) < 3600  # Within 1 hour

        # Test next week parsing
        next_week_date = agent._parse_date("next week")
        expected_next_week = datetime.utcnow() + timedelta(weeks=1)
        assert next_week_date is not None
        # Within 1 day
        assert abs((next_week_date - expected_next_week).total_seconds()) < 86400

        # Test invalid date
        invalid_date = agent._parse_date("invalid date string")
        assert invalid_date is None

        # Test None input
        none_date = agent._parse_date(None)
        assert none_date is None

    @pytest.mark.asyncio
    async def test_error_handling(self, agent, sample_message):
        """Test error handling in various scenarios."""
        # Test commitment tracking with AI error
        with patch('services.ai.memory.agent.get_provider') as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.generate_text.side_effect = Exception(
                "AI service error")
            mock_get_provider.return_value = mock_provider

            commitments = await agent.track_commitment(sample_message)
            assert len(commitments) == 0  # Should return empty list on error

        # Test file tracking with error
        with patch.object(agent, '_extract_file_references_ai') as mock_extract:
            mock_extract.side_effect = Exception("Extraction error")

            files = await agent.track_file_reference(sample_message)
            # Should still process attachments even if AI extraction fails
            assert isinstance(files, list)

        # Test dossier generation with missing contact
        with patch.object(agent, '_get_contact_info') as mock_get_contact, \
                patch('services.ai.memory.agent.get_async_session'):
            mock_get_contact.return_value = None

            with pytest.raises(ValueError, match="Contact .* not found"):
                await agent.generate_contact_dossier("nonexistent", "user123")

    @pytest.mark.asyncio
    async def test_input_validation(self, agent):
        """Test input validation."""
        # Test valid inputs
        assert agent._validate_input("test string")
        assert agent._validate_input({"key": "value"})
        assert agent._validate_input(123)

        # Test invalid inputs
        assert not agent._validate_input(None)

    @pytest.mark.asyncio
    async def test_context_preparation(self, agent, sample_message):
        """Test context preparation from different input types."""
        # Test with NormalizedMessage
        context1 = agent._prepare_context(sample_message, user_id="test_user")
        assert context1.message_id == sample_message.id
        assert context1.thread_id == sample_message.thread_id
        assert context1.platform == sample_message.platform
        assert context1.user_id == "test_user"

        # Test with MemoryContext
        original_context = MemoryContext(
            user_id="test_user", contact_id="test_contact")
        context2 = agent._prepare_context(original_context)
        assert context2 == original_context

        # Test with dict
        context3 = agent._prepare_context(
            {"user_id": "test_user"}, contact_id="test_contact")
        assert context3.user_id == "test_user"
        assert context3.contact_id == "test_contact"

    def test_stats_tracking(self, agent):
        """Test that agent statistics are properly tracked."""
        initial_stats = agent.get_stats()
        assert initial_stats['requests_processed'] == 0
        assert initial_stats['requests_failed'] == 0
        assert initial_stats['success_rate'] == 0.0
        assert initial_stats['agent_name'] == "proactive_memory_agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
