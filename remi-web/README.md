# R.E.M.I Web App - Next.js Progressive Web App

R.E.M.I (Real-time External Memory Interface) progressive web application built with Next.js, featuring unified authentication, cross-device synchronization, and modern web capabilities.

## 🚀 Quick Start

### Prerequisites

- **Node.js**: 18.0.0 or higher
- **npm**: 8.0.0 or higher
- **Modern Browser**: Chrome 90+, Firefox 88+, Safari 14+

### System Requirements

- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB free space
- **Network**: Stable internet connection for development

## 🌐 Local Development Setup

### 1. Clone and Install Dependencies

```bash
# Navigate to web app directory
cd remi-web

# Install dependencies
npm install

# Verify installation
npm run type-check
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env.local

# Edit environment file
nano .env.local
```

**Required Environment Variables:**

```env
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# App Configuration
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_APP_ENVIRONMENT=development

# Feature Flags
NEXT_PUBLIC_ENABLE_PWA=true
NEXT_PUBLIC_ENABLE_NOTIFICATIONS=true
NEXT_PUBLIC_ENABLE_ANALYTICS=false

# OAuth Configuration (for platform connections)
NEXT_PUBLIC_GMAIL_CLIENT_ID=your_gmail_client_id
NEXT_PUBLIC_SLACK_CLIENT_ID=your_slack_client_id

# Security
NEXT_PUBLIC_CSP_NONCE=development-nonce
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000

# Development Tools
NEXT_PUBLIC_ENABLE_DEVTOOLS=true
ANALYZE=false
```

### 3. Backend Setup

Ensure the R.E.M.I backend is running:

```bash
# In the main project directory
python main.py

# Verify backend is running
curl http://localhost:8000/api/v1/health
```

### 4. Start Development Server

```bash
# Start development server
npm run dev

# Server will start on http://localhost:3000
# Hot reload enabled for development
```

**Alternative Development Commands:**

```bash
# Start with custom port
npm run dev -- -p 3001

# Start with turbo mode (faster builds)
npm run dev -- --turbo

# Start with specific hostname
npm run dev -- -H 0.0.0.0
```

## 🔐 Authentication Setup

### Web Authentication Features

- **JWT Token Management**: Secure token storage with Web Crypto API
- **Session Management**: Cross-tab synchronization
- **OAuth Integration**: Platform connections (Gmail, Slack, etc.)
- **Security Monitoring**: Event logging and anomaly detection

### Local Storage Security

The app uses encrypted localStorage with Web Crypto API:

```javascript
// Automatic encryption for sensitive data
// Fallback to regular localStorage if crypto unavailable
// Secure token refresh with deduplication
```

### OAuth Platform Setup

**Gmail Integration:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Add `http://localhost:3000` to authorized origins
4. Add redirect URI: `http://localhost:3000/auth/callback/gmail`

