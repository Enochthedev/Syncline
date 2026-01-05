# 📧 Gmail & WhatsApp Integration Setup

This guide walks you through setting up Gmail and WhatsApp integrations for Syncline, plus testing message extraction per contact.

---

## 🎯 Overview

| Platform | Implementation Status | Auth Type | Complexity |
|----------|----------------------|-----------|------------|
| **Gmail** | ✅ **Fully Implemented** | OAuth 2.0 | Medium |
| **WhatsApp** | ⚠️ **Placeholder Only** | Matrix Bridge OR WhatsApp Business API | Higher |

---

## 📧 Part 1: Gmail Setup (Ready to Use!)

Gmail is fully implemented with OAuth 2.0, push notifications, and message fetching.

### Step 1: Create Google Cloud Project

1. **Go to Google Cloud Console**
   - Open: https://console.cloud.google.com/
   
2. **Create a New Project** (or select existing)
   - Click the project dropdown at the top
   - Click "New Project"
   - Name: `Syncline` or similar
   - Click "Create"

3. **Enable Gmail API**
   - Go to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click on it → Click "Enable"

### Step 2: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select **External** (for testing) or **Internal** (if you have Google Workspace)
3. Fill in required fields:
   - App name: `Syncline`
   - User support email: your email
   - Developer contact: your email
4. Click "Save and Continue"
5. **Add Scopes** → Click "Add or Remove Scopes":
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
6. Click "Save and Continue"
7. **Add Test Users** (for development):
   - Add your Gmail address
8. Click "Save and Continue"

### Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: **Web application**
4. Name: `Syncline Backend`
5. **Authorized redirect URIs** - Add these:
   ```
   http://localhost:8000/api/v1/connections/gmail/callback
   http://localhost:8000/auth/gmail/callback
   syncline://oauth/callback
   ```
6. Click "Create"
7. **Copy and save**:
   - Client ID
   - Client Secret

### Step 4: Add Credentials to Backend

Create or update `/Users/user/Code/Syncline/apps/backend/.env`:

```bash
# Gmail OAuth 2.0
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REDIRECT_URI=http://localhost:8000/api/v1/connections/gmail/callback

# Gmail API Scopes
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/userinfo.email
```

---

## 💬 Part 2: WhatsApp Setup (via Matrix Bridge)

WhatsApp integration uses the **mautrix-whatsapp** bridge which connects your personal WhatsApp to Matrix protocol.

### How It Works

```
WhatsApp Mobile App
       ↓ (QR code pairing, like WhatsApp Web)
mautrix-whatsapp Bridge
       ↓ (Matrix protocol)
Synapse (Matrix Homeserver)
       ↓ (Matrix Client-Server API)
Syncline Backend
```

### Quick Setup (Automated)

Run the setup script to configure everything automatically:

```bash
cd /Users/user/Code/Syncline/apps/backend
./scripts/setup_whatsapp_bridge.sh
```

This script will:
1. ✅ Generate Synapse configuration
2. ✅ Create security tokens for bridge communication
3. ✅ Create a Matrix user for Syncline
4. ✅ Save credentials to `.env` file
5. ✅ Start all Docker services

### Manual Setup (Step by Step)

If you prefer manual setup:

#### Step 1: Start Docker Services

```bash
cd /Users/user/Code/Syncline/apps/backend
docker-compose up -d postgres synapse whatsapp-bridge
```

#### Step 2: Create Matrix User

```bash
# Register Syncline user on Matrix
docker exec -it remi_synapse register_new_matrix_user \
    -c /data/homeserver.yaml \
    -u syncline \
    -p YOUR_SECURE_PASSWORD \
    -a \
    http://localhost:8008
```

#### Step 3: Get Access Token

```bash
# Login to get access token
curl -X POST \
    -H "Content-Type: application/json" \
    -d '{"type":"m.login.password","user":"syncline","password":"YOUR_PASSWORD"}' \
    http://localhost:8008/_matrix/client/r0/login
```

Response:
```json
{
    "access_token": "syt_c3luY2xpbmU_...",
    "user_id": "@syncline:localhost",
    ...
}
```

#### Step 4: Add to `.env`

```bash
# Add to apps/backend/.env
MATRIX_HOMESERVER_URL=http://localhost:8008
MATRIX_USER_ID=@syncline:localhost
MATRIX_ACCESS_TOKEN=syt_c3luY2xpbmU_...
WHATSAPP_BRIDGE_BOT_ID=@whatsappbot:localhost
```

