"""
Summary Generation Agent - Main implementation.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator

from config.config import settings
from services.message_schema import NormalizedMessage
from services.ai.base import BaseAIAgent, AIProvider, ProcessingStatus

from .types import (
    SummaryRequest, SummaryResult, StreamingSummaryChunk,
    SummaryQuality, SummaryType, SummaryScope
)
from .content_parser import ContentParser
from .prompt_builder import PromptBuilder
from .data_analyzer import DataAnalyzer
from .database import DatabaseOperations

# Import DB_AVAILABLE from database module
from .database import DB_AVAILABLE

if DB_AVAILABLE:
    try:
        from db.session import get_async_session
    except ImportError:
        get_async_session = None

logger = logging.getLogger(__name__)


class SummaryGenerationAgent(BaseAIAgent):
    """
    AI agent for generating intelligent summaries across multiple timeframes and scopes.

    Supports:
    - Micro-summaries: Real-time, single message context
    - Thread summaries: Conversation-level insights
    - Daily summaries: Per-contact and per-topic rollups
    - Weekly summaries: Trend analysis and relationship insights
    """

    def __init__(
        self,
        provider: AIProvider = None,
        model: str = None,
        max_retries: int = None,
        timeout: int = None
    ):
        """Initialize the Summary Generation Agent."""
        super().__init__(
            name="SummaryGenerationAgent",
            provider=provider,
            model=model,
            max_retries=max_retries,
            timeout=timeout
        )

        # Summary generation statistics
        self.summary_stats = {
            'summaries_generated': 0,
            'summaries_by_type': {},
            'average_processing_time': 0.0,
            'streaming_sessions': 0,
            'batch_operations': 0
        }

    async def process(self, input_data: SummaryRequest, **kwargs) -> SummaryResult:
        """
        Process a summary generation request.

        Args:
            input_data: SummaryRequest containing generation parameters
            **kwargs: Additional processing options

        Returns:
            SummaryResult with generated summary
        """
        start_time = datetime.utcnow()

        result = SummaryResult(
            request_id=input_data.id,
            status=ProcessingStatus.PROCESSING.value
        )

        try:
            # Validate input
            if not self._validate_input(input_data):
                raise ValueError("Invalid summary request")

            # Get messages for summarization
            messages = await DatabaseOperations.get_messages_for_summary(input_data)
            if not messages:
                result.content = "No messages found for the specified criteria."
                result.status = ProcessingStatus.COMPLETED.value
                return result

            # Generate summary based on type
            summary_content = await self._generate_summary_by_type(messages, input_data)

            # Parse and structure the summary
            result = ContentParser.parse_summary_response(
                summary_content, result, input_data)

            # Store summary in database
            summary_id = await DatabaseOperations.store_summary(result, input_data)
            result.summary_id = summary_id

            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            result.processing_time = processing_time
            result.status = ProcessingStatus.COMPLETED.value

            self._update_summary_stats(
                input_data.summary_type, processing_time, True)

            logger.info(
                f"Generated {input_data.summary_type.value} summary "
                f"for {len(messages)} messages in {processing_time:.2f}s"
            )

        except Exception as e:
            result.error = str(e)
            result.status = ProcessingStatus.FAILED.value
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            result.processing_time = processing_time

            self._update_summary_stats(
                input_data.summary_type, processing_time, False)
            logger.error(f"Summary generation failed: {e}")

        return result

    async def _generate_summary_by_type(self, messages: List[Dict[str, Any]], request: SummaryRequest) -> str:
        """Generate summary based on type."""
        if request.summary_type == SummaryType.micro:
            return await self._generate_micro_summary(messages, request)
        elif request.summary_type == SummaryType.thread:
            return await self._generate_thread_summary(messages, request)
        elif request.summary_type == SummaryType.daily:
            return await self._generate_daily_summary(messages, request)
        elif request.summary_type == SummaryType.weekly:
            return await self._generate_weekly_summary(messages, request)
        else:
            raise ValueError(
                f"Unsupported summary type: {request.summary_type}")

    async def _generate_micro_summary(self, messages: List[Dict[str, Any]], request: SummaryRequest) -> str:
        """Generate micro-summary for real-time context."""
        if not messages:
            return "No messages to summarize."

        # For micro-summaries, focus on the most recent message(s)
        recent_messages = messages[-3:] if len(messages) > 3 else messages

        prompt = PromptBuilder.build_summary_prompt(recent_messages, request)
        return await self._get_ai_response(prompt)

    async def _generate_thread_summary(self, messages: List[Dict[str, Any]], request: SummaryRequest) -> str:
        """Generate thread-level conversation summary."""
        if not messages:
            return "No messages in thread to summarize."

        prompt = PromptBuilder.build_summary_prompt(messages, request)
        return await self._get_ai_response(prompt)

    async def _generate_daily_summary(self, messages: List[Dict[str, Any]], request: SummaryRequest) -> str:
        """Generate daily rollup summary."""
        if not messages:
            return "No messages found for the specified day."

        # Group messages by thread/contact for daily summary
        grouped_messages = DataAnalyzer.group_messages_for_daily_summary(
            messages)

        prompt = PromptBuilder.build_daily_summary_prompt(
            grouped_messages, request)
        return await self._get_ai_response(prompt)

    async def _generate_weekly_summary(self, messages: List[Dict[str, Any]], request: SummaryRequest) -> str:
        """Generate weekly trend analysis summary."""
        if not messages:
            return "No messages found for the specified week."

        # Analyze trends and patterns for weekly summary
        trends = DataAnalyzer.analyze_weekly_trends(messages)

        prompt = PromptBuilder.build_weekly_summary_prompt(
            messages, trends, request)
        return await self._get_ai_response(prompt)

    async def _get_ai_response(self, prompt: str) -> str:
        """Get AI response for the given prompt."""
        from ..engine import get_ai_processing_engine

        ai_engine = await get_ai_processing_engine()
        result = await ai_engine.process_text(
            prompt,
            custom_prompt=None,
            model=self.model,
            redact_pii=True
        )

        return result.result if result.result else "Unable to generate summary."

    async def generate_streaming_summary(
        self,
        request: SummaryRequest,
        **kwargs
    ) -> AsyncGenerator[StreamingSummaryChunk, None]:
        """
        Generate streaming summary for active conversations.

        Args:
            request: SummaryRequest for streaming generation
            **kwargs: Additional options

        Yields:
            StreamingSummaryChunk: Chunks of summary content as they're generated
        """
        try:
            self.summary_stats['streaming_sessions'] += 1

            # Get messages for summarization
            messages = await DatabaseOperations.get_messages_for_summary(request)
            if not messages:
                yield StreamingSummaryChunk(
                    request_id=request.id,
                    content="No messages found for streaming summary.",
                    is_final=True
                )
                return

            # Build streaming prompt
            prompt = PromptBuilder.build_summary_prompt(messages, request)

            # Generate streaming response
            async for chunk in self._stream_ai_response(prompt, request):
                yield chunk

            logger.info(
                f"Completed streaming summary for request {request.id}")

        except Exception as e:
            logger.error(f"Streaming summary failed: {e}")
            yield StreamingSummaryChunk(
                request_id=request.id,
                content=f"Error generating streaming summary: {str(e)}",
                is_final=True,
                chunk_type="error"
            )

    async def _stream_ai_response(
        self,
        prompt: str,
        request: SummaryRequest
    ) -> AsyncGenerator[StreamingSummaryChunk, None]:
        """Stream AI response for real-time summary generation."""
        # This is a simplified implementation - real streaming would require
        # streaming-capable AI providers
        try:
            ai_response = await self._get_ai_response(prompt)

            if ai_response:
                # Simulate streaming by chunking the response
                content = ai_response
                chunk_size = 50  # words per chunk
                words = content.split()

                for i in range(0, len(words), chunk_size):
                    chunk_words = words[i:i + chunk_size]
                    chunk_content = ' '.join(chunk_words)

                    is_final = i + chunk_size >= len(words)

                    yield StreamingSummaryChunk(
                        request_id=request.id,
                        content=chunk_content,
                        is_final=is_final,
                        chunk_type="content"
                    )

                    # Small delay to simulate streaming
                    await asyncio.sleep(0.1)
            else:
                yield StreamingSummaryChunk(
                    request_id=request.id,
                    content="Unable to generate streaming summary.",
                    is_final=True,
                    chunk_type="error"
                )

        except Exception as e:
            yield StreamingSummaryChunk(
                request_id=request.id,
                content=f"Streaming error: {str(e)}",
                is_final=True,
                chunk_type="error"
            )

    async def process_batch_summaries(
        self,
        requests: List[SummaryRequest],
        batch_size: int = None,
        **kwargs
    ) -> List[SummaryResult]:
        """
        Process multiple summary requests in batch for historical data.

        Args:
            requests: List of SummaryRequest objects
            batch_size: Maximum concurrent processing
            **kwargs: Additional processing options

        Returns:
            List of SummaryResult objects
        """
        batch_size = batch_size or settings.AI_BATCH_SIZE
        self.summary_stats['batch_operations'] += 1

        logger.info(f"Processing batch of {len(requests)} summary requests")

        results = []

        # Process in chunks to control concurrency
        for i in range(0, len(requests), batch_size):
            chunk = requests[i:i + batch_size]

            # Process chunk concurrently
            tasks = [self.process_with_retry(req, **kwargs) for req in chunk]
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions in results
            for j, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    error_result = SummaryResult(
                        request_id=chunk[j].id,
                        status=ProcessingStatus.FAILED.value,
                        error=str(result)
                    )
                    results.append(error_result)
                else:
                    results.append(result)

            logger.debug(
                f"Processed batch chunk {i//batch_size + 1}/{(len(requests) + batch_size - 1)//batch_size}")

        return results

    async def update_incremental_summary(
        self,
        thread_id: str,
        new_message: NormalizedMessage,
        **kwargs
    ) -> Optional[SummaryResult]:
        """
        Update existing thread summary with new message incrementally.

        Args:
            thread_id: Thread ID to update summary for
            new_message: New message to incorporate
            **kwargs: Additional options

        Returns:
            Updated SummaryResult or None if no update needed
        """
        try:
            if not DB_AVAILABLE:
                # For testing without database, create new summary
                request = SummaryRequest(
                    summary_type=SummaryType.thread,
                    scope_type=SummaryScope.thread,
                    scope_id=thread_id,
                    quality=SummaryQuality.BASIC
                )
                return await self.process(request)

            # Get existing thread summary
            async with get_async_session() as session:
                existing_summary = await DatabaseOperations.get_latest_thread_summary(session, thread_id)

                if not existing_summary:
                    # No existing summary, create new one
                    request = SummaryRequest(
                        summary_type=SummaryType.thread,
                        scope_type=SummaryScope.thread,
                        scope_id=thread_id,
                        quality=SummaryQuality.BASIC
                    )
                    return await self.process(request)

                # Check if update is needed (e.g., significant new content)
                if not DataAnalyzer.should_update_summary(existing_summary, new_message):
                    return None

                # Generate incremental update
                update_request = SummaryRequest(
                    summary_type=SummaryType.thread,
                    scope_type=SummaryScope.thread,
                    scope_id=thread_id,
                    quality=SummaryQuality.BASIC,
                    context={
                        'existing_summary': existing_summary.content,
                        'new_message': new_message.to_dict(),
                        'incremental_update': True
                    }
                )

                return await self.process(update_request)

        except Exception as e:
            logger.error(f"Incremental summary update failed: {e}")
            return None

    def _build_prompt(self, input_data: Any, **kwargs) -> str:
        """Build prompt for AI model (required by base class)."""
        if isinstance(input_data, SummaryRequest):
            return f"Generate a {input_data.summary_type.value} summary"
        return str(input_data)

    def _update_summary_stats(self, summary_type: SummaryType, processing_time: float, success: bool):
        """Update summary generation statistics."""
        if success:
            self.summary_stats['summaries_generated'] += 1

            # Update per-type stats
            type_key = summary_type.value
            if type_key not in self.summary_stats['summaries_by_type']:
                self.summary_stats['summaries_by_type'][type_key] = 0
            self.summary_stats['summaries_by_type'][type_key] += 1

            # Update average processing time
            total_summaries = self.summary_stats['summaries_generated']
            current_avg = self.summary_stats['average_processing_time']
            self.summary_stats['average_processing_time'] = (
                (current_avg * (total_summaries - 1) +
                 processing_time) / total_summaries
            )

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary generation statistics."""
        return {
            **self.summary_stats,
            **self.get_stats()
        }
