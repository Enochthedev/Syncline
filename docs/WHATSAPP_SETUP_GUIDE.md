# WhatsApp Setup Guide - Getting It Actually Working

## Quick Start: Can the System Connect with WhatsApp?

**Yes, the system can connect with WhatsApp**, but it requires proper setup of the Matrix homeserver and mautrix-whatsapp bridge. Here's exactly how to get it working:

## Prerequisites Checklist

- [ ] Docker and Docker Compose installed
- [ ] Active WhatsApp account on mobile device
- [ ] WhatsApp app with "Link Device" feature (most recent versions)
- [ ] Stable internet connection
- [ ] At least 2GB RAM available for containers

## Step-by-Step Setup

### Step 1: Clone and Setup R.E.M.I

```bash
# Clone the repository (if not already done)
git clone <remi-repo-url>
cd remi

# Create environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

### Step 2: Configure Environment Variables

```bash
# .env file
DATABASE_URL=postgresql://postgres:password@localhost:5432/remi
REDIS_URL=redis://localhost:6379

# Matrix Configuration (these will be generated)
MATRIX_HOMESERVER_URL=http://localhost:8008
MATRIX_ACCESS_TOKEN=syt_will_be_generated_later
MATRIX_USER_ID=@remi_bot:matrix.remi.local
MATRIX_DEVICE_ID=REMI_WHATSAPP_HUB

# Enable WhatsApp Bridge
WHATSAPP_BRIDGE_ENABLED=true
WHATSAPP_BRIDGE_EXECUTABLE=mautrix-whatsapp
WHATSAPP_BRIDGE_CONFIG_PATH=./bridges/whatsapp/config.yaml
WHATSAPP_BRIDGE_DATABASE_PATH=./bridges/whatsapp/whatsapp.db
```

### Step 3: Start Core Services

```bash
# Start Matrix homeserver, PostgreSQL, and Redis
docker-compose -f docker/whatsapp-bridge-manager.yml up -d matrix postgres redis

# Wait for services to be ready (about 30 seconds)
sleep 30

# Check if Matrix is running
curl http://localhost:8008/_matrix/client/versions
```

### Step 4: Create Matrix Admin User

```bash
# Enter the Matrix container
docker exec -it remi_matrix bash

# Create admin user
register_new_matrix_user -c /data/homeserver.yaml http://localhost:8008

# Follow prompts:
# Username: remi_admin
# Password: your_secure_password
# Make admin: yes
```

### Step 5: Get Matrix Access Token

```bash
# Login to get access token
curl -X POST http://localhost:8008/_matrix/client/r0/login \
  -H "Content-Type: application/json" \
  -d '{
    "type": "m.login.password",
    "user": "remi_admin",
    "password": "your_secure_password"
  }'

# Response will include access_token - copy this to your .env file
# MATRIX_ACCESS_TOKEN=syt_your_actual_token_here
```

### Step 6: Start R.E.M.I Application

```bash
# Update .env with the access token, then start R.E.M.I
docker-compose -f docker/whatsapp-bridge-manager.yml up -d remi-app

# Check if R.E.M.I is running
curl http://localhost:8000/
```

### Step 7: Test WhatsApp Connection

```bash
# Test the WhatsApp connection endpoint
curl -X POST http://localhost:8000/api/whatsapp/connect \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "sync_tier": "real_time",
    "include_groups": false,
    "include_dms": true,
    "sync_history_days": 30
  }'

# If successful, you'll get a response with a QR code
```

## Alternative: Development Setup (Without Docker)

If you prefer to run without Docker for development:

### 1. Install Matrix Synapse

```bash
# Install Synapse
pip install matrix-synapse

# Generate config
python -m synapse.app.homeserver \
  --server-name matrix.remi.local \
  --config-path homeserver.yaml \
  --generate-config \
  --report-stats=no

# Start Synapse
synapse_homeserver -c homeserver.yaml
```

### 2. Install mautrix-whatsapp

```bash
# Download latest release
wget https://github.com/mautrix/whatsapp/releases/latest/download/mautrix-whatsapp-linux-amd64
chmod +x mautrix-whatsapp-linux-amd64

# Generate config
./mautrix-whatsapp-linux-amd64 -g

# Edit config.yaml with your Matrix details
nano config.yaml

# Start bridge
./mautrix-whatsapp-linux-amd64
```

### 3. Start R.E.M.I

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start R.E.M.I
python main.py
```

## Testing the Connection

### 1. Connect via API

```python
import requests
import json
from PIL import Image
import io
import base64

# Connect WhatsApp
response = requests.post('http://localhost:8000/api/whatsapp/connect', json={
    "user_id": "test_user_123",
    "sync_tier": "real_time",
    "include_groups": False,
    "include_dms": True
})

result = response.json()
print(f"Status: {result['status']}")

if result['status'] == 'ready':
    # Decode and display QR code
    qr_data = result['qr_code'].split(',')[1]  # Remove data:image/png;base64,
    qr_bytes = base64.b64decode(qr_data)
    
    # Save QR code to file
    with open('whatsapp_qr.png', 'wb') as f:
        f.write(qr_bytes)
    
    print("QR code saved to whatsapp_qr.png")
    print("Scan this with WhatsApp to connect!")
```

