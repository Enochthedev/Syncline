# Multi-Tenant Architecture

This document describes the multi-tenant architecture implementation in the REMI system, including tenant isolation, security, quotas, and management.

## Overview

The multi-tenant architecture provides complete data isolation between tenants while sharing the same application infrastructure. Each tenant has:

- **Isolated Data**: Row-level security ensures tenants can only access their own data
- **Tenant-Specific Encryption**: Each tenant has unique encryption keys for sensitive data
- **Quota Management**: Per-tenant resource limits and usage tracking
- **Access Control**: Role-based permissions within tenant boundaries
- **Audit Logging**: Tenant-specific audit trails for compliance

## Architecture Components

### 1. Database Models

#### Core Tenant Models
- **`Tenant`**: Main tenant configuration and metadata
- **`TenantUser`**: User-tenant associations with roles
- **`TenantQuotaUsage`**: Historical quota usage tracking

#### Tenant-Aware Models
All core data models include `tenant_id` for isolation:
- **`Message`**: Messages are isolated by tenant
- **`Thread`**: Conversation threads per tenant
- **`Participant`**: Platform participants per tenant
- **`AuditLog`**: Audit logs with tenant context

### 2. Row-Level Security (RLS)

PostgreSQL RLS policies enforce tenant isolation at the database level:

```sql
-- Example policy for messages table
CREATE POLICY messages_tenant_isolation ON messages
    FOR ALL
    TO PUBLIC
    USING (tenant_id = current_tenant_id() OR is_system_admin());
```

#### RLS Functions
- **`current_tenant_id()`**: Returns current session's tenant ID
- **`is_system_admin()`**: Checks if current session has admin privileges

### 3. Tenant-Aware Sessions

The `TenantAwareSession` class automatically sets PostgreSQL session variables:

```python
async with get_tenant_session(tenant_id) as session:
    # All queries automatically filtered by tenant_id
    messages = await session.execute(select(Message))
```

### 4. Security Services

#### TenantSecurityService
- Tenant-specific encryption key management
- Data encryption/decryption with tenant isolation
- Key rotation per tenant
- Access validation

#### SecurityManager Integration
- Unified security operations across tenants
- Audit logging with tenant context
- Token management per tenant

## API Endpoints

### Tenant Management

#### Create Tenant
```http
POST /api/v1/tenants
Authorization: Bearer <system_admin_token>
Content-Type: application/json

{
  "name": "acme-corp",
  "display_name": "ACME Corporation",
  "admin_email": "admin@acme.com",
  "tier": "premium"
}
```

#### List Tenants
```http
GET /api/v1/tenants?active_only=true&tier=premium
Authorization: Bearer <system_admin_token>
```

#### Get Tenant Details
```http
GET /api/v1/tenants/{tenant_id}
Authorization: Bearer <tenant_token>
X-Tenant-ID: {tenant_id}
```

#### Update Tenant
```http
PUT /api/v1/tenants/{tenant_id}
Authorization: Bearer <tenant_admin_token>
X-Tenant-ID: {tenant_id}

{
  "max_users": 50,
  "max_messages_per_month": 500000
}
```

### User Management

#### Add User to Tenant
```http
POST /api/v1/tenants/{tenant_id}/users
Authorization: Bearer <tenant_admin_token>

{
  "user_id": "user-uuid",
  "role": "member",
  "permissions": ["read_messages", "write_messages"]
}
```

#### Remove User from Tenant
```http
DELETE /api/v1/tenants/{tenant_id}/users/{user_id}
Authorization: Bearer <tenant_admin_token>
```

### Quota Management

#### Check Quota Status
```http
GET /api/v1/tenants/{tenant_id}/quotas/messages?requested_amount=100
Authorization: Bearer <tenant_token>
```

#### Update Quota Usage
```http
POST /api/v1/tenants/{tenant_id}/quotas/messages/usage
Authorization: Bearer <tenant_token>

{
  "amount": 50
}
```

### Security Operations

#### Rotate Tenant Keys
```http
POST /api/v1/tenants/{tenant_id}/security/rotate-keys?key_type=data_encryption_key
Authorization: Bearer <tenant_admin_token>
```

#### Get Security Status
```http
GET /api/v1/tenants/{tenant_id}/security/status
Authorization: Bearer <tenant_token>
```

## Authentication & Authorization

### JWT Token Structure

Tenant context is embedded in JWT tokens:

```json
{
  "user_id": "user-uuid",
  "tenant_id": "tenant-uuid",
  "is_system_admin": false,
  "roles": ["admin", "member"],
  "exp": 1234567890
}
```

