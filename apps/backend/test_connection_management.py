#!/usr/bin/env python3
"""
Test WhatsApp Connection Management

Test the connection management service to verify it detects existing connections.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from db.models.user import User
from db.session import get_db
from services.whatsapp_connection_manager import get_whatsapp_connection_manager


async def test_connection_management():
    """Test connection management service."""
    print("🔗 Testing WhatsApp Connection Management")
    print("=" * 60)

    async for db in get_db():
        try:
            # Get a user
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()

            if not user:
                print("❌ No users found")
                return

            print(f"✅ Testing with user: {user.username} ({user.id})")

            # Test connection manager
            connection_manager = get_whatsapp_connection_manager()

            print("\n1. Checking for existing connections...")
            result = await connection_manager.get_or_create_connection(db, user.id)

            print(f"   Connection ID: {result.get('connection_id')}")
            print(f"   Is Existing: {result.get('is_existing')}")
            print(f"   Is Logged In: {result.get('is_logged_in')}")
            print(f"   Phone: {result.get('phone')}")
            print(f"   Message: {result.get('message')}")

            if result.get("error"):
                print(f"   Error: {result.get('error')}")

            print("\n2. Listing user connections...")
            connections = await connection_manager.list_user_connections(db, user.id)

            print(f"   Found {len(connections)} connections:")
            for i, conn in enumerate(connections, 1):
                print(f"   {i}. {conn['connection_id']}")
                print(f"      Status: {conn['status']}")
                print(f"      Has Credentials: {conn['has_credentials']}")
                print(f"      Created: {conn['created_at']}")

            print("\n" + "=" * 60)
            print("✅ Connection management test completed!")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()

        break


if __name__ == "__main__":
    asyncio.run(test_connection_management())
