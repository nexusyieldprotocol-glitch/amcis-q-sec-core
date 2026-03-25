"""
Secure Trading Integration Tests
================================

End-to-end tests for secure trading agent with AMCIS kernel.
All tests use paper trading - NO REAL CAPITAL.
"""

import pytest
import asyncio
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.amcis_kernel import AMCISKernel
from secure_trading import SecureTradingAgent, PaperExchange, RiskLimits


class TestSecureTradingIntegration:
    """Integration tests for secure trading."""
    
    @pytest.fixture
    async def kernel(self):
        """Create AMCIS kernel."""
        kernel = AMCISKernel()
        await kernel.secure_boot()
        yield kernel
        await kernel.shutdown()
    
    @pytest.fixture
    async def agent(self, kernel):
        """Create secure trading agent."""
        risk_limits = RiskLimits(
            max_position_size=Decimal('5000'),
            max_positions=3,
            max_daily_loss=Decimal('500')
        )
        
        agent = SecureTradingAgent(
            kernel=kernel,
            name="test_trader",
            initial_balance=Decimal('50000'),
            risk_limits=risk_limits
        )
        
        await agent.initialize()
        yield agent
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, kernel):
        """Test agent initializes with kernel."""
        agent = SecureTradingAgent(
            kernel=kernel,
            name="init_test",
            initial_balance=Decimal('10000')
        )
        
        await agent.initialize()
        
        assert agent.agent_id is not None
        assert agent.kernel == kernel
        assert agent.exchange is not None
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_crypto_identity(self, kernel):
        """Test agent has cryptographic identity."""
        agent = SecureTradingAgent(kernel=kernel, name="crypto_test")
        await agent.initialize()
        
        # Check keypair exists
        assert agent.keypair is not None
        assert len(agent.keypair.kem_public_bytes) == 32
        assert len(agent.keypair.sig_public_bytes) > 100
        
        # Check key hash is generated
        key_hash = agent._get_key_hash()
        assert len(key_hash) == 16
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_paper_exchange_creation(self):
        """Test paper exchange with simulated balance."""
        exchange = PaperExchange(initial_balance=Decimal('25000'))
        
        summary = await exchange.get_portfolio_summary()
        
        assert summary['cash'] == 25000.0
        assert summary['total_equity'] == 25000.0
        assert summary['positions'] == 0
        assert summary['trades'] == 0
    
    @pytest.mark.asyncio
    async def test_price_fetching(self):
        """Test fetching real market prices."""
        exchange = PaperExchange()
        
        # Get BTC price
        price = await exchange.get_price('BTC-USD')
        
        assert price is not None
        assert price > Decimal('1000')  # BTC should be > $1000
        
        # Get ETH price
        price = await exchange.get_price('ETH-USD')
        
        assert price is not None
        assert price > Decimal('100')  # ETH should be > $100
    
    @pytest.mark.asyncio
    async def test_paper_order_execution(self):
        """Test paper order execution."""
        exchange = PaperExchange(initial_balance=Decimal('10000'))
        
        # Get price
        price = await exchange.get_price('BTC-USD')
        
        # Place buy order
        from secure_trading.paper_exchange import OrderSide, OrderType
        
        order = await exchange.place_order(
            symbol='BTC-USD',
            side=OrderSide.BUY,
            amount=Decimal('0.1'),
            order_type=OrderType.MARKET
        )
        
        assert order.status.name == 'FILLED'
        assert order.filled_price is not None
        assert order.filled_at is not None
        
        # Check position created
        position = await exchange.get_position('BTC-USD')
        assert position is not None
        assert position.amount == Decimal('0.1')
    
    @pytest.mark.asyncio
    async def test_risk_limits(self):
        """Test risk engine enforces limits."""
        from secure_trading.risk_engine import RiskEngine
        
        risk = RiskEngine(limits=RiskLimits(
            max_position_size=Decimal('1000'),
            max_positions=2,
            max_daily_loss=Decimal('100')
        ))
        
        # Should allow small order
        check = risk.check_order(
            symbol='BTC-USD',
            side='buy',
            amount=Decimal('0.01'),
            price=Decimal('50000'),
            portfolio_value=Decimal('10000'),
            current_positions=0
        )
        assert check.passed is True
        
        # Should reject oversized order
        check = risk.check_order(
            symbol='BTC-USD',
            side='buy',
            amount=Decimal('1.0'),
            price=Decimal('50000'),
            portfolio_value=Decimal('10000'),
            current_positions=0
        )
        assert check.passed is False
    
    @pytest.mark.asyncio
    async def test_trading_cycle(self, agent):
        """Test one trading cycle executes."""
        # Run one cycle
        await agent._trading_cycle()
        
        assert agent.cycles_run == 1
        
        # Get status
        status = await agent.get_status()
        
        assert status['agent_id'] == agent.agent_id
        assert 'portfolio' in status
        assert 'risk' in status
    
    @pytest.mark.asyncio
    async def test_signal_generation(self, agent):
        """Test signal generation."""
        # Generate signal for BTC
        signal = await agent._generate_signal('BTC-USD')
        
        # Signal may be None or a TradeSignal depending on state
        if signal:
            assert signal.symbol == 'BTC-USD'
            assert signal.side in ['buy', 'sell']
            assert signal.amount > 0
            assert 0 <= signal.confidence <= 1
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, kernel):
        """Test complete workflow with kernel events."""
        agent = SecureTradingAgent(
            kernel=kernel,
            name="workflow_test",
            initial_balance=Decimal('5000'),
            risk_limits=RiskLimits(
                max_position_size=Decimal('1000'),
                max_positions=2
            )
        )
        
        await agent.initialize()
        
        # Run a few cycles
        for _ in range(3):
            await agent._trading_cycle()
            await asyncio.sleep(0.1)  # Small delay
        
        # Get final status
        status = await agent.get_status()
        
        assert status['cycles_run'] == 3
        assert 'portfolio' in status
        
        portfolio = status['portfolio']
        assert 'cash' in portfolio
        assert 'total_equity' in portfolio
        
        await agent.stop()


