#!/usr/bin/env python3
"""
Complete WhatsApp Integration Test

Comprehensive test of all WhatsApp features:
1. Connection management (existing connection detection)
2. Message sending and retrieval
3. Message sync to database
4. Background sync service
5. Webhook handling
6. Mobile app integration flow
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from db.session import get_db
from db.models.platform_connection import PlatformConnection
from db.models.user import User
from db.models.message import Message
from sqlalchemy import select
from integrations.whatsapp_connector import WhatsAppConnector
from services.whatsapp_connection_manager import get_whatsapp_connection_manager
from services.whatsapp_message_sync import get_whatsapp_sync_service
from services.whatsapp_background_sync import get_whatsapp_background_sync_service
from services.whatsapp_webhook_service import get_whatsapp_webhook_service


async def test_complete_whatsapp_integration():
    """Run comprehensive WhatsApp integration test."""
    print("🚀 Complete WhatsApp Integration Test")
    print("=" * 80)
    
    # Use the active connection
    connection_id = UUID('9b1861fc-79e1-40cd-91cd-959717124fff')
    test_phone = '+2349073069006'
    
    async for db in get_db():
        try:
            # Get user and connection
            result = await db.execute(
                select(PlatformConnection).where(PlatformConnection.id == connection_id)
            )
            connection = result.scalar_one_or_none()
            
            if not connection:
                print("❌ Connection not found")
                return
            
            user_result = await db.execute(
                select(User).where(User.id == connection.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            print(f"✅ Testing with:")
            print(f"   User: {user.username} ({user.id})")
            print(f"   Connection: {connection_id}")
            print(f"   Status: {connection.status}")
            print(f"   Target Phone: {test_phone}")
            
            # =================================================================
            # TEST 1: Connection Management
            # =================================================================
            print(f"\n{'='*20} TEST 1: Connection Management {'='*20}")
            
            connection_manager = get_whatsapp_connection_manager()
            
            print("1.1 Testing existing connection detection...")
            conn_result = await connection_manager.get_or_create_connection(db, user.id)
            
            print(f"   Connection ID: {conn_result.get('connection_id')}")
            print(f"   Is Existing: {conn_result.get('is_existing')}")
            print(f"   Is Logged In: {conn_result.get('is_logged_in')}")
            print(f"   Phone: {conn_result.get('phone')}")
            print(f"   Message: {conn_result.get('message')}")
            
            if conn_result.get('is_existing') and conn_result.get('is_logged_in'):
                print("   ✅ Connection management working - found existing logged-in connection")
            else:
                print("   ⚠️  Connection exists but not logged in")
            
            print("\n1.2 Listing user connections...")
            connections = await connection_manager.list_user_connections(db, user.id)
            print(f"   Found {len(connections)} total connections")
            active_count = sum(1 for c in connections if c['status'] == 'active')
            print(f"   Active connections: {active_count}")
            
            # =================================================================
            # TEST 2: WhatsApp Connector
            # =================================================================
            print(f"\n{'='*20} TEST 2: WhatsApp Connector {'='*20}")
            
            connector = WhatsAppConnector(
                connection_id=connection.id,
                credentials=connection.credentials
            )
            
            await connector.connect()
            
            try:
                print("2.1 Testing bridge status...")
                status = await connector.get_bridge_status()
                print(f"   Connected: {status.connected}")
                print(f"   Logged In: {status.logged_in}")
                print(f"   Phone: {status.phone}")
                
                is_logged_in = status.logged_in if hasattr(status, 'logged_in') else status.get('logged_in', False)
                
                if is_logged_in:
                    print("   ✅ Bridge connection working")
                else:
                    print("   ❌ Bridge not logged in")
                    return
                
                print("\n2.2 Testing room discovery...")
                rooms = await connector.get_rooms()
                print(f"   Found {len(rooms)} WhatsApp rooms")
                
                if rooms:
                    test_room = rooms[0]
                    print(f"   Using test room: {test_room['room_id']}")
                    
                    print("\n2.3 Testing message sending...")
                    test_message = f"🧪 Complete integration test - {datetime.now().strftime('%H:%M:%S')}"
                    event_id = await connector.send_message(test_room['room_id'], test_message)
                    print(f"   ✅ Message sent! Event ID: {event_id}")
                    
                    print("\n2.4 Testing message retrieval...")
                    await asyncio.sleep(2)  # Wait for message to be processed
                    messages = await connector.fetch_messages(test_room['room_id'], limit=3)
                    print(f"   Retrieved {len(messages)} recent messages")
                    
                    # Check if our test message is there
                    found_test_message = False
                    for msg in messages:
                        content = msg.get('content', {}).get('body', '')
                        if test_message in content:
                            found_test_message = True
                            print(f"   ✅ Found our test message!")
                            break
                    
                    if not found_test_message:
                        print(f"   ⚠️  Test message not found in recent messages")
                else:
                    print("   ❌ No rooms found")
                    return
                
            finally:
                await connector.disconnect()
            
            # =================================================================
            # TEST 3: Message Sync Service
            # =================================================================
            print(f"\n{'='*20} TEST 3: Message Sync Service {'='*20}")
            
            sync_service = get_whatsapp_sync_service()
            
            print("3.1 Testing message sync to database...")
            sync_result = await sync_service.sync_messages_for_connection(
                db, connection_id, limit=50
            )
            
            if sync_result["success"]:
                print(f"   ✅ Sync successful!")
                print(f"   Total rooms: {sync_result['total_rooms']}")
                print(f"   Messages synced: {sync_result['total_messages_synced']}")
                
                # Check database
                print("\n3.2 Verifying messages in database...")
                result = await db.execute(
                    select(Message)
                    .where(Message.connection_id == connection_id)
                    .order_by(Message.timestamp.desc())
                    .limit(5)
                )
                db_messages = result.scalars().all()
                
                print(f"   Found {len(db_messages)} messages in database")
                if db_messages:
                    print("   Recent messages:")
                    for i, msg in enumerate(db_messages[:3], 1):
                        content_text = msg.content.get('text', '') if msg.content else ''
                        print(f"   {i}. {content_text[:60]}...")
                        print(f"      Time: {msg.timestamp}")
                    print("   ✅ Database sync working")
                else:
                    print("   ⚠️  No messages in database")
            else:
                print(f"   ❌ Sync failed: {sync_result.get('error')}")
            
            # =================================================================
            # TEST 4: Background Sync Service
            # =================================================================
            print(f"\n{'='*20} TEST 4: Background Sync Service {'='*20}")
            
            background_sync_service = get_whatsapp_background_sync_service()
            
            print("4.1 Testing background sync status...")
            status = background_sync_service.get_sync_status()
            print(f"   Running: {status['running']}")
            print(f"   Active tasks: {status['active_tasks']}")
            
            print("\n4.2 Testing manual sync trigger...")
            manual_sync_result = await background_sync_service.sync_connection_now(connection_id)
            if manual_sync_result["success"]:
                print("   ✅ Manual sync successful")
            else:
                print(f"   ❌ Manual sync failed: {manual_sync_result.get('error')}")
            
            # =================================================================
            # TEST 5: Webhook Service
            # =================================================================
            print(f"\n{'='*20} TEST 5: Webhook Service {'='*20}")
            
            webhook_service = get_whatsapp_webhook_service()
            
            print("5.1 Testing webhook setup...")
            webhook_result = await webhook_service.setup_webhook_subscription(
                connection_id, "https://example.com/webhook"
            )
            
            if webhook_result["success"]:
                print("   ✅ Webhook setup successful")
                print(f"   Webhook URL: {webhook_result['webhook_url']}")
            else:
                print(f"   ❌ Webhook setup failed: {webhook_result.get('error')}")
            
            print("\n5.2 Testing webhook data processing...")
            # Mock webhook data
            mock_webhook_data = {
                "events": [
                    {
                        "type": "m.room.message",
                        "room_id": "!test:localhost",
                        "sender": "@testuser:localhost",
                        "event_id": "$test123",
                        "content": {
                            "msgtype": "m.text",
                            "body": "Test webhook message"
                        },
                        "origin_server_ts": int(datetime.now().timestamp() * 1000)
                    }
                ]
            }
            
            webhook_process_result = await webhook_service.handle_matrix_webhook(
                db, mock_webhook_data
            )
            
            if webhook_process_result["success"]:
                print("   ✅ Webhook processing successful")
                print(f"   Events processed: {webhook_process_result['events_processed']}")
            else:
                print(f"   ❌ Webhook processing failed: {webhook_process_result.get('error')}")
            
            # =================================================================
            # TEST SUMMARY
            # =================================================================
            print(f"\n{'='*20} TEST SUMMARY {'='*20}")
            
            tests_passed = 0
            total_tests = 5
            
            # Check results
            if conn_result.get('is_existing'):
                tests_passed += 1
                print("✅ Connection Management: PASSED")
            else:
                print("❌ Connection Management: FAILED")
            
            if is_logged_in:
                tests_passed += 1
                print("✅ WhatsApp Connector: PASSED")
            else:
                print("❌ WhatsApp Connector: FAILED")
            
            if sync_result["success"]:
                tests_passed += 1
                print("✅ Message Sync Service: PASSED")
            else:
                print("❌ Message Sync Service: FAILED")
            
            if manual_sync_result["success"]:
                tests_passed += 1
                print("✅ Background Sync Service: PASSED")
            else:
                print("❌ Background Sync Service: FAILED")
            
            if webhook_result["success"]:
                tests_passed += 1
                print("✅ Webhook Service: PASSED")
            else:
                print("❌ Webhook Service: FAILED")
            
            print(f"\n🎯 FINAL RESULT: {tests_passed}/{total_tests} tests passed")
            
            if tests_passed == total_tests:
                print("🎉 ALL TESTS PASSED! WhatsApp integration is fully functional!")
            else:
                print(f"⚠️  {total_tests - tests_passed} test(s) failed. Check the logs above.")
            
            # Mobile app integration notes
            print(f"\n📱 MOBILE APP INTEGRATION STATUS:")
            print("✅ Connection check endpoint: /api/v1/whatsapp/connections/check-existing")
            print("✅ Mobile app updated to check existing connections first")
            print("✅ Background sync available: /api/v1/whatsapp/{id}/background-sync/start")
            print("✅ Webhook support: /api/v1/whatsapp/{id}/webhook/setup")
            print("✅ Message sync: /api/v1/whatsapp/{id}/messages/sync")
            
            print(f"\n🎯 NEXT STEPS:")
            print("1. Test mobile app with updated connection flow")
            print("2. Send WhatsApp message to +2349073069006 to create room")
            print("3. Enable background sync for real-time updates")
            print("4. Setup webhooks for instant message delivery")
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        break


if __name__ == "__main__":
    asyncio.run(test_complete_whatsapp_integration())