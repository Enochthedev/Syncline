"""
Test WhatsApp Connection Full Flow

This script tests the complete flow:
1. Create/get connection
2. Request pairing code
3. Display result
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from config.config import settings
from db.models.platform_connection import PlatformConnection, PlatformType
from db.models.user import User
from db.session import get_session
from integrations.whatsapp_connector_enhanced import EnhancedWhatsAppConnector
from services.whatsapp_connection_manager import get_whatsapp_connection_manager


async def test_full_flow():
    print("=" * 80)
    print("WhatsApp Connection Full Flow Test")
    print("=" * 80)

    async with get_session() as db:
        # Step 1: Get or create user
        print("\n[1] Getting user...")
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()

        if not user:
            print("❌ No user found. Create a user first.")
            return

        print(f"✓ Found user: {user.email} (ID: {user.id})")

        # Step 2: Get or create WhatsApp connection
        print("\n[2] Getting or creating WhatsApp connection...")
        connection_manager = get_whatsapp_connection_manager()

        conn_result = await connection_manager.get_or_create_connection(db, user.id)

        if conn_result.get("error"):
            print(f"❌ Error: {conn_result['error']}")
            return

        connection_id = conn_result["connection_id"]
        print(f"✓ Connection ID: {connection_id}")
        print(f"  Is existing: {conn_result['is_existing']}")
        print(f"  Is logged in: {conn_result['is_logged_in']}")

        # Step 3: Get the connection
        result = await db.execute(
            select(PlatformConnection).where(PlatformConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()

        if not connection:
            print("❌ Connection not found")
            return

        # Step 4: Test login with phone
        print("\n[3] Testing phone login...")
        print("-" * 80)

        test_phone = input("Enter phone number (e.g., +2349167674418): ").strip()

        if not test_phone:
            test_phone = "+2349167674418"
            print(f"Using default: {test_phone}")

        # Prepare credentials
        credentials = dict(connection.credentials) if connection.credentials else {}

        if not credentials.get("matrix_homeserver_url"):
            credentials["matrix_homeserver_url"] = settings.MATRIX_HOMESERVER_URL
        if not credentials.get("matrix_access_token"):
            credentials["matrix_access_token"] = settings.MATRIX_ACCESS_TOKEN
        if not credentials.get("matrix_user_id"):
            credentials["matrix_user_id"] = settings.MATRIX_USER_ID
        if not credentials.get("bridge_bot_id"):
            credentials["bridge_bot_id"] = settings.WHATSAPP_BRIDGE_BOT_ID

        # Create enhanced connector
        connector = EnhancedWhatsAppConnector(
            connection_id=connection_id, credentials=credentials
        )

        try:
            print("Connecting to Matrix...")
            await connector.connect()
            print("✓ Connected to Matrix")

            print(f"Requesting pairing code for {test_phone}...")
            pairing_code = await connector.login_with_phone(test_phone)

            print("\n" + "=" * 80)
            print("RESULT")
            print("=" * 80)

            if pairing_code == "CHECK_PHONE":
                print("✓ SUCCESS: Check your WhatsApp app for a notification!")
                print()
                print("Next steps:")
                print("1. Open WhatsApp on your phone")
                print("2. Go to Settings > Linked Devices")
                print("3. Follow the prompts to complete linking")
            elif pairing_code and len(pairing_code) >= 8:
                print(f"✓ SUCCESS: Your pairing code is:")
                print()
                print(f"    {pairing_code}")
                print()
                print("Next steps:")
                print("1. Open WhatsApp on your phone")
                print("2. Go to Settings > Linked Devices")
                print("3. Tap 'Link a Device'")
                print("4. Select 'Link with phone number instead'")
                print(f"5. Enter this code: {pairing_code}")
            else:
                print(f"⚠️  Unexpected response: {pairing_code}")
                print("This might mean the bridge is having issues.")
                print("Check bridge logs: docker logs syncline-whatsapp-bridge")

            print("=" * 80)

        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\nTroubleshooting:")
            print("1. Check if bridge is running: docker ps | grep whatsapp")
            print("2. Check bridge logs: docker logs syncline-whatsapp-bridge")
            print(
                "3. Verify Matrix homeserver: curl http://localhost:8008/_matrix/client/versions"
            )
        finally:
            await connector.disconnect()


if __name__ == "__main__":
    asyncio.run(test_full_flow())
