#!/usr/bin/env python3
"""
AMCIS Financial AI Agent System Launcher
Quick start script for the revenue-generating agent system
"""

import asyncio
import logging
import sys
import signal
from contextlib import asynccontextmanager

from core.agent_base import get_message_bus
from core.treasury import TreasuryManager
from agents.trading_agent import TradingAgent
from agents.arbitrage_agent import ArbitrageAgent
from agents.yield_agent import YieldAgent
from agents.market_analyzer import MarketAnalysisSwarm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FinanceAgentSystem:
    """Main system orchestrator"""
    
    def __init__(self):
        self.message_bus = None
        self.treasury = None
        self.trading_agent = None
        self.arbitrage_agent = None
        self.yield_agent = None
        self.market_swarm = None
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("🚀 Initializing AMCIS Financial Agent System...")
        
        # Message bus
        self.message_bus = get_message_bus()
        await self.message_bus.start()
        logger.info("✅ Message bus started")
        
        # Treasury
        self.treasury = TreasuryManager("MainTreasury", self.message_bus, {
            'strategy': 'balanced',
            'max_daily_drawdown': 0.05,
            'emergency_reserve': 0.10
        })
        await self.treasury.initialize()
        logger.info("✅ Treasury initialized")
        
        # Trading agent
        self.trading_agent = TradingAgent("AlphaTrader", self.message_bus, {
            'exchanges': ['binance', 'coinbase'],
            'pairs': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD'],
            'max_position_size': 50000,
            'active_strategies': ['momentum', 'mean_reversion', 'breakout'],
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.06,
            'max_positions': 10
        })
        await self.trading_agent.initialize()
        logger.info("✅ Trading agent initialized")
        
        # Arbitrage agent
        self.arbitrage_agent = ArbitrageAgent("ArbHunter", self.message_bus, {
            'exchanges': ['binance', 'coinbase', 'kraken', 'uniswap_v3'],
            'symbols': ['BTC-USD', 'ETH-USD', 'ETH-USDC', 'WBTC-ETH'],
            'min_profit_usd': 25,
            'min_profit_pct': 0.001,
            'max_trade_size': 100000
        })
        await self.arbitrage_agent.initialize()
        logger.info("✅ Arbitrage agent initialized")
        
        # Yield agent
        self.yield_agent = YieldAgent("YieldMaster", self.message_bus, {
            'strategy': 'balanced',
            'protocols': ['aave_v3', 'compound_v3', 'curve', 'lido', 'convex'],
            'assets': ['USDC', 'USDT', 'DAI', 'ETH', 'stETH'],
            'rebalance_threshold': 0.02,
            'harvest_threshold': 100
        })
        await self.yield_agent.initialize()
        logger.info("✅ Yield agent initialized")
        
        # Market analysis swarm
        self.market_swarm = MarketAnalysisSwarm("MarketIntel", self.message_bus)
        await self.market_swarm.initialize({
            'technical': {
                'timeframes': ['1h', '4h', '1d'],
                'symbols': ['BTC-USD', 'ETH-USD', 'SOL-USD']
            },
            'sentiment': {
                'symbols': ['BTC', 'ETH', 'SOL'],
                'sources': ['twitter', 'news', 'onchain']
            }
        })
        logger.info("✅ Market analysis swarm initialized")
        
        logger.info("✨ System initialization complete!")
        
    async def start(self):
        """Start all agents"""
        logger.info("▶️  Starting all agents...")
        
        await self.treasury.start()
        await self.trading_agent.start()
        await self.arbitrage_agent.start()
        await self.yield_agent.start()
        await self.market_swarm.start()
        
        logger.info("🟢 All agents running!")
        logger.info("")
        logger.info("📊 Revenue streams active:")
        logger.info("   • Trading Agent: Momentum, Mean Reversion, Breakout strategies")
        logger.info("   • Arbitrage Agent: Cross-exchange and triangular arbitrage")
        logger.info("   • Yield Agent: DeFi lending, liquidity mining, staking")
        logger.info("   • Market Intelligence: Multi-factor signal generation")
        logger.info("")
        logger.info("💰 Treasury management: Balanced strategy")
        logger.info("🛡️  Risk controls: 5% daily loss limit, 10% emergency reserve")
        logger.info("")
        logger.info("Press Ctrl+C to shutdown gracefully")
        
    async def stop(self):
        """Stop all agents"""
        logger.info("🛑 Shutting down...")
        
        await self.market_swarm.stop()
        await self.yield_agent.stop()
        await self.arbitrage_agent.stop()
        await self.trading_agent.stop()
        await self.treasury.stop()
        await self.message_bus.stop()
        
        logger.info("✅ Shutdown complete")
        
    async def print_stats(self):
        """Print periodic statistics"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=60)
            except asyncio.TimeoutError:
                # Print stats every minute
                total_profit = (
                    self.trading_agent.metrics.profit +
                    self.arbitrage_agent.metrics.profit +
                    self.yield_agent.metrics.profit
                )
                
                logger.info("")
                logger.info("📈 PERFORMANCE SNAPSHOT")
                logger.info(f"   Total Profit: ${total_profit:,.2f}")
                logger.info(f"   Trading: ${self.trading_agent.metrics.profit:,.2f} ({self.trading_agent.metrics.trades_executed} trades)")
                logger.info(f"   Arbitrage: ${self.arbitrage_agent.metrics.profit:,.2f} ({self.arbitrage_agent.total_opportunities_executed} ops)")
                logger.info(f"   Yield: ${self.yield_agent.metrics.profit:,.2f} ({len(self.yield_agent.positions)} positions)")
                logger.info("")
                
    async def run(self):
        """Main run loop"""
        try:
            await self.initialize()
            await self.start()
            
            # Start stats printer
            stats_task = asyncio.create_task(self.print_stats())
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
            stats_task.cancel()
            try:
                await stats_task
            except asyncio.CancelledError:
                pass
                
        except Exception as e:
            logger.exception(f"System error: {e}")
        finally:
            await self.stop()
            
    def signal_handler(self, sig):
        """Handle shutdown signals"""
        logger.info(f"Received signal {sig}")
        self._shutdown_event.set()


async def main():
    """Main entry point"""
    system = FinanceAgentSystem()
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: system.signal_handler(s))
    
    await system.run()


if __name__ == "__main__":
    asyncio.run(main())
