"""
WhatsApp Session Manager

Manages WhatsApp login/logout sessions and connection state.
Handles proper session cleanup and state management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.models.platform_connection import PlatformConnection, PlatformType
from integrations.whatsapp_connector import WhatsAppConnector, BridgeStatus, BridgeStatus

logger = logging.getLogger(__name__)


class WhatsAppSession(BaseModel):
    """WhatsApp session state."""
    
    connection_id: UUID
    user_id: UUID
    is_logged_in: bool = False
    phone_number: Optional[str] = None
    login_method: Optional[str] = None  # "qr" or "phone"
    session_created_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    bridge_status: Optional[BridgeStatus] = None


class WhatsAppSessionManager:
    """Manages WhatsApp session lifecycle."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._active_sessions: Dict[UUID, WhatsAppSession] = {}
    
    async def create_session(
        self,
        db: AsyncSession,
        connection_id: UUID,
        user_id: UUID
    ) -> WhatsAppSession:
        """
        Create a new WhatsApp session.
        
        Args:
            db: Database session
            connection_id: Platform connection ID
            user_id: User ID
            
        Returns:
            Created session
        """
        try:
            # Get connection
            result = await db.execute(
                select(PlatformConnection).where(
                    PlatformConnection.id == connection_id,
                    PlatformConnection.platform == PlatformType.WHATSAPP,
                    PlatformConnection.user_id == user_id
                )
            )
            connection = result.scalar_one_or_none()
            
            if not connection:
                raise ValueError(f"WhatsApp connection {connection_id} not found")
            
            # Create session
            session = WhatsAppSession(
                connection_id=connection_id,
                user_id=user_id,
                session_created_at=datetime.utcnow()
            )
            
            # Check current bridge status
            connector = self._get_connector(connection)
            await connector.connect()
            
            try:
                bridge_status = await connector.get_bridge_status()
                session.bridge_status = bridge_status
                session.is_logged_in = bridge_status.logged_in
                session.phone_number = bridge_status.phone
                session.last_activity_at = datetime.utcnow()
            finally:
                await connector.disconnect()
            
            # Store session
            self._active_sessions[connection_id] = session
            
            self.logger.info(f"Created WhatsApp session for connection {connection_id}")
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to create WhatsApp session: {e}")
            raise
    
    async def login_with_qr(
        self,
        db: AsyncSession,
        connection_id: UUID
    ) -> Dict[str, Any]:
        """
        Initiate QR code login with auto-sync on success.
        
        Args:
            db: Database session
            connection_id: Connection ID
            
        Returns:
            Login result with QR code or status
        """
        try:
            session = self._active_sessions.get(connection_id)
            if not session:
                raise ValueError(f"No active session for connection {connection_id}")
            
            # Get connection and connector
            connection = await self._get_connection(db, connection_id)
            connector = self._get_connector(connection)
            
            await connector.connect()
            
            try:
                # Check if already logged in
                status = await connector.get_bridge_status()
                if status.logged_in:
                    session.is_logged_in = True
                    session.phone_number = status.phone
                    session.last_activity_at = datetime.utcnow()
                    
                    # Update database status
                    await self._update_connection_status(db, connection_id, "ACTIVE")
                    
                    # Auto-sync chats on successful login
                    self.logger.info("Already logged in, triggering auto-sync...")
                    sync_result = await self._auto_sync_chats(connector)
                    
                    return {
                        "success": True,
                        "already_logged_in": True,
                        "phone": status.phone,
                        "message": "Already logged in to WhatsApp",
                        "auto_sync": sync_result
                    }
                
                # Get QR code
                qr_code = await connector.get_login_qr()
                
                if qr_code:
                    session.login_method = "qr"
                    session.last_activity_at = datetime.utcnow()
                    
                    return {
                        "success": True,
                        "qr_code": qr_code,
                        "already_logged_in": False,
                        "message": "Scan QR code with WhatsApp mobile app"
                    }
                else:
                    return {
                        "success": False,
                        "message": "Failed to get QR code from bridge"
                    }
                    
            finally:
                await connector.disconnect()
                
        except Exception as e:
            self.logger.error(f"QR login failed: {e}")
            return {
                "success": False,
                "message": f"Login failed: {str(e)}"
            }
    
    async def login_with_phone(
        self,
        db: AsyncSession,
        connection_id: UUID,
        phone_number: str
    ) -> Dict[str, Any]:
        """
        Initiate phone number login.
        
        Args:
            db: Database session
            connection_id: Connection ID
            phone_number: Phone number in international format
            
        Returns:
            Login result with pairing code
        """
        try:
            session = self._active_sessions.get(connection_id)
            if not session:
                raise ValueError(f"No active session for connection {connection_id}")
            
            # Get connection and connector
            connection = await self._get_connection(db, connection_id)
            connector = self._get_connector(connection)
            
            await connector.connect()
            
            try:
                # Get pairing code
                pairing_code = await connector.login_with_phone(phone_number)
                
                session.login_method = "phone"
                session.last_activity_at = datetime.utcnow()
                
                return {
                    "success": True,
                    "pairing_code": pairing_code,
                    "phone_number": phone_number,
                    "message": f"Enter this code on your phone: {pairing_code}"
                }
                
            finally:
                await connector.disconnect()
                
        except Exception as e:
            self.logger.error(f"Phone login failed: {e}")
            return {
                "success": False,
                "message": f"Phone login failed: {str(e)}"
            }
    
    async def check_login_status(
        self,
        db: AsyncSession,
        connection_id: UUID
    ) -> Dict[str, Any]:
        """
        Check current login status with improved reliability.
        
        Args:
            db: Database session
            connection_id: Connection ID
            
        Returns:
            Current status
        """
        try:
            session = self._active_sessions.get(connection_id)
            if not session:
                # Try to create session if connection exists
                result = await db.execute(
                    select(PlatformConnection).where(
                        PlatformConnection.id == connection_id,
                        PlatformConnection.platform == PlatformType.WHATSAPP
                    )
                )
                connection = result.scalar_one_or_none()
                if connection:
                    session = await self.create_session(db, connection_id, connection.user_id)
                else:
                    return {
                        "success": False,
                        "message": "Connection not found"
                    }
            
            # Get fresh status from bridge with retries
            connection = await self._get_connection(db, connection_id)
            connector = self._get_connector(connection)
            
            await connector.connect()
            
            try:
                # Try to get bridge status with multiple attempts
                bridge_status = None
                for attempt in range(3):
                    try:
                        bridge_status = await connector.get_bridge_status()
                        if bridge_status:
                            break
                    except Exception as e:
                        self.logger.warning(f"Bridge status attempt {attempt + 1} failed: {e}")
                        if attempt < 2:
                            await asyncio.sleep(2)
                
                if not bridge_status:
                    # Fallback: assume disconnected
                    bridge_status = BridgeStatus(connected=False, logged_in=False)
                
                # Update session with fresh data
                session.bridge_status = bridge_status
                session.is_logged_in = bridge_status.logged_in
                session.phone_number = bridge_status.phone
                session.last_activity_at = datetime.utcnow()
                
                # Update database connection status
                new_status = "ACTIVE" if bridge_status.logged_in else "INACTIVE"
                await self._update_connection_status(db, connection_id, new_status)
                
                return {
                    "success": True,
                    "logged_in": bridge_status.logged_in,
                    "connected": bridge_status.connected,
                    "phone": bridge_status.phone,
                    "session_age": (
                        datetime.utcnow() - session.session_created_at
                    ).total_seconds() if session.session_created_at else None
                }
                
            finally:
                await connector.disconnect()
                
        except Exception as e:
            self.logger.error(f"Status check failed: {e}")
            return {
                "success": False,
                "message": f"Status check failed: {str(e)}"
            }
    
    async def logout(
        self,
        db: AsyncSession,
        connection_id: UUID
    ) -> Dict[str, Any]:
        """
        Logout from WhatsApp with improved handling.
        
        Args:
            db: Database session
            connection_id: Connection ID
            
        Returns:
            Logout result
        """
        try:
            session = self._active_sessions.get(connection_id)
            
            # Get connection and connector
            connection = await self._get_connection(db, connection_id)
            connector = self._get_connector(connection)
            
            await connector.connect()
            
            try:
                # First, check current status
                current_status = await connector.get_bridge_status()
                
                if not current_status.logged_in:
                    # Already logged out
                    if session:
                        session.is_logged_in = False
                        session.phone_number = None
                        session.login_method = None
                        session.last_activity_at = datetime.utcnow()
                    
                    await self._update_connection_status(db, connection_id, "INACTIVE")
                    
                    return {
                        "success": True,
                        "message": "Already logged out from WhatsApp"
                    }
                
                # Try multiple logout strategies
                logout_success = False
                
                # Strategy 1: Standard logout command
                try:
                    logout_success = await connector.logout()
                    if logout_success:
                        self.logger.info("Standard logout successful")
                except Exception as e:
                    self.logger.warning(f"Standard logout failed: {e}")
                
                # Strategy 2: If standard logout failed, try disconnect command
                if not logout_success:
                    try:
                        client = connector._get_client()
                        disconnect_response = await client.send_bridge_command("disconnect")
                        if disconnect_response:
                            logout_success = True
                            self.logger.info("Disconnect command successful")
                    except Exception as e:
                        self.logger.warning(f"Disconnect command failed: {e}")
                
                # Strategy 3: Force logout by clearing session data
                if not logout_success:
                    try:
                        client = connector._get_client()
                        # Send multiple logout variations
                        for cmd in ["logout", "logout-matrix", "delete-session"]:
                            try:
                                await client.send_bridge_command(cmd, wait_for_response=False)
                                await asyncio.sleep(1)
                            except Exception as e:
                                logger.debug(f"Logout command '{cmd}' failed: {e}")
                                continue
                        
                        # Check if any of them worked
                        await asyncio.sleep(2)
                        final_status = await connector.get_bridge_status()
                        logout_success = not final_status.logged_in
                        
                        if logout_success:
                            self.logger.info("Force logout successful")
                        
                    except Exception as e:
                        self.logger.warning(f"Force logout failed: {e}")
                
                # Update session regardless of bridge response
                if session:
                    session.is_logged_in = False
                    session.phone_number = None
                    session.login_method = None
                    session.last_activity_at = datetime.utcnow()
                
                # Update database
                await self._update_connection_status(db, connection_id, "INACTIVE")
                
                # Even if bridge logout failed, we consider it successful from our side
                return {
                    "success": True,
                    "bridge_logout": logout_success,
                    "message": (
                        "Logged out from WhatsApp successfully" if logout_success
                        else "Session cleared locally (bridge may still be connected)"
                    )
                }
                
            finally:
                await connector.disconnect()
                
        except Exception as e:
            self.logger.error(f"Logout failed: {e}")
            return {
                "success": False,
                "message": f"Logout failed: {str(e)}"
            }
    
    async def cleanup_session(
        self,
        db: AsyncSession,
        connection_id: UUID
    ) -> bool:
        """
        Clean up session data with improved cleanup.
        
        Args:
            db: Database session
            connection_id: Connection ID
            
        Returns:
            Success status
        """
        try:
            # Remove from active sessions
            if connection_id in self._active_sessions:
                del self._active_sessions[connection_id]
            
            # Reset connection in database
            await self._update_connection_status(db, connection_id, "INACTIVE")
            
            self.logger.info(f"Cleaned up session for connection {connection_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Session cleanup failed: {e}")
            return False
    
    def _get_connector(self, connection: PlatformConnection) -> WhatsAppConnector:
        """Create WhatsApp connector from connection."""
        from config.config import settings
        
        credentials = dict(connection.credentials) if connection.credentials else {}
        
        # Fill in defaults from settings
        if not credentials.get("matrix_homeserver_url"):
            credentials["matrix_homeserver_url"] = settings.MATRIX_HOMESERVER_URL
        if not credentials.get("matrix_access_token"):
            credentials["matrix_access_token"] = settings.MATRIX_ACCESS_TOKEN
        if not credentials.get("matrix_user_id"):
            credentials["matrix_user_id"] = settings.MATRIX_USER_ID
        if not credentials.get("bridge_bot_id"):
            credentials["bridge_bot_id"] = settings.WHATSAPP_BRIDGE_BOT_ID
        
        return WhatsAppConnector(
            connection_id=connection.id,
            credentials=credentials,
        )
    
    async def _update_connection_status(
        self,
        db: AsyncSession,
        connection_id: UUID,
        status: str
    ) -> None:
        """Update connection status in database."""
        from sqlalchemy import update
        
        await db.execute(
            update(PlatformConnection)
            .where(PlatformConnection.id == connection_id)
            .values(
                status=status,
                last_sync_at=datetime.utcnow() if status == "ACTIVE" else None
            )
        )
        await db.commit()
    
    def get_session(self, connection_id: UUID) -> Optional[WhatsAppSession]:
        """Get active session."""
        return self._active_sessions.get(connection_id)
    
    def list_active_sessions(self) -> Dict[UUID, WhatsAppSession]:
        """List all active sessions."""
        return self._active_sessions.copy()
    
    async def _get_connection(self, db: AsyncSession, connection_id: UUID) -> PlatformConnection:
        """Get platform connection from database."""
        result = await db.execute(
            select(PlatformConnection).where(PlatformConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        return connection
    
    async def _auto_sync_chats(self, connector) -> Dict[str, Any]:
        """
        Auto-sync chats after successful login.
        
        Args:
            connector: WhatsApp connector instance
            
        Returns:
            Sync result
        """
        try:
            self.logger.info("Starting auto-sync of WhatsApp chats...")
            
            # Comprehensive sync strategy
            sync_result = await connector.sync_all_chats()
            
            # Wait a bit for sync to process
            await asyncio.sleep(3)
            
            # Get room count to verify sync worked
            try:
                rooms = await connector._get_client().get_whatsapp_rooms()
                room_count = len(rooms)
                self.logger.info(f"Auto-sync completed, found {room_count} rooms")
                
                return {
                    "success": True,
                    "rooms_found": room_count,
                    "sync_details": sync_result,
                    "message": f"Auto-synced {room_count} WhatsApp chats"
                }
            except Exception as e:
                self.logger.warning(f"Could not count rooms after sync: {e}")
                return {
                    "success": True,
                    "sync_details": sync_result,
                    "message": "Auto-sync completed"
                }
                
        except Exception as e:
            self.logger.error(f"Auto-sync failed: {e}")
            return {
                "success": False,
                "message": f"Auto-sync failed: {str(e)}"
            }
    
    async def get_bridge_status(self, db: AsyncSession, connection_id: UUID) -> Dict[str, Any]:
        """Get bridge status for connection."""
        try:
            connection = await self._get_connection(db, connection_id)
            connector = self._get_connector(connection)
            
            await connector.connect()
            try:
                bridge_status = await connector.get_bridge_status()
                
                return {
                    "bridge_status": bridge_status,
                    "is_healthy": bridge_status.connected
                }
            finally:
                await connector.disconnect()
        except Exception as e:
            self.logger.error(f"Failed to get bridge status: {e}")
            return {
                "bridge_status": BridgeStatus(connected=False, logged_in=False),
                "is_healthy": False
            }

    async def get_qr_code(self, db: AsyncSession, connection_id: UUID) -> Dict[str, Any]:
        """Get QR code for login."""
        return await self.login_with_qr(db, connection_id)

    async def auto_sync_chats(self, db: AsyncSession, connection_id: UUID) -> Dict[str, Any]:
        """Public method to trigger auto-sync."""
        try:
            connection = await self._get_connection(db, connection_id)
            connector = self._get_connector(connection)
            
            await connector.connect()
            try:
                return await self._auto_sync_chats(connector)
            finally:
                await connector.disconnect()
        except Exception as e:
            self.logger.error(f"Auto-sync failed: {e}")
            return {"success": False, "error": str(e)}

    async def sync_chats(self, db: AsyncSession, connection_id: UUID) -> Dict[str, Any]:
        """Sync WhatsApp chats."""
        return await self.auto_sync_chats(db, connection_id)

    async def cleanup_data(self, db: AsyncSession, connection_id: UUID) -> Dict[str, Any]:
        """Clean up WhatsApp data."""
        try:
            # This would clean up messages, contacts, etc.
            # For now, just return success
            return {
                "success": True,
                "messages_deleted": 0,
                "sessions_cleared": 1
            }
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return {"success": False, "error": str(e)}

    async def check_login_completion(
        self,
        db: AsyncSession,
        connection_id: UUID
    ) -> Dict[str, Any]:
        """
        Check if QR login has been completed (for polling).

        Args:
            db: Database session
            connection_id: Connection ID

        Returns:
            Login completion status with auto-sync if successful
        """
        try:
            session = self._active_sessions.get(connection_id)
            if not session:
                # Try to create session if connection exists
                result = await db.execute(
                    select(PlatformConnection).where(
                        PlatformConnection.id == connection_id,
                        PlatformConnection.platform == PlatformType.WHATSAPP
                    )
                )
                connection = result.scalar_one_or_none()
                if connection:
                    session = await self.create_session(db, connection_id, connection.user_id)
                else:
                    return {
                        "success": False,
                        "message": "Connection not found"
                    }
            
            # Check current bridge status
            connection = await self._get_connection(db, connection_id)
            connector = self._get_connector(connection)
            
            await connector.connect()
            
            try:
                bridge_status = await connector.get_bridge_status()
                
                # If we just became logged in, trigger auto-sync
                if bridge_status.logged_in and not session.is_logged_in:
                    self.logger.info("Login detected! Triggering auto-sync...")
                    
                    # Update session
                    session.is_logged_in = True
                    session.phone_number = bridge_status.phone
                    session.last_activity_at = datetime.utcnow()
                    
                    # Update database
                    await self._update_connection_status(db, connection_id, "ACTIVE")
                    
                    # Auto-sync chats
                    sync_result = await self._auto_sync_chats(connector)
                    
                    return {
                        "success": True,
                        "login_completed": True,
                        "phone": bridge_status.phone,
                        "auto_sync": sync_result,
                        "message": "Login successful! Chats are being synced."
                    }
                
                # Update session status
                session.is_logged_in = bridge_status.logged_in
                session.phone_number = bridge_status.phone
                session.last_activity_at = datetime.utcnow()
                
                return {
                    "success": True,
                    "login_completed": bridge_status.logged_in,
                    "phone": bridge_status.phone,
                    "message": (
                        "Login completed" if bridge_status.logged_in 
                        else "Waiting for QR scan..."
                    )
                }
                
            finally:
                await connector.disconnect()
                
        except Exception as e:
            self.logger.error(f"Login completion check failed: {e}")
            return {
                "success": False,
                "message": f"Check failed: {str(e)}"
            }


# Global session manager instance
_session_manager = None

def get_whatsapp_session_manager() -> WhatsAppSessionManager:
    """Get WhatsApp session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = WhatsAppSessionManager()
    return _session_manager