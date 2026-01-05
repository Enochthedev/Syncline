#!/bin/bash

# =============================================================================
# WhatsApp Bridge Setup Script for Syncline
# =============================================================================
# This script sets up Synapse (Matrix server) and mautrix-whatsapp bridge
# for WhatsApp integration.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$BACKEND_DIR/config"

echo "🔧 Syncline WhatsApp Bridge Setup"
echo "================================="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker is available"
echo ""

# Step 1: Generate Synapse configuration
echo "📝 Step 1: Setting up Synapse (Matrix homeserver)..."
echo ""

# Create data directories
mkdir -p "$CONFIG_DIR/synapse"
mkdir -p "$CONFIG_DIR/mautrix-whatsapp"

# Check if Synapse config exists
if [ ! -f "$CONFIG_DIR/synapse/homeserver.yaml" ]; then
    echo "   Creating Synapse configuration..."
    
    # Generate initial Synapse config by running generate command
    docker run -it --rm \
        -v "$CONFIG_DIR/synapse:/data" \
        -e SYNAPSE_SERVER_NAME=localhost \
        -e SYNAPSE_REPORT_STATS=no \
        matrixdotorg/synapse:latest generate
    
    echo "   ✅ Synapse configuration generated"
else
    echo "   ⏭️  Synapse configuration already exists"
fi

# Step 2: Generate registration tokens
echo ""
echo "🔑 Step 2: Generating bridge registration tokens..."
echo ""

AS_TOKEN=$(openssl rand -hex 32)
HS_TOKEN=$(openssl rand -hex 32)
PROVISIONING_SECRET=$(openssl rand -hex 32)

echo "   AS Token: ${AS_TOKEN:0:16}..."
echo "   HS Token: ${HS_TOKEN:0:16}..."

# Update mautrix-whatsapp config with tokens
if [ -f "$CONFIG_DIR/mautrix-whatsapp/config.yaml" ]; then
    # Use sed to replace placeholder tokens
    sed -i.bak "s/syncline-whatsapp-as-token-change-in-production/$AS_TOKEN/g" "$CONFIG_DIR/mautrix-whatsapp/config.yaml"
    sed -i.bak "s/syncline-whatsapp-hs-token-change-in-production/$HS_TOKEN/g" "$CONFIG_DIR/mautrix-whatsapp/config.yaml"
    sed -i.bak "s/syncline-provisioning-secret-change-me/$PROVISIONING_SECRET/g" "$CONFIG_DIR/mautrix-whatsapp/config.yaml"
    rm -f "$CONFIG_DIR/mautrix-whatsapp/config.yaml.bak"
    echo "   ✅ Updated mautrix-whatsapp config"
fi

# Update Synapse registration file
if [ -f "$CONFIG_DIR/synapse/whatsapp-registration.yaml" ]; then
    sed -i.bak "s/syncline-whatsapp-as-token-change-in-production/$AS_TOKEN/g" "$CONFIG_DIR/synapse/whatsapp-registration.yaml"
    sed -i.bak "s/syncline-whatsapp-hs-token-change-in-production/$HS_TOKEN/g" "$CONFIG_DIR/synapse/whatsapp-registration.yaml"
    rm -f "$CONFIG_DIR/synapse/whatsapp-registration.yaml.bak"
    echo "   ✅ Updated Synapse registration file"
fi

# Step 3: Create Matrix user for Syncline
echo ""
echo "👤 Step 3: Creating Matrix user for Syncline..."
echo ""

# Start just the Synapse container temporarily
docker-compose -f "$BACKEND_DIR/docker-compose.yml" up -d postgres synapse

echo "   Waiting for Synapse to start..."
sleep 10

# Register a user
MATRIX_PASSWORD=$(openssl rand -base64 16)

# Use register_new_matrix_user or curl
docker exec remi_synapse register_new_matrix_user \
    -c /data/homeserver.yaml \
    -u syncline \
    -p "$MATRIX_PASSWORD" \
    -a \
    http://localhost:8008 2>/dev/null || echo "   User may already exist"

echo "   ✅ Matrix user 'syncline' ready"
echo ""
echo "   📋 Matrix credentials:"
echo "   ----------------------"
echo "   User ID: @syncline:localhost"
echo "   Password: $MATRIX_PASSWORD"
echo ""

# Step 4: Get access token
echo "🎫 Step 4: Getting Matrix access token..."
echo ""

ACCESS_TOKEN=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"type\":\"m.login.password\",\"user\":\"syncline\",\"password\":\"$MATRIX_PASSWORD\"}" \
    http://localhost:8008/_matrix/client/r0/login | jq -r '.access_token')

if [ "$ACCESS_TOKEN" != "null" ] && [ -n "$ACCESS_TOKEN" ]; then
    echo "   ✅ Got access token: ${ACCESS_TOKEN:0:20}..."
    
    # Save to env file
    echo "" >> "$BACKEND_DIR/.env"
    echo "# WhatsApp Matrix Bridge Configuration" >> "$BACKEND_DIR/.env"
    echo "MATRIX_HOMESERVER_URL=http://localhost:8008" >> "$BACKEND_DIR/.env"
    echo "MATRIX_USER_ID=@syncline:localhost" >> "$BACKEND_DIR/.env"
    echo "MATRIX_ACCESS_TOKEN=$ACCESS_TOKEN" >> "$BACKEND_DIR/.env"
    echo "WHATSAPP_BRIDGE_BOT_ID=@whatsappbot:localhost" >> "$BACKEND_DIR/.env"
    echo "WHATSAPP_PROVISIONING_SECRET=$PROVISIONING_SECRET" >> "$BACKEND_DIR/.env"
    
    echo "   ✅ Saved to .env file"
else
    echo "   ⚠️  Could not get access token. You may need to configure manually."
fi

# Step 5: Start all services
echo ""
echo "🚀 Step 5: Starting all services..."
echo ""

docker-compose -f "$BACKEND_DIR/docker-compose.yml" up -d

echo ""
echo "✅ WhatsApp Bridge Setup Complete!"
echo "=================================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Start the Syncline backend:"
echo "   cd $BACKEND_DIR && python main.py"
echo ""
echo "2. Create a WhatsApp connection via API:"
echo "   curl -X POST http://localhost:8000/api/v1/connections/whatsapp/initiate"
echo ""
echo "3. Get QR code for WhatsApp login:"
echo "   curl http://localhost:8000/api/v1/whatsapp/{connection_id}/login"
echo ""
echo "4. Scan QR code with WhatsApp mobile app"
echo "   (Settings > Linked Devices > Link a Device)"
echo ""
echo "5. Check connection status:"
echo "   curl http://localhost:8000/api/v1/whatsapp/{connection_id}/status"
echo ""
echo "📚 Documentation:"
echo "   - Matrix/Synapse: http://localhost:8008"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "🔐 Matrix Credentials saved to .env file"
echo ""
