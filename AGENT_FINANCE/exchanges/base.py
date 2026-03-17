"""
AMCIS Exchange Connector Base Class
Unified interface for CEX and DEX integrations
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import time
import hashlib
import hmac
import aiohttp

logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class OrderBook:
    symbol: str
    bids: List[Tuple[Decimal, Decimal]]  # (price, amount)
    asks: List[Tuple[Decimal, Decimal]]
    timestamp: float
    
    @property
    def best_bid(self) -> Optional[Decimal]:
        return self.bids[0][0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[Decimal]:
        return self.asks[0][0] if self.asks else None
    
    @property
    def spread(self) -> Decimal:
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return Decimal('0')
    
    @property
    def mid_price(self) -> Optional[Decimal]:
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None


@dataclass
class Trade:
    id: str
    symbol: str
    side: OrderSide
    amount: Decimal
    price: Decimal
    fee: Decimal
    fee_currency: str
    timestamp: float
    raw_data: Dict = None


@dataclass
class Order:
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    amount: Decimal
    filled: Decimal
    remaining: Decimal
    price: Optional[Decimal]
    status: OrderStatus
    average_price: Optional[Decimal] = None
    fee: Decimal = Decimal('0')
    timestamp: float = 0
    raw_data: Dict = None
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


@dataclass
class Balance:
    asset: str
    free: Decimal
    used: Decimal
    total: Decimal
    
    @property
    def available(self) -> Decimal:
        return self.free


@dataclass
class Ticker:
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume_24h: Decimal
    high_24h: Decimal
    low_24h: Decimal
    change_24h: Decimal
    change_pct_24h: Decimal
    timestamp: float


class ExchangeConnector(ABC):
    """Base class for exchange connectors"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.passphrase = config.get('passphrase', '')
        self.testnet = config.get('testnet', False)
        
        # Rate limiting
        self.rate_limiter = asyncio.Semaphore(config.get('rate_limit', 10))
        self.last_request_time = 0
        self.min_request_interval = 1.0 / config.get('rate_limit', 10)
        
        # Connection
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_session: Optional[aiohttp.ClientSession] = None
        
        # Market data cache
        self._orderbook_cache: Dict[str, OrderBook] = {}
        self._ticker_cache: Dict[str, Ticker] = {}
        self._balance_cache: Dict[str, Balance] = {}
        self.cache_ttl = 5  # seconds
        
        # WebSocket
        self._ws_callbacks: List[callable] = []
        self._ws_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def initialize(self):
        """Initialize connector"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=self._get_default_headers()
        )
        logger.info(f"{self.name} connector initialized")
        
    async def close(self):
        """Close connector"""
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
        if self.session:
            await self.session.close()
        logger.info(f"{self.name} connector closed")
        
    @abstractmethod
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default HTTP headers"""
        pass
        
    @abstractmethod
    async def _sign_request(self, method: str, endpoint: str, 
                           params: Dict = None, data: Dict = None) -> Dict[str, str]:
        """Sign API request"""
        pass
        
    async def _make_request(self, method: str, endpoint: str,
                           params: Dict = None, data: Dict = None,
                           signed: bool = False) -> Dict:
        """Make HTTP request with rate limiting"""
        async with self.rate_limiter:
            # Rate limit delay
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - elapsed)
                
            url = f"{self._get_base_url()}{endpoint}"
            headers = self._get_default_headers()
            
            if signed:
                headers.update(await self._sign_request(method, endpoint, params, data))
                
            try:
                if method == 'GET':
                    async with self.session.get(url, params=params, headers=headers) as resp:
                        self.last_request_time = time.time()
                        resp.raise_for_status()
                        return await resp.json()
                elif method == 'POST':
                    async with self.session.post(url, json=data, headers=headers) as resp:
                        self.last_request_time = time.time()
                        resp.raise_for_status()
                        return await resp.json()
                elif method == 'DELETE':
                    async with self.session.delete(url, headers=headers) as resp:
                        self.last_request_time = time.time()
                        resp.raise_for_status()
                        return await resp.json()
                        
            except aiohttp.ClientError as e:
                logger.error(f"{self.name} request error: {e}")
                raise
                
    @abstractmethod
    def _get_base_url(self) -> str:
        """Get base API URL"""
        pass
        
    # ========== Market Data ==========
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get 24hr ticker data"""
        pass
        
    @abstractmethod
    async def get_orderbook(self, symbol: str, depth: int = 100) -> OrderBook:
        """Get order book"""
        pass
        
    @abstractmethod
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades"""
        pass
        
    @abstractmethod
    async def get_ohlcv(self, symbol: str, timeframe: str = '1h',
                       limit: int = 100) -> List[Dict]:
        """Get OHLCV candles"""
        pass
        
    # ========== Account ==========
    
    @abstractmethod
    async def get_balance(self, asset: str = None) -> Dict[str, Balance]:
        """Get account balance"""
        pass
        
    # ========== Trading ==========
    
    @abstractmethod
    async def create_order(self, symbol: str, side: OrderSide,
                          order_type: OrderType, amount: Decimal,
                          price: Decimal = None,
                          params: Dict = None) -> Order:
        """Create new order"""
        pass
        
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str = None) -> Order:
        """Cancel existing order"""
        pass
        
    @abstractmethod
    async def get_order(self, order_id: str, symbol: str = None) -> Order:
        """Get order status"""
        pass
        
    @abstractmethod
    async def get_open_orders(self, symbol: str = None) -> List[Order]:
        """Get all open orders"""
        pass
        
    @abstractmethod
    async def get_order_history(self, symbol: str = None,
                               limit: int = 100) -> List[Order]:
        """Get order history"""
        pass
        
    # ========== WebSocket ==========
    
    async def start_websocket(self, symbols: List[str],
                             on_ticker: callable = None,
                             on_orderbook: callable = None,
                             on_trade: callable = None):
        """Start WebSocket connection for real-time data"""
        self._running = True
        self._ws_callbacks = [cb for cb in [on_ticker, on_orderbook, on_trade] if cb]
        self._ws_task = asyncio.create_task(
            self._websocket_loop(symbols, on_ticker, on_orderbook, on_trade)
        )
        
    async def stop_websocket(self):
        """Stop WebSocket connection"""
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
                
    @abstractmethod
    async def _websocket_loop(self, symbols: List[str],
                             on_ticker: callable,
                             on_orderbook: callable,
                             on_trade: callable):
        """WebSocket message loop"""
        pass
        
    # ========== Utility ==========
    
    def format_symbol(self, symbol: str) -> str:
        """Format symbol for exchange"""
        return symbol.upper()
        
    def parse_symbol(self, symbol: str) -> str:
        """Parse exchange symbol to standard format"""
        return symbol.upper()
