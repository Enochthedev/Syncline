# Experimental Platform Connectors

This document provides comprehensive information about experimental platform connectors in the MESH ingestion system. These connectors are in proof-of-concept or early development stages and provide limited functionality with extensive mock data support for development and testing.

## Overview

Experimental connectors are designed to:
- Explore integration possibilities with platforms that have limited or restricted APIs
- Provide mock data for development and testing purposes
- Establish frameworks for future full implementations
- Test architectural patterns and data models

## Architecture

### Experimental Framework

The experimental framework (`integrations/experimental/framework.py`) provides:
- Connector registration and discovery
- Automated testing and validation
- Mock data generation utilities
- Documentation generation
- Development utilities

### Base Experimental Connector

All experimental connectors extend `ExperimentalConnector` which provides:
- Enhanced error handling with fallback mechanisms
- Mock mode support for development
- Debug logging and statistics collection
- Capability and limitation definitions
- Graceful degradation strategies

## Available Experimental Connectors

### TikTok Connector

**Status**: Proof of Concept  
**Platform**: TikTok (Short-form video platform)  
**File**: `integrations/experimental/tiktok_connector.py`

#### Capabilities
- ✅ Mock data generation
- ✅ Debug logging
- ✅ Test data generation
- ❌ Real-time ingestion (API limitation)
- ❌ Historical message fetch (API limitation)
- ❌ Authentication (requires special approval)
- ❌ Webhook support (not available)

#### Limitations
- TikTok API access requires special approval from TikTok
- No public API for direct messages or personal content
- Only business/creator APIs available with restrictions
- Extremely strict rate limiting and usage restrictions
- API documentation is limited and frequently changes

#### Mock Data Features
- Video content simulation
- Comment interactions
- Business inquiries
- User profile data
- Platform-specific metadata (algorithm scores, regions, etc.)

#### Configuration
```python
config = {
    "app_id": "your_tiktok_app_id",
    "app_secret": "your_tiktok_app_secret",
    "redirect_uri": "https://your-app.com/callback",
    "business_account": True,
    "experimental": {
        "mock_mode": True,
        "debug_mode": True,
        "api_timeout": 10,
        "max_retries": 2
    }
}
```

#### Usage Example
```python
from integrations.experimental import TikTokConnector

# Create connector
connector = TikTokConnector(config)

# Test connection
test_results = await connector.test_connection()

# Get platform info
platform_info = await connector.get_platform_info()

# Generate mock messages
messages = await connector.fetch_historical_messages()
```

### Snapchat Connector

**Status**: Proof of Concept  
**Platform**: Snapchat (Ephemeral messaging platform)  
**File**: `integrations/experimental/snapchat_connector.py`

#### Capabilities
- ✅ Mock data generation
- ✅ Debug logging
- ✅ Basic authentication (Snap Kit simulation)
- ✅ Ephemeral content simulation
- ❌ Real-time ingestion (API limitation)
- ❌ Historical message access (ephemeral nature)
- ❌ Webhook support (not available)

#### Limitations
- Snapchat API access limited to approved partners only
- No public API for personal messages or snaps
- Snap Kit SDK has very limited messaging capabilities
- Ephemeral nature of snaps makes historical access impossible
- Privacy-first design conflicts with messaging API needs

#### Mock Data Features
- Snap content (photos/videos) with expiration
- Chat messages with read/delivery status
- Story posts with view counts
- Saved memories
- Bitmoji stickers and reactions
- Ephemeral content simulation
- Screenshot notifications
- Snap streaks tracking

#### Unique Features
- Ephemeral content simulation with expiration times
- Screenshot detection and notification simulation
- Snap streak tracking
- Bitmoji integration
- Location-based features

#### Configuration
```python
config = {
    "client_id": "your_snapchat_client_id",
    "client_secret": "your_snapchat_client_secret",
    "redirect_uri": "https://your-app.com/callback",
    "snap_kit_enabled": True,
    "experimental": {
        "mock_mode": True,
        "debug_mode": True,
        "api_timeout": 10,
        "max_retries": 2
    }
}
```

#### Usage Example
```python
from integrations.experimental import SnapchatConnector

# Create connector
connector = SnapchatConnector(config)

# Simulate snap interaction
result = await connector.simulate_snap_interaction("snap_123", "view")

# Test connection
test_results = await connector.test_connection()

# Get mock messages with ephemeral content
messages = await connector.fetch_historical_messages()
```

## Using the Experimental Framework

### Basic Usage

```python
from integrations.experimental import ExperimentalFramework

# Initialize framework
framework = ExperimentalFramework()

# Get available connectors
connectors = framework.get_available_connectors()
print(f"Available: {list(connectors.keys())}")

# Create a connector
config = {"experimental": {"mock_mode": True}}
tiktok = await framework.create_connector("tiktok", config)

# Test a connector
test_result = await framework.test_connector("tiktok", config)
print(f"Tests: {test_result.tests_passed}/{test_result.tests_total} passed")

# Test all connectors
all_results = await framework.test_all_connectors(config)

# Generate documentation
docs = await framework.generate_documentation()

# Cleanup
await framework.cleanup()
```

