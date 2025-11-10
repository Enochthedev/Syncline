#!/bin/bash
# =============================================================================
# R.E.M.I Backend Setup Script
# =============================================================================
# This script automates the initial setup of the R.E.M.I backend
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python 3.11+ is required but not found"
        exit 1
    fi
    
    # Check Docker
    if command -v docker &> /dev/null; then
        print_success "Docker found"
    else
        print_error "Docker is required but not found"
        exit 1
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        print_success "Docker Compose found"
    else
        print_error "Docker Compose is required but not found"
        exit 1
    fi
}

# Create virtual environment
setup_venv() {
    print_header "Setting Up Virtual Environment"
    
    if [ -d ".venv" ]; then
        print_info "Virtual environment already exists"
    else
        print_info "Creating virtual environment..."
        python3 -m venv .venv
        print_success "Virtual environment created"
    fi
    
    print_info "Activating virtual environment..."
    source .venv/bin/activate
    print_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_header "Installing Python Dependencies"
    
    print_info "Upgrading pip..."
    pip install --upgrade pip
    
    print_info "Installing requirements..."
    pip install -r requirements.txt
    print_success "Dependencies installed"
}

# Setup environment file
setup_env() {
    print_header "Setting Up Environment Configuration"
    
    if [ -f ".env" ]; then
        print_info ".env file already exists"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Keeping existing .env file"
            return
        fi
    fi
    
    print_info "Copying .env.example to .env..."
    cp .env.example .env
    print_success ".env file created"
    print_info "Please edit .env with your configuration"
}

# Start Docker services
start_docker_services() {
    print_header "Starting Docker Services"
    
    print_info "Starting PostgreSQL, Redis, Ollama, and ChromaDB..."
    docker-compose up -d
    
    print_info "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    if docker-compose ps | grep -q "Up"; then
        print_success "Docker services started successfully"
    else
        print_error "Some services failed to start"
        docker-compose ps
        exit 1
    fi
}

# Initialize database
init_database() {
    print_header "Initializing Database"
    
    print_info "Running database migrations..."
    if alembic upgrade head; then
        print_success "Database initialized"
    else
        print_error "Database initialization failed"
        exit 1
    fi
}

# Download AI models
download_ai_models() {
    print_header "Downloading AI Models (Optional)"
    
    read -p "Do you want to download AI models now? This may take a while. (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Downloading tinyllama model..."
        docker exec remi_ollama ollama pull tinyllama:latest
        
        print_info "Downloading nomic-embed-text model..."
        docker exec remi_ollama ollama pull nomic-embed-text:latest
        
        print_success "AI models downloaded"
    else
        print_info "Skipping AI model download"
        print_info "You can download them later with:"
        print_info "  docker exec remi_ollama ollama pull tinyllama:latest"
        print_info "  docker exec remi_ollama ollama pull nomic-embed-text:latest"
    fi
}

# Print next steps
print_next_steps() {
    print_header "Setup Complete!"
    
    echo "Next steps:"
    echo ""
    echo "1. Edit .env file with your configuration:"
    echo "   nano .env"
    echo ""
    echo "2. Start the development server:"
    echo "   source .venv/bin/activate"
    echo "   python main.py"
    echo ""
    echo "3. Access the API:"
    echo "   - API: http://localhost:8000"
    echo "   - Docs: http://localhost:8000/docs"
    echo "   - Health: http://localhost:8000/api/v1/health"
    echo ""
    echo "4. View Docker services:"
    echo "   docker-compose ps"
    echo ""
    echo "5. View logs:"
    echo "   docker-compose logs -f"
    echo ""
    print_success "Happy coding!"
}

# Main execution
main() {
    print_header "R.E.M.I Backend Setup"
    
    check_prerequisites
    setup_venv
    install_dependencies
    setup_env
    start_docker_services
    init_database
    download_ai_models
    print_next_steps
}

# Run main function
main
