#!/usr/bin/env python3
"""
Test script for experimental platform connectors.

This script demonstrates the usage of experimental connectors and provides
a way to test their functionality without running the full test suite.
"""

from integrations.experimental import (
    ExperimentalFramework,
    TikTokConnector,
    SnapchatConnector,
    ExperimentalStatus
)
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_test_config() -> Dict[str, Any]:
    """Get test configuration for experimental connectors."""
    return {
        "experimental": {
            "mock_mode": True,
            "debug_mode": True,
            "api_timeout": 10,
            "max_retries": 2
        },
        # TikTok config
        "app_id": "test_tiktok_app_id",
        "app_secret": "test_tiktok_app_secret",
        "business_account": True,
        # Snapchat config
        "client_id": "test_snapchat_client_id",
        "client_secret": "test_snapchat_client_secret",
        "snap_kit_enabled": True,
        "redirect_uri": "https://example.com/callback"
    }


async def test_framework_basics():
    """Test basic framework functionality."""
    print("\n" + "="*60)
    print("TESTING EXPERIMENTAL FRAMEWORK BASICS")
    print("="*60)

    framework = ExperimentalFramework()

    try:
        # Test framework initialization
        print("\n1. Framework Initialization:")
        connectors = framework.get_available_connectors()
        print(f"   Available connectors: {list(connectors.keys())}")

        stats = framework.get_framework_statistics()
        print(f"   Framework stats: {stats}")

        # Test connector info
        print("\n2. Connector Information:")
        for platform in connectors:
            info = framework.get_connector_info(platform)
            print(f"   {platform}:")
            print(f"     Status: {info.status.value}")
            print(f"     Description: {info.description}")
            print(f"     Requirements: {len(info.requirements)} items")
            print(f"     Limitations: {len(info.limitations)} items")

        return True

    except Exception as e:
        logger.error(f"Framework basics test failed: {e}")
        return False

    finally:
        await framework.cleanup()


async def test_tiktok_connector():
    """Test TikTok experimental connector."""
    print("\n" + "="*60)
    print("TESTING TIKTOK EXPERIMENTAL CONNECTOR")
    print("="*60)

    config = get_test_config()
    connector = TikTokConnector(config)

    try:
        # Test initialization
        print("\n1. Connector Initialization:")
        print(f"   Platform: {connector.platform}")
        print(f"   Mock mode: {connector.mock_mode}")
        print(f"   Debug mode: {connector.debug_mode}")

        # Test capabilities
        print("\n2. Capabilities:")
        caps = connector.capabilities
        print(f"   Real-time ingestion: {caps.real_time_ingestion}")
        print(f"   Historical fetch: {caps.historical_fetch}")
        print(f"   Authentication: {caps.authentication}")
        print(f"   Mock mode: {caps.mock_mode}")
        print(f"   Media support: {caps.media_support}")

        # Test limitations
        print(f"\n3. Limitations ({len(connector.limitations)} items):")
        for i, limitation in enumerate(connector.limitations[:3], 1):
            print(f"   {i}. {limitation}")
        if len(connector.limitations) > 3:
            print(f"   ... and {len(connector.limitations) - 3} more")

        # Test mock authentication
        print("\n4. Mock Authentication:")
        await connector._authenticate_mock()
        print("   ✓ Mock authentication successful")

        # Test mock data generation
        print("\n5. Mock Data Generation:")
        messages = await connector._generate_mock_messages()
        print(f"   Generated {len(messages)} mock messages")

        if messages:
            sample = messages[0]
            print(f"   Sample message:")
            print(f"     ID: {sample.id}")
            print(f"     Platform: {sample.platform}")
            print(f"     Content type: {sample.metadata.get('content_type')}")
            print(f"     Mock: {sample.metadata.get('mock')}")

        # Test platform info
        print("\n6. Platform Information:")
        platform_info = await connector.get_platform_info()
        print(f"   Display name: {platform_info['display_name']}")
        print(f"   API status: {platform_info['api_status']}")
        print(
            f"   Supported features: {len(platform_info['supported_features'])}")
        print(
            f"   Unsupported features: {len(platform_info['unsupported_features'])}")

        # Test connection
        print("\n7. Connection Test:")
        test_results = await connector.test_connection()
        tests = test_results.get("tests", {})
        passed = sum(1 for t in tests.values() if t.get(
            "status") in ["passed", "expected_failure"])
        total = len(tests)
        print(f"   Tests passed: {passed}/{total}")

        # Test statistics
        print("\n8. Statistics:")
        stats = connector.get_statistics()
        print(f"   API call count: {stats['api_call_count']}")
        print(f"   Mock messages: {stats['mock_messages_count']}")
        print(f"   Debug logs: {stats['debug_logs_count']}")

        return True

    except Exception as e:
        logger.error(f"TikTok connector test failed: {e}")
        return False


