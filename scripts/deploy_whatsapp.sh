#!/bin/bash

# WhatsApp Integration Deployment Script
# This script sets up the complete WhatsApp integration system

set -e  # Exit on any error

echo "🚀 Starting WhatsApp Integration Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        print_status "Creating .env file..."
        cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/remi
REDIS_URL=redis://localhost:6379

# Matrix Configuration (will be updated after Matrix setup)
MATRIX_HOMESERVER_URL=http://localhost:8008
MATRIX_ACCESS_TOKEN=
MATRIX_USER_ID=
MATRIX_DEVICE_ID=REMI_WHATSAPP_HUB

# WhatsApp Bridge Configuration
WHATSAPP_BRIDGE_ENABLED=true
WHATSAPP_BRIDGE_EXECUTABLE=mautrix-whatsapp
WHATSAPP_BRIDGE_CONFIG_PATH=./bridges/whatsapp/config.yaml
WHATSAPP_BRIDGE_DATABASE_PATH=./bridges/whatsapp/whatsapp.db

# Application Configuration
ENV=development
DEBUG=true
EOF
        print_success "Created .env file"
    else
        print_warning ".env file already exists, skipping creation"
    fi
    
    # Create necessary directories
    mkdir -p bridges/whatsapp
    mkdir -p logs
    mkdir -p docker/matrix
    
    print_success "Environment setup complete"
}

# Start core services
start_core_services() {
    print_status "Starting core services (Matrix, PostgreSQL, Redis)..."
    
    # Start only core services first
    docker-compose -f docker/whatsapp-bridge-manager.yml up -d matrix postgres redis
    
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check if Matrix is ready
    local retries=0
    while [ $retries -lt 10 ]; do
        if curl -s http://localhost:8008/_matrix/client/versions > /dev/null 2>&1; then
            print_success "Matrix homeserver is ready"
            break
        fi
        print_status "Waiting for Matrix homeserver... (attempt $((retries + 1))/10)"
        sleep 10
        retries=$((retries + 1))
    done
    
    if [ $retries -eq 10 ]; then
        print_error "Matrix homeserver failed to start"
        exit 1
    fi
    
    print_success "Core services are running"
}

# Setup Matrix admin user
setup_matrix_user() {
    print_status "Setting up Matrix admin user..."
    
    # Check if admin user already exists
    if docker exec remi_matrix register_new_matrix_user -c /data/homeserver.yaml http://localhost:8008 --help > /dev/null 2>&1; then
        print_status "Creating Matrix admin user..."
        echo "Please create an admin user for Matrix:"
        echo "Username: remi_admin"
        echo "Password: (choose a secure password)"
        echo "Make admin: yes"
        
        docker exec -it remi_matrix register_new_matrix_user -c /data/homeserver.yaml http://localhost:8008
        
        # Get access token
        print_status "Getting access token..."
        echo "Please enter the password you just created:"
        read -s password
        
        response=$(curl -s -X POST http://localhost:8008/_matrix/client/r0/login \
            -H "Content-Type: application/json" \
            -d "{\"type\": \"m.login.password\", \"user\": \"remi_admin\", \"password\": \"$password\"}")
        
        access_token=$(echo $response | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        user_id=$(echo $response | grep -o '"user_id":"[^"]*' | cut -d'"' -f4)
        
        if [ -n "$access_token" ]; then
            # Update .env file
            sed -i.bak "s/MATRIX_ACCESS_TOKEN=.*/MATRIX_ACCESS_TOKEN=$access_token/" .env
            sed -i.bak "s/MATRIX_USER_ID=.*/MATRIX_USER_ID=$user_id/" .env
            print_success "Matrix user setup complete"
        else
            print_error "Failed to get access token. Please check your credentials."
            exit 1
        fi
    else
        print_warning "Matrix user registration tool not available, skipping user creation"
    fi
}

# Start R.E.M.I application
start_remi_app() {
    print_status "Starting R.E.M.I application..."
    
    # Start the main application
    docker-compose -f docker/whatsapp-bridge-manager.yml up -d remi-app
    
    print_status "Waiting for R.E.M.I application to be ready..."
    sleep 20
    
    # Check if R.E.M.I is ready
    local retries=0
    while [ $retries -lt 10 ]; do
        if curl -s http://localhost:8000/ > /dev/null 2>&1; then
            print_success "R.E.M.I application is ready"
            break
        fi
        print_status "Waiting for R.E.M.I application... (attempt $((retries + 1))/10)"
        sleep 10
        retries=$((retries + 1))
    done
    
    if [ $retries -eq 10 ]; then
        print_error "R.E.M.I application failed to start"
        exit 1
    fi
}

# Test WhatsApp integration
test_whatsapp_integration() {
    print_status "Testing WhatsApp integration..."
    
    # Test bridge status endpoint
    if curl -s http://localhost:8000/api/whatsapp/bridges/status > /dev/null 2>&1; then
        print_success "WhatsApp bridge status endpoint is working"
    else
        print_warning "WhatsApp bridge status endpoint is not responding"
    fi
    
    # Test connection endpoint
    print_status "Testing WhatsApp connection endpoint..."
    response=$(curl -s -X POST http://localhost:8000/api/whatsapp/connect \
        -H "Content-Type: application/json" \
        -d '{
            "user_id": "test_user_123",
            "sync_tier": "real_time",
            "include_groups": false,
            "include_dms": true
        }')
    
    if echo "$response" | grep -q "status"; then
        print_success "WhatsApp connection endpoint is working"
        echo "Response: $response"
    else
        print_warning "WhatsApp connection endpoint returned unexpected response"
        echo "Response: $response"
    fi
}

# Show deployment status
show_status() {
    print_status "Deployment Status:"
    echo ""
    
    # Show running containers
    echo "Running containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    
    # Show service URLs
    echo "Service URLs:"
    echo "  R.E.M.I Application: http://localhost:8000"
    echo "  R.E.M.I API Docs: http://localhost:8000/docs"
    echo "  Matrix Homeserver: http://localhost:8008"
    echo "  PostgreSQL: localhost:5432"
    echo "  Redis: localhost:6379"
    echo ""
    
    # Show next steps
    echo "Next Steps:"
    echo "1. Open http://localhost:8000/docs in your browser"
    echo "2. Try the WhatsApp connection endpoint:"
    echo "   POST /api/whatsapp/connect"
    echo "3. Scan the QR code with your WhatsApp mobile app"
    echo "4. Start sending messages!"
    echo ""
    
    print_success "Deployment complete! 🎉"
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    docker-compose -f docker/whatsapp-bridge-manager.yml down
    print_success "Cleanup complete"
}

# Main deployment flow
main() {
    echo "🔧 WhatsApp Integration Deployment Script"
    echo "=========================================="
    echo ""
    
    # Check if user wants to cleanup
    if [ "$1" = "cleanup" ]; then
        cleanup
        exit 0
    fi
    
    # Run deployment steps
    check_prerequisites
    setup_environment
    start_core_services
    setup_matrix_user
    start_remi_app
    test_whatsapp_integration
    show_status
    
    echo ""
    print_success "WhatsApp integration is now ready for use!"
    echo ""
    echo "To stop all services, run: $0 cleanup"
}

# Handle script interruption
trap cleanup INT TERM

# Run main function
main "$@"