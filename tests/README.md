# MESH Ingestion System Tests

This directory contains all tests for the MESH ingestion system, organized into focused test files by functionality.

## Test Structure

### `test_message_schema.py`
Tests for unified message schema data classes:
- **TestMessageContent** - Content creation, format selection, validation
- **TestAttachment** - MIME type processing, type detection, file handling
- **TestParticipant** - Identity management, identifier priority
- **TestThread** - Thread management, title generation, participant handling
- **TestNormalizedMessage** - Message methods, content preview, serialization
- **TestRawMessage** - Raw data handling, platform data access

### `test_content_processor.py`
Tests for content processing utilities:
- **TestContentProcessor** - HTML cleaning, format conversion, content standardization
- HTML sanitization and security
- Entity decoding and whitespace normalization
- Markdown conversion and malicious content removal

### `test_mime_utils.py`
Tests for MIME type processing:
- **TestMimeTypeProcessor** - MIME cleaning, categorization, safety checks
- File extension mapping and type resolution
- Format validation and corrections
- Human-readable descriptions

### `test_blob_storage.py`
Tests for blob storage functionality:
- **TestLocalFileSystemStorage** - Local storage operations
- **TestBlobStorageManager** - High-level storage management
- **TestBlobStorageFactory** - Storage client creation
- Upload, download, delete operations
- Metadata handling and error cases

### `test_message_normalizer.py`
Tests for message normalization service:
- **TestAttachmentProcessor** - Attachment processing and storage
- **TestPlatformNormalizers** - Gmail and Slack specific normalization
- **TestMessageNormalizer** - Main normalization service
- Platform-specific data extraction and error handling

### `test_infrastructure.py`
Tests for infrastructure and database:
- **TestDatabaseConnection** - Database connectivity and schema
- **TestRedisConnection** - Redis operations and data types
- **TestModelCreation** - Model persistence and relationships

### `test_gmail_integration.py`
Tests for Gmail integration:
- **TestGmailIntegration** - Gmail API integration and message processing
- Email fetching, HTML/multipart messages
- Multiple recipients and error handling
- Edge cases and minimal data scenarios

## Running Tests

Run all tests:
```bash
python -m pytest tests/ -v
```

Run specific test file:
```bash
python -m pytest tests/test_message_schema.py -v
```

Run specific test class:
```bash
python -m pytest tests/test_message_schema.py::TestMessageContent -v
```

Run specific test:
```bash
python -m pytest tests/test_message_schema.py::TestMessageContent::test_message_content_creation -v
```

Run tests by category:
```bash
# Core schema tests
python -m pytest tests/test_message_schema.py tests/test_content_processor.py -v

# Storage and processing tests  
python -m pytest tests/test_blob_storage.py tests/test_mime_utils.py -v

# Integration tests
python -m pytest tests/test_infrastructure.py tests/test_gmail_integration.py -v
```

## Test Coverage

The test suite covers:
- ✅ Message schema and data structures
- ✅ Content processing and sanitization
- ✅ MIME type handling and file classification
- ✅ Blob storage operations
- ✅ Platform-specific message normalization
- ✅ Database integration and model persistence
- ✅ Gmail API integration
- ✅ Error handling and edge cases
- ✅ Async/await patterns
- ✅ Serialization and deserialization

## Dependencies

Tests require:
- pytest
- pytest-asyncio
- All project dependencies (SQLAlchemy, Redis, etc.)
- Optional: Gmail API credentials for integration tests

## Notes

- Gmail integration tests will skip if credentials are not available
- Infrastructure tests require database and Redis to be running
- Some tests use mock data to avoid external dependencies
- All tests are designed to be independent and can run in any order