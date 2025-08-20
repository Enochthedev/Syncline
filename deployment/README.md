# MESH System Deployment Infrastructure

This directory contains all the deployment infrastructure for the MESH Ingestion System, including Docker containers, Kubernetes manifests, Helm charts, and CI/CD pipelines.

## Directory Structure

```
deployment/
├── README.md                    # This file
├── docker/                      # Docker configurations
│   ├── Dockerfile.api          # API service container
│   ├── Dockerfile.worker       # Background worker container
│   ├── Dockerfile.ai           # AI processing container
│   ├── Dockerfile.connectors   # Platform connectors container
│   └── nginx/                  # Nginx load balancer config
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yaml          # Namespace and resource quotas
│   ├── configmap.yaml          # Configuration management
│   ├── storage.yaml            # Persistent volume claims
│   ├── postgres.yaml           # PostgreSQL database
│   ├── redis.yaml              # Redis cache and streams
│   ├── chromadb.yaml           # Vector database
│   ├── api.yaml                # API service deployment
│   ├── worker.yaml             # Worker service deployment
│   ├── ai-processor.yaml       # AI processing service
│   ├── connectors.yaml         # Platform connectors
│   └── ingress.yaml            # Ingress and network policies
├── helm/                       # Helm charts
│   └── mesh-system/            # Main Helm chart
│       ├── Chart.yaml          # Chart metadata
│       ├── values.yaml         # Default values
│       └── templates/          # Kubernetes templates
├── scripts/                    # Deployment scripts
│   ├── deploy.sh               # Main deployment script
│   └── health-check.sh         # Health check script
└── .github/workflows/          # CI/CD pipelines
    ├── ci.yml                  # Main CI/CD pipeline
    └── security.yml            # Security scanning
```

## Quick Start

### 1. Development Environment (Docker)

```bash
# Clone repository
git clone https://github.com/your-org/mesh-ingestion-system.git
cd mesh-ingestion-system

# Copy environment configuration
cp .env.example .env
# Edit .env with your configuration

# Deploy with Docker Compose
./scripts/deploy.sh development docker

# Check health
./scripts/health-check.sh development docker
```

### 2. Production Environment (Kubernetes with Helm)

```bash
# Ensure kubectl is configured for your cluster
kubectl cluster-info

# Deploy to production
./scripts/deploy.sh production helm

# Verify deployment
./scripts/health-check.sh production helm
```

## Deployment Options

### Docker Compose (Development)

**Pros:**
- Quick setup for development
- Easy to debug and iterate
- Minimal infrastructure requirements

**Cons:**
- Not suitable for production
- Limited scalability
- No high availability

**Usage:**
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale API service
docker-compose up -d --scale api=3

# Stop services
docker-compose down
```

### Kubernetes (Production)

**Pros:**
- Production-ready
- High availability
- Auto-scaling capabilities
- Rolling updates

**Cons:**
- Complex setup
- Requires Kubernetes knowledge
- Higher resource requirements

**Usage:**
```bash
# Deploy infrastructure
kubectl apply -f k8s/

# Check status
kubectl get pods -n mesh-system

# Scale services
kubectl scale deployment mesh-api --replicas=5 -n mesh-system
```

### Helm (Recommended for Production)

**Pros:**
- Templated configurations
- Easy upgrades and rollbacks
- Environment-specific values
- Dependency management

**Cons:**
- Requires Helm knowledge
- Additional complexity

**Usage:**
```bash
# Install
helm install mesh-system ./helm/mesh-system \
  --namespace mesh-system \
  --create-namespace \
  --values production-values.yaml

# Upgrade
helm upgrade mesh-system ./helm/mesh-system \
  --values production-values.yaml

# Rollback
helm rollback mesh-system 1
```

## Configuration Management

### Environment Variables

Create environment-specific configuration files:

```bash
# Development
.env.development

# Staging
.env.staging

# Production
.env.production
```

### Required Configuration

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_URL=redis://host:6379

# Vector Database
CHROMA_HOST=chromadb-host
CHROMA_PORT=8000

# Platform Credentials
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret
DISCORD_BOT_TOKEN=your_discord_bot_token

# AI Services (Optional)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
OLLAMA_BASE_URL=http://ollama:11434

# Security
JWT_SECRET_KEY=your_jwt_secret
ENCRYPTION_KEY=your_encryption_key
```

### Helm Values

Create custom values files for different environments:

```yaml
# production-values.yaml
api:
  replicaCount: 3
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1"

ingress:
  enabled: true
  hosts:
    - host: mesh.yourdomain.com
      paths:
        - path: /
          pathType: Prefix

secrets:
  postgresPassword: "your_secure_password"
  # ... other secrets
```

## Monitoring and Observability

### Metrics Collection

The system includes built-in Prometheus metrics:

