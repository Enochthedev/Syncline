#!/usr/bin/env python3
"""
Quick AI status checker for MESH system.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def main():
    """Check AI status quickly."""
    try:
        from services.ai.detector import auto_configure_ai

        print("🤖 MESH AI Status Check")
        print("=" * 30)

        # Quick detection
        config_result = await auto_configure_ai()
        setup_info = config_result["setup_info"]
        providers = config_result["providers"]

        # Show status
        available_count = len([p for p in providers.values() if p.available])

        if available_count > 0:
            print(
                f"✅ AI Status: READY ({available_count} providers available)")

            # Show available providers
            for name, status in providers.items():
                if status.available:
                    location = "🏠" if status.local else "☁️"
                    print(f"   {location} {name.upper()}")
        else:
            print("❌ AI Status: NOT READY")
            print("   No AI providers available")

        # Show quick recommendations
        if setup_info["recommendations"]:
            print(f"\n💡 Quick Tips:")
            for rec in setup_info["recommendations"][:2]:  # Show first 2
                print(f"   {rec}")

        # Show setup commands if any
        if setup_info["setup_commands"]:
            print(f"\n🛠️  Quick Setup:")
            for cmd in setup_info["setup_commands"][:3]:  # Show first 3
                if not cmd.startswith("#"):
                    print(f"   $ {cmd}")

        print(f"\n💡 Run 'python scripts/setup_ai.py' for full setup")

    except Exception as e:
        print(f"❌ Error checking AI status: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
