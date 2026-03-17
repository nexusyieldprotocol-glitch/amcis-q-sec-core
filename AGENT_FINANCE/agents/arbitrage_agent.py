"""
AMCIS Arbitrage Agent - Cross-Exchange Arbitrage Detection & Execution
Detects price discrepancies and executes profitable arbitrage trades
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
import time

from AGENT_FINANCE.core.agent_base import BaseAgent
from exchanges.base import OrderSide

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageOpportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: Decimal
    sell_price: Decimal
    size: Decimal
    gross_profit: Decimal
    net_profit: Decimal
    profit_pct: Decimal
    confidence: float
    timestamp: float
    expires_at: float


class ArbitrageAgent(BaseAgent):
    """
    High-frequency arbitrage agent
    Monitors multiple exchanges for price discrepancies
    """
    
    def __init__(self, config: Dict):
        super().__init__("ArbitrageAgent", config)
        
        # Thresholds
        self.min_profit_usd = Decimal(str(config.get('min_profit_usd', 10)))
        self.min_profit_pct = Decimal(str(config.get('min_profit_pct', 0.001)))
        self.max_position_size = Decimal(str(config.get('max_position_size', 50000)))
        self.max_slippage = Decimal(str(config.get('max_slippage', 0.005)))
        
        # Monitored pairs
        self.symbols = config.get('symbols', ['BTC-USD', 'ETH-USD', 'SOL-USD'])
        self.exchanges = config.get('exchanges', ['binance', 'coinbase', 'kraken'])
        
        # State
        self.price_cache: Dict[str, Dict[str, Dict]] = {}
        self.active_opportunities: Dict[str, ArbitrageOpportunity] = {}
        self.execution_lock = asyncio.Lock()
        
        # Stats
        self.opportunities_found = 0
        self.opportunities_executed = 0
        self.total_profit = Decimal('0')
        
    async def run_cycle(self):
        """Main arbitrage detection cycle"""
        # Clean expired opportunities
        await self._cleanup_expired()
        
        # Detect new opportunities
        opportunities = await self._detect_opportunities()
        
        # Filter and sort by profit
        viable = [o for o in opportunities if o.net_profit >= self.min_profit_usd]
        viable.sort(key=lambda x: x.net_profit, reverse=True)
        
        # Execute best opportunities
        for opp in viable[:3]:
            async with self.execution_lock:
                if await self._validate_opportunity(opp):
                    success = await self._execute_arbitrage(opp)
                    if success:
                        break
                        
    async def _detect_opportunities(self) -> List[ArbitrageOpportunity]:
        """Detect arbitrage opportunities across exchanges"""
        opportunities = []
        
        for symbol in self.symbols:
            # Get prices from all exchanges
            prices = {}
            for exchange in self.exchanges:
                if exchange in self.price_cache and symbol in self.price_cache[exchange]:
                    data = self.price_cache[exchange][symbol]
                    if time.time() - data['timestamp'] < 5:  # 5 sec freshness
                        prices[exchange] = data
                        
            if len(prices) < 2:
                continue
                
            # Find best buy (lowest ask) and best sell (highest bid)
            best_buy = None
            best_sell = None
            
            for exchange, data in prices.items():
                if not best_buy or data['ask'] < best_buy['ask']:
                    best_buy = {**data, 'exchange': exchange}
                if not best_sell or data['bid'] > best_sell['bid']:
                    best_sell = {**data, 'exchange': exchange}
                    
            if not best_buy or not best_sell or best_buy['exchange'] == best_sell['exchange']:
                continue
                
            # Calculate profit
            spread = best_sell['bid'] - best_buy['ask']
            spread_pct = spread / best_buy['ask']
            
            if spread_pct < self.min_profit_pct:
                continue
                
            # Determine trade size
            trade_size = min(
                self.max_position_size,
                best_buy['ask_volume'],
                best_sell['bid_volume']
            )
            
            gross_profit = spread * trade_size
            
            # Estimate fees (0.1% taker fee typical)
            fee_buy = trade_size * best_buy['ask'] * Decimal('0.001')
            fee_sell = trade_size * best_sell['bid'] * Decimal('0.001')
            total_fees = fee_buy + fee_sell
            
            net_profit = gross_profit - total_fees
            
            if net_profit < self.min_profit_usd:
                continue
                
            opp = ArbitrageOpportunity(
                symbol=symbol,
                buy_exchange=best_buy['exchange'],
                sell_exchange=best_sell['exchange'],
                buy_price=best_buy['ask'],
                sell_price=best_sell['bid'],
                size=trade_size,
                gross_profit=gross_profit,
                net_profit=net_profit,
                profit_pct=spread_pct,
                confidence=min(float(spread_pct * 1000), 0.95),
                timestamp=time.time(),
                expires_at=time.time() + 3  # 3 second validity
            )
            
            opportunities.append(opp)
            self.opportunities_found += 1
            
        return opportunities
        
    async def _validate_opportunity(self, opp: ArbitrageOpportunity) -> bool:
        """Validate opportunity is still profitable"""
        # Check freshness
        if time.time() > opp.expires_at:
            return False
            
        # Re-check prices
        buy_data = self.price_cache.get(opp.buy_exchange, {}).get(opp.symbol)
        sell_data = self.price_cache.get(opp.sell_exchange, {}).get(opp.symbol)
        
        if not buy_data or not sell_data:
            return False
            
        # Verify spread still exists
        current_spread = sell_data['bid'] - buy_data['ask']
        if current_spread <= 0:
            return False
            
        return True
        
    async def _execute_arbitrage(self, opp: ArbitrageOpportunity) -> bool:
        """Execute the arbitrage trade"""
        logger.info(f"Executing arbitrage: {opp.symbol} | Buy @{opp.buy_exchange} ${opp.buy_price} | Sell @{opp.sell_exchange} ${opp.sell_price} | Profit: ${opp.net_profit:.2f}")
        
        try:
            # Send buy order
            buy_result = await self.send_order(
                exchange=opp.buy_exchange,
                symbol=opp.symbol,
                side=OrderSide.BUY,
                amount=opp.size,
                order_type='market'
            )
            
            if not buy_result['success']:
                logger.error(f"Buy failed: {buy_result.get('error')}")
                return False
                
            # Send sell order
            sell_result = await self.send_order(
                exchange=opp.sell_exchange,
                symbol=opp.symbol,
                side=OrderSide.SELL,
                amount=buy_result['filled'],
                order_type='market'
            )
            
            if not sell_result['success']:
                # Emergency: try to sell back on buy exchange
                logger.error(f"Sell failed! Attempting emergency exit...")
                await self.send_order(
                    exchange=opp.buy_exchange,
                    symbol=opp.symbol,
                    side=OrderSide.SELL,
                    amount=buy_result['filled'],
                    order_type='market'
                )
                return False
                
            # Calculate actual profit
            buy_cost = buy_result['filled'] * buy_result['price'] + buy_result['fee']
            sell_revenue = sell_result['filled'] * sell_result['price'] - sell_result['fee']
            actual_profit = sell_revenue - buy_cost
            
            self.total_profit += actual_profit
            self.opportunities_executed += 1
            
            logger.info(f"Arbitrage completed! Profit: ${actual_profit:.2f}")
            
            # Record to database
            await self.record_trade({
                'type': 'arbitrage',
                'symbol': opp.symbol,
                'buy_exchange': opp.buy_exchange,
                'sell_exchange': opp.sell_exchange,
                'size': float(opp.size),
                'profit': float(actual_profit),
                'timestamp': datetime.utcnow()
            })
            
            return True
            
        except Exception as e:
            logger.exception(f"Arbitrage execution failed: {e}")
            return False
            
    async def _cleanup_expired(self):
        """Remove expired opportunities"""
        now = time.time()
        expired = [k for k, v in self.active_opportunities.items() if now > v.expires_at]
        for k in expired:
            del self.active_opportunities[k]
            
    async def update_price(self, exchange: str, symbol: str, bid: Decimal, ask: Decimal,
                          bid_volume: Decimal, ask_volume: Decimal):
        """Update price cache from market data"""
        if exchange not in self.price_cache:
            self.price_cache[exchange] = {}
            
        self.price_cache[exchange][symbol] = {
            'bid': bid,
            'ask': ask,
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'timestamp': time.time()
        }
        
    async def send_order(self, exchange: str, symbol: str, side: OrderSide,
                        amount: Decimal, order_type: str) -> Dict:
        """Send order to exchange"""
        # Delegate to exchange connector
        return await self.emit('order.create', {
            'exchange': exchange,
            'symbol': symbol,
            'side': side.value,
            'amount': float(amount),
            'type': order_type
        })
