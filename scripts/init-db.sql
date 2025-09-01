-- Database initialization script for PostgreSQL
-- This script sets up the initial database structure and configuration

-- Create database if it doesn't exist (run this separately as superuser)
-- CREATE DATABASE orm_calculator;

-- Connect to the database
\c orm_calculator;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS orm_data;
CREATE SCHEMA IF NOT EXISTS orm_audit;
CREATE SCHEMA IF NOT EXISTS orm_config;

-- Set search path
SET search_path TO public, orm_data, orm_audit, orm_config;

-- Create custom types
CREATE TYPE calculation_status AS ENUM ('queued', 'running', 'completed', 'failed');
CREATE TYPE job_execution_mode AS ENUM ('sync', 'async');
CREATE TYPE calculation_methodology AS ENUM ('sma', 'bia', 'tsa', 'what-if');
CREATE TYPE business_line_type AS ENUM (
    'corporate_finance',
    'trading_sales', 
    'retail_banking',
    'commercial_banking',
    'payment_settlement',
    'agency_services',
    'asset_management',
    'retail_brokerage'
);
CREATE TYPE event_type AS ENUM (
    'internal_fraud',
    'external_fraud',
    'employment_practices',
    'clients_products_business',
    'damage_physical_assets',
    'business_disruption',
    'execution_delivery_process'
);

-- Create sequences
CREATE SEQUENCE IF NOT EXISTS job_sequence START 1000;
CREATE SEQUENCE IF NOT EXISTS run_sequence START 1000;

-- Create functions for audit trail
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create function for generating run IDs
CREATE OR REPLACE FUNCTION generate_run_id()
RETURNS TEXT AS $$
BEGIN
    RETURN 'run_' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDD_HH24MISS') || '_' || LPAD(nextval('run_sequence')::TEXT, 6, '0');
END;
$$ language 'plpgsql';

-- Create function for generating job IDs
CREATE OR REPLACE FUNCTION generate_job_id()
RETURNS TEXT AS $$
BEGIN
    RETURN 'job_' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDD_HH24MISS') || '_' || LPAD(nextval('job_sequence')::TEXT, 6, '0');
END;
$$ language 'plpgsql';

-- Create partitioning function for time-series data
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name TEXT, start_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    end_date DATE;
BEGIN
    partition_name := table_name || '_' || TO_CHAR(start_date, 'YYYY_MM');
    end_date := start_date + INTERVAL '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I 
                    FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ language 'plpgsql';

-- Create indexes for common queries
-- Note: Actual table creation will be handled by SQLAlchemy/Alembic
-- These are additional performance indexes

-- Performance optimization settings
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Create roles for different access levels
CREATE ROLE orm_readonly;
CREATE ROLE orm_readwrite;
CREATE ROLE orm_admin;

-- Grant permissions
GRANT CONNECT ON DATABASE orm_calculator TO orm_readonly, orm_readwrite, orm_admin;
GRANT USAGE ON SCHEMA public, orm_data, orm_audit, orm_config TO orm_readonly, orm_readwrite, orm_admin;

-- Readonly permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public, orm_data, orm_audit, orm_config TO orm_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public, orm_data, orm_audit, orm_config TO orm_readonly;

-- Read-write permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public, orm_data, orm_config TO orm_readwrite;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA orm_audit TO orm_readwrite;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public, orm_data, orm_audit, orm_config TO orm_readwrite;

-- Admin permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public, orm_data, orm_audit, orm_config TO orm_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public, orm_data, orm_audit, orm_config TO orm_admin;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public, orm_data, orm_audit, orm_config 
    GRANT SELECT ON TABLES TO orm_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public, orm_data, orm_config 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO orm_readwrite;
ALTER DEFAULT PRIVILEGES IN SCHEMA orm_audit 
    GRANT SELECT, INSERT ON TABLES TO orm_readwrite;
ALTER DEFAULT PRIVILEGES IN SCHEMA public, orm_data, orm_audit, orm_config 
    GRANT ALL ON TABLES TO orm_admin;

