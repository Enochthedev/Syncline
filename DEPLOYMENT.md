# R.E.M.I Backend - Production Deployment Guide

This guide covers deploying the R.E.M.I backend to production environments.

## Prerequisites

- Kubernetes cluster (1.24+)
- PostgreSQL 14+ database
- Redis 6+ instance
- Docker registry access
- kubectl configured with cluster access
- Domain name and TLS certificates

## Quick Start

```bash
# 1. Build and push Docker image
docker build -t your-registry/remi-backend:v1.0.0 apps/backend/
docker push your-registry/remi-backend:v1.0.0

# 2. Create namespace
kubectl create namespace remi

# 3. Create secrets
kubectl create secret generic remi-secrets \
  --from-literal=database-url="postgresql+asyncpg://user:pass@host:5432/remi" \
  --from-literal=redis-url="redis://host:6379/0" \
  --from-literal=jwt-secret-key="$(openssl rand -hex 32)" \
  -n remi

# 4. Deploy
kubectl apply -f apps/backend/k8s/ -n remi

# 5. Verify
kubectl get pods -n remi
kubectl logs -f deployment/remi-backend -n remi
```

## Detailed Configuration

### 1. Environment Variables

Required environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@localhost:5432/remi` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | Generate with `openssl rand -hex 32` |
| `ENVIRONMENT` | Environment name | `production`, `staging`, `development` |
| `LOG_LEVEL` | Logging level | `INFO`, `DEBUG`, `WARNING`, `ERROR` |

Optional environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `OLLAMA_BASE_URL` | Ollama API URL | `http://localhost:11434` |
| `CHROMADB_HOST` | ChromaDB host | `localhost` |
| `CHROMADB_PORT` | ChromaDB port | `8000` |

### 2. Database Setup

```bash
# Run migrations
kubectl exec -it deployment/remi-backend -n remi -- \
  alembic upgrade head

# Create admin user (if needed)
kubectl exec -it deployment/remi-backend -n remi -- \
  python -m scripts.create_admin_user
```

### 3. TLS/SSL Configuration

Create TLS secret:

```bash
kubectl create secret tls remi-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n remi
```

### 4. Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: remi-backend-ingress
  namespace: remi
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.remi.example.com
    secretName: remi-tls
  rules:
  - host: api.remi.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: remi-backend
            port:
              number: 80
```

## Monitoring and Observability

### Prometheus Metrics

Metrics are exposed at `/metrics` endpoint:

```yaml
apiVersion: v1
kind: ServiceMonitor
metadata:
  name: remi-backend
  namespace: remi
spec:
  selector:
    matchLabels:
      app: remi-backend
  endpoints:
  - port: metrics
    interval: 30s
```

### Logging

Logs are output to stdout in JSON format. Configure log aggregation:

```yaml
# Example Fluentd configuration
<match kubernetes.var.log.containers.remi-backend-**.log>
  @type elasticsearch
  host elasticsearch.logging.svc.cluster.local
  port 9200
  logstash_format true
  logstash_prefix remi-backend
</match>
```

### Alerts

Deploy Prometheus alert rules:

```bash
kubectl create configmap prometheus-alerts \
  --from-file=apps/backend/config/prometheus/alerts.yml \
  -n monitoring
```

## Scaling

### Horizontal Pod Autoscaling

HPA is configured to scale based on CPU and memory:

```yaml
# Already included in k8s/deployment.yml
minReplicas: 3
maxReplicas: 10
```

### Database Scaling

- Use PostgreSQL read replicas for read-heavy workloads
- Configure connection pooling (default: 50 connections)
- Monitor with `db_connections_active` metric

### Redis Scaling

- Use Redis Cluster for high availability
- Configure Redis Sentinel for automatic failover

## Security

### Secrets Management

Use external secrets operator:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: remi-secrets
  namespace: remi
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: remi-secrets
  data:
  - secretKey: database-url
    remoteRef:
      key: remi/database-url
  - secretKey: jwt-secret-key
    remoteRef:
      key: remi/jwt-secret-key
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: remi-backend-netpol
  namespace: remi
spec:
  podSelector:
    matchLabels:
      app: remi-backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 5432  # PostgreSQL
    - protocol: TCP
      port: 6379  # Redis
```

## Backup and Disaster Recovery

### Database Backups

```bash
# Daily backup cron job
apiVersion: batch/v1
kind: CronJob
metadata:
  name: remi-db-backup
  namespace: remi
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:14
            command:
            - /bin/sh
            - -c
            - pg_dump $DATABASE_URL | gzip > /backups/remi-$(date +%Y%m%d).sql.gz
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: remi-secrets
                  key: database-url
            volumeMounts:
            - name: backup-storage
              mountPath: /backups
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

## Troubleshooting

### Common Issues

**Pods not starting:**
```bash
kubectl describe pod <pod-name> -n remi
kubectl logs <pod-name> -n remi
```

**Database connection issues:**
```bash
# Test database connection
kubectl exec -it deployment/remi-backend -n remi -- \
  python -c "from db.session import test_connection; test_connection()"
```

**High memory usage:**
```bash
# Check metrics
kubectl top pods -n remi
# Adjust resource limits in deployment.yml
```

## Performance Tuning

### Database

```sql
-- Create indexes for common queries
CREATE INDEX CONCURRENTLY idx_messages_user_timestamp
ON messages(user_id, timestamp DESC);

-- Analyze tables
ANALYZE messages;
ANALYZE contacts;
```

### Redis

```ini
# redis.conf optimizations
maxmemory 2gb
maxmemory-policy allkeys-lru
tcp-backlog 511
timeout 300
```

### Application

```python
# config.py
DATABASE_POOL_SIZE = 50
DATABASE_MAX_OVERFLOW = 10
REDIS_POOL_SIZE = 20
```

## Maintenance

### Rolling Updates

```bash
# Update image
kubectl set image deployment/remi-backend \
  backend=your-registry/remi-backend:v1.1.0 \
  -n remi

# Watch rollout
kubectl rollout status deployment/remi-backend -n remi

# Rollback if needed
kubectl rollout undo deployment/remi-backend -n remi
```

### Data Retention

Configure retention policies:

```python
# Automatic cleanup runs daily
MESSAGES_RETENTION_DAYS = 365
RAW_MESSAGES_RETENTION_DAYS = 90
AUDIT_LOGS_RETENTION_DAYS = 730
```

## Support and Monitoring

### Health Checks

- **Liveness:** `GET /api/v1/health`
- **Readiness:** `GET /api/v1/health`
- **Metrics:** `GET /metrics`
- **Stats:** `GET /api/v1/stats`

### Dashboard Access

- Grafana: https://grafana.example.com
- Prometheus: https://prometheus.example.com
- Logs: https://kibana.example.com

## Additional Resources

- [API Documentation](https://api.remi.example.com/docs)
- [Architecture Overview](docs/SYSTEM_OVERVIEW.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [API Reference](docs/API_REFERENCE.md)
