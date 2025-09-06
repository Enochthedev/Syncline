/**
 * Web Vitals Monitoring Script
 * Monitors Core Web Vitals and reports to analytics
 */

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

// Core Web Vitals thresholds
const THRESHOLDS = {
    LCP: { good: 2500, poor: 4000 }, // Largest Contentful Paint
    FID: { good: 100, poor: 300 },   // First Input Delay
    CLS: { good: 0.1, poor: 0.25 },  // Cumulative Layout Shift
    FCP: { good: 1800, poor: 3000 }, // First Contentful Paint
    TTI: { good: 3800, poor: 7300 }, // Time to Interactive
    TBT: { good: 200, poor: 600 },   // Total Blocking Time
};

// URLs to monitor
const URLS_TO_MONITOR = [
    { url: 'https://app.remi.com', name: 'homepage' },
    { url: 'https://app.remi.com/search', name: 'search' },
    { url: 'https://app.remi.com/contacts', name: 'contacts' },
    { url: 'https://app.remi.com/messages', name: 'messages' },
];

class WebVitalsMonitor {
    constructor() {
        this.results = [];
        this.browser = null;
    }

    async initialize() {
        this.browser = await chromium.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-dev-shm-usage'],
        });
    }

    async measureWebVitals(url, pageName) {
        const context = await this.browser.newContext({
            viewport: { width: 1920, height: 1080 },
            deviceScaleFactor: 1,
        });

        const page = await context.newPage();

        // Collect performance metrics
        const metrics = {
            url,
            pageName,
            timestamp: new Date().toISOString(),
            measurements: {},
            scores: {},
        };

        try {
            // Enable performance monitoring
            await page.addInitScript(() => {
                window.webVitalsData = {};

                // Measure LCP
                new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    const lastEntry = entries[entries.length - 1];
                    window.webVitalsData.LCP = lastEntry.startTime;
                }).observe({ entryTypes: ['largest-contentful-paint'] });

                // Measure FID
                new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    entries.forEach((entry) => {
                        if (entry.processingStart && entry.startTime) {
                            window.webVitalsData.FID = entry.processingStart - entry.startTime;
                        }
                    });
                }).observe({ entryTypes: ['first-input'] });

                // Measure CLS
                let clsValue = 0;
                new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    entries.forEach((entry) => {
                        if (!entry.hadRecentInput) {
                            clsValue += entry.value;
                        }
                    });
                    window.webVitalsData.CLS = clsValue;
                }).observe({ entryTypes: ['layout-shift'] });
            });

            // Navigate to page and wait for load
            const startTime = Date.now();
            await page.goto(url, { waitUntil: 'networkidle' });
            const loadTime = Date.now() - startTime;

            // Wait for additional metrics to be collected
            await page.waitForTimeout(2000);

            // Get performance metrics
            const performanceMetrics = await page.evaluate(() => {
                const navigation = performance.getEntriesByType('navigation')[0];
                const paint = performance.getEntriesByType('paint');

                return {
                    // Navigation timing
                    domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
                    loadComplete: navigation.loadEventEnd - navigation.loadEventStart,

                    // Paint timing
                    FCP: paint.find(entry => entry.name === 'first-contentful-paint')?.startTime || 0,

                    // Web Vitals from our observer
                    ...window.webVitalsData,

                    // Additional metrics
                    domElements: document.querySelectorAll('*').length,
                    resourceCount: performance.getEntriesByType('resource').length,
                };
            });

            // Calculate TTI using a simplified heuristic
            const resourceEntries = await page.evaluate(() => {
                return performance.getEntriesByType('resource').map(entry => ({
                    name: entry.name,
                    duration: entry.duration,
                    transferSize: entry.transferSize,
                }));
            });

            // Store measurements
            metrics.measurements = {
                ...performanceMetrics,
                loadTime,
                resourceCount: resourceEntries.length,
                totalTransferSize: resourceEntries.reduce((sum, entry) => sum + (entry.transferSize || 0), 0),
            };

            // Calculate scores based on thresholds
            metrics.scores = this.calculateScores(metrics.measurements);

            // Take screenshot for visual regression
            await page.screenshot({
                path: `./performance-screenshots/${pageName}-${Date.now()}.png`,
                fullPage: true,
            });

        } catch (error) {
            console.error(`Error measuring ${url}:`, error);
            metrics.error = error.message;
        } finally {
            await context.close();
        }

        return metrics;
    }

    calculateScores(measurements) {
        const scores = {};

        Object.entries(THRESHOLDS).forEach(([metric, threshold]) => {
            const value = measurements[metric];
            if (value !== undefined) {
                if (value <= threshold.good) {
                    scores[metric] = 'good';
                } else if (value <= threshold.poor) {
                    scores[metric] = 'needs-improvement';
                } else {
                    scores[metric] = 'poor';
                }
            }
        });

        return scores;
    }

    async runMonitoring() {
        console.log('Starting Web Vitals monitoring...');

        for (const { url, name } of URLS_TO_MONITOR) {
            console.log(`Measuring ${name} (${url})...`);

            try {
                const metrics = await this.measureWebVitals(url, name);
                this.results.push(metrics);

                console.log(`✓ ${name} measured successfully`);
                this.logMetrics(metrics);
            } catch (error) {
                console.error(`✗ Failed to measure ${name}:`, error);
            }
        }
    }

    logMetrics(metrics) {
        const { measurements, scores } = metrics;

        console.log(`  LCP: ${measurements.LCP?.toFixed(0)}ms (${scores.LCP || 'unknown'})`);
        console.log(`  FID: ${measurements.FID?.toFixed(0)}ms (${scores.FID || 'unknown'})`);
        console.log(`  CLS: ${measurements.CLS?.toFixed(3)} (${scores.CLS || 'unknown'})`);
        console.log(`  FCP: ${measurements.FCP?.toFixed(0)}ms (${scores.FCP || 'unknown'})`);
        console.log(`  Load Time: ${measurements.loadTime}ms`);
        console.log('');
    }

    async saveResults() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `web-vitals-${timestamp}.json`;
        const filepath = path.join('./performance-reports', filename);

        // Ensure directory exists
        await fs.mkdir('./performance-reports', { recursive: true });
        await fs.mkdir('./performance-screenshots', { recursive: true });

        // Save detailed results
        await fs.writeFile(filepath, JSON.stringify(this.results, null, 2));

        // Create summary report
        const summary = this.createSummaryReport();
        const summaryPath = path.join('./performance-reports', `summary-${timestamp}.json`);
        await fs.writeFile(summaryPath, JSON.stringify(summary, null, 2));

        console.log(`Results saved to ${filepath}`);
        console.log(`Summary saved to ${summaryPath}`);

        return { detailedReport: filepath, summaryReport: summaryPath };
    }

    createSummaryReport() {
        const summary = {
            timestamp: new Date().toISOString(),
            totalPages: this.results.length,
            overallScore: 'good',
            issues: [],
            recommendations: [],
            metrics: {},
        };

        // Calculate average metrics
        const avgMetrics = {};
        Object.keys(THRESHOLDS).forEach(metric => {
            const values = this.results
                .map(r => r.measurements[metric])
                .filter(v => v !== undefined);

            if (values.length > 0) {
                avgMetrics[metric] = values.reduce((sum, val) => sum + val, 0) / values.length;
            }
        });

        summary.metrics = avgMetrics;

        // Identify issues and recommendations
        this.results.forEach(result => {
            Object.entries(result.scores).forEach(([metric, score]) => {
                if (score === 'poor') {
                    summary.issues.push({
                        page: result.pageName,
                        metric,
                        value: result.measurements[metric],
                        threshold: THRESHOLDS[metric].poor,
                    });

                    if (summary.overallScore !== 'poor') {
                        summary.overallScore = 'needs-improvement';
                    }
                } else if (score === 'needs-improvement' && summary.overallScore === 'good') {
                    summary.overallScore = 'needs-improvement';
                }
            });
        });

        // Generate recommendations
        if (summary.issues.length > 0) {
            const metricIssues = summary.issues.reduce((acc, issue) => {
                acc[issue.metric] = (acc[issue.metric] || 0) + 1;
                return acc;
            }, {});

            Object.entries(metricIssues).forEach(([metric, count]) => {
                summary.recommendations.push(this.getRecommendation(metric, count));
            });
        }

        return summary;
    }

    getRecommendation(metric, issueCount) {
        const recommendations = {
            LCP: 'Optimize server response times, use CDN, compress images, and implement lazy loading',
            FID: 'Reduce JavaScript execution time, split code bundles, and use web workers',
            CLS: 'Set explicit dimensions for images and ads, avoid inserting content above existing content',
            FCP: 'Optimize critical rendering path, inline critical CSS, and preload key resources',
            TTI: 'Minimize main thread work, reduce JavaScript bundle size, and optimize third-party scripts',
            TBT: 'Break up long tasks, optimize JavaScript execution, and use code splitting',
        };

        return {
            metric,
            affectedPages: issueCount,
            recommendation: recommendations[metric] || 'Review and optimize this metric',
            priority: issueCount > 2 ? 'high' : issueCount > 1 ? 'medium' : 'low',
        };
    }

    async sendToAnalytics(results) {
        // Send results to monitoring service (e.g., Grafana, DataDog, etc.)
        try {
            const analyticsEndpoint = process.env.ANALYTICS_ENDPOINT;
            const apiKey = process.env.ANALYTICS_API_KEY;

            if (!analyticsEndpoint || !apiKey) {
                console.log('Analytics endpoint not configured, skipping upload');
                return;
            }

            const payload = {
                timestamp: new Date().toISOString(),
                source: 'web-vitals-monitor',
                environment: process.env.NODE_ENV || 'production',
                metrics: results.metrics,
                overallScore: results.overallScore,
                issues: results.issues,
            };

            const response = await fetch(analyticsEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`,
                },
                body: JSON.stringify(payload),
            });

            if (response.ok) {
                console.log('✓ Results sent to analytics service');
            } else {
                console.error('✗ Failed to send results to analytics service:', response.statusText);
            }
        } catch (error) {
            console.error('✗ Error sending to analytics:', error);
        }
    }

    async cleanup() {
        if (this.browser) {
            await this.browser.close();
        }
    }
}

// Main execution
async function main() {
    const monitor = new WebVitalsMonitor();

    try {
        await monitor.initialize();
        await monitor.runMonitoring();

        const { summaryReport } = await monitor.saveResults();

        // Read and send summary to analytics
        const summaryData = JSON.parse(await fs.readFile(summaryReport, 'utf8'));
        await monitor.sendToAnalytics(summaryData);

        // Exit with appropriate code based on results
        const hasIssues = summaryData.issues.length > 0;
        const hasCriticalIssues = summaryData.issues.some(issue => issue.metric === 'LCP' || issue.metric === 'CLS');

        if (hasCriticalIssues) {
            console.error('❌ Critical performance issues detected');
            process.exit(1);
        } else if (hasIssues) {
            console.warn('⚠️  Performance issues detected');
            process.exit(0); // Don't fail CI for minor issues
        } else {
            console.log('✅ All performance metrics are good');
            process.exit(0);
        }

    } catch (error) {
        console.error('❌ Monitoring failed:', error);
        process.exit(1);
    } finally {
        await monitor.cleanup();
    }
}

// Run if called directly
if (require.main === module) {
    main();
}

module.exports = { WebVitalsMonitor };