**Slack Integration:**
1. Go to [Slack API](https://api.slack.com/apps)
2. Create new app
3. Configure OAuth & Permissions
4. Add redirect URI: `http://localhost:3000/auth/callback/slack`

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

### End-to-End Tests (Playwright)

**Setup:**
```bash
# Install Playwright browsers
npx playwright install

# Install system dependencies
npx playwright install-deps
```

**Run E2E Tests:**
```bash
# Run all E2E tests
npm run test:e2e

# Run tests in headed mode (visible browser)
npm run test:e2e:headed

# Run tests with UI mode
npm run test:e2e:ui

# Run specific test file
npx playwright test auth.spec.ts

# Run tests in specific browser
npx playwright test --project=chromium
```

### Component Testing (Storybook)

```bash
# Start Storybook
npm run storybook

# Build Storybook
npm run build-storybook

# Test stories
npm run test-storybook
```

## 🔧 Development Tools

### Next.js DevTools

- **Fast Refresh**: Automatic hot reloading
- **Error Overlay**: Detailed error information
- **Performance Insights**: Built-in performance monitoring

### Browser DevTools Integration

**React DevTools:**
```bash
# Install browser extension
# Automatically detects React components
# Inspect component props and state
```

**Redux DevTools:**
```bash
# Install browser extension
# Monitor Redux state changes
# Time-travel debugging
```

### Code Quality Tools

**ESLint:**
```bash
# Run linting
npm run lint

# Fix auto-fixable issues
npm run lint:fix
```

**TypeScript:**
```bash
# Type checking
npm run type-check

# Build type definitions
npm run build:types
```

**Prettier:**
```bash
# Format code
npm run format

# Check formatting
npm run format:check
```

## 📦 Building for Production

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start

# Export static files (if needed)
npm run export
```

### Build Analysis

```bash
# Analyze bundle size
npm run analyze

# Generate build report
ANALYZE=true npm run build
```

### Performance Optimization

**Automatic Optimizations:**
- Image optimization with Next.js Image component
- Code splitting and lazy loading
- CSS optimization and minification
- JavaScript minification and compression

**Manual Optimizations:**
```bash
# Enable experimental features in next.config.js
experimental: {
  optimizeCss: true,
  optimizePackageImports: ['lodash', 'date-fns']
}
```

## 🚀 Deployment

### Vercel Deployment (Recommended)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy to Vercel
vercel

# Deploy to production
vercel --prod

# Set environment variables
vercel env add NEXT_PUBLIC_API_BASE_URL
```

**Vercel Configuration (vercel.json):**
```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "env": {
    "NEXT_PUBLIC_API_BASE_URL": "@api-base-url"
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
        }
      ]
    }
  ]
}
```

### Netlify Deployment

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Build and deploy
npm run build
netlify deploy --prod --dir=out

# Configure redirects in netlify.toml
```

**Netlify Configuration (netlify.toml):**
```toml
[build]
  command = "npm run build && npm run export"
  publish = "out"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[build.environment]
  NEXT_PUBLIC_API_BASE_URL = "https://your-api.com"
```

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine AS builder
WORKDIR /app
COPY . .
COPY --from=deps /app/node_modules ./node_modules
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
ENV PORT 3000

CMD ["node", "server.js"]
```

**Build and Run:**
```bash
# Build Docker image
docker build -t remi-web .

# Run container
docker run -p 3000:3000 -e NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 remi-web
```

### Self-Hosted Deployment

**Using PM2:**
```bash
# Install PM2
npm install -g pm2

# Build application
npm run build

# Start with PM2
pm2 start npm --name "remi-web" -- start

# Save PM2 configuration
pm2 save
pm2 startup
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## 📱 Progressive Web App (PWA)

### PWA Features

- **Offline Support**: Service worker caching
- **Install Prompt**: Add to home screen
- **Push Notifications**: Web push API
- **Background Sync**: Offline data synchronization

### PWA Configuration

**Manifest (public/manifest.json):**
```json
{
  "name": "R.E.M.I - Real-time External Memory Interface",
  "short_name": "R.E.M.I",
  "description": "Unified communication platform with AI-enhanced search",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#000000",
  "icons": [
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

### Service Worker

```bash
# Service worker automatically generated by next-pwa
# Handles caching, offline support, and background sync
# Configured in next.config.js
```

## 🔍 Troubleshooting

### Common Issues

**Build Errors:**
```bash
# Clear Next.js cache
rm -rf .next

# Clear node_modules
rm -rf node_modules
npm install

# Clear npm cache
npm cache clean --force
```

**TypeScript Errors:**
```bash
# Regenerate type definitions
npm run type-check

# Update TypeScript
npm update typescript @types/node @types/react
```

**Styling Issues:**
```bash
# Clear Tailwind cache
npx tailwindcss -i ./src/styles/globals.css -o ./dist/output.css --watch

# Rebuild CSS
npm run build:css
```

### Authentication Issues

**Token Storage Problems:**
```bash
# Clear browser storage
# Open DevTools → Application → Storage → Clear storage

# Check Web Crypto API support
console.log('Crypto API supported:', !!window.crypto?.subtle)
```

**OAuth Connection Failures:**
```bash
# Verify redirect URIs match exactly
# Check CORS configuration in backend
# Ensure SSL certificates are valid in production
```

**Cross-tab Synchronization Issues:**
```bash
# Check localStorage events
# Verify BroadcastChannel API support
# Test in incognito mode to isolate issues
```

### Performance Issues

**Slow Loading:**
```bash
# Analyze bundle size
npm run analyze

# Check Core Web Vitals
# Use Lighthouse for performance audit
# Enable Next.js speed insights
```

**Memory Leaks:**
```bash
# Use Chrome DevTools Memory tab
# Check for retained event listeners
# Verify proper cleanup in useEffect hooks
```

## 🌐 Browser Support

### Supported Browsers

- **Chrome**: 90+
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+

### Feature Detection

```javascript
// Automatic fallbacks for unsupported features
// Progressive enhancement approach
// Graceful degradation for older browsers
```

## 📊 Monitoring and Analytics

### Performance Monitoring

**Web Vitals:**
```bash
# Built-in Next.js analytics
# Core Web Vitals tracking
# Real User Monitoring (RUM)
```

**Error Tracking:**
```bash
# Configure error boundary
# Integrate with Sentry (optional)
# Custom error reporting
```

### User Analytics

```bash
# Privacy-focused analytics
# GDPR compliant tracking
# Custom event tracking
```

## 📚 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Playwright Testing](https://playwright.dev/)
- [PWA Documentation](https://web.dev/progressive-web-apps/)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.