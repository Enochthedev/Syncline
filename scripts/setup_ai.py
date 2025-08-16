#!/usr/bin/env python3
"""
AI Setup Utility for MESH Ingestion System

This script helps users set up AI providers (local and/or cloud) for the MESH system.
It detects available providers, recommends models, and provides setup instructions.
"""

from services.ai.providers import OllamaProvider
from services.ai.detector import get_ai_detector, auto_configure_ai
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def main():
    """Main setup function."""
    print("🤖 MESH AI Setup Utility")
    print("=" * 50)

    # Auto-detect and configure AI providers
    print("🔍 Detecting available AI providers...")
    config_result = await auto_configure_ai()

    setup_info = config_result["setup_info"]
    providers = config_result["providers"]

    print(f"\n📊 Detection Results:")
    print(f"   Local providers available: {setup_info['local_available']}")
    print(f"   API providers available: {setup_info['api_available']}")
    print(
        f"   Total providers detected: {len([p for p in providers.values() if p.available])}")

    # Show available providers
    print(f"\n✅ Available Providers:")
    for name, status in providers.items():
        if status.available:
            location = "🏠 Local" if status.local else "☁️  Cloud"
            latency = f" ({status.latency_ms:.0f}ms)" if status.latency_ms else ""
            models_count = f" - {len(status.models)} models" if status.models else ""
            print(f"   {location} {name.upper()}{latency}{models_count}")

    # Show unavailable providers with reasons
    unavailable = [(name, status)
                   for name, status in providers.items() if not status.available]
    if unavailable:
        print(f"\n❌ Unavailable Providers:")
        for name, status in unavailable:
            print(f"   {name.upper()}: {status.error}")

    # Show recommendations
    print(f"\n💡 Recommendations:")
    for rec in setup_info["recommendations"]:
        print(f"   {rec}")

    # Show setup commands if needed
    if setup_info["setup_commands"]:
        print(f"\n🛠️  Setup Commands:")
        for cmd in setup_info["setup_commands"]:
            if cmd.startswith("#"):
                print(f"   {cmd}")
            else:
                print(f"   $ {cmd}")

    # Show missing models for Ollama
    if setup_info["missing_models"]:
        print(f"\n📦 Missing Ollama Models:")
        for model in setup_info["missing_models"]:
            print(f"   - {model}")

        print(f"\n   Run these commands to install missing models:")
        for model in setup_info["missing_models"]:
            print(f"   $ ollama pull {model}")

    # Interactive setup
    print(f"\n🚀 Quick Setup Options:")
    print("   1. Set up local AI (Ollama) - Recommended for privacy")
    print("   2. Configure OpenAI API - Full-featured cloud AI")
    print("   3. Configure Anthropic Claude API - Alternative cloud AI")
    print("   4. Show current configuration")
    print("   5. Test AI functionality")
    print("   0. Exit")

    while True:
        try:
            choice = input("\nSelect an option (0-5): ").strip()

            if choice == "0":
                print("👋 Goodbye!")
                break
            elif choice == "1":
                await setup_ollama()
            elif choice == "2":
                setup_openai()
            elif choice == "3":
                setup_anthropic()
            elif choice == "4":
                show_current_config()
            elif choice == "5":
                await test_ai_functionality()
            else:
                print("❌ Invalid choice. Please select 0-5.")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def setup_ollama():
    """Set up Ollama local AI."""
    print("\n🏠 Setting up Ollama (Local AI)")
    print("-" * 30)

    # Check if Ollama is installed
    detector = await get_ai_detector()
    await detector.detect_all_providers()
    ollama_status = detector.providers.get("ollama")

    if not ollama_status or not ollama_status.available:
        print("❌ Ollama is not running or not installed.")
        print("\n📥 Installation steps:")
        print("   1. Visit: https://ollama.ai/download")
        print("   2. Download and install Ollama for your OS")
        print("   3. Start Ollama (it should run automatically)")
        print("   4. Come back and run this setup again")
        return

    print("✅ Ollama is running!")
    print(f"   Available models: {len(ollama_status.models)}")

    # Recommend models to install
    recommended_models = {
        "llama3.2:1b": "Fast, lightweight model (1GB) - Good for basic tasks",
        "llama3.2:3b": "Balanced model (2GB) - Recommended for most tasks",
        "qwen2.5:7b": "High-quality model (4GB) - Best results, slower",
        "nomic-embed-text": "Embedding model (274MB) - Required for semantic search"
    }

    print(f"\n📦 Recommended models:")
    for model, description in recommended_models.items():
        installed = "✅" if model in ollama_status.models else "⬜"
        print(f"   {installed} {model} - {description}")

    # Ask which models to install
    missing_models = [model for model in recommended_models.keys(
    ) if model not in ollama_status.models]

    if missing_models:
        print(f"\n🔄 Install missing models? (y/n): ", end="")
        if input().lower().startswith('y'):
            provider = OllamaProvider()
            for model in missing_models:
                print(f"📥 Pulling {model}...")
                success = await provider.pull_model(model)
                if success:
                    print(f"✅ {model} installed successfully")
                else:
                    print(f"❌ Failed to install {model}")
            await provider.close()

    print(f"\n🎉 Ollama setup complete!")


