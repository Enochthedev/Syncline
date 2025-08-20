"""
Matrix authentication and session management.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
import uuid
import io
import base64

# Optional QR code dependency
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

from .types import (
    BridgeAuthSession, QRCodeData, AuthMethod, BridgeAuthError,
    BridgeConfig, BridgeInstance
)

logger = logging.getLogger(__name__)


class MatrixAuthManager:
    """
    Manages Matrix homeserver authentication and bridge session management.

    Handles QR code generation for WhatsApp, OAuth flows for Instagram/Facebook,
    and session persistence across bridge restarts.
    """

    def __init__(
        self,
        homeserver_url: str,
        access_token: str,
        user_id: str,
        device_id: str
    ):
        self.homeserver_url = homeserver_url
        self.access_token = access_token
        self.user_id = user_id
        self.device_id = device_id

        # Session management
        self._matrix_session: Optional[aiohttp.ClientSession] = None
        self._auth_sessions: Dict[str, BridgeAuthSession] = {}
        self._qr_codes: Dict[str, QRCodeData] = {}

        # Sync state
        self._sync_token: Optional[str] = None
        self._sync_running = False

    async def initialize(self) -> None:
        """Initialize Matrix authentication manager."""
        try:
            logger.info("Initializing Matrix authentication manager")

            # Create Matrix session
            self._matrix_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "User-Agent": "MESH Matrix Bridge Hub"
                }
            )

            # Verify authentication
            await self._verify_matrix_auth()

            logger.info("Matrix authentication manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Matrix auth manager: {e}")
            raise BridgeAuthError(f"Auth manager initialization failed: {e}")

    async def cleanup(self) -> None:
        """Cleanup authentication manager resources."""
        try:
            if self._matrix_session:
                await self._matrix_session.close()
                self._matrix_session = None

            # Clear auth sessions
            self._auth_sessions.clear()
            self._qr_codes.clear()

            logger.info("Matrix authentication manager cleaned up")

        except Exception as e:
            logger.error(f"Error cleaning up auth manager: {e}")

    async def _verify_matrix_auth(self) -> None:
        """Verify Matrix homeserver authentication."""
        try:
            url = f"{self.homeserver_url}/_matrix/client/r0/account/whoami"

            async with self._matrix_session.get(url) as response:
                if response.status == 401:
                    raise BridgeAuthError("Invalid Matrix access token")
                elif response.status != 200:
                    raise BridgeAuthError(
                        f"Matrix API error: {response.status}")

                user_info = await response.json()
                logger.info(
                    f"Matrix auth verified for user: {user_info.get('user_id')}")

        except Exception as e:
            logger.error(f"Matrix auth verification failed: {e}")
            raise BridgeAuthError(f"Auth verification failed: {e}")

    async def start_bridge_auth(
        self,
        bridge_config: BridgeConfig
    ) -> BridgeAuthSession:
        """Start authentication process for a bridge."""
        try:
            session_id = str(uuid.uuid4())

            auth_session = BridgeAuthSession(
                bridge_name=bridge_config.bridge_name,
                session_id=session_id,
                auth_method=bridge_config.auth_method,
                status="starting",
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
            )

            if bridge_config.auth_method == AuthMethod.QR_CODE:
                # Generate QR code for WhatsApp
                qr_data = await self._generate_whatsapp_qr(bridge_config)
                auth_session.qr_data = qr_data
                auth_session.status = "qr_ready"

            elif bridge_config.auth_method == AuthMethod.OAUTH:
                # Start OAuth flow for Instagram/Facebook
                oauth_url = await self._start_oauth_flow(bridge_config)
                auth_session.metadata["oauth_url"] = oauth_url
                auth_session.status = "oauth_ready"

            self._auth_sessions[session_id] = auth_session

            logger.info(
                f"Started auth session for {bridge_config.bridge_name}: {session_id}")
            return auth_session

        except Exception as e:
            logger.error(f"Failed to start bridge auth: {e}")
            raise BridgeAuthError(f"Failed to start auth: {e}")

    async def _generate_whatsapp_qr(self, bridge_config: BridgeConfig) -> QRCodeData:
        """Generate QR code for WhatsApp authentication."""
        try:
            # This would typically interact with the mautrix-whatsapp bridge
            # For now, we'll create a placeholder QR code

            # Generate a unique auth URL
            auth_token = str(uuid.uuid4())
            auth_url = f"whatsapp://auth/{auth_token}"

            if HAS_QRCODE:
                # Create QR code
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(auth_url)
                qr.make(fit=True)

                # Convert to base64 image
                img = qr.make_image(fill_color="black", back_color="white")
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)

                qr_code_b64 = base64.b64encode(img_buffer.getvalue()).decode()
            else:
                # Fallback: create a placeholder QR code data
                qr_code_b64 = "placeholder_qr_code_data"
                logger.warning(
                    "QR code library not available, using placeholder")

            qr_data = QRCodeData(
                qr_code=qr_code_b64,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                bridge_name=bridge_config.bridge_name,
                auth_url=auth_url
            )

            self._qr_codes[auth_token] = qr_data

            logger.info(f"Generated QR code for {bridge_config.bridge_name}")
            return qr_data

        except Exception as e:
            logger.error(f"Failed to generate WhatsApp QR code: {e}")
            raise BridgeAuthError(f"QR code generation failed: {e}")

    async def _start_oauth_flow(self, bridge_config: BridgeConfig) -> str:
        """Start OAuth flow for Instagram/Facebook."""
        try:
            # This would typically interact with the mautrix-meta bridge
            # For now, we'll create a placeholder OAuth URL

            state = str(uuid.uuid4())
            oauth_url = f"https://www.facebook.com/v18.0/dialog/oauth?client_id=placeholder&redirect_uri=http://localhost:8000/matrix/oauth/callback&state={state}&scope=instagram_basic,pages_messaging"

            logger.info(f"Generated OAuth URL for {bridge_config.bridge_name}")
            return oauth_url

        except Exception as e:
            logger.error(f"Failed to start OAuth flow: {e}")
            raise BridgeAuthError(f"OAuth flow start failed: {e}")

    async def get_auth_session(self, session_id: str) -> Optional[BridgeAuthSession]:
        """Get authentication session by ID."""
        return self._auth_sessions.get(session_id)

    async def get_qr_code(self, bridge_name: str) -> Optional[QRCodeData]:
        """Get QR code data for a bridge."""
        for qr_data in self._qr_codes.values():
            if qr_data.bridge_name == bridge_name:
                if qr_data.expires_at > datetime.now(timezone.utc):
                    return qr_data
                else:
                    # QR code expired, remove it
                    del self._qr_codes[bridge_name]
                    break
        return None

    async def complete_auth(
        self,
        session_id: str,
        auth_data: Dict[str, Any]
    ) -> bool:
        """Complete authentication for a bridge session."""
        try:
            session = self._auth_sessions.get(session_id)
            if not session:
                raise BridgeAuthError(f"Auth session not found: {session_id}")

            if session.auth_method == AuthMethod.QR_CODE:
                # Verify QR code scan
                success = await self._verify_qr_auth(session, auth_data)
            elif session.auth_method == AuthMethod.OAUTH:
                # Process OAuth callback
                success = await self._process_oauth_callback(session, auth_data)
            else:
                raise BridgeAuthError(
                    f"Unsupported auth method: {session.auth_method}")

            if success:
                session.status = "completed"
                logger.info(f"Auth completed for session: {session_id}")
            else:
                session.status = "failed"
                logger.warning(f"Auth failed for session: {session_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to complete auth: {e}")
            raise BridgeAuthError(f"Auth completion failed: {e}")

    async def _verify_qr_auth(
        self,
        session: BridgeAuthSession,
        auth_data: Dict[str, Any]
    ) -> bool:
        """Verify QR code authentication."""
        try:
            # This would typically verify with the WhatsApp bridge
            # For now, we'll simulate successful authentication

            phone_number = auth_data.get('phone_number')
            if phone_number:
                session.metadata['phone_number'] = phone_number
                return True

            return False

        except Exception as e:
            logger.error(f"QR auth verification failed: {e}")
            return False

    async def _process_oauth_callback(
        self,
        session: BridgeAuthSession,
        auth_data: Dict[str, Any]
    ) -> bool:
        """Process OAuth callback."""
        try:
            # This would typically process the OAuth callback
            # For now, we'll simulate successful authentication

            code = auth_data.get('code')
            if code:
                session.metadata['oauth_code'] = code
                return True

            return False

        except Exception as e:
            logger.error(f"OAuth callback processing failed: {e}")
            return False

    async def cleanup_expired_sessions(self) -> None:
        """Clean up expired authentication sessions."""
        try:
            now = datetime.now(timezone.utc)
            expired_sessions = [
                session_id for session_id, session in self._auth_sessions.items()
                if session.expires_at and session.expires_at < now
            ]

            for session_id in expired_sessions:
                del self._auth_sessions[session_id]
                logger.debug(f"Cleaned up expired auth session: {session_id}")

            # Clean up expired QR codes
            expired_qr_codes = [
                token for token, qr_data in self._qr_codes.items()
                if qr_data.expires_at < now
            ]

            for token in expired_qr_codes:
                del self._qr_codes[token]
                logger.debug(f"Cleaned up expired QR code: {token}")

        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")

    async def get_bridge_auth_status(self, bridge_name: str) -> Dict[str, Any]:
        """Get authentication status for a bridge."""
        try:
            # Find active session for bridge
            active_session = None
            for session in self._auth_sessions.values():
                if session.bridge_name == bridge_name:
                    active_session = session
                    break

            if not active_session:
                return {"status": "not_authenticated", "bridge_name": bridge_name}

            status_data = {
                "status": active_session.status,
                "bridge_name": bridge_name,
                "session_id": active_session.session_id,
                "auth_method": active_session.auth_method.value,
                "created_at": active_session.created_at.isoformat(),
            }

            if active_session.expires_at:
                status_data["expires_at"] = active_session.expires_at.isoformat()

            if active_session.qr_data:
                status_data["qr_code"] = active_session.qr_data.qr_code
                status_data["qr_expires_at"] = active_session.qr_data.expires_at.isoformat(
                )

            if active_session.metadata:
                status_data["metadata"] = active_session.metadata

            return status_data

        except Exception as e:
            logger.error(f"Error getting bridge auth status: {e}")
            return {"status": "error", "bridge_name": bridge_name, "error": str(e)}
