#!/usr/bin/env python3
"""
Check Users and Sessions

Check existing users and create test user if needed.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from db.session import get_db
from db.models.user import User
from db.models.platform_connection import PlatformConnection
from services.auth.jwt_service import get_jwt_service


async def check_users_and_sessions():
    """Check existing users and sessions."""
    print("🔍 Checking Users and Sessions")
    print("=" * 50)
    
    async for db in get_db():
        try:
            # Check existing users
            print("1. Checking existing users...")
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            if users:
                print(f"   Found {len(users)} users:")
                for user in users:
                    print(f"   - {user.username} ({user.email}) - Active: {user.is_active}")
            else:
                print("   No users found")
            
            # Check platform connections
            print("\n2. Checking platform connections...")
            result = await db.execute(select(PlatformConnection))
            connections = result.scalars().all()
            
            if connections:
                print(f"   Found {len(connections)} connections:")
                for conn in connections:
                    print(f"   - {conn.platform} (ID: {conn.id}) - Status: {conn.status}")
            else:
                print("   No connections found")
            
            # Create test user if none exist
            if not users:
                print("\n3. Creating test user...")
                jwt_service = get_jwt_service()
                
                test_user = User(
                    id=uuid4(),
                    email='test@example.com',
                    username='testuser',
                    hashed_password=jwt_service.hash_password('testpass123'),
                    full_name='Test User',
                    role='user',
                    is_active=True,
                    is_superuser=False,
                    permissions=[]
                )
                
                db.add(test_user)
                await db.commit()
                await db.refresh(test_user)
                
                print(f"   ✅ Created test user:")
                print(f"   - Username: testuser")
                print(f"   - Password: testpass123")
                print(f"   - Email: test@example.com")
                print(f"   - User ID: {test_user.id}")
                
                # Create a WhatsApp connection for this user
                print("\n4. Creating WhatsApp connection...")
                from config.config import settings
                
                whatsapp_conn = PlatformConnection(
                    id=uuid4(),
                    user_id=test_user.id,
                    platform="WHATSAPP",
                    credentials={
                        "matrix_homeserver_url": settings.MATRIX_HOMESERVER_URL,
                        "matrix_access_token": settings.MATRIX_ACCESS_TOKEN,
                        "matrix_user_id": settings.MATRIX_USER_ID,
                        "bridge_bot_id": settings.WHATSAPP_BRIDGE_BOT_ID,
                    },
                    status="INACTIVE",
                    platform_metadata={}
                )
                
                db.add(whatsapp_conn)
                await db.commit()
                await db.refresh(whatsapp_conn)
                
                print(f"   ✅ Created WhatsApp connection:")
                print(f"   - Connection ID: {whatsapp_conn.id}")
                print(f"   - Status: {whatsapp_conn.status}")
                
                return {
                    "user_id": test_user.id,
                    "username": "testuser",
                    "password": "testpass123",
                    "connection_id": whatsapp_conn.id
                }
            else:
                # Return first user info
                first_user = users[0]
                user_connections = [c for c in connections if c.user_id == first_user.id]
                whatsapp_conn = next((c for c in user_connections if c.platform == "WHATSAPP"), None)
                
                return {
                    "user_id": first_user.id,
                    "username": first_user.username,
                    "email": first_user.email,
                    "connection_id": whatsapp_conn.id if whatsapp_conn else None
                }
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        break


async def test_login(username: str, password: str):
    """Test login with credentials."""
    print(f"\n🔐 Testing login for {username}...")
    
    try:
        import requests
        
        response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"   ✅ Login successful!")
            print(f"   - Token: {token[:30]}...")
            print(f"   - Expires in: {data.get('expires_in')} seconds")
            return token
        else:
            print(f"   ❌ Login failed: {response.status_code}")
            print(f"   - Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return None


async def main():
    """Main function."""
    user_info = await check_users_and_sessions()
    
    if user_info:
        print("\n" + "=" * 50)
        print("📱 Mobile App Login Info:")
        print(f"Username: {user_info.get('username', 'N/A')}")
        print(f"Password: testpass123 (if test user)")
        print(f"Connection ID: {user_info.get('connection_id', 'N/A')}")
        
        # Test login
        if user_info.get('username'):
            token = await test_login(user_info['username'], 'testpass123')
            
            if token and user_info.get('connection_id'):
                print(f"\n🧪 Testing WhatsApp endpoint...")
                try:
                    import requests
                    
                    response = requests.get(
                        f"http://localhost:8000/api/v1/whatsapp/{user_info['connection_id']}/status",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        print(f"   ✅ WhatsApp endpoint works!")
                        print(f"   - Response: {response.json()}")
                    else:
                        print(f"   ❌ WhatsApp endpoint failed: {response.status_code}")
                        print(f"   - Error: {response.text}")
                        
                except Exception as e:
                    print(f"   ❌ WhatsApp test error: {e}")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)