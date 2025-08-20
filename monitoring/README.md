# MESH Monitoring and Observability

This directory contains the complete monitoring and observability stack for the MESH (Multi-platform External Source Hub) Ingestion System.

## Overview

The monitoring system provides:

- **Metrics Collection**: Prometheus-based metrics for all system components
- **Health Monitoring**: Comprehensive health checks for services and connectors
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Visualization**: Grafana dashboards for system insights
- **Alerting**: Prometheus Alertmanager for proactive notifications

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MESH API      │    │   Prometheus    │    │    Grafana      │
│                 │───▶│                 │───▶│                 │
│ /monitoring/*   │    │   Metrics DB    │    │   Dashboards    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │  Alertmanager   │              │
         │              │                 │              │
         │              │   Notifications │              │
         │              └─────────────────┘              │
         │                                                │
         ▼                                                ▼
┌─────────────────┐                            ┌─────────────────┐
│ Structured Logs │                            │   Dashboards    │
│                 │                            │                 │
│ JSON + Corr IDs │                            │ - System Health │
└─────────────────┘                            │ - Performance   │
                                               │ - Business KPIs │
                                               └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for testing)

### 1. Start Monitoring Stack

```bash
# Start all monitoring services
python scripts/setup_monitoring.py start
```

This will start:
- **Prometheus** (http://localhost:9090) - Metrics collection
- **Grafana** (http://localhost:3000) - Visualization (admin/admin)
- **Alertmanager** (http://localhost:9093) - Alert management
- **Node Exporter** (http://localhost:9100) - System metrics

### 2. Start MESH Application

```bash
# Start the main application
python main.py
```

The application will automatically:
- Register health checks
- Start collecting metrics
- Enable structured logging
- Expose monitoring endpoints

### 3. View Dashboards

1. Open Grafana: http://localhost:3000
2. Login with admin/admin
3. Import dashboards from `monitoring/grafana/dashboards/`
4. View real-time system metrics

## Monitoring Endpoints

The MESH API exposes several monitoring endpoints:

### Metrics
```bash
# Prometheus metrics
GET /api/v1/monitoring/metrics
```

### Health Checks
```bash
# Overall system health
GET /api/v1/monitoring/health

# Specific component health
GET /api/v1/monitoring/health/{component}

# Cached health results (fast)
GET /api/v1/monitoring/health/cached/all

# Force health check refresh
POST /api/v1/monitoring/health/refresh

# Simple status for load balancers
GET /api/v1/monitoring/status
```

### Legacy Health Endpoints
```bash
# Basic health check
GET /api/v1/health/

# Detailed health information
GET /api/v1/health/detailed
```

## Metrics Categories

### System Metrics
- `mesh_system_info` - System version and environment
- `mesh_active_connections` - Database/Redis connections
- `mesh_memory_usage_bytes` - Memory usage by component

### API Metrics
- `mesh_api_requests_total` - Total API requests by endpoint/status
- `mesh_api_request_duration_seconds` - API response times

### Message Processing
- `mesh_messages_ingested_total` - Messages ingested by platform
- `mesh_message_ingestion_duration_seconds` - Ingestion latency

### AI Processing
- `mesh_ai_operations_total` - AI operations by agent/status
- `mesh_ai_processing_duration_seconds` - AI processing times

### Connector Health
- `mesh_connector_health` - Platform connector status (1=healthy, 0=unhealthy)
- `mesh_connector_operations_total` - Connector operations

### Database Operations
- `mesh_database_operations_total` - Database operations by table
- `mesh_database_operation_duration_seconds` - Database query times

### Vector Database
- `mesh_vector_operations_total` - Vector DB operations
- `mesh_vector_operation_duration_seconds` - Vector operation times

### Search Operations
- `mesh_search_queries_total` - Search queries by type
- `mesh_search_duration_seconds` - Search response times

### Event Bus
- `mesh_events_published_total` - Events published to Redis Streams
- `mesh_events_consumed_total` - Events consumed by consumer groups

### Business Metrics
- `mesh_active_users` - Number of active users
- `mesh_total_threads` - Total conversation threads by platform
- `mesh_total_messages` - Total messages stored by platform

## Health Checks

The system includes comprehensive health checks:

### Core Infrastructure
- **Database** (Critical) - PostgreSQL connectivity
- **Redis** (Critical) - Redis connectivity and ping
- **Vector DB** (Non-critical) - ChromaDB connectivity
- **AI Engine** (Non-critical) - AI processing engine status

### Health Status Levels
- **Healthy** - All systems operational
- **Degraded** - Some non-critical systems slow/failing
- **Unhealthy** - Critical systems failing

## Structured Logging

All logs are structured JSON with correlation IDs:

```json
{
  "timestamp": "2024-01-16T10:30:00.000Z",
  "level": "INFO",
  "service": "mesh-system",
  "logger": "services.ai.engine",
  "message": "AI processing completed",
  "correlation_id": "req-123e4567-e89b-12d3-a456-426614174000",
  "module": "engine",
  "function": "process_message",
  "line": 145,
  "extra": {
    "agent_type": "entity_extractor",
    "duration_ms": 234.5,
    "entities_found": 3
  }
}
```

### Correlation ID Flow
- Generated automatically for each API request
- Propagated through all async operations
- Included in all log entries
- Returned in API response headers

## Dashboards

### 1. System Overview (`mesh-system-overview.json`)
- System health status matrix
- API request rates and response times
- Message ingestion rates
- AI processing performance
- Database operation metrics
- Active connections and memory usage

### 2. Platform Connectors (`mesh-connectors.json`)
- Connector health matrix
- Message ingestion by platform
- Connector operation rates
- Ingestion latency percentiles
- Total messages and threads by platform

### 3. AI Processing (`mesh-ai-processing.json`)
- AI operation rates by agent type
- AI processing latency percentiles
- Vector database operations
- Search query performance
- Error rates and success metrics

## Alerting

### Alert Rules

#### Critical Alerts
- **System Down** - API unavailable for >1 minute
- **High Error Rate** - >10% API errors for >5 minutes
- **No Active Users** - Zero users for >15 minutes

#### Performance Alerts
- **High API Latency** - 95th percentile >2 seconds for >5 minutes
- **Slow Message Ingestion** - 95th percentile >10 seconds for >5 minutes
- **Slow AI Processing** - 95th percentile >30 seconds for >10 minutes

#### Infrastructure Alerts
- **Connector Unhealthy** - Platform connector down for >2 minutes
- **High Database Connections** - >50 connections for >5 minutes
- **High Memory Usage** - >1GB for component for >10 minutes

### Alert Channels
- **Email** - Critical and warning alerts
- **Webhooks** - Integration with external systems
- **Slack/Discord** - Team notifications (configure in alertmanager.yml)

## Configuration

### Prometheus Configuration
Edit `prometheus/prometheus.yml` to:
- Add new scrape targets
- Adjust scrape intervals
- Configure recording rules

### Grafana Configuration
- Datasources: `grafana/datasources/prometheus.yml`
- Dashboard provisioning: `grafana/dashboards/dashboard-config.yml`
- Custom dashboards: Add JSON files to `grafana/dashboards/`

### Alertmanager Configuration
Edit `alertmanager/alertmanager.yml` to:
- Configure notification channels
- Set up routing rules
- Define inhibition rules

## Development

### Adding New Metrics

1. **Define the metric** in `services/monitoring/metrics.py`:
```python
self.custom_metric = Counter(
    'mesh_custom_metric_total',
    'Description of custom metric',
    ['label1', 'label2'],
    registry=self.registry
)
```

2. **Record the metric** in your code:
```python
from services.monitoring.metrics import get_metrics_collector

metrics = get_metrics_collector()
metrics.custom_metric.labels(label1="value1", label2="value2").inc()
```

3. **Add to dashboard** by editing the appropriate JSON file

### Adding New Health Checks

1. **Create health check function**:
```python
async def my_service_health_check() -> HealthCheckResult:
    try:
        # Check your service
        return HealthCheckResult(
            name="my_service",
            status=HealthStatus.HEALTHY,
            message="Service is running"
        )
    except Exception as e:
        return HealthCheckResult(
            name="my_service",
            status=HealthStatus.UNHEALTHY,
            message=f"Service failed: {e}"
        )
```

2. **Register the check**:
```python
from services.monitoring.health import get_health_checker, HealthCheck

health_checker = get_health_checker()
health_checker.register_check(HealthCheck(
    name="my_service",
    check_func=my_service_health_check,
    critical=True,  # Set to False for non-critical services
    tags=["custom", "service"]
))
```

### Testing

Run the monitoring test suite:

```bash
# Test metrics collection
pytest tests/test_monitoring_metrics.py -v

# Test health checks
pytest tests/test_monitoring_health.py -v

# Test structured logging
pytest tests/test_monitoring_logging.py -v

# Test API endpoints
pytest tests/test_monitoring_api.py -v

# Test monitoring services
python scripts/setup_monitoring.py test
```

## Troubleshooting

### Common Issues

#### Prometheus Not Scraping Metrics
1. Check if MESH API is running on port 8000
2. Verify `/api/v1/monitoring/metrics` endpoint is accessible
3. Check Prometheus logs: `docker logs mesh-prometheus`

#### Grafana Dashboards Not Loading
1. Ensure Prometheus datasource is configured
2. Check dashboard JSON syntax
3. Verify dashboard provisioning configuration

#### Health Checks Failing
1. Check database connectivity
2. Verify Redis is running
3. Ensure AI services are initialized
4. Check application logs for errors

#### High Memory Usage
1. Monitor metrics collection frequency
2. Check for metric label cardinality issues
3. Review log retention settings

### Logs and Debugging

```bash
# View monitoring stack logs
cd monitoring
docker-compose -f docker-compose.monitoring.yml logs -f

# View specific service logs
docker logs mesh-prometheus
docker logs mesh-grafana
docker logs mesh-alertmanager

# Check MESH application logs
tail -f logs/mesh-system.log

# Test health checks manually
curl http://localhost:8000/api/v1/monitoring/health

# Get metrics manually
curl http://localhost:8000/api/v1/monitoring/metrics
```

## Production Considerations

### Security
- Change default Grafana credentials
- Configure authentication for Prometheus/Alertmanager
- Use HTTPS for all monitoring endpoints
- Restrict network access to monitoring ports

### Scalability
- Use Prometheus federation for multiple instances
- Configure metric retention policies
- Set up log rotation for structured logs
- Monitor monitoring system resource usage

### Backup
- Backup Grafana dashboards and configuration
- Export Prometheus data for long-term storage
- Version control monitoring configurations

### High Availability
- Run multiple Prometheus instances
- Use Grafana clustering
- Configure Alertmanager clustering
- Set up monitoring for the monitoring system

## Support

For issues with the monitoring system:

1. Check the troubleshooting section above
2. Review application and monitoring logs
3. Test individual components with the setup script
4. Verify configuration files are valid

The monitoring system is designed to be self-healing and will automatically recover from most transient issues.