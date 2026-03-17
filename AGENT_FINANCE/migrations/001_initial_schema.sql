-- AMCIS Financial AI Agent Database Schema
-- Revenue-generating trading and DeFi operations

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ============================================
-- AGENT MANAGEMENT
-- ============================================

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(100) NOT NULL, -- 'trader', 'arbitrage', 'yield', 'analyzer'
    status VARCHAR(50) DEFAULT 'inactive', -- 'active', 'paused', 'error', 'inactive'
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE,
    api_key_hash VARCHAR(255),
    permissions JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_agents_type ON agents(agent_type);
CREATE INDEX idx_agents_status ON agents(status);

-- ============================================
-- TRADING OPERATIONS (Core Revenue)
-- ============================================

CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    
    -- Trade details
    trade_type VARCHAR(50) NOT NULL, -- 'spot', 'margin', 'futures', 'options', 'swap'
    side VARCHAR(10) NOT NULL, -- 'buy', 'sell'
    symbol VARCHAR(50) NOT NULL, -- 'BTC-USD', 'ETH-USDC'
    base_asset VARCHAR(20) NOT NULL,
    quote_asset VARCHAR(20) NOT NULL,
    
    -- Quantities
    amount DECIMAL(36, 18) NOT NULL,
    price DECIMAL(36, 18) NOT NULL,
    total_value DECIMAL(36, 18) NOT NULL,
    
    -- Exchange info
    exchange VARCHAR(100) NOT NULL, -- 'binance', 'coinbase', 'uniswap', 'aave'
    exchange_order_id VARCHAR(255),
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'open', 'filled', 'partial', 'cancelled', 'failed'
    filled_amount DECIMAL(36, 18) DEFAULT 0,
    remaining_amount DECIMAL(36, 18),
    avg_fill_price DECIMAL(36, 18),
    
    -- Fees (track exactly)
    fee_amount DECIMAL(36, 18) DEFAULT 0,
    fee_asset VARCHAR(20),
    
    -- P&L tracking
    realized_pnl DECIMAL(36, 18), -- Profit/loss when closed
    unrealized_pnl DECIMAL(36, 18), -- Current unrealized P&L
    
    -- Strategy info
    strategy_id VARCHAR(100),
    strategy_name VARCHAR(255),
    signal_confidence DECIMAL(5, 4), -- 0.0 to 1.0
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    
    -- Raw data
    raw_order_data JSONB,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_trades_agent ON trades(agent_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_created ON trades(created_at);
CREATE INDEX idx_trades_strategy ON trades(strategy_id);
CREATE INDEX idx_trades_exchange ON trades(exchange);

-- Trade execution history for audit
CREATE TABLE trade_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trade_id UUID NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
    execution_type VARCHAR(50) NOT NULL, -- 'fill', 'partial_fill', 'cancel', 'modify'
    amount DECIMAL(36, 18),
    price DECIMAL(36, 18),
    fee DECIMAL(36, 18),
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    raw_data JSONB
);

CREATE INDEX idx_exec_trade ON trade_executions(trade_id);

-- ============================================
-- ARBITRAGE OPPORTUNITIES (High-frequency revenue)
-- ============================================

CREATE TABLE arbitrage_opportunities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    
    -- Opportunity details
    opportunity_type VARCHAR(50) NOT NULL, -- 'cross_exchange', 'triangular', 'defi_yield', 'liquidation'
    symbol VARCHAR(50) NOT NULL,
    
    -- Price information
    buy_exchange VARCHAR(100) NOT NULL,
    buy_price DECIMAL(36, 18) NOT NULL,
    sell_exchange VARCHAR(100) NOT NULL,
    sell_price DECIMAL(36, 18) NOT NULL,
    
    -- Profit calculation
    price_difference_pct DECIMAL(10, 6) NOT NULL, -- Percentage difference
    estimated_profit DECIMAL(36, 18) NOT NULL,
    estimated_profit_usd DECIMAL(18, 2),
    
    -- Requirements
    min_capital_required DECIMAL(36, 18),
    estimated_gas_cost DECIMAL(36, 18),
    estimated_time_ms INTEGER, -- Expected execution time
    
    -- Status
    status VARCHAR(50) DEFAULT 'detected', -- 'detected', 'validating', 'executing', 'executed', 'expired', 'failed'
    executed_trade_id UUID REFERENCES trades(id),
    
    -- Timing (critical for arbitrage)
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE, -- Opportunity expires
    executed_at TIMESTAMP WITH TIME ZONE,
    
    -- Performance tracking
    actual_profit DECIMAL(36, 18),
    slippage DECIMAL(10, 6), -- Actual vs expected
    
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_arb_agent ON arbitrage_opportunities(agent_id);
CREATE INDEX idx_arb_status ON arbitrage_opportunities(status);
CREATE INDEX idx_arb_detected ON arbitrage_opportunities(detected_at);
CREATE INDEX idx_arb_symbol ON arbitrage_opportunities(symbol);

