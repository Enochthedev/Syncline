# React Native Deployment Guide

This guide covers the complete deployment process for the R.E.M.I React Native mobile application, including CI/CD pipelines, app store deployment, and CodePush over-the-air updates.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [CI/CD Pipeline](#cicd-pipeline)
4. [iOS Deployment](#ios-deployment)
5. [Android Deployment](#android-deployment)
6. [CodePush Integration](#codepush-integration)
7. [Monitoring and Analytics](#monitoring-and-analytics)
8. [Release Management](#release-management)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Development Environment

- Node.js 18+ and npm 8+
- React Native CLI
- Xcode 15+ (for iOS)
- Android Studio and SDK (for Android)
- Ruby 3.0+ and Bundler (for Fastlane)

### Required Accounts and Services

- Apple Developer Account (iOS deployment)
- Google Play Console Account (Android deployment)
- App Center Account (CodePush)
- Firebase Project (Analytics and Crashlytics)
- GitHub Account (CI/CD)
- Vercel/Netlify Account (Web deployment)

### Required Secrets and Keys

- iOS Certificates and Provisioning Profiles
- Android Keystore and Signing Keys
- App Store Connect API Key
- Google Play Service Account JSON
- Firebase Configuration Files
- CodePush Deployment Keys

## Environment Setup

### 1. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install iOS dependencies
cd ios && bundle install && pod install

# Install Android dependencies
cd android && bundle install
```

### 2. Configure Environment Variables

Create environment-specific configuration files:

```bash
# Development
cp .env.example .env.development

# Staging
cp .env.example .env.staging

# Production
cp .env.example .env.production
```

Required environment variables:

```env
# App Configuration
APP_NAME=R.E.M.I
BUNDLE_ID=com.remi.mobile
VERSION_NAME=1.0.0
VERSION_CODE=1

# API Configuration
API_BASE_URL=https://api.remi.com
WS_BASE_URL=wss://ws.remi.com
ENVIRONMENT=production

# Firebase Configuration
FIREBASE_PROJECT_ID=remi-mobile-prod
FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_APP_ID=your_firebase_app_id

# CodePush Configuration
CODEPUSH_IOS_DEPLOYMENT_KEY=your_ios_deployment_key
CODEPUSH_ANDROID_DEPLOYMENT_KEY=your_android_deployment_key

# Analytics
ANALYTICS_ENABLED=true
CRASHLYTICS_ENABLED=true
PERFORMANCE_MONITORING_ENABLED=true
```

### 3. Configure Signing

#### iOS Signing (using Fastlane Match)

```bash
# Initialize Match for certificate management
cd ios
bundle exec fastlane match init

# Generate certificates and provisioning profiles
bundle exec fastlane match development
bundle exec fastlane match appstore
```

#### Android Signing

Generate a keystore for release builds:

```bash
keytool -genkey -v -keystore android/app/remi-release-key.keystore \
  -alias remi-key-alias -keyalg RSA -keysize 2048 -validity 10000
```

Update `android/gradle.properties`:

```properties
REMI_RELEASE_STORE_FILE=remi-release-key.keystore
REMI_RELEASE_KEY_ALIAS=remi-key-alias
REMI_RELEASE_STORE_PASSWORD=your_keystore_password
REMI_RELEASE_KEY_PASSWORD=your_key_password
```

## CI/CD Pipeline

### GitHub Actions Configuration

The CI/CD pipeline is configured in `.github/workflows/ci-cd.yml` and includes:

1. **Code Quality Checks**

   - TypeScript compilation
   - ESLint linting
   - Unit tests with coverage
   - Security scanning

2. **Build Process**

   - iOS build with Xcode
   - Android build with Gradle
   - Artifact generation and storage

3. **Testing**

   - Unit tests
   - Integration tests
   - E2E tests with Detox
   - Performance tests

4. **Deployment**
   - CodePush for staging/production
   - App Store deployment (iOS)
   - Google Play deployment (Android)

### Required GitHub Secrets

Configure the following secrets in your GitHub repository:

```
# iOS Deployment
MATCH_PASSWORD=your_match_password
FASTLANE_PASSWORD=your_fastlane_password
APP_STORE_CONNECT_API_KEY_ID=your_api_key_id
APP_STORE_CONNECT_API_ISSUER_ID=your_issuer_id
APP_STORE_CONNECT_API_KEY=your_api_key_content

# Android Deployment
ANDROID_KEYSTORE_PASSWORD=your_keystore_password
ANDROID_KEY_ALIAS=your_key_alias
ANDROID_KEY_PASSWORD=your_key_password
GOOGLE_PLAY_SERVICE_ACCOUNT_JSON=your_service_account_json

# CodePush
APPCENTER_ACCESS_TOKEN=your_appcenter_token
APPCENTER_APP_NAME_IOS=your_ios_app_name
APPCENTER_APP_NAME_ANDROID=your_android_app_name

# Firebase
FIREBASE_TOKEN=your_firebase_token

# Notifications
SLACK_WEBHOOK=your_slack_webhook_url
```

## iOS Deployment

### 1. Fastlane Configuration

The iOS deployment is managed by Fastlane with the following lanes:

- `test`: Run unit tests
- `build_release`: Build release version
- `beta`: Deploy to TestFlight
- `deploy_to_app_store`: Deploy to App Store

### 2. Manual Deployment

```bash
cd ios

# Run tests
bundle exec fastlane test

# Deploy to TestFlight
bundle exec fastlane beta

# Deploy to App Store
bundle exec fastlane deploy_to_app_store
```

### 3. App Store Connect Configuration

1. Create app in App Store Connect
2. Configure app metadata, screenshots, and descriptions
3. Set up TestFlight for beta testing
4. Configure App Store review information

### 4. Certificate Management

Using Fastlane Match for certificate management:

```bash
# Sync certificates
bundle exec fastlane sync_certificates

# Register new devices
bundle exec fastlane register_devices

# Update provisioning profiles
bundle exec fastlane match --force
```

## Android Deployment

### 1. Fastlane Configuration

The Android deployment includes these lanes:

- `test`: Run unit tests and lint checks
- `build_release`: Build release AAB
- `internal`: Deploy to internal testing
- `alpha`: Deploy to alpha track
- `beta`: Deploy to beta track
- `deploy_to_play_store`: Deploy to production

### 2. Manual Deployment

```bash
cd android

# Run tests
bundle exec fastlane test

# Deploy to internal testing
bundle exec fastlane internal

# Deploy to production
bundle exec fastlane deploy_to_play_store
```

### 3. Google Play Console Configuration

1. Create app in Google Play Console
2. Upload initial APK/AAB manually
3. Configure store listing and assets
4. Set up testing tracks (internal, alpha, beta)
5. Configure release management

### 4. App Signing

Google Play App Signing is recommended:

1. Upload your signing key to Google Play Console
2. Let Google manage app signing
3. Use upload key for CI/CD pipeline

## CodePush Integration

### 1. Setup

Install and configure App Center CLI:

```bash
npm install -g appcenter-cli
appcenter login
```

Create apps in App Center:

```bash
appcenter apps create -d "R.E.M.I iOS" -o iOS -p React-Native
appcenter apps create -d "R.E.M.I Android" -o Android -p React-Native
```

### 2. Deployment Keys

Get deployment keys for each environment:

```bash
# iOS
appcenter codepush deployment list -a your-org/remi-ios

# Android
appcenter codepush deployment list -a your-org/remi-android
```

### 3. Release Process

#### Staging Deployment

```bash
# iOS
appcenter codepush release-react -a your-org/remi-ios -d Staging

# Android
appcenter codepush release-react -a your-org/remi-android -d Staging
```

#### Production Deployment

```bash
# iOS
appcenter codepush release-react -a your-org/remi-ios -d Production

# Android
appcenter codepush release-react -a your-org/remi-android -d Production
```

### 4. Feature Flags and A/B Testing

The app includes a feature flag system for controlled rollouts:

```typescript
import { FeatureFlagManager } from '../codepush.config';

const featureFlags = new FeatureFlagManager();
await featureFlags.initialize(userId);

// Check feature flag
if (featureFlags.isFeatureEnabled('ENHANCED_SEARCH')) {
  // Show enhanced search UI
}

// Get A/B test variant
const searchVariant = featureFlags.getABTestVariant('SEARCH_ALGORITHM');
```

## Monitoring and Analytics

### 1. Firebase Analytics

Analytics are automatically tracked for:

- User actions (login, search, navigation)
- Performance metrics (app start, API calls)
- Errors and crashes
- Feature usage

### 2. Crashlytics

Crash reporting is enabled by default:

```typescript
import { analyticsService } from '../services/analyticsService';

// Log custom error
analyticsService.logError('custom_error', error, { context: 'user_action' });

// Set user context
analyticsService.setUserId(userId);
analyticsService.setUserProperty('user_type', 'premium');
```

### 3. Performance Monitoring

Performance traces are automatically created for:

- App startup time
- Screen load times
- API response times
- Search performance

### 4. Custom Metrics

Track custom business metrics:

```typescript
// Log search performance
analyticsService.logSearchPerformance(query, resultCount, duration, 'text');

// Log feature usage
analyticsService.logFeatureUsage('voice_search', {
  query_length: query.length,
  success: true,
});
```

## Release Management

### 1. Version Management

Version numbers are managed automatically:

- **iOS**: Build number incremented automatically
- **Android**: Version code incremented automatically
- **Semantic Versioning**: Major.Minor.Patch format

### 2. Release Branches

Follow Git Flow branching strategy:

- `main`: Production releases
- `develop`: Development integration
- `release/*`: Release preparation
- `feature/*`: Feature development
- `hotfix/*`: Critical fixes

### 3. Release Process

1. **Feature Development**

   ```bash
   git checkout -b feature/new-feature develop
   # Develop feature
   git checkout develop
   git merge --no-ff feature/new-feature
   ```

2. **Release Preparation**

   ```bash
   git checkout -b release/1.2.0 develop
   # Update version numbers, changelog
   git checkout main
   git merge --no-ff release/1.2.0
   git tag -a v1.2.0 -m "Release version 1.2.0"
   ```

3. **Deployment**
   - Push to `main` triggers production deployment
   - Push to `develop` triggers staging deployment
   - Create GitHub release triggers app store deployment

### 4. Rollback Strategy

#### CodePush Rollback

```bash
# Rollback to previous version
appcenter codepush rollback -a your-org/remi-ios Production
appcenter codepush rollback -a your-org/remi-android Production
```

#### App Store Rollback

- Use App Store Connect to remove current version
- Resubmit previous version if needed

#### Emergency Hotfix

```bash
git checkout -b hotfix/critical-fix main
# Fix critical issue
git checkout main
git merge --no-ff hotfix/critical-fix
git tag -a v1.2.1 -m "Hotfix version 1.2.1"
```

## Troubleshooting

### Common Issues

#### iOS Build Failures

```bash
# Clean derived data
rm -rf ~/Library/Developer/Xcode/DerivedData

# Reset CocoaPods
cd ios && rm -rf Pods Podfile.lock && pod install

# Update certificates
bundle exec fastlane match --force
```

#### Android Build Failures

```bash
# Clean Gradle cache
cd android && ./gradlew clean

# Reset Gradle daemon
./gradlew --stop && ./gradlew clean

# Check keystore configuration
keytool -list -v -keystore app/remi-release-key.keystore
```

#### CodePush Issues

```bash
# Check deployment status
appcenter codepush deployment list -a your-org/remi-ios

# Clear CodePush cache
npx react-native-code-push clear-cache

# Verify deployment keys
appcenter codepush deployment list -a your-org/remi-ios --displayKeys
```

### Debug Commands

```bash
# Check app configuration
npx react-native info

# Validate iOS build
xcodebuild -workspace ios/RemiMobile.xcworkspace -scheme RemiMobile -configuration Release -destination generic/platform=iOS build

# Validate Android build
cd android && ./gradlew assembleRelease

# Test CodePush integration
npx appcenter codepush release-react -a your-org/remi-ios -d Staging --dry-run
```

### Performance Optimization

1. **Bundle Size Optimization**

   ```bash
   # Analyze bundle size
   npx react-native bundle --platform ios --dev false --entry-file index.js --bundle-output ios-bundle.js --assets-dest ios-assets

   # Enable Hermes (Android)
   # Set enableHermes: true in android/app/build.gradle
   ```

2. **Image Optimization**

   - Use WebP format for images
   - Implement lazy loading
   - Use react-native-fast-image

3. **Memory Management**
   - Monitor memory usage with Flipper
   - Implement proper cleanup in useEffect
   - Use FlatList for large lists

### Monitoring and Alerts

Set up alerts for:

- Crash rate > 1%
- App startup time > 3 seconds
- API error rate > 5%
- Low app store ratings

## Security Considerations

1. **Code Obfuscation**

   - Enable ProGuard (Android)
   - Use code obfuscation tools

2. **API Security**

   - Use certificate pinning
   - Implement proper authentication
   - Validate all inputs

3. **Data Protection**

   - Encrypt sensitive data
   - Use Keychain/Keystore for secrets
   - Implement proper session management

4. **App Store Security**
   - Regular security audits
   - Dependency vulnerability scanning
   - Code signing verification

## Support and Maintenance

### Regular Tasks

- Update dependencies monthly
- Review crash reports weekly
- Monitor performance metrics daily
- Update certificates before expiration

### Emergency Procedures

1. Critical bug discovered
2. Prepare hotfix branch
3. Test fix thoroughly
4. Deploy via CodePush if possible
5. Submit app store update if needed
6. Monitor deployment metrics
7. Communicate with users

For additional support, contact the development team or refer to the project documentation.
