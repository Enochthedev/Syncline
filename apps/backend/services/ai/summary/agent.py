"""
Summary Generation Agent

Generates AI-powered summaries of conversations and threads:
- Brief summaries for quick overview
- Detailed summaries with key points
- Insight summaries with patterns and analysis
- Thread context building
- Prompt template management
- Integration with Ollama for generation
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import settings
from db.models.message import Message
from db.models.summary import Summary
from db.models.thread import Thread
from services.ai.providers import get_llm_provider, LLMProvider, GenerationConfig

logger = logging.getLogger(__name__)


class SummaryType(str, Enum):
    """Types of summaries that can be generated."""
    BRIEF = "brief"  # Short overview (1-2 sentences)
    DETAILED = "detailed"  # Comprehensive summary with key points
    INSIGHT = "insight"  # Analysis with patterns and insights
    DAILY = "daily"  # Daily digest
    WEEKLY = "weekly"  # Weekly digest
    CONTACT = "contact"  # Contact-specific summary


class SummaryAgent:
    """
    Agent for generating conversation summaries using AI.
    
    Provides functionality for:
    - Building thread context from messages
    - Generating different types of summaries
    - Managing prompt templates
    - Storing summaries in database
    """
    
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        max_messages: int = 50,
        max_context_length: int = 4000,
    ):
        """
        Initialize summary agent.
        
        Args:
            llm_provider: LLM provider for generation
            model: Model name for summaries
            max_messages: Maximum messages to include in context
            max_context_length: Maximum context length in characters
        """
        self.llm_provider = llm_provider or get_llm_provider()
        self.model = model or settings.DEFAULT_CHAT_MODEL
        self.max_messages = max_messages
        self.max_context_length = max_context_length
        
        logger.info(
            f"Initialized SummaryAgent with model {self.model}, "
            f"max_messages={max_messages}, max_context={max_context_length}"
        )
    
    async def generate_thread_summary(
        self,
        thread_id: UUID,
        db: AsyncSession,
        summary_type: SummaryType = SummaryType.BRIEF,
        force_regenerate: bool = False,
    ) -> Optional[Summary]:
        """
        Generate summary for a thread.
        
        Args:
            thread_id: Thread ID
            db: Database session
            summary_type: Type of summary to generate
            force_regenerate: Force regeneration if summary exists
            
        Returns:
            Summary object or None if failed
        """
        try:
            # Check if summary already exists
            if not force_regenerate:
                result = await db.execute(
                    select(Summary)
                    .where(Summary.thread_id == thread_id)
                    .where(Summary.summary_type == summary_type.value)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    logger.debug(
                        f"Summary already exists for thread {thread_id} "
                        f"(type: {summary_type})"
                    )
                    return existing
            
            # Get thread
            thread = await db.get(Thread, thread_id)
            if not thread:
                logger.error(f"Thread {thread_id} not found")
                return None
            
            # Build context from messages
            context = await self._build_thread_context(thread_id, db)
            
            if not context:
                logger.warning(f"No context available for thread {thread_id}")
                return None
            
            # Generate summary
            summary_text = await self._generate_summary(
                context=context,
                summary_type=summary_type,
                thread=thread,
            )
            
            if not summary_text:
                logger.error(f"Failed to generate summary for thread {thread_id}")
                return None
            
            # Store summary
            if force_regenerate:
                # Update existing
                result = await db.execute(
                    select(Summary)
                    .where(Summary.thread_id == thread_id)
                    .where(Summary.summary_type == summary_type.value)
                )
                summary = result.scalar_one_or_none()
                if summary:
                    summary.content = summary_text
                    summary.summary_metadata = self._build_metadata(
                        thread=thread,
                        message_count=len(context.get("messages", [])),
                    )
                else:
                    summary = Summary(
                        thread_id=thread_id,
                        summary_type=summary_type.value,
                        content=summary_text,
                        summary_metadata=self._build_metadata(
                            thread=thread,
                            message_count=len(context.get("messages", [])),
                        ),
                    )
                    db.add(summary)
            else:
                # Create new
                summary = Summary(
                    thread_id=thread_id,
                    summary_type=summary_type.value,
                    content=summary_text,
                    summary_metadata=self._build_metadata(
                        thread=thread,
                        message_count=len(context.get("messages", [])),
                    ),
                )
                db.add(summary)
            
            await db.commit()
            await db.refresh(summary)
            
            logger.info(
                f"Generated {summary_type} summary for thread {thread_id}"
            )
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate thread summary: {e}")
            await db.rollback()
            return None
    
    async def generate_contact_summary(
        self,
        contact_id: UUID,
        db: AsyncSession,
        days: int = 30,
    ) -> Optional[str]:
        """
        Generate summary of communications with a contact.
        
        Args:
            contact_id: Contact ID
            db: Database session
            days: Number of days to include
            
        Returns:
            Summary text or None if failed
        """
        try:
            # Get threads for contact
            result = await db.execute(
                select(Thread)
                .where(Thread.contact_id == contact_id)
                .order_by(Thread.last_message_at.desc())
            )
            threads = result.scalars().all()
            
            if not threads:
                logger.warning(f"No threads found for contact {contact_id}")
                return None
            
            # Build context from recent messages across threads
            context = await self._build_contact_context(
                contact_id=contact_id,
                threads=list(threads),
                db=db,
                days=days,
            )
            
            if not context:
                logger.warning(f"No context available for contact {contact_id}")
                return None
            
            # Generate summary
            summary_text = await self._generate_contact_summary(context)
            
            logger.info(f"Generated contact summary for {contact_id}")
            return summary_text
            
        except Exception as e:
            logger.error(f"Failed to generate contact summary: {e}")
            return None
    
    async def _build_thread_context(
        self,
        thread_id: UUID,
        db: AsyncSession,
    ) -> dict:
        """
        Build context from thread messages.
        
        Args:
            thread_id: Thread ID
            db: Database session
            
        Returns:
            Context dictionary with messages and metadata
        """
        try:
            # Get messages for thread
            result = await db.execute(
                select(Message)
                .where(Message.thread_id == str(thread_id))
                .order_by(Message.timestamp.asc())
                .limit(self.max_messages)
            )
            messages = result.scalars().all()
            
            if not messages:
                return {}
            
            # Extract message data
            message_data = []
            total_length = 0
            
            for msg in messages:
                text = self._extract_text_from_message(msg)
                
                if not text:
                    continue
                
                # Check context length
                if total_length + len(text) > self.max_context_length:
                    break
                
                message_data.append({
                    "timestamp": msg.timestamp.isoformat(),
                    "sender": self._get_sender_name(msg),
                    "text": text,
                })
                
                total_length += len(text)
            
            return {
                "messages": message_data,
                "message_count": len(message_data),
                "first_message": messages[0].timestamp.isoformat(),
                "last_message": messages[-1].timestamp.isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to build thread context: {e}")
            return {}
    
    async def _build_contact_context(
        self,
        contact_id: UUID,
        threads: list[Thread],
        db: AsyncSession,
        days: int = 30,
    ) -> dict:
        """
        Build context from contact's recent messages.
        
        Args:
            contact_id: Contact ID
            threads: List of threads with contact
            db: Database session
            days: Number of days to include
            
        Returns:
            Context dictionary
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get recent messages across all threads
            thread_ids = [str(t.id) for t in threads]
            
            result = await db.execute(
                select(Message)
                .where(Message.thread_id.in_(thread_ids))
                .where(Message.timestamp >= cutoff_date)
                .order_by(Message.timestamp.desc())
                .limit(self.max_messages)
            )
            messages = result.scalars().all()
            
            if not messages:
                return {}
            
            # Extract message data
            message_data = []
            total_length = 0
            
            for msg in messages:
                text = self._extract_text_from_message(msg)
                
                if not text:
                    continue
                
                if total_length + len(text) > self.max_context_length:
                    break
                
                message_data.append({
                    "timestamp": msg.timestamp.isoformat(),
                    "platform": msg.platform,
                    "text": text,
                })
                
                total_length += len(text)
            
            return {
                "messages": message_data,
                "message_count": len(message_data),
                "thread_count": len(threads),
                "platforms": list(set(msg.platform for msg in messages)),
                "date_range": {
                    "start": cutoff_date.isoformat(),
                    "end": datetime.utcnow().isoformat(),
                },
            }
            
        except Exception as e:
            logger.error(f"Failed to build contact context: {e}")
            return {}

    async def _generate_summary(
        self,
        context: dict,
        summary_type: SummaryType,
        thread: Optional[Thread] = None,
    ) -> str:
        """
        Generate summary using LLM.
        
        Args:
            context: Context dictionary with messages
            summary_type: Type of summary to generate
            thread: Thread object (optional)
            
        Returns:
            Generated summary text
        """
        try:
            # Build prompt
            prompt = self._build_prompt(
                context=context,
                summary_type=summary_type,
                thread=thread,
            )
            
            # Configure generation
            config = GenerationConfig(
                temperature=0.3,  # Lower for more focused summaries
                max_tokens=500 if summary_type == SummaryType.BRIEF else 1500,
                top_p=0.9,
            )
            
            # Generate summary
            summary = await self.llm_provider.generate(
                prompt=prompt,
                model=self.model,
                config=config,
            )
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return ""
    
    async def _generate_contact_summary(self, context: dict) -> str:
        """
        Generate contact-specific summary.
        
        Args:
            context: Context dictionary
            
        Returns:
            Generated summary text
        """
        try:
            prompt = self._build_contact_prompt(context)
            
            config = GenerationConfig(
                temperature=0.3,
                max_tokens=1000,
                top_p=0.9,
            )
            
            summary = await self.llm_provider.generate(
                prompt=prompt,
                model=self.model,
                config=config,
            )
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate contact summary: {e}")
            return ""
    
    def _build_prompt(
        self,
        context: dict,
        summary_type: SummaryType,
        thread: Optional[Thread] = None,
    ) -> str:
        """
        Build prompt for summary generation.
        
        Args:
            context: Context dictionary
            summary_type: Type of summary
            thread: Thread object (optional)
            
        Returns:
            Prompt string
        """
        messages = context.get("messages", [])
        
        if not messages:
            return ""
        
        # Format messages
        formatted_messages = []
        for msg in messages:
            timestamp = msg.get("timestamp", "")
            sender = msg.get("sender", "Unknown")
            text = msg.get("text", "")
            formatted_messages.append(f"[{timestamp}] {sender}: {text}")
        
        conversation = "\n".join(formatted_messages)
        
        # Select template based on summary type
        if summary_type == SummaryType.BRIEF:
            template = self._get_brief_template()
        elif summary_type == SummaryType.DETAILED:
            template = self._get_detailed_template()
        elif summary_type == SummaryType.INSIGHT:
            template = self._get_insight_template()
        else:
            template = self._get_brief_template()
        
        # Build prompt
        prompt = template.format(
            conversation=conversation,
            message_count=len(messages),
            platform=thread.platform if thread else "unknown",
        )
        
        return prompt
    
    def _build_contact_prompt(self, context: dict) -> str:
        """
        Build prompt for contact summary.
        
        Args:
            context: Context dictionary
            
        Returns:
            Prompt string
        """
        messages = context.get("messages", [])
        
        if not messages:
            return ""
        
        # Format messages
        formatted_messages = []
        for msg in messages:
            timestamp = msg.get("timestamp", "")
            platform = msg.get("platform", "unknown")
            text = msg.get("text", "")
            formatted_messages.append(f"[{timestamp}] ({platform}): {text}")
        
        conversation = "\n".join(formatted_messages)
        
        template = """You are analyzing communication patterns with a contact across multiple platforms.

Conversation history ({message_count} messages across {thread_count} threads):
{conversation}

Platforms: {platforms}
Date range: {date_range}

Provide a comprehensive summary that includes:
1. Overall communication frequency and patterns
2. Main topics discussed
3. Relationship dynamics and tone
4. Any notable trends or changes
5. Key action items or follow-ups

Summary:"""
        
        prompt = template.format(
            conversation=conversation,
            message_count=context.get("message_count", 0),
            thread_count=context.get("thread_count", 0),
            platforms=", ".join(context.get("platforms", [])),
            date_range=f"{context.get('date_range', {}).get('start', '')} to {context.get('date_range', {}).get('end', '')}",
        )
        
        return prompt
    
    def _get_brief_template(self) -> str:
        """Get template for brief summary."""
        return """You are summarizing a conversation thread. Provide a concise 1-2 sentence summary.

Conversation ({message_count} messages on {platform}):
{conversation}

Brief summary:"""
    
    def _get_detailed_template(self) -> str:
        """Get template for detailed summary."""
        return """You are summarizing a conversation thread. Provide a comprehensive summary with key points.

Conversation ({message_count} messages on {platform}):
{conversation}

Provide a detailed summary that includes:
1. Main topics discussed
2. Key decisions or action items
3. Important information shared
4. Any questions or concerns raised

Detailed summary:"""
    
    def _get_insight_template(self) -> str:
        """Get template for insight summary."""
        return """You are analyzing a conversation thread to extract insights and patterns.

Conversation ({message_count} messages on {platform}):
{conversation}

Provide an insightful analysis that includes:
1. Communication patterns and dynamics
2. Sentiment and tone
3. Recurring themes or topics
4. Relationship insights
5. Notable observations

Insight summary:"""
    
    def _build_metadata(
        self,
        thread: Thread,
        message_count: int,
    ) -> dict:
        """
        Build metadata for summary.
        
        Args:
            thread: Thread object
            message_count: Number of messages summarized
            
        Returns:
            Metadata dictionary
        """
        return {
            "model": self.model,
            "message_count": message_count,
            "platform": thread.platform,
            "thread_title": thread.title,
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def _extract_text_from_message(self, message: Message) -> str:
        """
        Extract text content from message.
        
        Args:
            message: Message object
            
        Returns:
            Text content
        """
        try:
            content = message.content
            
            if isinstance(content, dict):
                text = content.get("text", "")
                
                if not text:
                    text = content.get("html", "")
                
                return text.strip()
            
            if isinstance(content, str):
                return content.strip()
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to extract text from message {message.id}: {e}")
            return ""
    
    def _get_sender_name(self, message: Message) -> str:
        """
        Get sender name from message.
        
        Args:
            message: Message object
            
        Returns:
            Sender name
        """
        try:
            # Try to get from sender relationship
            if message.sender:
                return message.sender.name or "Unknown"
            
            # Try to get from metadata
            metadata = message.message_metadata or {}
            sender_info = metadata.get("sender", {})
            
            if isinstance(sender_info, dict):
                return sender_info.get("name", "Unknown")
            
            return "Unknown"
            
        except Exception as e:
            logger.error(f"Failed to get sender name: {e}")
            return "Unknown"
    
    async def health_check(self) -> bool:
        """
        Check health of summary agent.
        
        Returns:
            True if healthy
        """
        try:
            # Check LLM provider
            return await self.llm_provider.health_check()
        except Exception as e:
            logger.error(f"Summary agent health check failed: {e}")
            return False


# Global service instance
_summary_agent: Optional[SummaryAgent] = None


def get_summary_agent() -> SummaryAgent:
    """
    Get the global summary agent instance.
    
    Returns:
        Summary agent
    """
    global _summary_agent
    
    if _summary_agent is None:
        _summary_agent = SummaryAgent()
    
    return _summary_agent


__all__ = [
    "SummaryAgent",
    "SummaryType",
    "get_summary_agent",
]
