"""
AMCIS Yield Agent - Autonomous DeFi Yield Optimization
Maximizes returns through intelligent yield farming and liquidity provision
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import time

from core.agent_base import BaseAgent, AgentMessage, AgentPriority

logger = logging.getLogger(__name__)


class YieldStrategy(Enum):
    CONSERVATIVE = "conservative"    # Stable, lower yields
    BALANCED = "balanced"            # Moderate risk/reward
    AGGRESSIVE = "aggressive"        # Higher yields, more risk
    YIELD_MAX = "yield_max"          # Maximum yield hunting


@dataclass
class YieldPool:
    """DeFi yield pool information"""
    protocol: str  # 'aave', 'compound', 'curve', 'convex', 'lido', 'rocket_pool'
    pool_address: str
    name: str
    asset: str
    
    # Yield metrics
    base_apy: Decimal  # Base lending/borrowing yield
    reward_apy: Decimal  # Additional token rewards
    total_apy: Decimal
    
    # Risk metrics
    tvl_usd: Decimal  # Total value locked
    utilization_rate: Decimal  # How much of pool is used
    liquidity_depth: Decimal  # Available liquidity for withdrawal
    
    # Fees
    deposit_fee: Decimal
    withdrawal_fee: Decimal
    performance_fee: Decimal
    
    # Safety
    audit_status: str  # 'audited', 'in_review', 'experimental'
    insurance_available: bool
    
    # Metadata
    chain: str = "ethereum"
    last_updated: float = field(default_factory=time.time)


@dataclass
class YieldPosition:
    """Active yield farming position"""
    id: str
    pool: YieldPool
    
    deposited_amount: Decimal
    current_amount: Decimal  # Including accrued interest
    
    entry_apy: Decimal
    current_apy: Decimal
    
    rewards_earned: Dict[str, Decimal]  # Token -> amount
    rewards_claimed: Dict[str, Decimal]
    
    deposit_time: float
    last_harvest_time: float
    
    # Tracking
    total_yield_earned: Decimal = Decimal('0')
    gas_spent: Decimal = Decimal('0')
    
    def calculate_current_value(self) -> Decimal:
        """Calculate total position value including rewards"""
        reward_value = sum(self.rewards_earned.values())
        return self.current_amount + reward_value
        
    @property
    def time_in_pool_hours(self) -> float:
        return (time.time() - self.deposit_time) / 3600


class YieldAgent(BaseAgent):
    """
    Autonomous yield farming agent that optimizes capital allocation
    across DeFi protocols to maximize risk-adjusted returns.
    """
    
    def __init__(self, name: str, message_bus, config: Optional[Dict] = None):
        super().__init__(name, "yield_optimizer", message_bus, config)
        
        # Strategy configuration
        self.strategy = YieldStrategy(config.get('strategy', 'balanced'))
        self.rebalance_threshold = Decimal(str(config.get('rebalance_threshold', 0.02)))  # 2%
        self.harvest_threshold_usd = Decimal(str(config.get('harvest_threshold', 50)))  # Min $50 to harvest
        self.compound_frequency_hours = config.get('compound_frequency', 24)
        
        # Risk parameters
        self.max_protocol_allocation = Decimal(str(config.get('max_protocol_pct', 0.30)))  # 30% per protocol
        self.min_pool_tvl_usd = Decimal(str(config.get('min_pool_tvl', 1_000_000)))  # $1M minimum
        self.max_slippage_exit = Decimal(str(config.get('max_slippage_exit', 0.01)))  # 1%
        
        # Supported protocols
        self.protocols: List[str] = config.get('protocols', [
            'aave_v3', 'compound_v3', 'curve', 'convex', 'lido', 'rocket_pool',
            'uniswap_v3', 'sushiswap', 'yearn'
        ])
        
        self.supported_assets: List[str] = config.get('assets', [
            'USDC', 'USDT', 'DAI', 'ETH', 'WBTC', 'stETH'
        ])
        
        # State
        self.pools: Dict[str, YieldPool] = {}  # pool_id -> YieldPool
        self.positions: Dict[str, YieldPosition] = {}  # position_id -> YieldPosition
        self.available_capital: Dict[str, Decimal] = {}  # asset -> amount
        
        # Tracking
        self.total_deposited = Decimal('0')
        self.total_current_value = Decimal('0')
        self.total_rewards_claimed = Decimal('0')
        self.total_gas_costs = Decimal('0')
        
        # Message handlers
        self._message_handlers = {
            'yield.pool_update': self._on_pool_update,
            'yield.rewards_available': self._on_rewards_available,
            'treasury.capital_update': self._on_capital_update,
        }
        
    async def _setup(self):
        """Initialize yield farming resources"""
        # Subscribe to pool updates
        for protocol in self.protocols:
            await self.send_message(
                'yield.subscribe_pools',
                {'protocol': protocol, 'subscriber': self.id}
            )
            
        # Load existing positions
        await self._load_positions()
        
        # Get available capital
        await self._refresh_capital()
        
        logger.info(f"Yield agent {self.name} initialized with strategy: {self.strategy.value}")
        
    async def _load_positions(self):
        """Load existing yield positions from database"""
        # Would query database
        self.positions = {}
        
    async def _refresh_capital(self):
        """Refresh available capital from treasury"""
        await self.send_message(
            'treasury.get_available',
            {'requester': self.id, 'purpose': 'yield_farming'}
        )
        
    async def execute_cycle(self):
        """Main yield optimization cycle"""
        # 1. Update pool data and calculate optimal allocations
        optimal_allocations = await self._calculate_optimal_allocations()
        
        # 2. Harvest rewards from existing positions
        await self._harvest_rewards()
        
        # 3. Rebalance if needed
        await self._rebalance_positions(optimal_allocations)
        
        # 4. Deploy idle capital
        await self._deploy_capital(optimal_allocations)
        
        # 5. Update metrics
        await self._update_metrics()
        
    async def _calculate_optimal_allocations(self) -> Dict[str, Decimal]:
        """
        Calculate optimal capital allocation across pools
        Based on risk-adjusted yields
        """
        allocations = {}
        
        if not self.pools:
            return allocations
            
        # Filter pools based on strategy and risk criteria
        eligible_pools = self._filter_eligible_pools()
        
        if not eligible_pools:
            return allocations
            
        # Calculate risk-adjusted scores
        scored_pools = []
        for pool_id, pool in eligible_pools.items():
            score = self._calculate_pool_score(pool)
            scored_pools.append((score, pool_id, pool))
            
        # Sort by score
        scored_pools.sort(reverse=True)
        
        # Allocate capital based on scores
        total_capital = sum(self.available_capital.values())
        
        if self.strategy == YieldStrategy.YIELD_MAX:
            # Put everything in highest yield
            if scored_pools:
                allocations[scored_pools[0][1]] = total_capital
                
        elif self.strategy == YieldStrategy.CONSERVATIVE:
            # Diversify across top stable pools
            top_pools = scored_pools[:5]
            equal_alloc = total_capital / len(top_pools) if top_pools else 0
            for _, pool_id, _ in top_pools:
                allocations[pool_id] = equal_alloc
                
        elif self.strategy == YieldStrategy.BALANCED:
            # Weight by score
            total_score = sum(score for score, _, _ in scored_pools[:10])
            for score, pool_id, _ in scored_pools[:10]:
                if total_score > 0:
                    weight = Decimal(str(score / total_score))
                    allocations[pool_id] = total_capital * weight
                    
        elif self.strategy == YieldStrategy.AGGRESSIVE:
            # Concentrate in top 3
            top_pools = scored_pools[:3]
            weights = [0.5, 0.3, 0.2]
            for i, (_, pool_id, _) in enumerate(top_pools):
                allocations[pool_id] = total_capital * Decimal(str(weights[i]))
                
        return allocations
        
    def _filter_eligible_pools(self) -> Dict[str, YieldPool]:
        """Filter pools based on risk criteria"""
        eligible = {}
        
        for pool_id, pool in self.pools.items():
            # Minimum TVL check
            if pool.tvl_usd < self.min_pool_tvl_usd:
                continue
                
            # Audit status check
            if self.strategy == YieldStrategy.CONSERVATIVE:
                if pool.audit_status != 'audited':
                    continue
            elif self.strategy == YieldStrategy.BALANCED:
                if pool.audit_status == 'experimental':
                    continue
                    
            # Asset support check
            if pool.asset not in self.supported_assets:
                continue
                
            # Minimum yield check
            min_yield = {
                YieldStrategy.CONSERVATIVE: Decimal('0.02'),  # 2%
                YieldStrategy.BALANCED: Decimal('0.05'),      # 5%
                YieldStrategy.AGGRESSIVE: Decimal('0.10'),    # 10%
                YieldStrategy.YIELD_MAX: Decimal('0.15'),     # 15%
            }
            
            if pool.total_apy < min_yield.get(self.strategy, Decimal('0.05')):
                continue
                
            eligible[pool_id] = pool
            
        return eligible
        
    def _calculate_pool_score(self, pool: YieldPool) -> float:
        """
        Calculate risk-adjusted score for a pool
        Higher score = better allocation target
        """
        # Base score from APY
        apy_score = float(pool.total_apy) * 100  # Scale up
        
        # TVL factor (larger = safer)
        tvl_factor = min(float(pool.tvl_usd / Decimal('10_000_000')), 1.0)
        
        # Liquidity factor
        liquidity_factor = min(float(pool.liquidity_depth / Decimal('1_000_000')), 1.0)
        
        # Fee penalty
        total_fees = pool.deposit_fee + pool.withdrawal_fee + pool.performance_fee
        fee_penalty = float(total_fees) * 100
        
        # Audit bonus
        audit_bonus = {
            'audited': 0.2,
            'in_review': 0.1,
            'experimental': 0.0
        }.get(pool.audit_status, 0.0)
        
        # Calculate final score
        score = (
            apy_score * 0.5 +           # 50% weight on yield
            tvl_factor * 20 +           # 20% weight on TVL
            liquidity_factor * 15 +     # 15% weight on liquidity
            audit_bonus * 10 -          # 10% weight on audit
            fee_penalty * 5             # 5% penalty for fees
        )
        
        return max(score, 0)
        
    async def _harvest_rewards(self):
        """Harvest rewards from existing positions"""
        for pos_id, position in list(self.positions.items()):
            # Check if enough rewards accumulated
            total_rewards_usd = sum(position.rewards_earned.values())
            
            if total_rewards_usd >= self.harvest_threshold_usd:
                # Time since last harvest
                hours_since_harvest = (time.time() - position.last_harvest_time) / 3600
                
                # Don't harvest too frequently (gas optimization)
                if hours_since_harvest >= 1:
                    await self._execute_harvest(position)
                    
    async def _execute_harvest(self, position: YieldPosition):
        """Execute reward harvest transaction"""
        pool = position.pool
        
        logger.info(f"Harvesting rewards from {pool.protocol} {pool.name}")
        
        # Send harvest request
        await self.send_message(
            'yield.harvest',
            {
                'position_id': position.id,
                'protocol': pool.protocol,
                'pool_address': pool.pool_address,
                'rewards': {k: float(v) for k, v in position.rewards_earned.items()},
                'requester': self.id
            },
            priority=AgentPriority.HIGH
        )
        
        # Update position tracking
        for token, amount in position.rewards_earned.items():
            position.rewards_claimed[token] = position.rewards_claimed.get(token, Decimal('0')) + amount
            
        position.total_yield_earned += sum(position.rewards_earned.values())
        position.rewards_earned = {}
        position.last_harvest_time = time.time()
        
    async def _rebalance_positions(self, target_allocations: Dict[str, Decimal]):
        """Rebalance positions to match target allocations"""
        # Group current positions by pool
        positions_by_pool: Dict[str, List[YieldPosition]] = {}
        for pos_id, pos in self.positions.items():
            pool_id = f"{pos.pool.protocol}:{pos.pool.pool_address}"
            if pool_id not in positions_by_pool:
                positions_by_pool[pool_id] = []
            positions_by_pool[pool_id].append(pos)
            
        # Check each target allocation
        for pool_id, target_amount in target_allocations.items():
            current_positions = positions_by_pool.get(pool_id, [])
            current_amount = sum(pos.current_amount for pos in current_positions)
            
            # Check if rebalance needed
            difference = target_amount - current_amount
            
            if abs(difference) > (current_amount * self.rebalance_threshold):
                if difference > 0:
                    # Need to add more
                    await self._increase_position(pool_id, difference)
                else:
                    # Need to reduce
                    await self._decrease_position(pool_id, abs(difference))
                    
    async def _increase_position(self, pool_id: str, amount: Decimal):
        """Increase position in a pool"""
        pool = self.pools.get(pool_id)
        if not pool:
            return
            
        # Check protocol allocation limit
        protocol_positions = sum(
            pos.current_amount for pos in self.positions.values()
            if pos.pool.protocol == pool.protocol
        )
        
        total_capital = sum(self.available_capital.values())
        protocol_allocation = (protocol_positions + amount) / total_capital if total_capital > 0 else 0
        
        if protocol_allocation > self.max_protocol_allocation:
            logger.warning(f"Protocol allocation limit reached for {pool.protocol}")
            return
            
        logger.info(f"Increasing position in {pool.name} by ${amount:.2f}")
        
        # Send deposit request
        await self.send_message(
            'yield.deposit',
            {
                'pool_id': pool_id,
                'protocol': pool.protocol,
                'pool_address': pool.pool_address,
                'asset': pool.asset,
                'amount': float(amount),
                'requester': self.id
            },
            priority=AgentPriority.HIGH
        )
        
    async def _decrease_position(self, pool_id: str, amount: Decimal):
        """Decrease position in a pool"""
        pool = self.pools.get(pool_id)
        if not pool:
            return
            
        # Find position to withdraw from
        positions = [p for p in self.positions.values() 
                    if p.pool.protocol == pool.protocol and p.pool.pool_address == pool.pool_address]
        
        if not positions:
            return
            
        position = positions[0]  # Withdraw from first position
        withdraw_amount = min(amount, position.current_amount * (Decimal('1') - self.max_slippage_exit))
        
        logger.info(f"Decreasing position in {pool.name} by ${withdraw_amount:.2f}")
        
        # Send withdrawal request
        await self.send_message(
            'yield.withdraw',
            {
                'position_id': position.id,
                'protocol': pool.protocol,
                'pool_address': pool.pool_address,
                'amount': float(withdraw_amount),
                'requester': self.id
            },
            priority=AgentPriority.HIGH
        )
        
    async def _deploy_capital(self, target_allocations: Dict[str, Decimal]):
        """Deploy idle capital to best opportunities"""
        for asset, amount in self.available_capital.items():
            if amount < Decimal('100'):  # Minimum deployment
                continue
                
            # Find best pool for this asset
            best_pool = None
            best_score = 0
            
            for pool_id, pool in self.pools.items():
                if pool.asset == asset:
                    score = self._calculate_pool_score(pool)
                    if score > best_score:
                        best_score = score
                        best_pool = pool
                        
            if best_pool:
                deploy_amount = min(amount, target_allocations.get(pool_id, amount))
                await self._increase_position(f"{best_pool.protocol}:{best_pool.pool_address}", deploy_amount)
                
    async def _update_metrics(self):
        """Update agent performance metrics"""
        # Calculate total value
        total_value = Decimal('0')
        total_yield = Decimal('0')
        
        for position in self.positions.values():
            total_value += position.calculate_current_value()
            total_yield += position.total_yield_earned
            
        self.total_current_value = total_value
        
        # Calculate profit (yield minus gas costs)
        profit = float(total_yield - self.total_gas_costs)
        
        self.metrics.update_profit(profit, float(self.total_gas_costs))
        
        # Send metrics update
        await self.send_message(
            'metrics.yield_update',
            {
                'agent_id': self.id,
                'total_value': float(total_value),
                'total_yield_earned': float(total_yield),
                'active_positions': len(self.positions),
                'avg_apy': self._calculate_avg_apy()
            }
        )
        
    def _calculate_avg_apy(self) -> float:
        """Calculate weighted average APY across positions"""
        if not self.positions:
            return 0.0
            
        total_value = Decimal('0')
        weighted_apy = Decimal('0')
        
        for position in self.positions.values():
            value = position.calculate_current_value()
            total_value += value
            weighted_apy += value * position.current_apy
            
        if total_value > 0:
            return float(weighted_apy / total_value)
        return 0.0
        
    # ========== Message Handlers ==========
    
    async def _on_pool_update(self, message: AgentMessage):
        """Handle pool APY/TVL updates"""
        payload = message.payload
        pool_data = payload.get('pool', {})
        
        pool_id = f"{pool_data.get('protocol')}:{pool_data.get('address')}"
        
        self.pools[pool_id] = YieldPool(
            protocol=pool_data.get('protocol', ''),
            pool_address=pool_data.get('address', ''),
            name=pool_data.get('name', ''),
            asset=pool_data.get('asset', ''),
            base_apy=Decimal(str(pool_data.get('base_apy', 0))),
            reward_apy=Decimal(str(pool_data.get('reward_apy', 0))),
            total_apy=Decimal(str(pool_data.get('total_apy', 0))),
            tvl_usd=Decimal(str(pool_data.get('tvl', 0))),
            utilization_rate=Decimal(str(pool_data.get('utilization', 0))),
            liquidity_depth=Decimal(str(pool_data.get('liquidity', 0))),
            deposit_fee=Decimal(str(pool_data.get('deposit_fee', 0))),
            withdrawal_fee=Decimal(str(pool_data.get('withdrawal_fee', 0))),
            performance_fee=Decimal(str(pool_data.get('performance_fee', 0))),
            audit_status=pool_data.get('audit_status', 'unknown'),
            insurance_available=pool_data.get('insured', False),
            chain=pool_data.get('chain', 'ethereum')
        )
        
    async def _on_rewards_available(self, message: AgentMessage):
        """Handle notification of available rewards"""
        payload = message.payload
        position_id = payload.get('position_id')
        
        if position_id in self.positions:
            position = self.positions[position_id]
            token = payload.get('token')
            amount = Decimal(str(payload.get('amount', 0)))
            
            position.rewards_earned[token] = position.rewards_earned.get(token, Decimal('0')) + amount
            
    async def _on_capital_update(self, message: AgentMessage):
        """Handle capital availability updates"""
        payload = message.payload
        assets = payload.get('assets', {})
        
        for asset, amount in assets.items():
            self.available_capital[asset] = Decimal(str(amount))
