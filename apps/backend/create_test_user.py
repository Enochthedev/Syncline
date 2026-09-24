#!/usr/bin/env python3
"""
Create Test User

Create a test user with known credentials for mobile app testing.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from db.models.platform_connection import PlatformConnection
from db.models.user import User
from db.session import get_db
from services.auth.jwt_service import get_jwt_service


async def create_test_user():
    """Create test user with known credentials."""
    print("🔧 Creating Test User")
    print("=" * 50)

    async for db in get_db():
        try:
            # Check if testuser already exists
            result = await db.execute(select(User).where(User.username == "testuser"))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print("   ⚠️  Test user already exists")
                print(f"   - Username: testuser")
                print(f"   - Email: {existing_user.email}")
                print(f"   - User ID: {existing_user.id}")

                # Get WhatsApp connection
                result = await db.execute(
                    select(PlatformConnection)
                    .where(PlatformConnection.user_id == existing_user.id)
                    .where(PlatformConnection.platform == "WHATSAPP")
                )
                whatsapp_conn = result.scalar_one_or_none()

                if whatsapp_conn:
                    print(f"   - WhatsApp Connection ID: {whatsapp_conn.id}")
                else:
                    print("   - No WhatsApp connection found")

                return {
                    "user_id": existing_user.id,
                    "username": "testuser",
                    "password": "testpass123",
                    "connection_id": whatsapp_conn.id if whatsapp_conn else None,
                }

            # Create new test user
            print("   📝 Creating new test user...")
            jwt_service = get_jwt_service()

            test_user = User(
                id=uuid4(),
                email="test@example.com",
                username="testuser",
                hashed_password=jwt_service.hash_password("testpass123"),
                full_name="Test User",
                role="user",
                is_active=True,
                is_superuser=False,
                permissions=[],
            )

            db.add(test_user)
            await db.commit()
            await db.refresh(test_user)

            print(f"   ✅ Created test user:")
            print(f"   - Username: testuser")
            print(f"   - Password: testpass123")
            print(f"   - Email: test@example.com")
            print(f"   - User ID: {test_user.id}")

            # Create WhatsApp connection
            print("\n   📱 Creating WhatsApp connection...")
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
                platform_metadata={},
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
                "connection_id": whatsapp_conn.id,
            }

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()
            return None

        break


async def test_login_and_whatsapp(user_info):
    """Test login and WhatsApp endpoint."""
    if not user_info:
        return

    print("\n" + "=" * 50)
    print("🧪 Testing Authentication")

    try:
        import requests

        # Test login
        print("1. Testing login...")
        response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"username": user_info["username"], "password": user_info["password"]},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"   ✅ Login successful!")
            print(f"   - Token: {token[:30]}...")

            # Test WhatsApp endpoint
            if user_info.get("connection_id"):
                print("\n2. Testing WhatsApp endpoint...")
                response = requests.get(
                    f"http://localhost:8000/api/v1/whatsapp/{user_info['connection_id']}/status",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )

                if response.status_code == 200:
                    print(f"   ✅ WhatsApp endpoint works!")
                    data = response.json()
                    print(f"   - Connection ID: {data.get('connection_id')}")
                    print(f"   - Healthy: {data.get('is_healthy')}")
                else:
                    print(f"   ❌ WhatsApp endpoint failed: {response.status_code}")
                    print(f"   - Error: {response.text}")
            else:
                print("\n2. ⚠️  No WhatsApp connection to test")

        else:
            print(f"   ❌ Login failed: {response.status_code}")
            print(f"   - Error: {response.text}")

    except Exception as e:
        print(f"   ❌ Test error: {e}")


async def main():
    """Main function."""
    user_info = await create_test_user()
    await test_login_and_whatsapp(user_info)

    if user_info:
        print("\n" + "=" * 50)
        print("📱 Mobile App Credentials:")
        print(f"Username: {user_info['username']}")
        print(f"Password: {user_info['password']}")
        print(f"Connection ID: {user_info.get('connection_id', 'N/A')}")
        print("\nUse these credentials in your mobile app!")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
