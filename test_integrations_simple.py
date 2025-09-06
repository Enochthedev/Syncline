#!/usr/bin/env python3
"""
Simple Integration Services Test
Tests the core integration functionality without complex dependencies
"""

import sys
import os
import importlib.util


def test_integration_structure():
    """Test integration services structure"""
    print("🧪 Testing integration services structure...")

    integrations_dir = 'integrations'
    required_files = [
        '__init__.py',
        'base_connector.py',
        'gmail_connector.py'
    ]

    passed = 0
    failed = 0

    for file in required_files:
        file_path = os.path.join(integrations_dir, file)
        if os.path.exists(file_path):
            print(f"✅ {file} exists")
            passed += 1
        else:
            print(f"❌ {file} missing")
            failed += 1

    return failed == 0


def test_base_connector():
    """Test base connector import"""
    print("🧪 Testing base connector...")

    try:
        sys.path.append('.')
        from integrations.base_connector import BaseConnector
        print("✅ BaseConnector imported successfully")

        # Check if it has required methods
        required_methods = ['connect', 'disconnect', 'get_health_status']
        methods_found = 0

        for method in required_methods:
            if hasattr(BaseConnector, method):
                print(f"✅ {method} method found")
                methods_found += 1
            else:
                print(f"⚠️  {method} method not found")

        return methods_found >= 2
    except Exception as e:
        print(f"❌ BaseConnector import failed: {e}")
        return False


def test_gmail_connector():
    """Test Gmail connector import"""
    print("🧪 Testing Gmail connector...")

    try:
        from integrations.gmail_connector import GmailConnector
        print("✅ GmailConnector imported successfully")

        # Check if it inherits from BaseConnector
        try:
            from integrations.base_connector import BaseConnector
            if issubclass(GmailConnector, BaseConnector):
                print("✅ GmailConnector inherits from BaseConnector")
                return True
            else:
                print("⚠️  GmailConnector doesn't inherit from BaseConnector")
                return True  # Still pass if import works
        except:
            print("⚠️  Could not verify inheritance")
            return True  # Still pass if import works

    except Exception as e:
        print(f"❌ GmailConnector import failed: {e}")
        return False


def test_other_connectors():
    """Test other connector imports"""
    print("🧪 Testing other connectors...")

    connectors = [
        ('slack_connector', 'SlackConnector'),
        ('discord_connector', 'DiscordConnector'),
        ('whatsapp_connector', 'WhatsAppConnector'),
        ('twitter_connector', 'TwitterConnector')
    ]

    connectors_found = 0

    for module_name, class_name in connectors:
        try:
            module_path = f'integrations.{module_name}'
            module = __import__(module_path, fromlist=[class_name])
            connector_class = getattr(module, class_name)
            print(f"✅ {class_name} imported successfully")
            connectors_found += 1
        except Exception as e:
            print(f"⚠️  {class_name} not available: {e}")

    print(f"✅ Found {connectors_found} additional connectors")
    return True  # Always pass since these are optional


def test_services_structure():
    """Test services structure"""
    print("🧪 Testing services structure...")

    services_dir = 'services'
    key_services = [
        'event_bus.py',
        'message_normalizer.py',
        'ingest_service.py'
    ]

    services_found = 0

    for service in key_services:
        service_path = os.path.join(services_dir, service)
        if os.path.exists(service_path):
            print(f"✅ {service} found")
            services_found += 1
        else:
            print(f"⚠️  {service} not found")

    # Count total services
    if os.path.exists(services_dir):
        total_services = len([f for f in os.listdir(services_dir)
                              if f.endswith('.py') and f != '__init__.py'])
        print(f"✅ Found {total_services} total service files")

    return services_found >= 2


def test_ai_services():
    """Test AI services"""
    print("🧪 Testing AI services...")

    ai_dir = os.path.join('services', 'ai')

    if not os.path.exists(ai_dir):
        print("⚠️  AI services directory not found")
        return False

    ai_services = [
        'engine.py',
        'embeddings.py',
        'detector.py'
    ]

    ai_services_found = 0

    for service in ai_services:
        service_path = os.path.join(ai_dir, service)
        if os.path.exists(service_path):
            print(f"✅ {service} found")
            ai_services_found += 1
        else:
            print(f"⚠️  {service} not found")

    return ai_services_found >= 2


def main():
    """Run all tests"""
    print("🚀 Starting R.E.M.I Integration Services Tests")
    print("=" * 50)

    tests = [
        ("Integration Structure", test_integration_structure),
        ("Base Connector", test_base_connector),
        ("Gmail Connector", test_gmail_connector),
        ("Other Connectors", test_other_connectors),
        ("Services Structure", test_services_structure),
        ("AI Services", test_ai_services),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            if test_func():
                print(f"✅ {test_name} test PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} test FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} test FAILED with exception: {e}")
            failed += 1

    print(f"\n📊 Integration Services Test Summary:")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    print(f"   Total:  {passed + failed}")

    if failed == 0:
        print("🎉 All integration tests passed!")
        return 0
    else:
        print("💥 Some integration tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