### Connecting Your WhatsApp

Once the bridge is running:

1. **Create Connection** (via API or app):
   ```bash
   curl -X POST http://localhost:8000/api/v1/connections/whatsapp/initiate \
       -H "Content-Type: application/json" \
       -d '{"user_id": "your-user-id"}'
   ```

2. **Get QR Code**:
   ```bash
   curl http://localhost:8000/api/v1/whatsapp/{connection_id}/login
   ```

3. **Scan QR Code** with WhatsApp mobile app:
   - Open WhatsApp → Settings → Linked Devices → Link a Device
   - Scan the QR code displayed

4. **Verify Connection**:
   ```bash
   curl http://localhost:8000/api/v1/whatsapp/{connection_id}/status
   ```

### Environment Variables

```bash
# Matrix/WhatsApp Bridge Configuration
MATRIX_HOMESERVER_URL=http://localhost:8008
MATRIX_USER_ID=@syncline:localhost
MATRIX_ACCESS_TOKEN=your-matrix-access-token
WHATSAPP_BRIDGE_BOT_ID=@whatsappbot:localhost
WHATSAPP_BRIDGE_ENABLED=true
```

### Troubleshooting WhatsApp Bridge

**Bridge not connecting:**
```bash
# Check bridge logs
docker logs remi_whatsapp_bridge

# Restart bridge
docker-compose restart whatsapp-bridge
```

**QR Code not appearing:**
```bash
# Send login command directly to bridge
# In Matrix client, message @whatsappbot:localhost with: !wa login
```

**Messages not syncing:**
- Ensure your phone has internet connection
- Check that WhatsApp is still linked (phone → Linked Devices)
- Bridge syncs message history on first connect (may take a few minutes)

### ⚠️ Important Considerations

#### Downsides of the Matrix Bridge Approach

| Concern | Details |
|---------|---------|
| **Unofficial** | Not sanctioned by Meta - uses WhatsApp Web protocol. Account *could* be banned (rare with normal usage) |
| **Phone Dependency** | Phone must stay online. Disconnects after ~14 days without phone activity |
| **Infrastructure** | Adds 2 services (Synapse + bridge) = more complexity, ~500MB+ RAM |
| **Message Delays** | Messages route through multiple hops (usually <1s, but not instant) |
| **Maintenance** | Need to update bridge when WhatsApp changes protocol |
| **Linked Device Slot** | Uses 1 of your 4 WhatsApp linked device slots |

#### Upsides (Why It's Still Worth It)

| Benefit | Why It Matters |
|---------|----------------|
| **Personal accounts** | WhatsApp Business API only works for verified businesses |
| **Full message access** | Get all messages, not just API-sent ones |
| **Two-way sync** | Read status, typing indicators, receipts |
| **Open source** | Can inspect/modify, no vendor lock-in |
| **Multi-platform** | Same approach works for Instagram, LinkedIn, Signal |

#### Alternatives Comparison

| Approach | Personal Account | Official | Complexity | Reliability |
|----------|-----------------|----------|------------|-------------|
| **Matrix Bridge** | ✅ Yes | ❌ No | 🔴 High | 🟡 Medium |
| **WhatsApp Business API** | ❌ Business only | ✅ Yes | 🟡 Medium | 🟢 High |
| **Telegram Bot** | ✅ Yes | ✅ Yes | 🟢 Low | 🟢 High |

#### Reducing Risk
1. **Normal usage** - Don't spam or abuse
2. **One account per user** - Don't share accounts
3. **Keep updated** - Follow mautrix releases
4. **User consent** - Users know they're linking via third-party

---

## 🧪 Part 3: Testing Message Extraction Per Contact

### Backend API Endpoints for Messages & Contacts

Your backend already has these endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/v1/contacts` | GET | List all contacts |
| `GET /api/v1/contacts/{id}` | GET | Get contact details |
| `GET /api/v1/contacts/{id}/threads` | GET | Get threads for a contact |
| `GET /api/v1/messages?contact_id={id}` | GET | Get messages for a contact |
| `GET /api/v1/messages/search?query=...&contact_ids=...` | GET | Search messages by contact |

### Test Commands (once backend is running)

```bash
# 1. Start the backend
cd /Users/user/Code/Syncline/apps/backend
python main.py

