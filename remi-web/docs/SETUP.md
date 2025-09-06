# R.E.M.I Web App Setup Guide

## Prerequisites

### Required Software

1. **Node.js 18+** and **npm/yarn**
   ```bash
   # Check versions
   node --version  # Should be 18.0.0 or higher
   npm --version   # Should be 8.0.0 or higher
   ```

2. **Modern Browser** for development and testing
   - Chrome 90+ (recommended for development)
   - Firefox 88+
   - Safari 14+
   - Edge 90+

3. **Git** for version control

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/remi-web.git
   cd remi-web
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

4. **Start development server**
   ```bash
   npm run dev
   ```

5. **Open browser**
   Navigate to `http://localhost:3000`

## Development

### Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Export static files
npm run export

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
npm run test:e2e
npm run test:e2e:ui
npm run test:e2e:headed

# Bundle analysis
npm run analyze

# Storybook
npm run storybook
npm run build-storybook

# Clean build
npm run clean
```

## Project Structure

```
remi-web/
├── src/
│   ├── components/         # Reusable React components
│   ├── pages/             # Next.js pages
│   ├── hooks/             # Custom React hooks
│   ├── services/          # Business logic and API services
│   ├── store/             # Redux store configuration
│   ├── utils/             # Utility functions
│   ├── types/             # TypeScript type definitions
│   └── constants/         # App constants
├── public/                # Static assets
│   ├── manifest.json      # PWA manifest
│   ├── sw.js             # Service Worker
│   └── icons/            # App icons
├── __tests__/             # Test files
└── docs/                  # Documentation
```

## Key Features to Implement

### 1. Contact-Based Auto-Search
- Advanced search interface with filters
- Real-time search suggestions
- Voice search with Web Speech API
- Natural language query processing
- Search result highlighting and facets

### 2. Progressive Web App Features
- Service Worker for offline functionality
- App installation prompts
- Push notifications
- Background sync
- Responsive design

### 3. Real-Time Synchronization
- WebSocket connection management
- Live updates across tabs
- Optimistic updates
- Conflict resolution

### 4. Advanced Analytics
- Contact relationship visualization
- Communication pattern analysis
- Interactive charts and graphs
- Data export capabilities

### 5. Offline Capabilities
- IndexedDB for local storage
- Offline search within cached data
- Service Worker caching strategies
- Progressive enhancement

## API Integration

The web app integrates with the R.E.M.I backend API. Key endpoints:

- **Authentication**: `/api/v1/auth/*`
- **Contact Search**: `/api/v1/participants/`
- **Advanced Search**: `/api/v1/search/advanced`
- **Contact Analytics**: `/api/v1/contacts/{id}/analytics`
- **Real-time Updates**: WebSocket at `/ws`

## Testing

### Unit Tests with Jest
```bash
npm run test
npm run test:watch
npm run test:coverage
```

### E2E Tests with Playwright
```bash
npm run test:e2e
npm run test:e2e:ui      # Interactive mode
npm run test:e2e:headed  # With browser UI
```

### Component Testing with Storybook
```bash
npm run storybook
```

## PWA Configuration

### Manifest Configuration
The PWA manifest is located at `public/manifest.json` and includes:
- App name and description
- Icons for different sizes
- Theme colors
- Display mode
- Start URL

### Service Worker
The service worker (`public/sw.js`) provides:
- Offline functionality
- Background sync
- Push notifications
- Cache management

### Installation
Users can install the PWA by:
1. Clicking the install prompt
2. Using browser's "Add to Home Screen" option
3. Using the install button in the app

## Performance Optimization

### Build Optimization
- Code splitting with Next.js
- Tree shaking for unused code
- Image optimization
- Bundle analysis with webpack-bundle-analyzer

### Runtime Optimization
- Virtual scrolling for large lists
- Lazy loading of components
- Memoization of expensive operations
- Efficient state management

### Caching Strategies
- Static assets caching
- API response caching
- IndexedDB for offline data
- Service Worker cache management

## Security

### Content Security Policy
Configured in `next.config.js`:
- Prevents XSS attacks
- Controls resource loading
- Enforces HTTPS in production

### Authentication
- JWT token management
- Automatic token refresh
- Secure token storage
- Session management

### Data Protection
- Input validation
- Output sanitization
- HTTPS enforcement
- Privacy controls

## Deployment

### Development Deployment
```bash
npm run build
npm start
```

### Production Deployment

#### Vercel (Recommended)
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

#### Netlify
```bash
# Build static files
npm run build
npm run export

# Deploy to Netlify
# Upload the 'out' folder to Netlify
```

#### Docker
```bash
# Build Docker image
docker build -t remi-web .

# Run container
docker run -p 3000:3000 remi-web
```

### Environment Variables for Deployment

#### Production
```bash
REACT_APP_API_URL=https://api.remi.com
REACT_APP_WS_URL=wss://api.remi.com/ws
REACT_APP_ENVIRONMENT=production
```

#### Staging
```bash
REACT_APP_API_URL=https://staging-api.remi.com
REACT_APP_WS_URL=wss://staging-api.remi.com/ws
REACT_APP_ENVIRONMENT=staging
```

## Monitoring and Analytics

### Performance Monitoring
- Core Web Vitals tracking
- Bundle size monitoring
- Lighthouse CI integration
- Real User Monitoring (RUM)

### Error Tracking
- Sentry integration for error reporting
- Console error monitoring
- User feedback collection

### Analytics
- Google Analytics integration
- Custom event tracking
- User behavior analysis
- A/B testing capabilities

## Browser Support

### Supported Browsers
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Progressive Enhancement
- Core functionality works in older browsers
- Enhanced features for modern browsers
- Graceful degradation for unsupported features

## Accessibility

### WCAG 2.1 AA Compliance
- Keyboard navigation
- Screen reader support
- Color contrast compliance
- Focus management
- ARIA labels and roles

### Testing
- Automated accessibility testing
- Manual testing with screen readers
- Keyboard-only navigation testing

## Troubleshooting

### Common Issues

1. **Build errors**
   ```bash
   npm run clean
   npm install
   npm run build
   ```

2. **Type errors**
   ```bash
   npm run type-check
   ```

3. **Linting errors**
   ```bash
   npm run lint:fix
   ```

4. **Service Worker issues**
   - Clear browser cache
   - Unregister service worker in DevTools
   - Hard refresh (Ctrl+Shift+R)

5. **PWA installation issues**
   - Check manifest.json validity
   - Ensure HTTPS in production
   - Verify service worker registration

### Performance Issues

1. **Slow loading**
   - Check bundle size with `npm run analyze`
   - Optimize images and assets
   - Implement code splitting

2. **Memory leaks**
   - Use React DevTools Profiler
   - Check for unsubscribed event listeners
   - Verify proper cleanup in useEffect

## Contributing

1. Follow the development guide in `DEVELOPMENT_GUIDE.md`
2. Use TypeScript for all new code
3. Write tests for new features
4. Follow accessibility guidelines
5. Test across different browsers
6. Update documentation as needed

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the development guide
- Run the test suite to identify issues
- Create an issue in the GitHub repository
- Contact the development team

## Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [PWA Documentation](https://web.dev/progressive-web-apps/)
- [Playwright Testing](https://playwright.dev)
- [Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)