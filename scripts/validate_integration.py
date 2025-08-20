#!/usr/bin/env python3
"""
Simple validation script to test core system integration.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))


def test_imports():
    """Test that all core components can be imported."""
    print("Testing core imports...")

    try:
        # Test connector imports
        from integrations.yahoo_connector import YahooConnector, YahooCredentials
        from integrations.yahoo_factory import YahooConnectorFactory
        from integrations.gmail_connector import GmailConnector
        from integrations.slack_connector import SlackConnector
        from integrations.discord_connector import DiscordConnector
        print("✅ All connectors imported successfully")

        # Test service imports
        from services.message_normalizer import MessageNormalizer
        from services.message_schema import RawMessage, NormalizedMessage
        from services.event_bus import EventBus
        print("✅ Core services imported successfully")

        # Test AI imports
        from services.ai.engine import AIProcessingEngine
        from services.ai.embeddings import EmbeddingService
        print("✅ AI services imported successfully")

        # Test database imports
        from db.models.message import Message
        from db.models.thread import Thread
        from db.models.participant import Participant
        print("✅ Database models imported successfully")

        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_yahoo_connector():
    """Test Yahoo connector functionality."""
    print("\nTesting Yahoo connector...")

    try:
        from integrations.yahoo_connector import YahooConnector, YahooCredentials
        from unittest.mock import Mock

        # Create mock dependencies
        mock_event_bus = Mock()
        mock_settings = Mock()

        # Create credentials
        credentials = YahooCredentials(
            email="test@yahoo.com",
            app_password="test_password"
        )

        # Create connector
        connector = YahooConnector(credentials, mock_event_bus, mock_settings)

        # Test basic properties
        assert connector.platform == "yahoo"
        assert connector.credentials.email == "test@yahoo.com"
        assert connector.polling_interval == 30

        print("✅ Yahoo connector created successfully")
        return True

    except Exception as e:
        print(f"❌ Yahoo connector test failed: {e}")
        return False


def test_message_normalization():
    """Test message normalization."""
    print("\nTesting message normalization...")

    try:
        from services.message_normalizer import MessageNormalizer
        from services.message_schema import RawMessage, Platform
        from datetime import datetime

        # Create a test raw message
        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id="test_123",
            raw_data={
                "content": "Test message content",
                "sender": "test@yahoo.com",
                "timestamp": datetime.now().isoformat()
            }
        )

        # Test that normalizer can be created
        normalizer = MessageNormalizer()

        print("✅ Message normalization setup successful")
        return True

    except Exception as e:
        print(f"❌ Message normalization test failed: {e}")
        return False


def test_configuration():
    """Test configuration loading."""
    print("\nTesting configuration...")

    try:
        from config.config import Settings

        settings = Settings()

        # Test that basic settings exist (these should always be defined)
        assert hasattr(settings, 'DATABASE_URL')
        assert hasattr(settings, 'REDIS_URL')

        # These might not be set but should be defined as attributes
        assert hasattr(settings, 'YAHOO_EMAIL')
        assert hasattr(settings, 'YAHOO_APP_PASSWORD')

        print("✅ Configuration loaded successfully")
        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_env_example():
    """Test that .env.example file exists and has required variables."""
    print("\nTesting .env.example file...")

    try:
        env_example_path = Path(__file__).parent.parent / ".env.example"

        if not env_example_path.exists():
            print("❌ .env.example file not found")
            return False

        content = env_example_path.read_text()

        # Check for key configuration sections
        required_sections = [
            "DATABASE_URL",
            "REDIS_URL",
            "YAHOO_EMAIL",
            "YAHOO_APP_PASSWORD",
            "GMAIL_CLIENT_ID",
            "SLACK_CLIENT_ID",
            "DISCORD_BOT_TOKEN",
            "OLLAMA_BASE_URL",
            "DEFAULT_LLM_PROVIDER"
        ]

        missing_sections = []
        for section in required_sections:
            if section not in content:
                missing_sections.append(section)

        if missing_sections:
            print(f"❌ Missing sections in .env.example: {missing_sections}")
            return False

        print("✅ .env.example file is complete")
        return True

    except Exception as e:
        print(f"❌ .env.example test failed: {e}")
        return False


def test_documentation():
    """Test that documentation files exist."""
    print("\nTesting documentation...")

    try:
        docs_path = Path(__file__).parent.parent / "docs"

        required_docs = [
            "FRONTEND_GUIDE.md"
        ]

        missing_docs = []
        for doc in required_docs:
            if not (docs_path / doc).exists():
                missing_docs.append(doc)

        if missing_docs:
            print(f"❌ Missing documentation: {missing_docs}")
            return False

        print("✅ Documentation files exist")
        return True

    except Exception as e:
        print(f"❌ Documentation test failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("🚀 Starting R.E.M.I system integration validation...\n")

    tests = [
        ("Core Imports", test_imports),
        ("Yahoo Connector", test_yahoo_connector),
        ("Message Normalization", test_message_normalization),
        ("Configuration", test_configuration),
        ("Environment Example", test_env_example),
        ("Documentation", test_documentation)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        if test_func():
            passed += 1
        print()

    print("=" * 50)
    print(f"Validation Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All validation tests passed! System integration is ready.")
        return 0
    else:
        print("❌ Some validation tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
