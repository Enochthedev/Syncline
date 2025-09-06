# R.E.M.I Mobile App Architecture Guide

## Overview

The R.E.M.I mobile application is built using React Native 0.72+ with TypeScript, providing native iOS and Android applications from a single codebase. This document explains the architecture, deployment structure, and how the various components work together.

## Project Structure

### Root Level Structure

```
remi-mobile/
├── src/                    # TypeScript source code
├── ios/                    # iOS native project files
├── android/                # Android native project files
├── __tests__/              # Test files
├── docs/                   # Documentation
├── App.tsx                 # Main app entry point
├── index.js                # React Native entry point
├── package.json            # Dependencies and scripts
├── metro.config.js         # Metro bundler configuration
├── react-native.config.js  # React Native configuration
└── tsconfig.json           # TypeScript configuration
```

### Source Code Structure (`src/`)

```
src/
├── components/             # Reusable UI components
│   ├── ContactProfile.tsx      # Contact profile display
│   ├── ContactMessages.tsx     # Message threads by platform
│   ├── SharedContent.tsx       # Files and links shared with contacts
│   ├── MessageThread.tsx       # Message display with search
│   ├── ContactCard.tsx         # Contact information card
│   ├── ContactSearchInput.tsx  # Search input component
│   └── ContactSearchResults.tsx # Search results display
├── screens/                # Screen components
│   ├── auth/                   # Authentication screens
│   ├── ContactProfileScreen.tsx # Contact profile screen
│   ├── MessageThreadScreen.tsx  # Message thread screen
│   ├── ContactsScreen.tsx       # Contacts list screen
│   ├── SearchScreen.tsx         # Search interface screen
│   └── DashboardScreen.tsx      # Main dashboard
├── navigation/             # Navigation configuration
│   ├── AppNavigator.tsx        # Main app navigation
│   ├── AuthNavigator.tsx       # Authentication flow
│   └── MainNavigator.tsx       # Main app tabs and stack
├── services/               # Business logic and API calls
│   ├── apiClient.ts            # HTTP client configuration
│   ├── authService.ts          # Authentication service
│   ├── contactSearchService.ts # Contact search API
│   └── syncService.ts          # Data synchronization
├── hooks/                  # Custom React hooks
│   ├── useAuth.ts              # Authentication hook
│   ├── useAuthQuery.ts         # Authenticated API queries
│   ├── useTheme.ts             # Theme management
│   └── useDebounce.ts          # Debounced input handling
├── contexts/               # React contexts
│   ├── AuthContext.tsx         # Authentication state
│   ├── ThemeContext.tsx        # Theme management
│   ├── SyncContext.tsx         # Data synchronization
│   └── NotificationContext.tsx # Push notifications
├── types/                  # TypeScript type definitions
│   └── index.ts                # Unified contact types
├── constants/              # App constants
│   └── api.ts                  # API endpoints
└── utils/                  # Utility functions
```

## iOS Deployment Structure

### iOS Directory (`ios/`)

```
ios/
├── RemiMobile/             # Main iOS app target
│   ├── AppDelegate.swift       # App lifecycle management
│   ├── Info.plist             # App configuration
│   ├── LaunchScreen.storyboard # Launch screen
│   ├── Images.xcassets/       # App icons and images
│   └── PrivacyInfo.xcprivacy  # Privacy manifest
├── RemiMobile.xcodeproj/   # Xcode project file
├── Pods/                   # CocoaPods dependencies
├── Podfile                 # CocoaPods configuration
└── .xcode.env             # Xcode environment variables
```

### iOS Build Process

1. **Metro Bundler**: Compiles TypeScript/JavaScript into a bundle
2. **Xcode Build**: Compiles Swift/Objective-C native code
3. **CocoaPods**: Manages native iOS dependencies (Firebase, etc.)
4. **Code Signing**: Signs the app for distribution
5. **Archive**: Creates .ipa file for App Store or TestFlight

### iOS Configuration Files

#### `ios/RemiMobile/Info.plist`

- App bundle identifier: `com.remi.mobile`
- App version and build number
- Permissions (camera, microphone, contacts, etc.)
- URL schemes for deep linking
- Firebase configuration keys

#### `ios/Podfile`

- React Native dependencies
- Firebase SDK (Analytics, Crashlytics, Messaging)
- Native iOS libraries (Keychain, Biometrics, etc.)

## Android Deployment Structure

### Android Directory (`android/`)

```
android/
├── app/                    # Main Android app module
│   ├── src/main/              # Main source set
│   │   ├── java/              # Java/Kotlin source code
│   │   ├── res/               # Resources (layouts, strings, etc.)
│   │   └── AndroidManifest.xml # App manifest
│   ├── build.gradle           # App-level build configuration
│   ├── debug.keystore         # Debug signing key
│   └── proguard-rules.pro     # Code obfuscation rules
├── gradle/                 # Gradle wrapper
├── build.gradle           # Project-level build configuration
├── gradle.properties      # Gradle properties
├── settings.gradle        # Project settings
├── gradlew               # Gradle wrapper script (Unix)
└── gradlew.bat           # Gradle wrapper script (Windows)
```

### Android Build Process

1. **Metro Bundler**: Compiles TypeScript/JavaScript into a bundle
2. **Gradle Build**: Compiles Java/Kotlin native code
3. **Resource Processing**: Processes Android resources (layouts, strings, etc.)
4. **DEX Compilation**: Converts Java bytecode to Android DEX format
5. **APK/AAB Creation**: Creates installable Android package

### Android Configuration Files

