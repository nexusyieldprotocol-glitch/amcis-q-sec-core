-- PostgreSQL Initialization for AMCIS
-- ====================================

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create extension for cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schema for AMCIS
CREATE SCHEMA IF NOT EXISTS amcis;

-- Set default schema
SET search_path TO amcis, public;

-- Create tables

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    level VARCHAR(20) NOT NULL,
    source VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    resource VARCHAR(200),
    action VARCHAR(100),
    status VARCHAR(20),
    details JSONB,
    hash VARCHAR(128),
    merkle_root VARCHAR(128)
);

-- Threat intelligence table
CREATE TABLE IF NOT EXISTS threat_intel (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ioc_value VARCHAR(500) NOT NULL,
    ioc_type VARCHAR(50) NOT NULL,
    threat_type VARCHAR(100),
    severity VARCHAR(20) NOT NULL,
    confidence INTEGER CHECK (confidence >= 0 AND confidence <= 100),
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source VARCHAR(200),
    tags TEXT[],
    metadata JSONB,
    active BOOLEAN DEFAULT TRUE
);

-- Compliance records table
CREATE TABLE IF NOT EXISTS compliance_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    framework VARCHAR(50) NOT NULL,
    control_id VARCHAR(100) NOT NULL,
    control_name VARCHAR(200),
    status VARCHAR(50) NOT NULL,
    evidence JSONB,
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assessed_by VARCHAR(100),
    notes TEXT,
    next_assessment TIMESTAMP WITH TIME ZONE
);

-- Key management table
CREATE TABLE IF NOT EXISTS key_management (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_id VARCHAR(200) UNIQUE NOT NULL,
    key_type VARCHAR(50) NOT NULL,
    algorithm VARCHAR(50) NOT NULL,
    purpose VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    rotated_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB
);

-- Device inventory table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(200) UNIQUE NOT NULL,
    hostname VARCHAR(200),
    ip_address INET,
    mac_address MACADDR,
    os_type VARCHAR(100),
    os_version VARCHAR(100),
    agent_version VARCHAR(50),
    last_seen TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'unknown',
    compliance_status VARCHAR(50) DEFAULT 'unknown',
    tags TEXT[],
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_level ON audit_logs(level);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_threat_intel_ioc ON threat_intel(ioc_value);
CREATE INDEX IF NOT EXISTS idx_threat_intel_type ON threat_intel(ioc_type);
CREATE INDEX IF NOT EXISTS idx_threat_intel_severity ON threat_intel(severity);
CREATE INDEX IF NOT EXISTS idx_threat_intel_active ON threat_intel(active);

CREATE INDEX IF NOT EXISTS idx_compliance_framework ON compliance_records(framework);
CREATE INDEX IF NOT EXISTS idx_compliance_control ON compliance_records(control_id);
CREATE INDEX IF NOT EXISTS idx_compliance_status ON compliance_records(status);

CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
CREATE INDEX IF NOT EXISTS idx_devices_compliance ON devices(compliance_status);

-- Create function for updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Insert sample data for development
INSERT INTO threat_intel (ioc_value, ioc_type, threat_type, severity, confidence, source, tags)
VALUES 
    ('192.168.100.100', 'ip', 'c2_server', 'high', 95, 'test_source', ARRAY['test', 'c2']),
    ('malware.example.com', 'domain', 'malware', 'critical', 98, 'test_source', ARRAY['test', 'malware']),
    ('d41d8cd98f00b204e9800998ecf8427e', 'md5', 'ransomware', 'high', 90, 'test_source', ARRAY['test', 'ransomware'])
ON CONFLICT DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA amcis TO amcis;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA amcis TO amcis;
GRANT ALL PRIVILEGES ON SCHEMA amcis TO amcis;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA amcis GRANT ALL ON TABLES TO amcis;
ALTER DEFAULT PRIVILEGES IN SCHEMA amcis GRANT ALL ON SEQUENCES TO amcis;
