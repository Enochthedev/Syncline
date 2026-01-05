# Phase 1 Usage Guide - How to Use New Features

## 🔐 1. Encrypted Credentials

### Automatic Encryption

**All new connections automatically encrypt credentials:**

```python
from db.models.platform_connection import PlatformConnection, PlatformType

# Create connection - credentials are automatically encrypted
connection = PlatformConnection(
    user_id=user.id,
    platform=PlatformType.WHATSAPP,
    credentials={
        "access_token": "secret_token_123",
        "refresh_token": "refresh_456",
        "matrix_access_token": "matrix_token_789"
    }
)
db.add(connection)
await db.commit()

# Reading credentials - automatic decryption
creds = connection.credentials
print(creds["access_token"])  # "secret_token_123"

# Get single credential safely
token = connection.get_credential("access_token", default="")
```

### Migrating Existing Credentials

**For existing unencrypted credentials, run the migration script:**

```bash
cd apps/backend
python scripts/migrate_encrypt_credentials.py
```

**Output:**
```
================================================================================
Credential Encryption Migration
================================================================================

Found 15 platform connections
[1/15] Processing connection abc-123...
  Platform: whatsapp
  ✓ Migrated to encrypted format

...

================================================================================
Migration Summary
================================================================================
Total connections: 15
Migrated to encrypted: 15
Already encrypted: 0
Errors: 0
================================================================================
✓ All credentials successfully encrypted!
```

---

## 🔄 2. Credential Rotation

### Using Rotation Features

```python
from db.models.platform_connection import PlatformConnection

# Load connection
connection = await db.get(PlatformConnection, connection_id)

# Check if rotation needed (default 90 days)
if connection.needs_rotation(max_age_days=90):
    print(f"Credentials are {age} days old, rotation recommended")

    # Rotate credentials
    new_credentials = await fetch_new_oauth_tokens()
    connection.rotate_credentials(new_credentials)
    await db.commit()

    print(f"Rotated to version: {connection.credentials_version}")  # v2, v3, etc.
    print(f"Rotated at: {connection.credentials_rotated_at}")

# Manual rotation
connection.rotate_credentials({
    "access_token": "new_token",
    "refresh_token": "new_refresh",
    "expires_at": "2026-01-01T00:00:00Z"
})
await db.commit()
```

### Rotation Tracking

**Database tracks:**
- `credentials_rotated_at`: Timestamp of last rotation
- `credentials_version`: Version string (v1, v2, v3...)

**Query old credentials:**
```python
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

# Find connections older than 90 days
threshold = datetime.now(timezone.utc) - timedelta(days=90)
result = await db.execute(
    select(PlatformConnection).where(
        PlatformConnection.credentials_rotated_at < threshold
    )
)
old_connections = result.scalars().all()
```

---

## 💾 3. Connector Cache

### Using the Cache (Automatic)

**The cache is integrated into the application lifecycle - no manual setup needed!**

**When app starts:**
```
INFO Starting R.E.M.I Backend...
INFO Starting connector cache...
INFO Connector cache started
```

**When app shuts down:**
```
INFO Stopping connector cache...
INFO Connector cache stopped
```

### Manual Cache Usage

**If you need to manually use the cache:**

```python
from services.connector_cache import get_connector_cache
from integrations.whatsapp_connector import WhatsAppConnector

cache = get_connector_cache()

# Get or create connector (automatically cached)
connector = await cache.get_or_create(
    connection_id=connection.id,
    connector_class=WhatsAppConnector,
    credentials=connection.credentials
)

# Connector is reused for 1 hour
# Next call with same connection_id returns cached instance

# Invalidate cache when credentials rotate
await cache.invalidate(connection.id)

# Get cache statistics
stats = cache.get_stats()
print(f"Cached connectors: {stats['size']}/{stats['max_size']}")
print(f"Total accesses: {stats['total_accesses']}")
```

### Cache Configuration

**Modify in `services/connector_cache.py`:**

```python
_connector_cache = ConnectorCache(
    max_size=100,        # Max cached connectors
    default_ttl=3600,    # 1 hour cache lifetime
    cleanup_interval=300 # Cleanup every 5 minutes
)
```

---

## ✅ 4. Config Validation

### Production Deployment Checklist

**Before deploying to production, ensure these environment variables are set:**

```bash
# Required secrets (will fail if using defaults)
export SECRET_KEY="your-32-char-or-longer-secret-key-here"
export JWT_SECRET_KEY="your-32-char-or-longer-jwt-key-here"

# Database (must not use default password)
export DATABASE_URL="postgresql+asyncpg://user:SECURE_PASSWORD@host:5432/db"

# Matrix/WhatsApp (if enabled)
export WHATSAPP_BRIDGE_ENABLED=true
export MATRIX_ACCESS_TOKEN="your-matrix-access-token"
export MATRIX_USER_ID="@your_user:your_domain"
```

### Validation Errors

**If validation fails on startup, you'll see:**

```
ValueError: SECRET_KEY must be changed from default value in production!
Set SECRET_KEY environment variable to a secure random string.
```

**Generate secure keys:**
```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Development vs Production

**Validators allow defaults in development but require real values in production:**

```bash
# Development - uses defaults
export ENV=development

