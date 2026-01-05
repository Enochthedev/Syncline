#!/usr/bin/env python3
"""
Check WhatsApp Connections

Check which WhatsApp connections have proper credentials.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from db.session import get_db
from db.models.platform_connection import PlatformConnection, PlatformType


async def check_whatsapp_connections():
    """Check WhatsApp connections and their credentials."""
    print("🔍 Checking WhatsApp Connections")
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
            
            print(f"Found {len(connections)} WhatsApp connections:")
            print()
            
            for i, conn in enumerate(connections, 1):
                print(f"{i}. Connection ID: {conn.id}")
                print(f"   Status: {conn.status}")
                print(f"   User ID: {conn.user_id}")
                print(f"   Created: {conn.created_at}")
                
                if conn.credentials:
                    print(f"   Credentials keys: {list(conn.credentials.keys())}")
                    
                    # Check if it has Matrix credentials
                    has_matrix = all(key in conn.credentials for key in [
                        "matrix_homeserver_url", 
                        "matrix_access_token", 
                        "matrix_user_id"
                    ])
                    print(f"   Has Matrix credentials: {has_matrix}")
                    
                    if has_matrix:
                        print(f"   Matrix homeserver: {conn.credentials.get('matrix_homeserver_url')}")
                        print(f"   Matrix user: {conn.credentials.get('matrix_user_id')}")
                        print(f"   Bridge bot: {conn.credentials.get('bridge_bot_id', 'Not set')}")
                else:
                    print(f"   Credentials: EMPTY")
                
                print()
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        break


if __name__ == "__main__":
    asyncio.run(check_whatsapp_connections())