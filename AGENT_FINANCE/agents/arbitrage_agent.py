"""
AMCIS Arbitrage Agent - Cross-Exchange & DeFi Arbitrage
High-frequency profit generation through price discrepancies
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_DOWN
from collections import defaultdict
import time
import heapq

from core.agent_base import BaseAgent, AgentMessage, AgentPriority

logger = logging.getLogger(__name__)


@dataclass
class PriceEntry:
    """Price data from an exchange"""
    exchange: str
    symbol: str
    bid: Decimal
    ask: Decimal
    timestamp: float
    volume_24h: Decimal = Decimal('0')
    
    @property
    def spread(self) -> Decimal:
        if self.bid > 0:
            return (self.ask - self.bid) / self.bid
        return Decimal('0')


@dataclass
class ArbitragePath:
    """Represents an arbitrage opportunity path"""
    id: str
    path_type: str  # 'direct', 'triangular', 'cross_chain'
    
    # For direct arbitrage (buy low, sell high)
    buy_exchange: str
    sell_exchange: str
    symbol: str
    
    # Pricing
    buy_price: Decimal
    sell_price: Decimal
    amount: Decimal
    
    # Profit calculation
    gross_profit: Decimal
    gas_cost: Decimal
    exchange_fees: Decimal
    net_profit: Decimal
    profit_pct: Decimal
    
    # Execution requirements
    min_capital: Decimal
    execution_time_ms: int
    
    # Validity
    valid_until: float
    confidence: float
    
    # Status
    status: str = 'detected'  # detected, executing, executed, failed
    executed_at: Optional[float] = None
    actual_profit: Optional[Decimal] = None
    
    metadata: Dict = field(default_factory=dict)


class ArbitrageAgent(BaseAgent):
    """
    High-frequency arbitrage agent that detects and executes
    profitable price discrepancies across exchanges and DeFi protocols.
    """
    
    def __init__(self, name: str, message_bus, config: Optional[Dict] = None):
        super().__init__(name, "arbitrage", message_bus, config)
        
        # Configuration
        self.min_profit_threshold = Decimal(str(config.get('min_profit_usd', 10)))
        self.min_profit_pct = config.get('min_profit_pct', 0.001)  # 0.1%
        self.max_slippage = config.get('max_slippage', 0.005)  # 0.5%
        self.max_execution_time_ms = config.get('max_execution_ms', 3000)
        
        # Exchanges and pairs to monitor
        self.exchanges: List[str] = config.get('exchanges', [
            'binance', 'coinbase', 'kraken', 'uniswap_v3', 'curve', 'aave'
        ])
        self.symbols: List[str] = config.get('symbols', [
            'BTC-USD', 'ETH-USD', 'ETH-USDC', 'WBTC-ETH', 'USDC-USDT'
        ])
        
        # Capital allocation
        self.max_position_per_trade = Decimal(str(config.get('max_trade_size', 50000)))
        self.capital_reserves: Dict[str, Decimal] = {}  # Per exchange
        
        # State
        self.price_book: Dict[str, Dict[str, PriceEntry]] = defaultdict(dict)
        self.active_opportunities: Dict[str, ArbitragePath] = {}
        self.opportunity_history: List[ArbitragePath] = []
        self.max_history = 1000
        
        # Performance tracking
        self.total_opportunities_found = 0
        self.total_opportunities_executed = 0
        self.total_profit = Decimal('0')
        self.total_gas_spent = Decimal('0')
        
        # Message handlers
        self._message_handlers = {
            'market.price_update': self._on_price_update,
            'arbitrage.executed': self._on_execution_update,
            'liquidity.update': self._on_liquidity_update,
        }
        
        # Execution lock to prevent concurrent trades
        self._execution_lock = asyncio.Lock()
        
    async def _setup(self):
        """Initialize arbitrage detection"""
        # Subscribe to price feeds
        for exchange in self.exchanges:
            await self.send_message(
                'market.subscribe',
                {'exchange': exchange, 'symbols': self.symbols, 'subscriber': self.id}
            )
            
        # Load capital allocations
        await self._load_capital_allocations()
        
        logger.info(f"Arbitrage agent {self.name} monitoring {len(self.symbols)} pairs across {len(self.exchanges)} exchanges")
        
    async def _load_capital_allocations(self):
        """Load available capital per exchange"""
        # Query treasury/wallets for available capital
        for exchange in self.exchanges:
            await self.send_message(
                'treasury.get_balance',
                {'exchange': exchange, 'requester': self.id}
            )
            
    async def execute_cycle(self):
        """Main arbitrage detection and execution cycle"""
        # Clean up expired opportunities
        await self._cleanup_expired()
        
        # Detect new opportunities
        opportunities = await self._detect_opportunities()
        
        # Filter and rank opportunities
        viable = self._filter_opportunities(opportunities)
        
        # Execute best opportunities
        for opp in viable[:3]:  # Top 3 opportunities per cycle
            async with self._execution_lock:
                success = await self._execute_arbitrage(opp)
                if success:
                    break  # Only execute one at a time to avoid conflicts
                    
        # Update metrics
        self.metrics.update_profit(
            float(self.total_profit),
            float(self.total_gas_spent)
        )
        
    async def _cleanup_expired(self):
        """Remove expired opportunities"""
        now = time.time()
        expired = [
            oid for oid, opp in self.active_opportunities.items()
            if now > opp.valid_until
        ]
        for oid in expired:
            del self.active_opportunities[oid]
            
    async def _detect_opportunities(self) -> List[ArbitragePath]:
        """Detect arbitrage opportunities across all exchanges"""
        opportunities = []
        
        # 1. Direct arbitrage (buy low on one exchange, sell high on another)
        direct = await self._detect_direct_arbitrage()
        opportunities.extend(direct)
        
        # 2. Triangular arbitrage (e.g., USD -> BTC -> ETH -> USD)
        triangular = await self._detect_triangular_arbitrage()
        opportunities.extend(triangular)
        
        # 3. Cross-chain arbitrage (if bridges available)
        cross_chain = await self._detect_cross_chain_arbitrage()
        opportunities.extend(cross_chain)
        
        self.total_opportunities_found += len(opportunities)
        
        return opportunities
        
    async def _detect_direct_arbitrage(self) -> List[ArbitragePath]:
        """
        Detect simple buy-low-sell-high opportunities across exchanges
        """
        opportunities = []
        
        for symbol in self.symbols:
            # Get all exchange prices for this symbol
            prices = {}
            for exchange, symbols in self.price_book.items():
                if symbol in symbols:
                    prices[exchange] = symbols[symbol]
                    
            if len(prices) < 2:
                continue
                
            # Find best bid (highest buy price) and best ask (lowest sell price)
            best_bid = None
            best_ask = None
            bid_exchange = None
            ask_exchange = None
            
            for exchange, price_entry in prices.items():
                if best_bid is None or price_entry.bid > best_bid:
                    best_bid = price_entry.bid
                    bid_exchange = exchange
                if best_ask is None or price_entry.ask < best_ask:
                    best_ask = price_entry.ask
                    ask_exchange = exchange
                    
            # Skip if same exchange
            if bid_exchange == ask_exchange or not best_bid or not best_ask:
                continue
                
            # Calculate potential profit
            spread = best_bid - best_ask
            spread_pct = spread / best_ask if best_ask > 0 else 0
            
            # Determine trade size based on available liquidity
            trade_size = min(
                self.max_position_per_trade,
                self.capital_reserves.get(ask_exchange, Decimal('0'))
            )
            
            if trade_size <= 0:
                continue
                
            # Calculate fees (simplified - would query actual fee structure)
            buy_fee = trade_size * Decimal('0.001')  # 0.1%
            sell_fee = (trade_size * best_bid / best_ask) * Decimal('0.001')
            exchange_fees = buy_fee + sell_fee
            
            # Gas/transaction costs
            gas_cost = await self._estimate_gas_cost(ask_exchange, bid_exchange, symbol)
            
            # Net profit calculation
            gross_profit = spread * (trade_size / best_ask)
            net_profit = gross_profit - exchange_fees - gas_cost
            
            # Check if profitable
            if net_profit >= self.min_profit_threshold and spread_pct >= self.min_profit_pct:
                opp_id = f"arb_{symbol}_{ask_exchange}_{bid_exchange}_{int(time.time()*1000)}"
                
                opportunity = ArbitragePath(
                    id=opp_id,
                    path_type='direct',
                    buy_exchange=ask_exchange,
                    sell_exchange=bid_exchange,
                    symbol=symbol,
                    buy_price=best_ask,
                    sell_price=best_bid,
                    amount=trade_size,
                    gross_profit=gross_profit,
                    gas_cost=gas_cost,
                    exchange_fees=exchange_fees,
                    net_profit=net_profit,
                    profit_pct=spread_pct,
                    min_capital=trade_size * Decimal('1.1'),  # 10% buffer
                    execution_time_ms=500,  # Estimated
                    valid_until=time.time() + 5,  # 5 second validity
                    confidence=min(0.95, 0.7 + float(spread_pct) * 100),
                    metadata={
                        'spread_usd': float(spread),
                        'liquidity_score': self._calculate_liquidity_score(symbol, ask_exchange, bid_exchange)
                    }
                )
                
                opportunities.append(opportunity)
                
        return opportunities
        
    async def _detect_triangular_arbitrage(self) -> List[ArbitragePath]:
        """
        Detect triangular arbitrage opportunities
        Example: USD -> BTC -> ETH -> USD
        """
        opportunities = []
        
        # Get base currencies
        currencies = set()
        for symbol in self.symbols:
            parts = symbol.split('-')
            if len(parts) == 2:
                currencies.add(parts[0])
                currencies.add(parts[1])
                
        # Find triangular paths
        for base in ['USD', 'USDC', 'USDT']:
            if base not in currencies:
                continue
                
            for mid in currencies:
                if mid == base:
                    continue
                    
                # Check if we have both legs
                leg1 = self._get_best_price(f"{mid}-{base}")  # Buy mid with base
                leg2 = self._get_best_price(f"{mid}-BTC")     # Sell mid for BTC
                leg3 = self._get_best_price("BTC-USD")        # Sell BTC for base
                
                if leg1 and leg2 and leg3:
                    # Calculate arbitrage
                    # Start with 1 unit of base
                    start_amount = Decimal('1')
                    
                    # Leg 1: base -> mid
                    mid_amount = start_amount / leg1['ask']
                    
                    # Leg 2: mid -> BTC
                    btc_amount = mid_amount * leg2['bid']
                    
                    # Leg 3: BTC -> base
                    final_amount = btc_amount * leg3['bid']
                    
                    profit_pct = (final_amount - start_amount) / start_amount
                    
                    if profit_pct > self.min_profit_pct:
                        # Create opportunity
                        opp_id = f"tri_{base}_{mid}_{int(time.time()*1000)}"
                        
                        # Estimate costs
                        gas_cost = Decimal('0.005')  # Approximate for DeFi
                        exchange_fees = final_amount * Decimal('0.003')  # 0.3% total fees
                        net_profit = (final_amount - start_amount) - gas_cost - exchange_fees
                        
                        opportunity = ArbitragePath(
                            id=opp_id,
                            path_type='triangular',
                            buy_exchange=leg1['exchange'],
                            sell_exchange=leg3['exchange'],
                            symbol=f"{base}->{mid}->BTC->{base}",
                            buy_price=leg1['ask'],
                            sell_price=leg3['bid'],
                            amount=start_amount,
                            gross_profit=final_amount - start_amount,
                            gas_cost=gas_cost,
                            exchange_fees=exchange_fees,
                            net_profit=net_profit,
                            profit_pct=profit_pct,
                            min_capital=Decimal('1000'),
                            execution_time_ms=2000,
                            valid_until=time.time() + 10,
                            confidence=0.7,
                            metadata={
                                'path': [f"{base}->{mid}", f"{mid}->BTC", f"BTC->{base}"],
                                'exchanges': [leg1['exchange'], leg2['exchange'], leg3['exchange']]
                            }
                        )
                        
                        opportunities.append(opportunity)
                        
        return opportunities
        
    async def _detect_cross_chain_arbitrage(self) -> List[ArbitragePath]:
        """
        Detect arbitrage opportunities between chains
        Requires bridge infrastructure
        """
        opportunities = []
        
        # For now, placeholder - would integrate with bridge protocols
        # like Across, Stargate, Synapse, etc.
        
        return opportunities
        
    def _filter_opportunities(self, opportunities: List[ArbitragePath]) -> List[ArbitragePath]:
        """Filter and rank opportunities by expected return"""
        
        # Filter by constraints
        viable = [
            opp for opp in opportunities
            if opp.net_profit >= self.min_profit_threshold
            and opp.profit_pct >= self.min_profit_pct
            and opp.valid_until > time.time()
            and opp.id not in self.active_opportunities
        ]
        
        # Score and sort by expected value (profit * confidence / execution_time)
        scored = []
        for opp in viable:
            score = float(opp.net_profit) * opp.confidence / (opp.execution_time_ms / 1000)
            scored.append((score, opp))
            
        scored.sort(reverse=True)
        
        return [opp for _, opp in scored]
        
    async def _execute_arbitrage(self, opportunity: ArbitragePath) -> bool:
        """Execute the arbitrage trade"""
        opportunity.status = 'executing'
        self.active_opportunities[opportunity.id] = opportunity
        
        try:
            logger.info(f"Executing arbitrage: {opportunity.symbol} "
                       f"Buy@{opportunity.buy_exchange} Sell@{opportunity.sell_exchange} "
                       f"Profit: ${opportunity.net_profit:.2f}")
            
            # Step 1: Execute buy leg
            buy_order = await self._place_order(
                exchange=opportunity.buy_exchange,
                symbol=opportunity.symbol,
                side='buy',
                amount=opportunity.amount,
                order_type='market',
                max_slippage=self.max_slippage
            )
            
            if not buy_order['success']:
                opportunity.status = 'failed'
                logger.error(f"Buy leg failed: {buy_order.get('error')}")
                return False
                
            # Step 2: Transfer if needed (CEX to DEX or cross-chain)
            if opportunity.buy_exchange != opportunity.sell_exchange:
                transfer = await self._transfer_assets(
                    from_exchange=opportunity.buy_exchange,
                    to_exchange=opportunity.sell_exchange,
                    asset=opportunity.symbol.split('-')[0],
                    amount=buy_order['filled_amount']
                )
                
                if not transfer['success']:
                    # Emergency: sell back on buy exchange
                    await self._place_order(
                        exchange=opportunity.buy_exchange,
                        symbol=opportunity.symbol,
                        side='sell',
                        amount=buy_order['filled_amount'],
                        order_type='market'
                    )
                    opportunity.status = 'failed'
                    return False
                    
            # Step 3: Execute sell leg
            sell_order = await self._place_order(
                exchange=opportunity.sell_exchange,
                symbol=opportunity.symbol,
                side='sell',
                amount=buy_order['filled_amount'],
                order_type='market',
                max_slippage=self.max_slippage
            )
            
            if not sell_order['success']:
                opportunity.status = 'failed'
                logger.error(f"Sell leg failed: {sell_order.get('error')}")
                return False
                
            # Calculate actual profit
            buy_cost = buy_order['filled_amount'] * buy_order['avg_price'] + buy_order['fee']
            sell_revenue = sell_order['filled_amount'] * sell_order['avg_price'] - sell_order['fee']
            actual_profit = sell_revenue - buy_cost
            
            opportunity.status = 'executed'
            opportunity.executed_at = time.time()
            opportunity.actual_profit = actual_profit
            
            # Update metrics
            self.total_opportunities_executed += 1
            self.total_profit += actual_profit
            self.total_gas_spent += opportunity.gas_cost
            
            self.metrics.record_trade(actual_profit > 0)
            
            # Report success
            await self.send_message(
                'arbitrage.completed',
                {
                    'opportunity_id': opportunity.id,
                    'symbol': opportunity.symbol,
                    'profit': float(actual_profit),
                    'expected_profit': float(opportunity.net_profit),
                    'buy_exchange': opportunity.buy_exchange,
                    'sell_exchange': opportunity.sell_exchange,
                    'execution_time_ms': int((time.time() - opportunity.valid_until + 5) * 1000)
                },
                priority=AgentPriority.HIGH
            )
            
            logger.info(f"Arbitrage completed! Profit: ${actual_profit:.2f}")
            
            return True
            
        except Exception as e:
            opportunity.status = 'failed'
            logger.exception(f"Arbitrage execution failed: {e}")
            return False
            
    async def _place_order(self, exchange: str, symbol: str, side: str,
                          amount: Decimal, order_type: str = 'market',
                          max_slippage: Optional[Decimal] = None) -> Dict:
        """Place order on exchange"""
        # Send order request to execution engine
        response_future = asyncio.Future()
        
        order_id = f"ord_{int(time.time()*1000)}"
        
        await self.send_message(
            'exchange.place_order',
            {
                'order_id': order_id,
                'exchange': exchange,
                'symbol': symbol,
                'side': side,
                'amount': float(amount),
                'order_type': order_type,
                'max_slippage': float(max_slippage) if max_slippage else None,
                'requester': self.id
            },
            priority=AgentPriority.CRITICAL
        )
        
        # Wait for response (with timeout)
        try:
            # In real implementation, would await on response
            # For now, simulate
            return {
                'success': True,
                'order_id': order_id,
                'filled_amount': float(amount * Decimal('0.995')),  # Simulate slippage
                'avg_price': self.price_book[exchange][symbol].ask if side == 'buy' else self.price_book[exchange][symbol].bid,
                'fee': float(amount * Decimal('0.001'))
            }
        except asyncio.TimeoutError:
            return {'success': False, 'error': 'Timeout'}
            
    async def _transfer_assets(self, from_exchange: str, to_exchange: str,
                              asset: str, amount: Decimal) -> Dict:
        """Transfer assets between exchanges"""
        await self.send_message(
            'treasury.transfer',
            {
                'from': from_exchange,
                'to': to_exchange,
                'asset': asset,
                'amount': float(amount),
                'requester': self.id
            },
            priority=AgentPriority.HIGH
        )
        
        # Simulate transfer
        return {'success': True, 'tx_id': f'tx_{int(time.time())}'}
        
    async def _estimate_gas_cost(self, buy_exchange: str, sell_exchange: str,
                                symbol: str) -> Decimal:
        """Estimate gas/transaction costs"""
        # Query gas prices
        is_defi = any(x in buy_exchange.lower() for x in ['uni', 'curve', 'aave', 'compound'])
        
        if is_defi:
            # DeFi gas estimation
            return Decimal('0.01')  # Approximate ETH cost
        else:
            # CEX withdrawal fees
            return Decimal('0.001')  # Minimal for CEX internal transfers
            
    def _calculate_liquidity_score(self, symbol: str, buy_ex: str, sell_ex: str) -> float:
        """Calculate liquidity score for opportunity"""
        buy_entry = self.price_book.get(buy_ex, {}).get(symbol)
        sell_entry = self.price_book.get(sell_ex, {}).get(symbol)
        
        if not buy_entry or not sell_entry:
            return 0.0
            
        # Higher volume = better liquidity score
        volume_score = min(float(buy_entry.volume_24h) / 1e6, 1.0)  # Normalize to millions
        spread_score = 1.0 - float(buy_entry.spread + sell_entry.spread)
        
        return (volume_score + spread_score) / 2
        
    def _get_best_price(self, symbol: str) -> Optional[Dict]:
        """Get best price across all exchanges for a symbol"""
        best = None
        
        for exchange, symbols in self.price_book.items():
            if symbol in symbols:
                entry = symbols[symbol]
                if best is None or entry.ask < best['ask']:
                    best = {
                        'exchange': exchange,
                        'bid': entry.bid,
                        'ask': entry.ask,
                        'symbol': symbol
                    }
                    
        return best
        
    # ========== Message Handlers ==========
    
    async def _on_price_update(self, message: AgentMessage):
        """Handle real-time price updates"""
        payload = message.payload
        exchange = payload.get('exchange')
        symbol = payload.get('symbol')
        
        if exchange and symbol:
            self.price_book[exchange][symbol] = PriceEntry(
                exchange=exchange,
                symbol=symbol,
                bid=Decimal(str(payload.get('bid', 0))),
                ask=Decimal(str(payload.get('ask', 0))),
                timestamp=payload.get('timestamp', time.time()),
                volume_24h=Decimal(str(payload.get('volume_24h', 0)))
            )
            
    async def _on_execution_update(self, message: AgentMessage):
        """Handle execution confirmations"""
        payload = message.payload
        opp_id = payload.get('opportunity_id')
        
        if opp_id in self.active_opportunities:
            opp = self.active_opportunities[opp_id]
            opp.status = payload.get('status', 'failed')
            
            if opp.status == 'executed':
                opp.actual_profit = Decimal(str(payload.get('actual_profit', 0)))
                
    async def _on_liquidity_update(self, message: AgentMessage):
        """Handle liquidity updates for DeFi pools"""
        # Update pool depth information for better sizing
        pass
