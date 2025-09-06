# R.E.M.I Authentication System Deployment Guide

This guide covers the complete deployment process for the R.E.M.I unified authentication system across React Native mobile and Next.js web applications.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mobile App    │    │    Web App      │    │   Backend API   │
│  (React Native) │    │   (Next.js)     │    │   (FastAPI)     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Keychain      │    │ • localStorage   │    │ • JWT Tokens    │
│ • Biometrics    │    │ • Web Crypto     │    │ • OAuth 2.0     │
│ • Push Notifs   │    │ • Service Worker │    │ • Session Mgmt  │
│ • Offline Auth  │    │ • PWA Features   │    │ • Security Logs │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Shared Auth   │
                    │   • JWT Tokens  │
                    │   • Cross-Device│
                    │   • Real-time   │
                    │   • Security    │
                    └─────────────────┘
```

## 🚀 Pre-Deployment Checklist

### Backend Requirements

- [ ] FastAPI backend running and accessible
- [ ] PostgreSQL database configured
- [ ] Redis for session management
- [ ] SSL certificates for production
- [ ] OAuth credentials configured
- [ ] Environment variables set

### Security Requirements

- [ ] JWT secret keys generated
- [ ] OAuth client secrets secured
- [ ] CORS policies configured
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Audit logging enabled

### Infrastructure Requirements

- [ ] Domain names registered
- [ ] SSL certificates obtained
- [ ] CDN configured (optional)
- [ ] Monitoring tools setup
- [ ] Backup systems configured
- [ ] Load balancers setup (if needed)

## 📱 Mobile App Deployment

### iOS App Store Deployment

#### 1. Prepare iOS Build

```bash
cd remi-mobile

# Update version numbers
# In package.json
{
  "version": "1.0.0"
}

# In ios/RemiMobile/Info.plist
<key>CFBundleShortVersionString</key>
<string>1.0.0</string>
<key>CFBundleVersion</key>
<string>1</string>
```

#### 2. Configure Production Environment

```bash
# Create production environment file
cp .env.example .env.production

# Configure production variables
API_BASE_URL=https://api.yourdomain.com
WS_URL=wss://api.yourdomain.com/ws
APP_ENVIRONMENT=production
ENABLE_ANALYTICS=true
ENABLE_CRASHLYTICS=true
LOG_LEVEL=error
```

#### 3. Code Signing Setup

```bash
# In Xcode:
# 1. Select project → Signing & Capabilities
# 2. Choose your development team
# 3. Ensure bundle identifier matches App Store Connect
# 4. Configure provisioning profiles

# Verify certificates
security find-identity -v -p codesigning
```

#### 4. Build and Archive

```bash
# Clean previous builds
rm -rf ios/build
cd ios && xcodebuild clean && cd ..

# Install dependencies
npm install
cd ios && pod install && cd ..

# Build release version
npx react-native run-ios --configuration Release

# Archive in Xcode:
# 1. Open ios/RemiMobile.xcworkspace
# 2. Select "Any iOS Device"
# 3. Product → Archive
# 4. Upload to App Store Connect
```

#### 5. App Store Connect Configuration

```bash
# Required information:
# - App name and description
# - Keywords and categories
# - Screenshots (all required sizes)
# - App icon (1024x1024)
# - Privacy policy URL
# - Support URL
# - Age rating questionnaire
```

### Android Play Store Deployment

#### 1. Generate Signing Key

```bash
cd remi-mobile/android/app

# Generate release keystore
keytool -genkeypair -v -keystore remi-release-key.keystore \
  -alias remi-key-alias -keyalg RSA -keysize 2048 -validity 10000

# Configure gradle.properties
echo "MYAPP_RELEASE_STORE_FILE=remi-release-key.keystore" >> ~/.gradle/gradle.properties
echo "MYAPP_RELEASE_KEY_ALIAS=remi-key-alias" >> ~/.gradle/gradle.properties
echo "MYAPP_RELEASE_STORE_PASSWORD=your_store_password" >> ~/.gradle/gradle.properties
echo "MYAPP_RELEASE_KEY_PASSWORD=your_key_password" >> ~/.gradle/gradle.properties
```

#### 2. Build Release APK/AAB

```bash
cd remi-mobile

# Build signed AAB (recommended for Play Store)
cd android && ./gradlew bundleRelease

# Build signed APK (for direct distribution)
cd android && ./gradlew assembleRelease

# Verify signing
jarsigner -verify -verbose -certs android/app/build/outputs/bundle/release/app-release.aab
```

#### 3. Google Play Console Setup

```bash
# Upload AAB to Play Console
# Configure store listing:
# - App title and description
# - Screenshots and graphics
# - Categorization
# - Content rating
# - Pricing and distribution
```

### CodePush Setup (Over-the-Air Updates)

```bash
# Install CodePush CLI
npm install -g code-push-cli

# Create CodePush apps
code-push app add remi-mobile-ios ios react-native
code-push app add remi-mobile-android android react-native

# Configure deployment keys in app
# iOS: ios/RemiMobile/Info.plist
# Android: android/app/src/main/res/values/strings.xml

