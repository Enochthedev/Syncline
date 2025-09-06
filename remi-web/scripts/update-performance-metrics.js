/**
 * Performance Metrics Update Script
 * Sends performance data to monitoring dashboards
 */

const fs = require('fs').promises;
const path = require('path');
const fetch = require('node-fetch');

class PerformanceMetricsUpdater {
    constructor() {
        this.grafanaApiKey = process.env.GRAFANA_API_KEY;
        this.grafanaUrl = process.env.GRAFANA_URL || 'https://grafana.remi.com';
        this.datadogApiKey = process.env.DATADOG_API_KEY;
        this.datadogAppKey = process.env.DATADOG_APP_KEY;
        this.environment = process.env.NODE_ENV || 'production';
    }

    async updateMetrics() {
        try {
            // Find the latest performance report
            const reportsDir = './performance-reports';
            const files = await fs.readdir(reportsDir);
            const summaryFiles = files.filter(f => f.startsWith('summary-')).sort().reverse();

            if (summaryFiles.length === 0) {
                console.log('No performance reports found');
                return;
            }

            const latestReport = path.join(reportsDir, summaryFiles[0]);
            const reportData = JSON.parse(await fs.readFile(latestReport, 'utf8'));

            console.log(`Processing report: ${summaryFiles[0]}`);

            // Send to different monitoring services
            await Promise.all([
                this.sendToGrafana(reportData),
                this.sendToDatadog(reportData),
                this.updateHealthCheck(reportData),
            ]);

            console.log('✅ Performance metrics updated successfully');
        } catch (error) {
            console.error('❌ Failed to update performance metrics:', error);
            throw error;
        }
    }