-- ============================================
-- YIELD FARMING & DEFI POSITIONS
-- ============================================

CREATE TABLE yield_positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    
    -- Position details
    protocol VARCHAR(100) NOT NULL, -- 'aave', 'compound', 'curve', 'uniswap', 'lido'
    pool_address VARCHAR(255),
    pool_name VARCHAR(255),
    
    -- Asset info
    asset_symbol VARCHAR(20) NOT NULL,
    asset_address VARCHAR(255),
    
    -- Position amounts
    deposited_amount DECIMAL(36, 18) NOT NULL,
    current_amount DECIMAL(36, 18), -- Including accrued interest
    withdrawn_amount DECIMAL(36, 18) DEFAULT 0,
    
    -- Yield metrics
    entry_apy DECIMAL(10, 6), -- APY when entered
    current_apy DECIMAL(10, 6), -- Current APY
    avg_apy DECIMAL(10, 6), -- Average APY over position lifetime
    
    -- Rewards tracking
    reward_tokens JSONB DEFAULT '[]', -- [{"token": "CRV", "amount": 100.5}]
    claimed_rewards JSONB DEFAULT '[]',
    unclaimed_rewards DECIMAL(36, 18) DEFAULT 0,
    
    -- Position status
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'exiting', 'closed', 'liquidated'
    
    -- Timestamps
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    exited_at TIMESTAMP WITH TIME ZONE,
    last_harvest_at TIMESTAMP WITH TIME ZONE,
    
    -- P&L
    total_yield_earned DECIMAL(36, 18) DEFAULT 0,
    total_fees_paid DECIMAL(36, 18) DEFAULT 0,
    net_profit DECIMAL(36, 18) DEFAULT 0,
    
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_yield_agent ON yield_positions(agent_id);
CREATE INDEX idx_yield_protocol ON yield_positions(protocol);
CREATE INDEX idx_yield_status ON yield_positions(status);
CREATE INDEX idx_yield_asset ON yield_positions(asset_symbol);

-- ============================================
-- TREASURY & WALLET MANAGEMENT
-- ============================================

CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    
    -- Wallet details
    wallet_type VARCHAR(50) NOT NULL, -- 'hot', 'warm', 'cold', 'multisig'
    blockchain VARCHAR(50) NOT NULL, -- 'ethereum', 'bitcoin', 'solana', 'arbitrum'
    address VARCHAR(255) NOT NULL UNIQUE,
    
    -- Security
    encrypted_private_key TEXT, -- Encrypted with KMS
    derivation_path VARCHAR(100),
    
    -- Balance tracking
    native_balance DECIMAL(36, 18),
    native_symbol VARCHAR(20),
    
    -- Limits and config
    daily_limit_usd DECIMAL(18, 2),
    tx_limit_usd DECIMAL(18, 2),
    allowed_tokens JSONB DEFAULT '[]',
    blocked_tokens JSONB DEFAULT '[]',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_monitored BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_wallets_agent ON wallets(agent_id);
CREATE INDEX idx_wallets_blockchain ON wallets(blockchain);
CREATE INDEX idx_wallets_address ON wallets(address);

-- Token balances per wallet
CREATE TABLE token_balances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id UUID NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
    token_symbol VARCHAR(20) NOT NULL,
    token_address VARCHAR(255),
    token_decimals INTEGER DEFAULT 18,
    balance DECIMAL(36, 18) NOT NULL DEFAULT 0,
    balance_usd DECIMAL(18, 2),
    price_usd DECIMAL(18, 8),
    price_updated_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(wallet_id, token_symbol)
);

