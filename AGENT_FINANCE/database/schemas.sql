-- AMCIS Financial Agent Database Schema
-- PostgreSQL schema for trading, positions, and P&L tracking

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Agents table
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'inactive',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    profit DECIMAL(36, 18) DEFAULT 0
);

-- Orders table
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    order_type VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    amount DECIMAL(36, 18) NOT NULL,
    price DECIMAL(36, 18),
    filled_amount DECIMAL(36, 18) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    exchange VARCHAR(100) NOT NULL,
    fee_amount DECIMAL(36, 18) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_at TIMESTAMP WITH TIME ZONE
);

-- Trades table
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES orders(id),
    agent_id UUID REFERENCES agents(id),
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,
    amount DECIMAL(36, 18) NOT NULL,
    price DECIMAL(36, 18) NOT NULL,
    total_value DECIMAL(36, 18) NOT NULL,
    fee_amount DECIMAL(36, 18) DEFAULT 0,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Positions table
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    symbol VARCHAR(50) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    side VARCHAR(10) NOT NULL,
    size DECIMAL(36, 18) NOT NULL,
    entry_price DECIMAL(36, 18) NOT NULL,
    current_price DECIMAL(36, 18),
    unrealized_pnl DECIMAL(36, 18) DEFAULT 0,
    realized_pnl DECIMAL(36, 18) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'open',
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

-- Arbitrage opportunities
CREATE TABLE arbitrage_opportunities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    symbol VARCHAR(50) NOT NULL,
    buy_exchange VARCHAR(100) NOT NULL,
    sell_exchange VARCHAR(100) NOT NULL,
    net_profit DECIMAL(36, 18) NOT NULL,
    status VARCHAR(50) DEFAULT 'detected',
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_at TIMESTAMP WITH TIME ZONE
);

-- Performance metrics
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    period_type VARCHAR(50) NOT NULL,
    net_profit DECIMAL(36, 18) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Risk events
CREATE TABLE risk_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT,
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_orders_agent ON orders(agent_id);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_trades_agent ON trades(agent_id);
CREATE INDEX idx_positions_agent ON positions(agent_id);
CREATE INDEX idx_arb_status ON arbitrage_opportunities(status);
