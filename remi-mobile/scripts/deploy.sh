#!/bin/bash

# R.E.M.I Mobile Deployment Script
# Simple deployment utilities for React Native

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[REMI]${NC} $1"
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

# Get local IP address
get_local_ip() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1
    else
        # Linux
        hostname -I | awk '{print $1}'
    fi
}

# Start development server
start_dev() {
    print_status "Starting R.E.M.I development server..."
    
    # Disable Watchman completely
    export REACT_NATIVE_NO_WATCHMAN=1
    export DISABLE_WATCHMAN=1
    
    # Shutdown any existing Watchman process
    watchman shutdown-server 2>/dev/null || true
    
    npx react-native start --reset-cache
}

# Start with QR code (tunnel)
start_qr() {
    print_status "Starting R.E.M.I with QR code access..."
    LOCAL_IP=$(get_local_ip)
    print_status "Your local IP: $LOCAL_IP"
    print_status "Metro will be available at: http://$LOCAL_IP:8081"
    print_warning "Make sure your phone and computer are on the same WiFi network"
    print_status "Starting Metro bundler..."
    
    # Disable Watchman completely
    export REACT_NATIVE_NO_WATCHMAN=1
    export DISABLE_WATCHMAN=1
    export RCT_METRO_HOST=$LOCAL_IP
    
    # Shutdown any existing Watchman process
    watchman shutdown-server 2>/dev/null || true
    
    npx react-native start --reset-cache --host $LOCAL_IP
}

# Build for production
build_production() {
    print_status "Building R.E.M.I for production..."
    
    # Clean previous builds
    print_status "Cleaning previous builds..."
    npm run clean
    
    # Build Android
    if [ -d "android" ]; then
        print_status "Building Android APK..."
        cd android && ./gradlew assembleRelease && cd ..
        print_success "Android APK built: android/app/build/outputs/apk/release/app-release.apk"
    fi
    
    # Build iOS (if on macOS)
    if [[ "$OSTYPE" == "darwin"* ]] && [ -d "ios" ]; then
        print_status "Building iOS app..."
        npx react-native run-ios --configuration Release
        print_success "iOS app built successfully"
    fi
}

# Install dependencies
install_deps() {
    print_status "Installing R.E.M.I dependencies..."
    npm install
    
    # Install iOS dependencies if on macOS
    if [[ "$OSTYPE" == "darwin"* ]] && [ -d "ios" ]; then
        print_status "Installing iOS pods..."
        cd ios && pod install && cd ..
    fi
    
    print_success "Dependencies installed successfully"
}

# Fix Watchman issues
fix_watchman() {
    print_status "Fixing Watchman issues..."
    
    # Shutdown Watchman
    watchman shutdown-server 2>/dev/null || true
    
    # Clear Watchman state
    rm -rf ~/.watchman* 2>/dev/null || true
    
    # Increase file limits
    ulimit -n 65536 2>/dev/null || true
    
    # Create watchmanconfig
    echo '{}' > .watchmanconfig
    
    print_success "Watchman fixed. Try running your command again."
}

# Show QR code for manual connection
show_qr_info() {
    LOCAL_IP=$(get_local_ip)
    METRO_URL="http://$LOCAL_IP:8081"
    
    print_status "=== QR CODE SETUP INSTRUCTIONS ==="
    echo ""
    print_status "1. Install Expo Go app on your phone:"
    echo "   📱 iOS: https://apps.apple.com/app/expo-go/id982107779"
    echo "   📱 Android: https://play.google.com/store/apps/details?id=host.exp.exponent"
    echo ""
    print_status "2. Make sure your phone and computer are on the same WiFi"
    echo ""
    print_status "3. Start the development server:"
    echo "   npm run qr"
    echo ""
    print_status "4. In Expo Go app, scan this URL or enter manually:"
    echo "   $METRO_URL"
    echo ""
    print_status "5. Alternative: Use the development build:"
    echo "   exp://localhost:19000 (if using Expo CLI)"
    echo ""
    print_warning "Note: If QR scanning doesn't work, you can manually enter the IP in Expo Go"
}

# Main script logic
case "$1" in
    "dev")
        start_dev
        ;;
    "qr")
        start_qr
        ;;
    "build")
        build_production
        ;;
    "install")
        install_deps
        ;;
    "info")
        show_qr_info
        ;;
    "fix")
        fix_watchman
        ;;
    *)
        echo "R.E.M.I Mobile Deployment Script"
        echo ""
        echo "Usage: $0 {dev|qr|build|install|info|fix}"
        echo ""
        echo "Commands:"
        echo "  dev     - Start development server (local only)"
        echo "  qr      - Start development server with QR code access"
        echo "  build   - Build production APK/iOS app"
        echo "  install - Install all dependencies"
        echo "  info    - Show QR code setup instructions"
        echo "  fix     - Fix Watchman and file limit issues"
        echo ""
        echo "Examples:"
        echo "  $0 dev       # Start local development"
        echo "  $0 qr        # Start with QR code for phone testing"
        echo "  $0 build     # Build production apps"
        echo ""
        exit 1
        ;;
esac
