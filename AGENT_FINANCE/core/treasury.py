"""
AMCIS Treasury Management System
Autonomous capital allocation and risk management for AI agent operations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from collections import defaultdict
import time

from core.agent_base import BaseAgent, AgentMessage, AgentPriority

logger = logging.getLogger(__name__)


class AllocationStrategy(Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass
class TreasuryAllocation:
    """Capital allocation across strategies"""
    # Asset allocation
    stablecoins_pct: Decimal = Decimal('0.30')  # USDC, USDT, DAI
    major_crypto_pct: Decimal = Decimal('0.40')  # BTC, ETH
    alt_crypto_pct: Decimal = Decimal('0.15')    # Other tokens
    cash_reserve_pct: Decimal = Decimal('0.15')  # Unallocated
    
    # Strategy allocation
    trading_pct: Decimal = Decimal('0.35')       # Active trading
    yield_farming_pct: Decimal = Decimal('0.30') # Yield generation
    arbitrage_pct: Decimal = Decimal('0.20')     # Arbitrage operations
    reserve_pct: Decimal = Decimal('0.15')       # Emergency reserve


@dataclass
class Wallet:
    """Wallet balance tracking"""
    address: str
    chain: str
    wallet_type: str  # 'hot', 'warm', 'cold'
    
    balances: Dict[str, Decimal] = field(default_factory=dict)
    balances_usd: Dict[str, Decimal] = field(default_factory=dict)
    
    total_value_usd: Decimal = Decimal('0')
    last_updated: float = field(default_factory=time.time)
    
    daily_limit_usd: Decimal = Decimal('100000')
    daily_used_usd: Decimal = Decimal('0')
    daily_reset_at: float = field(default_factory=time.time)


class TreasuryManager(BaseAgent):
    """
    Autonomous treasury manager that optimizes capital allocation
    across trading, yield farming, and arbitrage operations.
    """
    
    def __init__(self, name: str, message_bus, config: Optional[Dict] = None):
        super().__init__(name, "treasury_manager", message_bus, config)
        
        # Configuration
        self.strategy = AllocationStrategy(config.get('strategy', 'balanced'))
        self.rebalance_threshold = Decimal(str(config.get('rebalance_threshold', 0.05)))  # 5%
        self.emergency_reserve = Decimal(str(config.get('emergency_reserve', 0.10)))  # 10%
        
        # Capital limits
        self.max_daily_drawdown = Decimal(str(config.get('max_daily_drawdown', 0.05)))  # 5%
        self.max_position_size = Decimal(str(config.get('max_position_size', 1000000)))  # $1M
        
        # Allocation targets based on strategy
        self.target_allocation = self._get_allocation_for_strategy(self.strategy)
        
        # State
        self.wallets: Dict[str, Wallet] = {}
        self.agent_allocations: Dict[str, Decimal] = {}  # agent_id -> allocated capital
        self.agent_performance: Dict[str, List[Dict]] = defaultdict(list)
        
        # Revenue tracking
        self.daily_revenue = Decimal('0')
        self.daily_costs = Decimal('0')
        self.monthly_revenue = Decimal('0')
        self.total_aum = Decimal('0')  # Assets under management
        
        # Last rebalance
        self.last_rebalance = 0
        self.rebalance_interval = 3600  # 1 hour
        
        # Message handlers
        self._message_handlers = {
            'treasury.get_balance': self._on_balance_request,
            'treasury.get_available': self._on_available_request,
            'treasury.transfer': self._on_transfer_request,
            'metrics.agent_update': self._on_agent_metrics,
            'risk.emergency': self._on_emergency,
        }
        
    def _get_allocation_for_strategy(self, strategy: AllocationStrategy) -> TreasuryAllocation:
        """Get allocation targets for strategy"""
        allocations = {
            AllocationStrategy.CONSERVATIVE: TreasuryAllocation(
                stablecoins_pct=Decimal('0.50'),
                major_crypto_pct=Decimal('0.30'),
                alt_crypto_pct=Decimal('0.05'),
                cash_reserve_pct=Decimal('0.15'),
                trading_pct=Decimal('0.20'),
                yield_farming_pct=Decimal('0.40'),
                arbitrage_pct=Decimal('0.15'),
                reserve_pct=Decimal('0.25')
            ),
            AllocationStrategy.BALANCED: TreasuryAllocation(
                stablecoins_pct=Decimal('0.30'),
                major_crypto_pct=Decimal('0.40'),
                alt_crypto_pct=Decimal('0.15'),
                cash_reserve_pct=Decimal('0.15'),
                trading_pct=Decimal('0.35'),
                yield_farming_pct=Decimal('0.30'),
                arbitrage_pct=Decimal('0.20'),
                reserve_pct=Decimal('0.15')
            ),
            AllocationStrategy.AGGRESSIVE: TreasuryAllocation(
                stablecoins_pct=Decimal('0.15'),
                major_crypto_pct=Decimal('0.35'),
                alt_crypto_pct=Decimal('0.30'),
                cash_reserve_pct=Decimal('0.20'),
                trading_pct=Decimal('0.45'),
                yield_farming_pct=Decimal('0.20'),
                arbitrage_pct=Decimal('0.25'),
                reserve_pct=Decimal('0.10')
            )
        }
        return allocations.get(strategy, allocations[AllocationStrategy.BALANCED])
        
    async def _setup(self):
        """Initialize treasury"""
        # Load wallets
        await self._load_wallets()
        
        # Calculate total AUM
        await self._update_aum()
        
        logger.info(f"Treasury manager initialized with ${self.total_aum:,.2f} AUM")
        
    async def _load_wallets(self):
        """Load wallet balances from database/blockchain"""
        # Would query database and blockchain RPCs
        # For now, initialize empty
        self.wallets = {}
        
    async def _update_aum(self):
        """Update assets under management"""
        total = Decimal('0')
        for wallet in self.wallets.values():
            total += wallet.total_value_usd
        self.total_aum = total
        
    async def execute_cycle(self):
        """Main treasury management cycle"""
        # Update balances
        await self._update_balances()
        
        # Check daily limits
        await self._check_daily_limits()
        
        # Rebalance if needed
        if time.time() - self.last_rebalance > self.rebalance_interval:
            await self._rebalance_allocations()
            
        # Optimize agent capital allocations
        await self._optimize_agent_allocations()
        
        # Generate treasury report
        await self._generate_report()
        
    async def _update_balances(self):
        """Update all wallet balances"""
        for wallet in self.wallets.values():
            # Query blockchain for balances
            # Would use Web3, ethers.js equivalent, etc.
            wallet.last_updated = time.time()
            
        await self._update_aum()
        
    async def _check_daily_limits(self):
        """Check and reset daily trading limits"""
        now = time.time()
        
        for wallet in self.wallets.values():
            if now - wallet.daily_reset_at > 86400:  # 24 hours
                wallet.daily_used_usd = Decimal('0')
                wallet.daily_reset_at = now
                
        # Check drawdown
        daily_pnl = self.daily_revenue - self.daily_costs
        if self.total_aum > 0:
            drawdown_pct = daily_pnl / self.total_aum
            if drawdown_pct < -self.max_daily_drawdown:
                logger.warning(f"Daily drawdown limit reached: {drawdown_pct:.2%}")
                await self._trigger_risk_control()
                
    async def _rebalance_allocations(self):
        """Rebalance capital across asset classes and strategies"""
        if self.total_aum == 0:
            return
            
        logger.info("Starting portfolio rebalancing...")
        
        # Calculate current allocation
        current = await self._calculate_current_allocation()
        target = self.target_allocation
        
        # Check if rebalance needed
        deviations = {
            'stablecoins': abs(current['stablecoins_pct'] - target.stablecoins_pct),
            'major_crypto': abs(current['major_crypto_pct'] - target.major_crypto_pct),
            'trading': abs(current['trading_pct'] - target.trading_pct),
            'yield': abs(current['yield_farming_pct'] - target.yield_farming_pct),
            'arbitrage': abs(current['arbitrage_pct'] - target.arbitrage_pct),
        }
        
        needs_rebalance = any(d > self.rebalance_threshold for d in deviations.values())
        
        if not needs_rebalance:
            logger.info("No rebalancing needed")
            return
            
        # Execute rebalancing trades
        for category, deviation in deviations.items():
            if deviation > self.rebalance_threshold:
                await self._execute_rebalance_trade(category, current, target)
                
        self.last_rebalance = time.time()
        logger.info("Portfolio rebalancing completed")
        
    async def _calculate_current_allocation(self) -> Dict[str, Decimal]:
        """Calculate current capital allocation"""
        if self.total_aum == 0:
            return {
                'stablecoins_pct': Decimal('0'),
                'major_crypto_pct': Decimal('0'),
                'trading_pct': Decimal('0'),
                'yield_farming_pct': Decimal('0'),
                'arbitrage_pct': Decimal('0'),
            }
            
        # Calculate by asset type
        stablecoins = Decimal('0')
        major_crypto = Decimal('0')
        
        for wallet in self.wallets.values():
            for asset, balance in wallet.balances_usd.items():
                if asset in ['USDC', 'USDT', 'DAI']:
                    stablecoins += balance
                elif asset in ['BTC', 'ETH']:
                    major_crypto += balance
                    
        # Calculate by strategy (allocated to agents)
        trading_alloc = Decimal('0')
        yield_alloc = Decimal('0')
        arb_alloc = Decimal('0')
        
        for agent_id, amount in self.agent_allocations.items():
            # Would determine agent type from registry
            if 'trading' in agent_id.lower():
                trading_alloc += amount
            elif 'yield' in agent_id.lower():
                yield_alloc += amount
            elif 'arbitrage' in agent_id.lower():
                arb_alloc += amount
                
        return {
            'stablecoins_pct': stablecoins / self.total_aum,
            'major_crypto_pct': major_crypto / self.total_aum,
            'trading_pct': trading_alloc / self.total_aum,
            'yield_farming_pct': yield_alloc / self.total_aum,
            'arbitrage_pct': arb_alloc / self.total_aum,
        }
        
    async def _execute_rebalance_trade(self, category: str, current: Dict, target: TreasuryAllocation):
        """Execute a rebalancing trade"""
        # Determine target and current values
        target_values = {
            'stablecoins': target.stablecoins_pct * self.total_aum,
            'major_crypto': target.major_crypto_pct * self.total_aum,
            'trading': target.trading_pct * self.total_aum,
            'yield': target.yield_farming_pct * self.total_aum,
            'arbitrage': target.arbitrage_pct * self.total_aum,
        }
        
        current_values = {
            'stablecoins': current['stablecoins_pct'] * self.total_aum,
            'major_crypto': current['major_crypto_pct'] * self.total_aum,
            'trading': current['trading_pct'] * self.total_aum,
            'yield': current['yield_farming_pct'] * self.total_aum,
            'arbitrage': current['arbitrage_pct'] * self.total_aum,
        }
        
        diff = target_values[category] - current_values[category]
        
        if abs(diff) < 1000:  # Minimum $1000 rebalance
            return
            
        action = "increase" if diff > 0 else "decrease"
        logger.info(f"Rebalancing: {action} {category} by ${abs(diff):,.2f}")
        
        # Would execute actual trades here
        # For now, just log the intention
        
    async def _optimize_agent_allocations(self):
        """Optimize capital allocation to agents based on performance"""
        if not self.agent_performance:
            return
            
        # Calculate performance scores
        scores = {}
        for agent_id, history in self.agent_performance.items():
            if len(history) < 3:
                continue
                
            # Calculate Sharpe-like ratio
            returns = [h.get('return_pct', 0) for h in history[-30:]]  # Last 30 data points
            if not returns:
                continue
                
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5
            
            if std_dev > 0:
                sharpe = avg_return / std_dev
            else:
                sharpe = avg_return
                
            # Win rate
            wins = sum(1 for h in history[-30:] if h.get('profit', 0) > 0)
            win_rate = wins / min(len(history), 30)
            
            # Combined score
            scores[agent_id] = sharpe * 0.6 + win_rate * 0.4
            
        if not scores:
            return
            
        # Calculate new allocations based on scores
        total_score = sum(abs(s) for s in scores.values())
        if total_score == 0:
            return
            
        # Available capital (excluding emergency reserve)
        available = self.total_aum * (Decimal('1') - self.emergency_reserve)
        
        # Strategy limits
        strategy_limits = {
            'trading': self.target_allocation.trading_pct * self.total_aum,
            'yield': self.target_allocation.yield_farming_pct * self.total_aum,
            'arbitrage': self.target_allocation.arbitrage_pct * self.total_aum,
        }
        
        new_allocations = {}
        for agent_id, score in scores.items():
            # Determine agent type and limit
            agent_type = 'trading'  # Default
            if 'yield' in agent_id.lower():
                agent_type = 'yield'
            elif 'arbitrage' in agent_id.lower():
                agent_type = 'arbitrage'
                
            limit = strategy_limits.get(agent_type, available * Decimal('0.3'))
            
            # Proportional allocation
            alloc = available * Decimal(str(abs(score) / total_score))
            alloc = min(alloc, limit * Decimal('0.5'))  # Max 50% of strategy allocation per agent
            
            new_allocations[agent_id] = alloc
            
        # Apply new allocations
        for agent_id, amount in new_allocations.items():
            current = self.agent_allocations.get(agent_id, Decimal('0'))
            
            if abs(amount - current) > (self.total_aum * Decimal('0.02')):  # 2% threshold
                await self._adjust_agent_allocation(agent_id, amount)
                
    async def _adjust_agent_allocation(self, agent_id: str, new_amount: Decimal):
        """Adjust capital allocation to an agent"""
        current = self.agent_allocations.get(agent_id, Decimal('0'))
        delta = new_amount - current
        
        if delta > 0:
            # Allocate more capital
            logger.info(f"Increasing allocation to {agent_id}: ${delta:,.2f}")
            await self.send_message(
                'treasury.allocate',
                {
                    'agent_id': agent_id,
                    'amount': float(delta),
                    'total_allocation': float(new_amount)
                },
                priority=AgentPriority.HIGH
            )
        else:
            # Reduce allocation
            logger.info(f"Reducing allocation from {agent_id}: ${abs(delta):,.2f}")
            await self.send_message(
                'treasury.deallocate',
                {
                    'agent_id': agent_id,
                    'amount': float(abs(delta)),
                    'total_allocation': float(new_amount)
                },
                priority=AgentPriority.HIGH
            )
            
        self.agent_allocations[agent_id] = new_amount
        
    async def _trigger_risk_control(self):
        """Trigger emergency risk controls"""
        logger.critical("EMERGENCY RISK CONTROL TRIGGERED")
        
        # Stop all trading agents
        await self.send_message(
            'risk.stop_trading',
            {'broadcast': True, 'reason': 'daily_drawdown_limit'},
            priority=AgentPriority.CRITICAL
        )
        
        # Move capital to safe reserves
        for agent_id in list(self.agent_allocations.keys()):
            await self._adjust_agent_allocation(agent_id, Decimal('0'))
            
    async def _generate_report(self):
        """Generate treasury status report"""
        report = {
            'timestamp': time.time(),
            'total_aum': float(self.total_aum),
            'daily_revenue': float(self.daily_revenue),
            'daily_costs': float(self.daily_costs),
            'daily_pnl': float(self.daily_revenue - self.daily_costs),
            'agent_allocations': {k: float(v) for k, v in self.agent_allocations.items()},
            'strategy': self.strategy.value
        }
        
        await self.send_message(
            'treasury.report',
            report,
            priority=AgentPriority.NORMAL
        )
        
    # ========== Message Handlers ==========
    
    async def _on_balance_request(self, message: AgentMessage):
        """Handle balance requests from agents"""
        payload = message.payload
        exchange = payload.get('exchange')
        requester = payload.get('requester')
        
        # Find wallet for exchange
        balance = Decimal('0')
        for wallet in self.wallets.values():
            if exchange in wallet.address.lower() or exchange in str(wallet.balances).lower():
                balance = wallet.total_value_usd
                break
                
        # Send response
        await self.send_message(
            'treasury.balance_response',
            {
                'requester': requester,
                'exchange': exchange,
                'balance': float(balance)
            },
            recipient=requester
        )
        
    async def _on_available_request(self, message: AgentMessage):
        """Handle available capital requests"""
        payload = message.payload
        requester = payload.get('requester')
        purpose = payload.get('purpose', 'general')
        
        # Calculate available based on purpose
        available = self.total_aum * (Decimal('1') - self.emergency_reserve)
        
        # Subtract already allocated
        allocated = sum(self.agent_allocations.values())
        available -= allocated
        
        # Send response
        await self.send_message(
            'treasury.capital_update',
            {
                'requester': requester,
                'assets': {'USD': float(available)},  # Simplified
                'purpose': purpose
            },
            recipient=requester
        )
        
    async def _on_transfer_request(self, message: AgentMessage):
        """Handle transfer requests"""
        payload = message.payload
        # Would execute actual transfers
        # For now, just acknowledge
        logger.info(f"Transfer requested: {payload}")
        
    async def _on_agent_metrics(self, message: AgentMessage):
        """Handle performance updates from agents"""
        payload = message.payload
        agent_id = payload.get('agent_id')
        
        if agent_id:
            self.agent_performance[agent_id].append({
                'timestamp': time.time(),
                'profit': payload.get('profit', 0),
                'return_pct': payload.get('return_pct', 0),
                'trades': payload.get('trades', 0)
            })
            
            # Update revenue tracking
            profit = Decimal(str(payload.get('profit', 0)))
            costs = Decimal(str(payload.get('costs', 0)))
            
            self.daily_revenue += profit
            self.daily_costs += costs
            self.monthly_revenue += profit
            
    async def _on_emergency(self, message: AgentMessage):
        """Handle emergency signals"""
        payload = message.payload
        severity = payload.get('severity', 'medium')
        
        if severity == 'critical':
            await self._trigger_risk_control()
