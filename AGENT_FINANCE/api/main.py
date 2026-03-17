"""
AMCIS Financial AI Agent API
Revenue-generating trading and DeFi operations API
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import time

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import agent components
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent_base import get_message_bus, MessageBus, AgentState
from core.treasury import TreasuryManager, AllocationStrategy
from agents.trading_agent import TradingAgent
from agents.arbitrage_agent import ArbitrageAgent
from agents.yield_agent import YieldAgent, YieldStrategy
from agents.market_analyzer import MarketAnalysisSwarm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
message_bus: MessageBus = None
treasury: TreasuryManager = None
trading_agent: TradingAgent = None
arbitrage_agent: ArbitrageAgent = None
yield_agent: YieldAgent = None
market_swarm: MarketAnalysisSwarm = None

system_started = False


# ========== Pydantic Models ==========

class AgentCreateRequest(BaseModel):
    name: str
    agent_type: str = Field(..., description="Type: trading, arbitrage, yield, analyzer")
    config: Dict = Field(default_factory=dict)


class AgentResponse(BaseModel):
    id: str
    name: str
    type: str
    status: str
    metrics: Dict
    uptime: float


class TradeRequest(BaseModel):
    symbol: str
    side: str = Field(..., description="buy or sell")
    amount: float
    order_type: str = Field(default="market", description="market, limit, stop")
    price: Optional[float] = None
    strategy: str = "manual"


class TradeResponse(BaseModel):
    trade_id: str
    status: str
    symbol: str
    side: str
    amount: float
    executed_price: Optional[float]
    fee: float
    timestamp: float


class TreasuryStatus(BaseModel):
    total_aum: float
    daily_revenue: float
    daily_costs: float
    daily_pnl: float
    strategy: str
    allocations: Dict[str, float]
    agent_allocations: Dict[str, float]


class YieldPoolInfo(BaseModel):
    protocol: str
    name: str
    asset: str
    total_apy: float
    tvl_usd: float
    risk_score: float


class ArbitrageOpportunity(BaseModel):
    id: str
    symbol: str
    buy_exchange: str
    sell_exchange: str
    profit_pct: float
    net_profit_usd: float
    confidence: float


class SignalResponse(BaseModel):
    symbol: str
    consensus: str
    confidence: float
    action: str
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_score: float


class PerformanceMetrics(BaseModel):
    total_revenue: float
    total_costs: float
    net_profit: float
    win_rate: float
    trades_executed: int
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]


# ========== Lifespan Management ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global system_started, message_bus, treasury, trading_agent, arbitrage_agent, yield_agent, market_swarm
    
    logger.info("Starting AMCIS Financial Agent System...")
    
    # Initialize message bus
    message_bus = get_message_bus()
    await message_bus.start()
    
    # Initialize treasury
    treasury = TreasuryManager("TreasuryManager", message_bus, {
        'strategy': 'balanced',
        'max_daily_drawdown': 0.05
    })
    await treasury.initialize()
    
    # Initialize trading agent
    trading_agent = TradingAgent("PrimaryTrader", message_bus, {
        'exchanges': ['binance', 'coinbase'],
        'pairs': ['BTC-USD', 'ETH-USD', 'SOL-USD'],
        'max_position_size': 10000,
        'active_strategies': ['momentum', 'mean_reversion'],
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.06
    })
    await trading_agent.initialize()
    
    # Initialize arbitrage agent
    arbitrage_agent = ArbitrageAgent("ArbitrageBot", message_bus, {
        'exchanges': ['binance', 'coinbase', 'kraken', 'uniswap_v3'],
        'symbols': ['BTC-USD', 'ETH-USD', 'ETH-USDC'],
        'min_profit_usd': 10,
        'max_trade_size': 50000
    })
    await arbitrage_agent.initialize()
    
    # Initialize yield agent
    yield_agent = YieldAgent("YieldOptimizer", message_bus, {
        'strategy': 'balanced',
        'protocols': ['aave_v3', 'compound_v3', 'curve', 'lido'],
        'assets': ['USDC', 'USDT', 'DAI', 'ETH'],
        'rebalance_threshold': 0.02
    })
    await yield_agent.initialize()
    
    # Initialize market analysis swarm
    market_swarm = MarketAnalysisSwarm("MarketIntelligence", message_bus)
    await market_swarm.initialize({
        'technical': {
            'timeframes': ['1h', '4h', '1d'],
            'symbols': ['BTC-USD', 'ETH-USD']
        },
        'sentiment': {
            'symbols': ['BTC', 'ETH'],
            'sources': ['twitter', 'news', 'onchain']
        }
    })
    
    # Start all agents
    await trading_agent.start()
    await arbitrage_agent.start()
    await yield_agent.start()
    await market_swarm.start()
    await treasury.start()
    
    system_started = True
    logger.info("AMCIS Financial Agent System started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AMCIS Financial Agent System...")
    system_started = False
    
    await treasury.stop()
    await market_swarm.stop()
    await yield_agent.stop()
    await arbitrage_agent.stop()
    await trading_agent.stop()
    await message_bus.stop()
    
    logger.info("Shutdown complete")


app = FastAPI(
    title="AMCIS Financial AI Agent API",
    description="Autonomous revenue-generating AI agents for trading, arbitrage, and yield optimization",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== API Endpoints ==========

@app.get("/")
async def root():
    """API status"""
    return {
        "name": "AMCIS Financial AI Agent API",
        "version": "1.0.0",
        "status": "running" if system_started else "initializing",
        "agents": {
            "trading": trading_agent.get_status() if trading_agent else None,
            "arbitrage": arbitrage_agent.get_status() if arbitrage_agent else None,
            "yield": yield_agent.get_status() if yield_agent else None,
        }
    }


# ----- Agent Management -----

@app.get("/agents", response_model=List[AgentResponse])
async def list_agents():
    """List all active agents"""
    agents = []
    
    if trading_agent:
        agents.append(AgentResponse(**trading_agent.get_status()))
    if arbitrage_agent:
        agents.append(AgentResponse(**arbitrage_agent.get_status()))
    if yield_agent:
        agents.append(AgentResponse(**yield_agent.get_status()))
        
    return agents


@app.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get specific agent status"""
    for agent in [trading_agent, arbitrage_agent, yield_agent]:
        if agent and agent.id == agent_id:
            return AgentResponse(**agent.get_status())
    
    raise HTTPException(status_code=404, detail="Agent not found")


