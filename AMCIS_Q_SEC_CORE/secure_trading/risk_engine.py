"""
Risk Engine - Trading Risk Management
=====================================

Enforces risk limits for paper trading operations.
Prevents catastrophic losses and ensures strategy discipline.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger("amcis.trading.risk")


@dataclass
class RiskLimits:
    """Risk limit configuration."""
    max_position_size: Decimal = Decimal('10000')  # USD per position
    max_positions: int = 5  # Max concurrent positions
    max_daily_loss: Decimal = Decimal('1000')  # USD
    max_drawdown_pct: float = 0.05  # 5% portfolio drawdown
    min_order_size: Decimal = Decimal('10')  # USD
    max_order_size: Decimal = Decimal('50000')  # USD
    require_stop_loss: bool = True
    max_leverage: float = 1.0  # No leverage for paper trading


class RiskCheck:
    """Result of a risk check."""
    def __init__(self, passed: bool, reason: str = ""):
        self.passed = passed
        self.reason = reason
    
    def __bool__(self):
        return self.passed


class RiskEngine:
    """
    Trading Risk Engine
    ===================
    
    Validates trades against risk limits.
    All decisions are logged for audit.
    """
    
    def __init__(self, limits: Optional[RiskLimits] = None):
        """
        Initialize risk engine.
        
        Args:
            limits: Risk limit configuration
        """
        self.limits = limits or RiskLimits()
        self.daily_pnl = Decimal('0')
        self.peak_equity = Decimal('0')
        self.current_equity = Decimal('0')
        self.violations: list = []
        self.logger = structlog.get_logger("amcis.risk_engine")
        
        self.logger.info("risk_engine_initialized",
                        max_position=float(self.limits.max_position_size),
                        max_daily_loss=float(self.limits.max_daily_loss))
    
    def check_order(
        self,
        symbol: str,
        side: str,
        amount: Decimal,
        price: Decimal,
        portfolio_value: Decimal,
        current_positions: int
    ) -> RiskCheck:
        """
        Check if order passes risk limits.
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            amount: Order amount
            price: Order price
            portfolio_value: Current portfolio value
            current_positions: Number of current positions
            
        Returns:
            RiskCheck result
        """
        order_value = amount * price
        
        # Check minimum order size
        if order_value < self.limits.min_order_size:
            return RiskCheck(False, 
                f"Order value ${order_value} below minimum ${self.limits.min_order_size}")
        
        # Check maximum order size
        if order_value > self.limits.max_order_size:
            return RiskCheck(False,
                f"Order value ${order_value} exceeds maximum ${self.limits.max_order_size}")
        
        # Check position limit for buys
        if side == 'buy':
            if current_positions >= self.limits.max_positions:
                return RiskCheck(False,
                    f"Maximum positions ({self.limits.max_positions}) reached")
            
            if order_value > self.limits.max_position_size:
                return RiskCheck(False,
                    f"Order value ${order_value} exceeds position limit ${self.limits.max_position_size}")
        
        # Check daily loss limit
        if self.daily_pnl < -self.limits.max_daily_loss:
            self.logger.critical("daily_loss_limit_exceeded",
                               daily_pnl=float(self.daily_pnl),
                               limit=float(self.limits.max_daily_loss))
            return RiskCheck(False,
                f"Daily loss limit exceeded: ${self.daily_pnl}")
        
        # Check drawdown
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
            if drawdown > Decimal(str(self.limits.max_drawdown_pct)):
                self.logger.critical("max_drawdown_exceeded",
                                   drawdown=float(drawdown),
                                   max_drawdown=self.limits.max_drawdown_pct)
                return RiskCheck(False,
                    f"Maximum drawdown exceeded: {drawdown:.2%}")
        
        self.logger.info("risk_check_passed",
                        symbol=symbol,
                        side=side,
                        amount=float(amount),
                        value=float(order_value))
        
        return RiskCheck(True, "Risk check passed")
    
    def update_equity(self, equity: Decimal):
        """
        Update current equity and track peak.
        
        Args:
            equity: Current portfolio equity
        """
        self.current_equity = equity
        
        if equity > self.peak_equity:
            self.peak_equity = equity
    
    def update_pnl(self, pnl: Decimal):
        """
        Update daily P&L.
        
        Args:
            pnl: New P&L to add
        """
        self.daily_pnl += pnl
        
        if pnl < 0:
            self.logger.warning("negative_trade",
                              pnl=float(pnl),
                              daily_pnl=float(self.daily_pnl))
    
    def reset_daily_stats(self):
        """Reset daily statistics."""
        self.daily_pnl = Decimal('0')
        self.logger.info("daily_stats_reset")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current risk status."""
        drawdown = Decimal('0')
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
        
        return {
            'daily_pnl': float(self.daily_pnl),
            'current_equity': float(self.current_equity),
            'peak_equity': float(self.peak_equity),
            'drawdown_pct': float(drawdown),
            'daily_loss_remaining': float(self.limits.max_daily_loss + self.daily_pnl),
            'limits': {
                'max_position_size': float(self.limits.max_position_size),
                'max_positions': self.limits.max_positions,
                'max_daily_loss': float(self.limits.max_daily_loss),
                'max_drawdown_pct': self.limits.max_drawdown_pct
            }
        }
    
    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed."""
        # Check daily loss
        if self.daily_pnl < -self.limits.max_daily_loss:
            return False
        
        # Check drawdown
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
            if drawdown > Decimal(str(self.limits.max_drawdown_pct)):
                return False
        
        return True
