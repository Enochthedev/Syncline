# WhatsApp Sync - Quick Start Guide

## 🚀 Quick Implementation (5 Minutes)

### Step 1: Test Current Setup

First, let's diagnose your current WhatsApp integration:

```bash
cd apps/backend
python scripts/test_whatsapp_sync_enhanced.py
```

This will show you exactly what's working and what's not.

### Step 2: Update Your Routes

Add the enhanced routes to your API:

**In `apps/backend/api/routes/whatsapp/__init__.py`:**

```python
from .messaging_enhanced import router as messaging_enhanced_router

# Add to your app
app.include_router(
    messaging_enhanced_router,
    prefix="/api/whatsapp",
    tags=["whatsapp-enhanced"]
)
```

### Step 3: Use Enhanced Sync in Frontend

Update your frontend to use the new endpoint:

**Before:**
```javascript
// Old sync endpoint
const response = await fetch(`/api/whatsapp/${connectionId}/sync`, {
  method: 'POST'
});
```

**After:**
```javascript
// New enhanced sync with retry
const response = await fetch(`/api/whatsapp/${connectionId}/sync/enhanced`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ limit: 100, force: false })
});

const result = await response.json();
console.log(`Synced ${result.total_messages_synced} messages`);
console.log('Stats:', result.stats);
```

## 🔧 Common Issues & Solutions

### Issue 1: No rooms after login

**Quick Fix:**
```bash
# Run room discovery
curl -X POST "http://localhost:8000/api/whatsapp/${CONNECTION_ID}/rooms/discover" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Issue 2: Messages not syncing

**Quick Fix:**
```bash
# Run enhanced sync with diagnostics
curl -X POST "http://localhost:8000/api/whatsapp/${CONNECTION_ID}/sync/enhanced" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"limit": 100, "force": true}'
```

### Issue 3: Bridge not responding

**Quick Fix:**
```bash
# Check bridge status
docker logs syncline-whatsapp-bridge --tail 50

# Restart bridge if needed
docker-compose restart whatsapp-bridge

# Then trigger sync
curl -X POST "http://localhost:8000/api/whatsapp/${CONNECTION_ID}/bridge/sync" \
  -H "Authorization: Bearer ${TOKEN}"
```

## 📊 Monitoring & Diagnostics

### Run Full Diagnostics

```bash
# For specific connection
python scripts/test_whatsapp_sync_enhanced.py --connection-id <uuid>

# Via API
curl -X GET "http://localhost:8000/api/whatsapp/${CONNECTION_ID}/diagnostics" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Check Sync Status

```bash
curl -X GET "http://localhost:8000/api/whatsapp/${CONNECTION_ID}/sync/status" \
  -H "Authorization: Bearer ${TOKEN}"
```

## 🎯 Recommended Workflow

### For New Users (First Time Setup)

1. **User scans QR code** → Backend calls `/login`
2. **Poll login status** → `/login/status` until logged_in = true
3. **Trigger room discovery** → `/rooms/discover` (waits for bridge to create rooms)
4. **Run enhanced sync** → `/sync/enhanced` (syncs messages with retry)
5. **Check results** → `/sync/status` (verify sync completed)

### For Existing Users (Regular Sync)

1. **Check if logged in** → `/session/status`
2. **Run enhanced sync** → `/sync/enhanced` (automatic retry on failures)
3. **Monitor in background** → Background sync service runs every 5 minutes

## 💡 Best Practices

### 1. Always Use Enhanced Endpoints

```python
# ✅ Good - Uses retry logic
POST /api/whatsapp/{id}/sync/enhanced

# ❌ Old - No retry
POST /api/whatsapp/{id}/sync
```

### 2. Check Status Before Sync

```javascript
// Check login status first
const status = await fetch(`/api/whatsapp/${id}/session/status`);
const { is_logged_in } = await status.json();

if (is_logged_in) {
  // Now sync
  await fetch(`/api/whatsapp/${id}/sync/enhanced`, { method: 'POST' });
}
```

### 3. Handle Errors Gracefully

```javascript
try {
  const response = await fetch(`/api/whatsapp/${id}/sync/enhanced`, {
    method: 'POST',
    body: JSON.stringify({ limit: 100 })
  });

  const result = await response.json();

  if (result.success) {
    console.log(`✓ Synced ${result.total_messages_synced} messages`);
  } else {
    console.error('Sync failed:', result.stats);

    // Show user-friendly message
    if (result.error.includes('not logged in')) {
      showError('Please scan QR code first');
    } else if (result.stats.sync_attempts >= 5) {
      showError('Sync failed after retries. Please try again later.');
    }
  }
} catch (error) {
  console.error('Network error:', error);
  showError('Connection error. Check your network.');
}
```

## 🚑 Emergency Troubleshooting

