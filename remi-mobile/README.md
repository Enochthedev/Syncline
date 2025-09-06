# R.E.M.I Mobile App - React Native

R.E.M.I (Real-time External Memory Interface) mobile application built with React Native, featuring unified authentication, biometric security, and cross-platform synchronization.

## 🚀 Quick Start

### Prerequisites

- **Node.js**: 18.0.0 or higher
- **npm**: 8.0.0 or higher
- **React Native CLI**: Latest version
- **Xcode**: 14.0+ (for iOS development)
- **Android Studio**: Latest version (for Android development)
- **CocoaPods**: Latest version (for iOS dependencies)

### iOS Requirements

```bash
# Install Xcode from App Store
# Install CocoaPods
sudo gem install cocoapods

# Install iOS Simulator (if not already installed)
xcode-select --install
```

### Android Requirements

```bash
# Install Android Studio
# Set up Android SDK and emulator
# Add Android SDK to PATH
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

## 📱 Local Development Setup

### 1. Clone and Install Dependencies

```bash
# Navigate to mobile app directory
cd remi-mobile

# Install Node.js dependencies
npm install

# Install iOS dependencies (macOS only)
cd ios && pod install && cd ..

# For Android, sync project in Android Studio
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
nano .env
```

**Required Environment Variables:**

```env
# API Configuration
API_BASE_URL=http://localhost:8000
WS_URL=ws://localhost:8000/ws

# App Configuration
APP_VERSION=1.0.0
APP_ENVIRONMENT=development

# Feature Flags
ENABLE_BIOMETRIC_AUTH=true
ENABLE_PUSH_NOTIFICATIONS=true
ENABLE_ANALYTICS=false

# Debug Settings
ENABLE_FLIPPER=true
ENABLE_REACTOTRON=true
LOG_LEVEL=debug
```

### 3. Backend Setup

Ensure the R.E.M.I backend is running:

```bash
# In the main project directory
python main.py

# Verify backend is running
curl http://localhost:8000/api/v1/health
```

### 4. Start Development Servers

**Metro Bundler:**

```bash
npm start
# or
npx react-native start
```

**iOS Simulator:**

```bash
npm run ios
# or
npx react-native run-ios

# For specific device
npx react-native run-ios --simulator="iPhone 14 Pro"
```

**Android Emulator:**

```bash
npm run android
# or
npx react-native run-android

# For specific device
npx react-native run-android --deviceId=emulator-5554
```

## 🔐 Authentication Setup

### Biometric Authentication

**iOS Setup:**

1. Enable Face ID/Touch ID in iOS Simulator:
   - Device → Face ID/Touch ID → Enrolled
2. Grant biometric permissions in app settings

**Android Setup:**

1. Enable fingerprint in Android emulator:
   - Settings → Security → Fingerprint
2. Add fingerprint in emulator extended controls

### OAuth Platform Connections

Configure OAuth credentials in your backend `.env`:

```env
# Gmail OAuth
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret

# Slack OAuth
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret
```

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test -- authService.test.ts
```

### End-to-End Tests (Detox)

**Setup:**

```bash
# Install Detox CLI
npm install -g detox-cli

# Build test app (iOS)
npm run e2e:build:ios

# Build test app (Android)
npm run e2e:build:android
```

**Run E2E Tests:**

```bash
# iOS
npm run e2e:ios

# Android
npm run e2e:android

# Run specific test suite
detox test e2e/auth.e2e.ts --configuration ios.sim.debug
```

### Device Testing

**iOS Physical Device:**

```bash
# Build for device
npm run build:ios

# Install on connected device
npx react-native run-ios --device
```

**Android Physical Device:**

```bash
# Enable USB debugging on device
# Build and install
npm run build:android
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

## 🔧 Development Tools

### Debugging

**Flipper Integration:**

```bash
# Flipper should auto-detect running app
# Available plugins:
# - React DevTools
# - Network Inspector
# - AsyncStorage Inspector
# - Crash Reporter
```

**Reactotron (Alternative):**

```bash
# Install Reactotron desktop app
# Connect to app automatically in development
```

**Chrome DevTools:**

```bash
# Shake device or Cmd+D (iOS) / Cmd+M (Android)
# Select "Debug JS Remotely"
# Open Chrome DevTools
```

### Performance Monitoring

**React Native Performance Monitor:**

```bash
# Enable in development
# Shake device → "Perf Monitor"
```

**Flipper Performance Plugin:**

- CPU usage monitoring
- Memory leak detection
- Frame rate analysis

## 📦 Building for Production

### iOS Production Build

```bash
# Clean build
npm run clean

