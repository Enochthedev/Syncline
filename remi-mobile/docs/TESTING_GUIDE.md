# Comprehensive Testing Guide

This document provides a complete guide to the testing framework implemented for the R.E.M.I React Native mobile application.

## Overview

The testing framework includes six major categories of tests:

1. **Unit Tests** - Individual component and service testing
2. **Integration Tests** - Cross-platform synchronization and API communication
3. **End-to-End Tests** - Complete user workflow testing with Detox
4. **Performance Tests** - Memory analysis and battery usage monitoring
5. **Visual Regression Tests** - Screenshot comparison and UI consistency
6. **Security Tests** - Penetration testing and vulnerability assessment

## Test Structure

```
__tests__/
├── unit/                    # Unit tests for individual components
├── integration/             # Integration and sync tests
├── performance/             # Performance and resource monitoring
├── visual/                  # Visual regression testing
├── security/                # Security and vulnerability tests
├── e2e/                     # End-to-end user journey tests
├── setup.ts                 # Global test setup
├── globalSetup.js           # Jest global setup
└── globalTeardown.js        # Jest global teardown
```

## Running Tests

### Quick Commands

```bash
# Run all tests (except E2E)
npm test

# Run specific test suites
npm run test:unit
npm run test:integration
npm run test:performance
npm run test:visual
npm run test:security

# Run E2E tests
npm run e2e:ios
npm run e2e:android

# Run comprehensive test suite
./scripts/run-tests.sh

# Run with E2E tests included
./scripts/run-tests.sh --include-e2e
```

### Coverage Requirements

The testing framework enforces high coverage thresholds:

- **Global Coverage**: 90% lines, 90% functions, 85% branches, 90% statements
- **Services**: 95% lines, 95% functions, 90% branches, 95% statements
- **Components**: 90% lines, 90% functions, 85% branches, 90% statements
- **Hooks**: 95% lines, 95% functions, 90% branches, 95% statements

## Test Categories

### 1. Unit Tests

**Location**: `__tests__/unit/`

**Purpose**: Test individual components, services, and utilities in isolation.

**Key Features**:

- Comprehensive mocking of dependencies
- High code coverage requirements (90%+)
- Fast execution (< 5 seconds total)
- Isolated test environment

**Example Test Structure**:

```typescript
describe('ContactManager', () => {
  beforeEach(() => {
    // Setup mocks and test data
  });

  describe('searchContacts', () => {
    it('should search contacts with fuzzy matching', async () => {
      // Test implementation
    });
  });
});
```

**Coverage Areas**:

- Contact management functionality
- Search service operations
- Authentication flows
- Data synchronization logic
- Error handling scenarios
- Edge cases and boundary conditions

### 2. Integration Tests

**Location**: `__tests__/integration/`

**Purpose**: Test cross-platform synchronization and API communication.

**Key Features**:

- Real-time sync testing with WebSocket mocks
- Offline/online scenario testing
- Conflict resolution validation
- Data consistency verification
- Performance under load

**Test Scenarios**:

- Contact synchronization across devices
- Message real-time updates
- Offline operation queuing
- Sync conflict resolution
- Network failure recovery

### 3. End-to-End Tests (Detox)

**Location**: `e2e/`

**Purpose**: Test complete user workflows on real devices/simulators.

**Key Features**:

- Complete user journey testing
- Cross-platform consistency (iOS/Android)
- Real device interaction simulation
- Screenshot capture on failures
- Performance monitoring during tests

**Test Workflows**:

- Authentication flow (login, biometric, logout)
- Contact search journey
- Message thread navigation
- Real-time notification handling
- Offline functionality
- App backgrounding/foregrounding

**Configuration**:

```json
{
  "ios.sim.debug": {
    "binaryPath": "ios/build/Build/Products/Debug-iphonesimulator/RemiMobile.app",
    "type": "ios.simulator",
    "device": { "type": "iPhone 14" }
  },
  "android.emu.debug": {
    "binaryPath": "android/app/build/outputs/apk/debug/app-debug.apk",
    "type": "android.emulator",
    "device": { "avdName": "Pixel_4_API_30" }
  }
}
```

