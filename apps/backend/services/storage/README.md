# Storage Services

This module provides blob storage and attachment handling for message attachments.

## Components

### Storage Backends (`backends.py`)

Abstract base class and concrete implementations for blob storage:

- **`BlobStorageClient`**: Abstract base class defining the storage interface
- **`LocalStorageClient`**: Local filesystem storage implementation
- **`MemoryStorageClient`**: In-memory storage for testing

### Blob Storage Manager (`blob_storage.py`)

High-level manager for blob storage operations with features like:

- Content integrity checking (SHA-256 hashing)
- URL-based downloading
- Statistics tracking
- Health monitoring

### Attachment Handler (`../attachment_handler.py`)

Service for managing message attachments with database integration:

- Download attachments from platform URLs
- Store attachment content directly
- Retrieve attachment content
- Delete attachments
- Process multiple attachments for a message

## Usage Examples

### Basic Storage Operations

```python
from services.storage import get_default_storage_manager

# Get the default storage manager
storage = get_default_storage_manager()

# Store content
content = b"Hello, World!"
path = await storage.store("test/file.txt", content, "text/plain")

# Retrieve content
retrieved = await storage.retrieve("test/file.txt")

# Check if exists
exists = await storage.exists("test/file.txt")

# Get metadata
metadata = await storage.get_metadata("test/file.txt")

# Delete content
deleted = await storage.delete("test/file.txt")
```

### Download from URL

```python
from services.storage import get_default_storage_manager

storage = get_default_storage_manager()

# Download and store from URL
url = "https://example.com/image.jpg"
path = await storage.store_from_url(url, "attachments/image.jpg")
```

### Attachment Handler

```python
from services.attachment_handler import get_default_attachment_handler
from uuid import UUID

handler = get_default_attachment_handler()

# Download and store attachment
attachment = await handler.download_and_store_attachment(
    db=db_session,
    message_id=UUID("..."),
    platform_url="https://platform.com/file.pdf",
    filename="document.pdf",
    mime_type="application/pdf"
)

# Store attachment content directly
attachment = await handler.store_attachment_content(
    db=db_session,
    message_id=UUID("..."),
    filename="file.txt",
    content=b"File content",
    mime_type="text/plain"
)

# Get attachment content
content = await handler.get_attachment_content(
    db=db_session,
    attachment_id=attachment.id
)

# Process multiple attachments
attachments_data = [
    {
        "url": "https://platform.com/file1.jpg",
        "filename": "image1.jpg",
        "mime_type": "image/jpeg"
    },
    {
        "url": "https://platform.com/file2.pdf",
        "filename": "document.pdf",
        "mime_type": "application/pdf"
    }
]

attachments = await handler.process_message_attachments(
    db=db_session,
    message_id=UUID("..."),
    attachment_data=attachments_data
)
```

### Custom Storage Backend

```python
from services.storage import BlobStorageManager, LocalStorageClient

# Create custom storage client
client = LocalStorageClient(base_path="/custom/path")

# Create manager with custom settings
manager = BlobStorageManager(
    client=client,
    max_file_size=50 * 1024 * 1024  # 50MB
)

# Use the manager
await manager.store("file.txt", b"content")
```

## Configuration

Storage settings are configured in `config/config.py`:

- `STORAGE_BACKEND`: Storage backend type (default: "local")
- `STORAGE_LOCAL_PATH`: Local storage path (default: "./storage")
- `STORAGE_MAX_FILE_SIZE`: Maximum file size (default: "50MB")

## Storage Structure

Attachments are stored with the following path structure:

```
storage/
└── attachments/
    └── {message_id}/
        ├── filename1.jpg
        ├── filename1.jpg.metadata
        ├── filename2.pdf
        └── filename2.pdf.metadata
```

Each file has an associated `.metadata` file containing:
- `content_type`: MIME type
- `upload_time`: ISO 8601 timestamp
- `size`: File size in bytes
- `content_hash`: SHA-256 hash for integrity
- `source_url`: Original URL (if downloaded)

## Error Handling

The module defines two main exceptions:

- **`BlobStorageError`**: Base exception for storage operations
- **`BlobNotFoundError`**: Raised when a blob is not found

Example error handling:

```python
from services.storage import BlobNotFoundError, BlobStorageError

try:
    content = await storage.retrieve("nonexistent.txt")
except BlobNotFoundError:
    print("File not found")
except BlobStorageError as e:
    print(f"Storage error: {e}")
```

## Health Monitoring

Both the storage manager and attachment handler provide health check endpoints:

```python
# Storage health check
health = await storage.health_check()
print(health['status'])  # 'healthy' or 'unhealthy'

# Attachment handler health check
health = await handler.health_check()
print(health['status'])

# Get statistics
stats = storage.get_stats()
print(f"Uploads: {stats['uploads']}")
print(f"Downloads: {stats['downloads']}")
print(f"Error rate: {stats['error_rate']}")
```

## Testing

The module includes a `MemoryStorageClient` for testing:

```python
from services.storage import BlobStorageManager, MemoryStorageClient

# Create in-memory storage for tests
client = MemoryStorageClient()
manager = BlobStorageManager(client=client)

# Use in tests without filesystem I/O
await manager.store("test.txt", b"test content")
```
