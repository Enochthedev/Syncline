# WhatsApp Connection Troubleshooting Guide

## 🚨 Quick Fix for "Can't get pairing code" Issue

### Step 1: Run Diagnostics

```bash
cd apps/backend
python scripts/debug_whatsapp_connection.py
```

This will tell you exactly what's wrong.

### Step 2: Check Common Issues

#### Issue 1: Missing Configuration

**Symptoms:** `500 error` or `Missing configuration` error

**Fix:**

Check your `.env` file has these variables:

```env
MATRIX_HOMESERVER_URL=http://localhost:8008
MATRIX_ACCESS_TOKEN=your_token_here
MATRIX_USER_ID=@syncline:localhost
WHATSAPP_BRIDGE_BOT_ID=@whatsappbot:localhost
```

**How to get these values:**

1. **MATRIX_ACCESS_TOKEN**:
   ```bash
   # Generate a new token
   curl -X POST http://localhost:8008/_matrix/client/r0/login \
     -H "Content-Type: application/json" \
     -d '{"type":"m.login.password","user":"syncline","password":"your_password"}'

   # Look for "access_token" in the response
   ```

2. **MATRIX_USER_ID**: Should be `@syncline:localhost` (or your configured username)

3. **WHATSAPP_BRIDGE_BOT_ID**: Should be `@whatsappbot:localhost`

#### Issue 2: Bridge Not Running

**Symptoms:** Connection timeout, no response from bridge

**Check:**

```bash
docker ps | grep whatsapp
```

**Fix:**

```bash
# Start the bridge
docker-compose up -d whatsapp-bridge

# Check logs
docker logs syncline-whatsapp-bridge
```

#### Issue 3: Matrix Homeserver Not Accessible

**Symptoms:** `Connection failed` error

**Check:**

```bash
curl http://localhost:8008/_matrix/client/versions
```

**Expected response:** JSON with version information

**Fix:**

```bash
# Start Matrix homeserver
docker-compose up -d synapse

# Check logs
docker logs syncline-synapse
```

#### Issue 4: Invalid Access Token

**Symptoms:** `Authorization failed` or `401` error

**Fix:**

Generate a new access token (see Issue 1 above) and update your `.env` file.

### Step 3: Test the Fix

After fixing the configuration, test it:

```bash
# Run diagnostics again
python scripts/debug_whatsapp_connection.py
```

Should see:
```
✓ All configuration variables are set
✓ Successfully connected to Matrix
✓ Authenticated as: @syncline:localhost
```

### Step 4: Use Enhanced Endpoint

Update your mobile app to use the enhanced endpoint with better error handling:

**Before:**
```javascript
POST /api/whatsapp/{id}/login/phone
```

**After:**
```javascript
POST /api/whatsapp/{id}/login/phone-enhanced
```

**Add the route in your backend:**

In `apps/backend/main.py` or router configuration:

```python
from api.routes.whatsapp.auth_enhanced import router as whatsapp_auth_enhanced_router

app.include_router(
    whatsapp_auth_enhanced_router,
    prefix="/api/whatsapp",
    tags=["whatsapp-auth-enhanced"]
)
```

## 🔍 Detailed Diagnostics

### Check Backend Logs

```bash
# If using Docker
docker logs syncline-backend --tail 100 --follow

# If running directly
tail -f logs/app.log | grep -E '\[PHONE_LOGIN\]|\[BRIDGE\]'
```

### Check Bridge Logs

```bash
docker logs syncline-whatsapp-bridge --tail 100 --follow
```

**Look for:**
- Login attempts
- Error messages
- Bridge bot responses

### Check Matrix Logs

```bash
docker logs syncline-synapse --tail 100 --follow
```

**Look for:**
- Authentication errors
- API requests
- Rate limiting

## 🛠️ Common Error Messages

### "Failed to get pairing code from bridge"

**Causes:**
1. Bridge is not running
2. Bridge is not responding in time
3. Bridge bot is not configured

**Solutions:**
1. Check bridge is running: `docker ps | grep whatsapp`
2. Check bridge logs: `docker logs syncline-whatsapp-bridge`
3. Restart bridge: `docker-compose restart whatsapp-bridge`
4. Use enhanced endpoint (longer timeout)

### "Authentication failed"

**Causes:**
1. Invalid Matrix access token
2. User doesn't exist
3. Permissions issue