CREATE INDEX idx_balances_wallet ON token_balances(wallet_id);
CREATE INDEX idx_balances_token ON token_balances(token_symbol);

-- Treasury allocations
CREATE TABLE treasury_allocations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id),
    
    allocation_name VARCHAR(255) NOT NULL,
    strategy_type VARCHAR(100) NOT NULL, -- 'conservative', 'balanced', 'aggressive', 'yield_max'
    
    -- Target allocations (percentages)
    target_cash_pct DECIMAL(5, 2), -- Stablecoins/idle cash
    target_trading_pct DECIMAL(5, 2), -- Active trading capital
    target_yield_pct DECIMAL(5, 2), -- Yield farming
    target_reserve_pct DECIMAL(5, 2), -- Emergency reserve
    
    -- Current allocations
    current_cash_usd DECIMAL(18, 2),
    current_trading_usd DECIMAL(18, 2),
    current_yield_usd DECIMAL(18, 2),
    current_reserve_usd DECIMAL(18, 2),
    total_aum DECIMAL(18, 2), -- Assets under management
    
    -- Rebalancing config
    rebalance_threshold_pct DECIMAL(5, 2) DEFAULT 5.0, -- Rebalance when deviation exceeds this
    auto_rebalance BOOLEAN DEFAULT FALSE,
    
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_treasury_agent ON treasury_allocations(agent_id);

-- ============================================
-- MARKET DATA & SIGNALS
-- ============================================

CREATE TABLE market_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(100) NOT NULL,
    
    -- Price data
    price DECIMAL(36, 18) NOT NULL,
    bid DECIMAL(36, 18),
    ask DECIMAL(36, 18),
    spread DECIMAL(36, 18),
    
    -- Volume
    volume_24h DECIMAL(36, 18),
    volume_base DECIMAL(36, 18),
    
    -- Additional data
    high_24h DECIMAL(36, 18),
    low_24h DECIMAL(36, 18),
    change_24h_pct DECIMAL(10, 6),
    
    -- Orderbook depth
    bid_depth_usd DECIMAL(18, 2),
    ask_depth_usd DECIMAL(18, 2),
    
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    raw_data JSONB,
    
    UNIQUE(symbol, exchange, timestamp)
);

CREATE INDEX idx_market_symbol ON market_data(symbol);
CREATE INDEX idx_market_exchange ON market_data(exchange);
CREATE INDEX idx_market_time ON market_data(timestamp);

-- Trading signals
CREATE TABLE trading_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    
    signal_type VARCHAR(100) NOT NULL, -- 'momentum', 'mean_reversion', 'breakout', 'arbitrage'
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'buy', 'sell', 'neutral'
    
    -- Signal strength
    confidence DECIMAL(5, 4) NOT NULL, -- 0.0 to 1.0
    strength DECIMAL(10, 4), -- Signal strength score
    
    -- Price targets
    entry_price DECIMAL(36, 18),
    target_price DECIMAL(36, 18),
    stop_loss DECIMAL(36, 18),
    
    -- Risk metrics
    risk_reward_ratio DECIMAL(10, 4),
    expected_return_pct DECIMAL(10, 6),
    max_loss_pct DECIMAL(10, 6),
    
    -- Status
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'executed', 'expired', 'cancelled'
    executed_trade_id UUID REFERENCES trades(id),
    
    -- Timing
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE,
    executed_at TIMESTAMP WITH TIME ZONE,
    
    -- Performance
    actual_return_pct DECIMAL(10, 6),
    
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_signals_agent ON trading_signals(agent_id);
CREATE INDEX idx_signals_symbol ON trading_signals(symbol);
CREATE INDEX idx_signals_status ON trading_signals(status);
CREATE INDEX idx_signals_generated ON trading_signals(generated_at);

-- ============================================
-- AGENT PERFORMANCE & REVENUE TRACKING
-- ============================================

