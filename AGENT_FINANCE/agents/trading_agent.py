"""
AMCIS Trading Agent - Automated DeFi & Exchange Trading
Generates revenue through algorithmic trading strategies
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
import json
import time

from core.agent_base import BaseAgent, AgentMessage, AgentPriority, AgentState

logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    """Trading signal from strategy"""
    symbol: str
    side: str  # 'buy' or 'sell'
    amount: Decimal
    price: Optional[Decimal] = None
    order_type: str = 'market'  # 'market', 'limit', 'stop'
    confidence: float = 0.5
    strategy: str = ''
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Position:
    """Active trading position"""
    id: str
    symbol: str
    side: str
    entry_price: Decimal
    amount: Decimal
    unrealized_pnl: Decimal = Decimal('0')
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    opened_at: float = 0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.opened_at == 0:
            self.opened_at = time.time()
    
    @property
    def value(self) -> Decimal:
        return self.entry_price * self.amount


class TradingAgent(BaseAgent):
    """
    Autonomous trading agent for spot, futures, and DeFi trading.
    Generates revenue through algorithmic strategies.
    """
    
    def __init__(self, name: str, message_bus, config: Optional[Dict] = None):
        super().__init__(name, "trader", message_bus, config)
        
        # Trading configuration
        self.exchanges: List[str] = config.get('exchanges', ['binance', 'coinbase'])
        self.trading_pairs: List[str] = config.get('pairs', ['BTC-USD', 'ETH-USD'])
        self.max_position_size = Decimal(str(config.get('max_position_size', 1000)))  # USD
        self.max_positions = config.get('max_positions', 5)
        self.leverage = config.get('leverage', 1)  # 1 = spot
        
        # Risk management
        self.stop_loss_pct = config.get('stop_loss_pct', 0.02)  # 2%
        self.take_profit_pct = config.get('take_profit_pct', 0.06)  # 6%
        self.max_daily_loss = Decimal(str(config.get('max_daily_loss', 500)))
        self.min_confidence = config.get('min_confidence', 0.6)
        
        # Strategy registry
        self.strategies: Dict[str, Callable] = {}
        self.active_strategies: List[str] = config.get('active_strategies', ['momentum'])
        
        # State
        self.positions: Dict[str, Position] = {}
        self.pending_orders: Dict[str, Dict] = {}
        self.daily_pnl = Decimal('0')
        self.daily_trades = 0
        self.last_reset = time.time()
        
        # Market data cache
        self.price_cache: Dict[str, Dict] = {}
        self.cache_ttl = 5  # seconds
        
        # Register message handlers
        self._message_handlers = {
            'market.price_update': self._on_price_update,
            'trade.executed': self._on_trade_executed,
            'risk.stop_trading': self._on_stop_signal,
        }
        
    async def _setup(self):
        """Initialize trading resources"""
        # Register built-in strategies
        self._register_strategy('momentum', self._momentum_strategy)
        self._register_strategy('mean_reversion', self._mean_reversion_strategy)
        self._register_strategy('breakout', self._breakout_strategy)
        
        # Load open positions from database
        await self._load_positions()
        
        logger.info(f"Trading agent {self.name} ready with strategies: {self.active_strategies}")
        
    def _register_strategy(self, name: str, strategy_fn: Callable):
        """Register a trading strategy"""
        self.strategies[name] = strategy_fn
        
    async def _load_positions(self):
        """Load open positions from database"""
        # Implementation would query DB
        self.positions = {}
        
    async def execute_cycle(self):
        """Main trading cycle"""
        # Reset daily stats if needed
        await self._check_daily_reset()
        
        # Check risk limits
        if not await self._check_risk_limits():
            return
            
        # Update market data
        await self._update_market_data()
        
        # Check existing positions (stop loss / take profit)
        await self._manage_positions()
        
        # Generate signals from active strategies
        signals = await self._generate_signals()
        
        # Filter and execute best signals
        for signal in signals:
            if await self._validate_signal(signal):
                await self._execute_signal(signal)
                
    async def _check_daily_reset(self):
        """Reset daily counters"""
        if time.time() - self.last_reset > 86400:  # 24 hours
            self.daily_pnl = Decimal('0')
            self.daily_trades = 0
            self.last_reset = time.time()
            logger.info(f"Daily stats reset. Previous P&L: ${self.metrics.profit:.2f}")
            
    async def _check_risk_limits(self) -> bool:
        """Check if trading should continue based on risk limits"""
        if self.daily_pnl < -self.max_daily_loss:
            logger.warning(f"Daily loss limit hit: ${self.daily_pnl}")
            await self.send_message(
                'risk.limit_triggered',
                {'agent_id': self.id, 'limit': 'daily_loss', 'value': float(self.daily_pnl)},
                priority=AgentPriority.CRITICAL
            )
            return False
            
        if len(self.positions) >= self.max_positions:
            return False
            
        return True
        
    async def _update_market_data(self):
        """Fetch latest market prices"""
        # This would fetch from exchange APIs
        # For now, simulate with message requests
        for pair in self.trading_pairs:
            await self.send_message(
                'market.get_price',
                {'symbol': pair, 'requester': self.id},
                priority=AgentPriority.NORMAL
            )
            
    async def _manage_positions(self):
        """Check and manage open positions"""
        for pos_id, position in list(self.positions.items()):
            current_price = await self._get_current_price(position.symbol)
            if not current_price:
                continue
                
            # Calculate unrealized P&L
            if position.side == 'buy':
                pnl_pct = (current_price - position.entry_price) / position.entry_price
            else:
                pnl_pct = (position.entry_price - current_price) / position.entry_price
                
            position.unrealized_pnl = position.value * Decimal(str(pnl_pct))
            
            # Check stop loss
            if position.stop_loss:
                if position.side == 'buy' and current_price <= position.stop_loss:
                    await self._close_position(pos_id, current_price, 'stop_loss')
                    continue
                elif position.side == 'sell' and current_price >= position.stop_loss:
                    await self._close_position(pos_id, current_price, 'stop_loss')
                    continue
                    
            # Check take profit
            if position.take_profit:
                if position.side == 'buy' and current_price >= position.take_profit:
                    await self._close_position(pos_id, current_price, 'take_profit')
                    continue
                elif position.side == 'sell' and current_price <= position.take_profit:
                    await self._close_position(pos_id, current_price, 'take_profit')
                    continue
                    
    async def _generate_signals(self) -> List[TradeSignal]:
        """Generate trading signals from all active strategies"""
        signals = []
        
        for strategy_name in self.active_strategies:
            if strategy_name in self.strategies:
                try:
                    strategy_signals = await self.strategies[strategy_name]()
                    signals.extend(strategy_signals)
                except Exception as e:
                    logger.error(f"Strategy {strategy_name} error: {e}")
                    
        # Sort by confidence
        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals
        
    async def _validate_signal(self, signal: TradeSignal) -> bool:
        """Validate if signal should be executed"""
        if signal.confidence < self.min_confidence:
            return False
            
        # Check if we already have position in this symbol
        for pos in self.positions.values():
            if pos.symbol == signal.symbol:
                return False
                
        # Validate amount
        if signal.amount > self.max_position_size:
            signal.amount = self.max_position_size
            
        return True
        
    async def _execute_signal(self, signal: TradeSignal):
        """Execute trading signal"""
        # Build order
        order = {
            'symbol': signal.symbol,
            'side': signal.side,
            'amount': float(signal.amount),
            'order_type': signal.order_type,
            'price': float(signal.price) if signal.price else None,
            'strategy': signal.strategy,
            'confidence': signal.confidence
        }
        
        # Send to execution engine
        await self.send_message(
            'trade.execute',
            {
                'agent_id': self.id,
                'order': order,
                'timestamp': time.time()
            },
            priority=AgentPriority.HIGH
        )
        
        # Track pending
        order_id = f"{self.id}_{int(time.time()*1000)}"
        self.pending_orders[order_id] = order
        
        logger.info(f"Order sent: {signal.side} {signal.amount} {signal.symbol}")
        
    async def _close_position(self, pos_id: str, exit_price: Decimal, reason: str):
        """Close an open position"""
        position = self.positions.get(pos_id)
        if not position:
            return
            
        # Calculate realized P&L
        if position.side == 'buy':
            pnl = (exit_price - position.entry_price) * position.amount
        else:
            pnl = (position.entry_price - exit_price) * position.amount
            
        # Send close order
        close_side = 'sell' if position.side == 'buy' else 'buy'
        await self.send_message(
            'trade.execute',
            {
                'agent_id': self.id,
                'order': {
                    'symbol': position.symbol,
                    'side': close_side,
                    'amount': float(position.amount),
                    'order_type': 'market',
                    'reason': reason
                },
                'closing_position': pos_id
            },
            priority=AgentPriority.HIGH
        )
        
        # Update metrics
        self.metrics.update_profit(float(pnl), 0)
        self.daily_pnl += pnl
        self.metrics.record_trade(pnl > 0)
        self.daily_trades += 1
        
        del self.positions[pos_id]
        
        logger.info(f"Position closed: {reason}, P&L: ${pnl:.2f}")
        
    async def _get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get current price from cache or fetch"""
        cache = self.price_cache.get(symbol)
        if cache and time.time() - cache['time'] < self.cache_ttl:
            return cache['price']
        return None
        
    # ========== Trading Strategies ==========
    
    async def _momentum_strategy(self) -> List[TradeSignal]:
        """
        Momentum-based strategy
        Buys assets showing upward momentum, sells on downward
        """
        signals = []
        
        for pair in self.trading_pairs:
            price_data = self.price_cache.get(pair, {})
            if not price_data:
                continue
                
            # Simple momentum calculation
            price_change_1h = price_data.get('change_1h', 0)
            price_change_24h = price_data.get('change_24h', 0)
            volume_surge = price_data.get('volume_surge', 1.0)
            
            # Strong upward momentum
            if price_change_1h > 0.01 and price_change_24h > 0.05 and volume_surge > 1.5:
                confidence = min(0.5 + price_change_24h * 5, 0.95)
                signals.append(TradeSignal(
                    symbol=pair,
                    side='buy',
                    amount=self.max_position_size / Decimal('2'),
                    confidence=confidence,
                    strategy='momentum',
                    metadata={'indicators': {'change_1h': price_change_1h}}
                ))
                
            # Strong downward momentum
            elif price_change_1h < -0.01 and price_change_24h < -0.05 and volume_surge > 1.5:
                confidence = min(0.5 + abs(price_change_24h) * 5, 0.95)
                signals.append(TradeSignal(
                    symbol=pair,
                    side='sell',
                    amount=self.max_position_size / Decimal('2'),
                    confidence=confidence,
                    strategy='momentum',
                    metadata={'indicators': {'change_1h': price_change_1h}}
                ))
                
        return signals
        
    async def _mean_reversion_strategy(self) -> List[TradeSignal]:
        """
        Mean reversion strategy
        Buys oversold assets, sells overbought
        """
        signals = []
        
        for pair in self.trading_pairs:
            price_data = self.price_cache.get(pair, {})
            if not price_data:
                continue
                
            # RSI-like indicator
            rsi = price_data.get('rsi', 50)
            price_vs_ma = price_data.get('price_vs_ma20', 0)
            
            # Oversold - buy signal
            if rsi < 30 and price_vs_ma < -0.05:
                confidence = (30 - rsi) / 30 * 0.8 + 0.2
                signals.append(TradeSignal(
                    symbol=pair,
                    side='buy',
                    amount=self.max_position_size / Decimal('3'),
                    confidence=confidence,
                    strategy='mean_reversion',
                    metadata={'rsi': rsi, 'price_vs_ma': price_vs_ma}
                ))
                
            # Overbought - sell signal
            elif rsi > 70 and price_vs_ma > 0.05:
                confidence = (rsi - 70) / 30 * 0.8 + 0.2
                signals.append(TradeSignal(
                    symbol=pair,
                    side='sell',
                    amount=self.max_position_size / Decimal('3'),
                    confidence=confidence,
                    strategy='mean_reversion',
                    metadata={'rsi': rsi, 'price_vs_ma': price_vs_ma}
                ))
                
        return signals
        
    async def _breakout_strategy(self) -> List[TradeSignal]:
        """
        Breakout strategy
        Trades when price breaks support/resistance levels
        """
        signals = []
        
        for pair in self.trading_pairs:
            price_data = self.price_cache.get(pair, {})
            if not price_data:
                continue
                
            current_price = price_data.get('price', 0)
            resistance = price_data.get('resistance_24h', 0)
            support = price_data.get('support_24h', 0)
            
            # Break above resistance
            if resistance > 0 and current_price > resistance * 1.005:
                breakout_pct = (current_price - resistance) / resistance
                signals.append(TradeSignal(
                    symbol=pair,
                    side='buy',
                    amount=self.max_position_size / Decimal('2'),
                    confidence=min(0.6 + breakout_pct * 10, 0.9),
                    strategy='breakout',
                    metadata={'breakout_level': resistance, 'breakout_pct': breakout_pct}
                ))
                
            # Break below support
            elif support > 0 and current_price < support * 0.995:
                breakout_pct = (support - current_price) / support
                signals.append(TradeSignal(
                    symbol=pair,
                    side='sell',
                    amount=self.max_position_size / Decimal('2'),
                    confidence=min(0.6 + breakout_pct * 10, 0.9),
                    strategy='breakout',
                    metadata={'breakout_level': support, 'breakout_pct': breakout_pct}
                ))
                
        return signals
        
    # ========== Message Handlers ==========
    
    async def _on_price_update(self, message: AgentMessage):
        """Handle price updates"""
        payload = message.payload
        symbol = payload.get('symbol')
        price = payload.get('price')
        
        if symbol and price:
            self.price_cache[symbol] = {
                'price': Decimal(str(price)),
                'time': time.time(),
                **payload.get('indicators', {})
            }
            
    async def _on_trade_executed(self, message: AgentMessage):
        """Handle trade execution confirmation"""
        payload = message.payload
        order_id = payload.get('order_id')
        
        if order_id in self.pending_orders:
            order = self.pending_orders.pop(order_id)
            
            # Create position if successful
            if payload.get('success'):
                pos_id = f"pos_{int(time.time()*1000)}"
                
                # Calculate stop loss and take profit
                entry_price = Decimal(str(payload.get('fill_price', 0)))
                if entry_price > 0:
                    if order.get('side') == 'buy':
                        stop = entry_price * (1 - Decimal(str(self.stop_loss_pct)))
                        target = entry_price * (1 + Decimal(str(self.take_profit_pct)))
                    else:
                        stop = entry_price * (1 + Decimal(str(self.stop_loss_pct)))
                        target = entry_price * (1 - Decimal(str(self.take_profit_pct)))
                else:
                    stop = target = None
                    
                position = Position(
                    id=pos_id,
                    symbol=order['symbol'],
                    side=order['side'],
                    entry_price=entry_price,
                    amount=Decimal(str(order['amount'])),
                    stop_loss=stop,
                    take_profit=target,
                    metadata={'order_id': order_id, 'strategy': order.get('strategy', '')}
                )
                
                self.positions[pos_id] = position
                logger.info(f"Position opened: {order['side']} {order['symbol']} @ {entry_price}")
                
    async def _on_stop_signal(self, message: AgentMessage):
        """Handle emergency stop signal"""
        payload = message.payload
        if payload.get('agent_id') == self.id or payload.get('broadcast'):
            logger.warning(f"Emergency stop received: {payload.get('reason')}")
            await self.pause()
            
            # Close all positions
            for pos_id in list(self.positions.keys()):
                current_price = await self._get_current_price(self.positions[pos_id].symbol)
                if current_price:
                    await self._close_position(pos_id, current_price, 'emergency_stop')
