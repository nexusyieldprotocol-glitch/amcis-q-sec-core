"""
Secure Trading Module - Paper Trading Integration
=================================================

Integrates a single trading agent with the AMCIS security kernel.
All operations use paper trading (simulated) - NO REAL CAPITAL.

Components:
- PaperExchange: Simulated exchange with real market data
- SecureTradingAgent: Trading agent wrapped with security kernel
- RiskEngine: Enforces trading limits and risk checks

Status: EXPERIMENTAL - Paper trading only
"""

from .paper_exchange import PaperExchange, PaperOrder
from .secure_trading_agent import SecureTradingAgent
from .risk_engine import RiskEngine, RiskLimits

__all__ = [
    "PaperExchange",
    "PaperOrder", 
    "SecureTradingAgent",
    "RiskEngine",
    "RiskLimits"
]
