#!/usr/bin/env python3
"""
Cleanup WhatsApp Sessions

Clean up unused WhatsApp connections and sessions.
Keep only active connections with proper credentials.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, delete
from db.session import get_db
from db.models.platform_connection import PlatformConnection, PlatformType


async def cleanup_whatsapp_sessions():
    """Clean up unused WhatsApp sessions."""
    print("🧹 Cleaning Up WhatsApp Sessions")
    print("=" * 60)
    
    async for db in get_db():
        try:
            # Get all WhatsApp connections
            result = await db.execute(
                select(PlatformConnection).where(
                    PlatformConnection.platform == PlatformType.WHATSAPP
                )
            )
            connections = result.scalars().all()
            
            print(f"Found {len(connections)} WhatsApp connections")
            
            # Categorize connections
            active_with_creds = []
            active_without_creds = []
            inactive_with_creds = []
            inactive_without_creds = []
            
            for conn in connections:
                has_creds = bool(conn.credentials and 
                               conn.credentials.get("matrix_access_token") and
                               conn.credentials.get("matrix_user_id"))
                
                if conn.status.value == "ACTIVE":
                    if has_creds:
                        active_with_creds.append(conn)
                    else:
                        active_without_creds.append(conn)
                else:
                    if has_creds:
                        inactive_with_creds.append(conn)
                    else:
                        inactive_without_creds.append(conn)
            
            print(f"\nConnection Analysis:")
            print(f"  Active with credentials: {len(active_with_creds)}")
            print(f"  Active without credentials: {len(active_without_creds)}")
            print(f"  Inactive with credentials: {len(inactive_with_creds)}")
            print(f"  Inactive without credentials: {len(inactive_without_creds)}")
            
            # Keep active connections with credentials
            print(f"\n✅ Keeping {len(active_with_creds)} active connections with credentials:")
            for conn in active_with_creds:
                print(f"  - {conn.id} (Created: {conn.created_at})")
            
            # Delete connections to clean up
            to_delete = []
            
            # Delete active connections without credentials (broken)
            to_delete.extend(active_without_creds)
            print(f"\n🗑️  Deleting {len(active_without_creds)} active connections without credentials")
            
            # Delete old inactive connections (keep recent ones as backup)
            cutoff_date = datetime.utcnow() - timedelta(days=1)
            old_inactive = [c for c in inactive_with_creds + inactive_without_creds 
                           if c.created_at < cutoff_date]
            to_delete.extend(old_inactive)
            print(f"🗑️  Deleting {len(old_inactive)} old inactive connections (>1 day old)")
            
            # Keep recent inactive connections with credentials as backup
            recent_inactive_with_creds = [c for c in inactive_with_creds 
                                        if c.created_at >= cutoff_date]
            print(f"💾 Keeping {len(recent_inactive_with_creds)} recent inactive connections with credentials as backup")
            
            # Perform deletions
            if to_delete:
                print(f"\n🗑️  Deleting {len(to_delete)} connections...")
                for conn in to_delete:
                    print(f"  - Deleting {conn.id} (Status: {conn.status}, Created: {conn.created_at})")
                    await db.delete(conn)
                
                await db.commit()
                print(f"✅ Deleted {len(to_delete)} connections")
            else:
                print("\n✅ No connections to delete")
            
            # Final summary
            remaining_result = await db.execute(
                select(PlatformConnection).where(
                    PlatformConnection.platform == PlatformType.WHATSAPP
                )
            )
            remaining = remaining_result.scalars().all()
            
            print(f"\n📊 Final Summary:")
            print(f"  Total remaining connections: {len(remaining)}")
            
            active_remaining = [c for c in remaining if c.status.value == "ACTIVE"]
            print(f"  Active connections: {len(active_remaining)}")
            
            for conn in active_remaining:
                has_creds = bool(conn.credentials and conn.credentials.get("matrix_access_token"))
                print(f"    - {conn.id} (Credentials: {'✅' if has_creds else '❌'})")
            
            return {
                "deleted": len(to_delete),
                "remaining": len(remaining),
                "active": len(active_remaining)
            }
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        break


if __name__ == "__main__":
    result = asyncio.run(cleanup_whatsapp_sessions())
    if result:
        print(f"\n🎉 Cleanup completed!")
        print(f"   Deleted: {result['deleted']} connections")
        print(f"   Remaining: {result['remaining']} connections")
        print(f"   Active: {result['active']} connections")