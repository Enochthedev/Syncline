"""
Experimental connector framework.

This module provides a framework for managing experimental platform connectors,
including testing, validation, and development utilities.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field

from .base_experimental import (
    ExperimentalConnector,
    ExperimentalStatus,
    ExperimentalCapabilities,
    ExperimentalError
)
from .tiktok_connector import TikTokConnector
from .snapchat_connector import SnapchatConnector


logger = logging.getLogger(__name__)


@dataclass
class ExperimentalTestResult:
    """Result of experimental connector testing."""
    platform: str
    status: str
    timestamp: datetime
    tests_passed: int
    tests_failed: int
    tests_total: int
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ConnectorRegistry:
    """Registry of available experimental connectors."""
    name: str
    connector_class: Type[ExperimentalConnector]
    description: str
    status: ExperimentalStatus
    capabilities: ExperimentalCapabilities
    requirements: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


class ExperimentalFramework:
    """
    Framework for managing experimental platform connectors.

    Provides utilities for:
    - Connector registration and discovery
    - Testing and validation
    - Mock data generation
    - Development utilities
    - Documentation generation
    """

    def __init__(self):
        self._connectors: Dict[str, ConnectorRegistry] = {}
        self._active_connectors: Dict[str, ExperimentalConnector] = {}
        self._test_results: Dict[str, ExperimentalTestResult] = {}

        # Register built-in experimental connectors
        self._register_builtin_connectors()

        logger.info("Experimental framework initialized")

    def _register_builtin_connectors(self) -> None:
        """Register built-in experimental connectors."""
        # Register TikTok connector
        self.register_connector(
            "tiktok",
            TikTokConnector,
            "TikTok experimental connector for short-form video platform",
            ExperimentalStatus.PROOF_OF_CONCEPT,
            requirements=[
                "TikTok Developer Account",
                "App approval from TikTok",
                "Business verification (for some features)"
            ],
            limitations=[
                "API access requires special approval",
                "No personal message API",
                "Limited to business/creator features"
            ]
        )

        # Register Snapchat connector
        self.register_connector(
            "snapchat",
            SnapchatConnector,
            "Snapchat experimental connector for ephemeral messaging",
            ExperimentalStatus.PROOF_OF_CONCEPT,
            requirements=[
                "Snapchat Developer Account",
                "Partner approval from Snapchat",
                "Snap Kit SDK integration"
            ],
            limitations=[
                "Partner-only API access",
                "No messaging API",
                "Ephemeral content limitations"
            ]
        )

    def register_connector(
        self,
        platform: str,
        connector_class: Type[ExperimentalConnector],
        description: str,
        status: ExperimentalStatus,
        requirements: Optional[List[str]] = None,
        limitations: Optional[List[str]] = None
    ) -> None:
        """Register an experimental connector."""
        # Create a temporary instance to get capabilities
        temp_config = {"experimental": {"mock_mode": True}}
        temp_connector = connector_class(temp_config)

        registry = ConnectorRegistry(
            name=platform,
            connector_class=connector_class,
            description=description,
            status=status,
            capabilities=temp_connector.capabilities,
            requirements=requirements or [],
            limitations=limitations or []
        )

        self._connectors[platform] = registry
        logger.info(f"Registered experimental connector: {platform}")

    def get_available_connectors(self) -> Dict[str, ConnectorRegistry]:
        """Get all available experimental connectors."""
        return self._connectors.copy()

    def get_connector_info(self, platform: str) -> Optional[ConnectorRegistry]:
        """Get information about a specific connector."""
        return self._connectors.get(platform)

    async def create_connector(
        self,
        platform: str,
        config: Dict[str, Any]
    ) -> ExperimentalConnector:
        """Create an instance of an experimental connector."""
        if platform not in self._connectors:
            raise ExperimentalError(
                f"Unknown experimental platform: {platform}")

        registry = self._connectors[platform]
        connector = registry.connector_class(config)

        self._active_connectors[platform] = connector
        logger.info(f"Created experimental connector instance: {platform}")

        return connector

    async def test_connector(
        self,
        platform: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ExperimentalTestResult:
        """Test an experimental connector."""
        if platform not in self._connectors:
            raise ExperimentalError(
                f"Unknown experimental platform: {platform}")

        # Use default test config if none provided
        if config is None:
            config = {
                "experimental": {
                    "mock_mode": True,
                    "debug_mode": True
                }
            }

        start_time = datetime.now(timezone.utc)
        errors = []
        warnings = []
        test_details = {}

        try:
            # Create connector instance
            connector = await self.create_connector(platform, config)

            # Run connector-specific tests
            if hasattr(connector, 'test_connection'):
                test_results = await connector.test_connection()
                test_details.update(test_results)

            # Run framework tests
            framework_tests = await self._run_framework_tests(connector)
            test_details["framework_tests"] = framework_tests

            # Count test results
            tests_passed = 0
            tests_failed = 0
            tests_total = 0

            for test_name, test_result in test_details.get("tests", {}).items():
                tests_total += 1
                if test_result.get("status") in ["passed", "expected_failure", "simulated_success"]:
                    tests_passed += 1
                else:
                    tests_failed += 1
                    if "error" in test_result:
                        errors.append(f"{test_name}: {test_result['error']}")

            # Add framework test results
            for test_name, test_result in framework_tests.items():
                tests_total += 1
                if test_result.get("status") == "passed":
                    tests_passed += 1
                else:
                    tests_failed += 1
                    if "error" in test_result:
                        errors.append(
                            f"framework_{test_name}: {test_result['error']}")

            result = ExperimentalTestResult(
                platform=platform,
                status="passed" if tests_failed == 0 else "failed",
                timestamp=start_time,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tests_total=tests_total,
                details=test_details,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Test failed for {platform}: {e}")
            result = ExperimentalTestResult(
                platform=platform,
                status="error",
                timestamp=start_time,
                tests_passed=0,
                tests_failed=1,
                tests_total=1,
                details={"error": str(e)},
                errors=[str(e)],
                warnings=warnings
            )

        self._test_results[platform] = result
        return result

    async def _run_framework_tests(
        self,
        connector: ExperimentalConnector
    ) -> Dict[str, Any]:
        """Run framework-level tests on a connector."""
        tests = {}

        # Test connector initialization
        try:
            assert connector.platform is not None
            assert connector.capabilities is not None
            tests["initialization"] = {
                "status": "passed",
                "message": "Connector initialized successfully"
            }
        except Exception as e:
            tests["initialization"] = {
                "status": "failed",
                "error": str(e)
            }

        # Test health check
        try:
            health = await connector.health_check()
            assert health is not None
            tests["health_check"] = {
                "status": "passed",
                "message": f"Health status: {health.status.value}"
            }
        except Exception as e:
            tests["health_check"] = {
                "status": "failed",
                "error": str(e)
            }

        # Test mock data generation
        try:
            if connector.capabilities.test_data_generation:
                mock_messages = await connector._generate_mock_messages()
                assert len(mock_messages) > 0
                tests["mock_data"] = {
                    "status": "passed",
                    "message": f"Generated {len(mock_messages)} mock messages"
                }
            else:
                tests["mock_data"] = {
                    "status": "skipped",
                    "message": "Mock data generation not supported"
                }
        except Exception as e:
            tests["mock_data"] = {
                "status": "failed",
                "error": str(e)
            }

        # Test statistics collection
        try:
            stats = connector.get_statistics()
            assert isinstance(stats, dict)
            assert "platform" in stats
            tests["statistics"] = {
                "status": "passed",
                "message": "Statistics collection working"
            }
        except Exception as e:
            tests["statistics"] = {
                "status": "failed",
                "error": str(e)
            }

        return tests

    async def test_all_connectors(
        self,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ExperimentalTestResult]:
        """Test all registered experimental connectors."""
        results = {}

        for platform in self._connectors.keys():
            try:
                result = await self.test_connector(platform, config)
                results[platform] = result
                logger.info(f"Test completed for {platform}: {result.status}")
            except Exception as e:
                logger.error(f"Test failed for {platform}: {e}")
                results[platform] = ExperimentalTestResult(
                    platform=platform,
                    status="error",
                    timestamp=datetime.now(timezone.utc),
                    tests_passed=0,
                    tests_failed=1,
                    tests_total=1,
                    errors=[str(e)]
                )

        return results

    def get_test_results(self, platform: Optional[str] = None) -> Union[ExperimentalTestResult, Dict[str, ExperimentalTestResult]]:
        """Get test results for a platform or all platforms."""
        if platform:
            return self._test_results.get(platform)
        return self._test_results.copy()

    async def generate_documentation(self) -> Dict[str, Any]:
        """Generate documentation for all experimental connectors."""
        doc = {
            "title": "Experimental Platform Connectors",
            "description": "Documentation for experimental and proof-of-concept platform connectors",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "connectors": {}
        }

        for platform, registry in self._connectors.items():
            connector_doc = {
                "name": registry.name,
                "description": registry.description,
                "status": registry.status.value,
                "capabilities": {
                    "real_time_ingestion": registry.capabilities.real_time_ingestion,
                    "historical_fetch": registry.capabilities.historical_fetch,
                    "webhook_support": registry.capabilities.webhook_support,
                    "authentication": registry.capabilities.authentication,
                    "message_sending": registry.capabilities.message_sending,
                    "media_support": registry.capabilities.media_support,
                    "rate_limiting": registry.capabilities.rate_limiting,
                    "mock_mode": registry.capabilities.mock_mode,
                    "debug_logging": registry.capabilities.debug_logging,
                    "test_data_generation": registry.capabilities.test_data_generation
                },
                "requirements": registry.requirements,
                "limitations": registry.limitations
            }

            # Add platform-specific info if available
            try:
                temp_config = {"experimental": {"mock_mode": True}}
                connector = registry.connector_class(temp_config)
                if hasattr(connector, 'get_platform_info'):
                    platform_info = await connector.get_platform_info()
                    connector_doc["platform_info"] = platform_info
            except Exception as e:
                logger.warning(
                    f"Could not get platform info for {platform}: {e}")

            doc["connectors"][platform] = connector_doc

        return doc

    async def cleanup(self) -> None:
        """Clean up active connectors."""
        for platform, connector in self._active_connectors.items():
            try:
                if connector.is_running:
                    await connector.stop()
                logger.info(f"Cleaned up connector: {platform}")
            except Exception as e:
                logger.error(f"Error cleaning up {platform}: {e}")

        self._active_connectors.clear()

    def get_framework_statistics(self) -> Dict[str, Any]:
        """Get framework-level statistics."""
        return {
            "registered_connectors": len(self._connectors),
            "active_connectors": len(self._active_connectors),
            "test_results_available": len(self._test_results),
            "platforms": list(self._connectors.keys()),
            "statuses": {
                status.value: len([
                    r for r in self._connectors.values()
                    if r.status == status
                ])
                for status in ExperimentalStatus
            }
        }
