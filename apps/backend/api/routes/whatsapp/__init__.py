"""
WhatsApp API Routes Module

Modular WhatsApp routes split by functionality:
- auth.py: Authentication and session management
- auth_enhanced.py: Enhanced authentication with better error handling
- messaging.py: Message operations and sync
- messaging_enhanced.py: Enhanced sync with retry logic and diagnostics
- status.py: Status checking and health monitoring
"""

from fastapi import APIRouter
from . import auth, messaging, messaging_enhanced, status

# Try to import auth_enhanced if it exists
try:
    from . import auth_enhanced
    HAS_AUTH_ENHANCED = True
except ImportError:
    HAS_AUTH_ENHANCED = False

from ..whatsapp_connections import router as connections_router

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(auth.router, tags=["WhatsApp Auth"])
router.include_router(messaging.router, tags=["WhatsApp Messaging"])
router.include_router(messaging_enhanced.router, prefix="/enhanced", tags=["WhatsApp Enhanced"])
router.include_router(status.router, tags=["WhatsApp Status"])
router.include_router(connections_router, prefix="/connections", tags=["WhatsApp Connections"])

# Include enhanced auth if available
if HAS_AUTH_ENHANCED:
    router.include_router(auth_enhanced.router, prefix="/enhanced", tags=["WhatsApp Auth Enhanced"])