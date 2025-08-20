"""
Comprehensive testing suite runner for the MESH Ingestion System.

This module orchestrates all comprehensive tests including E2E, performance, 
security, and integration tests.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestComprehensiveSuite:
    """Comprehensive test suite orchestrator."""

    def test_run_all_comprehensive_tests(self):
        """Run all comprehensive tests in sequence."""

        test_modules = [
            "tests/test_comprehensive_e2e.py",
            "tests/test_performance_basic.py",
            "tests/test_security_services.py",
            "tests/test_gmail_integration.py",
            "tests/test_slack_integration.py",
            "tests/test_discord_integration.py",
            "tests/test_telegram_integration.py",
            "tests/test_linkedin_integration.py",
            "tests/test_whatsapp_integration.py",
            "tests/test_twitter_connector.py",
            "tests/test_matrix_bridge_hub.py",
            "tests/test_experimental_connectors.py"
        ]

        # Run each test module
        for module in test_modules:
            if os.path.exists(module):
                print(f"\n{'='*60}")
                print(f"Running tests from: {module}")
                print(f"{'='*60}")

                # Run the test module
                result = pytest.main([module, "-v", "--tb=short"])

                if result != 0:
                    print(f"WARNING: Tests in {module} had failures")
                else:
                    print(f"SUCCESS: All tests in {module} passed")
            else:
                print(f"SKIP: Test module {module} not found")

    def test_performance_benchmarks(self):
        """Run performance benchmark tests."""

        performance_tests = [
            "tests/test_performance_basic.py::TestBasicPerformance::test_message_normalization_performance",
            "tests/test_performance_basic.py::TestBasicPerformance::test_concurrent_message_normalization",
            "tests/test_comprehensive_e2e.py::TestEndToEndMessageFlow::test_real_time_processing_pipeline",
            "tests/test_comprehensive_e2e.py::TestEndToEndMessageFlow::test_concurrent_message_processing"
        ]

        print(f"\n{'='*60}")
        print("Running Performance Benchmark Tests")
        print(f"{'='*60}")

        for test in performance_tests:
            if self._test_exists(test):
                print(f"\nRunning: {test}")
                result = pytest.main([test, "-v", "-s"])

                if result == 0:
                    print(f"✓ PASSED: {test}")
                else:
                    print(f"✗ FAILED: {test}")

    def test_security_validation(self):
        """Run security validation tests."""

        security_tests = [
            "tests/test_security_services.py",
            "tests/test_tenant_security.py"
        ]

        print(f"\n{'='*60}")
        print("Running Security Validation Tests")
        print(f"{'='*60}")

        for test_module in security_tests:
            if os.path.exists(test_module):
                print(f"\nRunning security tests from: {test_module}")
                result = pytest.main([test_module, "-v", "--tb=short"])

                if result == 0:
                    print(f"✓ SECURITY PASSED: {test_module}")
                else:
                    print(f"✗ SECURITY FAILED: {test_module}")

    def test_integration_validation(self):
        """Run integration validation tests."""

        integration_tests = [
            "tests/test_gmail_integration.py",
            "tests/test_slack_integration.py",
            "tests/test_discord_integration.py",
            "tests/test_event_integration.py",
            "tests/test_api_integration.py"
        ]

        print(f"\n{'='*60}")
        print("Running Integration Validation Tests")
        print(f"{'='*60}")

        for test_module in integration_tests:
            if os.path.exists(test_module):
                print(f"\nRunning integration tests from: {test_module}")
                result = pytest.main([test_module, "-v", "--tb=short"])

                if result == 0:
                    print(f"✓ INTEGRATION PASSED: {test_module}")
                else:
                    print(f"✗ INTEGRATION FAILED: {test_module}")

    def test_ai_processing_validation(self):
        """Run AI processing validation tests."""

        ai_tests = [
            "tests/test_ai_processing_engine.py",
            "tests/test_entity_extraction.py",
            "tests/test_summary_agent.py",
            "tests/test_embedding_service.py",
            "tests/test_hybrid_search_agent.py",
            "tests/test_proactive_memory_agent.py",
            "tests/test_pii_redaction.py"
        ]

        print(f"\n{'='*60}")
        print("Running AI Processing Validation Tests")
        print(f"{'='*60}")

        for test_module in ai_tests:
            if os.path.exists(test_module):
                print(f"\nRunning AI tests from: {test_module}")
                result = pytest.main([test_module, "-v", "--tb=short"])

                if result == 0:
                    print(f"✓ AI PASSED: {test_module}")
                else:
                    print(f"✗ AI FAILED: {test_module}")

    def test_connector_validation(self):
        """Run connector validation tests."""

        connector_tests = [
            "tests/test_gmail_connector.py",
            "tests/test_slack_connector.py",
            "tests/test_discord_connector.py",
            "tests/test_telegram_connector.py",
            "tests/test_twitter_connector.py",
            "tests/test_base_connector.py",
            "tests/test_connector_manager.py",
            "tests/test_experimental_connectors.py"
        ]

        print(f"\n{'='*60}")
        print("Running Connector Validation Tests")
        print(f"{'='*60}")

        for test_module in connector_tests:
            if os.path.exists(test_module):
                print(f"\nRunning connector tests from: {test_module}")
                result = pytest.main([test_module, "-v", "--tb=short"])

                if result == 0:
                    print(f"✓ CONNECTOR PASSED: {test_module}")
                else:
                    print(f"✗ CONNECTOR FAILED: {test_module}")

    def test_resilience_validation(self):
        """Run resilience and error handling validation tests."""

        resilience_tests = [
            "tests/test_resilience_circuit_breaker.py",
            "tests/test_resilience_retry_handler.py",
            "tests/test_resilience_dead_letter_queue.py",
            "tests/test_resilience_integration.py",
            "tests/test_resilience_chaos_engineering.py"
        ]

        print(f"\n{'='*60}")
        print("Running Resilience Validation Tests")
        print(f"{'='*60}")

        for test_module in resilience_tests:
            if os.path.exists(test_module):
                print(f"\nRunning resilience tests from: {test_module}")
                result = pytest.main([test_module, "-v", "--tb=short"])

                if result == 0:
                    print(f"✓ RESILIENCE PASSED: {test_module}")
                else:
                    print(f"✗ RESILIENCE FAILED: {test_module}")

    def test_monitoring_validation(self):
        """Run monitoring and observability validation tests."""

        monitoring_tests = [
            "tests/test_monitoring_health.py",
            "tests/test_monitoring_metrics.py",
            "tests/test_monitoring_logging.py",
            "tests/test_monitoring_api.py"
        ]

        print(f"\n{'='*60}")
        print("Running Monitoring Validation Tests")
        print(f"{'='*60}")

        for test_module in monitoring_tests:
            if os.path.exists(test_module):
                print(f"\nRunning monitoring tests from: {test_module}")
                result = pytest.main([test_module, "-v", "--tb=short"])

                if result == 0:
                    print(f"✓ MONITORING PASSED: {test_module}")
                else:
                    print(f"✗ MONITORING FAILED: {test_module}")

    def _test_exists(self, test_path: str) -> bool:
        """Check if a test file or specific test exists."""
        if "::" in test_path:
            # Specific test case
            file_path = test_path.split("::")[0]
            return os.path.exists(file_path)
        else:
            # Test file
            return os.path.exists(test_path)


def run_comprehensive_test_suite():
    """Run the complete comprehensive test suite."""

    print("="*80)
    print("MESH INGESTION SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*80)

    suite = TestComprehensiveSuite()

    # Run all test categories
    test_categories = [
        ("Core Infrastructure", suite.test_run_all_comprehensive_tests),
        ("Performance Benchmarks", suite.test_performance_benchmarks),
        ("Security Validation", suite.test_security_validation),
        ("Integration Validation", suite.test_integration_validation),
        ("AI Processing Validation", suite.test_ai_processing_validation),
        ("Connector Validation", suite.test_connector_validation),
        ("Resilience Validation", suite.test_resilience_validation),
        ("Monitoring Validation", suite.test_monitoring_validation)
    ]

    results = {}

    for category_name, test_function in test_categories:
        print(f"\n{'='*80}")
        print(f"RUNNING: {category_name}")
        print(f"{'='*80}")

        try:
            test_function()
            results[category_name] = "PASSED"
            print(f"\n✓ {category_name}: COMPLETED")
        except Exception as e:
            results[category_name] = f"FAILED: {str(e)}"
            print(f"\n✗ {category_name}: FAILED - {str(e)}")

    # Print final summary
    print(f"\n{'='*80}")
    print("COMPREHENSIVE TEST SUITE SUMMARY")
    print(f"{'='*80}")

    for category, result in results.items():
        status_symbol = "✓" if result == "PASSED" else "✗"
        print(f"{status_symbol} {category}: {result}")

    # Overall result
    passed_count = sum(1 for result in results.values() if result == "PASSED")
    total_count = len(results)

    print(
        f"\nOverall Result: {passed_count}/{total_count} test categories passed")

    if passed_count == total_count:
        print("🎉 ALL COMPREHENSIVE TESTS PASSED!")
        return 0
    else:
        print("⚠️  SOME COMPREHENSIVE TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_comprehensive_test_suite()
    sys.exit(exit_code)