**Solutions:**
1. Generate new access token
2. Verify user exists in Matrix
3. Check user permissions

### "Connection timeout"

**Causes:**
1. Matrix homeserver not accessible
2. Network issues
3. Bridge not responding

**Solutions:**
1. Check homeserver: `curl http://localhost:8008/_matrix/client/versions`
2. Check Docker network: `docker network ls`
3. Restart services: `docker-compose restart`

### "Missing configuration"

**Causes:**
1. Environment variables not set
2. .env file not loaded

**Solutions:**
1. Check .env file exists
2. Verify all variables are set
3. Restart backend to reload .env

## 📱 Mobile App Integration

### Enhanced Error Handling

```javascript
try {
  const response = await fetch(
    `/api/whatsapp/${connectionId}/login/phone-enhanced`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: '+1234567890' })
    }
  );

  const result = await response.json();

  if (!response.ok) {
    // Enhanced error includes suggestions
    console.error('Login failed:', result.detail);

    if (result.detail.suggestions) {
      result.detail.suggestions.forEach(s => console.log('💡', s));
    }

    // Show user-friendly error
    showError('Could not connect to WhatsApp. Please try again.');
  } else {
    // Success
    if (result.check_phone) {
      showMessage('Check your WhatsApp for a notification!');
    } else {
      showPairingCode(result.pairing_code);
    }
  }
} catch (error) {
  console.error('Network error:', error);
  showError('Network error. Check your connection.');
}
```

### Use Diagnostics Endpoint

Before attempting login, check if everything is configured:

```javascript
const checkConfiguration = async () => {
  try {
    const response = await fetch(
      `/api/whatsapp/${connectionId}/login/diagnostics`
    );

    const diagnostics = await response.json();

    if (!diagnostics.summary.all_passed) {
      // Show user what's wrong
      console.error('Configuration issues:', diagnostics.recommendations);

      // Alert user
      showError(
        'WhatsApp is not configured correctly. Please contact support.'
      );
      return false;
    }

    return true;
  } catch (error) {
    console.error('Diagnostics failed:', error);
    return false;
  }
};

// Before login
const attemptLogin = async (phone) => {
  const configured = await checkConfiguration();

  if (!configured) {
    return;
  }

  // Proceed with login...
};
```

## 🔄 Complete Reset

If nothing works, try a complete reset:

```bash
# 1. Stop all services
docker-compose down

# 2. Remove WhatsApp bridge data (⚠️  This will log you out)
rm -rf data/whatsapp-bridge/*

# 3. Restart services
docker-compose up -d

# 4. Generate new access token
# (See Issue 1 above)

# 5. Update .env with new token

# 6. Restart backend
docker-compose restart backend

# 7. Run diagnostics
python scripts/debug_whatsapp_connection.py

# 8. Try login again
```

## ✅ Verification Checklist

After fixing, verify:

- [ ] Diagnostic script passes all tests
- [ ] Bridge is running (`docker ps`)
- [ ] Matrix is accessible (`curl http://localhost:8008/_matrix/client/versions`)
- [ ] Access token is valid
- [ ] Enhanced endpoint returns pairing code
- [ ] Mobile app can connect

## 📞 Still Not Working?

If you've tried everything:

1. **Check Docker logs for all services:**
   ```bash
   docker-compose logs --tail=100
   ```

2. **Verify network connectivity:**
   ```bash
   docker network inspect syncline_default
   ```

3. **Check if ports are available:**
   ```bash
   lsof -i :8008  # Matrix homeserver
   lsof -i :29318 # WhatsApp bridge
   ```

4. **Try with QR code instead of phone pairing:**
   ```bash
   GET /api/whatsapp/{id}/login
   ```

5. **Review documentation:**
   - Check `WHATSAPP_README.md`
   - Check `WHATSAPP_QUICK_START.md`
   - Review bridge logs for specific errors

## 🎯 Quick Command Reference

```bash
# Diagnostics
python scripts/debug_whatsapp_connection.py

# Check services
docker ps

# View logs
docker logs syncline-whatsapp-bridge --tail 50
docker logs syncline-backend --tail 50

# Restart services
docker-compose restart whatsapp-bridge
docker-compose restart backend

# Test Matrix
curl http://localhost:8008/_matrix/client/versions

# Test bridge health
curl http://localhost:29318/health
```

---

**Need more help?** Run the diagnostics and share the output!
