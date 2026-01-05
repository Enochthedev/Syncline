"""
Enhanced WhatsApp Message Sync Service

Provides improved message synchronization with:
- Retry logic with exponential backoff
- Better error handling and diagnostics
- Comprehensive logging and statistics
- Race condition prevention
- Bridge timeout handling
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import json
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from db.session import get_session
from db.models.platform_connection import PlatformConnection
from db.models.message import Message
from integrations.whatsapp_connector import WhatsAppConnector
from integrations.base_connector import AuthenticationError, ConnectionError
from services.message.normalizer import MessageNormalizer

logger = logging.getLogger(__name__)

# =============================================================================
# Enhanced Sync Statistics
# =============================================================================

class SyncStats:
    """Comprehensive sync statistics"""
    
    def __init__(self):
        self.sync_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
        self.total_rooms_processed = 0
        self.total_messages_fetched = 0
        self.total_messages_synced = 0
        self.total_messages_skipped = 0
        self.errors: List[str] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.bridge_timeouts = 0
        self.auth_failures = 0
        self.connection_failures = 0
        
    def start_sync(self):
        """Mark sync start time"""
        self.start_time = datetime.utcnow()
        
    def end_sync(self):
        """Mark sync end time"""
        self.end_time = datetime.utcnow()
        
    def add_attempt(self):
        """Record sync attempt"""
        self.sync_attempts += 1
        
    def add_success(self):
        """Record successful attempt"""
        self.successful_attempts += 1
        
    def add_failure(self, error: str):
        """Record failed attempt"""
        self.failed_attempts += 1
        self.last_error = error
        self.errors.append(f"Attempt {self.sync_attempts}: {error}")
        
        # Categorize error types
        if "auth" in error.lower() or "authorization" in error.lower():
            self.auth_failures += 1
        elif "timeout" in error.lower() or "bridge" in error.lower():
            self.bridge_timeouts += 1
        elif "connection" in error.lower():
            self.connection_failures += 1
            
    def get_duration(self) -> Optional[float]:
        """Get sync duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "sync_attempts": self.sync_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "total_rooms_processed": self.total_rooms_processed,
            "total_messages_fetched": self.total_messages_fetched,
            "total_messages_synced": self.total_messages_synced,
            "total_messages_skipped": self.total_messages_skipped,
            "errors": self.errors,
            "last_error": self.last_error,
            "bridge_timeouts": self.bridge_timeouts,
            "auth_failures": self.auth_failures,
            "connection_failures": self.connection_failures,
            "duration_seconds": self.get_duration(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }

# =============================================================================
# Enhanced Sync Service
# =============================================================================

