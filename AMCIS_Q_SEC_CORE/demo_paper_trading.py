"""
AMCIS Paper Trading Demo
========================

Demonstrates the secure trading agent with AMCIS kernel.
Uses real market data from CoinGecko with PAPER MONEY only.

NO REAL CAPITAL AT RISK - This is a simulation.

Usage:
    python demo_paper_trading.py

The demo will:
1. Initialize AMCIS security kernel
2. Create cryptographic identity
3. Start paper trading agent
4. Run trading cycles with real market data
5. Display portfolio and trade statistics
"""

import asyncio
import sys
from decimal import Decimal

from core.amcis_kernel import AMCISKernel
from secure_trading import SecureTradingAgent, RiskLimits


async def main():
    """Run paper trading demo."""
    print("=" * 60)
    print("AMCIS SECURE PAPER TRADING DEMO")
    print("=" * 60)
    print()
    print("WARNING: PAPER TRADING ONLY - NO REAL MONEY AT RISK")
    print()
    
    # Initialize kernel
    print("[1/6] Initializing AMCIS Security Kernel...")
    kernel = AMCISKernel()
    boot_success = await kernel.secure_boot()
    
    if not boot_success:
        print("[ERROR] Kernel secure boot failed!")
        sys.exit(1)
    
    print(f"[OK] Kernel state: {kernel.get_state().name}")
    print(f"     Boot hash: {kernel.health_check()['boot_hash']}")
    
    # Create trading agent
    print()
    print("[2/6] Creating Secure Trading Agent...")
    
    risk_limits = RiskLimits(
        max_position_size=Decimal('2000'),   # $2k max per position
        max_positions=3,                      # Max 3 concurrent
        max_daily_loss=Decimal('500'),       # $500 daily loss limit
        max_drawdown_pct=0.05                # 5% max drawdown
    )
    
    agent = SecureTradingAgent(
        kernel=kernel,
        name="demo_trader",
        initial_balance=Decimal('10000'),    # Start with $10k paper money
        risk_limits=risk_limits
    )
    
    await agent.initialize()
    
    print(f"[OK] Agent ID: {agent.agent_id}")
    print(f"     Public Key: {agent._get_key_hash()}")
    print(f"     Initial Balance: $10,000.00 (PAPER)")
    
    # Show risk configuration
    print()
    print("[3/6] Risk Configuration:")
    print(f"     Max Position: $2,000")
    print(f"     Max Positions: 3")
    print(f"     Max Daily Loss: $500")
    print(f"     Max Drawdown: 5%")
    
    # Run trading cycles
    print()
    print("[4/6] Running Trading Cycles...")
    print("     (Fetching real market data from CoinGecko)")
    print()
    
    num_cycles = 3
    for i in range(num_cycles):
        print(f"     Cycle {i+1}/{num_cycles}...", end=" ", flush=True)
        await agent._trading_cycle()
        
        # Get current status
        status = await agent.get_status()
        portfolio = status['portfolio']
        
        print(f"Equity: ${portfolio['total_equity']:,.2f} | "
              f"Positions: {portfolio['positions']} | "
              f"Trades: {status['trades_executed']}")
        
        # Small delay between cycles
        if i < num_cycles - 1:
            await asyncio.sleep(2)
    
    # Final status
    print()
    print("[5/6] Final Portfolio Status:")
    
    status = await agent.get_status()
    portfolio = status['portfolio']
    
    print(f"     Cash: ${portfolio['cash']:,.2f}")
    print(f"     Total Equity: ${portfolio['total_equity']:,.2f}")
    print(f"     Unrealized P&L: ${portfolio['unrealized_pnl']:,.2f}")
    print(f"     Realized P&L: ${portfolio['realized_pnl']:,.2f}")
    print(f"     Total P&L: ${portfolio['total_pnl']:+,.2f}")
    print()
    print(f"     Positions Held: {portfolio['positions']}")
    print(f"     Trades Executed: {status['trades_executed']}")
    print(f"     Cycles Completed: {status['cycles_run']}")
    
    # Show positions
    positions = await agent.exchange.get_all_positions()
    if positions:
        print()
        print("     Current Positions:")
        for symbol, pos in positions.items():
            current_price = await agent.exchange.get_price(symbol)
            if current_price:
                value = pos.amount * current_price
                print(f"       {symbol}: {float(pos.amount):.6f} "
                      f"(@ ${float(pos.avg_entry_price):,.2f}) "
                      f"= ${float(value):,.2f}")
    
    # Risk status
    print()
    print("[6/6] Risk Status:")
    risk = status['risk']
    print(f"     Daily P&L: ${risk['daily_pnl']:,.2f}")
    print(f"     Drawdown: {risk['drawdown_pct']*100:.2f}%")
    print(f"     Trading Allowed: {'YES' if agent.risk.is_trading_allowed() else 'NO'}")
    
    # Shutdown
    print()
    print("Shutting down...")
    await agent.stop()
    await kernel.shutdown()
    
    print()
    print("=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  - Kernel: {kernel.get_state().name}")
    print(f"  - Agent: {status['name']}")
    print(f"  - Final Equity: ${portfolio['total_equity']:,.2f}")
    print(f"  - Return: {(portfolio['total_equity']/10000 - 1)*100:+.2f}%")
    print()
    print("All trades were PAPER trades with simulated money.")
    print("No real capital was at risk.")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("\n[INTERRUPTED] Demo stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
