"""
Database Models Package

All SQLAlchemy models for the R.E.M.I backend.
"""

# Import all models here for Alembic autogenerate to work
from db.models.user import User
from db.models.platform_connection import PlatformConnection, PlatformType, ConnectionStatus
from db.models.raw_message import RawMessage
from db.models.message import Message
from db.models.contact import Contact
from db.models.thread import Thread
from db.models.participant import Participant
from db.models.attachment import Attachment
from db.models.entity import Entity
from db.models.summary import Summary
from db.models.embedding import Embedding
from db.models.collection_job import CollectionJob, JobType, JobStatus

__all__ = [
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
]
