"""
Binance Exchange Connector - REST API + WebSocket
Production-ready trading interface
"""

import asyncio
import aiohttp
import hmac
import hashlib
import time
import logging
from decimal import Decimal
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BinanceConnector:
    """Binance Spot Trading Connector"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        self.base_url = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        self.ws_url = "wss://testnet.binance.vision/ws" if testnet else "wss://stream.binance.com:9443/ws"
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.recv_window = 5000
        
        # Rate limiting
        self.rate_limiter = asyncio.Semaphore(20)  # 20 req/sec
        self.last_request = 0
        
    async def connect(self):
        """Initialize session"""
        self.session = aiohttp.ClientSession(
            headers={'X-MBX-APIKEY': self.api_key},
            timeout=aiohttp.ClientTimeout(total=30)
        )
        logger.info(f"Binance connector initialized ({'testnet' if self.testnet else 'live'})")
        
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
            
    def _sign(self, params: Dict) -> str:
        """Sign request parameters"""
        query = '&'.join([f"{k}={v}" for k, v in params.items()])
        return hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()
        
    async def _request(self, method: str, endpoint: str, 
                      params: Dict = None, signed: bool = False) -> Dict:
        """Make HTTP request"""
        async with self.rate_limiter:
            # Rate limit delay
            elapsed = time.time() - self.last_request
            if elapsed < 0.05:  # 50ms between requests
                await asyncio.sleep(0.05 - elapsed)
                
            url = f"{self.base_url}{endpoint}"
            params = params or {}
            
            if signed:
                params['timestamp'] = int(time.time() * 1000)
                params['recvWindow'] = self.recv_window
                params['signature'] = self._sign(params)
                
            try:
                if method == 'GET':
                    async with self.session.get(url, params=params) as resp:
                        self.last_request = time.time()
                        data = await resp.json()
                        if 'code' in data:
                            raise Exception(f"Binance API error: {data}")
                        return data
                        
                elif method == 'POST':
                    async with self.session.post(url, params=params) as resp:
                        self.last_request = time.time()
                        data = await resp.json()
                        if 'code' in data:
                            raise Exception(f"Binance API error: {data}")
                        return data
                        
                elif method == 'DELETE':
                    async with self.session.delete(url, params=params) as resp:
                        self.last_request = time.time()
                        data = await resp.json()
                        return data
                        
            except Exception as e:
                logger.error(f"Request failed: {e}")
                raise
                
    # ========== Market Data ==========
    
    async def get_ticker(self, symbol: str) -> Dict:
        """Get 24hr ticker"""
        return await self._request('GET', '/api/v3/ticker/24hr', 
                                   {'symbol': symbol.upper()})
        
    async def get_orderbook(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book"""
        return await self._request('GET', '/api/v3/depth',
                                   {'symbol': symbol.upper(), 'limit': limit})
        
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades"""
        return await self._request('GET', '/api/v3/trades',
                                   {'symbol': symbol.upper(), 'limit': limit})
        
    async def get_klines(self, symbol: str, interval: str = '1h', 
                        limit: int = 100) -> List[List]:
        """Get OHLCV candles"""
        return await self._request('GET', '/api/v3/klines',
                                   {'symbol': symbol.upper(), 
                                    'interval': interval, 
                                    'limit': limit})
        
    # ========== Account ==========
    
    async def get_account(self) -> Dict:
        """Get account info and balances"""
        return await self._request('GET', '/api/v3/account', signed=True)
        
    async def get_balance(self, asset: str) -> Decimal:
        """Get specific asset balance"""
        account = await self.get_account()
        for b in account.get('balances', []):
            if b['asset'] == asset.upper():
                return Decimal(b['free']) + Decimal(b['locked'])
        return Decimal('0')
        
    # ========== Trading ==========
    
    async def create_order(self, symbol: str, side: str, order_type: str,
                          quantity: float, price: float = None,
                          time_in_force: str = 'GTC') -> Dict:
        """Create new order"""
        params = {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': quantity
        }
        
        if order_type.upper() == 'LIMIT':
            params['price'] = price
            params['timeInForce'] = time_in_force
            
        return await self._request('POST', '/api/v3/order', params, signed=True)
        
    async def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """Cancel order"""
        return await self._request('DELETE', '/api/v3/order',
                                   {'symbol': symbol.upper(), 'orderId': order_id},
                                   signed=True)
        
    async def get_order(self, symbol: str, order_id: int) -> Dict:
        """Get order status"""
        return await self._request('GET', '/api/v3/order',
                                   {'symbol': symbol.upper(), 'orderId': order_id},
                                   signed=True)
        
    async def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Get open orders"""
        params = {}
        if symbol:
            params['symbol'] = symbol.upper()
        return await self._request('GET', '/api/v3/openOrders', params, signed=True)
        
    async def cancel_all_orders(self, symbol: str) -> List[Dict]:
        """Cancel all orders for symbol"""
        return await self._request('DELETE', '/api/v3/openOrders',
                                   {'symbol': symbol.upper()}, signed=True)
        
    # ========== WebSocket ==========
    
    async def start_websocket(self, symbols: List[str], callback: callable):
        """Start WebSocket stream"""
        streams = '/'.join([f"{s.lower()}@ticker" for s in symbols])
        ws_url = f"{self.ws_url}/stream?streams={streams}"
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                logger.info(f"WebSocket connected for {symbols}")
                
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = msg.json()
                        await callback(data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {ws.exception()}")
                        break
