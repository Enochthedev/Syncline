"""
Memory Model

Represents memories extracted from messages and conversations.
Used by the proactive memory system for context and recommendations.
"""

from enum import Enum
from sqlalchemy import Column, String, ForeignKey, Text, Boolean, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from db.base import Base


class MemoryType(str, Enum):
    """Types of memories that can be stored."""
    FACT = "fact"  # Factual information
    COMMITMENT = "commitment"  # Promises, deadlines, tasks
    PREFERENCE = "preference"  # Personal preferences
    RELATIONSHIP = "relationship"  # Relationship information
    PERSONAL = "personal"  # Personal information
    TASK = "task"  # Action items
    EVENT = "event"  # Events and meetings
    INSIGHT = "insight"  # AI-generated insights


class MemoryImportance(int, Enum):
    """Importance levels for memories."""
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5


class Memory(Base):
    """
    Memory model for storing extracted memories from conversations.
    
    Memories are pieces of information extracted from messages that
    are important for future context and recommendations.
    
    Attributes:
        type: Type of memory (fact, commitment, preference, etc.)
        content: The memory content/description
        importance: Importance level (1-5)
        contact_id: Related contact (nullable)
        thread_id: Related thread (nullable)
        platform: Platform where memory originated
        source_message_id: Original message that generated this memory
        metadata: Additional memory information
        is_active: Whether memory is active (for soft deletes)
        access_count: Number of times memory has been accessed
        last_accessed_at: When memory was last accessed
    """
    
    __tablename__ = "memories"
    
    # Memory type
    type = Column(String(50), nullable=False, index=True)
    
    # Memory content
    content = Column(Text, nullable=False)
    
    # Importance level (1-5)
    importance = Column(Integer, nullable=False, default=3, index=True)
    
    # Related entities
    contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    thread_id = Column(String(255), nullable=True, index=True)
    
    # Platform information
    platform = Column(String(50), nullable=True, index=True)
    
    # Source message
    source_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Additional metadata
    # Structure: {
    #   "due_date": "2024-01-15T10:00:00Z",  # For commitments
    #   "priority": "high|medium|low",
    #   "tags": ["work", "personal"],
    #   "entities": ["John Doe", "Acme Corp"],
    #   "confidence": 0.85,
    #   "extraction_method": "llm|rule_based",
    #   "consolidation_info": {...},
    #   "importance_history": [...],
    #   ...
    # }
    memory_metadata = Column(JSONB, nullable=True)
    
    # Memory status
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Access tracking
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    contact = relationship("Contact", back_populates="memories")
    source_message = relationship("Message")
    
    def __repr__(self) -> str:
        return f"<Memory(id={self.id}, type={self.type}, importance={self.importance})>"
    
    @property
    def memory_type(self) -> MemoryType:
        """Get memory type as enum."""
        return MemoryType(self.type)
    
    @property
    def memory_importance(self) -> MemoryImportance:
        """Get memory importance as enum."""
        return MemoryImportance(self.importance)
    
    def is_commitment(self) -> bool:
        """Check if memory is a commitment."""
        return self.type == MemoryType.COMMITMENT.value
    
    def is_overdue(self) -> bool:
        """Check if commitment is overdue."""
        if not self.is_commitment() or not self.memory_metadata:
            return False
        
        due_date_str = self.memory_metadata.get("due_date")
        if not due_date_str:
            return False
        
        try:
            from datetime import datetime
            due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
            return due_date < datetime.utcnow()
        except (ValueError, TypeError):
            return False
    
    def get_tags(self) -> list[str]:
        """Get memory tags."""
        if not self.memory_metadata:
            return []
        return self.memory_metadata.get("tags", [])
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the memory."""
        if not self.memory_metadata:
            self.memory_metadata = {}
        
        tags = self.memory_metadata.get("tags", [])
        if tag not in tags:
            tags.append(tag)
            self.memory_metadata["tags"] = tags
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the memory."""
        if not self.memory_metadata:
            return
        
        tags = self.memory_metadata.get("tags", [])
        if tag in tags:
            tags.remove(tag)
            self.memory_metadata["tags"] = tags