class WhatsAppSyncEnhanced:
    """Enhanced WhatsApp message synchronization service"""
    
    def __init__(self):
        self.message_normalizer = MessageNormalizer()
        self._active_syncs: Dict[UUID, asyncio.Lock] = {}
        
    async def sync_messages_enhanced(
        self,
        connection_id: UUID,
        limit: int = 100,
        force: bool = False,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 30.0
    ) -> Dict[str, Any]:
        """
        Enhanced message sync with retry logic and comprehensive statistics
        
        Args:
            connection_id: Platform connection ID
            limit: Maximum messages to sync per room
            force: Force sync even if recently synced
            max_retries: Maximum retry attempts
            base_delay: Base delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            
        Returns:
            Dictionary with sync results and statistics
        """
        stats = SyncStats()
        stats.start_sync()
        
        # Prevent concurrent syncs for the same connection
        if connection_id not in self._active_syncs:
            self._active_syncs[connection_id] = asyncio.Lock()
            
        async with self._active_syncs[connection_id]:
            logger.info(f"Starting enhanced sync for connection {connection_id}")
            
            for attempt in range(1, max_retries + 1):
                stats.add_attempt()
                logger.info(f"Sync attempt {attempt}/{max_retries} for connection {connection_id}")
                
                try:
                    # Execute sync attempt
                    result = await self._execute_sync(connection_id, limit, force, stats)
                    
                    if result["success"]:
                        stats.add_success()
                        stats.end_sync()
                        
                        return {
                            "success": True,
                            "connection_id": str(connection_id),
                            "total_messages_synced": stats.total_messages_synced,
                            "total_rooms_processed": stats.total_rooms_processed,
                            "stats": stats.to_dict(),
                            "message": f"Successfully synced {stats.total_messages_synced} messages from {stats.total_rooms_processed} rooms"
                        }
                    else:
                        # Sync returned failure
                        error_msg = result.get("error", "Unknown sync error")
                        stats.add_failure(error_msg)
                        
                except Exception as e:
                    error_msg = str(e)
                    stats.add_failure(error_msg)
                    logger.error(f"Message sync failed: {error_msg}")
                
                # Calculate delay for next retry
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1), max_delay)
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
            
            # All retries failed
            stats.end_sync()
            return {
                "success": False,
                "connection_id": str(connection_id),
                "error": f"All {max_retries} sync attempts failed. Last error: {stats.last_error}",
                "total_messages_synced": stats.total_messages_synced,
                "total_rooms_processed": stats.total_rooms_processed,
                "stats": stats.to_dict()
            }
    
    async def _execute_sync(
        self,
        connection_id: UUID,
        limit: int,
        force: bool,
        stats: SyncStats
    ) -> Dict[str, Any]:
        """Execute a single sync attempt"""
        
        async with get_session() as session:
            # Get connection
            result = await session.execute(
                select(PlatformConnection).where(PlatformConnection.id == connection_id)
            )
            connection = result.scalar_one_or_none()
            
            if not connection:
                return {"success": False, "error": f"Connection {connection_id} not found"}
            
            # Create connector
            connector = WhatsAppConnector(connection_id, connection.credentials)
            
            try:
                # Connect to WhatsApp
                await connector.connect()
                
                # Check if logged in
                status = await connector.get_status()
                if not status.get("logged_in", False):
                    return {"success": False, "error": "WhatsApp not logged in. Please scan QR code first."}
                
                # Get rooms
                rooms = await connector.get_rooms()
                stats.total_rooms_processed = len(rooms)
                
                logger.info(f"Found {len(rooms)} rooms to sync")
                
                # Sync messages from each room
                for room in rooms:
                    try:
                        room_id = room.get("room_id")
                        if not room_id:
                            continue
                            
                        # Fetch messages from room
                        messages = await connector.fetch_messages(room_id, limit=limit)
                        stats.total_messages_fetched += len(messages)
                        
                        # Process and save messages
                        for message_data in messages:
                            try:
                                # Normalize message
                                normalized = await self.message_normalizer.normalize_message(
                                    message_data, "whatsapp", connection_id
                                )
                                
                                if normalized:
                                    # Check if message already exists
                                    existing = await session.execute(
                                        select(Message).where(
                                            and_(
                                                Message.connection_id == connection_id,
                                                Message.platform_message_id == normalized.get("platform_message_id")
                                            )
                                        )
                                    )
                                    
                                    if existing.scalar_one_or_none():
                                        stats.total_messages_skipped += 1
                                        continue
                                    
                                    # Save new message
                                    message = Message(**normalized)
                                    session.add(message)
                                    stats.total_messages_synced += 1
                                    
                            except Exception as e:
                                logger.error(f"Failed to process message: {e}")
                                continue
                    
                    except Exception as e:
                        logger.error(f"Failed to sync room {room_id}: {e}")
                        continue
                
                # Commit all changes
                await session.commit()
                
                # Update connection last sync time
                connection.last_sync_at = datetime.utcnow()
                await session.commit()
                
                return {"success": True}
                
            except AuthenticationError as e:
                return {"success": False, "error": f"Authentication failed: {e}"}
            except ConnectionError as e:
                return {"success": False, "error": f"Connection failed: {e}"}
            except Exception as e:
                return {"success": False, "error": f"Unexpected error: {e}"}
            finally:
                try:
                    await connector.disconnect()
                except Exception as e:
                    logger.debug(f"Failed to disconnect connector during cleanup: {e}")
    
    async def get_sync_status(self, connection_id: UUID) -> Dict[str, Any]:
        """Get current sync status for a connection"""
        
        async with get_session() as session:
            # Get connection
            result = await session.execute(
                select(PlatformConnection).where(PlatformConnection.id == connection_id)
            )
            connection = result.scalar_one_or_none()
            
            if not connection:
                return {"error": "Connection not found"}
            
            # Get message counts
            message_count = await session.execute(
                select(func.count(Message.id)).where(Message.connection_id == connection_id)
            )
            total_messages = message_count.scalar() or 0
            
            # Check if sync is currently running
            is_syncing = connection_id in self._active_syncs and self._active_syncs[connection_id].locked()
            
            return {
                "connection_id": str(connection_id),
                "status": connection.status.value,
                "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
                "total_messages": total_messages,
                "is_syncing": is_syncing,
                "platform": connection.platform.value
            }
    
    async def discover_rooms_enhanced(
        self,
        connection_id: UUID,
        wait_time: int = 10,
        max_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Enhanced room discovery with retry logic
        
        Args:
            connection_id: Platform connection ID
            wait_time: Time to wait for rooms to appear (seconds)
            max_attempts: Maximum discovery attempts
            
        Returns:
            Dictionary with discovery results
        """
        
        async with get_session() as session:
            # Get connection
            result = await session.execute(
                select(PlatformConnection).where(PlatformConnection.id == connection_id)
            )
            connection = result.scalar_one_or_none()
            
            if not connection:
                return {"success": False, "error": f"Connection {connection_id} not found"}
            
            connector = WhatsAppConnector(connection_id, connection.credentials)
            
            try:
                await connector.connect()
                
                for attempt in range(1, max_attempts + 1):
                    logger.info(f"Room discovery attempt {attempt}/{max_attempts}")
                    
                    # Trigger room discovery
                    await connector.discover_rooms()
                    
                    # Wait for rooms to appear
                    await asyncio.sleep(wait_time)
                    
                    # Check for rooms
                    rooms = await connector.get_rooms()
                    
                    if rooms:
                        return {
                            "success": True,
                            "rooms_found": len(rooms),
                            "rooms": rooms[:5],  # Return first 5 rooms as sample
                            "message": f"Discovered {len(rooms)} rooms"
                        }
                
                return {
                    "success": False,
                    "error": f"No rooms found after {max_attempts} attempts",
                    "rooms_found": 0
                }
                
            except Exception as e:
                return {"success": False, "error": str(e)}
            finally:
                try:
                    await connector.disconnect()
                except Exception as e:
                    logger.debug(f"Failed to disconnect connector during cleanup: {e}")

# =============================================================================
# Service Instance
# =============================================================================

whatsapp_sync_enhanced = WhatsAppSyncEnhanced()

def get_enhanced_whatsapp_sync_service() -> WhatsAppSyncEnhanced:
    """Get the enhanced WhatsApp sync service instance"""
    return whatsapp_sync_enhanced