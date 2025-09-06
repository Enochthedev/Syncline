# MESH System Deployment Guide

This guide covers deploying the MESH Ingestion System in various environments using Docker, Kubernetes, and Helm.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Helm Deployment](#helm-deployment)
- [Configuration](#configuration)
- [Monitoring Setup](#monitoring-setup)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 100GB SSD
- Network: 1Gbps

**Recommended for Production:**
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 500GB+ NVMe SSD
- Network: 10Gbps
- GPU: Optional for AI processing acceleration

### Software Dependencies

- Docker 24.0+
- Docker Compose 2.20+
- Kubernetes 1.28+
- Helm 3.12+
- kubectl 1.28+

### External Services

- PostgreSQL 16+ (or managed database)
- Redis 7+ (or managed cache)
- ChromaDB (vector database)
- Optional: Ollama for local AI processing

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/mesh-ingestion-system.git
cd mesh-ingestion-system
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Required Environment Variables

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
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# AI Services (Optional)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
OLLAMA_BASE_URL=http://ollama:11434

# Security
JWT_SECRET_KEY=your_jwt_secret
ENCRYPTION_KEY=your_encryption_key
```

## Docker Deployment

### Development Environment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Environment

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Scale API service
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Update services
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Service Health Checks

```bash
# Check service status
docker-compose ps

# API health check
curl http://localhost:8000/api/v1/health

# Database connection test
docker-compose exec postgres pg_isready

# Redis connection test
docker-compose exec redis redis-cli ping
```

## Kubernetes Deployment

### 1. Cluster Setup

```bash
# Verify cluster access
kubectl cluster-info

# Create namespace
kubectl apply -f k8s/namespace.yaml
```

### 2. Storage Classes

```bash
# Create storage classes (example for AWS EKS)
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-storage
provisioner: efs.csi.aws.com
volumeBindingMode: Immediate
allowVolumeExpansion: true
EOF
```

### 3. Deploy Infrastructure

```bash
# Deploy in order
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/storage.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/chromadb.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgres -n mesh-system --timeout=300s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=redis -n mesh-system --timeout=300s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=chromadb -n mesh-system --timeout=300s
```

### 4. Deploy Application Services

```bash
# Deploy application components
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/worker.yaml
kubectl apply -f k8s/ai-processor.yaml
kubectl apply -f k8s/connectors.yaml

# Deploy ingress
kubectl apply -f k8s/ingress.yaml

# Check deployment status
kubectl get pods -n mesh-system
kubectl get services -n mesh-system
kubectl get ingress -n mesh-system
```

### 5. Database Migration

```bash
# Run migrations
kubectl exec -it deployment/mesh-api -n mesh-system -- alembic upgrade head
```

## Helm Deployment

### 1. Add Helm Repositories

```bash
# Add required repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 2. Install Dependencies

```bash
# Install PostgreSQL
helm install postgres bitnami/postgresql \
  --namespace mesh-system \
  --create-namespace \
  --set auth.postgresPassword=secure_password \
  --set auth.username=mesh_user \
  --set auth.password=secure_password \
  --set auth.database=mesh_production

# Install Redis
helm install redis bitnami/redis \
  --namespace mesh-system \
  --set auth.enabled=false \
  --set master.persistence.size=10Gi
```

### 3. Deploy MESH System

```bash
# Install with default values
helm install mesh-system ./helm/mesh-system \
  --namespace mesh-system \
  --create-namespace

# Install with custom values
helm install mesh-system ./helm/mesh-system \
  --namespace mesh-system \
  --create-namespace \
  --values custom-values.yaml

# Upgrade deployment
helm upgrade mesh-system ./helm/mesh-system \
  --namespace mesh-system \
  --values custom-values.yaml
```

### 4. Custom Values Example

```yaml
# custom-values.yaml
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
  gmail:
    clientId: "your_gmail_client_id"
    clientSecret: "your_gmail_client_secret"
```

## Configuration

### Platform Integration Setup

#### Gmail Integration

1. Create Google Cloud Project
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Configure redirect URIs
5. Set environment variables

```bash
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret
```

#### Slack Integration

1. Create Slack App
2. Configure OAuth scopes
3. Enable Events API
4. Set webhook URLs
5. Install app to workspace

```bash
SLACK_CLIENT_ID=your_client_id
SLACK_CLIENT_SECRET=your_client_secret
```

#### Discord Integration

1. Create Discord Application
2. Create Bot user
3. Configure permissions
4. Get bot token

```bash
DISCORD_BOT_TOKEN=your_bot_token
```

### AI Service Configuration

#### Local AI with Ollama

```bash
# Pull required models
docker exec ollama ollama pull tinyllama:latest
docker exec ollama ollama pull nomic-embed-text:latest

# Verify models
docker exec ollama ollama list
```

#### Cloud AI Services

```bash
# OpenAI configuration
OPENAI_API_KEY=your_openai_key

# Anthropic configuration
ANTHROPIC_API_KEY=your_anthropic_key
```

## Monitoring Setup

### 1. Deploy Monitoring Stack

```bash
# Deploy Prometheus and Grafana
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Or use Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### 2. Configure Dashboards

```bash
# Import Grafana dashboards
kubectl apply -f monitoring/grafana/dashboards/
```

### 3. Set Up Alerts

```bash
# Configure Alertmanager
kubectl apply -f monitoring/alertmanager/
```

## Troubleshooting

### Common Issues

#### Database Connection Issues

```bash
# Check database connectivity
kubectl exec -it deployment/mesh-api -n mesh-system -- python -c "
from db.session import get_db_session
import asyncio
async def test():
    async with get_db_session() as session:
        result = await session.execute('SELECT 1')
        print('Database connected:', result.scalar())
asyncio.run(test())
"
```

#### Redis Connection Issues

```bash
# Test Redis connectivity
kubectl exec -it deployment/mesh-api -n mesh-system -- python -c "
import redis
r = redis.from_url('redis://redis-service:6379')
print('Redis ping:', r.ping())
"
```

#### AI Service Issues

```bash
# Check Ollama status
curl http://ollama-service:11434/api/tags

# Test ChromaDB
curl http://chromadb-service:8000/api/v1/heartbeat
```

### Log Analysis

```bash
# View application logs
kubectl logs -f deployment/mesh-api -n mesh-system

# View all pod logs
kubectl logs -f -l app.kubernetes.io/name=mesh-system -n mesh-system

# Export logs for analysis
kubectl logs deployment/mesh-api -n mesh-system --since=1h > api-logs.txt
```

### Performance Tuning

#### Database Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM messages WHERE created_at > NOW() - INTERVAL '1 day';

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE tablename = 'messages';
```

#### Resource Scaling

```bash
# Scale API pods
kubectl scale deployment mesh-api --replicas=5 -n mesh-system

# Update resource limits
kubectl patch deployment mesh-api -n mesh-system -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "api",
          "resources": {
            "limits": {"memory": "2Gi", "cpu": "1"},
            "requests": {"memory": "1Gi", "cpu": "500m"}
          }
        }]
      }
    }
  }
}'
```

### Health Checks

```bash
# System health overview
curl -s http://mesh.yourdomain.com/api/v1/health | jq

# Component health checks
kubectl get pods -n mesh-system
kubectl describe pod <pod-name> -n mesh-system

# Service endpoints
kubectl get endpoints -n mesh-system
```

### Backup and Recovery

#### Database Backup

```bash
# Create backup
kubectl exec postgres-0 -n mesh-system -- pg_dump -U mesh_user mesh_production > backup.sql

# Restore backup
kubectl exec -i postgres-0 -n mesh-system -- psql -U mesh_user mesh_production < backup.sql
```

#### Configuration Backup

```bash
# Backup Kubernetes resources
kubectl get all,configmap,secret,pvc -n mesh-system -o yaml > mesh-system-backup.yaml

# Backup Helm values
helm get values mesh-system -n mesh-system > helm-values-backup.yaml
```

## Security Considerations

### Network Security

- Use network policies to restrict pod-to-pod communication
- Enable TLS for all external communications
- Use service mesh for internal encryption (optional)

### Secret Management

- Use Kubernetes secrets or external secret managers
- Rotate secrets regularly
- Never commit secrets to version control

### Access Control

- Implement RBAC for Kubernetes access
- Use service accounts with minimal permissions
- Enable audit logging

### Compliance

- Regular security scans
- Vulnerability assessments
- Compliance reporting (SOC 2, GDPR, etc.)

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly:**
   - Review system metrics and alerts
   - Check log aggregation for errors
   - Verify backup integrity

2. **Monthly:**
   - Update dependencies and security patches
   - Review resource utilization and scaling
   - Performance optimization review

3. **Quarterly:**
   - Security audit and penetration testing
   - Disaster recovery testing
   - Capacity planning review

### Getting Help

- Check the troubleshooting section
- Review system logs and metrics
- Contact support team with detailed error information
- Use GitHub issues for bug reports and feature requests

For additional support, please refer to the [operational runbooks](OPERATIONAL_RUNBOOKS.md) and [monitoring guide](MONITORING_GUIDE.md).