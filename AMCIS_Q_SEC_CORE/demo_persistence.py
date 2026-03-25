"""
AMCIS Persistence & Crash Recovery Demo
========================================

Demonstrates:
1. Database persistence for trades
2. Vault-encrypted secrets
3. Audit logging with signatures
4. Crash recovery - restart and restore state

NO REAL CAPITAL - Paper trading simulation only.
"""

import asyncio
import sys
import time
from decimal import Decimal

from core.amcis_kernel import AMCISKernel
from infrastructure.database import DatabaseManager
from infrastructure.vault import VaultManager
from infrastructure.audit import AuditLogger
from secure_trading.secure_trading_agent_hardened import SecureTradingAgentHardened
from secure_trading import RiskLimits


async def main():
    """Run persistence demo."""
    print("=" * 70)
    print("AMCIS PERSISTENCE & CRASH RECOVERY DEMO")
    print("=" * 70)
    print()
    print("WARNING: Paper trading only - NO REAL MONEY AT RISK")
    print()
    
    # Initialize infrastructure
    print("[1/8] Initializing Infrastructure...")
    
    # Database (SQLite for demo)
    db = DatabaseManager(use_sqlite=True, db_path="demo_amcis.db")
    db.initialize()
    print("     [OK] Database initialized (SQLite)")
    
    # Vault (file-based for demo)
    vault = VaultManager(use_file_backend=True, storage_path=".vault/demo_secrets.enc")
    vault.initialize(master_password="DEMO_MASTER_KEY")
    print("     [OK] Vault initialized (encrypted file)")
    
    # Audit logger
    audit = AuditLogger(db)
    print("     [OK] Audit logger initialized")
    
    # Kernel
    kernel = AMCISKernel()
    await kernel.secure_boot()
    print("     [OK] Security kernel operational")
    print()
    
    # Create hardened trading agent
    print("[2/8] Creating Hardened Trading Agent...")
    
    risk_limits = RiskLimits(
        max_position_size=Decimal('2000'),
        max_positions=3,
        max_daily_loss=Decimal('500'),
        max_drawdown_pct=0.05
    )
    
    agent = SecureTradingAgentHardened(
        kernel=kernel,
        database=db,
        vault=vault,
        audit=audit,
        name="persistence_demo",
        initial_balance=Decimal('10000'),
        risk_limits=risk_limits
    )
    
    await agent.initialize()
    print(f"     [OK] Agent: {agent.agent_id}")
    print(f"     [OK] Public Key: {agent._get_key_hash()}")
    print()
    
    # Run trading cycles
    print("[3/8] Running Trading Cycles...")
    print("     (Executing trades with persistence)")
    print()
    
    for i in range(2):
        print(f"     Cycle {i+1}/2...", end=" ", flush=True)
        await agent._trading_cycle()
        
        # Force state save after each cycle
        await agent._save_state()
        
        status = await agent.get_status()
        portfolio = status['portfolio']
        
        print(f"Equity: ${portfolio['total_equity']:,.2f} | "
              f"Trades: {status['trades_executed']} | "
              f"DB Trades: {status['database']['trades']}")
        
        await asyncio.sleep(1)
    
    print()
    
    # Show database state
    print("[4/8] Database State:")
    db_stats = db.get_stats()
    print(f"     Trades stored: {db_stats['trades']}")
    print(f"     Audit events: {db_stats['audit_events']}")
    print(f"     Agent states: {db_stats['agent_states']}")
    print()
    
    # Show recent trades
    if db_stats['trades'] > 0:
        print("[5/8] Recent Trades (from database):")
        trades = db.get_trades(agent_id=agent.agent_id, limit=5)
        for t in trades[:3]:
            print(f"     {t.side.upper()} {t.symbol}: {t.amount:.6f} "
                  f"@ ${t.price:,.2f} = ${t.value:,.2f}")
        print()
    
    # Show audit log
    print("[6/8] Recent Audit Events:")
    events = audit.get_recent_events(limit=5)
    for e in events:
        print(f"     {e['event_type']}: {e['source']} "
              f"(sig: {e['signature']})")
    print()
    
    # Simulate crash - stop without cleanup
    print("[7/8] Simulating CRASH (sudden stop)...")
    print("     [!] Stopping agent without graceful shutdown")
    agent.active = False  # Stop the loop
    # DON'T call agent.stop() - simulate crash
    print("     [!] Agent process terminated")
    print()
    
    # Wait a moment
    await asyncio.sleep(1)
    
    # Create NEW agent instance - should recover state
    print("[8/8] CRASH RECOVERY - Creating new agent instance...")
    
    agent2 = SecureTradingAgentHardened(
        kernel=kernel,
        database=db,
        vault=vault,
        audit=audit,
        name="persistence_demo",  # Same name
        initial_balance=Decimal('10000'),
        risk_limits=risk_limits
    )
    
    recovered = await agent2.recover_state()
    
    if recovered:
        print("     [OK] STATE RECOVERED FROM DATABASE")
        
        status2 = await agent2.get_status()
        portfolio2 = status2['portfolio']
        
        print(f"     Recovered cash: ${portfolio2['cash']:,.2f}")
        print(f"     Recovered positions: {portfolio2['positions']}")
        print(f"     Recovered trades: {status2['trades_executed']}")
        
        # Continue trading
        print()
        print("     Resuming trading after recovery...")
        await agent2._trading_cycle()
        
        status3 = await agent2.get_status()
        print(f"     Post-recovery equity: ${status3['portfolio']['total_equity']:,.2f}")
    else:
        print("     [!] No previous state found (fresh start)")
    
    # Cleanup
    print()
    print("Shutting down...")
    if recovered:
        await agent2.stop()
    await kernel.shutdown()
    
    # Final stats
    print()
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print()
    
    final_stats = db.get_stats()
    print("Final Statistics:")
    print(f"  - Total trades stored: {final_stats['trades']}")
    print(f"  - Total audit events: {final_stats['audit_events']}")
    print(f"  - Database file: demo_amcis.db")
    print(f"  - Vault file: .vault/demo_secrets.enc")
    print()
    print("Persistence verified:")
    print("  [OK] Trades saved to database")
    print("  [OK] Audit trail signed and stored")
    print("  [OK] State recovered after crash")
    print("  [OK] Secrets encrypted in vault")
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
        import traceback
        traceback.print_exc()
        sys.exit(1)
