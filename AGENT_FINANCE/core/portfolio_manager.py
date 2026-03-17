"""
AMCIS Portfolio Manager - Capital Allocation Across Strategies
Optimizes capital deployment across trading, arbitrage, and yield
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StrategyAllocation:
    name: str
    target_pct: Decimal
    current_value: Decimal
    target_value: Decimal
    performance_score: float


@dataclass
class PortfolioPosition:
    symbol: str
    strategy: str
    size: Decimal
    entry_price: Decimal
    current_price: Decimal
    value: Decimal
    unrealized_pnl: Decimal


class PortfolioManager:
    """
    Portfolio management and capital allocation
    Distributes capital across strategies based on performance
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Total capital
        self.total_capital = Decimal(str(config.get('total_capital', 100000)))
        self.cash_reserve = Decimal(str(config.get('cash_reserve', 0.1)))  # 10%
        
        # Strategy allocations
        self.allocations = {
            'trading': Decimal(str(config.get('trading_pct', 0.4))),
            'arbitrage': Decimal(str(config.get('arbitrage_pct', 0.3))),
            'market_making': Decimal(str(config.get('market_making_pct', 0.2))),
            'yield': Decimal(str(config.get('yield_pct', 0.1)))
        }
        
        # Rebalancing
        self.rebalance_threshold = Decimal(str(config.get('rebalance_threshold', 0.05)))
        self.auto_rebalance = config.get('auto_rebalance', True)
        
        # State
        self.positions: List[PortfolioPosition] = []
        self.strategy_values: Dict[str, Decimal] = {k: Decimal('0') for k in self.allocations}
        self.performance_history: Dict[str, List[Decimal]] = {k: [] for k in self.allocations}
        
        # Performance tracking
        self.total_pnl = Decimal('0')
        self.realized_pnl = Decimal('0')
        self.unrealized_pnl = Decimal('0')
        
    async def update_allocation(self, strategy: str, value: Decimal):
        """Update current allocation for a strategy"""
        self.strategy_values[strategy] = value
        
    async def record_performance(self, strategy: str, pnl: Decimal):
        """Record strategy performance"""
        self.performance_history[strategy].append(pnl)
        
        # Keep last 30 days
        if len(self.performance_history[strategy]) > 30:
            self.performance_history[strategy].pop(0)
            
    async def rebalance(self) -> List[Dict]:
        """
        Rebalance capital across strategies
        Returns list of rebalancing actions
        """
        actions = []
        
        total_deployed = sum(self.strategy_values.values())
        available_capital = self.total_capital * (Decimal('1') - self.cash_reserve)
        
        for strategy, target_pct in self.allocations.items():
            current_value = self.strategy_values.get(strategy, Decimal('0'))
            target_value = available_capital * target_pct
            
            deviation = (current_value - target_value) / target_value if target_value > 0 else Decimal('0')
            
            if abs(deviation) > self.rebalance_threshold:
                adjustment = target_value - current_value
                
                actions.append({
                    'strategy': strategy,
                    'current': float(current_value),
                    'target': float(target_value),
                    'adjustment': float(adjustment),
                    'action': 'increase' if adjustment > 0 else 'decrease'
                })
                
                logger.info(f"Rebalancing {strategy}: {current_value} -> {target_value} ({adjustment:+.2f})")
                
        return actions
        
    async def optimize_allocations(self):
        """
        Optimize allocations based on Sharpe ratios
        Moves capital to better performing strategies
        """
        scores = {}
        
        for strategy, history in self.performance_history.items():
            if len(history) < 7:  # Need at least 7 days
                continue
                
            # Calculate Sharpe-like ratio
            returns = [float(r) for r in history]
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5
            
            if std_dev > 0:
                sharpe = avg_return / std_dev
            else:
                sharpe = avg_return
                
            scores[strategy] = max(sharpe, 0)  # No negative scores
            
        if not scores:
            return
            
        # Normalize scores to allocations
        total_score = sum(scores.values())
        if total_score == 0:
            return
            
        # Update target allocations (gradually shift)
        for strategy, score in scores.items():
            new_allocation = Decimal(str(score / total_score))
            
            # Gradual shift (don't change by more than 10% at a time)
            current = self.allocations[strategy]
            max_change = Decimal('0.1')
            
            if new_allocation > current + max_change:
                new_allocation = current + max_change
            elif new_allocation < current - max_change:
                new_allocation = current - max_change
                
            self.allocations[strategy] = new_allocation
            
        logger.info(f"Optimized allocations: {self.allocations}")
        
    def get_allocation_for_strategy(self, strategy: str) -> Decimal:
        """Get target allocation for a strategy"""
        return self.allocations.get(strategy, Decimal('0')) * self.total_capital
        
    def get_available_capital(self, strategy: str) -> Decimal:
        """Get available capital for a strategy"""
        target = self.get_allocation_for_strategy(strategy)
        current = self.strategy_values.get(strategy, Decimal('0'))
        return max(target - current, Decimal('0'))
        
    async def add_position(self, position: PortfolioPosition):
        """Add a new position to portfolio"""
        self.positions.append(position)
        
        # Update strategy value
        if position.strategy in self.strategy_values:
            self.strategy_values[position.strategy] += position.value
            
    async def update_position(self, symbol: str, current_price: Decimal):
        """Update position with current price"""
        for pos in self.positions:
            if pos.symbol == symbol:
                pos.current_price = current_price
                pos.value = pos.size * current_price
                pos.unrealized_pnl = (current_price - pos.entry_price) * pos.size
                
    async def remove_position(self, symbol: str, realized_pnl: Decimal):
        """Remove position and record P&L"""
        for i, pos in enumerate(self.positions):
            if pos.symbol == symbol:
                self.realized_pnl += realized_pnl
                self.total_pnl += realized_pnl
                
                # Update strategy value
                if pos.strategy in self.strategy_values:
                    self.strategy_values[pos.strategy] -= pos.value
                    
                self.positions.pop(i)
                break
                
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        total_value = sum(self.strategy_values.values())
        cash = self.total_capital - total_value
        
        self.unrealized_pnl = sum(p.unrealized_pnl for p in self.positions)
        
        return {
            'total_capital': float(self.total_capital),
            'deployed': float(total_value),
            'cash': float(cash),
            'total_pnl': float(self.total_pnl),
            'realized_pnl': float(self.realized_pnl),
            'unrealized_pnl': float(self.unrealized_pnl),
            'allocations': {
                k: {
                    'target_pct': float(v),
                    'target_value': float(self.get_allocation_for_strategy(k)),
                    'current_value': float(self.strategy_values.get(k, Decimal('0')))
                }
                for k, v in self.allocations.items()
            },
            'positions': [
                {
                    'symbol': p.symbol,
                    'strategy': p.strategy,
                    'size': float(p.size),
                    'value': float(p.value),
                    'unrealized_pnl': float(p.unrealized_pnl)
                }
                for p in self.positions
            ]
        }
