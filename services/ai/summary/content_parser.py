"""
Content parsing utilities for summary generation.
"""

import re
from typing import List
from .types import SummaryResult


class ContentParser:
    """Utility class for parsing and extracting structured information from summary content."""

    @staticmethod
    def extract_key_points(content: str) -> List[str]:
        """Extract key points from summary content."""
        key_points = []
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            # Look for numbered lists, bullet points, or key phrases
            if (line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '•', '*')) or
                    'key point' in line.lower() or 'important' in line.lower()):
                # Clean up the line
                cleaned = line.lstrip('1234567890.-•* ').strip()
                if cleaned and len(cleaned) > 10:
                    key_points.append(cleaned)

        return key_points[:5]  # Limit to top 5 key points

    @staticmethod
    def extract_action_items(content: str) -> List[str]:
        """Extract action items from summary content."""
        action_items = []
        lines = content.split('\n')

        action_keywords = ['action', 'todo', 'follow up',
                           'next step', 'need to', 'should', 'will', 'must']

        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in action_keywords):
                # Clean up the line
                cleaned = line.lstrip('1234567890.-•* ').strip()
                if cleaned and len(cleaned) > 5:
                    action_items.append(cleaned)

        return action_items[:3]  # Limit to top 3 action items

    @staticmethod
    def extract_entities(content: str) -> List[str]:
        """Extract entities (people, organizations, topics) from summary content."""
        # This is a simple implementation - could be enhanced with NER
        entities = []

        # Find potential names (capitalized words)
        potential_names = re.findall(
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)

        # Filter out common words
        common_words = {'The', 'This', 'That', 'These',
                        'Those', 'Summary', 'Messages', 'Today', 'Week'}
        entities = [
            name for name in potential_names if name not in common_words]

        return list(set(entities))[:5]  # Unique entities, limit to 5

    @staticmethod
    def calculate_confidence_score(result: SummaryResult) -> float:
        """Calculate confidence score based on summary quality indicators."""
        score = 0.5  # Base score

        # Content length factor
        if 50 <= result.word_count <= result.word_count * 1.2:  # Within reasonable range
            score += 0.2

        # Key points factor
        if result.key_points:
            score += min(len(result.key_points) * 0.1, 0.2)

        # Action items factor
        if result.action_items:
            score += min(len(result.action_items) * 0.05, 0.1)

        # Entities factor
        if result.entities:
            score += min(len(result.entities) * 0.02, 0.1)

        return min(score, 1.0)

    @classmethod
    def parse_summary_response(
        cls,
        summary_content: str,
        result: SummaryResult,
        request
    ) -> SummaryResult:
        """Parse AI response and extract structured information."""
        result.content = summary_content.strip()
        result.word_count = len(result.content.split())

        # Extract key points (look for numbered lists or bullet points)
        key_points = cls.extract_key_points(summary_content)
        result.key_points = key_points

        # Extract action items (look for action-oriented language)
        if request.include_action_items:
            action_items = cls.extract_action_items(summary_content)
            result.action_items = action_items

        # Extract entities (look for mentioned names, organizations, etc.)
        if request.include_entities:
            entities = cls.extract_entities(summary_content)
            result.entities = entities

        # Calculate confidence score based on content quality
        result.confidence_score = cls.calculate_confidence_score(result)

        return result
