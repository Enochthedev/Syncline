"""
Proactive Memory Agent for intelligent relationship and commitment tracking.

This agent provides AI-powered proactive memory capabilities including:
- Commitment tracking and follow-up detection
- Contact dossier generation with relationship insights
- File tracking system for shared resources
- Nudge generation with contextual reminders
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai.base import BaseAIAgent, AIProvider
from services.ai.providers import get_provider
from services.message_schema import NormalizedMessage
from db.models.message import Message
from db.models.thread import Thread
from db.models.participant import Participant
from db.models.contact import Contact
from db.models.attachment import Attachment
from db.session import get_async_session

from .types import (
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

logger = logging.getLogger(__name__)


class ProactiveMemoryAgent(BaseAIAgent):
    """
    AI agent for proactive memory and relationship management.

    Provides intelligent tracking of commitments, relationships, and shared resources
    with proactive nudges and insights.
    """

    def __init__(
        self,
        provider: AIProvider = AIProvider.OLLAMA,
        model: str = "tinyllama:latest",
        **kwargs
    ):
        """Initialize the proactive memory agent."""
        super().__init__(
            name="proactive_memory_agent",
            provider=provider,
            model=model,
            **kwargs
        )

        # Memory storage (in production, this would be a proper database)
        self._commitments: Dict[str, Commitment] = {}
        self._files: Dict[str, FileReference] = {}
        self._dossiers: Dict[str, ContactDossier] = {}
        self._nudges: Dict[str, Nudge] = {}

        logger.info("Initialized ProactiveMemoryAgent")

    async def process(self, input_data: Any, **kwargs) -> MemoryAnalysisResult:
        """
        Process input for proactive memory analysis.

        Args:
            input_data: Can be a NormalizedMessage, MemoryContext, or dict
            **kwargs: Additional processing options

        Returns:
            MemoryAnalysisResult with extracted commitments, files, and insights
        """
        if not self._validate_input(input_data):
            raise ValueError(
                "Invalid input data for proactive memory analysis")

        # Convert input to MemoryContext
        context = self._prepare_context(input_data, **kwargs)

        start_time = datetime.utcnow()

        try:
            # Perform memory analysis
            result = await self._analyze_memory(context)

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            result.processing_time = processing_time

            logger.info(
                f"Completed proactive memory analysis in {processing_time:.2f}s: "
                f"{len(result.commitments)} commitments, "
                f"{len(result.files)} files, "
                f"{len(result.nudges)} nudges"
            )

            return result

        except Exception as e:
            logger.error(f"Error in proactive memory analysis: {e}")
            raise

    async def track_commitment(self, message: NormalizedMessage) -> List[Commitment]:
        """
        Extract and track commitments from a message.

        Args:
            message: Normalized message to analyze

        Returns:
            List of extracted commitments
        """
        try:
            # Build prompt for commitment extraction
            prompt = self._build_commitment_prompt(message)

            # Get AI provider
            provider = get_provider(self.provider)

            # Extract commitments using AI
            response = await provider.generate_text(
                prompt=prompt,
                model=self.model,
                max_tokens=1000,
                temperature=0.1
            )

            # Parse AI response into commitments
            commitments = self._parse_commitments_response(response, message)

            # Store commitments
            for commitment in commitments:
                self._commitments[commitment.id] = commitment

            logger.info(
                f"Extracted {len(commitments)} commitments from message {message.id}")
            return commitments

        except Exception as e:
            logger.error(f"Error tracking commitments: {e}")
            return []

    async def track_file_reference(self, message: NormalizedMessage) -> List[FileReference]:
        """
        Extract and track file references from a message.

        Args:
            message: Normalized message to analyze

        Returns:
            List of extracted file references
        """
        try:
            files = []

            # Process attachments
            if hasattr(message, 'attachments') and message.attachments:
                for attachment in message.attachments:
                    file_ref = FileReference(
                        filename=attachment.filename,
                        file_type=attachment.mime_type,
                        file_size=attachment.file_size,
                        file_url=attachment.storage_url,
                        shared_by=message.sender.id,
                        shared_with=[p.id for p in message.recipients],
                        shared_at=message.timestamp,
                        source_message_id=message.id,
                        source_thread_id=message.thread_id,
                        source_platform=message.platform
                    )
                    files.append(file_ref)

            # Extract file references from content using AI
            if message.content and message.content.text:
                ai_files = await self._extract_file_references_ai(message)
                files.extend(ai_files)

            # Store file references
            for file_ref in files:
                self._files[file_ref.id] = file_ref

            logger.info(
                f"Tracked {len(files)} file references from message {message.id}")
            return files

        except Exception as e:
            logger.error(f"Error tracking file references: {e}")
            return []

    async def generate_contact_dossier(self, contact_id: str, user_id: str) -> ContactDossier:
        """
        Generate a comprehensive contact dossier with AI insights.

        Args:
            contact_id: ID of the contact
            user_id: ID of the user requesting the dossier

        Returns:
            ContactDossier with relationship insights and analysis
        """
        try:
            # Get contact information from database
            async with get_async_session() as session:
                contact_info = await self._get_contact_info(session, contact_id, user_id)

            if not contact_info:
                raise ValueError(f"Contact {contact_id} not found")

            # Generate relationship insights
            insights = await self._generate_relationship_insights(contact_id, user_id)

            # Get related commitments and files
            commitments = [c for c in self._commitments.values()
                           if c.committed_to == contact_id or c.committed_by == contact_id]
            files = [f for f in self._files.values()
                     if contact_id in f.shared_with or f.shared_by == contact_id]

            # Generate AI summary
            summary = await self._generate_contact_summary(contact_info, insights, commitments, files)

            # Create dossier
            dossier = ContactDossier(
                contact_id=contact_id,
                name=contact_info.get('name', ''),
                email=contact_info.get('email'),
                platforms=contact_info.get('platforms', {}),
                first_interaction=contact_info.get('first_interaction'),
                last_interaction=contact_info.get('last_interaction'),
                total_messages=contact_info.get('total_messages', 0),
                total_threads=contact_info.get('total_threads', 0),
                relationship_insights=insights,
                shared_files=files,
                commitments=commitments,
                summary=summary,
                key_topics=insights.common_topics
            )

            # Store dossier
            self._dossiers[contact_id] = dossier

            logger.info(f"Generated contact dossier for {contact_id}")
            return dossier

        except Exception as e:
            logger.error(f"Error generating contact dossier: {e}")
            raise

    async def generate_nudges(self, user_id: str, context: Optional[MemoryContext] = None) -> List[Nudge]:
        """
        Generate proactive nudges based on current context and history.

        Args:
            user_id: ID of the user
            context: Optional context for nudge generation

        Returns:
            List of generated nudges
        """
        try:
            nudges = []

            # Generate commitment-based nudges
            commitment_nudges = await self._generate_commitment_nudges(user_id)
            nudges.extend(commitment_nudges)

            # Generate reconnection nudges
            reconnection_nudges = await self._generate_reconnection_nudges(user_id)
            nudges.extend(reconnection_nudges)

            # Generate file reference nudges
            file_nudges = await self._generate_file_nudges(user_id)
            nudges.extend(file_nudges)

            # Store nudges
            for nudge in nudges:
                self._nudges[nudge.id] = nudge

            logger.info(f"Generated {len(nudges)} nudges for user {user_id}")
            return nudges

        except Exception as e:
            logger.error(f"Error generating nudges: {e}")
            return []

    def _build_prompt(self, input_data: Any, **kwargs) -> str:
        """Build prompt for general memory analysis."""
        if isinstance(input_data, dict) and 'message' in input_data:
            message = input_data['message']
            # Handle both dict and NormalizedMessage objects
            if hasattr(message, 'content'):
                content_text = message.content.text if message.content else ''
                sender_name = message.sender.display_name if message.sender else 'Unknown'
                platform = message.platform.value if hasattr(
                    message.platform, 'value') else str(message.platform)
            else:
                content_text = message.get('content', {}).get('text', '')
                sender_name = message.get('sender', {}).get('name', 'Unknown')
                platform = message.get('platform', 'Unknown')

            return f"""
