"""
Search Services

Provides search capabilities for messages:
- Full-text search using PostgreSQL
- Semantic search using vector embeddings
"""

from services.search.fulltext_search import (
    FullTextSearchService,
    FullTextSearchFilter,
    FullTextSearchResult,
    get_fulltext_search_service,
)

__all__ = [
    "FullTextSearchService",
    "FullTextSearchFilter",
    "FullTextSearchResult",
    "get_fulltext_search_service",
]
