"""
Enhanced WhatsApp Connector with Improved Reliability

Improvements over base connector:
- Longer timeouts for bridge responses (15 attempts instead of 5)
- Better error handling and recovery
- More robust room discovery
- Enhanced logging for diagnostics
- Automatic retry on common failures
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from integrations.whatsapp_connector import (
    WhatsAppConnector,
    MatrixWhatsAppClient,
    BridgeStatus,
    ConnectionError,
)

logger = logging.getLogger(__name__)


class EnhancedMatrixWhatsAppClient(MatrixWhatsAppClient):
    """
    Enhanced Matrix client with improved reliability for bridge communication.

    Key improvements:
    - Longer timeouts (15 attempts vs 5)
    - Better response parsing
    - More detailed logging
    - Automatic retry on transient failures
    """

    async def send_bridge_command(
        self,
        command: str,
        wait_for_response: bool = True,
        max_attempts: int = 15,  # Increased from 5
        initial_delay: float = 1.0,
        max_delay: float = 3.0
    ) -> Optional[Dict[str, Any]]:
        """
        Send a command to the mautrix-whatsapp bridge bot with enhanced retry logic.

        Args:
            command: Command string (e.g. "login qr", "ping")
            wait_for_response: Whether to wait for and return the bot's response
            max_attempts: Maximum number of attempts to get response
            initial_delay: Initial delay between attempts in seconds
            max_delay: Maximum delay between attempts in seconds

        Returns:
            Full Matrix event of the response, or None
        """
        # Find or create management room with bridge bot
        logger.info(f"[BRIDGE] Sending command: {command}")
        management_room = await self._get_or_create_bridge_room()
        logger.info(f"[BRIDGE] Using management room: {management_room}")

        # Send command
        try:
            await self.send_message(management_room, command)
            logger.info(f"[BRIDGE] Command sent successfully")
        except Exception as e:
            logger.error(f"[BRIDGE] Failed to send command: {e}", exc_info=True)
            raise

        if not wait_for_response:
            return None

        # Wait for response with improved retry logic
        is_login_command = "login" in command.lower()

        for attempt in range(max_attempts):
            # Progressive delay: start at initial_delay, increase up to max_delay
            delay = min(initial_delay + (attempt * 0.5), max_delay)
            await asyncio.sleep(delay)

            try:
                # Get recent messages
                messages = await self.get_room_messages(management_room, limit=15)
                logger.debug(
                    f"[BRIDGE] Attempt {attempt + 1}/{max_attempts}: "
                    f"Got {len(messages)} messages from room"
                )

                # For login commands, prioritize finding m.image response (QR code)
                if is_login_command:
                    for msg in messages:
                        sender = msg.get("sender", "")
                        content = msg.get("content", {})
                        msgtype = content.get("msgtype", "")

                        if sender == self.bridge_bot and msgtype == "m.image":
                            logger.info(f"[BRIDGE] Found QR image response")
                            return msg

                # Look for any response from bot that isn't our command
                for msg in messages:
                    sender = msg.get("sender", "")
                    content = msg.get("content", {})
                    body = content.get("body", "")

                    # Skip if not from bridge bot
                    if sender != self.bridge_bot:
                        continue

                    # Skip if it's our command echoed back
                    if body == command:
                        continue

                    # Log all bot messages for debugging
                    logger.debug(f"[BRIDGE] Bot message: {body[:100]}...")

                    # For login commands, skip informational notices
                    if is_login_command:
                        skip_patterns = [
                            "scan the qr",
                            "not logged in",
                            "you're not logged in",
                            "use the login command"
                        ]
                        if any(pattern in body.lower() for pattern in skip_patterns):
                            logger.debug(f"[BRIDGE] Skipping informational notice")
                            continue

                    # Found a real response
                    logger.info(f"[BRIDGE] Got response: {body[:100]}...")
                    return msg

            except Exception as e:
                logger.warning(f"[BRIDGE] Error fetching messages on attempt {attempt + 1}: {e}")
                continue

        logger.warning(
            f"[BRIDGE] No response from bridge after {max_attempts} attempts (~{max_attempts * 2}s)"
        )
        return None

    async def get_whatsapp_rooms(self) -> List[Dict[str, Any]]:
        """
        Get all WhatsApp bridged rooms with enhanced discovery.

        Improvements:
        - Better error handling
        - Room metadata extraction
        - More detailed logging

        Returns:
            List of room info dicts with id, name, and metadata
        """
        rooms = []
        room_ids = await self.get_joined_rooms()

        logger.info(f"[ROOMS] Found {len(room_ids)} total joined rooms")

        # Get the management room so we can skip it
        management_room = await self._get_or_create_bridge_room()

        for room_id in room_ids:
            # Skip management room (it's for bot commands)
            if room_id == management_room:
                logger.debug(f"[ROOMS] Skipping management room: {room_id}")
                continue

            try:
                # Try to get room name and metadata
                room_info = await self._get_room_info(room_id)
                rooms.append(room_info)
                logger.debug(f"[ROOMS] Added room: {room_id} - {room_info.get('name', 'Unknown')}")

            except Exception as e:
                logger.warning(f"[ROOMS] Failed to get info for room {room_id}: {e}")
                # Still add the room with minimal info
                rooms.append({
                    "room_id": room_id,
                    "name": room_id,
                    "is_group": False
                })

        logger.info(f"[ROOMS] Found {len(rooms)} WhatsApp chat rooms (excluding management)")
        return rooms

    async def _get_room_info(self, room_id: str) -> Dict[str, Any]:
        """
        Get detailed room information.

        Args:
            room_id: Matrix room ID

        Returns:
            Room information dictionary
        """
        try:
            # Get room state to extract name
            response = await self._request("GET", f"/rooms/{room_id}/state")

            room_name = room_id  # Default to room_id
            is_group = False
            topic = None

            # Parse room state events
            for event in response:
                event_type = event.get("type", "")

                if event_type == "m.room.name":
                    room_name = event.get("content", {}).get("name", room_id)

                elif event_type == "m.room.topic":
                    topic = event.get("content", {}).get("topic")

                elif event_type == "m.room.join_rules":
                    # Groups typically have different join rules
                    join_rule = event.get("content", {}).get("join_rule", "")
                    is_group = join_rule != "invite"

            return {
                "room_id": room_id,
                "name": room_name,
                "is_group": is_group,
                "topic": topic
            }

        except Exception as e:
            logger.debug(f"Failed to get detailed room info for {room_id}: {e}")
            return {
                "room_id": room_id,
                "name": room_id,
                "is_group": False
            }

    async def get_bridge_status(self) -> BridgeStatus:
        """
        Get WhatsApp bridge connection status with better error handling.

        Returns:
            BridgeStatus object
        """
        try:
            # Send list-logins command
            management_room = await self._get_or_create_bridge_room()
            await self.send_message(management_room, "list-logins")

            # Wait longer for bridge to respond
            await asyncio.sleep(3)
            messages = await self.get_room_messages(management_room, limit=15)

            logger.debug(f"[STATUS] Checking {len(messages)} messages for status")

            # Look for the list-logins response
            for msg in messages:
                sender = msg.get("sender", "")
                content = msg.get("content", {})
                body = content.get("body", "")

                if sender != self.bridge_bot:
                    continue

                # Skip QR code responses
                if body.startswith("2@"):
                    continue

                # Skip informational messages
                if "scan the qr" in body.lower():
                    continue

                logger.debug(f"[STATUS] Checking message: {body[:100]}...")

                # Check for connected status
                if "CONNECTED" in body.upper():
                    import re
                    phone_match = re.search(r'\+\d+', body)
                    phone = phone_match.group() if phone_match else None
                    logger.info(f"[STATUS] Connected with phone: {phone}")
                    return BridgeStatus(
                        connected=True,
                        logged_in=True,
                        phone=phone,
                    )

                # Check for not logged in
                if "not logged in" in body.lower():
                    logger.info(f"[STATUS] Not logged in")
                    return BridgeStatus(connected=False, logged_in=False)

                # Check for BAD_CREDENTIALS (expired session)
                if "BAD_CREDENTIALS" in body.upper():
                    logger.warning(f"[STATUS] Bad credentials - session expired")
                    return BridgeStatus(connected=False, logged_in=False)

            # Default - couldn't determine status
            logger.warning(f"[STATUS] Could not determine status from bridge responses")
            return BridgeStatus(connected=False, logged_in=False)

        except Exception as e:
            logger.error(f"[STATUS] Failed to get bridge status: {e}", exc_info=True)
            return BridgeStatus(connected=False, logged_in=False)


class EnhancedWhatsAppConnector(WhatsAppConnector):
    """
    Enhanced WhatsApp connector with improved reliability.

    Uses EnhancedMatrixWhatsAppClient for better bridge communication.
    """

    def _get_client(self) -> EnhancedMatrixWhatsAppClient:
        """Get or create enhanced Matrix client."""
        if self._client is None:
            self._client = EnhancedMatrixWhatsAppClient(
                homeserver_url=self.credentials.get(
                    "matrix_homeserver_url",
                    "http://localhost:8008"
                ),
                access_token=self.credentials.get("matrix_access_token", ""),
                user_id=self.credentials.get("matrix_user_id", ""),
                bridge_bot=self.credentials.get(
                    "bridge_bot_id",
                    "@whatsappbot:localhost"
                ),
            )
        return self._client

    async def sync_all_chats(self) -> Dict[str, Any]:
        """
        Comprehensive WhatsApp chat synchronization with enhanced error handling.

        Improvements:
        - Longer waits between sync commands
        - Better error recovery
        - More detailed results

        Returns:
            Detailed sync results
        """
        client = self._get_client()
        results = {}

        try:
            # Step 1: Sync contacts with avatars
            logger.info("[SYNC] Syncing WhatsApp contacts...")
            try:
                contacts_response = await client.send_bridge_command(
                    "!wa sync contacts-with-avatars",
                    max_attempts=10
                )
                if contacts_response:
                    contacts_body = contacts_response.get("content", {}).get("body", "")
                    results["contacts"] = contacts_body[:200]  # Truncate for logging
                    logger.info(f"[SYNC] Contacts sync result: {contacts_body[:100]}")
                else:
                    logger.warning("[SYNC] Contacts sync command returned no response")
                    results["contacts"] = "No response from bridge"
            except Exception as e:
                logger.error(f"[SYNC] Contacts sync failed: {e}", exc_info=True)
                results["contacts"] = f"Failed: {str(e)}"

            # Wait longer between commands to let bridge process
            await asyncio.sleep(3)

            # Step 2: Sync groups
            logger.info("[SYNC] Syncing WhatsApp groups...")
            try:
                groups_response = await client.send_bridge_command(
                    "!wa sync groups",
                    max_attempts=10
                )
                if groups_response:
                    groups_body = groups_response.get("content", {}).get("body", "")
                    results["groups"] = groups_body[:200]
                    logger.info(f"[SYNC] Groups sync result: {groups_body[:100]}")
                else:
                    logger.warning("[SYNC] Groups sync command returned no response")
                    results["groups"] = "No response from bridge"
            except Exception as e:
                logger.error(f"[SYNC] Groups sync failed: {e}", exc_info=True)
                results["groups"] = f"Failed: {str(e)}"

            await asyncio.sleep(3)

            # Step 3: Sync app state
            logger.info("[SYNC] Syncing WhatsApp app state...")
            try:
                appstate_response = await client.send_bridge_command(
                    "!wa sync appstate",
                    max_attempts=10
                )
                if appstate_response:
                    appstate_body = appstate_response.get("content", {}).get("body", "")
                    results["appstate"] = appstate_body[:200]
                    logger.info(f"[SYNC] App state sync result: {appstate_body[:100]}")
                else:
                    logger.warning("[SYNC] App state sync command returned no response")
                    results["appstate"] = "No response from bridge"
            except Exception as e:
                logger.error(f"[SYNC] App state sync failed: {e}", exc_info=True)
                results["appstate"] = f"Failed: {str(e)}"

            # Wait longer for bridge to process and create rooms
            logger.info("[SYNC] Waiting for bridge to create rooms...")
            await asyncio.sleep(5)

            # Step 4: Check what rooms we have now
            rooms = await client.get_whatsapp_rooms()
            results["rooms_found"] = len(rooms)
            logger.info(f"[SYNC] Found {len(rooms)} rooms after sync")

            # Step 5: For each room, try to backfill recent messages
            backfill_results = []
            for room_info in rooms[:10]:  # Limit to first 10 rooms
                try:
                    room_id = room_info["room_id"]
                    logger.debug(f"[SYNC] Backfilling room {room_id}...")

                    # Get recent messages to trigger backfill
                    messages = await client.get_room_messages(room_id, limit=10)
                    backfill_results.append({
                        "room_id": room_id,
                        "room_name": room_info.get("name", "Unknown"),
                        "messages_found": len(messages)
                    })
                    logger.debug(f"[SYNC] Room {room_id} has {len(messages)} recent messages")

                except Exception as e:
                    logger.warning(f"[SYNC] Failed to backfill room {room_info.get('room_id')}: {e}")
                    backfill_results.append({
                        "room_id": room_info.get("room_id"),
                        "error": str(e)
                    })

            results["backfill"] = backfill_results

            return {
                "success": True,
                "message": f"Sync completed. Found {results.get('rooms_found', 0)} rooms.",
                "details": results,
                "action": "comprehensive_sync"
            }

        except Exception as e:
            logger.error(f"[SYNC] Failed to sync all WhatsApp chats: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Comprehensive sync failed: {str(e)}",
                "details": results
            }