Analyze this message for proactive memory insights:

Message: {content_text}
From: {sender_name}
Platform: {platform}

Extract:
1. Commitments or promises made
2. File references or shared resources
3. Relationship insights
4. Follow-up opportunities

Provide structured analysis in JSON format.
"""
        return "Analyze the provided data for proactive memory insights."

    def _build_commitment_prompt(self, message: NormalizedMessage) -> str:
        """Build prompt for commitment extraction."""
        content = message.content.text if message.content else ''
        sender_name = message.sender.display_name or 'Unknown'

        return f"""
Analyze this message for commitments, promises, or action items:

Message: "{content}"
From: {sender_name}
Date: {message.timestamp}

Look for:
1. Explicit commitments ("I will...", "I'll do...", "I promise...")
2. Implicit promises ("Let me check...", "I'll get back to you...")
3. Deadlines and due dates
4. Meeting commitments
5. Task assignments

For each commitment found, provide:
- Type (task, meeting, deadline, follow_up, promise, reminder)
- Description
- Due date (if mentioned)
- Confidence score (0-1)

Return as JSON array of commitments.
"""

    async def _extract_file_references_ai(self, message: NormalizedMessage) -> List[FileReference]:
        """Extract file references from message content using AI."""
        try:
            content = message.content.get(
                'text', '') if message.content else ''

            prompt = f"""