### Header-Based Context (Development)

For development and testing, tenant context can be passed via headers:

```http
X-Tenant-ID: tenant-uuid
X-User-ID: user-uuid
X-System-Admin: false
```

### Access Control Levels

1. **System Admin**: Full access to all tenants and system operations
2. **Tenant Admin**: Full access within their tenant
3. **Tenant Member**: Read/write access to tenant data
4. **Tenant Viewer**: Read-only access to tenant data

## Quota System

### Quota Types

- **Users**: Maximum number of users per tenant
- **Messages**: Monthly message processing limit
- **Storage**: Storage space in GB
- **API Requests**: Hourly API request limit
- **AI Requests**: Daily AI processing limit

### Tier-Based Quotas

#### Free Tier
- 3 users
- 10,000 messages/month
- 1 GB storage
- 100 API requests/hour
- 100 AI requests/day

#### Standard Tier
- 10 users
- 100,000 messages/month
- 10 GB storage
- 1,000 API requests/hour
- 1,000 AI requests/day

#### Premium Tier
- 50 users
- 1,000,000 messages/month
- 100 GB storage
- 10,000 API requests/hour
- 10,000 AI requests/day

#### Enterprise Tier
- 1,000 users
- 10,000,000 messages/month
- 1,000 GB storage
- 100,000 API requests/hour
- 100,000 AI requests/day

### Quota Enforcement

Quotas are enforced at multiple levels:

1. **API Level**: Middleware checks quotas before processing requests
2. **Service Level**: Services validate quotas before operations
3. **Database Level**: Triggers can enforce hard limits
4. **Background Jobs**: Monitor and update usage metrics

## Encryption & Security

### Tenant-Specific Encryption

Each tenant has unique encryption keys:

```python
# Encrypt data for tenant
encrypted = await security_service.encrypt_tenant_data(
    tenant_id, "sensitive data", "field_name"
)

# Decrypt data (only works with correct tenant context)
decrypted = await security_service.decrypt_tenant_data(
    tenant_id, encrypted, "field_name"
)
```

### Key Management

- **Master Key**: System-wide master key (KMS/HSM in production)
- **Tenant Keys**: Per-tenant data encryption keys
- **Token Keys**: Per-tenant token encryption keys
- **Automatic Rotation**: Configurable key rotation schedules

### Data Classification

- **PII Data**: Automatically encrypted with tenant keys
- **Platform Tokens**: Encrypted with tenant-specific token keys
- **Audit Logs**: Integrity-protected with hash chains
- **Metadata**: Tenant-isolated but not necessarily encrypted

## Deployment & Setup

### Database Migration

Run the multi-tenant migration:

```bash
alembic upgrade head
```

### RLS Setup

Execute the RLS setup script:

```bash
python scripts/setup_multi_tenant.py
```

### Validation

Validate the setup:

```bash
python scripts/setup_multi_tenant.py validate
```

### Environment Variables

```bash
# Database configuration
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# Security configuration
MESH_MASTER_KEY=base64-encoded-key
SECURITY_ENCRYPTION_ENABLED=true
SECURITY_TOKEN_ENCRYPTION_ENABLED=true

# JWT configuration
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

## Monitoring & Observability

### Metrics

- **Tenant Count**: Number of active tenants
- **Quota Usage**: Per-tenant quota utilization
- **API Requests**: Request rates per tenant
- **Data Volume**: Storage usage per tenant
- **Security Events**: Encryption/decryption operations

### Logging

- **Tenant Context**: All logs include tenant_id when available
- **Audit Trail**: Complete audit log for compliance
- **Security Events**: Encryption, key rotation, access violations
- **Performance**: Query performance per tenant

### Alerts

- **Quota Exceeded**: Alert when tenants approach limits
- **Security Violations**: Cross-tenant access attempts
- **Performance Issues**: Slow queries or high resource usage
- **Key Rotation**: Upcoming or failed key rotations

## Testing

### Security Tests

Run the comprehensive security test suite:

```bash
pytest tests/test_tenant_security.py -v
```

### Test Categories

1. **Isolation Tests**: Verify tenant data isolation
2. **Encryption Tests**: Test tenant-specific encryption
3. **Quota Tests**: Validate quota enforcement
4. **Access Control Tests**: Test permission boundaries
5. **Integration Tests**: End-to-end tenant workflows

### Test Data

Tests use isolated test tenants and automatically clean up:

```python
@pytest_asyncio.fixture
async def test_tenants():
    # Create test tenants
    tenant1 = await create_test_tenant("test-1")
    tenant2 = await create_test_tenant("test-2")
    
    yield tenant1, tenant2
    
    # Cleanup
    await delete_test_tenant(tenant1.id)
    await delete_test_tenant(tenant2.id)
