"""
Migrate Existing Credentials to Encrypted Format

This script encrypts all existing platform connection credentials
that are currently stored in plain JSONB format.

Usage:
    python scripts/migrate_encrypt_credentials.py

The script is idempotent - safe to run multiple times.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from db.session import get_session
from db.models.platform_connection import PlatformConnection
from services.encryption_service import get_encryption_service


async def migrate_credentials():
    """
    Migrate all platform connections to use encrypted credentials.
    """
    print("=" * 80)
    print("Credential Encryption Migration")
    print("=" * 80)

    migrated_count = 0
    already_encrypted_count = 0
    error_count = 0

    async with get_session() as db:
        # Get all platform connections
        result = await db.execute(select(PlatformConnection))
        connections = result.scalars().all()

        total = len(connections)
        print(f"\nFound {total} platform connections")

        for i, connection in enumerate(connections, 1):
            print(f"\n[{i}/{total}] Processing connection {connection.id}")
            print(f"  Platform: {connection.platform}")
            print(f"  Status: {connection.status}")

            try:
                # Attempt migration
                was_migrated = connection.migrate_to_encrypted()

                if was_migrated:
                    print("  ✓ Migrated to encrypted format")
                    migrated_count += 1
                else:
                    print("  ⊙ Already using encrypted format")
                    already_encrypted_count += 1

            except Exception as e:
                print(f"  ✗ Migration failed: {e}")
                error_count += 1
                continue

        # Commit all changes
        if migrated_count > 0:
            print("\nCommitting changes...")
            await db.commit()
            print("✓ Changes committed successfully")
        else:
            print("\nNo changes to commit")

    # Summary
    print("\n" + "=" * 80)
    print("Migration Summary")
    print("=" * 80)
    print(f"Total connections: {total}")
    print(f"Migrated to encrypted: {migrated_count}")
    print(f"Already encrypted: {already_encrypted_count}")
    print(f"Errors: {error_count}")
    print("=" * 80)

    if error_count > 0:
        print("\n⚠️  Some connections failed to migrate. Check logs above.")
        return False
    else:
        print("\n✓ All credentials successfully encrypted!")
        return True


if __name__ == "__main__":
    success = asyncio.run(migrate_credentials())
    sys.exit(0 if success else 1)
