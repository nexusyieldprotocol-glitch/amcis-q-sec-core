"""
Binance Exchange Connector
Production-ready spot and futures trading
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Optional
import aiohttp
import time
import hmac
import hashlib

from .base import (
    ExchangeConnector, OrderBook, Order, OrderSide, 
    OrderType, OrderStatus, Ticker, Balance, Trade
)

logger = logging.getLogger(__name__)


class BinanceConnector(ExchangeConnector):
    """
    Binance Spot & Futures Connector
    Supports: Spot trading, Margin trading, USD-M Futures
    """
    
    def __init__(self, config: Dict):
        super().__init__("Binance", config)
        self.market_type = config.get('market_type', 'spot')  # spot, margin, futures
        self.base_url = "https://testnet.binance.vision" if self.testnet else "https://api.binance.com"
        self.ws_url = "wss://testnet.binance.vision/ws" if self.testnet else "wss://stream.binance.com:9443/ws"
        
        if self.market_type == 'futures':
            self.base_url = "https://testnet.binancefuture.com" if self.testnet else "https://fapi.binance.com"
            self.ws_url = "wss://stream.binancefuture.com/ws" if self.testnet else "wss://fstream.binance.com/ws"
            
        self._recv_window = 5000
        self._symbol_info: Dict[str, Dict] = {}
        
    def _get_base_url(self) -> str:
        return self.base_url
        
    def _get_default_headers(self) -> Dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'X-MBX-APIKEY': self.api_key
        }
        
    async def _sign_request(self, method: str, endpoint: str,
                           params: Dict = None, data: Dict = None) -> Dict[str, str]:
        """Sign request with HMAC SHA256"""
        timestamp = str(int(time.time() * 1000))
        
        query_string = f"timestamp={timestamp}&recvWindow={self._recv_window}"
        if params:
            for key, value in params.items():
                query_string += f"&{key}={value}"
                
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'X-MBX-APIKEY': self.api_key,
            'timestamp': timestamp,
            'signature': signature,
            'recvWindow': str(self._recv_window)
        }
        
    async def initialize(self):
        await super().initialize()
        # Load exchange info for symbol precision
        await self._load_exchange_info()
        
    async def _load_exchange_info(self):
        """Load symbol trading rules"""
        try:
            data = await self._make_request('GET', '/api/v3/exchangeInfo')
            for symbol_data in data.get('symbols', []):
                if symbol_data['status'] == 'TRADING':
                    self._symbol_info[symbol_data['symbol']] = {
                        'baseAsset': symbol_data['baseAsset'],
                        'quoteAsset': symbol_data['quoteAsset'],
                        'filters': {f['filterType']: f for f in symbol_data['filters']}
                    }
            logger.info(f"Loaded {len(self._symbol_info)} trading pairs")
        except Exception as e:
            logger.error(f"Failed to load exchange info: {e}")
            
    # ========== Market Data ==========
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get 24hr ticker"""
        data = await self._make_request('GET', '/api/v3/ticker/24hr', 
                                        params={'symbol': self.format_symbol(symbol)})
        
        return Ticker(
            symbol=symbol,
            bid=Decimal(data['bidPrice']),
            ask=Decimal(data['askPrice']),
            last=Decimal(data['lastPrice']),
            volume_24h=Decimal(data['volume']),
            high_24h=Decimal(data['highPrice']),
            low_24h=Decimal(data['lowPrice']),
            change_24h=Decimal(data['priceChange']),
            change_pct_24h=Decimal(data['priceChangePercent']),
            timestamp=data['closeTime'] / 1000
        )
        
    async def get_orderbook(self, symbol: str, depth: int = 100) -> OrderBook:
        """Get order book"""
        data = await self._make_request('GET', '/api/v3/depth',
                                        params={'symbol': self.format_symbol(symbol), 'limit': depth})
        
        bids = [(Decimal(b[0]), Decimal(b[1])) for b in data['bids'][:10]]
        asks = [(Decimal(a[0]), Decimal(a[1])) for a in data['asks'][:10]]
        
        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=time.time()
        )
        
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades"""
        data = await self._make_request('GET', '/api/v3/trades',
                                        params={'symbol': self.format_symbol(symbol), 'limit': limit})
        
        return [
            Trade(
                id=str(t['id']),
                symbol=symbol,
                side=OrderSide.BUY if t['isBuyerMaker'] else OrderSide.SELL,
                amount=Decimal(t['qty']),
                price=Decimal(t['price']),
                fee=Decimal('0'),
                fee_currency='',
                timestamp=t['time'] / 1000
            )
            for t in data
        ]
        
    async def get_ohlcv(self, symbol: str, timeframe: str = '1h',
                       limit: int = 100) -> List[Dict]:
        """Get OHLCV candles"""
        interval_map = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h', '12h': '12h',
            '1d': '1d', '3d': '3d', '1w': '1w', '1M': '1M'
        }
        
        data = await self._make_request('GET', '/api/v3/klines', params={
            'symbol': self.format_symbol(symbol),
            'interval': interval_map.get(timeframe, '1h'),
            'limit': limit
        })
        
        return [
            {
                'timestamp': candle[0] / 1000,
                'open': Decimal(candle[1]),
                'high': Decimal(candle[2]),
                'low': Decimal(candle[3]),
                'close': Decimal(candle[4]),
                'volume': Decimal(candle[5]),
                'quote_volume': Decimal(candle[7])
            }
            for candle in data
        ]
        
    # ========== Account ==========
    
    async def get_balance(self, asset: str = None) -> Dict[str, Balance]:
        """Get account balance"""
        data = await self._make_request('GET', '/api/v3/account', signed=True)
        
        balances = {}
        for b in data.get('balances', []):
            free = Decimal(b['free'])
            locked = Decimal(b['locked'])
            total = free + locked
            
            if total > 0 or asset is None:
                balances[b['asset']] = Balance(
                    asset=b['asset'],
                    free=free,
                    used=locked,
                    total=total
                )
                
        return balances if asset is None else {asset: balances.get(asset)}
        
    # ========== Trading ==========
    
    async def create_order(self, symbol: str, side: OrderSide,
                          order_type: OrderType, amount: Decimal,
                          price: Decimal = None, params: Dict = None) -> Order:
        """Create new order"""
        params = params or {}
        
        order_data = {
            'symbol': self.format_symbol(symbol),
            'side': side.value.upper(),
            'type': order_type.value.upper(),
            'quantity': str(amount)
        }
        
        if order_type == OrderType.LIMIT:
            order_data['price'] = str(price)
            order_data['timeInForce'] = params.get('timeInForce', 'GTC')
            
        # Send signed request
        headers = await self._sign_request('POST', '/api/v3/order')
        url = f"{self.base_url}/api/v3/order"
        
        async with self.session.post(url, params=order_data, headers=self._get_default_headers()) as resp:
            data = await resp.json()
            
        if 'code' in data:
            raise Exception(f"Order failed: {data['msg']}")
            
        return self._parse_order(data)
        
    async def cancel_order(self, order_id: str, symbol: str = None) -> Order:
        """Cancel order"""
        params = {
            'symbol': self.format_symbol(symbol),
            'orderId': order_id
        }
        
        data = await self._make_request('DELETE', '/api/v3/order', params=params, signed=True)
        return self._parse_order(data)
        
    async def get_order(self, order_id: str, symbol: str = None) -> Order:
        """Get order status"""
        params = {
            'symbol': self.format_symbol(symbol),
            'orderId': order_id
        }
        
        data = await self._make_request('GET', '/api/v3/order', params=params, signed=True)
        return self._parse_order(data)
        
    async def get_open_orders(self, symbol: str = None) -> List[Order]:
        """Get open orders"""
        params = {}
        if symbol:
            params['symbol'] = self.format_symbol(symbol)
            
        data = await self._make_request('GET', '/api/v3/openOrders', params=params, signed=True)
        return [self._parse_order(o) for o in data]
        
    async def get_order_history(self, symbol: str = None, limit: int = 100) -> List[Order]:
        """Get order history"""
        params = {'limit': limit}
        if symbol:
            params['symbol'] = self.format_symbol(symbol)
            
        data = await self._make_request('GET', '/api/v3/allOrders', params=params, signed=True)
        return [self._parse_order(o) for o in data]
        
    def _parse_order(self, data: Dict) -> Order:
        """Parse Binance order response"""
        status_map = {
            'NEW': OrderStatus.OPEN,
            'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
            'FILLED': OrderStatus.FILLED,
            'CANCELED': OrderStatus.CANCELLED,
            'REJECTED': OrderStatus.REJECTED,
            'EXPIRED': OrderStatus.CANCELLED
        }
        
        return Order(
            id=str(data['orderId']),
            symbol=data['symbol'],
            side=OrderSide.BUY if data['side'] == 'BUY' else OrderSide.SELL,
            order_type=OrderType(data['type'].lower()),
            amount=Decimal(data['origQty']),
            filled=Decimal(data.get('executedQty', 0)),
            remaining=Decimal(data['origQty']) - Decimal(data.get('executedQty', 0)),
            price=Decimal(data['price']) if data.get('price') else None,
            status=status_map.get(data['status'], OrderStatus.PENDING),
            average_price=Decimal(data.get('avgPrice', 0)) if data.get('avgPrice') else None,
            timestamp=data.get('time', int(time.time() * 1000)) / 1000,
            raw_data=data
        )
        
    # ========== WebSocket ==========
    
    async def _websocket_loop(self, symbols: List[str],
                             on_ticker: callable,
                             on_orderbook: callable,
                             on_trade: callable):
        """WebSocket data stream"""
        streams = []
        for symbol in symbols:
            symbol_lower = symbol.lower().replace('-', '')
            if on_orderbook:
                streams.append(f"{symbol_lower}@depth10")
            if on_ticker:
                streams.append(f"{symbol_lower}@ticker")
            if on_trade:
                streams.append(f"{symbol_lower}@trade")
                
        stream_path = '/'.join(streams)
        ws_url = f"{self.ws_url}/stream?streams={stream_path}"
        
        while self._running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(ws_url) as ws:
                        logger.info(f"WebSocket connected for {symbols}")
                        
                        async for msg in ws:
                            if not self._running:
                                break
                                
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = msg.json()
                                await self._handle_ws_message(data, on_ticker, on_orderbook, on_trade)
                                
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                                
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(5)
                
    async def _handle_ws_message(self, data: Dict, on_ticker, on_orderbook, on_trade):
        """Handle WebSocket message"""
        stream = data.get('stream', '')
        payload = data.get('data', {})
        
        if '@ticker' in stream and on_ticker:
            symbol = stream.split('@')[0].upper()
            ticker = Ticker(
                symbol=symbol,
                bid=Decimal(payload.get('b', 0)),
                ask=Decimal(payload.get('a', 0)),
                last=Decimal(payload.get('c', 0)),
                volume_24h=Decimal(payload.get('v', 0)),
                high_24h=Decimal(payload.get('h', 0)),
                low_24h=Decimal(payload.get('l', 0)),
                change_24h=Decimal(payload.get('p', 0)),
                change_pct_24h=Decimal(payload.get('P', 0)),
                timestamp=payload.get('E', int(time.time() * 1000)) / 1000
            )
            await on_ticker(ticker)
            
        elif '@depth' in stream and on_orderbook:
            symbol = stream.split('@')[0].upper()
            orderbook = OrderBook(
                symbol=symbol,
                bids=[(Decimal(b[0]), Decimal(b[1])) for b in payload.get('b', [])[:10]],
                asks=[(Decimal(a[0]), Decimal(a[1])) for a in payload.get('a', [])[:10]],
                timestamp=payload.get('E', int(time.time() * 1000)) / 1000
            )
            await on_orderbook(orderbook)
            
        elif '@trade' in stream and on_trade:
            symbol = stream.split('@')[0].upper()
            trade = Trade(
                id=str(payload.get('t', 0)),
                symbol=symbol,
                side=OrderSide.BUY if not payload.get('m') else OrderSide.SELL,
                amount=Decimal(payload.get('q', 0)),
                price=Decimal(payload.get('p', 0)),
                fee=Decimal('0'),
                fee_currency='',
                timestamp=payload.get('T', int(time.time() * 1000)) / 1000
            )
            await on_trade(trade)
            
    def format_symbol(self, symbol: str) -> str:
        """Format symbol for Binance (BTC-USD -> BTCUSDT)"""
        return symbol.replace('-', '').replace('USD', 'USDT')
