#!/bin/bash

# R.E.M.I Authentication System - Local Development Setup Script
# This script sets up the complete authentication system for local development

set -e

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Node.js version
check_node_version() {
    if command_exists node; then
        NODE_VERSION=$(node --version | cut -d'v' -f2)
        REQUIRED_VERSION="18.0.0"
        
        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$NODE_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
            print_success "Node.js version $NODE_VERSION is compatible"
        else
            print_error "Node.js version $NODE_VERSION is too old. Required: $REQUIRED_VERSION+"
            exit 1
        fi
    else
        print_error "Node.js is not installed. Please install Node.js 18.0.0 or higher"
        exit 1
    fi
}

# Function to check Python version
check_python_version() {
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python version $PYTHON_VERSION found"
    else
        print_error "Python 3 is not installed. Please install Python 3.8 or higher"
        exit 1
    fi
}

# Function to setup backend
setup_backend() {
    print_status "Setting up R.E.M.I backend..."
    
    # Check if we're in the right directory
    if [ ! -f "main.py" ]; then
        print_error "main.py not found. Please run this script from the R.E.M.I root directory"
        exit 1
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv .venv
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Setup environment file
    if [ ! -f ".env" ]; then
        print_status "Creating backend environment file..."
        cp .env.example .env
        print_warning "Please edit .env file with your configuration"
    fi
    
    # Setup database
    print_status "Setting up database..."
    alembic upgrade head
    
    print_success "Backend setup completed"
}

# Function to setup mobile app
setup_mobile() {
    print_status "Setting up React Native mobile app..."
    
    if [ ! -d "remi-mobile" ]; then
        print_error "remi-mobile directory not found"
        return 1
    fi
    
    cd remi-mobile
    
    # Install Node.js dependencies
    print_status "Installing mobile app dependencies..."
    npm install
    
    # Setup environment file
    if [ ! -f ".env" ]; then
        print_status "Creating mobile app environment file..."
        cp .env.example .env
        print_warning "Please edit remi-mobile/.env file with your configuration"
    fi
    
    # iOS setup (macOS only)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command_exists pod; then
            print_status "Installing iOS dependencies..."
            cd ios && pod install && cd ..
            print_success "iOS dependencies installed"
        else
            print_warning "CocoaPods not found. iOS development will not be available"
            print_warning "Install CocoaPods: sudo gem install cocoapods"
        fi
    fi
    
    cd ..
    print_success "Mobile app setup completed"
}

# Function to setup web app
setup_web() {
    print_status "Setting up Next.js web app..."
    
    if [ ! -d "remi-web" ]; then
        print_error "remi-web directory not found"
        return 1
    fi
    
    cd remi-web
    
    # Install Node.js dependencies
    print_status "Installing web app dependencies..."
    npm install
    
    # Setup environment file
    if [ ! -f ".env.local" ]; then
        print_status "Creating web app environment file..."
        cp .env.example .env.local
        print_warning "Please edit remi-web/.env.local file with your configuration"
    fi
    
    cd ..
    print_success "Web app setup completed"
}

# Function to setup development tools
setup_dev_tools() {
    print_status "Setting up development tools..."
    
    # Check for React Native CLI
    if ! command_exists react-native; then
        print_status "Installing React Native CLI..."
        npm install -g @react-native-community/cli
    fi
    
    # Check for Detox CLI (for E2E testing)
    if ! command_exists detox; then
        print_status "Installing Detox CLI for E2E testing..."
        npm install -g detox-cli
    fi
    
    # Check for Playwright (for web E2E testing)
    if [ -d "remi-web" ]; then
        cd remi-web
        if [ ! -d "node_modules/@playwright" ]; then
            print_status "Installing Playwright browsers..."
            npx playwright install
        fi
        cd ..
    fi
    
    print_success "Development tools setup completed"
}

