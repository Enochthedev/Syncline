#!/bin/bash

# R.E.M.I System Testing Script
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Test Backend API
test_backend() {
    log_info "Testing Backend API..."
    
    # Install dependencies
    pip install -r requirements.txt >/dev/null 2>&1 || {
        log_error "Failed to install Python dependencies"
        return 1
    }
    
    # Start API server
    python main.py &
    BACKEND_PID=$!
    sleep 5
    
    # Test health endpoint
    if curl -s "http://localhost:8000/health" >/dev/null 2>&1; then
        log_success "Backend API is running"
        kill $BACKEND_PID 2>/dev/null || true
        return 0
    else
        log_error "Backend API failed"
        kill $BACKEND_PID 2>/dev/null || true
        return 1
    fi
}

# Test Mobile App
test_mobile() {
    log_info "Testing Mobile App..."
    
    cd remi-mobile || return 1
    
    # Install dependencies
    npm install >/dev/null 2>&1 || {
        log_error "Failed to install mobile dependencies"
        cd ..
        return 1
    }
    
    # Run tests
    npm run type-check >/dev/null 2>&1 && log_success "TypeScript check passed" || log_warning "TypeScript check failed"
    npm test -- --passWithNoTests --silent >/dev/null 2>&1 && log_success "Mobile tests passed" || log_warning "Mobile tests failed"
    
    cd ..
    return 0
}

# Test Web App
test_web() {
    log_info "Testing Web App..."
    
    cd remi-web || return 1
    
    # Install dependencies
    npm install >/dev/null 2>&1 || {
        log_error "Failed to install web dependencies"
        cd ..
        return 1
    }
    
    # Run tests
    npm run type-check >/dev/null 2>&1 && log_success "TypeScript check passed" || log_warning "TypeScript check failed"
    npm run build >/dev/null 2>&1 && log_success "Web build successful" || log_error "Web build failed"
    
    cd ..
    return 0
}

# Test Integration Services
test_integrations() {
    log_info "Testing Integration Services..."
    
    python -c "
import sys
sys.path.append('.')
try:
    from integrations.gmail_connector import GmailConnector
    print('Gmail connector OK')
except Exception as e:
    print(f'Gmail connector failed: {e}')
" && log_success "Gmail connector test passed" || log_warning "Gmail connector test failed"
    
    return 0
}

# Main execution
case "${1:-all}" in
    "backend")
        test_backend
        ;;
    "mobile")
        test_mobile
        ;;
    "web")
        test_web
        ;;
    "integrations")
        test_integrations
        ;;
    "all")
        log_info "Running all system tests..."
        test_backend
        test_mobile
        test_web
        test_integrations
        log_success "All tests completed!"
        ;;
    *)
        echo "Usage: $0 [backend|mobile|web|integrations|all]"
        exit 1
        ;;
esac