Analyze this message for file references, shared documents, or resources:

Message: "{content}"

Look for:
1. Mentions of files, documents, or attachments
2. Links to shared resources
3. References to previously shared files
4. Document names or types

Extract file information and return as JSON array.
"""

            provider = get_provider(self.provider)
            response = await provider.generate_text(
                prompt=prompt,
                model=self.model,
                max_tokens=500,
                temperature=0.1
            )

            # Parse response (simplified - in production would be more robust)
            files = []
            try:
                parsed = json.loads(response)
                for item in parsed:
                    if isinstance(item, dict) and 'filename' in item:
                        file_ref = FileReference(
                            filename=item.get('filename', ''),
                            file_type=item.get('file_type', ''),
                            shared_by=message.sender.id,
                            shared_with=[p.id for p in message.recipients],
                            shared_at=message.timestamp,
                            source_message_id=message.id,
                            source_thread_id=message.thread_id,
                            source_platform=message.platform,
                            content_summary=item.get('description', '')
                        )
                        files.append(file_ref)
            except json.JSONDecodeError:
                logger.warning(
                    "Could not parse AI response for file references")

            return files

        except Exception as e:
            logger.error(f"Error extracting file references with AI: {e}")
            return []

    def _parse_commitments_response(self, response: str, message: NormalizedMessage) -> List[Commitment]:
        """Parse AI response into Commitment objects."""
        commitments = []

        try:
            # Try to parse as JSON
            parsed = json.loads(response)

            for item in parsed:
                if isinstance(item, dict):
                    commitment = Commitment(
                        type=CommitmentType(item.get('type', 'task')),
                        description=item.get('description', ''),
                        context=message.content.text if message.content else '',
                        committed_by=message.sender.id,
                        due_date=self._parse_date(item.get('due_date')),
                        source_message_id=message.id,
                        source_thread_id=message.thread_id,
                        source_platform=message.platform,
                        confidence_score=float(
                            item.get('confidence_score', 0.5))
                    )
                    commitments.append(commitment)

        except json.JSONDecodeError:
            # Fallback: simple text parsing
            logger.warning(
                "Could not parse AI response as JSON, using fallback parsing")

        return commitments

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string into datetime object."""
        if not date_str:
            return None

        try:
            # Simple date parsing - in production would be more robust
            if 'tomorrow' in date_str.lower():
                return datetime.utcnow() + timedelta(days=1)
            elif 'next week' in date_str.lower():
                return datetime.utcnow() + timedelta(weeks=1)
            # Add more parsing logic as needed
        except Exception:
            pass

        return None

    async def _analyze_memory(self, context: MemoryContext) -> MemoryAnalysisResult:
        """Perform comprehensive memory analysis."""
        result = MemoryAnalysisResult(context=context)

        # Get relevant data based on context
        if context.message_id:
            # Analyze specific message
            async with get_async_session() as session:
                message = await self._get_message(session, context.message_id)
                if message:
                    normalized_msg = self._convert_to_normalized(message)
                    result.commitments = await self.track_commitment(normalized_msg)
                    result.files = await self.track_file_reference(normalized_msg)

        # Generate nudges if requested
        if context.user_id:
            result.nudges = await self.generate_nudges(context.user_id, context)

        return result

    def _prepare_context(self, input_data: Any, **kwargs) -> MemoryContext:
        """Prepare MemoryContext from input data."""
        if isinstance(input_data, MemoryContext):
            return input_data
        elif isinstance(input_data, NormalizedMessage):
            return MemoryContext(
                message_id=input_data.id,
                thread_id=input_data.thread_id,
                platform=input_data.platform,
                **kwargs
            )
        elif isinstance(input_data, dict):
            return MemoryContext(**input_data, **kwargs)
        else:
            return MemoryContext(**kwargs)

    async def _get_contact_info(self, session: AsyncSession, contact_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get contact information from database."""
        try:
            # Get contact details
            contact_query = select(Contact).where(
                and_(Contact.id == contact_id, Contact.user_id == user_id)
            )
            result = await session.execute(contact_query)
            contact = result.scalar_one_or_none()

            if not contact:
                return None

            # Get interaction statistics
            message_count_query = select(func.count(Message.id)).where(
                or_(
                    Message.sender_id == contact_id,
                    Message.recipients.contains([contact_id])
                )
            )
            message_count_result = await session.execute(message_count_query)
            total_messages = message_count_result.scalar() or 0

            # Get first and last interaction dates
            first_msg_query = select(Message.timestamp).where(
                or_(
                    Message.sender_id == contact_id,
                    Message.recipients.contains([contact_id])
                )
            ).order_by(Message.timestamp.asc()).limit(1)

            last_msg_query = select(Message.timestamp).where(
                or_(
                    Message.sender_id == contact_id,
                    Message.recipients.contains([contact_id])
                )
            ).order_by(Message.timestamp.desc()).limit(1)

            first_result = await session.execute(first_msg_query)
            last_result = await session.execute(last_msg_query)

            first_interaction = first_result.scalar()
            last_interaction = last_result.scalar()

            return {
                'name': f"{contact.first_name or ''} {contact.last_name or ''}".strip(),
                'email': contact.email,
                'platforms': {
                    'email': contact.email,
                    'phone': contact.phone,
                    'telegram': contact.telegram,
                    'whatsapp': contact.whatsapp,
                    'twitter': contact.twitter_handle,
                    'slack': contact.slack_handle,
                    'linkedin': contact.linkedin_profile
                },
                'first_interaction': first_interaction,
                'last_interaction': last_interaction,
                'total_messages': total_messages,
                'total_threads': 0  # Would need additional query
            }

        except Exception as e:
            logger.error(f"Error getting contact info: {e}")
            return None

    async def _generate_relationship_insights(self, contact_id: str, user_id: str) -> RelationshipInsight:
        """Generate AI-powered relationship insights."""
        # This would involve complex analysis of communication patterns
        # For now, return a basic insight structure
        return RelationshipInsight(
            contact_id=contact_id,
            contact_name="",
            relationship_strength=0.5,
            communication_style="professional",
            common_topics=["work", "projects"],
            suggested_actions=["Schedule regular check-in"]
        )

    async def _generate_contact_summary(
        self,
        contact_info: Dict[str, Any],
        insights: RelationshipInsight,
        commitments: List[Commitment],
        files: List[FileReference]
    ) -> str:
        """Generate AI summary of contact relationship."""
        try:
            prompt = f"""
Generate a concise summary of this professional relationship:

Contact: {contact_info.get('name', 'Unknown')}
Total Messages: {contact_info.get('total_messages', 0)}
Last Interaction: {contact_info.get('last_interaction', 'Unknown')}
Common Topics: {', '.join(insights.common_topics)}
Shared Files: {len(files)}
Active Commitments: {len([c for c in commitments if c.status == CommitmentStatus.PENDING])}

Provide a 2-3 sentence professional summary of the relationship and communication patterns.
"""

            provider = get_provider(self.provider)
            response = await provider.generate_text(
                prompt=prompt,
                model=self.model,
                max_tokens=200,
                temperature=0.3
            )

            return response.strip()

        except Exception as e:
            logger.error(f"Error generating contact summary: {e}")
            return "Professional contact with regular communication."

    async def _generate_commitment_nudges(self, user_id: str) -> List[Nudge]:
        """Generate nudges for pending commitments."""
        nudges = []

        # Find overdue or upcoming commitments
        now = datetime.utcnow()

        for commitment in self._commitments.values():
            if commitment.committed_by == user_id and commitment.status == CommitmentStatus.PENDING:
                if commitment.due_date:
                    days_until_due = (commitment.due_date - now).days

                    if days_until_due < 0:
                        # Overdue
                        nudge = Nudge(
                            type=NudgeType.DEADLINE_REMINDER,
                            priority=NudgePriority.URGENT,
                            title="Overdue Commitment",
                            message=f"Your commitment '{commitment.description}' was due {abs(days_until_due)} days ago.",
                            related_commitment_id=commitment.id,
                            confidence_score=0.9
                        )
                        nudges.append(nudge)
                    elif days_until_due <= 1:
                        # Due soon
                        nudge = Nudge(
                            type=NudgeType.DEADLINE_REMINDER,
                            priority=NudgePriority.HIGH,
                            title="Commitment Due Soon",
                            message=f"Your commitment '{commitment.description}' is due {'today' if days_until_due == 0 else 'tomorrow'}.",
                            related_commitment_id=commitment.id,
                            confidence_score=0.8
                        )
                        nudges.append(nudge)

        return nudges

    async def _generate_reconnection_nudges(self, user_id: str) -> List[Nudge]:
        """Generate nudges for reconnection opportunities."""
        nudges = []

        # This would analyze communication patterns to suggest reconnections
        # For now, return empty list

        return nudges

    async def _generate_file_nudges(self, user_id: str) -> List[Nudge]:
        """Generate nudges related to shared files."""
        nudges = []

        # This would analyze file sharing patterns and suggest follow-ups
        # For now, return empty list

        return nudges

    async def _get_message(self, session: AsyncSession, message_id: str) -> Optional[Message]:
        """Get message from database."""
        try:
            query = select(Message).where(Message.id == message_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return None

    def _convert_to_normalized(self, message: Message) -> NormalizedMessage:
        """Convert database Message to NormalizedMessage."""
        from services.message_schema import Participant, MessageContent, Platform

        # Create sender participant
        sender = Participant(
            id=str(message.sender_id),
            display_name='Unknown'
        )

        # Create message content
        content = MessageContent(
            text=message.content_text or ''
        )

        # This is a simplified conversion - in production would be more complete
        return NormalizedMessage(
            id=str(message.id),
            platform=Platform(message.platform),
            thread_id=str(message.thread_id),
            sender=sender,
            recipients=[],
            content=content,
            timestamp=message.timestamp,
            attachments=[],
            metadata=message.metadata or {}
        )

    # Storage methods (in production, these would use proper database)
    def get_commitments(self, user_id: str, status: Optional[CommitmentStatus] = None) -> List[Commitment]:
        """Get commitments for a user."""
        commitments = [c for c in self._commitments.values()
                       if c.committed_by == user_id]
        if status:
            commitments = [c for c in commitments if c.status == status]
        return commitments

    def get_files(self, user_id: str, contact_id: Optional[str] = None) -> List[FileReference]:
        """Get file references for a user."""
        files = [f for f in self._files.values() if f.shared_by ==
                 user_id or user_id in f.shared_with]
        if contact_id:
            files = [f for f in files if f.shared_by ==
                     contact_id or contact_id in f.shared_with]
        return files

    def get_nudges(self, user_id: str, delivered: Optional[bool] = None) -> List[Nudge]:
        """Get nudges for a user."""
        # In production, would filter by user_id properly
        nudges = list(self._nudges.values())
        if delivered is not None:
            nudges = [n for n in nudges if n.is_delivered == delivered]
        return nudges

    def get_dossier(self, contact_id: str) -> Optional[ContactDossier]:
        """Get contact dossier."""
        return self._dossiers.get(contact_id)