@app.post("/agents/{agent_id}/pause")
async def pause_agent(agent_id: str):
    """Pause an agent"""
    for agent in [trading_agent, arbitrage_agent, yield_agent]:
        if agent and agent.id == agent_id:
            await agent.pause()
            return {"status": "paused", "agent_id": agent_id}
    
    raise HTTPException(status_code=404, detail="Agent not found")


@app.post("/agents/{agent_id}/resume")
async def resume_agent(agent_id: str):
    """Resume a paused agent"""
    for agent in [trading_agent, arbitrage_agent, yield_agent]:
        if agent and agent.id == agent_id:
            await agent.resume()
            return {"status": "resumed", "agent_id": agent_id}
    
    raise HTTPException(status_code=404, detail="Agent not found")


@app.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Stop an agent"""
    for agent in [trading_agent, arbitrage_agent, yield_agent]:
        if agent and agent.id == agent_id:
            await agent.stop()
            return {"status": "stopped", "agent_id": agent_id}
    
    raise HTTPException(status_code=404, detail="Agent not found")


# ----- Trading Operations -----

@app.post("/trades", response_model=TradeResponse)
async def execute_trade(trade: TradeRequest):
    """Execute a manual trade"""
    if not trading_agent or trading_agent.state != AgentState.RUNNING:
        raise HTTPException(status_code=503, detail="Trading agent not available")
    
    trade_id = f"manual_{int(time.time()*1000)}"
    
    # Send trade to agent
    await message_bus.publish({
        'sender_id': 'api',
        'recipient_id': trading_agent.id,
        'message_type': 'trade.execute',
        'payload': {
            'order_id': trade_id,
            'order': {
                'symbol': trade.symbol,
                'side': trade.side,
                'amount': trade.amount,
                'order_type': trade.order_type,
                'price': trade.price,
                'strategy': trade.strategy
            }
        },
        'timestamp': time.time(),
        'priority': 4  # CRITICAL
    })
    
    return TradeResponse(
        trade_id=trade_id,
        status="submitted",
        symbol=trade.symbol,
        side=trade.side,
        amount=trade.amount,
        executed_price=None,
        fee=0.0,
        timestamp=time.time()
    )


@app.get("/trades")
async def list_trades(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000)
):
    """List recent trades"""
    # Would query database
    return {
        "trades": [],
        "total": 0,
        "symbol": symbol,
        "status": status
    }


@app.get("/positions")
async def list_positions():
    """List open positions"""
    if not trading_agent:
        return {"positions": []}
    
    positions = []
    for pos_id, pos in trading_agent.positions.items():
        positions.append({
            "id": pos_id,
            "symbol": pos.symbol,
            "side": pos.side,
            "entry_price": float(pos.entry_price),
            "amount": float(pos.amount),
            "unrealized_pnl": float(pos.unrealized_pnl),
            "stop_loss": float(pos.stop_loss) if pos.stop_loss else None,
            "take_profit": float(pos.take_profit) if pos.take_profit else None,
            "opened_at": pos.opened_at
        })
    
    return {"positions": positions, "count": len(positions)}


# ----- Treasury Management -----

@app.get("/treasury", response_model=TreasuryStatus)
async def get_treasury_status():
    """Get treasury status and allocations"""
    if not treasury:
        raise HTTPException(status_code=503, detail="Treasury not available")
    
    return TreasuryStatus(
        total_aum=float(treasury.total_aum),
        daily_revenue=float(treasury.daily_revenue),
        daily_costs=float(treasury.daily_costs),
        daily_pnl=float(treasury.daily_revenue - treasury.daily_costs),
        strategy=treasury.strategy.value,
        allocations={
            "trading": float(treasury.target_allocation.trading_pct),
            "yield": float(treasury.target_allocation.yield_farming_pct),
            "arbitrage": float(treasury.target_allocation.arbitrage_pct),
            "reserve": float(treasury.target_allocation.reserve_pct)
        },
        agent_allocations={k: float(v) for k, v in treasury.agent_allocations.items()}
    )


@app.post("/treasury/strategy/{strategy}")
async def set_treasury_strategy(strategy: str):
    """Update treasury allocation strategy"""
    if not treasury:
        raise HTTPException(status_code=503, detail="Treasury not available")
    
    try:
        new_strategy = AllocationStrategy(strategy)
        treasury.strategy = new_strategy
        treasury.target_allocation = treasury._get_allocation_for_strategy(new_strategy)
        
        return {
            "status": "updated",
            "strategy": strategy,
            "allocations": {
                "trading": float(treasury.target_allocation.trading_pct),
                "yield": float(treasury.target_allocation.yield_farming_pct),
                "arbitrage": float(treasury.target_allocation.arbitrage_pct),
                "reserve": float(treasury.target_allocation.reserve_pct)
            }
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")


@app.post("/treasury/rebalance")
async def trigger_rebalance():
    """Manually trigger portfolio rebalancing"""
    if not treasury:
        raise HTTPException(status_code=503, detail="Treasury not available")
    
    await treasury._rebalance_allocations()
    return {"status": "rebalancing_triggered"}


# ----- Arbitrage -----

@app.get("/arbitrage/opportunities", response_model=List[ArbitrageOpportunity])
async def list_arbitrage_opportunities(
    min_profit: float = Query(0.0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """List current arbitrage opportunities"""
    if not arbitrage_agent:
        return []
    
    opportunities = []
    for opp in arbitrage_agent.active_opportunities.values():
        if float(opp.net_profit) >= min_profit:
            opportunities.append(ArbitrageOpportunity(
                id=opp.id,
                symbol=opp.symbol,
                buy_exchange=opp.buy_exchange,
                sell_exchange=opp.sell_exchange,
                profit_pct=float(opp.profit_pct) * 100,
                net_profit_usd=float(opp.net_profit),
                confidence=opp.confidence
            ))
    
    # Sort by profit
    opportunities.sort(key=lambda x: x.net_profit_usd, reverse=True)
    return opportunities[:limit]


@app.post("/arbitrage/execute/{opportunity_id}")
async def execute_arbitrage(opportunity_id: str):
    """Manually execute a specific arbitrage opportunity"""
    if not arbitrage_agent:
        raise HTTPException(status_code=503, detail="Arbitrage agent not available")
    
    if opportunity_id not in arbitrage_agent.active_opportunities:
        raise HTTPException(status_code=404, detail="Opportunity not found or expired")
    
    opp = arbitrage_agent.active_opportunities[opportunity_id]
    
    # Execute
    success = await arbitrage_agent._execute_arbitrage(opp)
    
    return {
        "opportunity_id": opportunity_id,
        "executed": success,
        "status": opp.status,
        "profit": float(opp.actual_profit) if opp.actual_profit else None
    }


# ----- Yield Farming -----

@app.get("/yield/pools", response_model=List[YieldPoolInfo])
async def list_yield_pools(
    protocol: Optional[str] = None,
    asset: Optional[str] = None,
    min_apy: float = Query(0.0, ge=0)
):
    """List available yield farming pools"""
    if not yield_agent:
        return []
    
    pools = []
    for pool in yield_agent.pools.values():
        if protocol and pool.protocol != protocol:
            continue
        if asset and pool.asset != asset:
            continue
        if float(pool.total_apy) < min_apy:
            continue
        
        pools.append(YieldPoolInfo(
            protocol=pool.protocol,
            name=pool.name,
            asset=pool.asset,
            total_apy=float(pool.total_apy) * 100,
            tvl_usd=float(pool.tvl_usd),
            risk_score=0.5  # Would calculate properly
        ))
    
    return pools


@app.get("/yield/positions")
async def list_yield_positions():
    """List active yield farming positions"""
    if not yield_agent:
        return {"positions": []}
    
    positions = []
    for pos_id, pos in yield_agent.positions.items():
        positions.append({
            "id": pos_id,
            "protocol": pos.pool.protocol,
            "pool": pos.pool.name,
            "asset": pos.pool.asset,
            "deposited": float(pos.deposited_amount),
            "current_value": float(pos.calculate_current_value()),
            "total_yield": float(pos.total_yield_earned),
            "apy": float(pos.current_apy) * 100,
            "time_in_pool_hours": pos.time_in_pool_hours
        })
    
    return {"positions": positions, "total_value": float(yield_agent.total_current_value)}


@app.post("/yield/harvest")
async def harvest_all_rewards():
    """Harvest rewards from all positions"""
    if not yield_agent:
        raise HTTPException(status_code=503, detail="Yield agent not available")
    
    await yield_agent._harvest_rewards()
    return {"status": "harvest_triggered"}


# ----- Market Signals -----

@app.get("/signals/{symbol}", response_model=SignalResponse)
async def get_signal(symbol: str):
    """Get aggregated trading signal for a symbol"""
    # Would get from market analysis swarm
    return SignalResponse(
        symbol=symbol,
        consensus="NEUTRAL",
        confidence=0.5,
        action="hold",
        entry_price=None,
        stop_loss=None,
        take_profit=None,
        risk_score=50.0
    )


@app.get("/signals")
async def list_signals(
    symbols: Optional[str] = Query(None, description="Comma-separated symbols"),
    min_confidence: float = Query(0.5, ge=0, le=1)
):
    """List trading signals for multiple symbols"""
    symbol_list = symbols.split(",") if symbols else ["BTC-USD", "ETH-USD"]
    
    signals = []
    for symbol in symbol_list:
        signals.append({
            "symbol": symbol,
            "signal": "NEUTRAL",
            "confidence": 0.5,
            "action": "hold"
        })
    
    return {"signals": signals}


# ----- Performance & Analytics -----

@app.get("/performance", response_model=PerformanceMetrics)
async def get_performance(
    period: str = Query("1d", description="1h, 1d, 7d, 30d")
):
    """Get system performance metrics"""
    # Aggregate from all agents
    total_revenue = Decimal('0')
    total_costs = Decimal('0')
    total_trades = 0
    winning_trades = 0
    
    for agent in [trading_agent, arbitrage_agent, yield_agent]:
        if agent:
            total_revenue += Decimal(str(agent.metrics.total_revenue))
            total_costs += Decimal(str(agent.metrics.total_costs))
            total_trades += agent.metrics.trades_executed
            winning_trades += agent.metrics.successful_trades
    
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    return PerformanceMetrics(
        total_revenue=float(total_revenue),
        total_costs=float(total_costs),
        net_profit=float(total_revenue - total_costs),
        win_rate=win_rate,
        trades_executed=total_trades,
        sharpe_ratio=None,
        max_drawdown=None
    )


@app.get("/performance/agents")
async def get_agent_performance():
    """Get performance breakdown by agent"""
    performance = []
    
    for agent in [trading_agent, arbitrage_agent, yield_agent]:
        if agent:
            performance.append({
                "agent_id": agent.id,
                "name": agent.name,
                "type": agent.agent_type,
                "revenue": agent.metrics.total_revenue,
                "costs": agent.metrics.total_costs,
                "profit": agent.metrics.profit,
                "trades": agent.metrics.trades_executed,
                "win_rate": agent.metrics.win_rate
            })
    
    return {"agents": performance}


@app.get("/performance/revenue")
async def get_revenue_breakdown(
    period: str = Query("1d", description="1h, 1d, 7d, 30d")
):
    """Get revenue breakdown by source"""
    return {
        "period": period,
        "breakdown": {
            "trading": 0.0,
            "arbitrage": 0.0,
            "yield_farming": 0.0,
            "total": 0.0
        }
    }


# ----- Emergency Controls -----

@app.post("/emergency/stop-all")
async def emergency_stop():
    """Emergency stop all trading activity"""
    await message_bus.publish({
        'sender_id': 'api',
        'message_type': 'risk.stop_trading',
        'payload': {'broadcast': True, 'reason': 'emergency_api_stop'},
        'timestamp': time.time(),
        'priority': 4  # CRITICAL
    })
    
    return {
        "status": "emergency_stop_triggered",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/emergency/liquidate-all")
async def emergency_liquidate():
    """Emergency liquidation of all positions"""
    if trading_agent:
        for pos_id, pos in list(trading_agent.positions.items()):
            current_price = await trading_agent._get_current_price(pos.symbol)
            if current_price:
                await trading_agent._close_position(pos_id, current_price, 'emergency_liquidate')
    
    return {
        "status": "emergency_liquidation_completed",
        "timestamp": datetime.utcnow().isoformat()
    }


# ----- WebSocket Support (for real-time updates) -----

@app.get("/ws/trades")
async def websocket_trades():
    """WebSocket endpoint for real-time trade updates"""
    # Would implement WebSocket handler
    return {"note": "WebSocket support available at /ws/trades"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