```

## Best Practices

### Development

1. **Always Use Tenant Context**: Never query data without tenant context
2. **Validate Access**: Check tenant access before operations
3. **Encrypt Sensitive Data**: Use tenant-specific encryption for PII
4. **Log Tenant Context**: Include tenant_id in all logs
5. **Test Isolation**: Write tests that verify tenant boundaries

### Security

1. **Principle of Least Privilege**: Grant minimal necessary permissions
2. **Regular Key Rotation**: Implement automated key rotation
3. **Audit Everything**: Log all tenant operations
4. **Validate Input**: Sanitize and validate all tenant data
5. **Monitor Access**: Alert on suspicious cross-tenant access

### Performance

1. **Index Tenant Columns**: Ensure tenant_id columns are indexed
2. **Partition Large Tables**: Consider partitioning by tenant_id
3. **Cache Tenant Data**: Cache frequently accessed tenant metadata
4. **Monitor Query Performance**: Track per-tenant query performance
5. **Optimize RLS Policies**: Ensure RLS policies are efficient

### Operations

1. **Backup Per Tenant**: Consider tenant-specific backup strategies
2. **Monitor Quotas**: Set up quota monitoring and alerting
3. **Plan Capacity**: Monitor tenant growth and resource usage
4. **Document Procedures**: Maintain runbooks for tenant operations
5. **Test Disaster Recovery**: Regularly test tenant data recovery

## Troubleshooting

### Common Issues

#### RLS Not Working
```sql
-- Check if RLS is enabled
SELECT relrowsecurity FROM pg_class WHERE relname = 'messages';

-- Check if policies exist
SELECT * FROM pg_policies WHERE tablename = 'messages';
```

#### Cross-Tenant Data Leakage
```python
# Check session context
async with get_tenant_session(tenant_id) as session:
    result = await session.execute(text("SELECT current_setting('app.current_tenant_id')"))
    print(f"Current tenant: {result.scalar()}")
```

#### Encryption Key Issues
```python
# Check tenant keys
security_service = TenantSecurityService()
status = await security_service.get_tenant_security_status(tenant_id)
print(f"Key count: {status['encryption']['key_count']}")
```

#### Quota Not Enforcing
```python
# Check quota status
tenant_service = TenantService(session)
quota = await tenant_service.check_quota(tenant_id, "messages", 1)
print(f"Quota allowed: {quota['allowed']}")
```

### Debug Commands

```bash
# Check database connectivity
python -c "from db.tenant_session import session_manager; import asyncio; print(asyncio.run(session_manager.health_check()))"

# Validate RLS setup
python scripts/setup_multi_tenant.py validate

# Run security tests
pytest tests/test_tenant_security.py::TestTenantIsolation -v

# Check tenant statistics
python -c "
from services.tenant_service import TenantService
from db.tenant_session import get_system_session
import asyncio

async def check_tenant(tenant_id):
    async with get_system_session() as session:
        service = TenantService(session)
        stats = await service.get_tenant_statistics(tenant_id)
        print(stats)

asyncio.run(check_tenant('your-tenant-id'))
"
```

## Migration Guide

### From Single-Tenant

1. **Add tenant_id columns** to all data tables
2. **Create tenant records** for existing data
3. **Set up RLS policies** for data isolation
4. **Update application code** to use tenant context
5. **Test thoroughly** with multiple tenants

### Rollback Plan

1. **Disable RLS policies** temporarily
2. **Remove tenant_id constraints** if needed
3. **Restore from backup** if data corruption occurs
4. **Re-run migrations** after fixing issues

## Future Enhancements

### Planned Features

1. **Tenant-Specific Domains**: Custom domains per tenant
2. **Advanced RBAC**: Fine-grained permission system
3. **Tenant Analytics**: Detailed usage analytics per tenant
4. **Automated Scaling**: Auto-scale resources based on tenant usage
5. **Compliance Frameworks**: Built-in compliance reporting

### Scalability Improvements

1. **Database Sharding**: Shard data by tenant for scale
2. **Microservices**: Split services by tenant boundaries
3. **Caching Layers**: Tenant-aware caching strategies
4. **CDN Integration**: Tenant-specific content delivery
5. **Load Balancing**: Tenant-aware load balancing