```bash
# Deploy monitoring stack
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Or with Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### Key Metrics

- **API Response Time**: 95th percentile < 200ms
- **Error Rate**: < 1%
- **Message Ingestion Rate**: Messages per minute by platform
- **AI Processing Latency**: < 30 seconds
- **Database Query Time**: < 100ms
- **Resource Utilization**: CPU < 70%, Memory < 80%

### Dashboards

Pre-configured Grafana dashboards are available in `monitoring/grafana/dashboards/`:

- System Overview
- API Performance
- AI Processing
- Platform Connectors
- Database Performance

### Alerting

Alert rules are configured in `monitoring/prometheus/rules/`:

- High error rate (> 5%)
- Slow response time (> 500ms)
- Database connection issues
- AI processing failures
- Resource exhaustion

## Security

### Container Security

All Docker images follow security best practices:

- Non-root user execution
- Minimal base images (Alpine Linux)
- Multi-stage builds
- Security scanning with Trivy
- Regular dependency updates

### Kubernetes Security

- Pod Security Standards enforcement
- Network policies for traffic isolation
- RBAC for access control
- Secret management with encryption at rest
- Regular security scanning

### Secret Management

Secrets are managed through:

- Kubernetes Secrets (encrypted at rest)
- External secret managers (AWS Secrets Manager, HashiCorp Vault)
- Regular secret rotation
- No secrets in container images or code

## CI/CD Pipeline

### GitHub Actions Workflow

The CI/CD pipeline includes:

1. **Code Quality Checks**
   - Linting (Black, isort, flake8)
   - Type checking (mypy)
   - Security scanning (bandit, safety)

2. **Testing**
   - Unit tests with pytest
   - Integration tests
   - Coverage reporting

3. **Security Scanning**
   - Dependency vulnerability scanning
   - Container image scanning
   - Infrastructure as Code scanning
   - Secret detection

4. **Build and Deploy**
   - Multi-architecture Docker builds
   - Automated deployment to staging
   - Manual approval for production
   - Rollback capabilities

### Deployment Environments

- **Development**: Automatic deployment on feature branches
- **Staging**: Automatic deployment on develop branch
- **Production**: Manual deployment on release tags

### Pipeline Configuration

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  release:
    types: [ published ]
```

## Scaling and Performance

### Horizontal Scaling

Services can be scaled independently:

```bash
# Scale API service
kubectl scale deployment mesh-api --replicas=5 -n mesh-system

# Scale workers
kubectl scale deployment mesh-worker --replicas=3 -n mesh-system

# Auto-scaling with HPA
kubectl autoscale deployment mesh-api \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n mesh-system
```

### Vertical Scaling

Resource limits can be adjusted:

```bash
# Update resource limits
kubectl patch deployment mesh-api -n mesh-system -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "api",
          "resources": {
            "limits": {"memory": "4Gi", "cpu": "2"},
            "requests": {"memory": "2Gi", "cpu": "1"}
          }
        }]
      }
    }
  }
}'
```

### Performance Optimization

- **Database**: Connection pooling, query optimization, indexing
- **Caching**: Redis for frequently accessed data
- **AI Processing**: Batch processing, model optimization
- **Load Balancing**: Nginx with multiple API instances

## Backup and Recovery

### Automated Backups

Daily backups are configured for:

- PostgreSQL database (pg_dump)
- ChromaDB vector data
- Configuration and secrets
- Application logs

### Disaster Recovery

Recovery procedures are documented in `docs/OPERATIONAL_RUNBOOKS.md`:

- RTO (Recovery Time Objective): 15 minutes
- RPO (Recovery Point Objective): 5 minutes
- Automated failover for databases
- Cross-region replication for critical data

## Troubleshooting

### Common Issues

1. **Database Connection Failures**
   ```bash
   # Check database status
   kubectl exec -it postgres-0 -n mesh-system -- pg_isready
   
   # Check connection pool
   kubectl logs deployment/mesh-api -n mesh-system | grep "database"
   ```

2. **AI Processing Delays**
   ```bash
   # Check AI processor logs
   kubectl logs deployment/mesh-ai-processor -n mesh-system
   
   # Check Ollama status
   curl http://ollama-service:11434/api/tags
   ```

3. **Platform Connector Issues**
   ```bash
   # Check connector health
   kubectl logs deployment/mesh-connectors -n mesh-system
   
   # Refresh OAuth tokens
   kubectl exec -it deployment/mesh-connectors -n mesh-system -- \
     python -c "from integrations.token_manager import TokenManager; TokenManager().refresh_all_tokens()"
   ```

### Health Checks

Use the provided health check script:

```bash
# Comprehensive health check
./scripts/health-check.sh production helm

# Quick API health check
curl -f https://mesh.yourdomain.com/api/v1/health
```

### Log Analysis

Centralized logging with structured logs:

```bash
# View application logs
kubectl logs -f deployment/mesh-api -n mesh-system

# Search for errors
kubectl logs deployment/mesh-api -n mesh-system | grep ERROR

# Export logs for analysis
kubectl logs deployment/mesh-api -n mesh-system --since=1h > api-logs.txt
```

## Support and Maintenance

### Regular Maintenance

- **Weekly**: Review metrics, check logs, verify backups
- **Monthly**: Update dependencies, security patches, performance review
- **Quarterly**: Security audit, disaster recovery testing, capacity planning

### Getting Help

1. Check the troubleshooting section
2. Review system logs and metrics
3. Consult operational runbooks
4. Contact support team with detailed error information
5. Use GitHub issues for bug reports and feature requests

### Documentation

- [Deployment Guide](../docs/DEPLOYMENT_GUIDE.md)
- [Operational Runbooks](../docs/OPERATIONAL_RUNBOOKS.md)
- [API Reference](../docs/API_REFERENCE.md)
- [System Overview](../docs/SYSTEM_OVERVIEW.md)

## Contributing

When contributing to the deployment infrastructure:

1. Test changes in development environment first
2. Update documentation for any configuration changes
3. Follow security best practices
4. Add appropriate monitoring and alerting
5. Update CI/CD pipeline if needed

## License

This deployment infrastructure is part of the MESH Ingestion System and is licensed under the same terms as the main project.