# Build release version
npm run build:ios

# Archive in Xcode
# 1. Open ios/RemiMobile.xcworkspace in Xcode
# 2. Select "Any iOS Device" as target
# 3. Product → Archive
# 4. Upload to App Store Connect
```

### Android Production Build

```bash
# Generate signed APK
npm run build:android

# Generate signed AAB (recommended for Play Store)
npm run build:android:bundle

# Upload to Google Play Console
```

### Code Signing

**iOS:**

```bash
# Set up certificates and provisioning profiles in Xcode
# Configure signing in project settings
# Ensure bundle ID matches App Store Connect
```

**Android:**

```bash
# Generate keystore
keytool -genkeypair -v -keystore remi-release-key.keystore -alias remi-key-alias -keyalg RSA -keysize 2048 -validity 10000

# Configure in android/gradle.properties
MYAPP_RELEASE_STORE_FILE=remi-release-key.keystore
MYAPP_RELEASE_KEY_ALIAS=remi-key-alias
MYAPP_RELEASE_STORE_PASSWORD=your_store_password
MYAPP_RELEASE_KEY_PASSWORD=your_key_password
```

## 🚀 Deployment

### App Store Deployment (iOS)

1. **Prepare for Release:**

   ```bash
   # Update version in package.json and ios/RemiMobile/Info.plist
   # Ensure all certificates are valid
   # Test on physical devices
   ```

2. **Submit to App Store:**
   ```bash
   # Archive in Xcode
   # Upload to App Store Connect
   # Fill out app metadata
   # Submit for review
   ```

### Google Play Store Deployment (Android)

1. **Prepare Release:**

   ```bash
   # Update version in package.json and android/app/build.gradle
   # Generate signed AAB
   npm run build:android:bundle
   ```

2. **Upload to Play Console:**
   ```bash
   # Create release in Play Console
   # Upload AAB file
   # Fill out store listing
   # Submit for review
   ```

### CodePush Deployment (Over-the-Air Updates)

```bash
# Install CodePush CLI
npm install -g code-push-cli

# Login to CodePush
code-push login

# Release update to iOS
npm run codepush:ios

# Release update to Android
npm run codepush:android

# Release with specific deployment
code-push release-react remi-mobile-ios ios --deploymentName Staging
```

## 🔍 Troubleshooting

### Common Issues

**Metro bundler issues:**

```bash
# Clear Metro cache
npx react-native start --reset-cache

# Clear npm cache
npm start -- --reset-cache
```

**iOS build issues:**

```bash
# Clean iOS build
cd ios && xcodebuild clean && cd ..
rm -rf ios/build

# Reinstall pods
cd ios && pod deintegrate && pod install && cd ..
```

**Android build issues:**

```bash
# Clean Android build
cd android && ./gradlew clean && cd ..

# Reset Android project
cd android && ./gradlew cleanBuildCache && cd ..
```

**Dependency issues:**

```bash
# Clear node_modules and reinstall
rm -rf node_modules
npm install

# Clear watchman cache
watchman watch-del-all
```

### Authentication Issues

**Keychain access errors:**

```bash
# Reset iOS Simulator
Device → Erase All Content and Settings

# Clear Android app data
adb shell pm clear com.remimobile
```

**Biometric authentication not working:**

```bash
# iOS: Ensure Face ID/Touch ID is enrolled in simulator
# Android: Enable fingerprint in emulator settings
# Check permissions in app settings
```

**OAuth connection failures:**

```bash
# Verify backend OAuth configuration
# Check redirect URIs match exactly
# Ensure SSL certificates are valid
```

### Performance Issues

**Slow startup:**

```bash
# Enable Hermes engine (Android)
# Optimize bundle size
# Use release builds for testing
```

**Memory leaks:**

```bash
# Use Flipper memory profiler
# Check for retained listeners
# Verify proper cleanup in useEffect
```

## 📚 Additional Resources

### Project Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - Complete app architecture and deployment structure
- [Development Guide](DEVELOPMENT_GUIDE.md) - Comprehensive development steering guide

### External Resources

- [React Native Documentation](https://reactnative.dev/docs/getting-started)
- [React Navigation](https://reactnavigation.org/)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Detox Testing Framework](https://github.com/wix/Detox)
- [Flipper Debugging](https://fbflipper.com/)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
