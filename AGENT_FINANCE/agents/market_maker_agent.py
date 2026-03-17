"""
AMCIS Market Maker Agent - Automated Liquidity Provision
Provides liquidity by placing bid/ask orders, collecting spread
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from decimal import Decimal
import time

from AGENT_FINANCE.core.agent_base import BaseAgent
from exchanges.base import OrderSide, OrderType

logger = logging.getLogger(__name__)


@dataclass
class Quote:
    bid_price: Decimal
    bid_size: Decimal
    ask_price: Decimal
    ask_size: Decimal
    timestamp: float


class MarketMakerAgent(BaseAgent):
    """
    Automated market maker
    Places bid/ask orders around mid price, manages inventory
    """
    
    def __init__(self, config: Dict):
        super().__init__("MarketMakerAgent", config)
        
        # Quote parameters
        self.spread_bps = Decimal(str(config.get('spread_bps', 10)))  # 0.1%
        self.min_spread_bps = Decimal(str(config.get('min_spread_bps', 5)))
        self.max_spread_bps = Decimal(str(config.get('max_spread_bps', 50)))
        
        # Order sizes
        self.base_order_size = Decimal(str(config.get('base_order_size', 0.01)))  # BTC
        self.max_position = Decimal(str(config.get('max_position', 1.0)))  # Max inventory
        
        # Inventory management
        self.target_inventory = Decimal('0')  # Target delta neutral
        self.inventory_skew = Decimal(str(config.get('inventory_skew', 0.5)))  # 0-1
        
        # Risk
        self.stop_loss_bps = Decimal(str(config.get('stop_loss_bps', 100)))
        self.max_orders_per_side = config.get('max_orders_per_side', 3)
        
        # State
        self.symbols = config.get('symbols', ['BTC-USD'])
        self.exchange = config.get('exchange', 'binance')
        self.active_quotes: Dict[str, Quote] = {}
        self.active_orders: Dict[str, List[Dict]] = {}
        self.position: Decimal = Decimal('0')
        self.entry_price: Optional[Decimal] = None
        
        # Performance
        self.total_fees = Decimal('0')
        self.realized_pnl = Decimal('0')
        
    async def run_cycle(self):
        """Main market making cycle"""
        for symbol in self.symbols:
            await self._update_quotes(symbol)
            
        await self._check_inventory_risk()
        
    async def _update_quotes(self, symbol: str):
        """Update bid/ask quotes for symbol"""
        # Get market data
        market_data = await self.get_market_data(self.exchange, symbol)
        if not market_data:
            return
            
        mid_price = (market_data['bid'] + market_data['ask']) / 2
        
        # Adjust spread based on inventory
        inventory_adjustment = self._calculate_inventory_adjustment()
        adjusted_spread = self._adjust_spread_for_volatility(
            self.spread_bps, market_data.get('volatility', 0)
        )
        
        half_spread = (adjusted_spread / 2) * mid_price / Decimal('10000')
        
        # Calculate skewed prices
        bid_price = mid_price - half_spread * (Decimal('1') + inventory_adjustment)
        ask_price = mid_price + half_spread * (Decimal('1') - inventory_adjustment)
        
        # Adjust sizes based on inventory
        bid_size = self._calculate_bid_size()
        ask_size = self._calculate_ask_size()
        
        # Cancel existing orders
        await self._cancel_existing_orders(symbol)
        
        # Place new orders
        orders_placed = []
        
        if bid_size > 0:
            bid_order = await self.place_order(
                symbol=symbol,
                side=OrderSide.BUY,
                price=bid_price,
                amount=bid_size
            )
            if bid_order:
                orders_placed.append(bid_order)
                
        if ask_size > 0:
            ask_order = await self.place_order(
                symbol=symbol,
                side=OrderSide.SELL,
                price=ask_price,
                amount=ask_size
            )
            if ask_order:
                orders_placed.append(ask_order)
                
        self.active_orders[symbol] = orders_placed
        self.active_quotes[symbol] = Quote(
            bid_price=bid_price,
            bid_size=bid_size,
            ask_price=ask_price,
            ask_size=ask_size,
            timestamp=time.time()
        )
        
    def _calculate_inventory_adjustment(self) -> Decimal:
        """Calculate price skew based on inventory"""
        if self.max_position == 0:
            return Decimal('0')
            
        # Normalize position to -1 to 1 range
        normalized_pos = self.position / self.max_position
        
        # Apply skew factor
        return normalized_pos * self.inventory_skew
        
    def _calculate_bid_size(self) -> Decimal:
        """Calculate bid size based on inventory"""
        if self.position >= self.max_position:
            return Decimal('0')
            
        # Reduce bid size as inventory increases
        inventory_ratio = self.position / self.max_position
        size_factor = Decimal('1') - (inventory_ratio * self.inventory_skew)
        
        return self.base_order_size * max(size_factor, Decimal('0.1'))
        
    def _calculate_ask_size(self) -> Decimal:
        """Calculate ask size based on inventory"""
        if self.position <= -self.max_position:
            return Decimal('0')
            
        # Increase ask size as inventory increases
        inventory_ratio = self.position / self.max_position
        size_factor = Decimal('1') + (inventory_ratio * self.inventory_skew)
        
        return self.base_order_size * max(size_factor, Decimal('0.1'))
        
    def _adjust_spread_for_volatility(self, base_spread: Decimal, volatility: Decimal) -> Decimal:
        """Widen spread in high volatility"""
        if volatility == 0:
            return base_spread
            
        # Increase spread proportionally to volatility
        vol_adjustment = volatility * Decimal('100')  # Scale factor
        adjusted = base_spread + vol_adjustment
        
        # Clamp to min/max
        return max(self.min_spread_bps, min(self.max_spread_bps, adjusted))
        
    async def _check_inventory_risk(self):
        """Check and manage inventory risk"""
        if abs(self.position) >= self.max_position:
            logger.warning(f"Max position reached: {self.position}")
            await self._reduce_inventory()
            
        # Check stop loss
        if self.entry_price and self.position != 0:
            pnl_pct = await self._calculate_unrealized_pnl_pct()
            if pnl_pct < -self.stop_loss_bps / Decimal('10000'):
                logger.warning(f"Stop loss triggered: {pnl_pct:.4%}")
                await self._flatten_position()
                
    async def _reduce_inventory(self):
        """Reduce inventory by adjusting quotes"""
        # Increase skew to favor reducing position
        self.inventory_skew = Decimal('0.8')
        
    async def _flatten_position(self):
        """Close all positions"""
        if self.position > 0:
            await self.place_order(
                symbol=self.symbols[0],
                side=OrderSide.SELL,
                amount=abs(self.position),
                order_type=OrderType.MARKET
            )
        elif self.position < 0:
            await self.place_order(
                symbol=self.symbols[0],
                side=OrderSide.BUY,
                amount=abs(self.position),
                order_type=OrderType.MARKET
            )
            
    async def _cancel_existing_orders(self, symbol: str):
        """Cancel existing orders for symbol"""
        for order in self.active_orders.get(symbol, []):
            await self.emit('order.cancel', {
                'exchange': self.exchange,
                'order_id': order['id']
            })
            
    async def place_order(self, symbol: str, side: OrderSide, amount: Decimal,
                         price: Decimal = None, order_type: OrderType = OrderType.LIMIT) -> Optional[Dict]:
        """Place order on exchange"""
        result = await self.emit('order.create', {
            'exchange': self.exchange,
            'symbol': symbol,
            'side': side.value,
            'amount': float(amount),
            'price': float(price) if price else None,
            'type': order_type.value
        })
        
        if result and result.get('success'):
            # Update position tracking
            if side == OrderSide.BUY:
                self.position += amount
            else:
                self.position -= amount
                
            # Track entry price
            if self.position != 0:
                if self.entry_price is None:
                    self.entry_price = price
                else:
                    # Weighted average
                    self.entry_price = (self.entry_price * (self.position - amount) + price * amount) / self.position
                    
            return result
            
        return None
        
    async def get_market_data(self, exchange: str, symbol: str) -> Optional[Dict]:
        """Get current market data"""
        return await self.emit('market.data', {
            'exchange': exchange,
            'symbol': symbol
        })
        
    async def _calculate_unrealized_pnl_pct(self) -> Decimal:
        """Calculate unrealized P&L percentage"""
        if not self.entry_price or self.position == 0:
            return Decimal('0')
            
        current_data = await self.get_market_data(self.exchange, self.symbols[0])
        if not current_data:
            return Decimal('0')
            
        current_price = (current_data['bid'] + current_data['ask']) / 2
        
        if self.position > 0:
            return (current_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - current_price) / self.entry_price