### 4. Performance Tests

**Location**: `__tests__/performance/`

**Purpose**: Monitor memory usage, battery consumption, and app performance.

**Key Features**:

- Memory leak detection
- Battery usage monitoring
- Performance bottleneck identification
- Flipper integration for profiling
- CI/CD performance regression detection

**Monitoring Areas**:

- App launch time (< 3 seconds)
- Search response time (< 1 second)
- Memory usage (< 200MB peak)
- Battery efficiency (> 70%)
- Frame rate consistency (60fps)

**Performance Thresholds**:

```typescript
const performanceThresholds = {
  appLaunchTime: 3000, // 3 seconds
  searchResponseTime: 1000, // 1 second
  memoryUsage: 200 * 1024 * 1024, // 200MB
  batteryEfficiency: 0.7, // 70%
  frameRate: 60, // 60fps
};
```

### 5. Visual Regression Tests

**Location**: `__tests__/visual/`

**Purpose**: Detect unintended UI changes through screenshot comparison.

**Key Features**:

- Pixel-perfect screenshot comparison
- Cross-platform visual consistency
- Theme and responsive layout testing
- Animation frame analysis
- Automatic baseline management

**Test Coverage**:

- Component visual baselines
- Theme variations (light/dark/high-contrast)
- Responsive layouts (phone/tablet)
- Font scaling (85% to 130%)
- Platform-specific styling (iOS/Android)
- Error and empty states
- Loading and interaction states

**Configuration**:

```typescript
const visualConfig = {
  threshold: 0.1, // 10% difference threshold
  includeAA: false, // Ignore anti-aliasing
  diffColor: [255, 0, 0], // Red for differences
  baselineDir: '__tests__/visual/baselines',
  outputDir: '__tests__/visual/output',
  diffDir: '__tests__/visual/diffs',
};
```

### 6. Security Tests

**Location**: `__tests__/security/`

**Purpose**: Identify security vulnerabilities and ensure compliance.

**Key Features**:

- OWASP Mobile Top 10 vulnerability scanning
- Penetration testing simulation
- Authentication security validation
- Data encryption verification
- Device security assessment
- Compliance checking (GDPR, CCPA)

**Security Test Areas**:

- Authentication bypass attempts
- Session management security
- Data encryption at rest and in transit
- Injection vulnerability testing
- Device compromise detection
- PII handling and redaction
- Secure communication validation

**Compliance Standards**:

- OWASP Mobile Security Testing Guide
- NIST Mobile Security Guidelines
- GDPR data protection requirements
- CCPA privacy compliance
- React Native security best practices

## Test Utilities and Helpers

### Global Test Utilities

Available in all tests via `global.testUtils`:

```typescript
// Mock data creation
const contact = global.testUtils.createMockContact(overrides);
const message = global.testUtils.createMockMessage(overrides);

// API response mocking
const response = global.testUtils.mockApiResponse(data, status);

// Async waiting utilities
await global.testUtils.waitFor(condition, timeout);
```

### E2E Test Utilities

Available in E2E tests via `global.e2eUtils`:

```typescript
// Authentication helpers
await global.e2eUtils.loginUser(email, password);
await global.e2eUtils.logoutUser();

// Navigation helpers
await global.e2eUtils.performSearch(query);
await global.e2eUtils.selectContact(name);

// Device simulation
await global.e2eUtils.backgroundApp(duration);
await global.e2eUtils.simulateBiometricAuth(success);
await global.e2eUtils.goOffline();
```

## Continuous Integration

### GitHub Actions Workflow

The CI/CD pipeline runs all test suites automatically:

