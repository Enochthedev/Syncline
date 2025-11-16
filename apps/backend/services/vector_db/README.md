# Vector Database Services

This package provides vector database functionality using ChromaDB for semantic search and similarity matching.

## Components

### ChromaDB Client (`chroma_client.py`)

High-level interface for ChromaDB operations:

- Collection management
- Document storage with embeddings
- Similarity search
- Local persistence
- Metadata filtering

#### Features

- Automatic collection creation
- Persistent storage
- Configurable distance functions (cosine, L2, inner product)
- Batch operations
- Health checking

#### Usage

```python
from services.vector_db import get_chroma_client

# Get client instance
client = get_chroma_client()

# Create or get collection
collection = client.get_or_create_collection("my_collection")

# Add documents
client.add_documents(
    documents=["Document 1", "Document 2"],
    ids=["id1", "id2"],
    metadatas=[{"source": "email"}, {"source": "slack"}],
    collection_name="my_collection"
)

# Query for similar documents
results = client.query(
    query_texts=["search query"],
    n_results=10,
    where={"source": "email"}  # Optional metadata filter
)

for result in results:
    print(f"ID: {result.id}")
    print(f"Document: {result.document}")
    print(f"Score: {result.score}")
    print(f"Metadata: {result.metadata}")

# Get documents by ID
docs = client.get_documents(ids=["id1", "id2"])

# Count documents
count = client.count_documents("my_collection")

# Delete documents
client.delete_documents(ids=["id1"])

# List all collections
collections = client.list_collections()

# Delete collection
client.delete_collection("my_collection")

# Health check
is_healthy = client.health_check()
```

## Initialization

Use the provided script to initialize the vector database:

```bash
# Initialize with defaults
python scripts/init_vector_db.py

# Reset and initialize (WARNING: deletes all data)
python scripts/init_vector_db.py --reset

# Create specific collection
python scripts/init_vector_db.py --collection my_collection

# Verbose output
python scripts/init_vector_db.py --verbose
```

## Configuration

All vector DB settings are configured in `config/config.py`:

```python
# ChromaDB Settings
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
CHROMA_PERSIST_DIRECTORY = "./vector_db"
CHROMA_COLLECTION_NAME = "mesh_messages"
CHROMA_DISTANCE_FUNCTION = "cosine"  # cosine, l2, or ip
```

## Collections

### Default Collections

- `mesh_messages`: Message-level embeddings for semantic search
- `mesh_messages_threads`: Thread-level embeddings for conversation search

### Collection Metadata

Collections store:
- Document text
- Vector embeddings
- Custom metadata (platform, user_id, timestamp, etc.)
- Distance/similarity scores

## Distance Functions

- **cosine**: Cosine similarity (default, range 0-2, lower is more similar)
- **l2**: Euclidean distance (L2 norm)
- **ip**: Inner product (dot product)

## Persistence

ChromaDB data is persisted to disk at `CHROMA_PERSIST_DIRECTORY`:

```
vector_db/
├── chroma.sqlite3          # Metadata database
└── [collection-uuid]/      # Vector index files
    ├── data_level0.bin
    ├── header.bin
    ├── length.bin
    └── link_lists.bin
```

## Integration with AI Services

The vector database works with the AI services for embedding generation:

```python
from services.ai import get_llm_provider
from services.vector_db import get_chroma_client

# Generate embeddings
provider = get_llm_provider()
embeddings = await provider.embed(["text1", "text2"])

# Store in vector DB
client = get_chroma_client()
client.add_documents(
    documents=["text1", "text2"],
    ids=["id1", "id2"],
    embeddings=embeddings
)
```

## Requirements

- ChromaDB installed (`pip install chromadb`)
- Sufficient disk space for persistence
- Python packages: `chromadb`, `pydantic`

## Performance Tips

1. **Batch Operations**: Add documents in batches for better performance
2. **Metadata Filtering**: Use metadata filters to narrow search scope
3. **Collection Size**: Keep collections focused and reasonably sized
4. **Distance Function**: Choose appropriate distance function for your use case

## Troubleshooting

### OpenTelemetry Import Error

If you encounter OpenTelemetry import errors, this is a known ChromaDB dependency issue. Solutions:

1. Update ChromaDB: `pip install --upgrade chromadb`
2. Downgrade OpenTelemetry: `pip install opentelemetry-api==1.20.0`
3. Use ChromaDB in client-server mode instead of embedded mode

### Persistence Issues

If data isn't persisting:
- Check `CHROMA_PERSIST_DIRECTORY` exists and is writable
- Ensure ChromaDB client is properly closed
- Verify disk space availability

## Future Enhancements

- Hybrid search (vector + keyword)
- Multi-collection queries
- Automatic embedding generation
- Batch processing optimization
- Collection backup/restore
- Performance monitoring
