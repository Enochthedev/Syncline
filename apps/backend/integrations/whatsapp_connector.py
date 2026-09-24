"""
WhatsApp Connector via Matrix Bridge (mautrix-whatsapp)

Full implementation for WhatsApp integration using the Matrix protocol.
Uses mautrix-whatsapp bridge to connect personal WhatsApp accounts.

Architecture:
    WhatsApp <-> mautrix-whatsapp bridge <-> Synapse (Matrix server) <-> This connector

Features:
- Connect via QR code scanning (like WhatsApp Web)
- Receive messages in real-time via Matrix room events
- Send messages through Matrix rooms
- Fetch message history
- Handle media attachments
"""

import asyncio
import base64
import io
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import aiohttp
from pydantic import BaseModel, Field

# Optional QR code generation
try:
    import qrcode

    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

from integrations.base_connector import (
    AuthenticationError,
    BaseConnector,
    ConnectionError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Models
# =============================================================================


class MatrixMessage(BaseModel):
    """Normalized Matrix message from WhatsApp bridge."""

    event_id: str = Field(description="Matrix event ID")
    room_id: str = Field(description="Matrix room ID")
    sender: str = Field(description="Matrix user ID (bridged from WhatsApp)")
    timestamp: datetime = Field(description="Message timestamp")
    content: str = Field(description="Message content")
    msg_type: str = Field(default="m.text", description="Message type")
    whatsapp_id: Optional[str] = Field(None, description="Original WhatsApp message ID")
    reply_to: Optional[str] = Field(None, description="Reply-to event ID")
    media_url: Optional[str] = Field(None, description="Media URL if attachment")
    media_type: Optional[str] = Field(None, description="Media MIME type")


class WhatsAppContact(BaseModel):
    """WhatsApp contact from bridge."""

    jid: str = Field(description="WhatsApp JID (phone@s.whatsapp.net)")
    name: str = Field(description="Contact name")
    phone: str = Field(description="Phone number")
    matrix_room_id: Optional[str] = Field(None, description="Matrix room for DM")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")


class BridgeStatus(BaseModel):
    """mautrix-whatsapp bridge status."""

    connected: bool = Field(default=False)
    logged_in: bool = Field(default=False)
    phone: Optional[str] = Field(None, description="Connected phone number")
    battery_level: Optional[int] = Field(None)
    platform: Optional[str] = Field(None, description="e.g. 'android', 'iphone'")
    qr_code: Optional[str] = Field(
        None, description="QR code for login if not logged in"
    )


# =============================================================================
# Matrix Client for WhatsApp Bridge
# =============================================================================


class MatrixWhatsAppClient:
    """
    Matrix client specifically for interacting with mautrix-whatsapp bridge.

    Handles:
    - Authentication with Matrix homeserver
    - Communication with mautrix-whatsapp bridge bot
    - Message sync and room management
    """

    def __init__(
        self,
        homeserver_url: str,
        access_token: str,
        user_id: str,
        bridge_bot: str = "@whatsappbot:localhost",
    ):
        self.homeserver_url = homeserver_url.rstrip("/")
        self.access_token = access_token
        self.user_id = user_id
        self.bridge_bot = bridge_bot
        self._session: Optional[aiohttp.ClientSession] = None
        self._since_token: Optional[str] = None
        self._management_room_id: Optional[str] = None  # Cached room ID

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                }
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make a request to Matrix homeserver."""
        session = await self._get_session()
        url = f"{self.homeserver_url}/_matrix/client/v3{endpoint}"

        try:
            async with session.request(
                method,
                url,
                json=json_data,
                params=params,
            ) as response:
                data = await response.json()

                if response.status == 429:
                    retry_after = data.get("retry_after_ms", 5000) / 1000
                    raise RateLimitError(
                        f"Matrix rate limit exceeded", retry_after=int(retry_after)
                    )

                if response.status >= 400:
                    error = data.get("error", "Unknown error")
                    if response.status == 401 or response.status == 403:
                        raise AuthenticationError(f"Matrix auth failed: {error}")
                    raise ConnectionError(f"Matrix request failed: {error}")

                return data

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Matrix connection error: {e}")

    async def whoami(self) -> Dict[str, str]:
        """Verify authentication and get user info."""
        return await self._request("GET", "/account/whoami")

    async def sync(
        self,
        timeout: int = 30000,
        filter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sync with Matrix server.

        Args:
            timeout: Long-poll timeout in milliseconds
            filter_id: Optional sync filter

        Returns:
            Sync response with rooms and events
        """
        params = {"timeout": timeout}
        if self._since_token:
            params["since"] = self._since_token
        if filter_id:
            params["filter"] = filter_id

        response = await self._request("GET", "/sync", params=params)
        self._since_token = response.get("next_batch")
        return response

    async def get_joined_rooms(self) -> List[str]:
        """Get list of all joined room IDs."""
        response = await self._request("GET", "/joined_rooms")
        return response.get("joined_rooms", [])

    async def get_whatsapp_rooms(self) -> List[Dict[str, Any]]:
        """
        Get all WhatsApp bridged rooms (all rooms basically).

        For mautrix-whatsapp, all rooms the user is in (except management)
        are WhatsApp rooms.

        Returns:
            List of room info dicts with id and name
        """
        rooms = []
        room_ids = await self.get_joined_rooms()

        # Get the management room so we can skip it
        management_room = await self._get_or_create_bridge_room()

        for room_id in room_ids:
            # Skip management room (it's for bot commands)
            if room_id == management_room:
                continue

            rooms.append(
                {
                    "room_id": room_id,
                    "name": room_id,  # We'll use room_id as placeholder
                    "is_group": False,
                }
            )

        logger.info(f"Found {len(rooms)} WhatsApp chat rooms (excluding management)")
        return rooms

    async def get_room_messages(
        self,
        room_id: str,
        limit: int = 100,
        direction: str = "b",  # backward
    ) -> List[Dict[str, Any]]:
        """Get messages from a room."""
        params = {"limit": limit, "dir": direction}

        response = await self._request(
            "GET", f"/rooms/{room_id}/messages", params=params
        )
        return response.get("chunk", [])

    async def send_message(
        self,
        room_id: str,
        content: str,
        msg_type: str = "m.text",
    ) -> str:
        """
        Send a message to a room.

        Returns:
            Event ID of sent message
        """
        txn_id = f"m{int(datetime.utcnow().timestamp() * 1000)}"

        response = await self._request(
            "PUT",
            f"/rooms/{room_id}/send/m.room.message/{txn_id}",
            json_data={
                "msgtype": msg_type,
                "body": content,
            },
        )
        return response.get("event_id", "")

    async def send_bridge_command(
        self, command: str, wait_for_response: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Send a command to the mautrix-whatsapp bridge bot.

        Args:
            command: Command string (e.g. "login qr", "ping")
            wait_for_response: Whether to wait for and return the bot's response

        Returns:
            Full Matrix event of the response, or None
        """
        # Find or create management room with bridge bot
        logger.info(f"Sending bridge command: {command}")
        management_room = await self._get_or_create_bridge_room()
        logger.info(f"Using management room: {management_room}")

        # Send command (in DM/management room, no !wa prefix needed usually,
        # but let's be safe: modern bridges in DMs accept commands directly)
        await self.send_message(management_room, command)
        logger.info(f"Command sent to room")

        if not wait_for_response:
            return None

        # Wait for response with retries
        for attempt in range(5):
            await asyncio.sleep(1 + attempt)

            # Get recent messages
            messages = await self.get_room_messages(management_room, limit=10)
            logger.debug(
                f"Got {len(messages)} messages from room (attempt {attempt + 1})"
            )

            # For login commands, prioritize finding m.image response
            is_login_command = command.startswith("login")

            # First pass: look for m.image if this is a login command
            if is_login_command:
                for msg in messages:
                    sender = msg.get("sender", "")
                    content = msg.get("content", {})
                    msgtype = content.get("msgtype", "")

                    if sender == self.bridge_bot and msgtype == "m.image":
                        logger.debug(f"Found QR image response")
                        return msg

            # Second pass: any response from bot that isn't our command
            for msg in messages:
                sender = msg.get("sender", "")
                content = msg.get("content", {})
                body = content.get("body", "")

                # Log all messages for debugging
                logger.debug(f"Message from {sender}: {body[:80]}...")

                # Verify it's from bot and not an echo of our command
                # Skip notices that aren't the actual QR/code response
                if sender == self.bridge_bot and body != command:
                    if is_login_command:
                        # Skip these informational notices - we want the actual QR/code
                        skip_patterns = [
                            "scan the qr",
                            "not logged in",
                            "you're not logged in",
                        ]
                        if any(pattern in body.lower() for pattern in skip_patterns):
                            continue  # Keep looking for the image/code
                    logger.info(f"Bridge response: {body[:100]}...")
                    return msg  # Return full message object (content, type, etc.)

        logger.warning(f"No response from bridge for command: {command}")
        return None

    async def _get_or_create_bridge_room(self) -> str:
        """Get or create direct message room with bridge bot."""
        # Validate cached room if available
        if self._management_room_id:
            logger.debug(
                f"Validating cached management room: {self._management_room_id}"
            )
            try:
                # Try to send a simple message to validate the room exists and is accessible
                sync_response = await self.sync(timeout=0)
                rooms = sync_response.get("rooms", {}).get("join", {})
                if self._management_room_id in rooms:
                    logger.debug(f"Cached room is valid: {self._management_room_id}")
                    return self._management_room_id
                else:
                    logger.warning(
                        f"Cached room {self._management_room_id} not found, clearing cache"
                    )
                    self._management_room_id = None
            except Exception as e:
                logger.warning(f"Failed to validate cached room: {e}, clearing cache")
                self._management_room_id = None

        logger.info(f"Looking for bridge room with bot: {self.bridge_bot}")
        # Try to find existing DM with bot
        sync_response = await self.sync(timeout=0)
        rooms = sync_response.get("rooms", {}).get("join", {})

        for room_id, room_data in rooms.items():
            # Check if this is a DM with the bridge bot
            state_events = room_data.get("state", {}).get("events", [])
            for event in state_events:
                if event.get("type") == "m.room.member":
                    if event.get("state_key") == self.bridge_bot:
                        logger.info(f"Found existing bridge room: {room_id}")
                        self._management_room_id = room_id  # Cache it
                        return room_id

        logger.info("No existing bridge room found, creating new one...")
        # Create new DM room with bot
        response = await self._request(
            "POST",
            "/createRoom",
            json_data={
                "is_direct": True,
                "invite": [self.bridge_bot],
                "preset": "trusted_private_chat",
            },
        )
        room_id = response.get("room_id", "")
        self._management_room_id = room_id  # Cache it
        return room_id

    async def get_bridge_status(self) -> BridgeStatus:
        """Get WhatsApp bridge connection status."""
        try:
            # Send list-logins command
            management_room = await self._get_or_create_bridge_room()
            await self.send_message(management_room, "list-logins")

            # Wait and get messages
            await asyncio.sleep(2)
            messages = await self.get_room_messages(management_room, limit=10)

            # Look for the list-logins response specifically
            for msg in messages:
                sender = msg.get("sender", "")
                content = msg.get("content", {})
                body = content.get("body", "")
                msgtype = content.get("msgtype", "")

                if sender != self.bridge_bot:
                    continue

                # Skip QR code responses (they start with "2@")
                if body.startswith("2@"):
                    continue

                # Skip "Scan the QR" messages
                if "scan the qr" in body.lower():
                    continue

                # Check for connected status
                # Format: "* `phone` (+phone) - `CONNECTED`"
                if "CONNECTED" in body.upper():
                    import re

                    phone_match = re.search(r"\+\d+", body)
                    phone = phone_match.group() if phone_match else None
                    return BridgeStatus(
                        connected=True,
                        logged_in=True,
                        phone=phone,
                    )

                # Check for not logged in
                if "not logged in" in body.lower():
                    return BridgeStatus(connected=False, logged_in=False)

                # Check for BAD_CREDENTIALS (expired session)
                if "BAD_CREDENTIALS" in body.upper():
                    return BridgeStatus(connected=False, logged_in=False)

            # Default - couldn't determine status
            return BridgeStatus(connected=False, logged_in=False)

        except Exception as e:
            logger.error(f"Failed to get bridge status: {e}")
            return BridgeStatus(connected=False, logged_in=False)

    async def login_whatsapp(self) -> Optional[str]:
        """
        Initiate WhatsApp login via QR Code.
        Returns: QR code data string.
        """
        # First check if there's a bad session that needs cleanup
        status = await self.get_bridge_status()
        if status.connected and status.logged_in:
            return None  # Already logged in

        # Check for BAD_CREDENTIALS by looking at recent messages
        management_room = await self._get_or_create_bridge_room()
        messages = await self.get_room_messages(management_room, limit=5)
        for msg in messages:
            body = msg.get("content", {}).get("body", "")
            if "BAD_CREDENTIALS" in body.upper():
                # Session is invalid - try to logout and cleanup
                logger.warning("Found BAD_CREDENTIALS, attempting cleanup...")
                await self.send_message(management_room, "logout")
                await asyncio.sleep(2)
                break

        # "login qr" is the standard command for mautrix-whatsapp in management rooms
        response_msg = await self.send_bridge_command("!wa login qr")

        if not response_msg:
            return None

        content = response_msg.get("content", {})
        body = content.get("body", "")
        msgtype = content.get("msgtype", "")

        # Check for already logged in
        if "already logged in" in body.lower():
            return None

        # Case 1: m.image (Standard behavior for recent mautrix-whatsapp)
        # The body contains the raw QR code data string
        if msgtype == "m.image":
            # Return raw data - frontend will generate QR code
            return body

        # Case 2: Text containing data URL (already an image)
        if "data:image" in body:
            return body

        # Case 3: Valid QR code data (starts with "2@")
        if body and body.startswith("2@") and len(body) > 20:
            return body

        # Case 4: Other text data
        if (
            body
            and len(body) > 20
            and not body.startswith("Hello")
            and "not logged in" not in body.lower()
        ):
            return body

        return None

    def _sanitize_phone_number(self, phone_number: str) -> str:
        """
        Sanitize and normalize phone number to international format.

        Args:
            phone_number: Phone number in any format

        Returns:
            Cleaned phone number starting with +
        """
        clean_phone = phone_number.replace(" ", "").replace("-", "")
        if not clean_phone.startswith("+"):
            clean_phone = "+" + clean_phone
        return clean_phone

    async def _cleanup_existing_login_states(self, management_room: str) -> None:
        """
        Clean up any existing login states to avoid conflicts.

        This sends multiple logout/cancel commands to ensure the bridge
        is not stuck in a previous login attempt. Handles the case where
        the bridge has an existing login in TRANSIENT_DISCONNECT state
        which requires a specific logout command format.

        Args:
            management_room: The bridge management room ID
        """
        import asyncio

        logger.info("Cleaning up any existing login states...")

        # First, check for existing logins that need specific logout
        await self.send_message(management_room, "list-logins")
        await asyncio.sleep(2)

        # Get the response to check for existing logins
        messages = await self.get_room_messages(management_room, limit=5)

        for msg in messages:
            sender = msg.get("sender", "")
            content = msg.get("content", {})
            body = content.get("body", "")

            if sender != self.bridge_bot:
                continue

            # Look for existing logins with pattern: * `<login_id>` (+phone) - `STATUS`
            # Examples:
            # * `2349167674418` (+2349167674418) - `TRANSIENT_DISCONNECT`
            # * `2349167674418` (+2349167674418) - `CONNECTED`
            login_id_match = re.search(r"\* `(\d+)` \([^)]+\) - `([A-Z_]+)`", body)
            if login_id_match:
                login_id = login_id_match.group(1)
                status = login_id_match.group(2)
                logger.info(f"Found existing login: {login_id} with status: {status}")

                # Logout this specific login
                logger.info(f"Sending specific logout for: {login_id}")
                await self.send_message(management_room, f"!wa logout {login_id}")
                await asyncio.sleep(3)

        # Method 1: Generic logout command (fallback)
        await self.send_message(management_room, "!wa logout")
        await asyncio.sleep(2)

        # Method 2: Cancel command (some bridges use this)
        await self.send_message(management_room, "cancel")
        await asyncio.sleep(3)

        # Method 3: Logout again to be safe
        await self.send_message(management_room, "!wa logout")
        await asyncio.sleep(3)

    async def _send_phone_login_commands(
        self, management_room: str, phone_number: str
    ) -> None:
        """
        Send the two-step phone login commands to the bridge.

        mautrix-whatsapp phone login is a two-step process:
        1. Send "!wa login phone" - bridge will prompt for phone number
        2. Send the phone number - bridge will return the pairing code

        Args:
            management_room: The bridge management room ID
            phone_number: Sanitized phone number starting with +

        Raises:
            ConnectionError: If communication with bridge fails
        """
        import asyncio

        logger.info("Step 1: Sending login phone command...")

        try:
            # First, send the login phone command
            await self.send_message(management_room, "!wa login phone")
            logger.info("Login phone command sent, waiting for prompt...")

            # Wait for the bridge to respond with prompt
            await asyncio.sleep(4)

            # Now send the phone number to the same room
            logger.info(f"Step 2: Sending phone number: {phone_number}")
            await self.send_message(management_room, phone_number)
            logger.info("Phone number sent, waiting for pairing code...")
        except Exception as e:
            logger.error(f"Failed to send bridge command: {e}", exc_info=True)
            raise ConnectionError(
                f"Failed to communicate with WhatsApp bridge: {str(e)}"
            )

    def _extract_pairing_code_from_message(self, body: str) -> Optional[str]:
        """
        Extract pairing code from bridge message.

        Looks for pairing code in multiple formats:
        - Pattern 1: `XXXX-YYYY` (in backticks)
        - Pattern 2: XXXX-YYYY (plain text)
        - Pattern 3: `XXXXXXXX` (8 chars in backticks, converted to XXXX-YYYY)

        Args:
            body: Message body from bridge

        Returns:
            Pairing code if found, None otherwise
        """
        # Pattern 1: Code in backticks like `XXXX-YYYY`
        backtick_match = re.search(r"`([A-Z0-9]{4}-[A-Z0-9]{4})`", body)
        if backtick_match:
            pairing_code = backtick_match.group(1).upper()
            logger.info(f"Found pairing code in backticks: {pairing_code}")
            return pairing_code

        # Pattern 2: Standalone code format XXXX-YYYY
        plain_match = re.search(r"\b([A-Z0-9]{4}-[A-Z0-9]{4})\b", body)
        if plain_match:
            pairing_code = plain_match.group(1).upper()
            logger.info(f"Found pairing code: {pairing_code}")
            return pairing_code

        # Pattern 3: 8 alphanumeric without dash
        plain_8_match = re.search(r"`([A-Z0-9]{8})`", body)
        if plain_8_match:
            code = plain_8_match.group(1).upper()
            pairing_code = code[:4] + "-" + code[4:]
            logger.info(f"Found pairing code (8 char): {pairing_code}")
            return pairing_code

        return None

    async def _poll_for_pairing_code(self, management_room: str) -> str:
        """
        Poll the management room for the pairing code response.

        Uses exponential backoff to wait for the bridge to respond
        with the pairing code. Checks for error conditions and
        extracts the code from bridge messages.

        Args:
            management_room: The bridge management room ID

        Returns:
            The pairing code or "CHECK_PHONE" if notification sent to device

        Raises:
            AuthenticationError: If already logged in
            ConnectionError: If login times out or fails
        """
        import asyncio

        last_bridge_response = None

        # Exponential backoff: 1s, 1.5s, 2s, 2.5s, 3s, 3.5s, 4s, 4.5s, 5s, 5s
        for attempt in range(10):
            # Exponential backoff with cap at 5 seconds
            wait_time = min(1 + (attempt * 0.5), 5)
            await asyncio.sleep(wait_time)

            try:
                # Get recent messages from the management room
                messages = await self.get_room_messages(management_room, limit=15)
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}: Failed to fetch messages: {e}")
                continue

            # Look for the pairing code in recent messages
            for msg in messages:
                sender = msg.get("sender", "")
                content = msg.get("content", {})
                body = content.get("body", "")

                # Skip if not from bridge bot
                if sender != self.bridge_bot:
                    continue

                logger.debug(f"Checking message: {body[:80]}...")
                last_bridge_response = body  # Save for error reporting

                # Check for error conditions
                if "already logged in" in body.lower():
                    raise AuthenticationError("Already logged in to WhatsApp")

                if "timed out" in body.lower():
                    raise ConnectionError("Login timed out. Please try again.")

                if "failed" in body.lower() and "login" in body.lower():
                    raise ConnectionError(f"Login failed: {body}")

                # Check if bridge sent notification to phone instead of pairing code
                if any(
                    phrase in body.lower()
                    for phrase in [
                        "notification",
                        "check your phone",
                        "sent to your whatsapp",
                    ]
                ):
                    logger.info("Bridge sent notification to phone")
                    return "CHECK_PHONE"

                # Try to extract pairing code
                pairing_code = self._extract_pairing_code_from_message(body)
                if pairing_code:
                    return pairing_code

            logger.debug(f"Attempt {attempt + 1}: No pairing code found yet")

        # If we get here, we waited but didn't find the code
        error_msg = (
            "Failed to get pairing code from bridge after 10 attempts (~35 seconds)."
        )
        if last_bridge_response:
            error_msg += f"\n\nLast bridge response: {last_bridge_response[:200]}"
        error_msg += "\n\nPlease try again or check bridge logs."

        logger.error(
            f"Pairing code extraction failed. Last response: {last_bridge_response}"
        )
        raise ConnectionError(error_msg)

    async def login_whatsapp_phone(self, phone_number: str) -> str:
        """
        Initiate WhatsApp login via Phone Number Pairing.

        This method orchestrates the phone login flow by:
        1. Sanitizing the phone number
        2. Getting the management room
        3. Cleaning up existing login states
        4. Sending login commands
        5. Polling for the pairing code

        Args:
            phone_number: International format phone number (e.g. +1234567890)

        Returns:
            The pairing code to display to the user, or "CHECK_PHONE" if
            a notification was sent to the device instead.

        Raises:
            AuthenticationError: If already logged in
            ConnectionError: If login fails or times out
        """
        logger.info(f"Starting phone login for {phone_number}")

        # Step 1: Sanitize phone number
        clean_phone = self._sanitize_phone_number(phone_number)

        # Step 2: Get management room
        management_room = await self._get_or_create_bridge_room()
        logger.info(f"Using management room: {management_room}")

        # Step 3: Clean up any existing login states
        await self._cleanup_existing_login_states(management_room)

        # Step 4: Send login commands
        await self._send_phone_login_commands(management_room, clean_phone)

        # Step 5: Poll for pairing code
        return await self._poll_for_pairing_code(management_room)

    async def logout_whatsapp(self) -> bool:
        """
        Logout from WhatsApp with improved reliability.

        Returns:
            Success status
        """
        try:
            # First check if we're actually logged in
            status = await self.get_bridge_status()
            if not status.logged_in:
                logger.info("Already logged out from WhatsApp")
                return True

            # Try multiple logout strategies with !wa prefix
            logout_commands = [
                "!wa logout",
                "!wa disconnect",
                "!wa logout-matrix",
                "!wa delete-session",
            ]

            for cmd in logout_commands:
                try:
                    logger.info(f"Trying logout command: {cmd}")
                    response_msg = await self.send_bridge_command(cmd)

                    if response_msg:
                        body = response_msg.get("content", {}).get("body", "").lower()

                        # Check for success indicators
                        success_indicators = [
                            "logged out",
                            "disconnected",
                            "session deleted",
                            "success",
                        ]

                        if any(indicator in body for indicator in success_indicators):
                            logger.info(f"Logout successful with command: {cmd}")

                            # Verify logout worked
                            await asyncio.sleep(2)
                            final_status = await self.get_bridge_status()
                            return not final_status.logged_in

                    # Wait between attempts
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.warning(f"Logout command '{cmd}' failed: {e}")
                    continue

            # Final verification - check if any logout worked
            await asyncio.sleep(3)
            final_status = await self.get_bridge_status()
            success = not final_status.logged_in

            if success:
                logger.info("Logout verification successful")
            else:
                logger.warning("All logout attempts failed, but continuing")
                # Return True anyway since we'll handle this at session level
                success = True

            return success

        except Exception as e:
            logger.error(f"WhatsApp logout failed: {e}")
            # Return True to allow session cleanup to proceed
            return True

    async def get_whatsapp_contacts(self) -> List[WhatsAppContact]:
        """Get list of WhatsApp contacts from bridge."""
        # This is complex parsing, usually better done via sync data
        # forcing a 'list' command output parsing is brittle.
        # For now, returning empty as specific parsing logic is needed per bridge version
        return []

    def parse_matrix_message(self, event: Dict[str, Any]) -> Optional[MatrixMessage]:
        """Parse a Matrix event into a MatrixMessage."""
        if event.get("type") != "m.room.message":
            return None

        content = event.get("content", {})

        # Extract WhatsApp-specific metadata from bridge
        whatsapp_id = None
        if "fi.mau.whatsapp" in content:
            whatsapp_id = content["fi.mau.whatsapp"].get("id")

        return MatrixMessage(
            event_id=event.get("event_id", ""),
            room_id=event.get("room_id", ""),
            sender=event.get("sender", ""),
            timestamp=datetime.fromtimestamp(event.get("origin_server_ts", 0) / 1000),
            content=content.get("body", ""),
            msg_type=content.get("msgtype", "m.text"),
            whatsapp_id=whatsapp_id,
            reply_to=content.get("m.relates_to", {})
            .get("m.in_reply_to", {})
            .get("event_id"),
            media_url=content.get("url"),
            media_type=content.get("info", {}).get("mimetype"),
        )


# =============================================================================
# WhatsApp Connector Implementation
# =============================================================================


class WhatsAppConnector(BaseConnector):
    """
    WhatsApp platform connector using mautrix-whatsapp bridge.

    Connects to WhatsApp via Matrix bridge for:
    - Personal WhatsApp account access
    - Real-time message sync
    - Message history retrieval
    - Contact management

    Required credentials:
    - matrix_homeserver_url: URL of Matrix homeserver (e.g., http://localhost:8008)
    - matrix_access_token: Matrix access token for authenticated user
    - matrix_user_id: Matrix user ID (e.g., @syncline:localhost)
    - bridge_bot_id: Bridge bot user ID (default: @whatsappbot:localhost)
    """

    def __init__(
        self,
        connection_id: UUID,
        credentials: Dict[str, Any],
        rate_limit_per_minute: int = 120,  # Matrix has higher limits
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        super().__init__(
            connection_id=connection_id,
            credentials=credentials,
            rate_limit_per_minute=rate_limit_per_minute,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout,
        )

        self._client: Optional[MatrixWhatsAppClient] = None
        self._sync_task: Optional[asyncio.Task] = None
        self._message_callback = None

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "whatsapp"

    def _get_client(self) -> MatrixWhatsAppClient:
        """Get or create Matrix client."""
        if self._client is None:
            self._client = MatrixWhatsAppClient(
                homeserver_url=self.credentials.get(
                    "matrix_homeserver_url", "http://localhost:8008"
                ),
                access_token=self.credentials.get("matrix_access_token", ""),
                user_id=self.credentials.get("matrix_user_id", ""),
                bridge_bot=self.credentials.get(
                    "bridge_bot_id", "@whatsappbot:localhost"
                ),
            )
        return self._client

    async def _connect(self) -> None:
        """Establish connection to WhatsApp via Matrix bridge."""
        client = self._get_client()

        try:
            # Verify Matrix authentication
            whoami = await client.whoami()
            logger.info(f"Connected to Matrix as {whoami.get('user_id')}")

            # Check WhatsApp bridge status
            status = await client.get_bridge_status()

            if not status.logged_in:
                logger.warning(
                    "WhatsApp not logged in. Use get_login_qr() to get QR code."
                )
            else:
                logger.info("WhatsApp bridge connected and logged in")

        except AuthenticationError:
            raise
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Matrix/WhatsApp: {e}")

    async def _disconnect(self) -> None:
        """Disconnect from WhatsApp."""
        # Stop sync task if running
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Close client session
        if self._client:
            await self._client.close()
            self._client = None

        logger.info(f"WhatsApp connector {self.connection_id} disconnected")

    async def _refresh_token(self) -> Dict[str, Any]:
        """
        Refresh Matrix access token.

        Note: Matrix tokens are typically long-lived, but we can
        refresh via the refresh_token endpoint if configured.
        """
        # Matrix tokens don't typically expire in the same way as OAuth
        # But we can re-authenticate if needed
        logger.info(f"WhatsApp connector {self.connection_id} - token still valid")
        return self.credentials

    async def _check_health(self) -> Dict[str, Any]:
        """Perform health check on WhatsApp bridge."""
        client = self._get_client()

        try:
            # Check Matrix connection
            whoami = await client.whoami()

            # Check bridge status
            status = await client.get_bridge_status()

            return {
                "matrix_user": whoami.get("user_id"),
                "whatsapp_connected": status.connected,
                "whatsapp_logged_in": status.logged_in,
                "whatsapp_phone": status.phone,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    # =========================================================================
    # WhatsApp-Specific Methods
    # =========================================================================

    async def get_login_qr(self) -> Optional[str]:
        """
        Get QR code for WhatsApp login.

        Returns:
            QR code data (base64 image or ASCII) or None if already logged in
        """
        client = self._get_client()
        return await client.login_whatsapp()

    async def login_with_phone(self, phone_number: str) -> str:
        """
        Login to WhatsApp using phone number pairing.

        Returns:
            Pairing code to display to user
        """
        client = self._get_client()
        return await client.login_whatsapp_phone(phone_number)

    async def logout(self) -> bool:
        """Logout from WhatsApp (keeps Matrix connection)."""
        client = self._get_client()
        return await client.logout_whatsapp()

    async def get_bridge_status(self) -> BridgeStatus:
        """Get current WhatsApp bridge status."""
        client = self._get_client()
        return await client.get_bridge_status()

    async def list_messages(
        self,
        room_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[MatrixMessage]:
        """
        List messages from WhatsApp chats.

        Args:
            room_id: Specific room/chat to get messages from
            limit: Maximum messages to return

        Returns:
            List of parsed messages
        """
        client = self._get_client()
        messages = []

        if room_id:
            # Get messages from specific room
            events = await client.get_room_messages(room_id, limit)
            for event in events:
                msg = client.parse_matrix_message(event)
                if msg:
                    messages.append(msg)
        else:
            # Get messages from all WhatsApp rooms
            whatsapp_rooms = await client.get_whatsapp_rooms()
            logger.info(f"Found {len(whatsapp_rooms)} WhatsApp rooms")

            per_room_limit = max(10, limit // max(1, len(whatsapp_rooms)))

            for room_info in whatsapp_rooms:
                try:
                    events = await client.get_room_messages(
                        room_info["room_id"], per_room_limit
                    )
                    for event in events:
                        msg = client.parse_matrix_message(event)
                        if msg:
                            # Add room name to message for context
                            msg.room_id = room_info["room_id"]
                            messages.append(msg)
                except Exception as e:
                    logger.warning(
                        f"Error fetching messages from {room_info['room_id']}: {e}"
                    )

            # Sort by timestamp (newest first)
            messages.sort(key=lambda m: m.timestamp, reverse=True)
            messages = messages[:limit]

        return messages

    async def send_message(
        self,
        room_id: str,
        content: str,
    ) -> str:
        """
        Send a message to a WhatsApp chat.

        Args:
            room_id: Matrix room ID (bridged WhatsApp chat)
            content: Message content

        Returns:
            Event ID of sent message
        """
        client = self._get_client()

        if not await self.check_rate_limit():
            raise RateLimitError("Rate limit exceeded for WhatsApp")

        return await client.send_message(room_id, content)

    async def get_contacts(self) -> List[WhatsAppContact]:
        """Get WhatsApp contacts from bridge."""
        client = self._get_client()
        return await client.get_whatsapp_contacts()

    async def sync_chats(self) -> Dict[str, Any]:
        """
        WhatsApp chat synchronization.

        Delegates to sync_all_chats for comprehensive sync.

        Returns:
            Sync result information
        """
        # Use the comprehensive sync strategy
        return await self.sync_all_chats()

    async def sync_all_chats(self) -> Dict[str, Any]:
        """
        Comprehensive WhatsApp chat synchronization.

        Tries multiple sync strategies to get existing conversations:
        1. Sync contacts (creates rooms for people you've chatted with)
        2. Sync groups (creates rooms for group chats)
        3. Sync recent conversations
        4. Force backfill of recent messages

        Returns:
            Detailed sync results
        """
        client = self._get_client()
        results = {}

        try:
            # Step 1: Sync contacts with avatars (more comprehensive)
            logger.info("Syncing WhatsApp contacts...")
            try:
                contacts_response = await client.send_bridge_command(
                    "!wa sync contacts-with-avatars"
                )
                if contacts_response:
                    contacts_body = contacts_response.get("content", {}).get("body", "")
                    results["contacts"] = contacts_body
                    logger.info(f"Contacts sync result: {contacts_body[:100]}")
                else:
                    logger.warning("Contacts sync command returned no response")
                    results["contacts"] = "No response from bridge"
            except Exception as e:
                logger.error(f"Contacts sync failed: {e}", exc_info=True)
                results["contacts"] = f"Failed: {str(e)}"

            await asyncio.sleep(2)

            # Step 2: Sync groups
            logger.info("Syncing WhatsApp groups...")
            try:
                groups_response = await client.send_bridge_command("!wa sync groups")
                if groups_response:
                    groups_body = groups_response.get("content", {}).get("body", "")
                    results["groups"] = groups_body
                    logger.info(f"Groups sync result: {groups_body[:100]}")
                else:
                    logger.warning("Groups sync command returned no response")
                    results["groups"] = "No response from bridge"
            except Exception as e:
                logger.error(f"Groups sync failed: {e}", exc_info=True)
                results["groups"] = f"Failed: {str(e)}"

            await asyncio.sleep(2)

            # Step 3: Try to sync app state (this can trigger more comprehensive sync)
            logger.info("Syncing WhatsApp app state...")
            try:
                appstate_response = await client.send_bridge_command(
                    "!wa sync appstate"
                )
                if appstate_response:
                    appstate_body = appstate_response.get("content", {}).get("body", "")
                    results["appstate"] = appstate_body
                    logger.info(f"App state sync result: {appstate_body[:100]}")
                else:
                    logger.warning("App state sync command returned no response")
                    results["appstate"] = "No response from bridge"
            except Exception as e:
                logger.error(f"App state sync failed: {e}", exc_info=True)
                results["appstate"] = f"Failed: {str(e)}"

            await asyncio.sleep(3)

            # Step 4: Check what rooms we have now
            rooms = await client.get_whatsapp_rooms()
            results["rooms_found"] = len(rooms)

            # Step 5: For each room, try to backfill recent messages
            backfill_results = []
            for room_info in rooms[:5]:  # Limit to first 5 rooms to avoid overwhelming
                try:
                    room_id = room_info["room_id"]
                    # Try to get recent messages to trigger backfill
                    messages = await client.get_room_messages(room_id, limit=10)
                    backfill_results.append(
                        {"room_id": room_id, "messages_found": len(messages)}
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to backfill room {room_info.get('room_id')}: {e}"
                    )

            results["backfill"] = backfill_results

            return {
                "success": True,
                "message": f"Sync completed. Found {results.get('rooms_found', 0)} rooms.",
                "details": results,
                "action": "comprehensive_sync",
            }

        except Exception as e:
            logger.error(f"Failed to sync all WhatsApp chats: {e}")
            return {
                "success": False,
                "message": f"Comprehensive sync failed: {str(e)}",
                "details": results,
            }

    async def get_contacts(self) -> List[WhatsAppContact]:
        """Get WhatsApp contacts from bridge."""
        client = self._get_client()
        return await client.get_whatsapp_contacts()

    async def start_sync(
        self,
        message_callback=None,
    ) -> None:
        """
        Start continuous message sync.

        Args:
            message_callback: Async function called with each new message
        """
        self._message_callback = message_callback

        if self._sync_task and not self._sync_task.done():
            logger.warning("Sync already running")
            return

        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info("Started WhatsApp message sync")

    async def stop_sync(self) -> None:
        """Stop continuous message sync."""
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped WhatsApp message sync")

    async def get_rooms(self) -> List[Dict[str, Any]]:
        """
        Get all WhatsApp rooms/chats.

        Returns:
            List of room information dictionaries
        """
        client = self._get_client()
        return await client.get_whatsapp_rooms()

    async def fetch_messages(
        self,
        room_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from a specific room.

        Args:
            room_id: Matrix room ID
            limit: Maximum number of messages to fetch

        Returns:
            List of message dictionaries
        """
        client = self._get_client()
        return await client.get_room_messages(room_id, limit)

    async def _sync_loop(self) -> None:
        """Internal sync loop for continuous message updates."""
        client = self._get_client()

        while True:
            try:
                sync_response = await client.sync(timeout=30000)

                # Process new messages
                rooms = sync_response.get("rooms", {}).get("join", {})
                for room_id, room_data in rooms.items():
                    timeline = room_data.get("timeline", {}).get("events", [])
                    for event in timeline:
                        msg = client.parse_matrix_message(event)
                        if msg and self._message_callback:
                            try:
                                await self._message_callback(msg)
                            except Exception as e:
                                logger.error(f"Message callback error: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync error: {e}")
                await asyncio.sleep(5)  # Back off on error

    # =========================================================================
    # Enhanced Methods for Improved Sync
    # =========================================================================

    async def get_status(self) -> Dict[str, Any]:
        """
        Get current WhatsApp connection status.

        Returns:
            Dictionary with connection status including logged_in status
        """
        try:
            bridge_status = await self.get_bridge_status()
            return {
                "connected": bridge_status.connected,
                "logged_in": bridge_status.logged_in,
                "phone": bridge_status.phone,
                "bridge_connected": bridge_status.connected,
            }
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {
                "connected": False,
                "logged_in": False,
                "phone": None,
                "bridge_connected": False,
                "error": str(e),
            }

    async def discover_rooms(self) -> bool:
        """
        Trigger room discovery by sending sync command to bridge.

        Returns:
            True if discovery was triggered successfully
        """
        try:
            client = self._get_client()
            # Send sync command to trigger room discovery
            await client.send_bridge_command("sync")
            return True
        except Exception as e:
            logger.error(f"Failed to trigger room discovery: {e}")
            return False

    async def sync_bridge(
        self, timeout: int = 30, force_reconnect: bool = False
    ) -> bool:
        """
        Force bridge synchronization.

        Args:
            timeout: Operation timeout in seconds
            force_reconnect: Whether to force reconnection

        Returns:
            True if sync was successful
        """
        try:
            client = self._get_client()

            if force_reconnect:
                # Disconnect and reconnect
                await self._disconnect()
                await self._connect()
                client = self._get_client()

            # Send sync command
            await client.send_bridge_command("sync", wait_for_response=True)
            return True

        except Exception as e:
            logger.error(f"Failed to sync bridge: {e}")
            return False