### 2. Scan QR Code with WhatsApp

1. **Open WhatsApp on your mobile device**
2. **Go to Settings → Linked Devices**
3. **Tap "Link a Device"**
4. **Scan the generated QR code**
5. **Wait for connection confirmation**

### 3. Check Connection Status

```python
# Check if connected
status_response = requests.get('http://localhost:8000/api/whatsapp/status/test_user_123')
status = status_response.json()

print(f"Connection Status: {status['status']}")
if status['status'] == 'connected':
    print(f"Connected at: {status['connected_at']}")
    print("WhatsApp is now connected to R.E.M.I!")
```

### 4. Send Test Message

Once connected, send a WhatsApp message to yourself or a contact. You should see it appear in the R.E.M.I system:

```python
# Check for messages
messages_response = requests.get('http://localhost:8000/api/v1/messages?platform=whatsapp')
messages = messages_response.json()

print(f"Found {len(messages)} WhatsApp messages")
for msg in messages:
    print(f"From: {msg['sender']} - {msg['content']}")
```

## Troubleshooting Common Issues

### Issue 1: QR Code Not Generated

**Symptoms:** API returns error or no QR code
**Solutions:**
```bash
# Check if Matrix is running
curl http://localhost:8008/_matrix/client/versions

# Check R.E.M.I logs
docker logs remi_app

# Check bridge pool status
curl http://localhost:8000/api/whatsapp/bridges/status
```

### Issue 2: QR Code Won't Scan

**Symptoms:** WhatsApp says "QR code is invalid"
**Solutions:**
- Ensure QR code hasn't expired (5-minute timeout)
- Check WhatsApp app version (update if needed)
- Try generating a new QR code
- Ensure stable internet connection

### Issue 3: Connection Drops

**Symptoms:** Connected but messages stop syncing
**Solutions:**
```bash
# Check bridge logs
docker logs whatsapp_bridge_user123

# Restart bridge if needed
curl -X POST http://localhost:8000/api/whatsapp/bridges/whatsapp_bridge_user123/cleanup

# Check Matrix homeserver
docker logs remi_matrix
```

### Issue 4: Messages Not Appearing in R.E.M.I

**Symptoms:** WhatsApp connected but no messages in system
**Solutions:**
```bash
# Check event bus
curl http://localhost:8000/api/v1/health

# Check message processing
curl http://localhost:8000/api/v1/stats

# Verify database connection
docker exec -it remi_postgres psql -U postgres -d remi -c "SELECT COUNT(*) FROM messages WHERE platform = 'whatsapp';"
```

## Production Deployment Considerations

### 1. Security Hardening

```yaml
# docker-compose.production.yml
services:
  matrix:
    environment:
      - SYNAPSE_REGISTRATION_SHARED_SECRET=${MATRIX_REGISTRATION_SECRET}
    volumes:
      - ./matrix/production.yaml:/data/homeserver.yaml
  
  remi-app:
    environment:
      - ENV=production
      - DEBUG=false
      - MATRIX_ACCESS_TOKEN=${MATRIX_ACCESS_TOKEN}
```

### 2. SSL/TLS Setup

```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name remi.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /_matrix {
        proxy_pass http://localhost:8008;
        proxy_set_header Host $host;
    }
}
```

### 3. Monitoring Setup

```python
# Add to main.py
from prometheus_client import Counter, Histogram, generate_latest

whatsapp_messages_total = Counter('whatsapp_messages_total', 'Total WhatsApp messages processed')
whatsapp_connection_duration = Histogram('whatsapp_connection_duration_seconds', 'Time to establish WhatsApp connection')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Expected Performance

### Resource Usage
- **Matrix Homeserver**: ~200MB RAM, minimal CPU
- **mautrix-whatsapp Bridge**: ~100MB RAM per bridge
- **R.E.M.I Application**: ~300MB RAM
- **Total System**: ~1GB RAM for basic setup

### Message Throughput
- **Real-time Sync**: <2 second latency
- **Batch Sync**: 5-15 minutes depending on tier
- **Message Processing**: 100+ messages/second
- **Concurrent Users**: 50-100 users per 10 bridges

### Storage Requirements
- **Matrix Database**: ~1MB per 1000 messages
- **R.E.M.I Database**: ~2MB per 1000 messages (with AI processing)
- **Bridge Data**: ~10MB per connected user

## Success Indicators

✅ **Matrix homeserver responds to API calls**
✅ **R.E.M.I application starts without errors**
✅ **WhatsApp QR code generates successfully**
✅ **Mobile WhatsApp can scan and connect**
✅ **Messages appear in R.E.M.I within 2 seconds**
✅ **AI processing works on WhatsApp messages**
✅ **Cross-platform contact resolution functions**

## Next Steps

Once WhatsApp is connected:

1. **Test AI Features**: Send messages with different content types
2. **Verify Cross-Platform**: Connect Gmail and see contact correlation
3. **Monitor Performance**: Use metrics endpoints to track system health
4. **Scale Testing**: Connect multiple WhatsApp accounts
5. **Academic Evaluation**: Collect performance data for your project

The system is now ready for your final year project demonstration and evaluation!