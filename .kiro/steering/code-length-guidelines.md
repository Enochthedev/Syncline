---
inclusion: always
---

# Kiro Code Length Guidelines - R.E.M.I Backend

## 🎯 Updated Rules for R.E.M.I Backend
**For this large-scale mesh ingestion system, we allow larger files due to complexity**

## 📏 Line Count Guidelines

### Maximum Limits for R.E.M.I Backend
- **Single File**: 800 lines maximum (increased from 500)
- **Critical Limit**: Stop at 600 lines and suggest splitting
- **Ideal Target**: 300-500 lines per file

### What Counts as Lines
- All code lines (including comments and whitespace)
- Does NOT count import statements separately from total
- Measure the complete file output

## 🚨 When Approaching Limits

### At 400+ Lines
**Alert**: "This file is getting large (~400 lines). Consider if we should split it into multiple files."
**Ask**: "Would you like me to break this into smaller modules?"

### At 600+ Lines
**Stop**: "I need to pause - this file is approaching 600 lines."
**Require**: User confirmation to continue OR agreement to split the file
**Suggest**: Specific ways to modularize

### At 800 Lines
**Hard Stop**: "I cannot create files longer than 800 lines."
**Must**: Split into multiple files before continuing

## 🎪 R.E.M.I-Specific Exceptions

### Acceptable Larger Files (up to 800 lines)
- **Complex connectors** (Gmail, WhatsApp, Slack integrations)
- **Service classes** with multiple related methods
- **API route files** with comprehensive endpoint coverage
- **AI processing services** with multiple algorithms
- **Database models** with complex relationships
- **Configuration files** with extensive platform settings

### Still Never Acceptable (even for R.E.M.I)
- Files over 800 lines
- Monolithic files without clear structure
- Mixed unrelated responsibilities

## 🏗️ R.E.M.I-Specific Patterns

### Platform Connectors (up to 800 lines)
```python
# WhatsApp connector with full Matrix integration
integrations/whatsapp_connector.py  # ~700 lines - acceptable
├── Matrix client implementation
├── Bridge communication
├── Message sync logic
├── Authentication handling
├── Error recovery
└── Health monitoring
```

### Service Classes (up to 600 lines)
```python
# Session manager with comprehensive features
services/whatsapp_session_manager.py  # ~500 lines - good
├── Session lifecycle
├── Login/logout flows
├── Status monitoring
├── Auto-sync triggers
└── Cleanup operations
```

### API Routes (up to 500 lines)
```python
# Comprehensive API endpoints
api/routes/whatsapp/messaging.py  # ~400 lines - ideal
├── Message operations
├── Sync endpoints
├── Background sync
├── Webhook handling
└── Status monitoring
```

## 📊 Current R.E.M.I File Status
- `whatsapp_connector.py`: ~700 lines ✅ (Complex integration)
- `whatsapp_session_manager.py`: ~500 lines ✅ (Comprehensive service)
- `whatsapp_message_sync.py`: ~300 lines ✅ (Focused service)
- `whatsapp_background_sync.py`: ~200 lines ✅ (Single responsibility)
- `whatsapp_webhook_service.py`: ~250 lines ✅ (Webhook handling)

## 🎯 Quality Over Quantity (Still Applies)

### Encourage
- Modular design within larger files
- Clear section separation with comments
- Single responsibility per file (even if large)
- Logical method grouping
- Comprehensive documentation

### Monitor
- Files approaching 600 lines
- Complex nested logic
- Mixed responsibilities
- Testing difficulty

## 🎖️ R.E.M.I Best Practices

1. **Document Large Files**: Use clear section headers and docstrings
2. **Group Related Methods**: Keep related functionality together
3. **Use Type Hints**: Essential for large codebases
4. **Comprehensive Error Handling**: Critical for platform integrations
5. **Extensive Logging**: Important for debugging complex flows
6. **Test Thoroughly**: Large files need comprehensive test coverage

Remember: For R.E.M.I's complex platform integrations, larger files are acceptable when they maintain clear structure and single responsibility. The 800-line limit ensures we don't create unmaintainable monoliths while allowing for comprehensive implementations.