-- Create monitoring views
CREATE OR REPLACE VIEW v_system_health AS
SELECT 
    'database' as component,
    CASE WHEN pg_is_in_recovery() THEN 'standby' ELSE 'primary' END as status,
    pg_database_size(current_database()) as size_bytes,
    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
    (SELECT count(*) FROM pg_stat_activity) as total_connections,
    CURRENT_TIMESTAMP as checked_at;

CREATE OR REPLACE VIEW v_table_stats AS
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY schemaname, tablename;

-- Create maintenance procedures
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(retention_days INTEGER DEFAULT 180)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete audit logs older than retention period
    DELETE FROM audit_trail 
    WHERE timestamp < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Log the cleanup
    INSERT INTO audit_trail (run_id, operation, initiator, timestamp, details)
    VALUES (
        generate_run_id(),
        'AUDIT_CLEANUP',
        'SYSTEM',
        CURRENT_TIMESTAMP,
        jsonb_build_object('deleted_records', deleted_count, 'retention_days', retention_days)
    );
    
    RETURN deleted_count;
END;
$$ language 'plpgsql';

-- Create backup verification function
CREATE OR REPLACE FUNCTION verify_backup_integrity()
RETURNS TABLE(table_name TEXT, record_count BIGINT, last_updated TIMESTAMP) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.tablename::TEXT,
        t.n_live_tup,
        GREATEST(t.last_vacuum, t.last_autovacuum, t.last_analyze, t.last_autoanalyze)
    FROM pg_stat_user_tables t
    WHERE t.schemaname IN ('public', 'orm_data', 'orm_audit', 'orm_config')
    ORDER BY t.tablename;
END;
$$ language 'plpgsql';

-- Create notification triggers for critical events
CREATE OR REPLACE FUNCTION notify_critical_event()
RETURNS TRIGGER AS $$
BEGIN
    -- Notify on calculation failures
    IF TG_TABLE_NAME = 'jobs' AND NEW.status = 'failed' THEN
        PERFORM pg_notify('calculation_failed', 
            json_build_object('job_id', NEW.id, 'entity_id', NEW.entity_id)::text);
    END IF;
    
    -- Notify on parameter changes
    IF TG_TABLE_NAME = 'parameter_versions' AND TG_OP = 'INSERT' THEN
        PERFORM pg_notify('parameter_changed',
            json_build_object('model_name', NEW.model_name, 'version_id', NEW.version_id)::text);
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Initial data setup
INSERT INTO orm_config.system_parameters (key, value, description) VALUES
    ('minimum_loss_threshold', '100000', 'Minimum loss threshold in INR'),
    ('loss_data_years', '10', 'Number of years of loss data to consider'),
    ('bi_averaging_years', '3', 'Number of years for BI averaging'),
    ('bucket_1_threshold', '80000000000', 'Bucket 1 threshold (₹8,000 crore)'),
    ('bucket_2_threshold', '2400000000000', 'Bucket 2 threshold (₹2,40,000 crore)'),
    ('alpha_coefficient', '0.15', 'Alpha coefficient for BIA calculation'),
    ('marginal_coeff_1', '0.12', 'Marginal coefficient for Bucket 1 (12%)'),
    ('marginal_coeff_2', '0.15', 'Marginal coefficient for Bucket 2 (15%)'),
    ('marginal_coeff_3', '0.18', 'Marginal coefficient for Bucket 3 (18%)'),
    ('loss_multiplier', '15', 'Loss multiplier for LC calculation'),
    ('rwa_multiplier', '12.5', 'RWA multiplier for capital calculation')
ON CONFLICT (key) DO NOTHING;

-- Create initial admin user (password should be changed immediately)
-- This would typically be done through the application
INSERT INTO orm_config.users (username, email, role, is_active, created_at) VALUES
    ('admin', 'admin@example.com', 'orm_admin', true, CURRENT_TIMESTAMP)
ON CONFLICT (username) DO NOTHING;

COMMIT;