async def test_snapchat_connector():
    """Test Snapchat experimental connector."""
    print("\n" + "="*60)
    print("TESTING SNAPCHAT EXPERIMENTAL CONNECTOR")
    print("="*60)

    config = get_test_config()
    connector = SnapchatConnector(config)

    try:
        # Test initialization
        print("\n1. Connector Initialization:")
        print(f"   Platform: {connector.platform}")
        print(f"   Snap Kit enabled: {connector.snap_kit_enabled}")
        print(f"   Mock mode: {connector.mock_mode}")

        # Test capabilities
        print("\n2. Capabilities:")
        caps = connector.capabilities
        print(f"   Authentication: {caps.authentication}")
        print(f"   Media support: {caps.media_support}")
        print(f"   Real-time ingestion: {caps.real_time_ingestion}")
        print(f"   Webhook support: {caps.webhook_support}")

        # Test mock data generation
        print("\n3. Mock Data Generation:")
        messages = await connector._generate_mock_messages()
        print(f"   Generated {len(messages)} mock messages")

        # Analyze content types
        content_types = {}
        ephemeral_count = 0
        for msg in messages:
            content_type = msg.metadata.get("content_type", "unknown")
            content_types[content_type] = content_types.get(
                content_type, 0) + 1
            if msg.metadata.get("privacy", {}).get("ephemeral"):
                ephemeral_count += 1

        print(f"   Content types: {dict(content_types)}")
        print(f"   Ephemeral messages: {ephemeral_count}/{len(messages)}")

        # Test snap interactions
        print("\n4. Snap Interactions:")
        interactions = ["view", "screenshot", "replay", "save"]
        for action in interactions:
            result = await connector.simulate_snap_interaction("test_snap_123", action)
            print(
                f"   {action}: {result['success']} - {result.get('note', 'OK')}")

        # Test platform info
        print("\n5. Platform Information:")
        platform_info = await connector.get_platform_info()
        print(f"   Display name: {platform_info['display_name']}")
        print(f"   API status: {platform_info['api_status']}")
        print(f"   Unique features: {len(platform_info['unique_features'])}")

        # Show some unique features
        for feature in platform_info['unique_features'][:3]:
            print(f"     - {feature}")

        # Test connection
        print("\n6. Connection Test:")
        test_results = await connector.test_connection()
        tests = test_results.get("tests", {})
        passed = sum(1 for t in tests.values() if t.get("status") in [
                     "passed", "expected_limitation", "simulated_success"])
        total = len(tests)
        print(f"   Tests passed: {passed}/{total}")

        return True

    except Exception as e:
        logger.error(f"Snapchat connector test failed: {e}")
        return False


async def test_framework_integration():
    """Test framework integration with connectors."""
    print("\n" + "="*60)
    print("TESTING FRAMEWORK INTEGRATION")
    print("="*60)

    framework = ExperimentalFramework()
    config = get_test_config()

    try:
        # Test connector creation through framework
        print("\n1. Connector Creation:")
        tiktok = await framework.create_connector("tiktok", config)
        snapchat = await framework.create_connector("snapchat", config)
        print(f"   Created TikTok connector: {tiktok.platform}")
        print(f"   Created Snapchat connector: {snapchat.platform}")

        # Test individual connector testing
        print("\n2. Individual Connector Testing:")
        tiktok_result = await framework.test_connector("tiktok", config)
        print(
            f"   TikTok: {tiktok_result.status} ({tiktok_result.tests_passed}/{tiktok_result.tests_total})")

        snapchat_result = await framework.test_connector("snapchat", config)
        print(
            f"   Snapchat: {snapchat_result.status} ({snapchat_result.tests_passed}/{snapchat_result.tests_total})")

        # Test all connectors at once
        print("\n3. All Connectors Testing:")
        all_results = await framework.test_all_connectors(config)
        for platform, result in all_results.items():
            print(
                f"   {platform}: {result.status} ({result.tests_passed}/{result.tests_total})")
            if result.errors:
                print(f"     Errors: {len(result.errors)}")

        # Test documentation generation
        print("\n4. Documentation Generation:")
        docs = await framework.generate_documentation()
        print(
            f"   Generated documentation for {len(docs['connectors'])} connectors")
        print(f"   Title: {docs['title']}")

        # Show connector documentation summary
        for platform, connector_doc in docs['connectors'].items():
            print(f"   {platform}:")
            print(f"     Status: {connector_doc['status']}")
            print(f"     Requirements: {len(connector_doc['requirements'])}")
            print(f"     Limitations: {len(connector_doc['limitations'])}")

        return True

    except Exception as e:
        logger.error(f"Framework integration test failed: {e}")
        return False

    finally:
        await framework.cleanup()


