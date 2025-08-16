"""
Data analysis utilities for summary generation.
"""

from typing import List, Dict, Any


class DataAnalyzer:
    """Utility class for analyzing message data for summary generation."""

    @staticmethod
    def group_messages_for_daily_summary(messages: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Group messages by thread/contact for daily summary."""
        grouped = {}

        for message in messages:
            # Group by thread_id or sender
            key = f"Thread {message['thread_id'][:8]}" if message.get(
                'thread_id') else message['sender']

            if key not in grouped:
                grouped[key] = []
            grouped[key].append(message)

        return grouped

    @staticmethod
    def analyze_weekly_trends(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze weekly trends and patterns."""
        if not messages:
            return {}

        # Count messages by day
        daily_counts = {}
        thread_counts = {}
        sender_counts = {}

        for message in messages:
            day = message['timestamp'].strftime('%Y-%m-%d')
            daily_counts[day] = daily_counts.get(day, 0) + 1

            thread_id = message.get('thread_id', 'unknown')
            thread_counts[thread_id] = thread_counts.get(thread_id, 0) + 1

            sender = message['sender']
            sender_counts[sender] = sender_counts.get(sender, 0) + 1

        # Find peak day
        peak_day = max(daily_counts.items(), key=lambda x: x[1])[
            0] if daily_counts else None

        # Top contacts
        top_contacts = sorted(sender_counts.items(),
                              key=lambda x: x[1], reverse=True)[:5]

        return {
            'daily_counts': daily_counts,
            'active_threads': len(thread_counts),
            'peak_day': peak_day,
            'top_contacts': [contact[0] for contact in top_contacts],
            'total_messages': len(messages)
        }

    @staticmethod
    def should_update_summary(existing_summary, new_message) -> bool:
        """Determine if summary should be updated with new message."""
        from datetime import datetime, timedelta

        # Simple heuristic - update if:
        # 1. Summary is older than 1 hour
        # 2. New message has significant content (>50 chars)

        time_threshold = datetime.utcnow() - timedelta(hours=1)
        content = new_message.content.get_primary_content() or ""

        return (
            existing_summary.created_at < time_threshold or
            len(content) > 50
        )