# Deploy updates
code-push release-react remi-mobile-ios ios --deploymentName Production
code-push release-react remi-mobile-android android --deploymentName Production
```

## 🌐 Web App Deployment

### Vercel Deployment (Recommended)

#### 1. Prepare Build

```bash
cd remi-web

# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login
```

#### 2. Configure Environment Variables

```bash
# Set production environment variables
vercel env add NEXT_PUBLIC_API_BASE_URL production
vercel env add NEXT_PUBLIC_WS_URL production
vercel env add NEXTAUTH_SECRET production
vercel env add NEXTAUTH_URL production

# Add OAuth credentials
vercel env add NEXT_PUBLIC_GMAIL_CLIENT_ID production
vercel env add NEXT_PUBLIC_SLACK_CLIENT_ID production
```

#### 3. Deploy to Production

```bash
# Deploy to production
vercel --prod

# Configure custom domain
vercel domains add yourdomain.com
vercel domains add www.yourdomain.com
```

#### 4. Vercel Configuration

Create `vercel.json`:

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "functions": {
    "app/api/**/*.ts": {
      "maxDuration": 30
    }
  },
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "Referrer-Policy",
          "value": "strict-origin-when-cross-origin"
        },
        {
          "key": "Permissions-Policy",
          "value": "camera=(), microphone=(), geolocation=()"
        }
      ]
    }
  ],
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://api.yourdomain.com/api/:path*"
    }
  ]
}
```

### Netlify Deployment

#### 1. Build Configuration

Create `netlify.toml`:

```toml
[build]
  command = "npm run build"
  publish = ".next"

[build.environment]
  NEXT_PUBLIC_API_BASE_URL = "https://api.yourdomain.com"
  NEXT_PUBLIC_WS_URL = "wss://api.yourdomain.com/ws"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
```

#### 2. Deploy

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Build and deploy
npm run build
netlify deploy --prod --dir=.next
```

### Docker Deployment

#### 1. Create Dockerfile

```dockerfile
# Multi-stage build for production
FROM node:18-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT 3000

CMD ["node", "server.js"]
```

#### 2. Build and Deploy

```bash
# Build Docker image
docker build -t remi-web:latest .

# Run container
docker run -d \
  --name remi-web \
  -p 3000:3000 \
  -e NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com \
  -e NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com/ws \
  remi-web:latest

# Using Docker Compose
version: '3.8'
services:
  web:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
      - NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com/ws
    restart: unless-stopped
```

## 🔧 Backend Configuration

### FastAPI Production Setup

#### 1. Environment Configuration

```bash
# Production environment variables
API_BASE_URL=https://api.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost:5432/remi_prod
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# OAuth Configuration
GMAIL_CLIENT_ID=your-gmail-client-id
GMAIL_CLIENT_SECRET=your-gmail-client-secret
SLACK_CLIENT_ID=your-slack-client-id
SLACK_CLIENT_SECRET=your-slack-client-secret

# Security
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]
ALLOWED_HOSTS=["api.yourdomain.com"]
SECURE_COOKIES=true
HTTPS_ONLY=true

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

#### 2. Database Migration

```bash
# Run database migrations
alembic upgrade head

# Create initial admin user
python scripts/create_admin_user.py
```

#### 3. SSL Configuration

```bash
# Using Let's Encrypt with Certbot
sudo certbot --nginx -d api.yourdomain.com

# Or using custom certificates
# Configure in nginx or load balancer
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔐 Security Configuration

### OAuth Provider Setup

#### Gmail OAuth Setup

1. **Google Cloud Console:**
   ```bash
   # Go to https://console.cloud.google.com/
   # Create new project or select existing
   # Enable Gmail API
   # Create OAuth 2.0 credentials
   ```

2. **Configure Redirect URIs:**
   ```
   # Web app redirects
   https://yourdomain.com/auth/callback/gmail
   https://www.yourdomain.com/auth/callback/gmail
   
   # Mobile app redirects (custom schemes)
   com.remimobile://oauth/gmail
   ```

3. **Scopes Required:**
   ```
   https://www.googleapis.com/auth/gmail.readonly
   https://www.googleapis.com/auth/gmail.send
   https://www.googleapis.com/auth/userinfo.email
   https://www.googleapis.com/auth/userinfo.profile
   ```

#### Slack OAuth Setup

1. **Slack App Configuration:**
   ```bash
   # Go to https://api.slack.com/apps
   # Create new app
   # Configure OAuth & Permissions
   ```

2. **Redirect URIs:**
   ```
   https://yourdomain.com/auth/callback/slack
   com.remimobile://oauth/slack
   ```

3. **Scopes Required:**
   ```
   channels:read
   chat:write
   users:read
   users:read.email
   ```

### Security Headers

#### Web App Security Headers

```javascript
// next.config.js
const securityHeaders = [
  {
    key: 'X-DNS-Prefetch-Control',
    value: 'on'
  },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload'
  },
  {
    key: 'X-XSS-Protection',
    value: '1; mode=block'
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY'
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  },
  {
    key: 'Referrer-Policy',
    value: 'strict-origin-when-cross-origin'
  },
  {
    key: 'Content-Security-Policy',
    value: "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://api.yourdomain.com wss://api.yourdomain.com;"
  }
]
```

#### Mobile App Security

```javascript
// App Transport Security (iOS)
// ios/RemiMobile/Info.plist
<key>NSAppTransportSecurity</key>
<dict>
  <key>NSExceptionDomains</key>
  <dict>
    <key>api.yourdomain.com</key>
    <dict>
      <key>NSExceptionRequiresForwardSecrecy</key>
      <false/>
      <key>NSExceptionMinimumTLSVersion</key>
      <string>TLSv1.2</string>
      <key>NSIncludesSubdomains</key>
      <true/>
    </dict>
  </dict>
