"""
Infrastructure Layer - Persistence & Secrets Management
=======================================================

Production-grade storage and secrets management for AMCIS.

Components:
- Database: PostgreSQL (production) / SQLite (development fallback)
- Vault: HashiCorp Vault (production) / Encrypted file (development)
- Audit: Tamper-evident logging with signatures

Security:
- All secrets encrypted at rest
- Automatic key rotation support
- Crash recovery with state restoration
"""

from .database import DatabaseManager, TradeRecord, AuditRecord
from .vault import VaultManager, SecretType
from .audit import AuditLogger

__all__ = [
    "DatabaseManager",
    "TradeRecord",
    "AuditRecord",
    "VaultManager",
    "SecretType",
    "AuditLogger",
]
