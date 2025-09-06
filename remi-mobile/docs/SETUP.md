# R.E.M.I Mobile App Setup Guide

## Prerequisites

### Required Software

1. **Node.js 18+** and **npm/yarn**
   ```bash
   # Check versions
   node --version  # Should be 18.0.0 or higher
   npm --version   # Should be 8.0.0 or higher
   ```

2. **React Native CLI**
   ```bash
   npm install -g @react-native-community/cli
   ```

3. **iOS Development** (macOS only)
   - Xcode 14+ (from Mac App Store)
   - iOS Simulator
   - CocoaPods
     ```bash
     sudo gem install cocoapods
     ```

4. **Android Development**
   - Android Studio
   - Android SDK (API 31+)
   - Android Emulator or physical device
   - Java Development Kit (JDK 11)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/remi-mobile.git
   cd remi-mobile
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **iOS Setup** (macOS only)
   ```bash
   cd ios
   pod install
   cd ..
   ```

5. **Android Setup**
   - Open Android Studio
   - Open the `android` folder
   - Let Android Studio download and configure dependencies
   - Create an Android Virtual Device (AVD) or connect a physical device

## Development

### Running the App

1. **Start Metro bundler**
   ```bash
   npm start
   ```

2. **Run on iOS** (in another terminal)
   ```bash
   npm run ios
   # Or for specific simulator
   npm run ios -- --simulator="iPhone 14"
   ```

3. **Run on Android** (in another terminal)
   ```bash
   npm run android
   # Or for specific device
   npm run android -- --deviceId=<device_id>
   ```

### Development Commands

```bash
# Type checking
npm run type-check

# Linting
npm run lint
npm run lint:fix

# Testing
npm run test
npm run test:watch
npm run test:coverage

# E2E Testing
npm run e2e:build:ios
npm run e2e:ios
npm run e2e:build:android
npm run e2e:android

# Clean project
npm run clean
```

## Project Structure

```
remi-mobile/
├── src/
│   ├── components/         # Reusable UI components
│   ├── screens/           # Screen components
│   ├── navigation/        # Navigation configuration
│   ├── services/          # Business logic and API services
│   ├── hooks/             # Custom React hooks
│   ├── utils/             # Utility functions
│   ├── types/             # TypeScript type definitions
│   └── constants/         # App constants
├── android/               # Android-specific code
├── ios/                   # iOS-specific code
├── __tests__/             # Test files
└── docs/                  # Documentation
```

## Key Features to Implement

### 1. Contact-Based Auto-Search
- Real-time contact search with fuzzy matching
- Voice search integration
- Natural language query processing
- Contact suggestions with platform indicators

### 2. Real-Time Synchronization
- WebSocket connection management
- Automatic reconnection
- Offline action queuing
- Conflict resolution

### 3. Offline Capabilities
- SQLite local database
- Intelligent caching
- Offline search
- Data synchronization

### 4. Security Features
- Biometric authentication
- Secure token storage
- Device security checks
- Data encryption

## API Integration

The app integrates with the R.E.M.I backend API. Key endpoints:

- **Authentication**: `/api/v1/auth/*`
- **Contact Search**: `/api/v1/participants/`
- **Message Search**: `/api/v1/search/`
- **Contact Insights**: `/api/v1/contacts/dossiers/{id}`
- **Real-time Updates**: WebSocket at `/ws`

## Testing

### Unit Tests
```bash
npm run test
```

### E2E Tests with Detox
```bash
# iOS
npm run e2e:build:ios
npm run e2e:ios

# Android
npm run e2e:build:android
npm run e2e:android
```

## Troubleshooting

### Common Issues

1. **Metro bundler issues**
   ```bash
   npm start -- --reset-cache
   ```

2. **iOS build issues**
   ```bash
   cd ios
   pod install
   cd ..
   npm run ios
   ```

3. **Android build issues**
   ```bash
   cd android
   ./gradlew clean
   cd ..
   npm run android
   ```

4. **Node modules issues**
   ```bash
   rm -rf node_modules
   npm install
   ```

### Performance Tips

1. **Enable Hermes** (already configured)
2. **Use Flipper** for debugging
3. **Optimize images** with react-native-fast-image
4. **Use FlatList** for large lists
5. **Implement proper memoization**

## Deployment

### Development Build
```bash
# iOS
npm run build:ios

# Android
npm run build:android
```

### Production Build
```bash
# iOS (requires Apple Developer account)
cd ios
bundle exec fastlane beta

# Android
cd android
./gradlew bundleRelease
```

### CodePush (OTA Updates)
```bash
# iOS
npm run codepush:ios

# Android
npm run codepush:android
```

## Contributing

1. Follow the development guide in `DEVELOPMENT_GUIDE.md`
2. Use TypeScript for all new code
3. Write tests for new features
4. Follow the established code style
5. Update documentation as needed

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the development guide
- Create an issue in the GitHub repository
- Contact the development team