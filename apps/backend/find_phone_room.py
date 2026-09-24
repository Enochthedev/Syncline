#!/usr/bin/env python3
"""
Find WhatsApp Room for Phone Number

Find the Matrix room for a specific phone number in WhatsApp.
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from db.models.platform_connection import PlatformConnection
from db.session import get_db
from integrations.whatsapp_connector import WhatsAppConnector


async def find_phone_room():
    """Find room for specific phone number."""
    print("🔍 Finding WhatsApp Room for Phone Number")
    print("=" * 60)

    # Use the active connection
    connection_id = UUID("9b1861fc-79e1-40cd-91cd-959717124fff")
    target_phone = "+2349073069006"

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

            print(f"✅ Using connection: {connection_id}")
            print(f"🎯 Looking for phone: {target_phone}")

            # Create connector
            connector = WhatsAppConnector(
                connection_id=connection.id, credentials=connection.credentials
            )

            await connector.connect()

            try:
                # Get all rooms
                rooms = await connector.get_rooms()
                print(f"\n📱 Found {len(rooms)} total rooms")

                # Search for rooms that might match the phone number
                potential_matches = []

                for i, room in enumerate(rooms, 1):
                    room_id = room["room_id"]
                    room_name = room.get("name", room_id)

                    print(f"\n{i}. Room: {room_id}")
                    print(f"   Name: {room_name}")

                    # Check if phone number appears in room name or ID
                    phone_variants = [
                        target_phone,  # +2349073069006
                        target_phone[1:],  # 2349073069006
                        target_phone[4:],  # 9073069006
                        "0" + target_phone[4:],  # 09073069006
                    ]

                    match_found = False
                    for variant in phone_variants:
                        if variant in room_name or variant in room_id:
                            print(f"   🎯 POTENTIAL MATCH! Contains: {variant}")
                            potential_matches.append(
                                {"room": room, "variant": variant, "index": i}
                            )
                            match_found = True
                            break

                    # Get recent messages to see participants
                    try:
                        messages = await connector.fetch_messages(room_id, limit=3)
                        if messages:
                            print(f"   Recent messages: {len(messages)}")
                            for msg in messages[:2]:
                                sender = msg.get("sender", "Unknown")
                                content = msg.get("content", {}).get(
                                    "body", "No content"
                                )
                                print(f"     - {sender}: {content[:50]}...")
                        else:
                            print("   No recent messages")
                    except Exception as e:
                        print(f"   ⚠️  Could not fetch messages: {e}")

                # Summary
                print("\n" + "=" * 60)
                if potential_matches:
                    print(f"🎯 Found {len(potential_matches)} potential matches:")
                    for match in potential_matches:
                        room = match["room"]
                        print(f"\n{match['index']}. {room['room_id']}")
                        print(f"   Matched variant: {match['variant']}")
                        print(f"   Room name: {room.get('name', 'No name')}")

                        # Test sending a message to this room
                        print(f"   Testing message send...")
                        try:
                            test_msg = f"🧪 Test message for {target_phone} - checking room match"
                            event_id = await connector.send_message(
                                room["room_id"], test_msg
                            )
                            print(f"   ✅ Message sent! Event ID: {event_id}")
                        except Exception as e:
                            print(f"   ❌ Failed to send: {e}")
                else:
                    print("❌ No rooms found matching the phone number")
                    print("\n💡 Suggestions:")
                    print(
                        "1. Start a conversation with +2349073069006 from your WhatsApp"
                    )
                    print("2. Send a message to that number first")
                    print("3. Wait a few minutes for the bridge to sync")
                    print("4. Run this script again")

                    print(f"\n📋 All rooms for reference:")
                    for i, room in enumerate(rooms[:10], 1):  # Show first 10
                        print(f"{i}. {room['room_id']} - {room.get('name', 'No name')}")

            finally:
                await connector.disconnect()

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()

        break


if __name__ == "__main__":
    asyncio.run(find_phone_room())
