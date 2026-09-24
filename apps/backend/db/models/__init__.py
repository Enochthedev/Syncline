"""
Database Models Package

All SQLAlchemy models for the R.E.M.I backend.
"""

from db.models.attachment import Attachment
from db.models.audit import AuditLog
from db.models.collection_job import CollectionJob, JobStatus, JobType
from db.models.contact import Contact
from db.models.embedding import Embedding
from db.models.entity import Entity
from db.models.memory import Memory, MemoryImportance, MemoryType
from db.models.message import Message
from db.models.participant import Participant
from db.models.platform_connection import (
    ConnectionStatus,
    PlatformConnection,
    PlatformType,
)
from db.models.raw_message import RawMessage
from db.models.summary import Summary
from db.models.thread import Thread

# Import all models here for Alembic autogenerate to work
from db.models.user import User

__all__ = [
    "AuditLog",
    "User",
    "PlatformConnection",
    "PlatformType",
    "ConnectionStatus",
    "RawMessage",
    "Message",
    "Contact",
    "Thread",
    "Participant",
    "Attachment",
    "Entity",
    "Summary",
    "Embedding",
    "CollectionJob",
    "JobType",
    "JobStatus",
    "Memory",
    "MemoryType",
    "MemoryImportance",
]
