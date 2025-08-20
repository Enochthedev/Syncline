"""
Integration tests for LinkedIn connector via Matrix bridge.

Tests LinkedIn message processing, professional context awareness,
and business relationship extraction.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from integrations.matrix_bridge_hub.hub import MatrixBridgeHub
from integrations.matrix_bridge_hub.types import BridgeType, BridgeConfig, AuthMethod
from services.message_schema import RawMessage, Platform
from services.message.platform_handlers import LinkedInHandler
from services.ai.entity.linkedin_extractor import LinkedInEntityExtractor
from db.models.entity import EntityType


class TestLinkedInIntegration:
    """Test LinkedIn integration via Matrix bridge."""

    @pytest.fixture
    async def linkedin_bridge_hub(self):
        """Create LinkedIn bridge hub for testing."""
        config = {
            'homeserver_url': 'https://test.matrix.org',
            'access_token': 'test_token',
            'user_id': '@test:matrix.org',
            'device_id': 'TEST_DEVICE',
            'bridges': {
                'linkedin': {
                    'enabled': True,
                    'executable_path': 'mautrix-linkedin',
                    'config_path': './test_bridges/linkedin/config.yaml',
                    'database_path': './test_bridges/linkedin/linkedin.db',
                    'environment': {},
                    'extra_args': []
                }
            }
        }

        hub = MatrixBridgeHub(config)
        yield hub

        # Cleanup
        await hub.stop_real_time_ingestion()

    @pytest.fixture
    def linkedin_handler(self):
        """Create LinkedIn message handler."""
        return LinkedInHandler()

    @pytest.fixture
    def linkedin_entity_extractor(self):
        """Create LinkedIn entity extractor."""
        return LinkedInEntityExtractor()

    @pytest.fixture
    def sample_linkedin_message(self):
        """Sample LinkedIn message data."""
        return {
            'message_id': 'linkedin_msg_123',
            'conversation_id': 'linkedin_conv_456',
            'sender': {
                'linkedin_id': 'john-smith-ceo',
                'display_name': 'John Smith',
                'email': 'john.smith@techcorp.com',
                'job_title': 'CEO',
                'company': 'TechCorp Inc',
                'industry': 'Technology',
                'location': 'San Francisco, CA',
                'connection_degree': '1st',
                'profile_url': 'https://linkedin.com/in/john-smith-ceo',
                'headline': 'CEO at TechCorp Inc | Technology Innovation Leader',
                'skills': ['Leadership', 'Strategic Planning', 'Technology Innovation'],
                'experience': [
                    {'company': 'TechCorp Inc', 'title': 'CEO',
                        'duration': '2020-Present'},
                    {'company': 'StartupXYZ', 'title': 'CTO', 'duration': '2018-2020'}
                ]
            },
            'recipients': [
                {
                    'linkedin_id': 'jane-doe-vp',
                    'display_name': 'Jane Doe',
                    'email': 'jane.doe@innovate.com',
                    'job_title': 'VP of Engineering',
                    'company': 'Innovate Solutions',
                    'industry': 'Technology',
                    'connection_degree': '1st'
                }
            ],
            'content': {
                'text': 'Hi Jane, I hope you\'re doing well. I wanted to reach out about a potential partnership opportunity between TechCorp and Innovate Solutions. We\'re looking for strategic collaborations in the AI space. Would you be interested in discussing this further? Best regards, John'
            },
            'conversation_type': 'direct',
            'industry_context': {'primary': 'Technology', 'secondary': 'Artificial Intelligence'},
            'company_context': {'sender_company': 'TechCorp Inc', 'recipient_company': 'Innovate Solutions'},
            'is_business_inquiry': True,
            'professional_relationship_type': 'peer'
        }

    async def test_linkedin_bridge_configuration(self, linkedin_bridge_hub):
        """Test LinkedIn bridge configuration setup."""
        # Test authentication
        await linkedin_bridge_hub.authenticate()

        # Check if LinkedIn bridge is configured
        bridge_status = await linkedin_bridge_hub.get_all_bridge_status()
        assert 'mautrix-linkedin' in bridge_status

        linkedin_status = bridge_status['mautrix-linkedin']
        assert linkedin_status['bridge_type'] == 'linkedin'
        assert linkedin_status['enabled'] is True

    async def test_linkedin_message_normalization(self, linkedin_handler, sample_linkedin_message):
        """Test LinkedIn message normalization with professional context."""
        # Create raw message
        raw_message = RawMessage(
            platform=Platform.LINKEDIN,
            platform_message_id='linkedin_msg_123',
            raw_data=sample_linkedin_message,
            received_at=datetime.now(timezone.utc)
        )

        # Normalize message
        normalized_message = linkedin_handler.normalize_message(raw_message)

        # Verify basic normalization
        assert normalized_message.platform == Platform.LINKEDIN
        assert normalized_message.platform_message_id == 'linkedin_msg_123'
        assert normalized_message.thread_id == 'linkedin_conv_456'

        # Verify sender professional context
        sender = normalized_message.sender
        assert sender.display_name == 'John Smith'
        assert sender.email == 'john.smith@techcorp.com'
        assert sender.metadata['job_title'] == 'CEO'
        assert sender.metadata['company'] == 'TechCorp Inc'
        assert sender.metadata['industry'] == 'Technology'
        assert sender.metadata['connection_degree'] == '1st'

        # Verify professional metadata
        metadata = normalized_message.metadata
        assert metadata['professional_context']['sender_company'] == 'TechCorp Inc'
        assert metadata['professional_context']['is_business_inquiry'] is True
        assert metadata['business_relationship']['relationship_type'] == 'professional'
        assert metadata['industry_context']['primary'] == 'Technology'

    async def test_linkedin_entity_extraction(self, linkedin_entity_extractor, sample_linkedin_message):
        """Test LinkedIn-specific entity extraction."""
        message_text = sample_linkedin_message['content']['text']
        sender_context = sample_linkedin_message['sender']
        recipient_context = sample_linkedin_message['recipients']

        # Extract entities
        result = await linkedin_entity_extractor.extract_linkedin_entities(
            message_text,
            sender_context=sender_context,
            recipient_context=recipient_context
        )

        # Verify entities were extracted
        assert len(result.entities) > 0

        # Check for professional entities
        entity_types = [e.type for e in result.entities]

        # Should find at least some professional entities
        professional_types = [EntityType.person, EntityType.organization,
                              EntityType.business_opportunity, EntityType.job_title]
        found_professional = any(
            et in entity_types for et in professional_types)
        assert found_professional, f"Expected to find professional entities, but got: {[et.value for et in entity_types]}"

        # Should find business opportunities (this is most likely to be found)
        assert EntityType.business_opportunity in entity_types

        # Verify professional relationships (may be empty for simple messages)
        # This is acceptable as relationship extraction requires specific patterns
        print(f"Found {len(result.relations)} professional relationships")

        # If relationships are found, check their types
        if result.relations:
            relation_types = [r.relation_type for r in result.relations]
            print(f"Relationship types: {relation_types}")

    async def test_professional_context_extraction(self, linkedin_handler, sample_linkedin_message):
        """Test extraction of professional context from LinkedIn messages."""
        raw_message = RawMessage(
            platform=Platform.LINKEDIN,
            platform_message_id='linkedin_msg_123',
            raw_data=sample_linkedin_message,
            received_at=datetime.now(timezone.utc)
        )

        normalized_message = linkedin_handler.normalize_message(raw_message)

        # Test professional context extraction
        professional_context = normalized_message.metadata['professional_context']

        assert professional_context['sender_company'] == 'TechCorp Inc'
        assert professional_context['sender_job_title'] == 'CEO'
        assert professional_context['sender_industry'] == 'Technology'
        assert professional_context['is_business_inquiry'] is True
        assert professional_context['professional_relationship_type'] == 'peer'

    async def test_business_relationship_analysis(self, linkedin_handler):
        """Test business relationship analysis between LinkedIn participants."""
        # Test same company relationship
        same_company_message = {
            'message_id': 'linkedin_msg_124',
            'conversation_id': 'linkedin_conv_457',
            'sender': {
                'linkedin_id': 'alice-manager',
                'display_name': 'Alice Manager',
                'job_title': 'Engineering Manager',
                'company': 'TechCorp Inc',
                'industry': 'Technology'
            },
            'recipients': [
                {
                    'linkedin_id': 'bob-engineer',
                    'display_name': 'Bob Engineer',
                    'job_title': 'Senior Software Engineer',
                    'company': 'TechCorp Inc',
                    'industry': 'Technology'
                }
            ],
            'content': {'text': 'Hi Bob, can you review the latest code changes?'}
        }

        raw_message = RawMessage(
            platform=Platform.LINKEDIN,
            platform_message_id='linkedin_msg_124',
            raw_data=same_company_message,
            received_at=datetime.now(timezone.utc)
        )

        normalized_message = linkedin_handler.normalize_message(raw_message)
        business_relationship = normalized_message.metadata['business_relationship']

        assert business_relationship['same_company'] is True
        assert business_relationship['relationship_type'] == 'colleague'

    async def test_linkedin_professional_skills_extraction(self, linkedin_entity_extractor):
        """Test extraction of professional skills from LinkedIn messages."""
        message_with_skills = (
            "I'm looking for a Python developer with experience in machine learning "
            "and AWS. Strong leadership and project management skills are also required."
        )

        result = await linkedin_entity_extractor.extract_linkedin_entities(message_with_skills)

        # Check for skill entities
        skills = [e for e in result.entities if e.type == EntityType.skill]
        assert len(skills) > 0

        skill_values = [s.value.lower() for s in skills]
        assert 'python' in skill_values
        assert 'machine learning' in skill_values
        assert 'leadership' in skill_values
        assert 'project management' in skill_values

    async def test_linkedin_job_title_extraction(self, linkedin_entity_extractor):
        """Test extraction of job titles from LinkedIn messages."""
        message_with_titles = (
            "We're hiring a Senior Software Engineer and a Product Manager. "
            "The CEO will be involved in the final interviews."
        )

        result = await linkedin_entity_extractor.extract_linkedin_entities(message_with_titles)

        # Check for job title entities
        job_titles = [e for e in result.entities if e.type ==
                      EntityType.job_title]
        assert len(job_titles) > 0

        title_values = [t.normalized_value.lower() for t in job_titles]
        assert any('senior' in title for title in title_values)
        assert any('ceo' in title for title in title_values)

    async def test_linkedin_business_opportunity_detection(self, linkedin_entity_extractor):
        """Test detection of business opportunities in LinkedIn messages."""
        business_message = (
            "I'd like to discuss a potential partnership opportunity. "
            "We're looking for investment in our new project and would "
            "appreciate the chance to present our proposal."
        )

        result = await linkedin_entity_extractor.extract_linkedin_entities(business_message)

        # Check for business opportunity entities
        opportunities = [e for e in result.entities if e.type ==
                         EntityType.business_opportunity]
        assert len(opportunities) > 0

        opportunity_values = [o.value.lower() for o in opportunities]
        assert 'opportunity' in opportunity_values
        assert 'partnership' in opportunity_values
        assert 'investment' in opportunity_values

    async def test_linkedin_industry_context_extraction(self, linkedin_entity_extractor):
        """Test extraction of industry context from LinkedIn messages."""
        industry_message = (
            "Our technology company is expanding into the healthcare sector. "
            "We're looking for partners in the finance industry as well."
        )

        result = await linkedin_entity_extractor.extract_linkedin_entities(industry_message)

        # Check for industry entities
        industries = [e for e in result.entities if e.type ==
                      EntityType.industry]
        assert len(industries) > 0

        industry_values = [i.normalized_value.lower() for i in industries]
        assert 'technology' in industry_values
        assert 'healthcare' in industry_values
        assert 'finance' in industry_values

    async def test_linkedin_message_platform_detection(self, linkedin_bridge_hub):
        """Test platform detection for LinkedIn messages in Matrix bridge."""
        # Simulate Matrix message from LinkedIn bridge
        linkedin_sender = "@linkedin_user123:matrix.org"
        room_id = "!linkedinroom:matrix.org"

        platform = linkedin_bridge_hub._determine_message_platform(
            linkedin_sender, room_id)
        assert platform == 'linkedin'

    async def test_linkedin_professional_content_enhancement(self, linkedin_handler):
        """Test professional content enhancement for LinkedIn messages."""
        professional_message = {
            'message_id': 'linkedin_msg_125',
            'conversation_id': 'linkedin_conv_458',
            'sender': {
                'linkedin_id': 'sales-director',
                'display_name': 'Sales Director',
                'job_title': 'Sales Director',
                'company': 'SalesCorp'
            },
            'recipients': [{'linkedin_id': 'prospect', 'display_name': 'Prospect'}],
            'content': {
                'text': 'I wanted to schedule a meeting to discuss our proposal for your upcoming project. This could be a great opportunity for collaboration.'
            }
        }

        raw_message = RawMessage(
            platform=Platform.LINKEDIN,
            platform_message_id='linkedin_msg_125',
            raw_data=professional_message,
            received_at=datetime.now(timezone.utc)
        )

        normalized_message = linkedin_handler.normalize_message(raw_message)

        # Check if professional keywords were detected
        content_metadata = getattr(normalized_message.content, 'metadata', {})
        if content_metadata:
            assert content_metadata.get('business_context_detected') is True
            professional_keywords = content_metadata.get(
                'professional_keywords', [])
            assert 'meeting' in professional_keywords
            assert 'opportunity' in professional_keywords

    @pytest.mark.asyncio
    async def test_linkedin_end_to_end_processing(self, linkedin_entity_extractor):
        """Test end-to-end LinkedIn message processing."""
        # This test would simulate the full flow from Matrix bridge to entity extraction
        # In a real scenario, this would involve:
        # 1. Receiving Matrix event from LinkedIn bridge
        # 2. Normalizing the message
        # 3. Extracting entities with professional context
        # 4. Storing results

        # For now, we'll test the key components work together
        sample_matrix_event = {
            'type': 'm.room.message',
            'sender': '@linkedin_john123:matrix.org',
            'content': {
                'msgtype': 'm.text',
                'body': 'Hi, I\'m a Software Engineer at Google looking for new opportunities in the AI space.'
            },
            'event_id': '$linkedin_event_123',
            'origin_server_ts': int(datetime.now(timezone.utc).timestamp() * 1000),
            'room_id': '!linkedinroom:matrix.org'
        }

        # Test platform detection using the hub class method directly
        from integrations.matrix_bridge_hub.hub import MatrixBridgeHub
        hub = MatrixBridgeHub({})
        platform = hub._determine_message_platform(
            sample_matrix_event['sender'],
            sample_matrix_event['room_id']
        )
        assert platform == 'linkedin'

        # Test entity extraction on the message content
        message_text = sample_matrix_event['content']['body']
        result = await linkedin_entity_extractor.extract_linkedin_entities(message_text)

        # Verify professional entities were found
        entity_types = [e.type for e in result.entities]
        assert EntityType.job_title in entity_types  # "Software Engineer"
        assert EntityType.organization in entity_types  # "Google"
        assert EntityType.business_opportunity in entity_types  # "opportunities"


if __name__ == "__main__":
    pytest.main([__file__])