If everything is broken:

```bash
# 1. Check configuration
echo "MATRIX_HOMESERVER_URL=$MATRIX_HOMESERVER_URL"
echo "MATRIX_ACCESS_TOKEN=$MATRIX_ACCESS_TOKEN"
echo "MATRIX_USER_ID=$MATRIX_USER_ID"
echo "WHATSAPP_BRIDGE_BOT_ID=$WHATSAPP_BRIDGE_BOT_ID"

# 2. Check bridge is running
docker ps | grep whatsapp-bridge

# 3. Check bridge logs
docker logs syncline-whatsapp-bridge --tail 100

# 4. Restart bridge
docker-compose restart whatsapp-bridge

# 5. Run diagnostics
python scripts/test_whatsapp_sync_enhanced.py

# 6. Check database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM messages WHERE platform='whatsapp';"
```

## 📱 Mobile App Integration

### After User Scans QR Code

```javascript
// 1. Poll for login completion (with auto-sync)
const pollLogin = async () => {
  const response = await fetch(
    `/api/whatsapp/${connectionId}/session/status`
  );
  const { is_logged_in, auto_sync } = await response.json();

  if (is_logged_in) {
    console.log('Logged in!', auto_sync);

    // 2. Wait a bit for auto-sync to complete
    await new Promise(r => setTimeout(r, 5000));

    // 3. Trigger enhanced sync to ensure all messages
    await fetch(`/api/whatsapp/${connectionId}/sync/enhanced`, {
      method: 'POST',
      body: JSON.stringify({ limit: 100 })
    });

    return true;
  }

  return false;
};

// Poll every 3 seconds
const interval = setInterval(async () => {
  const done = await pollLogin();
  if (done) clearInterval(interval);
}, 3000);
```

### Background Sync

```javascript
// Set up periodic sync in the background
const startBackgroundSync = async () => {
  const response = await fetch(
    `/api/whatsapp/${connectionId}/background-sync/start`,
    {
      method: 'POST',
      body: JSON.stringify({ sync_interval: 300 }) // 5 minutes
    }
  );

  const result = await response.json();
  console.log('Background sync started:', result);
};
```

## 🎓 Understanding the Enhanced Version

### What's Different?

| Feature | Old Version | Enhanced Version |
|---------|-------------|------------------|
| Bridge timeout | 5 attempts (5s) | 15 attempts (30s) |
| Retry on failure | ❌ No | ✅ Yes (5 retries) |
| Room discovery | Basic | With retry + wait |
| Diagnostics | ❌ None | ✅ Comprehensive |
| Logging | Basic | Detailed with prefixes |
| Statistics | ❌ None | ✅ Full metrics |
| Race prevention | ❌ No | ✅ Per-connection locks |

### When to Use Each Endpoint

- **`/sync/enhanced`** - Always use this for message sync
- **`/rooms/discover`** - When rooms aren't appearing
- **`/bridge/sync`** - When bridge seems stuck
- **`/diagnostics`** - When troubleshooting issues
- **`/sync/status`** - To check if sync is running

## 🎉 Success Checklist

After implementation, verify:

- [ ] Diagnostic script runs without errors
- [ ] User can scan QR code and login
- [ ] Rooms appear within 10 seconds of login
- [ ] Messages sync successfully
- [ ] Enhanced sync endpoint returns statistics
- [ ] Retry logic works (check logs)
- [ ] Background sync is running (if enabled)

## 📞 Need Help?

If you're still having issues:

1. Run full diagnostics: `python scripts/test_whatsapp_sync_enhanced.py`
2. Check the generated JSON report
3. Look for failed tests and review error messages
4. Check bridge logs: `docker logs syncline-whatsapp-bridge`
5. Review the comprehensive guide: `WHATSAPP_SYNC_FIX_GUIDE.md`

## 🔗 Key Files Reference

```
apps/backend/
├── integrations/
│   ├── whatsapp_connector.py                 # Original (still works)
│   └── whatsapp_connector_enhanced.py        # Enhanced (recommended)
├── services/
│   ├── whatsapp_message_sync.py             # Original (still works)
│   ├── whatsapp_sync_enhanced.py            # Enhanced (recommended)
│   └── whatsapp_session_manager.py          # Session management
├── api/routes/whatsapp/
│   ├── auth.py                              # Login/logout
│   ├── messaging.py                         # Original endpoints
│   └── messaging_enhanced.py                # Enhanced endpoints
├── scripts/
│   └── test_whatsapp_sync_enhanced.py       # Diagnostic tool
├── WHATSAPP_SYNC_FIX_GUIDE.md              # Comprehensive guide
└── WHATSAPP_QUICK_START.md                 # This file
```

---

**That's it! You should now have a fully working WhatsApp integration with reliable message syncing. 🎊**
