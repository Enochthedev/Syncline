# MESH Ingestion System - Deployment Guide

## Overview
This guide covers deployment, configuration, and operational procedures for the MESH Ingestion System.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Database Setup](#database-setup)
- [Redis Configuration](#redis-configuration)
- [Application Deployment](#application-deployment)
- [Platform Configuration](#platform-configuration)
- [Monitoring Setup](#monitoring-setup)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended) or macOS
- **Python**: 3.11 or higher
- **Memory**: 4GB minimum, 8GB recommended
- **Storage**: 50GB minimum for logs and data
- **Network**: Outbound HTTPS access for platform APIs

### External Services
- **PostgreSQL**: 14.0 or higher
- **Redis**: 6.0 or higher
- **Google Cloud Project**: For Gmail integration
- **SSL Certificate**: For webhook endpoints (production)

## Environment Setup

### 1. Create Application User
```bash
# Create dedicated user
sudo useradd -m -s /bin/bash mesh
sudo usermod -aG sudo mesh

# Switch to application user
sudo su - mesh
```

### 2. Install Python Dependencies
```bash
# Install Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Create virtual environment
python3.11 -m venv /home/mesh/venv
source /home/mesh/venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Clone Repository
```bash
cd /home/mesh
git clone https://github.com/your-org/mesh-ingestion-system.git
cd mesh-ingestion-system

# Install dependencies
pip install -r requirements.txt
```

## Database Setup

### 1. PostgreSQL Installation
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Database Configuration
```bash
# Switch to postgres user
sudo su - postgres

# Create database and user
createdb mesh_production
createuser --interactive mesh_user

# Set password
psql -c "ALTER USER mesh_user PASSWORD 'secure_password_here';"

# Grant permissions
psql -c "GRANT ALL PRIVILEGES ON DATABASE mesh_production TO mesh_user;"
```

### 3. Database Tuning
Edit `/etc/postgresql/14/main/postgresql.conf`:
```ini
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Connection settings
max_connections = 100
listen_addresses = 'localhost'

# Performance settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

### 4. Run Migrations
```bash
# Set database URL
export DATABASE_URL="postgresql://mesh_user:secure_password_here@localhost/mesh_production"

# Run migrations
alembic upgrade head
```

## Redis Configuration

### 1. Redis Installation
```bash
# Install Redis
sudo apt install redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
```

### 2. Redis Configuration
Edit `/etc/redis/redis.conf`:
```ini
# Memory settings
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Security
requirepass your_redis_password_here
bind 127.0.0.1

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log
```

### 3. Start Redis
```bash
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

## Application Deployment

### 1. Environment Configuration
Create `/home/mesh/mesh-ingestion-system/.env`:
```bash
# Environment
ENV=production
DEBUG=false

# Database
DATABASE_URL=postgresql://mesh_user:secure_password_here@localhost/mesh_production
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_PRE_PING=true

# Redis
REDIS_URL=redis://:your_redis_password_here@localhost:6379

# Gmail Configuration
GMAIL_SCOPES="https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify"
GMAIL_CREDENTIALS_FILE="/home/mesh/config/gmail_credentials.json"
GMAIL_TOKEN_FILE="/home/mesh/config/gmail_token.json"
GMAIL_WEBHOOK_ENDPOINT="/webhooks/gmail"
GMAIL_WEBHOOK_SECRET="your_webhook_secret_here"
GMAIL_TOPIC_NAME="projects/your-project/topics/gmail-push"

# Security
TOKEN_ENCRYPTION_KEY="your_32_byte_encryption_key_here"

# Logging
LOG_LEVEL=INFO
LOG_FILE="/var/log/mesh/application.log"
```

### 2. Create Systemd Service
Create `/etc/systemd/system/mesh-ingestion.service`:
```ini
[Unit]
Description=MESH Ingestion System
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=mesh
Group=mesh
WorkingDirectory=/home/mesh/mesh-ingestion-system
Environment=PATH=/home/mesh/venv/bin
ExecStart=/home/mesh/venv/bin/python main.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

# Resource limits
LimitNOFILE=65536
MemoryMax=2G

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mesh-ingestion

[Install]
WantedBy=multi-user.target
```

### 3. Create Log Directory
```bash
sudo mkdir -p /var/log/mesh
sudo chown mesh:mesh /var/log/mesh
```

### 4. Start Application
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable mesh-ingestion
sudo systemctl start mesh-ingestion

# Check status
sudo systemctl status mesh-ingestion
```

## Platform Configuration

### Gmail Setup

#### 1. Google Cloud Project
1. Create or select a Google Cloud Project
2. Enable the Gmail API
3. Create OAuth 2.0 credentials
4. Download credentials JSON file

#### 2. OAuth Credentials
```bash
# Copy credentials file
cp ~/Downloads/credentials.json /home/mesh/config/gmail_credentials.json
chown mesh:mesh /home/mesh/config/gmail_credentials.json
chmod 600 /home/mesh/config/gmail_credentials.json
```

#### 3. Push Notifications Setup
```bash
# Create Pub/Sub topic
gcloud pubsub topics create gmail-push

# Create subscription
gcloud pubsub subscriptions create gmail-push-sub --topic=gmail-push

# Set up webhook endpoint
# Configure your domain to point to the application
```

#### 4. Initial Authentication
```bash
# Run initial OAuth flow (interactive)
cd /home/mesh/mesh-ingestion-system
source /home/mesh/venv/bin/activate
python -c "
from integrations.gmail_factory import setup_gmail_integration
import asyncio
asyncio.run(setup_gmail_integration())
"
```

## Reverse Proxy Setup (Nginx)

### 1. Install Nginx
```bash
sudo apt install nginx
```

### 2. Configure Nginx
Create `/etc/nginx/sites-available/mesh-ingestion`:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Proxy to application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Webhook endpoints (higher limits)
    location /webhooks/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increased limits for webhooks
        client_max_body_size 10M;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
}
```

### 3. Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/mesh-ingestion /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Monitoring Setup

### 1. Log Rotation
Create `/etc/logrotate.d/mesh-ingestion`:
```
/var/log/mesh/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 mesh mesh
    postrotate
        systemctl reload mesh-ingestion
    endscript
}
```

### 2. Health Check Script
Create `/home/mesh/scripts/health_check.sh`:
```bash
#!/bin/bash

HEALTH_URL="http://localhost:8000/health"
TIMEOUT=10

response=$(curl -s -w "%{http_code}" -o /dev/null --max-time $TIMEOUT "$HEALTH_URL")

if [ "$response" = "200" ]; then
    echo "$(date): Health check passed"
    exit 0
else
    echo "$(date): Health check failed (HTTP $response)"
    exit 1
fi
```

### 3. Cron Job for Health Checks
```bash
# Add to crontab
crontab -e

# Add this line (check every 5 minutes)
*/5 * * * * /home/mesh/scripts/health_check.sh >> /var/log/mesh/health_check.log 2>&1
```

### 4. System Metrics Collection
Install and configure monitoring tools:
```bash
# Install htop for system monitoring
sudo apt install htop

# Install netdata for real-time metrics (optional)
bash <(curl -Ss https://my-netdata.io/kickstart.sh)
```

## Backup & Recovery

### 1. Database Backup
Create `/home/mesh/scripts/backup_db.sh`:
```bash
#!/bin/bash

BACKUP_DIR="/home/mesh/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="mesh_production"
DB_USER="mesh_user"

mkdir -p $BACKUP_DIR

# Create backup
pg_dump -h localhost -U $DB_USER -d $DB_NAME | gzip > $BACKUP_DIR/mesh_db_$DATE.sql.gz

# Keep only last 7 days of backups
find $BACKUP_DIR -name "mesh_db_*.sql.gz" -mtime +7 -delete

echo "$(date): Database backup completed: mesh_db_$DATE.sql.gz"
```

### 2. Configuration Backup
```bash
#!/bin/bash

BACKUP_DIR="/home/mesh/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup configuration files
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    /home/mesh/mesh-ingestion-system/.env \
    /home/mesh/config/ \
    /etc/nginx/sites-available/mesh-ingestion \
    /etc/systemd/system/mesh-ingestion.service

echo "$(date): Configuration backup completed: config_$DATE.tar.gz"
```

### 3. Automated Backups
Add to crontab:
```bash
# Daily database backup at 2 AM
0 2 * * * /home/mesh/scripts/backup_db.sh >> /var/log/mesh/backup.log 2>&1

# Weekly configuration backup on Sundays at 3 AM
0 3 * * 0 /home/mesh/scripts/backup_config.sh >> /var/log/mesh/backup.log 2>&1
```

## Troubleshooting

### Common Issues

#### 1. Application Won't Start
```bash
# Check service status
sudo systemctl status mesh-ingestion

# Check logs
sudo journalctl -u mesh-ingestion -f

# Check application logs
tail -f /var/log/mesh/application.log
```

#### 2. Database Connection Issues
```bash
# Test database connection
psql -h localhost -U mesh_user -d mesh_production -c "SELECT 1;"

# Check PostgreSQL status
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

#### 3. Redis Connection Issues
```bash
# Test Redis connection
redis-cli -a your_redis_password_here ping

# Check Redis status
sudo systemctl status redis-server

# Check Redis logs
sudo tail -f /var/log/redis/redis-server.log
```

#### 4. Gmail Webhook Issues
```bash
# Check webhook endpoint
curl -X POST https://your-domain.com/webhooks/gmail \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Check Gmail push notification setup
gcloud pubsub topics list
gcloud pubsub subscriptions list
```

### Performance Tuning

#### 1. Database Optimization
```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Analyze table statistics
ANALYZE messages;
ANALYZE entities;
```

#### 2. Redis Optimization
```bash
# Check Redis memory usage
redis-cli -a your_redis_password_here info memory

# Monitor Redis performance
redis-cli -a your_redis_password_here --latency-history
```

#### 3. Application Tuning
```bash
# Monitor application performance
htop

# Check application metrics
curl http://localhost:8000/status
```

### Log Analysis

#### 1. Application Logs
```bash
# Search for errors
grep -i error /var/log/mesh/application.log

# Monitor real-time logs
tail -f /var/log/mesh/application.log | grep -i "gmail\|webhook\|error"

# Analyze log patterns
awk '/ERROR/ {print $1, $2, $NF}' /var/log/mesh/application.log | sort | uniq -c
```

#### 2. System Logs
```bash
# Check system messages
sudo journalctl -f

# Check specific service logs
sudo journalctl -u mesh-ingestion -n 100
```

## Security Considerations

### 1. File Permissions
```bash
# Secure configuration files
chmod 600 /home/mesh/mesh-ingestion-system/.env
chmod 600 /home/mesh/config/gmail_credentials.json
chmod 600 /home/mesh/config/gmail_token.json
```

### 2. Network Security
- Use firewall to restrict access
- Enable SSL/TLS for all external communications
- Regularly update SSL certificates
- Monitor for suspicious webhook requests

### 3. Credential Management
- Rotate API keys and secrets regularly
- Use environment variables for sensitive data
- Enable audit logging for credential access
- Implement proper backup encryption

---

**Last Updated**: January 15, 2025  
**Version**: 1.0.0

For additional support, see `/docs/troubleshooting/` or contact the development team.