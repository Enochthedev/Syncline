#!/usr/bin/env python3
"""
Test WhatsApp Message Sending and Sync

Send a test message and check if messages are syncing.
"""

import asyncio
from uuid import UUID

from sqlalchemy import select

from db.models.platform_connection import PlatformConnection
from db.session import get_db
from integrations.whatsapp_connector import WhatsAppConnector


async def test_whatsapp_messaging():
    """Test sending a message and checking sync."""
    print("🧪 Testing WhatsApp Messaging")
    print("=" * 60)

    connection_id = UUID(
        "9b1861fc-79e1-40cd-91cd-959717124fff"
    )  # Active connection with credentials
    test_phone = "+2349073069006"  # Your actual phone number

    async for db in get_db():
        try:
            # Get connection
            result = await db.execute(
                select(PlatformConnection).where(PlatformConnection.id == connection_id)
            )
            connection = result.scalar_one_or_none()

            if not connection:
                print("❌ Connection not found")
                return

            print(f"✅ Found connection: {connection_id}")
            print(f"   Status: {connection.status}")
            print(f"   Credentials keys: {list(connection.credentials.keys())}")

            # Create connector with correct parameters
            connector = WhatsAppConnector(
                connection_id=connection.id, credentials=connection.credentials
            )

            # Check bridge status first
            print("\n1. Checking bridge status...")
            status = await connector.get_bridge_status()
            print(f"   Connected: {status.connected}")
            print(f"   Logged In: {status.logged_in}")
            print(f"   Phone: {status.phone}")

            if not status.logged_in:
                print("❌ Not logged in to WhatsApp")
                return

            # Get or create room for the phone number
            print(f"\n2. Finding room for {test_phone}...")
            rooms = await connector.get_rooms()
            print(f"   Found {len(rooms)} total rooms")

            # Look for existing room with this phone number
            target_room = None
            for room in rooms:
                room_name = room.get("name", "")
                if test_phone in room_name or test_phone.replace("+", "") in room_name:
                    target_room = room
                    print(f"   ✅ Found existing room: {room['room_id']}")
                    print(f"      Name: {room_name}")
                    break

            if not target_room:
                print(f"   ⚠️  No existing room found for {test_phone}")
                print("   You may need to start a conversation first from WhatsApp")

                # Try to find any room to test with
                if rooms:
                    target_room = rooms[0]
                    print(
                        f"   Using first available room for testing: {target_room['room_id']}"
                    )
                else:
                    print("   ❌ No rooms available")
                    return

            room_id = target_room["room_id"]

            # Send test message
            print(f"\n3. Sending test message to room {room_id}...")
            test_message = "🤖 Test message from Syncline backend - testing Matrix bridge integration!"

            try:
                event_id = await connector.send_message(room_id, test_message)
                print(f"   ✅ Message sent successfully!")
                print(f"   Event ID: {event_id}")
            except Exception as e:
                print(f"   ❌ Failed to send message: {e}")
                return

            # Wait a moment for message to be processed
            print("\n4. Waiting for message to be processed...")
            await asyncio.sleep(2)

            # Fetch recent messages
            print("\n5. Fetching recent messages from room...")
            try:
                messages = await connector.fetch_messages(room_id, limit=5)
                print(f"   Found {len(messages)} recent messages:")

                for i, msg in enumerate(messages[:5], 1):
                    sender = msg.get("sender", "Unknown")
                    content = msg.get("content", {})
                    body = content.get("body", "No content")
                    timestamp = msg.get("origin_server_ts", 0)

                    print(f"\n   Message {i}:")
                    print(f"     From: {sender}")
                    print(f"     Content: {body[:100]}...")
                    print(f"     Time: {timestamp}")

                    if body == test_message:
                        print(f"     ✅ Found our test message!")

            except Exception as e:
                print(f"   ❌ Failed to fetch messages: {e}")

            # Check if messages are in database
            print("\n6. Checking database for synced messages...")
            from db.models.message import Message

            result = await db.execute(
                select(Message)
                .where(Message.connection_id == connection_id)
                .order_by(Message.timestamp.desc())
                .limit(10)
            )
            db_messages = result.scalars().all()

            print(f"   Found {len(db_messages)} messages in database")

            if db_messages:
                print("\n   Recent messages:")
                for i, msg in enumerate(db_messages[:5], 1):
                    content_text = msg.content.get("text", "") if msg.content else ""
                    print(f"   {i}. {content_text[:100]}...")
                    print(
                        f"      From: {msg.sender.full_name if msg.sender else 'Unknown'}"
                    )
                    print(f"      Time: {msg.timestamp}")
            else:
                print("   ⚠️  No messages found in database yet")
                print("   Running message sync...")

                # Import and run message sync
                from services.whatsapp_message_sync import get_whatsapp_sync_service

                sync_service = get_whatsapp_sync_service()

                sync_result = await sync_service.sync_messages_for_connection(
                    db, connection_id, limit=50
                )

                if sync_result["success"]:
                    print(f"   ✅ Sync completed!")
                    print(f"   - Total rooms: {sync_result['total_rooms']}")
                    print(
                        f"   - Messages synced: {sync_result['total_messages_synced']}"
                    )

                    # Check database again
                    result = await db.execute(
                        select(Message)
                        .where(Message.connection_id == connection_id)
                        .order_by(Message.timestamp.desc())
                        .limit(5)
                    )
                    new_messages = result.scalars().all()

                    if new_messages:
                        print(f"\n   📨 Found {len(new_messages)} synced messages:")
                        for i, msg in enumerate(new_messages, 1):
                            content_text = (
                                msg.content.get("text", "") if msg.content else ""
                            )
                            print(f"   {i}. {content_text[:50]}...")
                            print(f"      Time: {msg.timestamp}")
                else:
                    print(
                        f"   ❌ Sync failed: {sync_result.get('error', 'Unknown error')}"
                    )

            print("\n" + "=" * 60)
            print("✅ Test completed!")
            print("\nNext steps:")
            print("1. Check your WhatsApp to see if you received the test message")
            print("2. Send a reply from WhatsApp")
            print("3. Run sync to pull messages into the database")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()

        break


if __name__ == "__main__":
    asyncio.run(test_whatsapp_messaging())
