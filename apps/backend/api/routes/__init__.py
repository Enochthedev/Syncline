"""
API Routes Package

Contains all API endpoint routers:
- Health check endpoints
- Connection management
- Collection endpoints
- Message endpoints
- Chat endpoints
- Contact endpoints
- Thread endpoints
- AI endpoints
"""

from . import health, connections, chats, ai

__all__ = ["health", "connections", "chats", "ai"]
