-- AMCIS NG Database Schema v1.0
-- PostgreSQL 16+ with pgcrypto

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    trust_score DECIMAL(3,2) DEFAULT 1.0,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Devices table
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),
    device_type VARCHAR(50) NOT NULL,
    trust_score DECIMAL(3,2) DEFAULT 0.5,
    encryption_enabled BOOLEAN DEFAULT FALSE,
    edr_active BOOLEAN DEFAULT FALSE,
    compliance_status VARCHAR(50) DEFAULT 'unknown',
    last_seen TIMESTAMP WITH TIME ZONE,
    ip_address INET,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Threats table
CREATE TABLE threats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    threat_id VARCHAR(255) UNIQUE NOT NULL,
    threat_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'new',
    description TEXT,
    affected_device_id UUID REFERENCES devices(id),
    confidence DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Security events (audit log)
CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'info',
    user_id UUID REFERENCES users(id),
    device_id UUID REFERENCES devices(id),
    action VARCHAR(255),
    result VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_devices_user ON devices(user_id);
CREATE INDEX idx_threats_severity ON threats(severity);
CREATE INDEX idx_threats_status ON threats(status);
CREATE INDEX idx_events_user ON security_events(user_id);
CREATE INDEX idx_events_created ON security_events(created_at);

-- Sample data
INSERT INTO users (username, email, password_hash, trust_score) VALUES
    ('admin', 'admin@amcis.io', crypt('changeme', gen_salt('bf')), 1.0),
    ('analyst', 'analyst@amcis.io', crypt('changeme', gen_salt('bf')), 0.9);

-- Active threats view
CREATE VIEW v_active_threats AS
SELECT severity, COUNT(*) as count
FROM threats WHERE status IN ('new', 'investigating')
GROUP BY severity;