async def generate_sample_output():
    """Generate sample output files for documentation."""
    print("\n" + "="*60)
    print("GENERATING SAMPLE OUTPUT FILES")
    print("="*60)

    framework = ExperimentalFramework()
    config = get_test_config()

    try:
        # Generate documentation
        docs = await framework.generate_documentation()

        # Save documentation to file
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        docs_file = output_dir / "experimental_connectors_docs.json"
        with open(docs_file, 'w') as f:
            json.dump(docs, f, indent=2, default=str)
        print(f"   Documentation saved to: {docs_file}")

        # Generate test results
        test_results = await framework.test_all_connectors(config)

        results_file = output_dir / "experimental_test_results.json"
        with open(results_file, 'w') as f:
            # Convert test results to JSON-serializable format
            serializable_results = {}
            for platform, result in test_results.items():
                serializable_results[platform] = {
                    "platform": result.platform,
                    "status": result.status,
                    "timestamp": result.timestamp.isoformat(),
                    "tests_passed": result.tests_passed,
                    "tests_failed": result.tests_failed,
                    "tests_total": result.tests_total,
                    "details": result.details,
                    "errors": result.errors,
                    "warnings": result.warnings
                }
            json.dump(serializable_results, f, indent=2)
        print(f"   Test results saved to: {results_file}")

        # Generate sample mock data
        tiktok = await framework.create_connector("tiktok", config)
        snapchat = await framework.create_connector("snapchat", config)

        tiktok_messages = await tiktok._generate_mock_messages()
        snapchat_messages = await snapchat._generate_mock_messages()

        # Save sample messages
        sample_data = {
            "tiktok": [
                {
                    "id": msg.id,
                    "platform": msg.platform,
                    "content": msg.content,
                    "metadata": msg.metadata,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in tiktok_messages[:3]  # First 3 messages
            ],
            "snapchat": [
                {
                    "id": msg.id,
                    "platform": msg.platform,
                    "content": msg.content,
                    "metadata": msg.metadata,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in snapchat_messages[:3]  # First 3 messages
            ]
        }

        sample_file = output_dir / "experimental_sample_data.json"
        with open(sample_file, 'w') as f:
            json.dump(sample_data, f, indent=2, default=str)
        print(f"   Sample data saved to: {sample_file}")

        return True

    except Exception as e:
        logger.error(f"Sample output generation failed: {e}")
        return False

    finally:
        await framework.cleanup()


async def main():
    """Main test function."""
    print("EXPERIMENTAL CONNECTORS TEST SCRIPT")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")

    tests = [
        ("Framework Basics", test_framework_basics),
        ("TikTok Connector", test_tiktok_connector),
        ("Snapchat Connector", test_snapchat_connector),
        ("Framework Integration", test_framework_integration),
        ("Sample Output Generation", generate_sample_output),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        try:
            result = await test_func()
            results[test_name] = "PASSED" if result else "FAILED"
            print(f"Result: {results[test_name]}")
        except Exception as e:
            results[test_name] = f"ERROR: {e}"
            print(f"Result: {results[test_name]}")

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for r in results.values() if r == "PASSED")
    total = len(results)

    for test_name, result in results.items():
        status_symbol = "✓" if result == "PASSED" else "✗"
        print(f"{status_symbol} {test_name}: {result}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Experimental connectors are working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
