"""
Prompt building utilities for different summary types.
"""

from typing import List, Dict, Any
from .types import SummaryRequest, SummaryQuality, SummaryType


class PromptBuilder:
    """Utility class for building AI prompts for different summary types."""

    @staticmethod
    def build_summary_prompt(messages: List[Dict[str, Any]], request: SummaryRequest) -> str:
        """Build AI prompt for summary generation."""
        message_text = "\n\n".join([
            f"[{msg['timestamp'].strftime('%Y-%m-%d %H:%M')}] {msg['sender']}: {msg['content'][:500]}"
            for msg in messages
        ])

        quality_instructions = {
            SummaryQuality.BASIC: "Provide a brief, concise summary focusing on key points.",
            SummaryQuality.DETAILED: "Provide a detailed summary with context and important details.",
            SummaryQuality.COMPREHENSIVE: "Provide a comprehensive analysis with insights and implications."
        }

        prompt = f"""
{quality_instructions[request.quality]}

Summary Type: {request.summary_type.value.title()}
Maximum Length: {request.max_length} words

Messages to summarize:
{message_text}

Please provide a well-structured summary that includes:
1. Main topics and themes discussed
2. Key decisions or outcomes
"""

        if request.include_action_items:
            prompt += "\n3. Action items and next steps (if any)"

        if request.include_entities:
            prompt += "\n4. Important people, organizations, or topics mentioned"

        prompt += f"\n\nSummary ({request.max_length} words max):"

        return prompt

    @staticmethod
    def build_daily_summary_prompt(grouped_messages: Dict[str, List[Dict]], request: SummaryRequest) -> str:
        """Build prompt for daily summary generation."""
        summary_parts = []

        for group_key, group_messages in grouped_messages.items():
            message_text = "\n".join([
                f"[{msg['timestamp'].strftime('%H:%M')}] {msg['sender']}: {msg['content'][:200]}"
                for msg in group_messages
            ])
            summary_parts.append(f"=== {group_key} ===\n{message_text}")

        all_messages = "\n\n".join(summary_parts)

        return f"""
Generate a daily summary for {request.timeframe_start.strftime('%Y-%m-%d') if request.timeframe_start else 'today'}.

Organize the summary by conversations/contacts and include:
1. Key conversations and their main topics
2. Important decisions or outcomes from each conversation
3. Action items and follow-ups needed
4. Notable patterns or trends across conversations

Daily Messages:
{all_messages}

Daily Summary:
"""

    @staticmethod
    def build_weekly_summary_prompt(messages: List[Dict], trends: Dict[str, Any], request: SummaryRequest) -> str:
        """Build prompt for weekly summary generation."""
        return f"""
Generate a weekly summary and trend analysis for the period {request.timeframe_start.strftime('%Y-%m-%d') if request.timeframe_start else 'this week'} to {request.timeframe_end.strftime('%Y-%m-%d') if request.timeframe_end else 'now'}.

Weekly Statistics:
- Total messages: {len(messages)}
- Active conversations: {trends.get('active_threads', 0)}
- Most active contacts: {', '.join(trends.get('top_contacts', [])[:3])}
- Peak activity day: {trends.get('peak_day', 'Unknown')}

Focus on:
1. Major themes and topics discussed this week
2. Relationship and communication patterns
3. Important decisions and outcomes
4. Trends and changes compared to previous periods
5. Upcoming commitments and follow-ups

Weekly Summary:
"""
