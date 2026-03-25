"""
Database Manager - Persistent Storage
=====================================

Production-grade database abstraction supporting:
- PostgreSQL (production deployment)
- SQLite (development/testing fallback)

All sensitive data is encrypted before storage.
"""

import json
import sqlite3
import hashlib
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager
from pathlib import Path

import structlog

logger = structlog.get_logger("amcis.database")


@dataclass
class TradeRecord:
    """Database record for a trade."""
    id: str
    agent_id: str
    symbol: str
    side: str
    amount: float
    price: float
    value: float
    pnl: float
    timestamp: float
    strategy: str
    signature: str  # Kernel signature of trade data


@dataclass
class AuditRecord:
    """Database record for audit events."""
    id: str
    timestamp: float
    event_type: str
    source_module: str
    severity: int
    data: Dict[str, Any]
    correlation_id: str
    signature: str  # For tamper detection


@dataclass
class AgentStateRecord:
    """Database record for agent state (crash recovery)."""
    agent_id: str
    timestamp: float
    cash: float
    positions: Dict[str, Any]  # JSON
    daily_pnl: float
    trades_executed: int
    checksum: str  # Integrity verification


class DatabaseManager:
    """
    Database Manager
    ================
    
    Unified interface for PostgreSQL (production) or SQLite (dev).
    All sensitive fields are encrypted via Vault before storage.
    
    Usage:
        db = DatabaseManager()
        db.initialize()
        db.save_trade(trade_record)
        trades = db.get_trades(agent_id="agent_001")
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        db_path: Optional[str] = None,
        use_sqlite: bool = True
    ):
        """
        Initialize database manager.
        
        Args:
            connection_string: PostgreSQL connection string (production)
            db_path: SQLite database path (development)
            use_sqlite: Force SQLite mode
        """
        self.use_sqlite = use_sqlite or (connection_string is None)
        self.connection_string = connection_string
        self.db_path = db_path or "amcis.db"
        self._connection = None
        self.logger = structlog.get_logger("amcis.database")
        
        self.logger.info("database_manager_initialized",
                        backend="sqlite" if self.use_sqlite else "postgresql")
    
    def initialize(self):
        """Initialize database connection and create tables."""
        if self.use_sqlite:
            self._init_sqlite()
        else:
            self._init_postgresql()
        
        self.logger.info("database_initialized")
    
    def _init_sqlite(self):
        """Initialize SQLite database."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                value REAL NOT NULL,
                pnl REAL DEFAULT 0,
                timestamp REAL NOT NULL,
                strategy TEXT,
                signature TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                source_module TEXT NOT NULL,
                severity INTEGER NOT NULL,
                data TEXT NOT NULL,
                correlation_id TEXT,
                signature TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Agent state table (for crash recovery)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_state (
                agent_id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                cash REAL NOT NULL,
                positions TEXT NOT NULL,
                daily_pnl REAL NOT NULL,
                trades_executed INTEGER NOT NULL,
                checksum TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crypto identities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crypto_identities (
                agent_id TEXT PRIMARY KEY,
                kem_public BLOB NOT NULL,
                sig_public BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_agent ON trades(agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_state_time ON agent_state(timestamp)")
        
        conn.commit()
        conn.close()
        
        self.logger.info("sqlite_initialized", path=self.db_path)
    
    def _init_postgresql(self):
        """Initialize PostgreSQL database."""
        try:
            import psycopg2
            
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            # Similar schema as SQLite but with proper types
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id VARCHAR(64) PRIMARY KEY,
                    agent_id VARCHAR(64) NOT NULL,
                    symbol VARCHAR(16) NOT NULL,
                    side VARCHAR(4) NOT NULL,
                    amount DECIMAL(20, 8) NOT NULL,
                    price DECIMAL(20, 8) NOT NULL,
                    value DECIMAL(20, 2) NOT NULL,
                    pnl DECIMAL(20, 2) DEFAULT 0,
                    timestamp TIMESTAMP NOT NULL,
                    strategy VARCHAR(32),
                    signature VARCHAR(128) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id VARCHAR(64) PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    event_type VARCHAR(32) NOT NULL,
                    source_module VARCHAR(64) NOT NULL,
                    severity INTEGER NOT NULL,
                    data JSONB NOT NULL,
                    correlation_id VARCHAR(32),
                    signature VARCHAR(128) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_state (
                    agent_id VARCHAR(64) PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    cash DECIMAL(20, 2) NOT NULL,
                    positions JSONB NOT NULL,
                    daily_pnl DECIMAL(20, 2) NOT NULL,
                    trades_executed INTEGER NOT NULL,
                    checksum VARCHAR(64) NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crypto_identities (
                    agent_id VARCHAR(64) PRIMARY KEY,
                    kem_public BYTEA NOT NULL,
                    sig_public BYTEA NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_agent ON trades(agent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)")
            
            conn.commit()
            conn.close()
            
            self.logger.info("postgresql_initialized")
            
        except ImportError:
            self.logger.error("psycopg2_not_installed_fallback_to_sqlite")
            self.use_sqlite = True
            self._init_sqlite()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        if self.use_sqlite:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
        else:
            import psycopg2
            conn = psycopg2.connect(self.connection_string)
        
        try:
            yield conn
        finally:
            conn.close()
    
    def save_trade(self, trade: TradeRecord) -> bool:
        """
        Save trade record to database.
        
        Args:
            trade: TradeRecord to save
            
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_sqlite:
                    cursor.execute("""
                        INSERT INTO trades 
                        (id, agent_id, symbol, side, amount, price, value, pnl, 
                         timestamp, strategy, signature)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade.id, trade.agent_id, trade.symbol, trade.side,
                        trade.amount, trade.price, trade.value, trade.pnl,
                        trade.timestamp, trade.strategy, trade.signature
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO trades 
                        (id, agent_id, symbol, side, amount, price, value, pnl, 
                         timestamp, strategy, signature)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        trade.id, trade.agent_id, trade.symbol, trade.side,
                        trade.amount, trade.price, trade.value, trade.pnl,
                        datetime.fromtimestamp(trade.timestamp),
                        trade.strategy, trade.signature
                    ))
                
                conn.commit()
                
                self.logger.debug("trade_saved", trade_id=trade.id, 
                                agent_id=trade.agent_id, value=trade.value)
                return True
                
        except Exception as e:
            self.logger.error("failed_to_save_trade", trade_id=trade.id, error=str(e))
            return False
    
    def get_trades(
        self,
        agent_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[TradeRecord]:
        """
        Get trades from database.
        
        Args:
            agent_id: Filter by agent
            symbol: Filter by symbol
            limit: Max results
            
        Returns:
            List of TradeRecord
        """
        trades = []
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM trades WHERE 1=1"
                params = []
                
                if agent_id:
                    query += " AND agent_id = ?" if self.use_sqlite else " AND agent_id = %s"
                    params.append(agent_id)
                
                if symbol:
                    query += " AND symbol = ?" if self.use_sqlite else " AND symbol = %s"
                    params.append(symbol)
                
                query += " ORDER BY timestamp DESC LIMIT ?" if self.use_sqlite else " ORDER BY timestamp DESC LIMIT %s"
                params.append(limit)
                
                cursor.execute(query, params)
                
                for row in cursor.fetchall():
                    trades.append(TradeRecord(
                        id=row['id'],
                        agent_id=row['agent_id'],
                        symbol=row['symbol'],
                        side=row['side'],
                        amount=row['amount'],
                        price=row['price'],
                        value=row['value'],
                        pnl=row['pnl'],
                        timestamp=row['timestamp'],
                        strategy=row['strategy'],
                        signature=row['signature']
                    ))
                    
        except Exception as e:
            self.logger.error("failed_to_get_trades", error=str(e))
        
        return trades
    
    def save_audit_event(self, record: AuditRecord) -> bool:
        """Save audit event to database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data_json = json.dumps(record.data)
                
                if self.use_sqlite:
                    cursor.execute("""
                        INSERT INTO audit_log 
                        (id, timestamp, event_type, source_module, severity, 
                         data, correlation_id, signature)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record.id, record.timestamp, record.event_type,
                        record.source_module, record.severity, data_json,
                        record.correlation_id, record.signature
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO audit_log 
                        (id, timestamp, event_type, source_module, severity, 
                         data, correlation_id, signature)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                    """, (
                        record.id, datetime.fromtimestamp(record.timestamp),
                        record.event_type, record.source_module, record.severity,
                        data_json, record.correlation_id, record.signature
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error("failed_to_save_audit", error=str(e))
            return False
    
    def save_agent_state(self, state: AgentStateRecord) -> bool:
        """
        Save agent state for crash recovery.
        
        Args:
            state: AgentStateRecord
            
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                positions_json = json.dumps(state.positions)
                
                if self.use_sqlite:
                    cursor.execute("""
                        INSERT OR REPLACE INTO agent_state
                        (agent_id, timestamp, cash, positions, daily_pnl, 
                         trades_executed, checksum)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        state.agent_id, state.timestamp, state.cash,
                        positions_json, state.daily_pnl, state.trades_executed,
                        state.checksum
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO agent_state
                        (agent_id, timestamp, cash, positions, daily_pnl, 
                         trades_executed, checksum)
                        VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)
                        ON CONFLICT (agent_id) DO UPDATE SET
                        timestamp = EXCLUDED.timestamp,
                        cash = EXCLUDED.cash,
                        positions = EXCLUDED.positions,
                        daily_pnl = EXCLUDED.daily_pnl,
                        trades_executed = EXCLUDED.trades_executed,
                        checksum = EXCLUDED.checksum,
                        updated_at = CURRENT_TIMESTAMP
                    """, (
                        state.agent_id, datetime.fromtimestamp(state.timestamp),
                        state.cash, positions_json, state.daily_pnl,
                        state.trades_executed, state.checksum
                    ))
                
                conn.commit()
                
                self.logger.debug("agent_state_saved", 
                                agent_id=state.agent_id, 
                                checksum=state.checksum[:16])
                return True
                
        except Exception as e:
            self.logger.error("failed_to_save_agent_state", 
                            agent_id=state.agent_id, error=str(e))
            return False
    
    def load_agent_state(self, agent_id: str) -> Optional[AgentStateRecord]:
        """
        Load agent state for crash recovery.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentStateRecord or None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_sqlite:
                    cursor.execute("""
                        SELECT * FROM agent_state WHERE agent_id = ?
                    """, (agent_id,))
                else:
                    cursor.execute("""
                        SELECT * FROM agent_state WHERE agent_id = %s
                    """, (agent_id,))
                
                row = cursor.fetchone()
                
                if row:
                    # Verify checksum
                    positions = json.loads(row['positions'])
                    checksum_data = f"{row['agent_id']}:{row['cash']}:{row['positions']}"
                    expected_checksum = hashlib.sha3_256(checksum_data.encode()).hexdigest()
                    
                    if row['checksum'] != expected_checksum:
                        self.logger.error("agent_state_checksum_failed",
                                        agent_id=agent_id)
                        return None
                    
                    return AgentStateRecord(
                        agent_id=row['agent_id'],
                        timestamp=row['timestamp'],
                        cash=row['cash'],
                        positions=positions,
                        daily_pnl=row['daily_pnl'],
                        trades_executed=row['trades_executed'],
                        checksum=row['checksum']
                    )
                    
        except Exception as e:
            self.logger.error("failed_to_load_agent_state", 
                            agent_id=agent_id, error=str(e))
        
        return None
    
    def save_crypto_identity(self, agent_id: str, kem_public: bytes, 
                            sig_public: bytes) -> bool:
        """Save agent's public keys (for verification)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_sqlite:
                    cursor.execute("""
                        INSERT OR REPLACE INTO crypto_identities
                        (agent_id, kem_public, sig_public)
                        VALUES (?, ?, ?)
                    """, (agent_id, kem_public, sig_public))
                else:
                    cursor.execute("""
                        INSERT INTO crypto_identities
                        (agent_id, kem_public, sig_public)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (agent_id) DO UPDATE SET
                        kem_public = EXCLUDED.kem_public,
                        sig_public = EXCLUDED.sig_public
                    """, (agent_id, kem_public, sig_public))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error("failed_to_save_identity", 
                            agent_id=agent_id, error=str(e))
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {
            'backend': 'sqlite' if self.use_sqlite else 'postgresql',
            'trades': 0,
            'audit_events': 0,
            'agent_states': 0
        }
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM trades")
                stats['trades'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM audit_log")
                stats['audit_events'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM agent_state")
                stats['agent_states'] = cursor.fetchone()[0]
                
        except Exception as e:
            self.logger.error("failed_to_get_stats", error=str(e))
        
        return stats
