-- Row-Level Security (RLS) policies for multi-tenant architecture
-- This file contains PostgreSQL RLS policies to enforce tenant isolation

-- Enable RLS on all tenant-aware tables
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Create a function to get the current tenant ID from the session
-- This would typically be set by the application when establishing a connection
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID AS $$
BEGIN
    -- Get tenant_id from session variable set by application
    RETURN COALESCE(
        current_setting('app.current_tenant_id', true)::UUID,
        '00000000-0000-0000-0000-000000000000'::UUID
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a function to check if user is system admin
CREATE OR REPLACE FUNCTION is_system_admin() RETURNS BOOLEAN AS $$
BEGIN
    -- Get system_admin flag from session variable set by application
    RETURN COALESCE(
        current_setting('app.is_system_admin', true)::BOOLEAN,
        false
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Messages table RLS policies
CREATE POLICY messages_tenant_isolation ON messages
    FOR ALL
    TO PUBLIC
    USING (tenant_id = current_tenant_id() OR is_system_admin());

CREATE POLICY messages_insert_tenant ON messages
    FOR INSERT
    TO PUBLIC
    WITH CHECK (tenant_id = current_tenant_id() OR is_system_admin());

-- Threads table RLS policies
CREATE POLICY threads_tenant_isolation ON threads
    FOR ALL
    TO PUBLIC
    USING (tenant_id = current_tenant_id() OR is_system_admin());

CREATE POLICY threads_insert_tenant ON threads
    FOR INSERT
    TO PUBLIC
    WITH CHECK (tenant_id = current_tenant_id() OR is_system_admin());

-- Participants table RLS policies
CREATE POLICY participants_tenant_isolation ON participants
    FOR ALL
    TO PUBLIC
    USING (tenant_id = current_tenant_id() OR is_system_admin());

CREATE POLICY participants_insert_tenant ON participants
    FOR INSERT
    TO PUBLIC
    WITH CHECK (tenant_id = current_tenant_id() OR is_system_admin());

-- Audit logs table RLS policies
CREATE POLICY audit_logs_tenant_isolation ON audit_logs
    FOR ALL
    TO PUBLIC
    USING (tenant_id = current_tenant_id() OR is_system_admin());

CREATE POLICY audit_logs_insert_tenant ON audit_logs
    FOR INSERT
    TO PUBLIC
    WITH CHECK (tenant_id = current_tenant_id() OR is_system_admin());

-- Create indexes to optimize RLS policy performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_tenant_rls ON messages (tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_threads_tenant_rls ON threads (tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_tenant_rls ON participants (tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_tenant_rls ON audit_logs (tenant_id) WHERE tenant_id IS NOT NULL;

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION current_tenant_id() TO PUBLIC;
GRANT EXECUTE ON FUNCTION is_system_admin() TO PUBLIC;

-- Create a view for tenant-aware queries (optional helper)
CREATE OR REPLACE VIEW tenant_messages AS
SELECT * FROM messages WHERE tenant_id = current_tenant_id();

CREATE OR REPLACE VIEW tenant_threads AS
SELECT * FROM threads WHERE tenant_id = current_tenant_id();

CREATE OR REPLACE VIEW tenant_participants AS
SELECT * FROM participants WHERE tenant_id = current_tenant_id();

-- Grant permissions on views
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_messages TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_threads TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_participants TO PUBLIC;

-- Comments for documentation
COMMENT ON FUNCTION current_tenant_id() IS 'Returns the current tenant ID from session variable app.current_tenant_id';
COMMENT ON FUNCTION is_system_admin() IS 'Returns true if current user is system admin from session variable app.is_system_admin';
COMMENT ON POLICY messages_tenant_isolation ON messages IS 'Ensures users can only access messages from their tenant';
COMMENT ON POLICY threads_tenant_isolation ON threads IS 'Ensures users can only access threads from their tenant';
COMMENT ON POLICY participants_tenant_isolation ON participants IS 'Ensures users can only access participants from their tenant';
COMMENT ON POLICY audit_logs_tenant_isolation ON audit_logs IS 'Ensures users can only access audit logs from their tenant';