### Testing Framework

The experimental framework includes comprehensive testing:

```python
# Run framework tests
python -m pytest tests/test_experimental_connectors.py -v

# Run specific connector tests
python -m pytest tests/test_experimental_connectors.py::TestTikTokConnector -v

# Run with coverage
python -m pytest tests/test_experimental_connectors.py --cov=integrations.experimental
```

## Development Guidelines

### Adding New Experimental Connectors

1. **Create Connector Class**
   ```python
   from integrations.experimental import ExperimentalConnector
   
   class NewPlatformConnector(ExperimentalConnector):
       def __init__(self, config: Dict[str, Any], **kwargs):
           super().__init__("new_platform", config, **kwargs)
           # Platform-specific initialization
       
       def _define_capabilities(self) -> ExperimentalCapabilities:
           # Define what the connector can do
           pass
       
       def _define_limitations(self) -> List[str]:
           # Define current limitations
           pass
       
       # Implement required abstract methods
   ```

2. **Register with Framework**
   ```python
   framework = ExperimentalFramework()
   framework.register_connector(
       "new_platform",
       NewPlatformConnector,
       "Description of the platform",
       ExperimentalStatus.PROOF_OF_CONCEPT
   )
   ```

3. **Add Tests**
   ```python
   class TestNewPlatformConnector:
       @pytest.mark.asyncio
       async def test_initialization(self):
           # Test connector initialization
           pass
   ```

### Best Practices

1. **Always Use Mock Mode**: Experimental connectors should default to mock mode
2. **Comprehensive Error Handling**: Handle API limitations gracefully
3. **Detailed Logging**: Use debug logging extensively for troubleshooting
4. **Clear Documentation**: Document all limitations and known issues
5. **Realistic Mock Data**: Generate mock data that reflects platform characteristics
6. **Test Coverage**: Write comprehensive tests for all functionality

### Mock Data Guidelines

1. **Platform-Specific**: Mock data should reflect the platform's unique characteristics
2. **Realistic Structure**: Use realistic message structures and metadata
3. **Variety**: Generate diverse content types and scenarios
4. **Temporal Patterns**: Include realistic timestamps and sequences
5. **Error Scenarios**: Include some mock error conditions for testing

## API Reference

### ExperimentalConnector

Base class for all experimental connectors.

#### Key Methods

- `authenticate()`: Authenticate with fallback to mock mode
- `fetch_historical_messages()`: Fetch messages with mock fallback
- `health_check()`: Enhanced health check with experimental status
- `get_statistics()`: Get connector statistics and metrics
- `test_connection()`: Test connector functionality

#### Properties

- `capabilities`: Defines what the connector supports
- `limitations`: List of current limitations
- `known_issues`: List of known issues
- `mock_mode`: Whether mock mode is enabled
- `debug_mode`: Whether debug logging is enabled

### ExperimentalFramework

Framework for managing experimental connectors.

#### Key Methods

- `register_connector()`: Register a new experimental connector
- `create_connector()`: Create connector instance
- `test_connector()`: Test specific connector
- `test_all_connectors()`: Test all registered connectors
- `generate_documentation()`: Generate connector documentation
- `get_framework_statistics()`: Get framework statistics

## Troubleshooting

### Common Issues

1. **API Access Denied**
   - Expected for most experimental connectors
   - Ensure mock mode is enabled
   - Check platform-specific requirements

2. **Mock Data Not Generated**
   - Check connector capabilities
   - Verify mock mode is enabled
   - Review debug logs for errors

3. **Tests Failing**
   - Check test configuration
   - Verify mock mode in test config
   - Review error messages in test results

### Debug Information

Enable debug mode to get detailed logging:

```python
config = {
    "experimental": {
        "debug_mode": True,
        "mock_mode": True
    }
}

connector = TikTokConnector(config)
# Debug logs will be available via connector.get_debug_logs()
```

### Getting Help

1. Check the debug logs: `connector.get_debug_logs()`
2. Review test results: `framework.test_connector(platform)`
3. Check platform-specific documentation
4. Review known limitations and issues

## Future Development

### Planned Improvements

1. **Enhanced Mock Data**: More sophisticated mock data generation
2. **API Simulation**: Better simulation of real API behaviors
3. **Integration Testing**: More comprehensive integration tests
4. **Documentation**: Auto-generated API documentation
5. **Monitoring**: Better monitoring and metrics collection

### Potential New Connectors

- **BeReal**: Social photo sharing platform
- **Clubhouse**: Audio-based social networking
- **Pinterest**: Visual discovery platform
- **Reddit**: Discussion and news aggregation

### Migration Path

When platforms provide better API access:
1. Implement real API methods alongside mock methods
2. Add feature flags to enable real API usage
3. Gradually transition from experimental to production status
4. Maintain backward compatibility with mock mode

## Conclusion

Experimental connectors provide a valuable framework for exploring integration possibilities with platforms that have limited API access. They enable development and testing while maintaining realistic expectations about platform limitations.

The mock data and testing frameworks ensure that the overall system architecture can accommodate these platforms when full API access becomes available, while providing immediate value for development and testing purposes.