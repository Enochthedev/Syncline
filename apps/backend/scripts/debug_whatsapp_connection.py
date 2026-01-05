"""
WhatsApp Connection Debug Script

Quick diagnostic to identify why phone login is failing.
Run this to check your WhatsApp setup.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import settings
from integrations.whatsapp_connector import WhatsAppConnector
from integrations.whatsapp_connector_enhanced import EnhancedWhatsAppConnector
from uuid import uuid4

print("=" * 80)
print("WhatsApp Connection Diagnostics")
print("=" * 80)

# Step 1: Check configuration
print("\n[1] Checking Configuration...")
print("-" * 80)

config_issues = []

if not settings.MATRIX_HOMESERVER_URL:
    print("❌ MATRIX_HOMESERVER_URL is not set")
    config_issues.append("MATRIX_HOMESERVER_URL")
else:
    print(f"✓ MATRIX_HOMESERVER_URL: {settings.MATRIX_HOMESERVER_URL}")

if not settings.MATRIX_ACCESS_TOKEN:
    print("❌ MATRIX_ACCESS_TOKEN is not set")
    config_issues.append("MATRIX_ACCESS_TOKEN")
else:
    print(f"✓ MATRIX_ACCESS_TOKEN: {'*' * 20} (length: {len(settings.MATRIX_ACCESS_TOKEN)})")

if not settings.MATRIX_USER_ID:
    print("❌ MATRIX_USER_ID is not set")
    config_issues.append("MATRIX_USER_ID")
else:
    print(f"✓ MATRIX_USER_ID: {settings.MATRIX_USER_ID}")

if not settings.WHATSAPP_BRIDGE_BOT_ID:
    print("❌ WHATSAPP_BRIDGE_BOT_ID is not set")
    config_issues.append("WHATSAPP_BRIDGE_BOT_ID")
else:
    print(f"✓ WHATSAPP_BRIDGE_BOT_ID: {settings.WHATSAPP_BRIDGE_BOT_ID}")

if config_issues:
    print(f"\n⚠️  Missing configuration: {', '.join(config_issues)}")
    print("\nPlease add these to your .env file:")
    for var in config_issues:
        print(f"  {var}=<your_value>")
    sys.exit(1)

print("\n✓ All configuration variables are set")


# Step 2: Test Matrix connection
async def test_connection():
    print("\n[2] Testing Matrix Connection...")
    print("-" * 80)

    credentials = {
        "matrix_homeserver_url": settings.MATRIX_HOMESERVER_URL,
        "matrix_access_token": settings.MATRIX_ACCESS_TOKEN,
        "matrix_user_id": settings.MATRIX_USER_ID,
        "bridge_bot_id": settings.WHATSAPP_BRIDGE_BOT_ID,
    }

    # Use enhanced connector for better error messages
    connector = EnhancedWhatsAppConnector(
        connection_id=uuid4(),
        credentials=credentials
    )

    try:
        print("Connecting to Matrix homeserver...")
        await connector.connect()
        print("✓ Successfully connected to Matrix")

        client = connector._get_client()
        whoami = await client.whoami()
        print(f"✓ Authenticated as: {whoami.get('user_id')}")

        # Test bridge status
        print("\n[3] Testing Bridge Status...")
        print("-" * 80)

        status = await connector.get_bridge_status()
        print(f"  Bridge connected: {status.connected}")
        print(f"  WhatsApp logged in: {status.logged_in}")
        print(f"  Phone: {status.phone or 'Not logged in'}")

        if status.logged_in:
            print("\n✓ WhatsApp is already logged in!")
        else:
            print("\n⚠️  WhatsApp is not logged in yet")
            print("   You need to scan QR code or use phone pairing")

        # Test phone login capability
        print("\n[4] Testing Phone Login...")
        print("-" * 80)

        test_phone = "+1234567890"  # Dummy phone
        print(f"Testing pairing code request (using dummy phone: {test_phone})...")

        try:
            # This will fail but we can see if the bridge responds
            pairing_code = await connector.login_with_phone(test_phone)
            print(f"✓ Bridge responded with: {pairing_code}")

            if pairing_code == "CHECK_PHONE":
                print("  Bridge sent notification to phone")
            elif pairing_code and len(pairing_code) >= 8:
                print(f"  Bridge returned pairing code: {pairing_code}")
            else:
                print(f"  Unexpected response: {pairing_code}")

        except Exception as e:
            print(f"⚠️  Phone login test failed: {e}")
            print("   This is expected if using a dummy phone number")

        await connector.disconnect()
        print("\n" + "=" * 80)
        print("Diagnostics Complete!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nTroubleshooting steps:")
        print("1. Check if Matrix homeserver is running:")
        print(f"   curl {settings.MATRIX_HOMESERVER_URL}/_matrix/client/versions")
        print("\n2. Check if WhatsApp bridge is running:")
        print("   docker ps | grep whatsapp")
        print("\n3. Check bridge logs:")
        print("   docker logs syncline-whatsapp-bridge --tail 50")
        print("\n4. Verify your access token is valid")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_connection())