# Production - enforces real secrets
export ENV=production
export SECRET_KEY="real-secure-key-here"
export JWT_SECRET_KEY="real-jwt-key-here"
```

---

## 🎯 5. Custom Error Types

### Using Specific Exceptions

```python
from integrations.exceptions import (
    BridgeTimeoutError,
    AuthenticationError,
    RoomNotFoundError,
    MessageSendError
)

async def send_whatsapp_message(connection_id: str, content: str):
    try:
        connector = await get_connector(connection_id)
        await connector.send_message(room_id, content)

    except BridgeTimeoutError as e:
        logger.error(f"Bridge timeout: {e.timeout_seconds}s")
        # Retry logic here

    except AuthenticationError as e:
        logger.error(f"Auth failed: {e.phone_number}")
        # Redirect to login

    except RoomNotFoundError as e:
        logger.error(f"Room not found: {e.room_id}")
        # Create room or handle gracefully

    except MessageSendError as e:
        logger.error(f"Send failed to {e.recipient}: {e.message}")
        # Queue for retry
```

### Error Context

**All WhatsApp errors include rich context:**

```python
try:
    await connector.login_with_phone("+1234567890")
except BridgeTimeoutError as e:
    # Access error details
    print(f"Connection ID: {e.connection_id}")
    print(f"Bridge command: {e.bridge_command}")
    print(f"Timeout: {e.timeout_seconds}s")
    print(f"Details: {e.details}")
```

### Catching All WhatsApp Errors

```python
from integrations.exceptions import WhatsAppError

try:
    # WhatsApp operations
    await connector.sync_messages()

except WhatsAppError as e:
    # Catches all WhatsApp-specific errors
    logger.error(f"WhatsApp error: {e}")
    # Generic fallback handling
```

---

## 📊 6. Monitoring & Observability

### Check Encryption Status

```python
from sqlalchemy import select, func
from db.models.platform_connection import PlatformConnection

# Count encrypted vs legacy
encrypted_count = await db.scalar(
    select(func.count()).where(
        PlatformConnection._credentials_encrypted.isnot(None)
    )
)

legacy_count = await db.scalar(
    select(func.count()).where(
        PlatformConnection._credentials_encrypted.is_(None),
        PlatformConnection._credentials_legacy.isnot(None)
    )
)

print(f"Encrypted: {encrypted_count}, Legacy: {legacy_count}")
```

### Monitor Cache Health

```python
from services.connector_cache import get_connector_cache

cache = get_connector_cache()
stats = cache.get_stats()

print(f"Cache size: {stats['size']}/{stats['max_size']}")
print(f"Utilization: {stats['utilization']:.1%}")
print(f"Total accesses: {stats['total_accesses']}")

# Per-connection details
for conn in stats['connections']:
    print(f"  {conn['connection_id']}: {conn['access_count']} accesses")
```

### Log Credential Rotations

```python
from sqlalchemy import select
from db.models.platform_connection import PlatformConnection

# Recent rotations
result = await db.execute(
    select(PlatformConnection)
    .where(PlatformConnection.credentials_rotated_at.isnot(None))
    .order_by(PlatformConnection.credentials_rotated_at.desc())
    .limit(10)
)

for conn in result.scalars():
    print(f"{conn.platform}: rotated {conn.credentials_rotated_at} (version {conn.credentials_version})")
```

---

## 🚀 Migration Checklist

### For Existing Deployments

**Steps to migrate from unencrypted to encrypted credentials:**

1. ✅ **Backup database**
   ```bash
   pg_dump -U postgres mesh_development > backup_$(date +%Y%m%d).sql
   ```

2. ✅ **Run database migrations**
   ```bash
   cd apps/backend
   python -m alembic upgrade head
   ```

3. ✅ **Verify migrations applied**
   ```bash
   python -m alembic current
   # Should show: c33589a78bc8 (head)
   ```

4. ✅ **Migrate existing credentials**
   ```bash
   python scripts/migrate_encrypt_credentials.py
   ```

5. ✅ **Set production secrets**
   ```bash
   export ENV=production
   export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   ```

6. ✅ **Test application startup**
   ```bash
   python main.py
   # Should see: "Connector cache started"
   ```

7. ✅ **Verify encryption**
   ```bash
   python scripts/test_phase1.py
   # Should show: ✅ Encryption Service: PASSED
   ```

---

## 🔒 Security Best Practices

### Do's ✅

- ✅ Use strong SECRET_KEY in production (32+ characters)
- ✅ Rotate credentials every 90 days
- ✅ Run migration script to encrypt existing credentials
- ✅ Monitor cache utilization
- ✅ Use specific exception types for better error handling

### Don'ts ❌

- ❌ Don't use default SECRET_KEY in production
- ❌ Don't store credentials in code or version control
- ❌ Don't manually modify `_credentials_encrypted` column
- ❌ Don't bypass validators by setting ENV to development in production
- ❌ Don't catch generic `Exception` - use specific error types

---

## 📞 Need Help?

**Common Issues:**

**Q: Migration fails with "credentials column not found"**
A: Run `python -m alembic upgrade head` first

**Q: App fails with "SECRET_KEY must be changed"**
A: Set `SECRET_KEY` environment variable or set `ENV=development`

**Q: Connector cache not working**
A: Check logs for "Connector cache started" message

**Q: Credentials not decrypting**
A: Ensure SECRET_KEY hasn't changed since encryption

**For more help, check:**
- `PHASE1_COMPLETION_SUMMARY.md` - Full technical details
- `scripts/test_phase1.py` - Test examples
- `integrations/exceptions.py` - All error types
