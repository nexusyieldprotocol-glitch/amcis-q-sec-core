"""
AMCIS Risk Manager - Position Limits, Stop Losses, Risk Controls
Prevents catastrophic losses and enforces trading limits
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class RiskLimit:
    name: str
    current: Decimal
    limit: Decimal
    exceeded: bool


@dataclass
class PositionRisk:
    symbol: str
    size: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    pnl_pct: Decimal
    stop_loss_triggered: bool


class RiskManager:
    """
    Centralized risk management system
    Enforces position limits, stop losses, and daily loss limits
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Position limits
        self.max_position_size = Decimal(str(config.get('max_position_size', 100000)))  # USD
        self.max_position_pct = Decimal(str(config.get('max_position_pct', 0.1)))  # 10% of portfolio
        self.max_orders_per_minute = config.get('max_orders_per_minute', 60)
        
        # Loss limits
        self.daily_loss_limit = Decimal(str(config.get('daily_loss_limit', 5000)))
        self.stop_loss_pct = Decimal(str(config.get('stop_loss_pct', 0.02)))
        self.take_profit_pct = Decimal(str(config.get('take_profit_pct', 0.06)))
        
        # Circuit breakers
        self.circuit_breaker_enabled = config.get('circuit_breaker_enabled', True)
        self.circuit_breaker_threshold = Decimal(str(config.get('circuit_breaker_threshold', 0.05)))
        self.circuit_breaker_cooldown = config.get('circuit_breaker_cooldown', 3600)  # 1 hour
        
        # State
        self.daily_pnl = Decimal('0')
        self.daily_trades = 0
        self.last_reset = time.time()
        self.circuit_breaker_triggered = False
        self.circuit_breaker_until = 0
        
        # Order tracking for rate limiting
        self.order_history: List[float] = []
        
        # Position risks
        self.position_risks: Dict[str, PositionRisk] = {}
        
        # Callbacks
        self.on_stop_loss: Optional[callable] = None
        self.on_take_profit: Optional[callable] = None
        self.on_circuit_breaker: Optional[callable] = None
        
    async def check_order(self, symbol: str, side: str, amount: Decimal,
                         price: Decimal, portfolio_value: Decimal) -> Dict:
        """
        Check if order passes all risk checks
        Returns: {'allowed': bool, 'reason': str}
        """
        # Reset daily counters if needed
        await self._reset_daily_counters()
        
        # Check circuit breaker
        if await self._check_circuit_breaker():
            return {'allowed': False, 'reason': 'Circuit breaker active'}
            
        # Check rate limit
        if not await self._check_rate_limit():
            return {'allowed': False, 'reason': 'Rate limit exceeded'}
            
        # Check position size
        order_value = amount * price
        if order_value > self.max_position_size:
            return {'allowed': False, 'reason': f'Position size {order_value} exceeds limit {self.max_position_size}'}
            
        # Check portfolio concentration
        if order_value > portfolio_value * self.max_position_pct:
            return {'allowed': False, 'reason': 'Position would exceed portfolio concentration limit'}
            
        # Check daily loss limit
        if self.daily_pnl < -self.daily_loss_limit:
            return {'allowed': False, 'reason': 'Daily loss limit reached'}
            
        return {'allowed': True, 'reason': 'OK'}
        
    async def update_position(self, symbol: str, size: Decimal, 
                             entry_price: Decimal, current_price: Decimal):
        """Update position and check risk triggers"""
        pnl = (current_price - entry_price) * size if size > 0 else (entry_price - current_price) * abs(size)
        pnl_pct = pnl / (entry_price * abs(size)) if entry_price and size else Decimal('0')
        
        risk = PositionRisk(
            symbol=symbol,
            size=size,
            entry_price=entry_price,
            current_price=current_price,
            unrealized_pnl=pnl,
            pnl_pct=pnl_pct,
            stop_loss_triggered=False
        )
        
        self.position_risks[symbol] = risk
        
        # Check stop loss
        if pnl_pct < -self.stop_loss_pct:
            risk.stop_loss_triggered = True
            logger.warning(f"Stop loss triggered for {symbol}: {pnl_pct:.2%}")
            if self.on_stop_loss:
                await self.on_stop_loss(symbol, risk)
                
        # Check take profit
        elif pnl_pct > self.take_profit_pct:
            logger.info(f"Take profit triggered for {symbol}: {pnl_pct:.2%}")
            if self.on_take_profit:
                await self.on_take_profit(symbol, risk)
                
    async def record_trade(self, symbol: str, realized_pnl: Decimal):
        """Record completed trade P&L"""
        self.daily_pnl += realized_pnl
        self.daily_trades += 1
        
        # Check if circuit breaker should trigger
        portfolio_value = await self._get_portfolio_value()
        if portfolio_value > 0 and self.daily_pnl < -portfolio_value * self.circuit_breaker_threshold:
            await self._trigger_circuit_breaker()
            
    async def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is active"""
        if not self.circuit_breaker_triggered:
            return False
            
        if time.time() > self.circuit_breaker_until:
            logger.info("Circuit breaker expired, resuming trading")
            self.circuit_breaker_triggered = False
            return False
            
        return True
        
    async def _trigger_circuit_breaker(self):
        """Trigger circuit breaker"""
        if not self.circuit_breaker_enabled:
            return
            
        self.circuit_breaker_triggered = True
        self.circuit_breaker_until = time.time() + self.circuit_breaker_cooldown
        
        logger.critical(f"CIRCUIT BREAKER TRIGGERED! Daily loss: {self.daily_pnl}")
        
        if self.on_circuit_breaker:
            await self.on_circuit_breaker(self.daily_pnl)
            
    async def _check_rate_limit(self) -> bool:
        """Check order rate limit"""
        now = time.time()
        
        # Remove orders older than 1 minute
        self.order_history = [t for t in self.order_history if now - t < 60]
        
        if len(self.order_history) >= self.max_orders_per_minute:
            return False
            
        self.order_history.append(now)
        return True
        
    async def _reset_daily_counters(self):
        """Reset daily counters"""
        if time.time() - self.last_reset > 86400:  # 24 hours
            self.daily_pnl = Decimal('0')
            self.daily_trades = 0
            self.last_reset = time.time()
            self.circuit_breaker_triggered = False
            logger.info("Daily counters reset")
            
    async def _get_portfolio_value(self) -> Decimal:
        """Get current portfolio value"""
        # Would query portfolio manager
        return Decimal('100000')  # Placeholder
        
    def get_risk_summary(self) -> Dict:
        """Get current risk status"""
        return {
            'daily_pnl': float(self.daily_pnl),
            'daily_trades': self.daily_trades,
            'circuit_breaker': self.circuit_breaker_triggered,
            'circuit_breaker_until': self.circuit_breaker_until,
            'limits': {
                'max_position_size': float(self.max_position_size),
                'daily_loss_limit': float(self.daily_loss_limit),
                'stop_loss_pct': float(self.stop_loss_pct),
                'take_profit_pct': float(self.take_profit_pct)
            },
            'positions': [
                {
                    'symbol': p.symbol,
                    'size': float(p.size),
                    'unrealized_pnl': float(p.unrealized_pnl),
                    'pnl_pct': float(p.pnl_pct)
                }
                for p in self.position_risks.values()
            ]
        }
        
    async def emergency_stop(self):
        """Emergency stop - close all positions"""
        logger.critical("EMERGENCY STOP ACTIVATED")
        self.circuit_breaker_triggered = True
        self.circuit_breaker_until = time.time() + 86400  # 24 hours
        
        # Trigger callback for position liquidation
        if self.on_circuit_breaker:
            await self.on_circuit_breaker(self.daily_pnl, emergency=True)
