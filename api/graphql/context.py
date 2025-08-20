"""GraphQL context management for MESH ingestion system."""

from typing import Optional, Dict, Any
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.fastapi import BaseContext

from db.session import get_db


class GraphQLContext(BaseContext):
    """GraphQL execution context."""

    def __init__(self, request: Request):
        super().__init__()
        self.request = request
        self.db_session: Optional[AsyncSession] = None
        self.user_id: Optional[str] = None
        self.tenant_id: Optional[str] = None
        self.permissions: Optional[Dict[str, Any]] = None


async def get_context(request: Request) -> GraphQLContext:
    """Create GraphQL context from FastAPI request."""
    context = GraphQLContext(request=request)

    # Extract user information from request (will be enhanced with auth)
    # For now, we'll use placeholder values
    context.user_id = request.headers.get("X-User-ID")
    context.tenant_id = request.headers.get("X-Tenant-ID", "default")

    # Set default permissions (will be enhanced with RBAC)
    context.permissions = {
        "read_messages": True,
        "read_threads": True,
        "read_participants": True,
        "search": True,
        "read_summaries": True,
        "read_contact_dossiers": True,
        "read_file_references": True
    }

    return context