# Function to verify setup
verify_setup() {
    print_status "Verifying setup..."
    
    # Check backend
    print_status "Checking backend..."
    if [ -f ".env" ] && [ -d ".venv" ]; then
        print_success "Backend configuration found"
    else
        print_warning "Backend setup may be incomplete"
    fi
    
    # Check mobile app
    print_status "Checking mobile app..."
    if [ -d "remi-mobile/node_modules" ] && [ -f "remi-mobile/.env" ]; then
        print_success "Mobile app configuration found"
    else
        print_warning "Mobile app setup may be incomplete"
    fi
    
    # Check web app
    print_status "Checking web app..."
    if [ -d "remi-web/node_modules" ] && [ -f "remi-web/.env.local" ]; then
        print_success "Web app configuration found"
    else
        print_warning "Web app setup may be incomplete"
    fi
}

# Function to start development servers
start_dev_servers() {
    print_status "Starting development servers..."
    
    # Create tmux session for development
    if command_exists tmux; then
        print_status "Creating tmux session 'remi-dev'..."
        
        # Kill existing session if it exists
        tmux kill-session -t remi-dev 2>/dev/null || true
        
        # Create new session
        tmux new-session -d -s remi-dev -n backend
        
        # Backend window
        tmux send-keys -t remi-dev:backend "source .venv/bin/activate && python main.py" C-m
        
        # Web app window
        tmux new-window -t remi-dev -n web
        tmux send-keys -t remi-dev:web "cd remi-web && npm run dev" C-m
        
        # Mobile metro window
        tmux new-window -t remi-dev -n metro
        tmux send-keys -t remi-dev:metro "cd remi-mobile && npm start" C-m
        
        print_success "Development servers started in tmux session 'remi-dev'"
        print_status "Attach to session: tmux attach -t remi-dev"
        print_status "List windows: Ctrl+B, w"
        print_status "Switch windows: Ctrl+B, [0-9]"
        
    else
        print_warning "tmux not found. Starting servers manually..."
        print_status "Start backend: source .venv/bin/activate && python main.py"
        print_status "Start web app: cd remi-web && npm run dev"
        print_status "Start mobile metro: cd remi-mobile && npm start"
        print_status "Run iOS: cd remi-mobile && npm run ios"
        print_status "Run Android: cd remi-mobile && npm run android"
    fi
}

# Function to display next steps
show_next_steps() {
    print_success "Setup completed successfully!"
    echo
    print_status "Next steps:"
    echo "1. Edit environment files with your configuration:"
    echo "   - .env (backend)"
    echo "   - remi-mobile/.env (mobile app)"
    echo "   - remi-web/.env.local (web app)"
    echo
    echo "2. Configure OAuth credentials:"
    echo "   - Gmail: https://console.cloud.google.com/"
    echo "   - Slack: https://api.slack.com/apps"
    echo
    echo "3. Start development servers:"
    if command_exists tmux; then
        echo "   - tmux attach -t remi-dev (if using tmux)"
    fi
    echo "   - Backend: source .venv/bin/activate && python main.py"
    echo "   - Web: cd remi-web && npm run dev"
    echo "   - Mobile Metro: cd remi-mobile && npm start"
    echo "   - iOS: cd remi-mobile && npm run ios"
    echo "   - Android: cd remi-mobile && npm run android"
    echo
    echo "4. Access applications:"
    echo "   - Backend API: http://localhost:8000"
    echo "   - Web App: http://localhost:3000"
    echo "   - API Docs: http://localhost:8000/docs"
    echo
    echo "5. Run tests:"
    echo "   - Backend: pytest"
    echo "   - Mobile: cd remi-mobile && npm test"
    echo "   - Web: cd remi-web && npm test"
    echo "   - E2E Mobile: cd remi-mobile && npm run e2e:ios"
    echo "   - E2E Web: cd remi-web && npm run test:e2e"
    echo
    print_status "For detailed documentation, see:"
    echo "   - remi-mobile/README.md"
    echo "   - remi-web/README.md"
    echo "   - docs/AUTHENTICATION_DEPLOYMENT_GUIDE.md"
}

# Main execution
main() {
    echo "🚀 R.E.M.I Authentication System Setup"
    echo "======================================"
    echo
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    check_node_version
    check_python_version
    
    # Setup components
    setup_backend
    setup_mobile
    setup_web
    setup_dev_tools
    
    # Verify setup
    verify_setup
    
    # Ask if user wants to start dev servers
    echo
    read -p "Do you want to start development servers now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_dev_servers
    fi
    
    # Show next steps
    show_next_steps
}

# Run main function
main "$@"