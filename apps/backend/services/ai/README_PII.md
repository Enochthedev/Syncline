# PII Detection and Redaction Service

## Overview

The PII (Personally Identifiable Information) Detection and Redaction Service provides automated detection and optional redaction of sensitive information in text using Microsoft Presidio.

## Features

- **Comprehensive PII Detection**: Detects emails, phone numbers, credit cards, SSNs, names, addresses, IP addresses, and more
- **Configurable Confidence Thresholds**: Filter detections based on confidence scores
- **Optional Redaction**: Choose to detect only or detect and redact
- **Custom Placeholders**: Use custom replacement text for redacted PII
- **Batch Processing**: Process multiple texts efficiently
- **Message Integration**: Direct integration with Message models
- **Health Monitoring**: Built-in health checks

## Supported PII Entity Types

- `EMAIL_ADDRESS`: Email addresses
- `PHONE_NUMBER`: Phone numbers (various formats)
- `CREDIT_CARD`: Credit card numbers
- `US_SSN`: Social Security Numbers
- `US_PASSPORT`: US Passport numbers
- `US_DRIVER_LICENSE`: US Driver's License numbers
- `PERSON`: Person names
- `LOCATION`: Locations and addresses
- `IP_ADDRESS`: IP addresses
- `URL`: URLs
- `DATE_TIME`: Dates and times
- `MEDICAL_LICENSE`: Medical license numbers
- And many more...

## Configuration

Configure PII redaction in your `.env` file or environment variables:

```bash
# Enable/disable PII redaction
PII_REDACTION_ENABLED=true

# Placeholder text for redacted PII
PII_REDACTION_PLACEHOLDER="[REDACTED]"

# Minimum confidence threshold (0.0 to 1.0)
PII_CONFIDENCE_THRESHOLD=0.8
```

## Usage Examples

### Basic Detection

```python
from services.ai.pii_redaction import get_pii_redaction_service

# Get service instance
service = get_pii_redaction_service()

# Detect PII in text
text = "Contact me at john@example.com or call 555-1234"
detected_pii = service.detect_pii(text)

for pii in detected_pii:
    print(f"{pii.entity_type}: {pii.text} (confidence: {pii.confidence})")
```

### Redaction

```python
from services.ai.pii_redaction import get_pii_redaction_service

service = get_pii_redaction_service()

# Redact PII from text
text = "My email is john@example.com and phone is 555-1234"
redacted_text, detected_pii = service.redact_pii(text)

print(f"Original: {text}")
print(f"Redacted: {redacted_text}")
print(f"Found {len(detected_pii)} PII entities")
```

### Custom Placeholder

```python
# Use custom placeholder
redacted_text, detected_pii = service.redact_pii(
    text,
    placeholder="[HIDDEN]"
)
```

### Specific Entity Types

```python
# Detect only specific entity types
detected_pii = service.detect_pii(
    text,
    entity_types=["EMAIL_ADDRESS", "PHONE_NUMBER"]
)
```

### Batch Processing

```python
# Process multiple texts
texts = [
    "Email: alice@example.com",
    "Phone: 555-9876",
    "Contact: bob@test.com"
]

# Batch detection
detected_batch = service.detect_pii_batch(texts)

# Batch redaction
redacted_batch = service.redact_pii_batch(texts)

for text, (redacted, pii_list) in zip(texts, redacted_batch):
    print(f"Original: {text}")
    print(f"Redacted: {redacted}")
    print(f"Found: {len(pii_list)} PII entities\n")
```

### Message Integration

```python
from services.ai.pii_redaction import get_pii_redaction_service
from db.models.message import Message

service = get_pii_redaction_service()

# Detect PII in a message
detected_pii = await service.detect_pii_in_message(message)

# Redact PII in a message (updates message in database)
redacted_text, detected_pii = await service.redact_pii_in_message(
    message,
    db,
    store_original=True  # Store original text in metadata
)
```

### Batch Message Processing

```python
# Process multiple messages
messages = [msg1, msg2, msg3]

detected_batch = await service.detect_pii_in_messages_batch(messages)

for message, pii_list in zip(messages, detected_batch):
    print(f"Message {message.id}: {len(pii_list)} PII entities")
```

## Advanced Usage

### Custom Service Configuration

```python
from services.ai.pii_redaction import PIIRedactionService

# Create service with custom settings
service = PIIRedactionService(
    confidence_threshold=0.9,  # Higher threshold
    redaction_placeholder="[PRIVATE]",
    enabled=True,
    language="en"
)
```

### Get Supported Entity Types

```python
# Get list of all supported entity types
supported_types = service.get_supported_entity_types()
print(f"Supported entity types: {supported_types}")
```

### Health Check

```python
# Check service health
is_healthy = service.health_check()
print(f"Service healthy: {is_healthy}")
```

## Integration with AI Pipeline

The PII redaction service integrates seamlessly with other AI services:

```python
from services.ai.pii_redaction import get_pii_redaction_service
from services.ai.entity_extraction import get_entity_extraction_service
from services.ai.embeddings import get_embedding_service

# Get services
pii_service = get_pii_redaction_service()
entity_service = get_entity_extraction_service()
embedding_service = get_embedding_service()

# Process message through pipeline
async def process_message(message, db):
    # 1. Detect PII (optional: redact before further processing)
    detected_pii = await pii_service.detect_pii_in_message(message)
    
    # 2. Extract entities
    entities = await entity_service.extract_and_store_entities(message, db)
    
    # 3. Generate embeddings
    embedding = await embedding_service.embed_message(message, db)
    
    return {
        "pii_detected": len(detected_pii),
        "entities_extracted": len(entities),
        "embedding_generated": embedding is not None
    }
```

## Performance Considerations

- **Lazy Initialization**: Presidio engines are initialized on first use
- **Batch Processing**: Use batch methods for processing multiple texts
- **Confidence Threshold**: Higher thresholds reduce false positives but may miss some PII
- **Entity Type Filtering**: Specify only needed entity types for faster processing

## Privacy and Security

- **Local Processing**: All PII detection runs locally using Presidio
- **No External Calls**: No data is sent to external services
- **Original Text Storage**: When redacting messages, original text can be stored in metadata
- **Configurable**: Enable/disable redaction globally or per-request

## Error Handling

The service handles errors gracefully:

```python
try:
    detected_pii = service.detect_pii(text)
except Exception as e:
    logger.error(f"PII detection failed: {e}")
    # Service returns empty list on error
```

## Dependencies

- `presidio-analyzer`: PII detection engine
- `presidio-anonymizer`: PII redaction engine
- `spacy`: NLP processing (used by Presidio)
- `en_core_web_sm`: English language model (auto-downloaded)

## Testing

Run tests to verify the service:

```bash
pytest apps/backend/tests/test_pii_redaction.py -v
```

## Troubleshooting

### Model Not Found

If you see "Model not found" errors, install the spaCy model:

```bash
python -m spacy download en_core_web_sm
```

### Low Detection Rate

- Lower the confidence threshold in configuration
- Ensure text is in English (or configure appropriate language)
- Check that Presidio recognizers are loaded correctly

### Performance Issues

- Use batch processing for multiple texts
- Consider increasing confidence threshold to reduce processing
- Filter to specific entity types if you don't need all types

## References

- [Microsoft Presidio Documentation](https://microsoft.github.io/presidio/)
- [spaCy Documentation](https://spacy.io/)
- [PII Detection Best Practices](https://microsoft.github.io/presidio/analyzer/best_practices/)
