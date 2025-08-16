# AI Setup for M1 MacBook Air (8GB RAM)

Your M1 Air with 8GB RAM is perfectly capable of running local AI models, but we need to optimize for your hardware constraints.

## 🎯 Recommended Models for M1 Air 8GB

### For Chat/Text Processing
1. **tinyllama:latest** (637MB) - ✅ You already have this!
   - Ultra-fast, minimal memory usage
   - Great for basic tasks like summarization
   
2. **llama3.2:1b** (1GB) - Recommended upgrade
   - Better quality than tinyllama
   - Still very fast on M1

3. **llama3.2:3b** (2GB) - Good balance
   - Higher quality responses
   - Will be slower but manageable

### For Embeddings
- **nomic-embed-text:latest** (274MB) - ✅ You already have this!
  - Perfect for semantic search
  - Very fast on M1

## 🚀 Quick Setup for Your Hardware

Let's configure the system to use your fastest available model:

```bash
# Use your existing tinyllama for now (fastest)
echo "DEFAULT_CHAT_MODEL=tinyllama:latest" >> .env

# Or install the 1B model for better quality
ollama pull llama3.2:1b
echo "DEFAULT_CHAT_MODEL=llama3.2:1b" >> .env
```

## ⚡ Performance Tips for M1 Air

### Memory Management
- Close other apps when using AI models
- Use smaller models for development/testing
- Consider the 1B models over 3B+ for daily use

### Model Loading
- First request will be slow (model loading)
- Subsequent requests will be much faster
- Keep Ollama running to avoid reload delays

### Timeout Settings
- Increase timeouts for your hardware
- First generation might take 30-60 seconds
- Later generations will be much faster (2-5 seconds)

## 🔧 Optimized Configuration

Let me update your system to work better with your M1 Air:

```env
# Optimized for M1 Air 8GB
DEFAULT_CHAT_MODEL=tinyllama:latest
DEFAULT_EMBEDDING_MODEL=nomic-embed-text:latest
AI_REQUEST_TIMEOUT=120  # Longer timeout for M1 Air
AI_MAX_TOKENS=1000      # Smaller responses = faster
AI_TEMPERATURE=0.3      # Slightly higher for creativity
```

## 📊 Expected Performance

| Model | Load Time | First Response | Subsequent | Quality |
|-------|-----------|----------------|------------|---------|
| tinyllama | 2-5s | 10-30s | 2-5s | ⭐⭐ |
| llama3.2:1b | 5-10s | 15-45s | 3-8s | ⭐⭐⭐ |
| llama3.2:3b | 10-20s | 30-90s | 5-15s | ⭐⭐⭐⭐ |

## 🎯 Recommended Workflow

1. **Start with tinyllama** - Test the system works
2. **Upgrade to 1B** - Better quality, still fast
3. **Try 3B later** - When you need higher quality

## 🛠️ Troubleshooting M1 Air Issues

### If models are too slow:
- Use tinyllama for development
- Switch to 1B models for production
- Consider cloud APIs for complex tasks

### If running out of memory:
- Close other applications
- Use smaller models
- Restart Ollama occasionally

### If timeouts occur:
- Increase AI_REQUEST_TIMEOUT to 180
- Use shorter prompts
- Try smaller models

## 💡 Pro Tips

- **Hybrid approach**: Use local for basic tasks, cloud APIs for complex ones
- **Model switching**: Easy to change models in config
- **Batch processing**: Process multiple items together for efficiency
- **Keep it running**: Leave Ollama running to avoid reload delays