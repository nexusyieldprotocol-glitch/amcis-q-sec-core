"""
Paper Exchange - Simulated Trading Environment
==============================================

Paper trading implementation that simulates exchange operations
using real market data from public APIs. NO REAL CAPITAL AT RISK.

Features:
- Simulated order execution
- Real market data from CoinGecko (free API)
- Portfolio tracking with P&L calculation
- Trade history and performance metrics
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum
import aiohttp
import structlog

logger = structlog.get_logger("amcis.trading.paper")


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class PaperOrder:
    """Paper trading order."""
    id: str
    symbol: str
    side: OrderSide
    amount: Decimal
    order_type: OrderType
    price: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[Decimal] = None
    filled_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Current position in a symbol."""
    symbol: str
    amount: Decimal
    avg_entry_price: Decimal
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')


@dataclass
class Portfolio:
    """Paper trading portfolio."""
    cash: Decimal = Decimal('100000')  # Start with $100k paper money
    positions: Dict[str, Position] = field(default_factory=dict)
    total_equity: Decimal = Decimal('100000')
    day_trades: int = 0
    last_reset: float = field(default_factory=time.time)


class PaperExchange:
    """
    Paper Exchange Simulator
    ========================
    
    Simulates exchange operations using real market data.
    NO REAL MONEY - Pure simulation for strategy testing.
    
    Data Source: CoinGecko API (free tier)
    """
    
    COINGECKO_API = "https://api.coingecko.com/api/v3"
    
    def __init__(self, initial_balance: Decimal = Decimal('100000')):
        """
        Initialize paper exchange.
        
        Args:
            initial_balance: Starting paper money balance (USD)
        """
        self.portfolio = Portfolio(cash=initial_balance)
        self.orders: Dict[str, PaperOrder] = {}
        self.order_history: List[PaperOrder] = []
        self.trade_history: List[Dict] = []
        self.price_cache: Dict[str, Dict] = {}
        self.cache_ttl = 60  # seconds
        self.logger = structlog.get_logger("amcis.paper_exchange")
        
        self.logger.info("paper_exchange_initialized", 
                        initial_balance=float(initial_balance))
    
    async def get_price(self, symbol: str) -> Optional[Decimal]:
        """
        Get current price for symbol from CoinGecko.
        
        Args:
            symbol: Trading pair (e.g., 'BTC-USD')
            
        Returns:
            Current price as Decimal or None if unavailable
        """
        # Check cache
        now = time.time()
        if symbol in self.price_cache:
            cached = self.price_cache[symbol]
            if now - cached['timestamp'] < self.cache_ttl:
                return cached['price']
        
        # Map symbols to CoinGecko IDs
        coin_map = {
            'BTC-USD': 'bitcoin',
            'ETH-USD': 'ethereum',
            'SOL-USD': 'solana',
            'ADA-USD': 'cardano',
            'DOT-USD': 'polkadot',
            'LINK-USD': 'chainlink',
        }
        
        coin_id = coin_map.get(symbol)
        if not coin_id:
            self.logger.warning("unknown_symbol", symbol=symbol)
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.COINGECKO_API}/simple/price"
                params = {
                    'ids': coin_id,
                    'vs_currencies': 'usd'
                }
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        price = Decimal(str(data[coin_id]['usd']))
                        
                        # Cache price
                        self.price_cache[symbol] = {
                            'price': price,
                            'timestamp': now
                        }
                        
                        return price
                    else:
                        self.logger.warning("price_fetch_failed", 
                                          symbol=symbol, status=resp.status)
                        return None
        except Exception as e:
            self.logger.error("price_fetch_error", symbol=symbol, error=str(e))
            return None
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        amount: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None
    ) -> PaperOrder:
        """
        Place a paper trading order.
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            amount: Order amount
            order_type: MARKET or LIMIT
            price: Limit price (required for LIMIT orders)
            
        Returns:
            PaperOrder object
        """
        order_id = f"paper_{int(time.time() * 1000)}_{len(self.orders)}"
        
        order = PaperOrder(
            id=order_id,
            symbol=symbol,
            side=side,
            amount=amount,
            order_type=order_type,
            price=price
        )
        
        self.orders[order_id] = order
        
        # For market orders, execute immediately
        if order_type == OrderType.MARKET:
            await self._execute_order(order)
        
        self.logger.info("order_placed",
                        order_id=order_id,
                        symbol=symbol,
                        side=side.value,
                        amount=float(amount))
        
        return order
    
    async def _execute_order(self, order: PaperOrder):
        """
        Execute a paper order.
        
        Args:
            order: Order to execute
        """
        # Get current price
        current_price = await self.get_price(order.symbol)
        if current_price is None:
            order.status = OrderStatus.REJECTED
            order.metadata['reject_reason'] = 'Price unavailable'
            return
        
        # Check limit price
        if order.order_type == OrderType.LIMIT and order.price:
            if order.side == OrderSide.BUY and current_price > order.price:
                return  # Wait for price to come down
            if order.side == OrderSide.SELL and current_price < order.price:
                return  # Wait for price to go up
        
        # Calculate order value
        order_value = order.amount * current_price
        
        # Check buying power for buys
        if order.side == OrderSide.BUY:
            if order_value > self.portfolio.cash:
                order.status = OrderStatus.REJECTED
                order.metadata['reject_reason'] = 'Insufficient funds'
                self.logger.warning("order_rejected_insufficient_funds",
                                  order_id=order.id,
                                  required=float(order_value),
                                  available=float(self.portfolio.cash))
                return
            
            # Deduct cash
            self.portfolio.cash -= order_value
            
            # Update position
            if order.symbol not in self.portfolio.positions:
                self.portfolio.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    amount=order.amount,
                    avg_entry_price=current_price
                )
            else:
                pos = self.portfolio.positions[order.symbol]
                total_value = (pos.amount * pos.avg_entry_price) + order_value
                total_amount = pos.amount + order.amount
                pos.avg_entry_price = total_value / total_amount
                pos.amount = total_amount
        
        # Execute sell
        else:
            if order.symbol not in self.portfolio.positions:
                order.status = OrderStatus.REJECTED
                order.metadata['reject_reason'] = 'No position to sell'
                return
            
            pos = self.portfolio.positions[order.symbol]
            if order.amount > pos.amount:
                order.status = OrderStatus.REJECTED
                order.metadata['reject_reason'] = 'Insufficient position'
                return
            
            # Calculate P&L
            entry_value = order.amount * pos.avg_entry_price
            exit_value = order.amount * current_price
            pnl = exit_value - entry_value
            
            # Update position
            pos.amount -= order.amount
            pos.realized_pnl += pnl
            
            if pos.amount == 0:
                del self.portfolio.positions[order.symbol]
            
            # Add cash
            self.portfolio.cash += exit_value
            
            # Record trade
            self.trade_history.append({
                'symbol': order.symbol,
                'side': 'sell',
                'amount': float(order.amount),
                'entry_price': float(pos.avg_entry_price),
                'exit_price': float(current_price),
                'pnl': float(pnl),
                'timestamp': time.time()
            })
        
        # Fill order
        order.status = OrderStatus.FILLED
        order.filled_price = current_price
        order.filled_at = time.time()
        
        # Update portfolio equity
        await self._update_equity()
        
        self.logger.info("order_filled",
                        order_id=order.id,
                        symbol=order.symbol,
                        side=order.side.value,
                        amount=float(order.amount),
                        price=float(current_price))
    
    async def _update_equity(self):
        """Update total portfolio equity."""
        equity = self.portfolio.cash
        
        for symbol, position in self.portfolio.positions.items():
            price = await self.get_price(symbol)
            if price:
                equity += position.amount * price
        
        self.portfolio.total_equity = equity
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for symbol."""
        return self.portfolio.positions.get(symbol)
    
    async def get_all_positions(self) -> Dict[str, Position]:
        """Get all current positions."""
        return self.portfolio.positions.copy()
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary."""
        await self._update_equity()
        
        # Calculate unrealized P&L
        unrealized_pnl = Decimal('0')
        for symbol, pos in self.portfolio.positions.items():
            current_price = await self.get_price(symbol)
            if current_price:
                unrealized = (current_price - pos.avg_entry_price) * pos.amount
                unrealized_pnl += unrealized
        
        # Calculate realized P&L
        realized_pnl = sum(
            Decimal(str(t['pnl'])) for t in self.trade_history
        )
        
        return {
            'cash': float(self.portfolio.cash),
            'total_equity': float(self.portfolio.total_equity),
            'unrealized_pnl': float(unrealized_pnl),
            'realized_pnl': float(realized_pnl),
            'total_pnl': float(unrealized_pnl + realized_pnl),
            'positions': len(self.portfolio.positions),
            'trades': len(self.trade_history)
        }
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CANCELLED
            return True
        
        return False
    
    def get_order_history(self) -> List[PaperOrder]:
        """Get all orders."""
        return list(self.orders.values())
    
    def get_trade_history(self) -> List[Dict]:
        """Get trade history."""
        return self.trade_history.copy()
