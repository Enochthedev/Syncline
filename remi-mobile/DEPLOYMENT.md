# 🚀 R.E.M.I Mobile Deployment Guide

Quick and easy deployment scripts for the R.E.M.I React Native mobile app.

## 📱 Quick Start Commands

### Development Server
```bash
npm run dev          # Start local development server
npm run deploy:dev   # Same as above (alternative)
```

### QR Code Deployment (Phone Testing)
```bash
npm run qr           # Start server with QR code access
npm run qr:info      # Show QR setup instructions
npm run qr:server    # Start QR code web interface
```

### Production Builds
```bash
npm run deploy:build # Build production APK + iOS app
npm run build:ios    # iOS build only
npm run build:android # Android APK only
```

### Utilities
```bash
npm run deploy       # Show all deployment options
npm run clean        # Clean build cache
```

## 📋 QR Code Setup (2 minutes)

### 1. Install Expo Go on your phone:
- **iOS**: [Expo Go on App Store](https://apps.apple.com/app/expo-go/id982107779)
- **Android**: [Expo Go on Play Store](https://play.google.com/store/apps/details?id=host.exp.exponent)

### 2. Connect to same WiFi
Make sure your phone and computer are on the same WiFi network.

### 3. Start QR deployment:
```bash
npm run qr
```

### 4. Scan or enter URL manually
- **Option A**: Scan the QR code that appears in terminal
- **Option B**: Open Expo Go → Enter URL → Use the IP shown in terminal
- **Option C**: Open `http://localhost:3000` in browser for web QR interface

## 🛠 Advanced Usage

### Custom IP/Port
```bash
# Start with specific IP
RCT_METRO_HOST=192.168.1.100 npm run qr

# Start QR server on different port
npm run qr:server 8081 3001
```

### Production Deployment
```bash
# Full production build
npm run deploy:build

# Install all dependencies
npm run deploy:install
```

### Troubleshooting
```bash
# If Watchman issues occur
REACT_NATIVE_NO_WATCHMAN=1 npm run dev

# Clean everything and restart
npm run clean
npm install
npm run dev
```

## 📂 Script Files

- `scripts/deploy.sh` - Main deployment script
- `scripts/qr-server.js` - QR code web interface
- `package.json` - npm scripts configuration

## 🔧 What Each Script Does

| Script | Purpose |
|--------|---------|
| `npm run dev` | Local development with Watchman disabled |
| `npm run qr` | Network development server for phone testing |
| `npm run qr:info` | Show setup instructions |
| `npm run qr:server` | Web interface with QR code |
| `npm run deploy:build` | Build production apps |

## 📱 Supported Platforms

- ✅ **iOS**: Requires Xcode (macOS only)
- ✅ **Android**: Requires Android Studio
- ✅ **Phone Testing**: Works with Expo Go (any platform)
- ✅ **Web QR Interface**: Works in any browser

## 🎯 Quick Demo

1. Run `npm run qr:info` to see your IP
2. Run `npm run qr` in one terminal
3. Run `npm run qr:server` in another terminal
4. Open `http://localhost:3000` to see QR code
5. Scan with Expo Go app on your phone
6. R.E.M.I app loads on your device! 🎉

---

*Built for R.E.M.I (Real-time External Memory Interface)*