if __name__ == "__main__":
    print("Running Secure Trading Integration Tests...")
    print("WARNING: These tests make real API calls to CoinGecko")
    print("and may take 30-60 seconds to complete.")
    print()
    
    # Run basic smoke test
    async def smoke_test():
        print("[1/5] Creating AMCIS kernel...")
        kernel = AMCISKernel()
        await kernel.secure_boot()
        print("[OK] Kernel initialized")
        
        print("[2/5] Creating paper exchange...")
        exchange = PaperExchange(initial_balance=Decimal('10000'))
        summary = await exchange.get_portfolio_summary()
        print(f"[OK] Exchange ready: ${summary['cash']:.2f}")
        
        print("[3/5] Fetching market price...")
        price = await exchange.get_price('BTC-USD')
        print(f"[OK] BTC price: ${price:,.2f}")
        
        print("[4/5] Creating secure trading agent...")
        agent = SecureTradingAgent(
            kernel=kernel,
            name="smoke_test",
            initial_balance=Decimal('5000')
        )
        await agent.initialize()
        print(f"[OK] Agent initialized: {agent.agent_id}")
        
        print("[5/5] Running trading cycle...")
        await agent._trading_cycle()
        status = await agent.get_status()
        print(f"[OK] Cycle complete: {status['cycles_run']} cycles")
        
        await agent.stop()
        await kernel.shutdown()
        
        print()
        print("=" * 50)
        print("SMOKE TEST PASSED")
        print("=" * 50)
        print()
        print("Summary:")
        print(f"  - Kernel: Operational")
        print(f"  - Crypto: {agent._get_key_hash()}")
        print(f"  - Paper Balance: ${status['portfolio']['cash']:.2f}")
        print(f"  - Trades: {status['trades_executed']}")
        print()
    
    asyncio.run(smoke_test())