def setup_openai():
    """Set up OpenAI API."""
    print("\n☁️  Setting up OpenAI API")
    print("-" * 25)

    print("🔑 You'll need an OpenAI API key:")
    print("   1. Visit: https://platform.openai.com/api-keys")
    print("   2. Create a new API key")
    print("   3. Copy the key")

    api_key = input(
        "\n🔐 Enter your OpenAI API key (or press Enter to skip): ").strip()

    if api_key:
        # Update .env file
        env_path = project_root / ".env"
        update_env_file(env_path, "OPENAI_API_KEY", api_key)
        print("✅ OpenAI API key saved to .env file")
        print("🔄 Restart the application to use the new key")
    else:
        print("⏭️  Skipped OpenAI setup")


def setup_anthropic():
    """Set up Anthropic Claude API."""
    print("\n☁️  Setting up Anthropic Claude API")
    print("-" * 32)

    print("🔑 You'll need an Anthropic API key:")
    print("   1. Visit: https://console.anthropic.com/")
    print("   2. Create a new API key")
    print("   3. Copy the key")

    api_key = input(
        "\n🔐 Enter your Anthropic API key (or press Enter to skip): ").strip()

    if api_key:
        # Update .env file
        env_path = project_root / ".env"
        update_env_file(env_path, "ANTHROPIC_API_KEY", api_key)
        print("✅ Anthropic API key saved to .env file")
        print("🔄 Restart the application to use the new key")
    else:
        print("⏭️  Skipped Anthropic setup")


def show_current_config():
    """Show current AI configuration."""
    print("\n⚙️  Current AI Configuration")
    print("-" * 28)

    # Read current .env file
    env_path = project_root / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            content = f.read()

        # Extract AI-related settings
        ai_settings = {}
        for line in content.split('\n'):
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                if any(ai_key in key for ai_key in ['AI_', 'LLM_', 'OPENAI_', 'ANTHROPIC_', 'OLLAMA_']):
                    # Mask API keys
                    if 'API_KEY' in key and value and not value.startswith('your_'):
                        value = value[:8] + "..." + \
                            value[-4:] if len(value) > 12 else "***"
                    ai_settings[key] = value

        for key, value in ai_settings.items():
            print(f"   {key}: {value}")
    else:
        print("   ❌ No .env file found")


async def test_ai_functionality():
    """Test AI functionality."""
    print("\n🧪 Testing AI Functionality")
    print("-" * 25)

    try:
        from services.ai.engine import get_ai_processing_engine

        print("🔄 Initializing AI engine...")
        engine = await get_ai_processing_engine()

        print("🧪 Running health check...")
        health = await engine.health_check()

        if health['status'] == 'healthy':
            print("✅ AI engine is healthy!")
            print(f"   Provider: {health['provider']}")
            print(f"   Chat model: {health['models']['chat']}")
            print(f"   Embedding model: {health['models']['embedding']}")
            print(
                f"   Test processing time: {health['test_processing_time']:.2f}s")
        else:
            print("❌ AI engine is not healthy")
            print(f"   Error: {health.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Test failed: {e}")


def update_env_file(env_path: Path, key: str, value: str):
    """Update a key in the .env file."""
    if env_path.exists():
        with open(env_path, 'r') as f:
            lines = f.readlines()
    else:
        lines = []

    # Find and update the key, or add it
    key_found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            key_found = True
            break

    if not key_found:
        lines.append(f"{key}={value}\n")

    # Write back to file
    with open(env_path, 'w') as f:
        f.writelines(lines)


if __name__ == "__main__":
    asyncio.run(main())
