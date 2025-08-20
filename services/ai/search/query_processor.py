"""
Natural language query processing for intelligent search.

This module handles query intent detection, entity extraction,
and query enhancement for better search results.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from services.ai.engine import get_ai_engine
from .types import SearchQuery, QueryIntent, SearchFilters

logger = logging.getLogger(__name__)


class QueryProcessor:
    """
    Processes natural language queries for intelligent search.

    Handles intent detection, entity extraction, temporal parsing,
    and query enhancement to improve search accuracy.
    """

    def __init__(self):
        """Initialize the query processor."""
        self.ai_engine = None

        # Intent detection patterns
        self.intent_patterns = {
            QueryIntent.COMMITMENT_SEARCH: [
                r"what did i (promise|commit|agree)",
                r"(promised|committed|agreed) .* (to|with)",
                r"my (commitments|promises|agreements)",
                r"what am i supposed to",
                r"deadline.*for",
            ],
            QueryIntent.PERSON_SEARCH: [
                r"messages? (from|with|to) (\w+)",
                r"conversation with (\w+)",
                r"(\w+) (said|wrote|mentioned)",
                r"talk to (\w+) about",
            ],
            QueryIntent.TIME_BASED_SEARCH: [
                r"(yesterday|today|last week|this week)",
                r"(before|after|since|until) (\d{4}-\d{2}-\d{2})",
                r"in (january|february|march|april|may|june|july|august|september|october|november|december)",
                r"(\d+) (days?|weeks?|months?) ago",
            ],
            QueryIntent.FILE_SEARCH: [
                r"(files?|documents?|attachments?) (shared|sent)",
                r"(shared|sent) (files?|documents?|attachments?)",
                r"(pdf|doc|image|video) (from|with|files?)",
                r"shared .* with (\w+)",
                r"attachments in",
                r"(image|video|audio) files",
            ],
            QueryIntent.TOPIC_SEARCH: [
                r"about (\w+)",
                r"regarding (\w+)",
                r"discussion (on|about) (\w+)",
                r"project (\w+)",
            ],
        }

        # Temporal parsing patterns
        self.temporal_patterns = {
            "yesterday": lambda: datetime.now() - timedelta(days=1),
            "today": lambda: datetime.now(),
            "last week": lambda: datetime.now() - timedelta(weeks=1),
            "this week": lambda: datetime.now() - timedelta(days=datetime.now().weekday()),
        }

        # Regex temporal patterns
        self.temporal_regex_patterns = [
            (r"(\d+) days? ago", lambda m: datetime.now() -
             timedelta(days=int(m.group(1)))),
            (r"(\d+) weeks? ago", lambda m: datetime.now() -
             timedelta(weeks=int(m.group(1)))),
            (r"(\d+) months? ago", lambda m: datetime.now() -
             timedelta(days=int(m.group(1)) * 30)),
        ]

    async def initialize(self) -> None:
        """Initialize AI engine for advanced processing."""
        try:
            self.ai_engine = await get_ai_engine()
            logger.info("QueryProcessor initialized with AI engine")
        except Exception as e:
            logger.warning(f"Failed to initialize AI engine: {e}")

    async def process_query(self, query: SearchQuery) -> SearchQuery:
        """
        Process a search query to enhance it with intent and extracted information.

        Args:
            query: The search query to process

        Returns:
            Enhanced search query with detected intent and extracted entities
        """
        try:
            # Detect query intent
            query.intent = self._detect_intent(query.text)

            # Extract entities and temporal constraints
            query.extracted_entities = await self._extract_entities(query.text)
            query.temporal_constraints = self._extract_temporal_constraints(
                query.text)

            # Process query text for better search
            query.processed_text = self._process_query_text(query.text)

            # Apply intent-specific enhancements
            query = await self._apply_intent_enhancements(query)

            logger.debug(
                f"Processed query: intent={query.intent}, entities={len(query.extracted_entities or [])}")

            return query

        except Exception as e:
            logger.error(f"Failed to process query: {e}")
            # Return original query if processing fails
            return query

    def _detect_intent(self, query_text: str) -> QueryIntent:
        """Detect the intent of a search query using pattern matching."""
        query_lower = query_text.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent

        return QueryIntent.GENERAL_SEARCH

    async def _extract_entities(self, query_text: str) -> List[Dict[str, Any]]:
        """Extract entities from the query text."""
        entities = []

        try:
            # Extract person names (simple pattern matching)
            person_matches = re.findall(
                r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', query_text)
            for person in person_matches:
                entities.append({
                    "type": "person",
                    "value": person,
                    "confidence": 0.8
                })

            # Extract email addresses
            email_matches = re.findall(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', query_text)
            for email in email_matches:
                entities.append({
                    "type": "email",
                    "value": email,
                    "confidence": 0.9
                })

            # Use AI engine for more sophisticated entity extraction if available
            if self.ai_engine:
                ai_entities = await self._ai_extract_entities(query_text)
                entities.extend(ai_entities)

        except Exception as e:
            logger.error(f"Failed to extract entities: {e}")

        return entities

    async def _ai_extract_entities(self, query_text: str) -> List[Dict[str, Any]]:
        """Use AI engine for advanced entity extraction."""
        try:
            prompt = f"""
            Extract entities from this search query: "{query_text}"
            
            Return entities in this format:
            - Type: person, organization, topic, file, date, location
            - Value: the actual entity text
            - Confidence: 0.0 to 1.0
            
            Focus on entities that would be useful for search filtering.
            """

            response = await self.ai_engine.generate_text(
                prompt=prompt,
                max_tokens=200,
                temperature=0.1
            )

            # Parse AI response (simplified - would need more robust parsing)
            entities = []
            lines = response.strip().split('\n')

            for line in lines:
                if ':' in line and any(t in line.lower() for t in ['person', 'organization', 'topic', 'file', 'date']):
                    parts = line.split(':')
                    if len(parts) >= 2:
                        entity_type = parts[0].strip().lower()
                        value = parts[1].strip()
                        entities.append({
                            "type": entity_type,
                            "value": value,
                            "confidence": 0.7
                        })

            return entities

        except Exception as e:
            logger.error(f"AI entity extraction failed: {e}")
            return []

    def _extract_temporal_constraints(self, query_text: str) -> Dict[str, Any]:
        """Extract temporal constraints from the query."""
        constraints = {}
        query_lower = query_text.lower()

        try:
            # Check simple patterns
            for pattern, date_func in self.temporal_patterns.items():
                if pattern in query_lower:
                    constraints["date_from"] = date_func()
                    break

            # Check regex patterns if no simple pattern matched
            if not constraints:
                for pattern, date_func in self.temporal_regex_patterns:
                    match = re.search(pattern, query_lower)
                    if match:
                        constraints["date_from"] = date_func(match)
                        break

            # Extract date ranges
            date_range_match = re.search(
                r'between (\d{4}-\d{2}-\d{2}) and (\d{4}-\d{2}-\d{2})', query_lower)
            if date_range_match:
                constraints["date_from"] = datetime.strptime(
                    date_range_match.group(1), "%Y-%m-%d")
                constraints["date_to"] = datetime.strptime(
                    date_range_match.group(2), "%Y-%m-%d")

        except Exception as e:
            logger.error(f"Failed to extract temporal constraints: {e}")

        return constraints

    def _process_query_text(self, query_text: str) -> str:
        """Process and clean query text for better search."""
        # Remove common stop words that don't add search value
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but',
                      'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}

        # Split into words and filter
        words = query_text.lower().split()
        filtered_words = [
            word for word in words if word not in stop_words and len(word) > 2]

        # Rejoin and return
        return ' '.join(filtered_words)

    async def _apply_intent_enhancements(self, query: SearchQuery) -> SearchQuery:
        """Apply intent-specific enhancements to the query."""
        if not query.filters:
            query.filters = SearchFilters()

        try:
            if query.intent == QueryIntent.COMMITMENT_SEARCH:
                # Focus on messages with action items or commitments
                query.filters.entity_types = ["task", "commitment", "deadline"]

            elif query.intent == QueryIntent.PERSON_SEARCH:
                # Extract person names and add to participant filters
                person_entities = [e for e in (
                    query.extracted_entities or []) if e["type"] == "person"]
                if person_entities:
                    query.filters.participants = [
                        e["value"] for e in person_entities]

            elif query.intent == QueryIntent.FILE_SEARCH:
                # Focus on messages with attachments
                query.filters.has_attachments = True

            elif query.intent == QueryIntent.TIME_BASED_SEARCH:
                # Apply temporal constraints
                if query.temporal_constraints:
                    if "date_from" in query.temporal_constraints:
                        query.filters.date_from = query.temporal_constraints["date_from"]
                    if "date_to" in query.temporal_constraints:
                        query.filters.date_to = query.temporal_constraints["date_to"]

        except Exception as e:
            logger.error(f"Failed to apply intent enhancements: {e}")

        return query

    def generate_search_suggestions(self, query_text: str) -> List[str]:
        """Generate search suggestions based on query text."""
        suggestions = []

        try:
            query_lower = query_text.lower()

            # Intent-based suggestions
            if "promise" in query_lower or "commit" in query_lower:
                suggestions.extend([
                    "commitments from last week",
                    "promises to [person name]",
                    "deadlines this month"
                ])

            if "file" in query_lower or "document" in query_lower:
                suggestions.extend([
                    "files shared with [person]",
                    "documents from [platform]",
                    "attachments in [thread]"
                ])

            if any(word in query_lower for word in ["who", "person", "contact"]):
                suggestions.extend([
                    "messages from [person]",
                    "conversations with [person]",
                    "participants in [thread]"
                ])

        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")

        return suggestions[:5]  # Limit to 5 suggestions
