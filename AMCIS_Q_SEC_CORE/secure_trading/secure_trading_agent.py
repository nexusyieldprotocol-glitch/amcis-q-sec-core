"""
Secure Trading Agent - AMCIS Kernel Integration
===============================================

Single trading agent that communicates exclusively through
the AMCIS security kernel. All operations are encrypted and
audited via the kernel's event system.

Status: PAPER TRADING ONLY - No real capital at risk
"""

import asyncio
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import structlog

# Import from AMCIS core
from core.amcis_kernel import AMCISKernel, SecurityEvent
from crypto.amcis_hybrid_pqc import ProductionCryptoProvider

# Import from secure trading
from .paper_exchange import PaperExchange, OrderSide, OrderType
from .risk_engine import RiskEngine, RiskLimits

logger = structlog.get_logger("amcis.secure_trading")


@dataclass
class TradeSignal:
    """Trading signal from strategy."""
    symbol: str
    side: str  # 'buy' or 'sell'
    amount: Decimal
    confidence: float
    strategy: str
    metadata: Dict[str, Any]


class SecureTradingAgent:
    """
    Secure Trading Agent
    ====================
    
    Single paper trading agent integrated with AMCIS security kernel.
    
    Architecture:
    1. All orders go through RiskEngine
    2. All events are emitted to AMCIS Kernel
    3. All communications are logged via kernel audit trail
    4. Cryptographic identity via ProductionCryptoProvider
    
    NO REAL CAPITAL - Paper trading simulation only.
    """
    
    def __init__(
        self,
        kernel: AMCISKernel,
        name: str = "paper_trader_001",
        initial_balance: Decimal = Decimal('100000'),
        risk_limits: Optional[RiskLimits] = None
    ):
        """
        Initialize secure trading agent.
        
        Args:
            kernel: AMCIS security kernel instance
            name: Agent identifier
            initial_balance: Starting paper money
            risk_limits: Risk configuration
        """
        self.kernel = kernel
        self.name = name
        self.agent_id = f"agent_{name}_{int(time.time())}"
        
        # Initialize crypto identity
        self.crypto = ProductionCryptoProvider()
        self.keypair = self.crypto.generate_keypair()
        
        # Initialize paper exchange
        self.exchange = PaperExchange(initial_balance=initial_balance)
        
        # Initialize risk engine
        self.risk = RiskEngine(limits=risk_limits or RiskLimits())
        
        # Trading state
        self.active = False
        self.trading_pairs = ['BTC-USD', 'ETH-USD']
        self.check_interval = 60  # seconds between trading cycles
        
        # Statistics
        self.cycles_run = 0
        self.signals_generated = 0
        self.orders_placed = 0
        self.trades_executed = 0
        
        self.logger = structlog.get_logger("amcis.secure_trader")
        self.logger.info("secure_trading_agent_initialized",
                        agent_id=self.agent_id,
                        name=name,
                        initial_balance=float(initial_balance))
    
    async def initialize(self):
        """Initialize agent and register with kernel."""
        # Register with kernel
        self.kernel.register_module(self.name, self)
        
        # Emit initialization event
        await self.kernel.emit_event(
            event_type=SecurityEvent.THREAT_INTELLIGENCE,  # Using as audit event
            source_module=self.name,
            severity=1,
            data={
                'event': 'agent_initialized',
                'agent_id': self.agent_id,
                'type': 'paper_trading',
                'public_key_hash': self._get_key_hash()
            }
        )
        
        self.logger.info("agent_registered_with_kernel", agent_id=self.agent_id)
    
    def _get_key_hash(self) -> str:
        """Get hash of public key for identification."""
        import hashlib
        return hashlib.sha3_256(self.keypair.kem_public_bytes).hexdigest()[:16]
    
    async def start(self):
        """Start trading agent."""
        self.active = True
        
        await self.kernel.emit_event(
            event_type=SecurityEvent.THREAT_INTELLIGENCE,
            source_module=self.name,
            severity=1,
            data={'event': 'agent_started', 'agent_id': self.agent_id}
        )
        
        self.logger.info("trading_agent_started")
        
        # Start trading loop
        while self.active:
            try:
                await self._trading_cycle()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                self.logger.error("trading_cycle_error", error=str(e))
                await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Stop trading agent."""
        self.active = False
        
        # Get final summary
        summary = await self.exchange.get_portfolio_summary()
        
        await self.kernel.emit_event(
            event_type=SecurityEvent.THREAT_INTELLIGENCE,
            source_module=self.name,
            severity=1,
            data={
                'event': 'agent_stopped',
                'agent_id': self.agent_id,
                'final_equity': summary['total_equity'],
                'total_pnl': summary['total_pnl'],
                'trades_executed': self.trades_executed
            }
        )
        
        self.logger.info("trading_agent_stopped",
                        final_equity=summary['total_equity'],
                        total_pnl=summary['total_pnl'])
    
    async def _trading_cycle(self):
        """Execute one trading cycle."""
        self.cycles_run += 1
        
        self.logger.debug("trading_cycle_started", cycle=self.cycles_run)
        
        # Update portfolio value for risk tracking
        summary = await self.exchange.get_portfolio_summary()
        self.risk.update_equity(Decimal(str(summary['total_equity'])))
        
        # Check if trading allowed
        if not self.risk.is_trading_allowed():
            self.logger.warning("trading_disabled_by_risk_engine")
            return
        
        # Generate signals for each pair
        for symbol in self.trading_pairs:
            signal = await self._generate_signal(symbol)
            
            if signal:
                self.signals_generated += 1
                await self._process_signal(signal)
        
        self.logger.debug("trading_cycle_completed", cycle=self.cycles_run)
    
    async def _generate_signal(self, symbol: str) -> Optional[TradeSignal]:
        """
        Generate trading signal for symbol.
        
        Uses a simple mean-reversion strategy for demonstration.
        
        Args:
            symbol: Trading pair
            
        Returns:
            TradeSignal or None
        """
        # Get current price
        price = await self.exchange.get_price(symbol)
        if not price:
            return None
        
        # Simple strategy: Check if we have position
        position = await self.exchange.get_position(symbol)
        
        if position:
            # Check if we should sell (take profit or stop loss)
            current_value = position.amount * price
            entry_value = position.amount * position.avg_entry_price
            pnl_pct = (current_value - entry_value) / entry_value
            
            if pnl_pct > Decimal('0.05'):  # 5% profit
                return TradeSignal(
                    symbol=symbol,
                    side='sell',
                    amount=position.amount,
                    confidence=0.7,
                    strategy='take_profit',
                    metadata={'pnl_pct': float(pnl_pct)}
                )
            
            if pnl_pct < Decimal('-0.02'):  # 2% loss
                return TradeSignal(
                    symbol=symbol,
                    side='sell',
                    amount=position.amount,
                    confidence=0.8,
                    strategy='stop_loss',
                    metadata={'pnl_pct': float(pnl_pct)}
                )
        else:
            # No position - check if we should buy
            # Simple: Buy with small amount if we have cash
            portfolio = await self.exchange.get_portfolio_summary()
            
            if Decimal(str(portfolio['cash'])) > Decimal('1000'):
                # Calculate position size (fixed $1000 for paper trading)
                amount = Decimal('1000') / price
                
                return TradeSignal(
                    symbol=symbol,
                    side='buy',
                    amount=amount,
                    confidence=0.6,
                    strategy='entry',
                    metadata={'entry_price': float(price)}
                )
        
        return None
    
    async def _process_signal(self, signal: TradeSignal):
        """
        Process trading signal through risk engine and execute.
        
        Args:
            signal: Trading signal to process
        """
        # Get current price
        price = await self.exchange.get_price(signal.symbol)
        if not price:
            return
        
        # Check risk limits
        portfolio = await self.exchange.get_portfolio_summary()
        positions = await self.exchange.get_all_positions()
        
        risk_check = self.risk.check_order(
            symbol=signal.symbol,
            side=signal.side,
            amount=signal.amount,
            price=price,
            portfolio_value=Decimal(str(portfolio['total_equity'])),
            current_positions=len(positions)
        )
        
        if not risk_check:
            self.logger.warning("risk_check_failed",
                              symbol=signal.symbol,
                              reason=risk_check.reason)
            
            await self.kernel.emit_event(
                event_type=SecurityEvent.POLICY_VIOLATION,
                source_module=self.name,
                severity=5,
                data={
                    'event': 'risk_check_failed',
                    'signal': signal.__dict__,
                    'reason': risk_check.reason
                }
            )
            return
        
        # Execute order
        await self._execute_order(signal, price)
    
    async def _execute_order(self, signal: TradeSignal, price: Decimal):
        """
        Execute order on paper exchange.
        
        Args:
            signal: Trading signal
            price: Execution price
        """
        try:
            # Map side
            side = OrderSide.BUY if signal.side == 'buy' else OrderSide.SELL
            
            # Place order
            order = await self.exchange.place_order(
                symbol=signal.symbol,
                side=side,
                amount=signal.amount,
                order_type=OrderType.MARKET
            )
            
            self.orders_placed += 1
            
            if order.filled_price:
                self.trades_executed += 1
                
                # Calculate P&L for sells
                if signal.side == 'sell':
                    # Get position to calculate P&L
                    position = await self.exchange.get_position(signal.symbol)
                    if position:
                        pnl = position.realized_pnl
                        self.risk.update_pnl(pnl)
                
                # Emit execution event to kernel
                await self.kernel.emit_event(
                    event_type=SecurityEvent.THREAT_INTELLIGENCE,
                    source_module=self.name,
                    severity=2,
                    data={
                        'event': 'order_executed',
                        'order_id': order.id,
                        'symbol': signal.symbol,
                        'side': signal.side,
                        'amount': float(signal.amount),
                        'price': float(order.filled_price),
                        'strategy': signal.strategy
                    }
                )
                
                self.logger.info("order_executed",
                               order_id=order.id,
                               symbol=signal.symbol,
                               side=signal.side,
                               amount=float(signal.amount),
                               price=float(order.filled_price))
            
        except Exception as e:
            self.logger.error("order_execution_failed", error=str(e))
            
            await self.kernel.emit_event(
                event_type=SecurityEvent.INTEGRITY_VIOLATION,
                source_module=self.name,
                severity=6,
                data={
                    'event': 'order_execution_failed',
                    'error': str(e),
                    'signal': signal.__dict__
                }
            )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        portfolio = await self.exchange.get_portfolio_summary()
        risk_status = self.risk.get_status()
        
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'active': self.active,
            'cycles_run': self.cycles_run,
            'signals_generated': self.signals_generated,
            'orders_placed': self.orders_placed,
            'trades_executed': self.trades_executed,
            'portfolio': portfolio,
            'risk': risk_status,
            'public_key_hash': self._get_key_hash()
        }
