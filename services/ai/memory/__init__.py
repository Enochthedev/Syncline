"""
Proactive memory AI services for the MESH system.

This module provides AI-powered proactive memory capabilities including:
- Commitment tracking and follow-up detection
- Contact dossier generation with relationship insights
- File tracking system for shared resources
- Nudge generation with contextual reminders
"""

from .agent import ProactiveMemoryAgent
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
    MemoryContext
)

__all__ = [
    "ProactiveMemoryAgent",
    "Commitment",
    "CommitmentStatus",
    "CommitmentType",
    "ContactDossier",
    "FileReference",
    "Nudge",
    "NudgeType",
    "NudgePriority",
    "RelationshipInsight",
    "MemoryContext"
]