CREATE TABLE agent_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    
    -- Time period
    period_type VARCHAR(50) NOT NULL, -- 'hourly', 'daily', 'weekly', 'monthly'
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Trading metrics
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5, 4),
    
    -- P&L
    gross_profit DECIMAL(36, 18) DEFAULT 0,
    gross_loss DECIMAL(36, 18) DEFAULT 0,
    net_profit DECIMAL(36, 18) DEFAULT 0,
    fees_paid DECIMAL(36, 18) DEFAULT 0,
    
    -- Performance ratios
    profit_factor DECIMAL(10, 4), -- Gross profit / Gross loss
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    max_drawdown_pct DECIMAL(10, 6),
    
    -- Capital metrics
    starting_capital DECIMAL(36, 18),
    ending_capital DECIMAL(36, 18),
    return_pct DECIMAL(10, 6),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(agent_id, period_type, period_start)
);

CREATE INDEX idx_perf_agent ON agent_performance(agent_id);
CREATE INDEX idx_perf_period ON agent_performance(period_type, period_start);

-- Revenue streams summary (for business reporting)
CREATE TABLE revenue_streams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stream_type VARCHAR(100) NOT NULL, -- 'trading', 'arbitrage', 'yield_farming', 'liquidations', 'mm'
    
    period_type VARCHAR(50) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Revenue breakdown
    gross_revenue DECIMAL(36, 18) NOT NULL DEFAULT 0,
    operating_costs DECIMAL(36, 18) DEFAULT 0, -- Gas, fees, infra
    net_revenue DECIMAL(36, 18) DEFAULT 0,
    
    -- Detailed breakdown
    trading_pnl DECIMAL(36, 18) DEFAULT 0,
    yield_earned DECIMAL(36, 18) DEFAULT 0,
    arbitrage_profit DECIMAL(36, 18) DEFAULT 0,
    reward_tokens_value DECIMAL(36, 18) DEFAULT 0,
    
    -- Metrics
    trade_count INTEGER DEFAULT 0,
    avg_trade_size DECIMAL(36, 18),
    avg_profit_per_trade DECIMAL(36, 18),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(stream_type, period_type, period_start)
);

CREATE INDEX idx_revenue_stream ON revenue_streams(stream_type);
CREATE INDEX idx_revenue_period ON revenue_streams(period_type, period_start);

-- ============================================
-- AUDIT & COMPLIANCE
-- ============================================

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    
    action_type VARCHAR(100) NOT NULL, -- 'trade', 'withdraw', 'config_change', 'login'
    action_description TEXT,
    
    -- Before/after states for critical changes
    before_state JSONB,
    after_state JSONB,
    
    -- IP and user tracking
    ip_address INET,
    user_agent TEXT,
    
    -- Result
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_agent ON audit_log(agent_id);
CREATE INDEX idx_audit_action ON audit_log(action_type);
CREATE INDEX idx_audit_time ON audit_log(created_at);

-- ============================================
-- VIEWS FOR REPORTING
-- ============================================

-- Daily revenue summary view
CREATE VIEW daily_revenue_summary AS
SELECT 
    DATE_TRUNC('day', period_start) as date,
    stream_type,
    SUM(gross_revenue) as total_gross,
    SUM(net_revenue) as total_net,
    SUM(trade_count) as total_trades
FROM revenue_streams
WHERE period_type = 'daily'
GROUP BY DATE_TRUNC('day', period_start), stream_type;

-- Agent performance leaderboard
CREATE VIEW agent_leaderboard AS
SELECT 
    a.id,
    a.name,
    a.agent_type,
    SUM(ap.net_profit) as total_profit,
    SUM(ap.total_trades) as total_trades,
    AVG(ap.win_rate) as avg_win_rate,
    MAX(ap.period_end) as last_active
FROM agents a
LEFT JOIN agent_performance ap ON a.id = ap.agent_id
WHERE a.status = 'active'
GROUP BY a.id, a.name, a.agent_type
ORDER BY total_profit DESC;

-- Active opportunities view
CREATE VIEW active_arbitrage_opportunities AS
SELECT 
    symbol,
    buy_exchange,
    sell_exchange,
    price_difference_pct,
    estimated_profit_usd,
    valid_until
FROM arbitrage_opportunities
WHERE status = 'detected'
    AND valid_until > NOW()
ORDER BY estimated_profit_usd DESC;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_wallets_updated_at BEFORE UPDATE ON wallets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_yield_positions_updated_at BEFORE UPDATE ON yield_positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
