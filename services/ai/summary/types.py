"""
Data types and enums for summary generation.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

try:
    from db.models.summary import SummaryType, SummaryScope
    DB_AVAILABLE = True
except ImportError:
    # Mock enums for testing
    class MockEnum:
        def __init__(self, value):
            self.value = value

        def __eq__(self, other):
            if isinstance(other, MockEnum):
                return self.value == other.value
            return self.value == other

        def __str__(self):
            return self.value

        def __repr__(self):
            return f"MockEnum('{self.value}')"

    class MockSummaryType:
        micro = MockEnum("micro")
        thread = MockEnum("thread")
        daily = MockEnum("daily")
        weekly = MockEnum("weekly")

    class MockSummaryScope:
        message = MockEnum("message")
        thread = MockEnum("thread")
        contact = MockEnum("contact")
        global_scope = MockEnum("global")

    SummaryType = MockSummaryType()
    SummaryScope = MockSummaryScope()
    DB_AVAILABLE = False


class SummaryQuality(str, Enum):
    """Summary quality levels."""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


@dataclass
class SummaryRequest:
    """Request for summary generation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    summary_type: SummaryType = field(
        default_factory=lambda: SummaryType.micro)
    scope_type: SummaryScope = field(
        default_factory=lambda: SummaryScope.message)
    scope_id: Optional[str] = None
    timeframe_start: Optional[datetime] = None
    timeframe_end: Optional[datetime] = None
    quality: SummaryQuality = field(
        default_factory=lambda: SummaryQuality.BASIC)
    max_length: int = 500
    include_action_items: bool = True
    include_entities: bool = True
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SummaryResult:
    """Result of summary generation."""
    request_id: str
    summary_id: Optional[str] = None
    content: str = ""
    key_points: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    processing_time: float = 0.0
    word_count: int = 0
    status: str = "pending"  # Use string to avoid import issues
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StreamingSummaryChunk:
    """Chunk of streaming summary content."""
    request_id: str
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    is_final: bool = False
    chunk_type: str = "content"  # content, key_point, action_item
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