    async sendToGrafana(reportData) {
        if (!this.grafanaApiKey) {
            console.log('Grafana API key not configured, skipping Grafana update');
            return;
        }

        try {
            const metrics = this.formatGrafanaMetrics(reportData);

            const response = await fetch(`${this.grafanaUrl}/api/annotations`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.grafanaApiKey}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    time: Date.now(),
                    timeEnd: Date.now(),
                    tags: ['performance', 'web-vitals', this.environment],
                    text: `Performance Report: ${reportData.overallScore}`,
                    title: 'Web Vitals Update',
                }),
            });

            if (response.ok) {
                console.log('✓ Grafana annotation created');
            } else {
                console.error('✗ Failed to create Grafana annotation:', response.statusText);
            }

            // Send metrics to Grafana via Prometheus pushgateway if configured
            await this.sendToPrometheus(metrics);

        } catch (error) {
            console.error('Error sending to Grafana:', error);
        }
    }

    async sendToPrometheus(metrics) {
        const pushgatewayUrl = process.env.PROMETHEUS_PUSHGATEWAY_URL;
        if (!pushgatewayUrl) return;

        try {
            const prometheusMetrics = this.formatPrometheusMetrics(metrics);

            const response = await fetch(`${pushgatewayUrl}/metrics/job/web-vitals/instance/${this.environment}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'text/plain',
                },
                body: prometheusMetrics,
            });

            if (response.ok) {
                console.log('✓ Metrics sent to Prometheus');
            } else {
                console.error('✗ Failed to send to Prometheus:', response.statusText);
            }
        } catch (error) {
            console.error('Error sending to Prometheus:', error);
        }
    }

    formatPrometheusMetrics(metrics) {
        const timestamp = Date.now();
        let output = '';

        // Core Web Vitals
        if (metrics.LCP) {
            output += `# HELP web_vitals_lcp Largest Contentful Paint in milliseconds\n`;
            output += `# TYPE web_vitals_lcp gauge\n`;
            output += `web_vitals_lcp{environment="${this.environment}"} ${metrics.LCP} ${timestamp}\n`;
        }

        if (metrics.FID) {
            output += `# HELP web_vitals_fid First Input Delay in milliseconds\n`;
            output += `# TYPE web_vitals_fid gauge\n`;
            output += `web_vitals_fid{environment="${this.environment}"} ${metrics.FID} ${timestamp}\n`;
        }

        if (metrics.CLS) {
            output += `# HELP web_vitals_cls Cumulative Layout Shift score\n`;
            output += `# TYPE web_vitals_cls gauge\n`;
            output += `web_vitals_cls{environment="${this.environment}"} ${metrics.CLS} ${timestamp}\n`;
        }

        if (metrics.FCP) {
            output += `# HELP web_vitals_fcp First Contentful Paint in milliseconds\n`;
            output += `# TYPE web_vitals_fcp gauge\n`;
            output += `web_vitals_fcp{environment="${this.environment}"} ${metrics.FCP} ${timestamp}\n`;
        }

        return output;
    }

    async sendToDatadog(reportData) {
        if (!this.datadogApiKey || !this.datadogAppKey) {
            console.log('Datadog API keys not configured, skipping Datadog update');
            return;
        }

        try {
            const metrics = this.formatDatadogMetrics(reportData);

            const response = await fetch('https://api.datadoghq.com/api/v1/series', {
                method: 'POST',
                headers: {
                    'DD-API-KEY': this.datadogApiKey,
                    'DD-APPLICATION-KEY': this.datadogAppKey,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ series: metrics }),
            });

            if (response.ok) {
                console.log('✓ Metrics sent to Datadog');
            } else {
                console.error('✗ Failed to send to Datadog:', response.statusText);
            }
        } catch (error) {
            console.error('Error sending to Datadog:', error);
        }
    }

    formatGrafanaMetrics(reportData) {
        return {
            timestamp: new Date(reportData.timestamp).getTime(),
            environment: this.environment,
            overallScore: reportData.overallScore,
            metrics: reportData.metrics,
            issueCount: reportData.issues.length,
        };
    }

    formatDatadogMetrics(reportData) {
        const timestamp = Math.floor(Date.now() / 1000);
        const tags = [`environment:${this.environment}`, 'source:web-vitals'];

        const series = [];

        // Core Web Vitals metrics
        Object.entries(reportData.metrics).forEach(([metric, value]) => {
            if (typeof value === 'number') {
                series.push({
                    metric: `remi.web_vitals.${metric.toLowerCase()}`,
                    points: [[timestamp, value]],
                    tags: [...tags, `metric:${metric}`],
                    type: 'gauge',
                });
            }
        });

        // Overall score as numeric value
        const scoreValue = reportData.overallScore === 'good' ? 3 :
            reportData.overallScore === 'needs-improvement' ? 2 : 1;

        series.push({
            metric: 'remi.web_vitals.overall_score',
            points: [[timestamp, scoreValue]],
            tags: [...tags, `score:${reportData.overallScore}`],
            type: 'gauge',
        });

        // Issue count
        series.push({
            metric: 'remi.web_vitals.issue_count',
            points: [[timestamp, reportData.issues.length]],
            tags,
            type: 'gauge',
        });

        return series;
    }

    async updateHealthCheck(reportData) {
        try {
            const healthCheckUrl = process.env.HEALTH_CHECK_URL;
            if (!healthCheckUrl) return;

            const isHealthy = reportData.overallScore !== 'poor' && reportData.issues.length < 5;

            const response = await fetch(healthCheckUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${process.env.HEALTH_CHECK_TOKEN}`,
                },
                body: JSON.stringify({
                    service: 'web-performance',
                    status: isHealthy ? 'healthy' : 'degraded',
                    timestamp: reportData.timestamp,
                    details: {
                        overallScore: reportData.overallScore,
                        issueCount: reportData.issues.length,
                        criticalIssues: reportData.issues.filter(i =>
                            i.metric === 'LCP' || i.metric === 'CLS'
                        ).length,
                    },
                }),
            });

            if (response.ok) {
                console.log('✓ Health check updated');
            } else {
                console.error('✗ Failed to update health check:', response.statusText);
            }
        } catch (error) {
            console.error('Error updating health check:', error);
        }
    }

    async createPerformanceDashboard() {
        if (!this.grafanaApiKey) return;

        const dashboard = {
            dashboard: {
                title: 'R.E.M.I Web Performance',
                tags: ['performance', 'web-vitals'],
                timezone: 'browser',
                panels: [
                    {
                        title: 'Core Web Vitals',
                        type: 'stat',
                        targets: [
                            {
                                expr: 'web_vitals_lcp',
                                legendFormat: 'LCP (ms)',
                            },
                            {
                                expr: 'web_vitals_fid',
                                legendFormat: 'FID (ms)',
                            },
                            {
                                expr: 'web_vitals_cls',
                                legendFormat: 'CLS',
                            },
                        ],
                        fieldConfig: {
                            defaults: {
                                thresholds: {
                                    steps: [
                                        { color: 'green', value: null },
                                        { color: 'yellow', value: 2500 },
                                        { color: 'red', value: 4000 },
                                    ],
                                },
                            },
                        },
                    },
                    {
                        title: 'Performance Trends',
                        type: 'graph',
                        targets: [
                            {
                                expr: 'web_vitals_lcp',
                                legendFormat: 'LCP',
                            },
                            {
                                expr: 'web_vitals_fcp',
                                legendFormat: 'FCP',
                            },
                        ],
                    },
                ],
            },
        };

        try {
            const response = await fetch(`${this.grafanaUrl}/api/dashboards/db`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.grafanaApiKey}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(dashboard),
            });

            if (response.ok) {
                console.log('✓ Performance dashboard created/updated');
            } else {
                console.error('✗ Failed to create dashboard:', response.statusText);
            }
        } catch (error) {
            console.error('Error creating dashboard:', error);
        }
    }

    async setupAlerts() {
        if (!this.grafanaApiKey) return;

        const alerts = [
            {
                name: 'High LCP Alert',
                message: 'Largest Contentful Paint is above threshold',
                frequency: '1m',
                conditions: [
                    {
                        query: { queryType: '', refId: 'A' },
                        reducer: { type: 'last', params: [] },
                        evaluator: { params: [4000], type: 'gt' },
                    },
                ],
                executionErrorState: 'alerting',
                noDataState: 'no_data',
                for: '5m',
            },
            {
                name: 'High CLS Alert',
                message: 'Cumulative Layout Shift is above threshold',
                frequency: '1m',
                conditions: [
                    {
                        query: { queryType: '', refId: 'A' },
                        reducer: { type: 'last', params: [] },
                        evaluator: { params: [0.25], type: 'gt' },
                    },
                ],
                executionErrorState: 'alerting',
                noDataState: 'no_data',
                for: '5m',
            },
        ];

        for (const alert of alerts) {
            try {
                const response = await fetch(`${this.grafanaUrl}/api/alerts`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.grafanaApiKey}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(alert),
                });

                if (response.ok) {
                    console.log(`✓ Alert "${alert.name}" created/updated`);
                } else {
                    console.error(`✗ Failed to create alert "${alert.name}":`, response.statusText);
                }
            } catch (error) {
                console.error(`Error creating alert "${alert.name}":`, error);
            }
        }
    }
}

// Main execution
async function main() {
    const updater = new PerformanceMetricsUpdater();

    try {
        await updater.updateMetrics();

        // Setup dashboard and alerts if this is the first run
        if (process.argv.includes('--setup')) {
            await updater.createPerformanceDashboard();
            await updater.setupAlerts();
        }

    } catch (error) {
        console.error('Failed to update performance metrics:', error);
        process.exit(1);
    }
}

// Run if called directly
if (require.main === module) {
    main();
}

module.exports = { PerformanceMetricsUpdater };