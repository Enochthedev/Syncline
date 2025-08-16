# AI Setup Guide for MESH Ingestion System

The MESH system supports both **local AI processing** (private, fast, no API costs) and **cloud AI APIs** (full-featured, reliable) with automatic detection and fallback.

## 🚀 Quick Start

### Option 1: Automatic Setup (Recommended)
```bash
# Run the interactive setup utility
python scripts/setup_ai.py

# Or check current status
python scripts/ai_status.py
```

### Option 2: Manual Setup

#### Local AI (Ollama) - Recommended for Privacy
1. **Install Ollama**: Visit [ollama.ai/download](https://ollama.ai/download)
2. **Pull recommended models**:
   ```bash
   ollama pull llama3.2:3b      # Chat model (2GB)
   ollama pull nomic-embed-text # Embedding model (274MB)
   ```
3. **Verify**: Ollama should auto-start and be available at `http://localhost:11434`

#### Cloud APIs (Optional)
1. **OpenAI**: Add your API key to `.env`:
   ```env
   OPENAI_API_KEY=your_actual_api_key_here
   ```
2. **Anthropic**: Add your API key to `.env`:
   ```env
   ANTHROPIC_API_KEY=your_actual_api_key_here
   ```

## 🤖 Recommended Models

### Local Models (Ollama)
| Model | Size | Use Case | Speed |
|-------|------|----------|-------|
| `llama3.2:1b` | 1GB | Basic tasks, very fast | ⚡⚡⚡ |
| `llama3.2:3b` | 2GB | **Recommended** - balanced | ⚡⚡ |
| `qwen2.5:7b` | 4GB | High quality, slower | ⚡ |
| `nomic-embed-text` | 274MB | **Required** for embeddings | ⚡⚡⚡ |

### Cloud Models
| Provider | Model | Use Case |
|----------|-------|----------|
| OpenAI | `gpt-4o-mini` | Cost-effective chat |
| OpenAI | `text-embedding-3-small` | Cost-effective embeddings |
| Anthropic | `claude-3-haiku-20240307` | Fast, accurate chat |

## 🔧 Configuration

The system automatically detects and configures the best available providers. You can override defaults in `.env`:

```env
# Provider priority: ollama (local) -> openai -> anthropic
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_CHAT_MODEL=llama3.2:3b
DEFAULT_EMBEDDING_MODEL=nomic-embed-text

# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434

# API keys (optional)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# AI processing settings
AI_MAX_TOKENS=4000
AI_TEMPERATURE=0.1
AI_REQUEST_TIMEOUT=30
PII_REDACTION_ENABLED=true
```

## 🔄 How Provider Selection Works

1. **Detection**: System checks all providers on startup
2. **Local First**: Prefers local providers (Ollama) for privacy and speed
3. **Automatic Fallback**: Falls back to cloud APIs if local unavailable
4. **Smart Routing**: Different capabilities can use different providers

```python
# Example: The system might use:
# - Ollama for chat (fast, private)
# - OpenAI for embeddings (if local embedding model not available)
```

## 🧪 Testing Your Setup

```bash
# Quick status check
python scripts/ai_status.py

# Full setup and test
python scripts/setup_ai.py

# Test from Python
python -c "
import asyncio
from services.ai import get_ai_processing_engine

async def test():
    engine = await get_ai_processing_engine()
    result = await engine.process_text('Hello world', 'summarization')
    print(f'Result: {result.result}')
    print(f'Provider: {result.provider_used}')
    print(f'Model: {result.model_used}')

asyncio.run(test())
"
```

## 🔒 Privacy & Security

### Local Processing (Ollama)
- ✅ **Complete Privacy**: Data never leaves your machine
- ✅ **No API Costs**: Free to use
- ✅ **Offline Capable**: Works without internet
- ✅ **Fast**: No network latency

### Cloud APIs
- ⚠️ **Data Sharing**: Text sent to external services
- 💰 **API Costs**: Pay per request
- 🌐 **Internet Required**: Needs connectivity
- 🔒 **PII Redaction**: Automatically removes sensitive data before sending

## 🛠️ Troubleshooting

### Ollama Issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama (macOS)
brew services restart ollama

# Check available models
ollama list

# Pull missing models
ollama pull llama3.2:3b
```

### API Issues
```bash
# Test OpenAI key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Check .env file
cat .env | grep API_KEY
```

### Common Solutions
1. **"No AI providers available"**: Install Ollama or add API keys
2. **"Model not found"**: Pull the model with `ollama pull <model>`
3. **"Connection refused"**: Start Ollama service
4. **"API key invalid"**: Check your API key in `.env`

## 📊 Performance Comparison

| Provider | Speed | Quality | Privacy | Cost |
|----------|-------|---------|---------|------|
| Ollama (local) | ⚡⚡⚡ | ⭐⭐⭐ | 🔒🔒🔒 | 💰 Free |
| OpenAI | ⚡⚡ | ⭐⭐⭐⭐⭐ | ⚠️ | 💰💰 |
| Anthropic | ⚡⚡ | ⭐⭐⭐⭐⭐ | ⚠️ | 💰💰 |

## 🎯 Best Practices

1. **Start Local**: Begin with Ollama for development and testing
2. **Hybrid Setup**: Use local for basic tasks, APIs for complex ones
3. **Monitor Usage**: Check API costs if using cloud providers
4. **PII Protection**: Keep PII redaction enabled for cloud APIs
5. **Model Selection**: Choose models based on your hardware and needs

## 🔄 Switching Providers

You can change providers at runtime:

```python
from services.ai import get_ai_processing_engine

# Get engine (auto-detects best provider)
engine = await get_ai_processing_engine()

# Or force a specific provider
from services.ai import get_provider
provider = get_provider("openai")  # or "ollama", "anthropic"
```

## 📈 Scaling Considerations

- **Local**: Limited by your hardware (CPU/RAM)
- **Cloud**: Virtually unlimited, but costs scale
- **Hybrid**: Best of both - local for bulk processing, cloud for complex tasks

---

Need help? Run `python scripts/setup_ai.py` for interactive setup assistance!