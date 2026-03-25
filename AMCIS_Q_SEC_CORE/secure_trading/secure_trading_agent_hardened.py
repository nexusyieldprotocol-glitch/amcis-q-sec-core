"""
Secure Trading Agent - Hardened with Persistence
================================================

Enhanced trading agent with:
- Database persistence for trades and state
- Vault integration for secrets
- Crash recovery capability
- Signed audit logging
- Rate limiting and input validation

Status: EXPERIMENTAL - Paper trading only
"""

import asyncio
import hashlib
import hmac
import json
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import structlog

from core.amcis_kernel import AMCISKernel, SecurityEvent
from crypto.amcis_hybrid_pqc import ProductionCryptoProvider
from infrastructure.database import DatabaseManager, TradeRecord, AgentStateRecord
from infrastructure.vault import VaultManager, SecretType
from infrastructure.audit import AuditLogger

from .paper_exchange import PaperExchange, OrderSide, OrderType
from .risk_engine import RiskEngine, RiskLimits

logger = structlog.get_logger("amcis.secure_trading_hardened")


@dataclass
class TradeSignal:
    """Trading signal from strategy."""
    symbol: str
    side: str
    amount: Decimal
    confidence: float
    strategy: str
    metadata: Dict[str, Any]


class SecureTradingAgentHardened:
    """
    Hardened Secure Trading Agent
    =============================
    
    Paper trading agent with full persistence and security:
    - All trades stored in database
    - Secrets managed by Vault
    - Audit trail for all actions
    - Automatic crash recovery
    - Rate limiting and input validation
    
    NO REAL CAPITAL - Paper trading simulation only.
    """
    
    def __init__(
        self,
        kernel: AMCISKernel,
        database: DatabaseManager,
        vault: VaultManager,
        audit: Optional[AuditLogger] = None,
        name: str = "paper_trader_001",
        initial_balance: Decimal = Decimal('100000'),
        risk_limits: Optional[RiskLimits] = None
    ):
        """
        Initialize hardened trading agent.
        
        Args:
            kernel: AMCIS security kernel
            database: Database manager
            vault: Vault manager
            audit: Audit logger
            name: Agent identifier
            initial_balance: Starting paper money
            risk_limits: Risk configuration
        """
        self.kernel = kernel
        self.database = database
        self.vault = vault
        self.name = name
        self.agent_id = f"agent_{name}_{int(time.time())}"
        
        # Initialize crypto identity
        self.crypto = ProductionCryptoProvider()
        self.keypair = self.crypto.generate_keypair()
        
        # Initialize audit logger if not provided
        self.audit = audit or AuditLogger(database)
        
        # Initialize paper exchange
        self.exchange = PaperExchange(initial_balance=initial_balance)
        
        # Initialize risk engine
        self.risk = RiskEngine(limits=risk_limits or RiskLimits())
        
        # Trading state
        self.active = False
        self.trading_pairs = ['BTC-USD', 'ETH-USD']
        self.check_interval = 60
        
        # Rate limiting
        self._rate_limits = {
            'orders_per_minute': 10,
            'api_calls_per_minute': 30
        }
        self._order_times: List[float] = []
        self._api_call_times: List[float] = []
        
        # Statistics
        self.cycles_run = 0
        self.signals_generated = 0
        self.orders_placed = 0
        self.trades_executed = 0
        
        # Crash recovery
        self._last_state_save = 0
        self._state_save_interval = 30  # seconds
        
        self.logger = structlog.get_logger("amcis.secure_trader_hardened")
        self.logger.info("hardened_agent_initialized",
                        agent_id=self.agent_id,
                        name=name)
    
    async def initialize(self) -> bool:
        """Initialize agent with persistence."""
        try:
            # Save crypto identity to database
            self.database.save_crypto_identity(
                self.agent_id,
                self.keypair.kem_public_bytes,
                self.keypair.sig_public_bytes
            )
            
            # Save signing key to vault
            self.vault.store_secret(
                f"{self.agent_id}_signing_key",
                self.audit.signing_key,
                SecretType.KERNEL_MASTER_KEY,
                {'agent_id': self.agent_id}
            )
            
            # Register with kernel
            self.kernel.register_module(self.name, self)
            
            # Log initialization
            await self._log_audit('agent_initialized', {
                'agent_id': self.agent_id,
                'type': 'paper_trading_hardened',
                'public_key_hash': self._get_key_hash()
            })
            
            self.logger.info("agent_initialized_with_persistence")
            return True
            
        except Exception as e:
            self.logger.error("failed_to_initialize_agent", error=str(e))
            return False
    
    def _get_key_hash(self) -> str:
        """Get hash of public key for identification."""
        return hashlib.sha3_256(self.keypair.kem_public_bytes).hexdigest()[:16]
    
    async def _log_audit(self, event_type: str, data: Dict[str, Any], 
                        severity: int = 1):
        """Log signed audit event."""
        # Log to audit system
        self.audit.log_event(
            event_type=event_type,
            data=data,
            source_module=self.name,
            severity=severity,
            correlation_id=self.agent_id[:8]
        )
        
        # Also emit to kernel
        await self.kernel.emit_event(
            event_type=SecurityEvent.THREAT_INTELLIGENCE,
            source_module=self.name,
            severity=severity,
            data={'event': event_type, **data}
        )
    
    def _check_rate_limit(self, limit_type: str) -> bool:
        """Check if action is within rate limit."""
        now = time.time()
        
        if limit_type == 'orders':
            # Clean old entries
            cutoff = now - 60
            self._order_times = [t for t in self._order_times if t > cutoff]
            
            if len(self._order_times) >= self._rate_limits['orders_per_minute']:
                self.logger.warning("order_rate_limit_exceeded")
                return False
            
            self._order_times.append(now)
            return True
        
        elif limit_type == 'api_calls':
            cutoff = now - 60
            self._api_call_times = [t for t in self._api_call_times if t > cutoff]
            
            if len(self._api_call_times) >= self._rate_limits['api_calls_per_minute']:
                return False
            
            self._api_call_times.append(now)
            return True
        
        return True
    
    def _validate_input(self, symbol: str, amount: Decimal, 
                       side: str) -> bool:
        """Validate trading inputs."""
        # Validate symbol
        valid_symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD']
        if symbol not in valid_symbols:
            self.logger.warning("invalid_symbol", symbol=symbol)
            return False
        
        # Validate amount
        if amount <= 0:
            self.logger.warning("invalid_amount", amount=str(amount))
            return False
        
        if amount > Decimal('1000'):  # Max $1000 per order
            self.logger.warning("amount_exceeds_limit", amount=str(amount))
            return False
        
        # Validate side
        if side not in ['buy', 'sell']:
            self.logger.warning("invalid_side", side=side)
            return False
        
        return True
    
    async def recover_state(self) -> bool:
        """
        Recover agent state from database after crash.
        
        Returns:
            True if state recovered
        """
        try:
            state = self.database.load_agent_state(self.agent_id)
            
            if state:
                # Restore exchange state
                self.exchange.portfolio.cash = Decimal(str(state.cash))
                self.risk.daily_pnl = Decimal(str(state.daily_pnl))
                self.trades_executed = state.trades_executed
                
                # Restore positions
                for symbol, pos_data in state.positions.items():
                    from .paper_exchange import Position
                    self.exchange.portfolio.positions[symbol] = Position(
                        symbol=symbol,
                        amount=Decimal(str(pos_data['amount'])),
                        avg_entry_price=Decimal(str(pos_data['avg_entry_price'])),
                        realized_pnl=Decimal(str(pos_data.get('realized_pnl', 0)))
                    )
                
                await self._log_audit('agent_state_recovered', {
                    'agent_id': self.agent_id,
                    'cash': float(state.cash),
                    'positions': len(state.positions),
                    'timestamp': state.timestamp
                })
                
                self.logger.info("state_recovered_from_database",
                               cash=float(state.cash),
                               positions=len(state.positions))
                return True
            
            return False
            
        except Exception as e:
            self.logger.error("failed_to_recover_state", error=str(e))
            return False
    
    async def _save_state(self):
        """Save agent state to database."""
        try:
            portfolio = await self.exchange.get_portfolio_summary()
            positions = await self.exchange.get_all_positions()
            
            # Build positions dict
            positions_data = {}
            for symbol, pos in positions.items():
                positions_data[symbol] = {
                    'amount': float(pos.amount),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'realized_pnl': float(pos.realized_pnl)
                }
            
            # Calculate checksum
            checksum_data = f"{self.agent_id}:{portfolio['cash']}:{json.dumps(positions_data, sort_keys=True)}"
            checksum = hashlib.sha3_256(checksum_data.encode()).hexdigest()
            
            state = AgentStateRecord(
                agent_id=self.agent_id,
                timestamp=time.time(),
                cash=portfolio['cash'],
                positions=positions_data,
                daily_pnl=float(self.risk.daily_pnl),
                trades_executed=self.trades_executed,
                checksum=checksum
            )
            
            self.database.save_agent_state(state)
            self._last_state_save = time.time()
            
        except Exception as e:
            self.logger.error("failed_to_save_state", error=str(e))
    
    async def start(self):
        """Start trading agent with persistence."""
        # Try to recover state
        recovered = await self.recover_state()
        
        self.active = True
        
        await self._log_audit('agent_started', {
            'agent_id': self.agent_id,
            'state_recovered': recovered
        })
        
        self.logger.info("trading_agent_started", recovered=recovered)
        
        # Start trading loop
        while self.active:
            try:
                await self._trading_cycle()
                
                # Save state periodically
                if time.time() - self._last_state_save > self._state_save_interval:
                    await self._save_state()
                
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                self.logger.error("trading_cycle_error", error=str(e))
                await self._save_state()  # Save on error
                await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Stop trading agent and save final state."""
        self.active = False
        
        # Save final state
        await self._save_state()
        
        # Get final summary
        summary = await self.exchange.get_portfolio_summary()
        
        await self._log_audit('agent_stopped', {
            'agent_id': self.agent_id,
            'final_equity': summary['total_equity'],
            'total_pnl': summary['total_pnl'],
            'trades_executed': self.trades_executed
        })
        
        self.logger.info("trading_agent_stopped",
                        final_equity=summary['total_equity'])
    
    async def _trading_cycle(self):
        """Execute one trading cycle with persistence."""
        self.cycles_run += 1
        
        self.logger.debug("trading_cycle_started", cycle=self.cycles_run)
        
        # Update portfolio value for risk tracking
        summary = await self.exchange.get_portfolio_summary()
        self.risk.update_equity(Decimal(str(summary['total_equity'])))
        
        # Check if trading allowed
        if not self.risk.is_trading_allowed():
            self.logger.warning("trading_disabled_by_risk_engine")
            return
        
        # Check API rate limit
        if not self._check_rate_limit('api_calls'):
            self.logger.warning("api_rate_limit_hit")
            return
        
        # Generate signals for each pair
        for symbol in self.trading_pairs:
            signal = await self._generate_signal(symbol)
            
            if signal and self._validate_input(
                signal.symbol, signal.amount, signal.side
            ):
                self.signals_generated += 1
                await self._process_signal(signal)
        
        self.logger.debug("trading_cycle_completed", cycle=self.cycles_run)
    
    async def _generate_signal(self, symbol: str) -> Optional[TradeSignal]:
        """Generate trading signal for symbol."""
        price = await self.exchange.get_price(symbol)
        if not price:
            return None
        
        position = await self.exchange.get_position(symbol)
        
        if position:
            current_value = position.amount * price
            entry_value = position.amount * position.avg_entry_price
            pnl_pct = (current_value - entry_value) / entry_value
            
            if pnl_pct > Decimal('0.05'):  # 5% profit
                return TradeSignal(
                    symbol=symbol,
                    side='sell',
                    amount=position.amount,
                    confidence=0.7,
                    strategy='take_profit',
                    metadata={'pnl_pct': float(pnl_pct)}
                )
            
            if pnl_pct < Decimal('-0.02'):  # 2% loss
                return TradeSignal(
                    symbol=symbol,
                    side='sell',
                    amount=position.amount,
                    confidence=0.8,
                    strategy='stop_loss',
                    metadata={'pnl_pct': float(pnl_pct)}
                )
        else:
            portfolio = await self.exchange.get_portfolio_summary()
            
            if Decimal(str(portfolio['cash'])) > Decimal('1000'):
                amount = Decimal('1000') / price
                
                return TradeSignal(
                    symbol=symbol,
                    side='buy',
                    amount=amount,
                    confidence=0.6,
                    strategy='entry',
                    metadata={'entry_price': float(price)}
                )
        
        return None
    
    async def _process_signal(self, signal: TradeSignal):
        """Process trading signal through risk engine and execute."""
        price = await self.exchange.get_price(signal.symbol)
        if not price:
            return
        
        portfolio = await self.exchange.get_portfolio_summary()
        positions = await self.exchange.get_all_positions()
        
        risk_check = self.risk.check_order(
            symbol=signal.symbol,
            side=signal.side,
            amount=signal.amount,
            price=price,
            portfolio_value=Decimal(str(portfolio['total_equity'])),
            current_positions=len(positions)
        )
        
        if not risk_check:
            await self._log_audit('risk_check_failed', {
                'symbol': signal.symbol,
                'reason': risk_check.reason
            }, severity=4)
            return
        
        await self._execute_order(signal, price)
    
    async def _execute_order(self, signal: TradeSignal, price: Decimal):
        """Execute order on paper exchange with persistence."""
        if not self._check_rate_limit('orders'):
            self.logger.warning("order_rate_limit_exceeded")
            return
        
        try:
            side = OrderSide.BUY if signal.side == 'buy' else OrderSide.SELL
            
            order = await self.exchange.place_order(
                symbol=signal.symbol,
                side=side,
                amount=signal.amount,
                order_type=OrderType.MARKET
            )
            
            self.orders_placed += 1
            
            if order.filled_price:
                self.trades_executed += 1
                
                # Calculate P&L
                pnl = 0.0
                if signal.side == 'sell':
                    position = await self.exchange.get_position(signal.symbol)
                    if position:
                        pnl = float(position.realized_pnl)
                        self.risk.update_pnl(Decimal(str(pnl)))
                
                # Create and save trade record
                trade = TradeRecord(
                    id=order.id,
                    agent_id=self.agent_id,
                    symbol=signal.symbol,
                    side=signal.side,
                    amount=float(signal.amount),
                    price=float(order.filled_price),
                    value=float(signal.amount * order.filled_price),
                    pnl=pnl,
                    timestamp=order.filled_at,
                    strategy=signal.strategy,
                    signature=self._sign_trade(order.id, signal.symbol, 
                                              signal.side, float(signal.amount))
                )
                
                self.database.save_trade(trade)
                
                await self._log_audit('trade_executed', {
                    'order_id': order.id,
                    'symbol': signal.symbol,
                    'side': signal.side,
                    'amount': float(signal.amount),
                    'price': float(order.filled_price),
                    'pnl': pnl,
                    'strategy': signal.strategy
                })
                
                self.logger.info("trade_executed_and_persisted",
                               order_id=order.id,
                               symbol=signal.symbol,
                               pnl=pnl)
                
                # Save state after trade
                await self._save_state()
            
        except Exception as e:
            self.logger.error("order_execution_failed", error=str(e))
            await self._log_audit('order_execution_failed', {
                'error': str(e),
                'symbol': signal.symbol
            }, severity=6)
    
    def _sign_trade(self, order_id: str, symbol: str, side: str, 
                   amount: float) -> str:
        """Create HMAC signature for trade verification."""
        message = f"{order_id}:{symbol}:{side}:{amount}:{time.time()}"
        return hmac.new(
            self.audit.signing_key,
            message.encode(),
            hashlib.sha3_256
        ).hexdigest()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        portfolio = await self.exchange.get_portfolio_summary()
        risk_status = self.risk.get_status()
        db_stats = self.database.get_stats()
        
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'active': self.active,
            'cycles_run': self.cycles_run,
            'signals_generated': self.signals_generated,
            'orders_placed': self.orders_placed,
            'trades_executed': self.trades_executed,
            'portfolio': portfolio,
            'risk': risk_status,
            'database': db_stats,
            'audit': self.audit.get_stats(),
            'public_key_hash': self._get_key_hash(),
            'persistence': {
                'database_connected': db_stats.get('trades', 0) >= 0,
                'vault_initialized': self.vault.get_status().get('master_key_loaded', False)
            }
        }
