# AI Services

This package provides AI processing capabilities for the R.E.M.I backend.

## Components

### LLM Provider Abstraction (`providers.py`)

Unified interface for different LLM providers with local-first approach:

- **OllamaProvider**: Local LLM inference using Ollama (default)
- **OpenAI/Anthropic**: Cloud fallbacks (planned)

#### Features

- Text generation and completion
- Chat-based interactions
- Embedding generation
- Model management (download, list, select)
- Automatic retry with exponential backoff
- Health checking

#### Usage

```python
from services.ai import get_llm_provider, GenerationConfig

# Get default provider (Ollama)
provider = get_llm_provider()

# Generate text
response = await provider.generate(
    prompt="Summarize this conversation...",
    config=GenerationConfig(temperature=0.1, max_tokens=500)
)

# Chat completion
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
]
response = await provider.chat(messages)

# Generate embeddings
embeddings = await provider.embed("Text to embed")

# List available models
models = await provider.list_models()

# Download a model
success = await provider.pull_model("llama3.2:3b")

# Health check
is_healthy = await provider.health_check()

# Clean up
await provider.close()
```

## Configuration

All AI settings are configured in `config/config.py`:

```python
# LLM Provider Settings
DEFAULT_LLM_PROVIDER = "ollama"
DEFAULT_CHAT_MODEL = "llama3.2:3b"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text:latest"

# Ollama Settings
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_TIMEOUT = 120
OLLAMA_MAX_RETRIES = 3

# AI Processing Settings
AI_MAX_TOKENS = 1000
AI_TEMPERATURE = 0.1
AI_BATCH_SIZE = 10
AI_CONCURRENT_REQUESTS = 5
```

## Models

### Recommended Models for M1 Air

- **Chat**: `llama3.2:3b` (3B parameters, optimized for M1)
- **Embeddings**: `nomic-embed-text:latest` (efficient embeddings)

### Model Management

```bash
# Pull a model
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# List models
ollama list

# Remove a model
ollama rm model-name
```

## Requirements

- Ollama installed and running (`brew install ollama`)
- Models downloaded (see above)
- Python packages: `aiohttp`, `pydantic`

## Future Enhancements

- OpenAI provider implementation
- Anthropic provider implementation
- Streaming response support
- Token usage tracking
- Cost estimation
- Model performance metrics