1. **Unit Tests** - Fast feedback on code changes
2. **Integration Tests** - Validate API and sync functionality
3. **Performance Tests** - Monitor performance regressions
4. **Visual Regression Tests** - Catch UI changes
5. **Security Tests** - Identify vulnerabilities
6. **E2E Tests** - Full workflow validation (main branch only)

### Quality Gates

Tests must pass quality gates to merge:

- ✅ Unit tests must pass (blocking)
- ✅ Integration tests must pass (blocking)
- ✅ Security tests must pass (blocking)
- ⚠️ Performance tests (warning only)
- ⚠️ Visual regression tests (warning only)

### Artifacts and Reporting

The CI system generates comprehensive reports:

- **Coverage Reports** - HTML and LCOV formats
- **Performance Metrics** - JSON reports with trends
- **Visual Diffs** - Images showing UI changes
- **Security Scan Results** - Vulnerability assessments
- **E2E Screenshots** - Failure investigation artifacts

## Best Practices

### Writing Tests

1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **Use Descriptive Names**: Test names should explain the scenario
3. **Mock External Dependencies**: Keep tests isolated and fast
4. **Test Edge Cases**: Include boundary conditions and error scenarios
5. **Maintain Test Data**: Use factories for consistent test data

### Performance Testing

1. **Set Realistic Thresholds**: Based on actual device capabilities
2. **Monitor Trends**: Track performance over time
3. **Test on Real Devices**: Simulators don't reflect real performance
4. **Profile Memory Usage**: Detect leaks early
5. **Measure Battery Impact**: Optimize for mobile constraints

### Visual Testing

1. **Stable Baselines**: Ensure consistent screenshot conditions
2. **Cross-Platform Testing**: Verify consistency across iOS/Android
3. **Theme Coverage**: Test all supported themes
4. **Responsive Design**: Validate layouts across screen sizes
5. **Animation Testing**: Capture key animation frames

### Security Testing

1. **Regular Scans**: Run security tests on every commit
2. **Update Threat Models**: Keep security tests current
3. **Penetration Testing**: Simulate real attack scenarios
4. **Compliance Monitoring**: Ensure regulatory compliance
5. **Incident Response**: Test security incident procedures

## Troubleshooting

### Common Issues

**Test Timeouts**:

```bash
# Increase timeout for slow operations
jest.setTimeout(30000);
```

**Mock Issues**:

```bash
# Clear mocks between tests
beforeEach(() => {
  jest.clearAllMocks();
});
```

**E2E Test Failures**:

```bash
# Check device/simulator status
detox test --configuration ios.sim.debug --loglevel verbose
```

**Visual Test Failures**:

```bash
# Update baselines after intentional changes
npm run test:visual -- --updateSnapshot
```

### Debug Commands

```bash
# Run tests with debug output
npm test -- --verbose

# Run specific test file
npm test ContactManager.test.ts

# Run tests in watch mode
npm run test:watch

# Generate coverage report
npm run test:coverage
```

## Maintenance

### Regular Tasks

1. **Update Dependencies**: Keep testing libraries current
2. **Review Baselines**: Update visual baselines for intentional changes
3. **Monitor Performance**: Track performance trends over time
4. **Security Updates**: Keep security tests current with threats
5. **Clean Artifacts**: Remove old test artifacts and reports

### Metrics Tracking

Monitor these key testing metrics:

- **Test Coverage**: Maintain > 90% coverage
- **Test Execution Time**: Keep under 10 minutes total
- **Flaky Test Rate**: Keep under 1%
- **Security Vulnerability Count**: Maintain zero critical issues
- **Performance Regression Rate**: Monitor trends

## Resources

- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Detox E2E Testing](https://github.com/wix/Detox)
- [React Native Testing Library](https://callstack.github.io/react-native-testing-library/)
- [OWASP Mobile Security](https://owasp.org/www-project-mobile-security-testing-guide/)
- [React Native Performance](https://reactnative.dev/docs/performance)

---

This comprehensive testing framework ensures high-quality, secure, and performant React Native applications through automated testing at every level.
