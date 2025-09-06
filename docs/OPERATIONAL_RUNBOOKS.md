# MESH System Operational Runbooks

This document provides step-by-step procedures for common operational tasks and incident response for the MESH Ingestion System.

## Table of Contents

- [System Overview](#system-overview)
- [Incident Response](#incident-response)
- [Maintenance Procedures](#maintenance-procedures)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Backup and Recovery](#backup-and-recovery)
- [Performance Optimization](#performance-optimization)
- [Security Operations](#security-operations)

## System Overview

### Architecture Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   API Gateway   │    │   Web UI        │
│   (Nginx)       │────│   (FastAPI)     │────│   (Optional)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Connectors    │    │   AI Processor  │    │   Workers       │
│   (Platform     │    │   (ML/NLP)      │    │   (Background)  │
│   Integrations) │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │   Event Bus     │
                    │   (Redis)       │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Databases     │
                    │   PostgreSQL    │
                    │   ChromaDB      │
                    └─────────────────┘
```

### Service Dependencies

- **API Service**: Depends on PostgreSQL, Redis, ChromaDB
- **Workers**: Depends on PostgreSQL, Redis, ChromaDB
- **AI Processor**: Depends on PostgreSQL, Redis, ChromaDB, Ollama (optional)
- **Connectors**: Depends on PostgreSQL, Redis, External APIs

## Incident Response

### Severity Levels

- **P0 (Critical)**: Complete system outage, data loss
- **P1 (High)**: Major functionality impaired, significant user impact
- **P2 (Medium)**: Minor functionality impaired, limited user impact
- **P3 (Low)**: Cosmetic issues, no user impact

### P0 - Critical Incident Response

#### System Completely Down

**Symptoms:**
- All health checks failing
- No API responses
- Database connectivity issues

**Immediate Actions:**

1. **Assess Impact**
   ```bash
   # Check overall system status
   kubectl get pods -n mesh-system
   kubectl get services -n mesh-system
   curl -f https://mesh.yourdomain.com/api/v1/health
   ```

2. **Check Infrastructure**
   ```bash
   # Database status
   kubectl exec -it postgres-0 -n mesh-system -- pg_isready
   
   # Redis status
   kubectl exec -it redis-0 -n mesh-system -- redis-cli ping
   
   # ChromaDB status
   curl -f http://chromadb-service:8000/api/v1/heartbeat
   ```

3. **Restart Services**
   ```bash
   # Restart API pods
   kubectl rollout restart deployment/mesh-api -n mesh-system
   
   # Check rollout status
   kubectl rollout status deployment/mesh-api -n mesh-system
   ```

4. **Escalation**
   - Notify on-call engineer
   - Update status page
   - Prepare communication for stakeholders

#### Database Failure

**Symptoms:**
- Database connection errors
- Data inconsistency
- Transaction failures

**Recovery Steps:**

1. **Assess Database Health**
   ```bash
   # Check PostgreSQL status
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "SELECT version();"
   
   # Check replication status (if applicable)
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "SELECT * FROM pg_stat_replication;"
   ```

2. **Check Disk Space**
   ```bash
   kubectl exec -it postgres-0 -n mesh-system -- df -h
   ```

3. **Review Logs**
   ```bash
   kubectl logs postgres-0 -n mesh-system --tail=100
   ```

4. **Recovery Actions**
   ```bash
   # If disk space issue, clean up logs
   kubectl exec -it postgres-0 -n mesh-system -- find /var/lib/postgresql/data/log -name "*.log" -mtime +7 -delete
   
   # If corruption, restore from backup
   kubectl exec -it postgres-0 -n mesh-system -- pg_restore -U mesh_user -d mesh_production /backup/latest.dump
   ```

### P1 - High Priority Incidents

#### Platform Connector Failures

**Symptoms:**
- Specific platform not ingesting messages
- Authentication errors
- Rate limiting issues

**Diagnosis:**

1. **Check Connector Status**
   ```bash
   # View connector logs
   kubectl logs deployment/mesh-connectors -n mesh-system --tail=100
   
   # Check connector health
   curl -s http://mesh-connectors-service:8003/health | jq
   ```

2. **Platform-Specific Checks**
   ```bash
   # Gmail connector
   kubectl exec -it deployment/mesh-connectors -n mesh-system -- python -c "
   from integrations.gmail_connector import GmailConnector
   connector = GmailConnector()
   print(connector.get_health_status())
   "
   
   # Slack connector
   kubectl exec -it deployment/mesh-connectors -n mesh-system -- python -c "
   from integrations.slack_connector import SlackConnector
   connector = SlackConnector()
   print(connector.get_health_status())
   "
   ```

3. **Token Refresh**
   ```bash
   # Refresh OAuth tokens
   kubectl exec -it deployment/mesh-connectors -n mesh-system -- python -c "
   from integrations.token_manager import TokenManager
   manager = TokenManager()
   manager.refresh_all_tokens()
   "
   ```

#### AI Processing Failures

**Symptoms:**
- Messages not being processed by AI
- Embedding generation failures
- Summary generation errors

**Recovery Steps:**

1. **Check AI Service Health**
   ```bash
   # AI processor status
   kubectl logs deployment/mesh-ai-processor -n mesh-system --tail=50
   
   # Ollama status (if using local AI)
   curl -f http://ollama-service:11434/api/tags
   ```

2. **Restart AI Services**
   ```bash
   kubectl rollout restart deployment/mesh-ai-processor -n mesh-system
   ```

3. **Reprocess Failed Messages**
   ```bash
   kubectl exec -it deployment/mesh-ai-processor -n mesh-system -- python -c "
   from services.ai.engine import AIProcessingEngine
   engine = AIProcessingEngine()
   engine.reprocess_failed_messages()
   "
   ```

### P2 - Medium Priority Incidents

#### Performance Degradation

**Symptoms:**
- Slow API responses
- High resource utilization
- Queue backlog

**Investigation:**

1. **Check Resource Usage**
   ```bash
   # CPU and memory usage
   kubectl top pods -n mesh-system
   kubectl top nodes
   
   # Detailed resource metrics
   kubectl describe pod <pod-name> -n mesh-system
   ```

2. **Database Performance**
   ```bash
   # Check slow queries
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "
   SELECT query, mean_exec_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_exec_time DESC 
   LIMIT 10;
   "
   
   # Check active connections
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "
   SELECT count(*) as active_connections 
   FROM pg_stat_activity 
   WHERE state = 'active';
   "
   ```

3. **Scale Resources**
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

## Maintenance Procedures

### Scheduled Maintenance

#### Database Maintenance

**Weekly Tasks:**

1. **Vacuum and Analyze**
   ```bash
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "VACUUM ANALYZE;"
   ```

2. **Update Statistics**
   ```bash
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "
   SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del 
   FROM pg_stat_user_tables 
   ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC;
   "
   ```

3. **Check Index Usage**
   ```bash
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "
   SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch 
   FROM pg_stat_user_indexes 
   WHERE idx_tup_read = 0 AND idx_tup_fetch = 0;
   "
   ```

#### Application Updates

**Deployment Process:**

1. **Pre-deployment Checks**
   ```bash
   # Backup database
   kubectl exec postgres-0 -n mesh-system -- pg_dump -U mesh_user mesh_production > backup-$(date +%Y%m%d).sql
   
   # Check current system health
   curl -s https://mesh.yourdomain.com/api/v1/health | jq
   ```

2. **Rolling Update**
   ```bash
   # Update API service
   kubectl set image deployment/mesh-api api=mesh-system/api:v1.1.0 -n mesh-system
   
   # Monitor rollout
   kubectl rollout status deployment/mesh-api -n mesh-system
   ```

3. **Post-deployment Verification**
   ```bash
   # Health check
   curl -s https://mesh.yourdomain.com/api/v1/health | jq
   
   # Smoke tests
   curl -s https://mesh.yourdomain.com/api/v1/messages?limit=1 | jq
   ```

4. **Rollback if Needed**
   ```bash
   kubectl rollout undo deployment/mesh-api -n mesh-system
   ```

### Configuration Updates

#### Environment Variables

1. **Update ConfigMap**
   ```bash
   kubectl patch configmap mesh-config -n mesh-system -p '
   {
     "data": {
       "LOG_LEVEL": "DEBUG"
     }
   }'
   ```

2. **Restart Affected Pods**
   ```bash
   kubectl rollout restart deployment/mesh-api -n mesh-system
   ```

#### Secrets Management

1. **Update Secrets**
   ```bash
   kubectl patch secret mesh-secrets -n mesh-system -p '
   {
     "stringData": {
       "GMAIL_CLIENT_SECRET": "new_secret_value"
     }
   }'
   ```

2. **Verify Secret Update**
   ```bash
   kubectl get secret mesh-secrets -n mesh-system -o jsonpath='{.data.GMAIL_CLIENT_SECRET}' | base64 -d
   ```

## Monitoring and Alerting

### Key Metrics to Monitor

#### System Health Metrics

1. **API Response Time**
   - Target: < 200ms for 95th percentile
   - Alert: > 500ms for 95th percentile

2. **Error Rate**
   - Target: < 1% error rate
   - Alert: > 5% error rate

3. **Database Performance**
   - Target: < 100ms query time
   - Alert: > 500ms query time

#### Business Metrics

1. **Message Ingestion Rate**
   - Monitor: Messages per minute by platform
   - Alert: 50% drop in ingestion rate

2. **AI Processing Latency**
   - Target: < 30 seconds for message processing
   - Alert: > 2 minutes processing time

### Alert Response Procedures

#### High Error Rate Alert

1. **Immediate Investigation**
   ```bash
   # Check error logs
   kubectl logs deployment/mesh-api -n mesh-system --since=10m | grep ERROR
   
   # Check specific error patterns
   kubectl logs deployment/mesh-api -n mesh-system --since=10m | grep -E "(500|502|503|504)"
   ```

2. **Identify Root Cause**
   ```bash
   # Database connectivity
   kubectl exec -it deployment/mesh-api -n mesh-system -- python -c "
   from db.session import get_db_session
   import asyncio
   async def test():
       try:
           async with get_db_session() as session:
               await session.execute('SELECT 1')
               print('DB: OK')
       except Exception as e:
           print(f'DB Error: {e}')
   asyncio.run(test())
   "
   ```

3. **Mitigation Actions**
   ```bash
   # Scale up if resource constrained
   kubectl scale deployment mesh-api --replicas=5 -n mesh-system
   
   # Restart if memory leaks suspected
   kubectl rollout restart deployment/mesh-api -n mesh-system
   ```

#### Database Connection Alert

1. **Check Connection Pool**
   ```bash
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "
   SELECT count(*) as total_connections, 
          count(*) FILTER (WHERE state = 'active') as active_connections,
          count(*) FILTER (WHERE state = 'idle') as idle_connections
   FROM pg_stat_activity;
   "
   ```

2. **Kill Long-Running Queries**
   ```bash
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'active' 
   AND query_start < NOW() - INTERVAL '5 minutes'
   AND query NOT LIKE '%pg_stat_activity%';
   "
   ```

## Backup and Recovery

### Automated Backup Procedures

#### Database Backup

1. **Daily Backup Script**
   ```bash
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)
   BACKUP_FILE="mesh_backup_${DATE}.sql"
   
   # Create backup
   kubectl exec postgres-0 -n mesh-system -- pg_dump -U mesh_user mesh_production > ${BACKUP_FILE}
   
   # Compress and upload to S3
   gzip ${BACKUP_FILE}
   aws s3 cp ${BACKUP_FILE}.gz s3://mesh-backups/database/
   
   # Clean up local file
   rm ${BACKUP_FILE}.gz
   
   # Retain only last 30 days
   aws s3 ls s3://mesh-backups/database/ | awk '{print $4}' | sort | head -n -30 | xargs -I {} aws s3 rm s3://mesh-backups/database/{}
   ```

2. **Vector Database Backup**
   ```bash
   # Backup ChromaDB
   kubectl exec chromadb-0 -n mesh-system -- tar -czf /tmp/chroma_backup_$(date +%Y%m%d).tar.gz /chroma/chroma
   kubectl cp mesh-system/chromadb-0:/tmp/chroma_backup_$(date +%Y%m%d).tar.gz ./chroma_backup_$(date +%Y%m%d).tar.gz
   ```

### Disaster Recovery

#### Complete System Recovery

1. **Infrastructure Recovery**
   ```bash
   # Restore from Helm backup
   helm install mesh-system ./helm/mesh-system \
     --namespace mesh-system \
     --create-namespace \
     --values backup-values.yaml
   ```

2. **Database Recovery**
   ```bash
   # Download latest backup
   aws s3 cp s3://mesh-backups/database/latest.sql.gz ./
   gunzip latest.sql.gz
   
   # Restore database
   kubectl exec -i postgres-0 -n mesh-system -- psql -U mesh_user mesh_production < latest.sql
   ```

3. **Vector Database Recovery**
   ```bash
   # Restore ChromaDB
   kubectl cp ./chroma_backup_latest.tar.gz mesh-system/chromadb-0:/tmp/
   kubectl exec chromadb-0 -n mesh-system -- tar -xzf /tmp/chroma_backup_latest.tar.gz -C /
   kubectl rollout restart deployment/chromadb -n mesh-system
   ```

#### Point-in-Time Recovery

1. **Identify Recovery Point**
   ```bash
   # List available backups
   aws s3 ls s3://mesh-backups/database/ | grep $(date +%Y%m%d)
   ```

2. **Restore to Specific Time**
   ```bash
   # Download specific backup
   aws s3 cp s3://mesh-backups/database/mesh_backup_20240116_143000.sql.gz ./
   
   # Create new database for recovery
   kubectl exec -it postgres-0 -n mesh-system -- createdb -U mesh_user mesh_recovery
   
   # Restore to recovery database
   gunzip mesh_backup_20240116_143000.sql.gz
   kubectl exec -i postgres-0 -n mesh-system -- psql -U mesh_user mesh_recovery < mesh_backup_20240116_143000.sql
   ```

## Performance Optimization

### Database Optimization

#### Query Performance

1. **Identify Slow Queries**
   ```sql
   -- Enable query statistics
   ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
   SELECT pg_reload_conf();
   
   -- Find slow queries
   SELECT query, mean_exec_time, calls, total_exec_time
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```

2. **Index Optimization**
   ```sql
   -- Find missing indexes
   SELECT schemaname, tablename, attname, n_distinct, correlation
   FROM pg_stats
   WHERE schemaname = 'public'
   AND n_distinct > 100
   ORDER BY n_distinct DESC;
   
   -- Create composite indexes for common queries
   CREATE INDEX CONCURRENTLY idx_messages_platform_timestamp 
   ON messages(platform, created_at DESC);
   ```

#### Connection Pool Tuning

1. **Optimize PostgreSQL Settings**
   ```sql
   -- Update postgresql.conf
   ALTER SYSTEM SET max_connections = 200;
   ALTER SYSTEM SET shared_buffers = '256MB';
   ALTER SYSTEM SET effective_cache_size = '1GB';
   ALTER SYSTEM SET work_mem = '4MB';
   SELECT pg_reload_conf();
   ```

2. **Application Connection Pool**
   ```python
   # Update database configuration
   DATABASE_POOL_SIZE = 20
   DATABASE_MAX_OVERFLOW = 30
   DATABASE_POOL_TIMEOUT = 30
   ```

### Application Performance

#### Memory Optimization

1. **Monitor Memory Usage**
   ```bash
   # Check memory usage by pod
   kubectl top pods -n mesh-system --sort-by=memory
   
   # Detailed memory analysis
   kubectl exec -it deployment/mesh-api -n mesh-system -- python -c "
   import psutil
   process = psutil.Process()
   print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
   print(f'CPU: {process.cpu_percent()}%')
   "
   ```

2. **Optimize Batch Processing**
   ```python
   # Adjust batch sizes based on memory usage
   MAX_MESSAGE_BATCH_SIZE = 50  # Reduce if memory constrained
   AI_PROCESSING_BATCH_SIZE = 10
   VECTOR_BATCH_SIZE = 100
   ```

#### CPU Optimization

1. **Profile CPU Usage**
   ```bash
   # Use py-spy for Python profiling
   kubectl exec -it deployment/mesh-api -n mesh-system -- py-spy top --pid 1 --duration 30
   ```

2. **Optimize AI Processing**
   ```bash
   # Use multiple workers for AI processing
   kubectl patch deployment mesh-ai-processor -n mesh-system -p '
   {
     "spec": {
       "template": {
         "spec": {
           "containers": [{
             "name": "ai-processor",
             "env": [
               {"name": "AI_WORKER_THREADS", "value": "4"},
               {"name": "BATCH_SIZE", "value": "10"}
             ]
           }]
         }
       }
     }
   }'
   ```

## Security Operations

### Security Monitoring

#### Log Analysis

1. **Security Event Detection**
   ```bash
   # Check for suspicious API access
   kubectl logs deployment/mesh-api -n mesh-system --since=1h | grep -E "(401|403|429)"
   
   # Monitor failed authentication attempts
   kubectl logs deployment/mesh-api -n mesh-system --since=1h | grep "authentication failed"
   ```

2. **Audit Log Review**
   ```bash
   # Review database audit logs
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "
   SELECT * FROM audit_logs 
   WHERE created_at > NOW() - INTERVAL '1 hour'
   AND action IN ('DELETE', 'UPDATE')
   ORDER BY created_at DESC;
   "
   ```

#### Vulnerability Management

1. **Container Security Scanning**
   ```bash
   # Scan running containers
   trivy image mesh-system/api:latest
   trivy image mesh-system/worker:latest
   trivy image mesh-system/ai-processor:latest
   ```

2. **Dependency Scanning**
   ```bash
   # Check Python dependencies
   safety check --json
   pip-audit --format=json
   ```

### Incident Response

#### Security Breach Response

1. **Immediate Containment**
   ```bash
   # Isolate affected pods
   kubectl label pod <compromised-pod> security.breach=true -n mesh-system
   
   # Apply network policy to block traffic
   kubectl apply -f - <<EOF
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: isolate-compromised-pod
     namespace: mesh-system
   spec:
     podSelector:
       matchLabels:
         security.breach: "true"
     policyTypes:
     - Ingress
     - Egress
   EOF
   ```

2. **Evidence Collection**
   ```bash
   # Collect logs
   kubectl logs <compromised-pod> -n mesh-system > incident-logs.txt
   
   # Export pod configuration
   kubectl get pod <compromised-pod> -n mesh-system -o yaml > pod-config.yaml
   
   # Memory dump (if possible)
   kubectl exec <compromised-pod> -n mesh-system -- gcore 1
   ```

3. **Recovery Actions**
   ```bash
   # Rotate all secrets
   kubectl delete secret mesh-secrets -n mesh-system
   kubectl apply -f new-secrets.yaml
   
   # Force pod recreation
   kubectl delete pod <compromised-pod> -n mesh-system
   
   # Update all tokens
   kubectl exec -it deployment/mesh-connectors -n mesh-system -- python -c "
   from integrations.token_manager import TokenManager
   manager = TokenManager()
   manager.rotate_all_tokens()
   "
   ```

### Compliance Operations

#### Data Protection

1. **PII Audit**
   ```bash
   # Check PII redaction effectiveness
   kubectl exec -it deployment/mesh-api -n mesh-system -- python -c "
   from services.ai.pii_redaction import PIIRedactor
   redactor = PIIRedactor()
   test_text = 'Contact John Doe at john.doe@example.com or 555-123-4567'
   redacted = redactor.redact_pii(test_text)
   print(f'Original: {test_text}')
   print(f'Redacted: {redacted}')
   "
   ```

2. **Data Retention Compliance**
   ```bash
   # Clean up old data per retention policy
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "
   DELETE FROM messages 
   WHERE created_at < NOW() - INTERVAL '7 years';
   
   DELETE FROM audit_logs 
   WHERE created_at < NOW() - INTERVAL '7 years';
   "
   ```

#### Access Audit

1. **Review User Access**
   ```bash
   # Check API key usage
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "
   SELECT api_key_id, last_used, request_count 
   FROM api_keys 
   WHERE last_used > NOW() - INTERVAL '30 days'
   ORDER BY last_used DESC;
   "
   ```

2. **Generate Compliance Reports**
   ```bash
   # Export access logs for compliance
   kubectl exec -it postgres-0 -n mesh-system -- psql -U mesh_user -d mesh_production -c "
   COPY (
     SELECT user_id, action, resource, timestamp, ip_address 
     FROM audit_logs 
     WHERE timestamp >= '2024-01-01' 
     AND timestamp < '2024-02-01'
   ) TO '/tmp/audit_report_jan2024.csv' WITH CSV HEADER;
   "
   
   kubectl cp mesh-system/postgres-0:/tmp/audit_report_jan2024.csv ./audit_report_jan2024.csv
   ```

## Emergency Contacts

### Escalation Matrix

- **L1 Support**: On-call engineer (24/7)
- **L2 Support**: Senior engineer (business hours)
- **L3 Support**: Architecture team (on-call)
- **Management**: Engineering manager (critical incidents)

### Communication Channels

- **Slack**: #mesh-system-alerts
- **PagerDuty**: mesh-system-oncall
- **Email**: mesh-system-team@company.com
- **Status Page**: status.mesh.yourdomain.com

### External Vendors

- **Cloud Provider**: AWS/GCP/Azure support
- **Database**: PostgreSQL support contract
- **Monitoring**: Datadog/New Relic support
- **Security**: Security vendor contacts

---

**Document Version**: 1.0  
**Last Updated**: January 16, 2024  
**Next Review**: April 16, 2024