# 2. Check health
curl http://localhost:8000/health

# 3. List all contacts
curl http://localhost:8000/api/v1/contacts

# 4. Get contact details
curl http://localhost:8000/api/v1/contacts/{contact_id}

# 5. Get threads for a contact
curl http://localhost:8000/api/v1/contacts/{contact_id}/threads

# 6. Get messages filtered by contact
curl "http://localhost:8000/api/v1/messages?contact_id={contact_id}"

# 7. Search messages for a contact
curl "http://localhost:8000/api/v1/messages/search?query=hello&contact_ids={contact_id}"
```

### Frontend API (Already Implemented)

The mobile app already has these API modules:

**`src/api/endpoints/contacts.ts`**:
```typescript
// List contacts
const response = await contactsAPI.listContacts({ search: 'John', limit: 20 });

// Get single contact
const contact = await contactsAPI.getContact(contactId);
```

**`src/api/endpoints/connections.ts`**:
```typescript
// Connect Gmail
const response = await connectionsAPI.initiateConnection('gmail', userId);
await Linking.openURL(response.authorization_url);
```

---

## 🚀 Quick Start Steps

### For Gmail (Do This First!)

1. ✅ Create Google Cloud project and enable Gmail API
2. ✅ Configure OAuth consent screen
3. ✅ Create OAuth credentials
4. ✅ Add credentials to `.env` file
5. ✅ Start backend: `cd apps/backend && python main.py`
6. ✅ Test connection flow via API or mobile app

### For WhatsApp (After Gmail Works)

Choose your path:
- **Business use** → WhatsApp Business API
- **Personal testing** → Matrix Bridge (complex setup)
- **Quick alternative** → Use Telegram for now (much simpler!)

---

## 📁 Files to Create/Update

### 1. Create `.env` file in backend

```bash
# File: /Users/user/Code/Syncline/apps/backend/.env

# =============================================================================
# Core Settings
# =============================================================================
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/syncline_dev
REDIS_URL=redis://localhost:6379
SECRET_KEY=generate-with-python-secrets
JWT_SECRET_KEY=generate-with-python-secrets

# =============================================================================
# Gmail OAuth 2.0
# =============================================================================
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REDIRECT_URI=http://localhost:8000/api/v1/connections/gmail/callback

# =============================================================================
# WhatsApp (Choose one approach)
# =============================================================================
# Option A: WhatsApp Business API
# WHATSAPP_PHONE_NUMBER_ID=
# WHATSAPP_BUSINESS_ACCOUNT_ID=
# WHATSAPP_ACCESS_TOKEN=

# Option B: Matrix Bridge
# MATRIX_HOMESERVER_URL=http://localhost:8008
# MATRIX_ACCESS_TOKEN=

# =============================================================================
# AI (Local - No API key needed)
# =============================================================================
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_CHAT_MODEL=llama3.2:3b
DEFAULT_EMBEDDING_MODEL=nomic-embed-text:latest

# =============================================================================
# CORS (for mobile app)
# =============================================================================
CORS_ORIGINS=["http://localhost:3000","http://localhost:8081","http://localhost:19000"]
```

### 2. Generate Security Keys

```bash
cd /Users/user/Code/Syncline/apps/backend

# Generate and append to .env
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env
```

---

## 🔄 Testing Flow: Gmail → Contacts → Messages

```
1. User opens mobile app
        ↓
2. Goes to Connections screen
        ↓
3. Taps "Connect Gmail"
        ↓
4. Backend initiates OAuth → Returns authorization URL
        ↓
5. App opens browser → User logs into Google
        ↓
6. Google redirects to callback URL with auth code
        ↓
7. Backend exchanges code for tokens → Stores credentials
        ↓
8. Backend starts syncing Gmail messages
        ↓
9. Messages are normalized → Contacts are created
        ↓
10. User can now view:
    - Contacts list
    - Threads per contact
    - Messages per contact
    - AI-generated insights
```

---

## ❓ Need Help?

Let me know:
1. If you want me to help you create the `.env` file with placeholders
2. If you need help implementing the WhatsApp connector (Business API or Matrix)
3. If you want to test with Telegram first (simpler alternative)
4. If you want me to add a "messages per contact" endpoint to the frontend API

**Ready when you are!** 🚀
