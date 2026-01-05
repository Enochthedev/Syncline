"""
Test Script for Phase 1 Security Features

Tests:
1. Encryption service (encrypt/decrypt)
2. Credential rotation
3. Connector cache
4. Config validators
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.encryption_service import get_encryption_service
from services.connector_cache import get_connector_cache
from config.config import settings


def test_encryption_service():
    """Test encryption and decryption of credentials."""
    print("\n" + "=" * 80)
    print("TEST 1: Encryption Service")
    print("=" * 80)

    service = get_encryption_service()

    # Test data
    test_credentials = {
        "access_token": "super_secret_token_123",
        "refresh_token": "refresh_token_456",
        "expires_at": "2025-12-31T23:59:59Z",
        "api_key": "sk-1234567890abcdef"
    }

    print("\n[1] Original credentials:")
    print(f"  access_token: {test_credentials['access_token']}")
    print(f"  refresh_token: {test_credentials['refresh_token']}")

    # Encrypt
    print("\n[2] Encrypting credentials...")
    encrypted = service.encrypt_credentials(test_credentials)
    print(f"  Encrypted length: {len(encrypted)} bytes")
    print(f"  Encrypted preview: {encrypted[:50]}...")

    # Verify it's actually encrypted (not plain JSON)
    assert "super_secret_token" not in encrypted, "❌ Credentials not encrypted!"
    print("  ✓ Credentials are encrypted (not plaintext)")

    # Decrypt
    print("\n[3] Decrypting credentials...")
    decrypted = service.decrypt_credentials(encrypted)
    print(f"  Decrypted: {decrypted}")

    # Verify
    assert decrypted == test_credentials, "❌ Decryption failed!"
    print("  ✓ Decryption successful - matches original")

    # Test single value encryption
    print("\n[4] Testing single value encryption...")
    secret = "my_secret_value_xyz"
    encrypted_value = service.encrypt_value(secret)
    decrypted_value = service.decrypt_value(encrypted_value)

    assert decrypted_value == secret, "❌ Value decryption failed!"
    print(f"  ✓ Single value encryption/decryption works")

    print("\n✅ Encryption Service: PASSED")
    return True


async def test_credential_rotation():
    """Test credential rotation tracking (simplified - logic only)."""
    print("\n" + "=" * 80)
    print("TEST 2: Credential Rotation")
    print("=" * 80)

    from db.models.platform_connection import PlatformConnection, PlatformType, ConnectionStatus
    from datetime import datetime, timedelta, timezone

    # Test rotation logic without database
    print("\n[1] Creating mock connection object...")

    # Simulate a connection with initial state
    test_conn = PlatformConnection.__new__(PlatformConnection)
    test_conn.id = uuid4()
    test_conn.platform = PlatformType.WHATSAPP
    test_conn.status = ConnectionStatus.INACTIVE
    test_conn._credentials_encrypted = None
    test_conn._credentials_legacy = None
    test_conn.credentials_version = "v1"
    test_conn.credentials_rotated_at = None
    test_conn.created_at = datetime.now(timezone.utc) - timedelta(days=100)  # Old connection

    print(f"  ✓ Mock connection created")
    print(f"  Initial version: {test_conn.credentials_version}")
    print(f"  Initial rotated_at: {test_conn.credentials_rotated_at}")

    # Test setting credentials
    print("\n[2] Setting initial credentials...")
    test_conn.credentials = {
        "access_token": "initial_token_123",
        "refresh_token": "initial_refresh_456"
    }

    # Verify encryption happened
    assert test_conn._credentials_encrypted is not None, "❌ Credentials not encrypted!"
    assert test_conn._credentials_legacy is None, "❌ Legacy credentials should be None!"
    print(f"  ✓ Credentials encrypted (length: {len(test_conn._credentials_encrypted)} bytes)")

    # Verify decryption works
    creds = test_conn.credentials
    assert creds["access_token"] == "initial_token_123", "❌ Decryption failed!"
    print(f"  ✓ Credentials decryption works")

    # Test rotation
    print("\n[3] Rotating credentials...")
    test_conn.rotate_credentials({
        "access_token": "new_token_789",
        "refresh_token": "new_refresh_xyz"
    })

    print(f"  ✓ Credentials rotated")
    print(f"  New version: {test_conn.credentials_version}")
    print(f"  Rotated at: {test_conn.credentials_rotated_at}")

    assert test_conn.credentials_version == "v2", "❌ Version not incremented!"
    assert test_conn.credentials_rotated_at is not None, "❌ Rotation timestamp not set!"

    # Verify new decrypted credentials
    creds = test_conn.credentials
    assert creds["access_token"] == "new_token_789", "❌ Credentials not updated!"
    print(f"  ✓ New credentials: {creds['access_token']}")

    # Test needs_rotation
    print("\n[4] Testing rotation age check...")
    needs_rotation_new = test_conn.needs_rotation(max_age_days=0)  # Just rotated
    needs_rotation_old = test_conn.needs_rotation(max_age_days=365)  # Not old enough

    print(f"  Needs rotation (0 days): {needs_rotation_new}")
    print(f"  Needs rotation (365 days): {needs_rotation_old}")

    print("\n✅ Credential Rotation: PASSED")
    return True


async def test_connector_cache():
    """Test connector cache lifecycle."""
    print("\n" + "=" * 80)
    print("TEST 3: Connector Cache")
    print("=" * 80)

    cache = get_connector_cache()

    print("\n[1] Starting cache...")
    await cache.start()
    print("  ✓ Cache started")

    # Get cache stats
    print("\n[2] Checking initial stats...")
    stats = cache.get_stats()
    print(f"  Size: {stats['size']}/{stats['max_size']}")
    print(f"  Utilization: {stats['utilization']:.1%}")
    print(f"  Default TTL: {stats['default_ttl']} seconds")

    # Test manual operations (without creating actual connectors)
    print("\n[3] Testing cache operations...")
    test_conn_id = uuid4()

    # Check get on non-existent
    connector = await cache.get(test_conn_id)
    assert connector is None, "❌ Should return None for non-existent connector"
    print("  ✓ Get non-existent returns None")

    # Test invalidate
    invalidated = await cache.invalidate(test_conn_id)
    assert not invalidated, "❌ Should return False for non-existent connector"
    print("  ✓ Invalidate non-existent returns False")

    print("\n[4] Stopping cache...")
    await cache.stop()
    print("  ✓ Cache stopped")

    print("\n✅ Connector Cache: PASSED")
    return True


def test_config_validators():
    """Test configuration validators."""
    print("\n" + "=" * 80)
    print("TEST 4: Config Validators")
    print("=" * 80)

    # Test that settings loaded successfully
    print("\n[1] Checking settings loaded...")
    print(f"  Environment: {settings.ENV}")
    print(f"  Debug: {settings.DEBUG}")
    print(f"  Database: {settings.DATABASE_URL[:30]}...")
    print(f"  Log level: {settings.LOG_LEVEL}")

    # Verify validators worked
    print("\n[2] Verifying validators...")

    # SECRET_KEY should be at least 32 chars
    assert len(settings.SECRET_KEY) >= 32, "❌ SECRET_KEY too short!"
    print(f"  ✓ SECRET_KEY length: {len(settings.SECRET_KEY)} chars")

    # JWT_SECRET_KEY should be at least 32 chars
    assert len(settings.JWT_SECRET_KEY) >= 32, "❌ JWT_SECRET_KEY too short!"
    print(f"  ✓ JWT_SECRET_KEY length: {len(settings.JWT_SECRET_KEY)} chars")

    # DATABASE_URL should start with postgresql
    assert settings.DATABASE_URL.startswith("postgresql"), "❌ Invalid DATABASE_URL!"
    print(f"  ✓ DATABASE_URL format valid")

    # LOG_LEVEL should be uppercase
    assert settings.LOG_LEVEL.isupper(), "❌ LOG_LEVEL not normalized!"
    print(f"  ✓ LOG_LEVEL normalized: {settings.LOG_LEVEL}")

    # MATRIX_USER_ID format (if set)
    if settings.MATRIX_USER_ID:
        assert settings.MATRIX_USER_ID.startswith("@"), "❌ MATRIX_USER_ID invalid!"
        assert ":" in settings.MATRIX_USER_ID, "❌ MATRIX_USER_ID missing domain!"
        print(f"  ✓ MATRIX_USER_ID format valid: {settings.MATRIX_USER_ID}")

    print("\n✅ Config Validators: PASSED")
    return True


async def run_all_tests():
    """Run all Phase 1 tests."""
    print("\n" + "=" * 80)
    print("PHASE 1 SECURITY FEATURES - COMPREHENSIVE TEST SUITE")
    print("=" * 80)

    results = {}

    # Test 1: Encryption Service
    try:
        results["encryption"] = test_encryption_service()
    except Exception as e:
        print(f"\n❌ Encryption Service: FAILED - {e}")
        results["encryption"] = False

    # Test 2: Credential Rotation
    try:
        results["rotation"] = await test_credential_rotation()
    except Exception as e:
        print(f"\n❌ Credential Rotation: FAILED - {e}")
        import traceback
        traceback.print_exc()
        results["rotation"] = False

    # Test 3: Connector Cache
    try:
        results["cache"] = await test_connector_cache()
    except Exception as e:
        print(f"\n❌ Connector Cache: FAILED - {e}")
        results["cache"] = False

    # Test 4: Config Validators
    try:
        results["validators"] = test_config_validators()
    except Exception as e:
        print(f"\n❌ Config Validators: FAILED - {e}")
        results["validators"] = False

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name.title():20} {status}")

    print("\n" + "=" * 80)
    print(f"OVERALL: {passed}/{total} tests passed")
    print("=" * 80)

    return all(results.values())


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