#### `android/app/src/main/AndroidManifest.xml`

- App package name: `com.remi.mobile`
- App permissions (internet, camera, storage, etc.)
- Activities and services
- Intent filters for deep linking
- Firebase configuration

#### `android/app/build.gradle`

- App version and build configuration
- Dependencies (React Native, Firebase, etc.)
- Build variants (debug, release)
- Signing configuration

## React Native Bridge Architecture

### How React Native Works

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   JavaScript    │    │   React Native  │    │   Native Code   │
│     Thread      │◄──►│     Bridge      │◄──►│   (iOS/Android) │
│                 │    │                 │    │                 │
│ - React         │    │ - Message       │    │ - UI Components │
│ - Business      │    │   Passing       │    │ - Native APIs   │
│ - Logic         │    │ - Serialization │    │ - Platform      │
│ - State         │    │ - Threading     │    │   Features      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Rendering Flow

1. **React Components**: Written in TypeScript/JSX
2. **React Native Bridge**: Converts React elements to native views
3. **Native Rendering**: iOS UIKit or Android Views render the UI
4. **Event Handling**: Touch events flow back through the bridge
5. **State Updates**: Trigger re-renders through React's reconciliation

## Development Workflow

### Local Development

```bash
# Start Metro bundler
npm start

# Run on iOS simulator
npm run ios

# Run on Android emulator
npm run android

# Run tests
npm test

# Type checking
npm run type-check
```

### Build Process

```bash
# iOS Release Build
cd ios && xcodebuild -workspace RemiMobile.xcworkspace \
  -scheme RemiMobile -configuration Release \
  -destination generic/platform=iOS \
  -archivePath RemiMobile.xcarchive archive

# Android Release Build
cd android && ./gradlew assembleRelease

# Android Bundle (for Play Store)
cd android && ./gradlew bundleRelease
```

## Configuration Management

### Environment Variables

```typescript
// .env.development
API_BASE_URL=http://localhost:8000
WS_URL=ws://localhost:8000/ws
ENVIRONMENT=development

// .env.production
API_BASE_URL=https://api.remi.com
WS_URL=wss://api.remi.com/ws
ENVIRONMENT=production
```

### Metro Configuration (`metro.config.js`)

- Path aliases for clean imports (`@/components`, `@/screens`)
- Asset resolution for fonts and images
- Transform options for JavaScript/TypeScript
- Platform-specific file resolution

### TypeScript Configuration (`tsconfig.json`)

- Strict type checking enabled
- Path mapping for aliases
- React Native type definitions
- ES2020 target for modern JavaScript features

## Native Module Integration

### iOS Native Modules

- **Keychain**: Secure token storage using iOS Keychain Services
- **Biometrics**: Face ID/Touch ID authentication
- **Firebase**: Analytics, Crashlytics, Push Notifications
- **Voice**: Speech recognition and text-to-speech

### Android Native Modules

- **Keychain**: Secure storage using Android Keystore
- **Biometrics**: Fingerprint and face authentication
- **Firebase**: Analytics, Crashlytics, Push Notifications
- **Voice**: Speech recognition and text-to-speech

## Testing Architecture

### Unit Tests (`__tests__/`)

```
__tests__/
├── components/             # Component tests
│   ├── ContactProfile.test.tsx
│   ├── ContactMessages.test.tsx
│   ├── SharedContent.test.tsx
│   └── MessageThread.test.tsx
├── hooks/                  # Hook tests
├── services/               # Service tests
└── integration/            # Integration tests
```

### Testing Stack

- **Jest**: JavaScript testing framework
- **React Native Testing Library**: Component testing utilities
- **Detox**: End-to-end testing for React Native
- **Mock Services**: API mocking for isolated testing

## Performance Considerations

### React Native Optimizations

- **FlatList**: Virtualized lists for large datasets
- **FastImage**: Optimized image loading and caching
- **Hermes**: JavaScript engine for improved performance
- **Code Splitting**: Lazy loading of components
- **Memory Management**: Proper cleanup of listeners and timers

### Bundle Optimization

- **Metro Tree Shaking**: Removes unused code
- **Image Optimization**: Compressed assets for different screen densities
- **Native Dependencies**: Only include necessary native modules
- **Bundle Splitting**: Separate bundles for different platforms

## Security Implementation

### Data Protection

- **Keychain Storage**: Secure token storage on device
- **Biometric Authentication**: Hardware-backed authentication
- **Certificate Pinning**: Prevent man-in-the-middle attacks
- **Code Obfuscation**: Protect against reverse engineering

### Privacy Features

- **PII Redaction**: Remove sensitive information from logs
- **Data Encryption**: Encrypt sensitive data at rest
- **Secure Communication**: HTTPS/WSS for all network requests
- **Permission Management**: Request minimal necessary permissions

## Deployment Pipeline

### CI/CD Workflow

1. **Code Push**: Developer pushes code to repository
2. **Automated Testing**: Run unit tests, integration tests, and linting
3. **Build Generation**: Create iOS and Android builds
4. **Code Signing**: Sign builds with distribution certificates
5. **Store Upload**: Upload to App Store Connect and Google Play Console
6. **Release Management**: Staged rollout with monitoring

### Release Channels

- **Development**: Internal testing builds
- **Staging**: QA and stakeholder testing
- **Production**: Public app store releases
- **CodePush**: Over-the-air updates for JavaScript changes

This architecture provides a robust foundation for the R.E.M.I mobile application, enabling efficient development, testing, and deployment across both iOS and Android platforms while maintaining code quality and performance standards.
