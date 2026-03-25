-- AMCIS Enterprise Schema Initialization
-- Version: 2026.03.07
-- Run order: 01

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enterprise OS Schema
CREATE SCHEMA IF NOT EXISTS enterprise_os;

CREATE TABLE IF NOT EXISTS enterprise_os.transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vertical VARCHAR(50) NOT NULL,
    transaction_data JSONB NOT NULL,
    verdict JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS enterprise_os.ai_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_type VARCHAR(100) NOT NULL,
    inputs_hash VARCHAR(64) NOT NULL,
    outputs JSONB NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_transactions_vertical ON enterprise_os.transactions(vertical);
CREATE INDEX idx_transactions_created ON enterprise_os.transactions(created_at);
CREATE INDEX idx_decisions_type ON enterprise_os.ai_decisions(decision_type);

-- SPHINX Schema
CREATE SCHEMA IF NOT EXISTS sphinx;

CREATE TABLE IF NOT EXISTS sphinx.agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(100) UNIQUE NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    capabilities TEXT[],
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS sphinx.decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id VARCHAR(100) UNIQUE NOT NULL,
    agent_id VARCHAR(100) REFERENCES sphinx.agents(agent_id),
    proposal_hash VARCHAR(64) NOT NULL,
    vote VARCHAR(10) NOT NULL,
    justification TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- StableCoin Schema
CREATE SCHEMA IF NOT EXISTS stablecoin;

CREATE TABLE IF NOT EXISTS stablecoin.stability_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_type VARCHAR(50) NOT NULL,
    value FLOAT NOT NULL,
    target FLOAT NOT NULL,
    deviation FLOAT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stablecoin.pid_adjustments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kp FLOAT NOT NULL,
    ki FLOAT NOT NULL,
    kd FLOAT NOT NULL,
    adjustment_type VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_stability_timestamp ON stablecoin.stability_metrics(timestamp);

-- Security Schema
CREATE SCHEMA IF NOT EXISTS security;

CREATE TABLE IF NOT EXISTS security.adversary_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    adversary_class VARCHAR(10) NOT NULL,
    capabilities TEXT[],
    threat_level INTEGER NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS security.detection_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    details JSONB NOT NULL,
    evidence_hash VARCHAR(64),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_detection_timestamp ON security.detection_events(timestamp);
CREATE INDEX idx_detection_severity ON security.detection_events(severity);