</dict>

// Network Security Config (Android)
// android/app/src/main/res/xml/network_security_config.xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">api.yourdomain.com</domain>
    </domain-config>
</network-security-config>
```

## 📊 Monitoring and Analytics

### Application Monitoring

#### Error Tracking (Sentry)

```bash
# Install Sentry
npm install @sentry/react @sentry/nextjs  # Web
npm install @sentry/react-native          # Mobile

# Configure Sentry
# Web: sentry.client.config.js
# Mobile: index.js
```

#### Performance Monitoring

```javascript
// Web Vitals tracking
// pages/_app.tsx
export function reportWebVitals(metric) {
  // Send to analytics service
  analytics.track('Web Vital', {
    name: metric.name,
    value: metric.value,
    id: metric.id,
  })
}

// Mobile performance tracking
// React Native Performance Monitor
import { Performance } from 'react-native-performance'
Performance.mark('app-start')
```

### Security Monitoring

#### Audit Logging

```python
# Backend audit logging
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} in {process_time:.4f}s")
    
    return response
```

#### Rate Limiting

```python
# FastAPI rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginCredentials):
    # Login logic
    pass
```

## 🚨 Incident Response

### Monitoring Alerts

```yaml
# Example monitoring configuration
alerts:
  - name: "High Error Rate"
    condition: "error_rate > 5%"
    duration: "5m"
    actions:
      - email: "alerts@yourdomain.com"
      - slack: "#alerts"
  
  - name: "Authentication Failures"
    condition: "auth_failures > 10/minute"
    duration: "2m"
    actions:
      - email: "security@yourdomain.com"
      - pagerduty: "auth-team"
```

### Rollback Procedures

#### Web App Rollback

```bash
# Vercel rollback
vercel rollback [deployment-url]

# Docker rollback
docker pull remi-web:previous-tag
docker stop remi-web
docker run -d --name remi-web remi-web:previous-tag
```

#### Mobile App Rollback

```bash
# CodePush rollback
code-push rollback remi-mobile-ios Production
code-push rollback remi-mobile-android Production

# App Store rollback
# Use App Store Connect to revert to previous version
```

## 📋 Post-Deployment Checklist

### Functional Testing

- [ ] User registration and login
- [ ] Biometric authentication (mobile)
- [ ] OAuth platform connections
- [ ] Cross-device synchronization
- [ ] Password reset functionality
- [ ] Session management
- [ ] Offline authentication (mobile)
- [ ] Push notifications
- [ ] Security event logging

### Performance Testing

- [ ] Load testing with realistic user scenarios
- [ ] Database query performance
- [ ] API response times
- [ ] Mobile app startup time
- [ ] Web app Core Web Vitals
- [ ] Memory usage monitoring
- [ ] Network request optimization

### Security Testing

- [ ] Penetration testing
- [ ] OAuth flow security
- [ ] JWT token validation
- [ ] HTTPS enforcement
- [ ] CORS configuration
- [ ] Rate limiting effectiveness
- [ ] Input validation
- [ ] XSS protection
- [ ] CSRF protection

### Monitoring Setup

- [ ] Error tracking configured
- [ ] Performance monitoring active
- [ ] Security alerts configured
- [ ] Uptime monitoring
- [ ] Database monitoring
- [ ] Log aggregation
- [ ] Backup verification
- [ ] SSL certificate monitoring

## 🔄 Maintenance and Updates

### Regular Maintenance Tasks

```bash
# Weekly tasks
- Review security logs
- Check error rates
- Monitor performance metrics
- Update dependencies
- Backup verification

# Monthly tasks
- Security audit
- Performance optimization
- Dependency updates
- SSL certificate renewal
- Database maintenance

# Quarterly tasks
- Penetration testing
- Disaster recovery testing
- Architecture review
- Capacity planning
- Security training
```

### Update Procedures

#### Mobile App Updates

```bash
# Minor updates (CodePush)
code-push release-react remi-mobile-ios ios --deploymentName Production

# Major updates (App Store)
# Follow full deployment process
# Increment version numbers
# Submit for review
```

#### Web App Updates

```bash
# Zero-downtime deployment
vercel --prod

# Database migrations
alembic upgrade head

# Feature flag rollouts
# Use feature flags for gradual rollouts
```

This comprehensive deployment guide ensures a secure, scalable, and maintainable authentication system across all platforms. Follow the checklists and procedures to maintain high availability and security standards.