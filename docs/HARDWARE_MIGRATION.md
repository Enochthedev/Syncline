# Hardware Migration Guide

The MESH Ingestion System is designed to be **completely portable** and automatically adapts to different hardware configurations. This guide covers how to migrate your system between different machines.

## 🔄 **Complete Portability**

Your system will work seamlessly when moved to:
- Different operating systems (Windows, Mac, Linux)
- Various hardware configurations (M1 Air → Gaming PC → Server)
- Cloud environments and local development machines
- Different AI capabilities (local-only → hybrid → cloud-only)

## 🚀 **Migration Process**

### **Step 1: Copy Your Project**
```bash
# Copy entire project directory to new machine
# All your specs, configurations, and data migrate together
```

### **Step 2: Install Dependencies**
```bash
# On the new machine
pip install -r requirements.txt
```

### **Step 3: Auto-Configure for New Hardware**
```bash
# Automatic setup (recommended)
python scripts/setup_ai.py

# This will:
# 1. Detect your new hardware capabilities
# 2. Recommend optimal AI models
# 3. Update configuration automatically
# 4. Test everything works
```

### **Step 4: Verify Migration**
```bash
# Check system status
python scripts/ai_status.py

# Test AI functionality
python -c "
import asyncio
from services.ai import get_ai_processing_engine

async def test():
    engine = await get_ai_processing_engine()
    result = await engine.process_text('Migration test', 'summarization')
    print(f'✅ Working! Provider: {result.provider_used}, Model: {result.model_used}')

asyncio.run(test())
"
```

## 💻 **Hardware-Specific Adaptations**

### **M1 Air (8GB) → Gaming PC (32GB)**
```bash
# Your new PC can handle much larger models
ollama pull llama3.2:7b     # 4GB model - much better quality
ollama pull qwen2.5:14b     # 8GB model - excellent quality

# System automatically detects and recommends:
# - Larger models for better performance
# - Higher token limits
# - Faster processing settings
```

**Auto-updated configuration:**
```env
DEFAULT_CHAT_MODEL=llama3.2:7b    # Upgraded from tinyllama
AI_MAX_TOKENS=4000                # Increased from 1000
AI_REQUEST_TIMEOUT=60             # Reduced from 120 (faster hardware)
```

### **Local Machine → Cloud Server**
```bash
# On cloud server, you can use both local models AND APIs
# Add API keys to .env
echo "OPENAI_API_KEY=your_key_here" >> .env
echo "ANTHROPIC_API_KEY=your_key_here" >> .env

# System will use hybrid approach:
# - Local models for basic/bulk processing
# - Cloud APIs for complex tasks
```

### **Windows → Mac → Linux**
The system automatically adapts to each platform:
- **Windows**: Uses Windows-specific Ollama installation
- **Mac**: Leverages M1/M2 optimization
- **Linux**: Uses native Linux performance

## 🎯 **Migration Scenarios**

### **Scenario 1: Development → Production**
```bash
# Development (M1 Air)
DEFAULT_CHAT_MODEL=tinyllama:latest

# Production (Server)
DEFAULT_CHAT_MODEL=llama3.2:70b
DEFAULT_LLM_PROVIDER=openai  # Hybrid approach
```

### **Scenario 2: Offline → Online Environment**
```bash
# Offline (local only)
DEFAULT_LLM_PROVIDER=ollama

# Online (hybrid)
DEFAULT_LLM_PROVIDER=openai
# Keep ollama as fallback
```

### **Scenario 3: Personal → Team Environment**
```bash
# Personal setup
DEFAULT_CHAT_MODEL=llama3.2:3b

# Team server
DEFAULT_CHAT_MODEL=qwen2.5:14b
AI_BATCH_SIZE=50  # Handle multiple team members
```

## ⚙️ **Configuration Migration Methods**

### **Method 1: Automatic (Recommended)**
```bash
python scripts/setup_ai.py
# Detects hardware and configures optimally
# Preserves your existing data and specs
```

### **Method 2: Manual Configuration**
Edit `.env` file for specific needs:
```env
# For powerful hardware
DEFAULT_CHAT_MODEL=llama3.2:7b
AI_MAX_TOKENS=4000
AI_BATCH_SIZE=20

# For resource-constrained hardware
DEFAULT_CHAT_MODEL=tinyllama:latest
AI_MAX_TOKENS=500
AI_REQUEST_TIMEOUT=180
```

### **Method 3: Runtime Switching**
```python
# Switch providers/models at runtime
from services.ai import get_ai_processing_engine, get_provider

# Use auto-detected best provider
engine = await get_ai_processing_engine()

# Or force specific provider
openai_provider = get_provider("openai")
ollama_provider = get_provider("ollama")
```

## 📊 **Hardware Optimization Matrix**

| Hardware Type | Recommended Model | Memory Usage | Performance | Config Changes |
|---------------|------------------|--------------|-------------|----------------|
| **M1 Air 8GB** | `tinyllama:latest` | 637MB | ⚡⚡⚡ | Timeout: 120s |
| **M1 Pro 16GB** | `llama3.2:3b` | 2GB | ⚡⚡ | Timeout: 60s |
| **Gaming PC 32GB** | `qwen2.5:7b` | 4GB | ⚡ | Tokens: 4000 |
| **Server 64GB+** | `llama3.2:70b` | 40GB | 🚀 | Batch: 50 |
| **Cloud Instance** | Hybrid setup | Variable | 🚀🚀 | APIs + Local |

## 🔧 **Migration Checklist**

### **Before Migration**
- [ ] Backup your project directory
- [ ] Note your current AI configuration
- [ ] Export any custom settings

### **During Migration**
- [ ] Copy entire project to new machine
- [ ] Install Python dependencies
- [ ] Install Ollama (if using local AI)
- [ ] Run setup script
- [ ] Test AI functionality

### **After Migration**
- [ ] Verify all specs still work
- [ ] Test ingestion pipeline
- [ ] Check AI processing performance
- [ ] Update documentation if needed

## 🛠️ **Troubleshooting Migration Issues**

### **Models Not Found**
```bash
# Pull required models on new machine
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### **Performance Issues**
```bash
# Re-run setup to optimize for new hardware
python scripts/setup_ai.py
```

### **API Key Issues**
```bash
# Verify API keys in .env
cat .env | grep API_KEY

# Test API connectivity
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

### **Configuration Conflicts**
```bash
# Reset to defaults and reconfigure
mv .env .env.backup
python scripts/setup_ai.py
```

## 💡 **Pro Migration Tips**

### **For Teams**
- Use shared configuration templates
- Document hardware-specific optimizations
- Set up CI/CD for consistent deployments

### **For Development**
- Keep lightweight config for laptops
- Use powerful config for workstations
- Test on target hardware before deployment

### **For Production**
- Use hybrid approach (local + cloud)
- Monitor performance after migration
- Have rollback plan ready

## 🔄 **Continuous Adaptation**

The system continuously adapts to your environment:
- **Startup Detection**: Checks available providers on each start
- **Automatic Fallback**: Switches providers if one becomes unavailable
- **Performance Monitoring**: Adjusts timeouts based on actual performance
- **Resource Management**: Optimizes based on available memory/CPU

## 🎯 **Best Practices**

1. **Always run setup script** on new hardware
2. **Test thoroughly** after migration
3. **Keep backups** of working configurations
4. **Document custom settings** for your team
5. **Monitor performance** and adjust as needed

---

Your MESH Ingestion System is designed to work everywhere - from your M1 Air to the most powerful servers! 🚀