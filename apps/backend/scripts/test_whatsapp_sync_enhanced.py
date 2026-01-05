"""
WhatsApp Sync Diagnostic and Testing Tool

Comprehensive testing script to:
- Test WhatsApp connection
- Verify bridge communication
- Test message synchronization
- Diagnose common issues
- Provide detailed reports
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from db.models.platform_connection import PlatformConnection, PlatformType
from db.models.message import Message
from integrations.whatsapp_connector import WhatsAppConnector
from services.whatsapp_sync_enhanced import whatsapp_sync_enhanced
from config.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WhatsAppDiagnostics:
    """WhatsApp diagnostic tool."""

    def __init__(self):
        self.results: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "tests": []
        }

    def add_test_result(
        self,
        test_name: str,
        success: bool,
        details: Any = None,
        error: str = None
    ):
        """Add a test result."""
        self.results["tests"].append({
            "test": test_name,
            "success": success,
            "details": details,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def run_full_diagnostics(self, connection_id: str = None) -> Dict[str, Any]:
        """
        Run full diagnostic suite.

        Args:
            connection_id: Optional specific connection ID to test

        Returns:
            Diagnostic results
        """
        logger.info("=" * 80)
        logger.info("WhatsApp Integration Diagnostics - Enhanced Version")
        logger.info("=" * 80)

        async with get_session() as db:
            try:
                # Test 1: Configuration
                await self.test_configuration()

                # Test 2: Database connectivity
                await self.test_database_connectivity(db)

                # Test 3: Find WhatsApp connections
                connections = await self.find_whatsapp_connections(db, connection_id)

                if not connections:
                    logger.error("No WhatsApp connections found!")
                    self.add_test_result(
                        "find_connections",
                        False,
                        error="No WhatsApp connections found in database"
                    )
                    return

                # Test each connection
                for conn in connections:
                    await self.test_connection(db, conn)

                # Print summary
                self.print_summary()

            except Exception as e:
                logger.error(f"Diagnostic suite failed: {e}", exc_info=True)
                self.add_test_result("diagnostic_suite", False, error=str(e))

        return self.results

    async def test_configuration(self):
        """Test configuration settings."""
        logger.info("\n[TEST] Configuration Check")
        logger.info("-" * 80)

        config_ok = True
        details = {}

        # Check Matrix settings
        if not settings.MATRIX_HOMESERVER_URL:
            logger.error("❌ MATRIX_HOMESERVER_URL not configured")
            config_ok = False
        else:
            logger.info(f"✓ Matrix homeserver: {settings.MATRIX_HOMESERVER_URL}")
            details["homeserver_url"] = settings.MATRIX_HOMESERVER_URL

        if not settings.MATRIX_ACCESS_TOKEN:
            logger.error("❌ MATRIX_ACCESS_TOKEN not configured")
            config_ok = False
        else:
            logger.info(f"✓ Matrix access token configured (length: {len(settings.MATRIX_ACCESS_TOKEN)})")
            details["access_token_length"] = len(settings.MATRIX_ACCESS_TOKEN)

        if not settings.MATRIX_USER_ID:
            logger.error("❌ MATRIX_USER_ID not configured")
            config_ok = False
        else:
            logger.info(f"✓ Matrix user ID: {settings.MATRIX_USER_ID}")
            details["matrix_user_id"] = settings.MATRIX_USER_ID

        if not settings.WHATSAPP_BRIDGE_BOT_ID:
            logger.error("❌ WHATSAPP_BRIDGE_BOT_ID not configured")
            config_ok = False
        else:
            logger.info(f"✓ Bridge bot ID: {settings.WHATSAPP_BRIDGE_BOT_ID}")
            details["bridge_bot_id"] = settings.WHATSAPP_BRIDGE_BOT_ID

        self.add_test_result("configuration", config_ok, details)

    async def test_database_connectivity(self, db: AsyncSession):
        """Test database connectivity."""
        logger.info("\n[TEST] Database Connectivity")
        logger.info("-" * 80)

        try:
            # Simple query
            result = await db.execute(select(PlatformConnection).limit(1))
            logger.info("✓ Database connection successful")
            self.add_test_result("database_connectivity", True)

        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            self.add_test_result("database_connectivity", False, error=str(e))
            raise

    async def find_whatsapp_connections(
        self,
        db: AsyncSession,
        connection_id: str = None
    ) -> List[PlatformConnection]:
        """Find WhatsApp connections."""
        logger.info("\n[TEST] Finding WhatsApp Connections")
        logger.info("-" * 80)

        try:
            if connection_id:
                # Find specific connection
                result = await db.execute(
                    select(PlatformConnection).where(
                        PlatformConnection.id == connection_id
                    )
                )
                connections = [result.scalar_one_or_none()]
                connections = [c for c in connections if c]  # Filter None
            else:
                # Find all WhatsApp connections
                result = await db.execute(
                    select(PlatformConnection).where(
                        PlatformConnection.platform == PlatformType.WHATSAPP
                    )
                )
                connections = result.scalars().all()

            logger.info(f"✓ Found {len(connections)} WhatsApp connection(s)")

            for conn in connections:
                logger.info(f"  - Connection ID: {conn.id}")
                logger.info(f"    Status: {conn.status}")
                logger.info(f"    User ID: {conn.user_id}")
                logger.info(f"    Has credentials: {bool(conn.credentials)}")

            self.add_test_result(
                "find_connections",
                True,
                {"count": len(connections), "connection_ids": [str(c.id) for c in connections]}
            )

            return connections

        except Exception as e:
            logger.error(f"❌ Failed to find connections: {e}")
            self.add_test_result("find_connections", False, error=str(e))
            return []

    async def test_connection(self, db: AsyncSession, connection: PlatformConnection):
        """Test a specific connection."""
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Testing Connection: {connection.id}")
        logger.info(f"{'=' * 80}")

        # Test 1: Bridge connectivity
        await self.test_bridge_connectivity(connection)

        # Test 2: Bridge status
        await self.test_bridge_status(connection)

        # Test 3: Room discovery
        rooms = await self.test_room_discovery(connection)

        # Test 4: Message fetching
        if rooms:
            await self.test_message_fetching(connection, rooms[0])

        # Test 5: Message sync
        await self.test_message_sync(db, connection)

        # Test 6: Database message count
        await self.test_database_messages(db, connection)

    async def test_bridge_connectivity(self, connection: PlatformConnection):
        """Test bridge connectivity."""
        logger.info("\n[TEST] Bridge Connectivity")
        logger.info("-" * 80)

        try:
            connector = WhatsAppConnector(
                connection_id=connection.id,
                credentials=self._get_credentials(connection)
            )

            await connector.connect()
            logger.info("✓ Connected to Matrix homeserver")

            client = connector._get_client()
            whoami = await client.whoami()
            logger.info(f"✓ Authenticated as: {whoami.get('user_id')}")

            self.add_test_result(
                f"bridge_connectivity_{connection.id}",
                True,
                {"user_id": whoami.get('user_id')}
            )

            await connector.disconnect()

        except Exception as e:
            logger.error(f"❌ Bridge connectivity failed: {e}")
            self.add_test_result(
                f"bridge_connectivity_{connection.id}",
                False,
                error=str(e)
            )

    async def test_bridge_status(self, connection: PlatformConnection):
        """Test bridge status check."""
        logger.info("\n[TEST] Bridge Status")
        logger.info("-" * 80)

        try:
            connector = WhatsAppConnector(
                connection_id=connection.id,
                credentials=self._get_credentials(connection)
            )

            await connector.connect()
            status = await connector.get_bridge_status()

            logger.info(f"  Connected: {status.connected}")
            logger.info(f"  Logged in: {status.logged_in}")
            logger.info(f"  Phone: {status.phone}")

            if status.logged_in:
                logger.info("✓ WhatsApp is logged in")
            else:
                logger.warning("⚠ WhatsApp is NOT logged in")

            self.add_test_result(
                f"bridge_status_{connection.id}",
                True,
                {
                    "connected": status.connected,
                    "logged_in": status.logged_in,
                    "phone": status.phone
                }
            )

            await connector.disconnect()

        except Exception as e:
            logger.error(f"❌ Bridge status check failed: {e}")
            self.add_test_result(
                f"bridge_status_{connection.id}",
                False,
                error=str(e)
            )

    async def test_room_discovery(self, connection: PlatformConnection) -> List[Dict[str, Any]]:
        """Test room discovery."""
        logger.info("\n[TEST] Room Discovery")
        logger.info("-" * 80)

        try:
            connector = WhatsAppConnector(
                connection_id=connection.id,
                credentials=self._get_credentials(connection)
            )

            await connector.connect()
            rooms = await connector.get_rooms()

            logger.info(f"✓ Found {len(rooms)} WhatsApp rooms")

            for i, room in enumerate(rooms[:5], 1):  # Show first 5
                logger.info(f"  {i}. Room ID: {room['room_id']}")
                logger.info(f"     Name: {room.get('name', 'Unknown')}")
                logger.info(f"     Is Group: {room.get('is_group', False)}")

            if len(rooms) > 5:
                logger.info(f"  ... and {len(rooms) - 5} more rooms")

            self.add_test_result(
                f"room_discovery_{connection.id}",
                True,
                {"room_count": len(rooms), "rooms": rooms[:5]}
            )

            await connector.disconnect()
            return rooms

        except Exception as e:
            logger.error(f"❌ Room discovery failed: {e}")
            self.add_test_result(
                f"room_discovery_{connection.id}",
                False,
                error=str(e)
            )
            return []

    async def test_message_fetching(
        self,
        connection: PlatformConnection,
        room: Dict[str, Any]
    ):
        """Test message fetching from a room."""
        logger.info("\n[TEST] Message Fetching")
        logger.info("-" * 80)

        try:
            connector = WhatsAppConnector(
                connection_id=connection.id,
                credentials=self._get_credentials(connection)
            )

            await connector.connect()

            room_id = room["room_id"]
            logger.info(f"Testing room: {room.get('name', room_id)}")

            messages = await connector.fetch_messages(room_id, limit=10)

            logger.info(f"✓ Fetched {len(messages)} messages from room")

            for i, msg in enumerate(messages[:3], 1):  # Show first 3
                sender = msg.get("sender", "Unknown")
                content = msg.get("content", {})
                body = content.get("body", "")[:50]
                logger.info(f"  {i}. From: {sender}")
                logger.info(f"     Content: {body}...")

            self.add_test_result(
                f"message_fetching_{connection.id}",
                True,
                {"room_id": room_id, "message_count": len(messages)}
            )

            await connector.disconnect()

        except Exception as e:
            logger.error(f"❌ Message fetching failed: {e}")
            self.add_test_result(
                f"message_fetching_{connection.id}",
                False,
                error=str(e)
            )

    async def test_message_sync(self, db: AsyncSession, connection: PlatformConnection):
        """Test message synchronization."""
        logger.info("\n[TEST] Message Synchronization")
        logger.info("-" * 80)

        try:
            sync_service = whatsapp_sync_enhanced

            logger.info("Starting sync...")
            result = await sync_service.sync_messages_enhanced(
                connection_id=connection.id,
                limit=50,
                force=False
            )

            if result["success"]:
                logger.info("✓ Message sync successful")
                logger.info(f"  Total rooms: {result.get('total_rooms', 0)}")
                logger.info(f"  Messages synced: {result.get('total_messages_synced', 0)}")

                stats = result.get("stats", {})
                logger.info(f"  Sync attempts: {stats.get('sync_attempts', 0)}")
                logger.info(f"  Duration: {stats.get('duration_seconds', 0)}s")
            else:
                logger.error(f"❌ Message sync failed: {result.get('error')}")

            self.add_test_result(
                f"message_sync_{connection.id}",
                result["success"],
                result if result["success"] else None,
                result.get("error") if not result["success"] else None
            )

        except Exception as e:
            logger.error(f"❌ Message sync failed: {e}")
            self.add_test_result(
                f"message_sync_{connection.id}",
                False,
                error=str(e)
            )

    async def test_database_messages(self, db: AsyncSession, connection: PlatformConnection):
        """Test database message count."""
        logger.info("\n[TEST] Database Messages")
        logger.info("-" * 80)

        try:
            result = await db.execute(
                select(Message).where(
                    Message.connection_id == connection.id
                )
            )
            messages = result.scalars().all()

            logger.info(f"✓ Found {len(messages)} messages in database")

            if messages:
                # Show sample
                sample = messages[:3]
                for i, msg in enumerate(sample, 1):
                    logger.info(f"  {i}. Thread: {msg.thread_id}")
                    logger.info(f"     Content: {str(msg.content)[:50]}...")
                    logger.info(f"     Timestamp: {msg.timestamp}")

            self.add_test_result(
                f"database_messages_{connection.id}",
                True,
                {"message_count": len(messages)}
            )

        except Exception as e:
            logger.error(f"❌ Database message check failed: {e}")
            self.add_test_result(
                f"database_messages_{connection.id}",
                False,
                error=str(e)
            )

    def print_summary(self):
        """Print diagnostic summary."""
        logger.info("\n" + "=" * 80)
        logger.info("DIAGNOSTIC SUMMARY")
        logger.info("=" * 80)

        total_tests = len(self.results["tests"])
        passed_tests = sum(1 for t in self.results["tests"] if t["success"])
        failed_tests = total_tests - passed_tests

        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")

        if failed_tests > 0:
            logger.info("\nFailed tests:")
            for test in self.results["tests"]:
                if not test["success"]:
                    logger.info(f"  ❌ {test['test']}: {test.get('error', 'Unknown error')}")

        # Save to file
        output_file = f"whatsapp_diagnostics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"\nDetailed results saved to: {output_file}")

    def _get_credentials(self, connection: PlatformConnection) -> Dict[str, Any]:
        """Get credentials for connection."""
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

        return credentials


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="WhatsApp Integration Diagnostics")
    parser.add_argument(
        "--connection-id",
        help="Specific connection ID to test",
        default=None
    )

    args = parser.parse_args()

    diagnostics = WhatsAppDiagnostics()
    await diagnostics.run_full_diagnostics(args.connection_id)


if __name__ == "__main__":
    asyncio.run(main())
