"""
AMCIS Market Analysis Multi-Agent System
Coordinated analysis across multiple specialized agents for comprehensive market intelligence
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import time
import json

from core.agent_base import BaseAgent, AgentMessage, AgentPriority, AgentSwarm

logger = logging.getLogger(__name__)


class SignalStrength(Enum):
    STRONG_BUY = 5
    BUY = 4
    NEUTRAL = 3
    SELL = 2
    STRONG_SELL = 1


@dataclass
class MarketInsight:
    """Structured market insight from analysis"""
    source: str  # Which analyzer produced this
    symbol: str
    timeframe: str  # '1m', '5m', '1h', '4h', '1d'
    
    signal: SignalStrength
    confidence: float  # 0.0 to 1.0
    
    # Analysis data
    indicators: Dict[str, float] = field(default_factory=dict)
    patterns_detected: List[str] = field(default_factory=list)
    key_levels: Dict[str, float] = field(default_factory=dict)
    
    # Rationale
    reasoning: str = ""
    
    # Metadata
    timestamp: float = field(default_factory=time.time)
    expires_at: float = 0
    
    def __post_init__(self):
        if self.expires_at == 0:
            # Default expiration based on timeframe
            ttl = {
                '1m': 60, '5m': 300, '15m': 900,
                '1h': 3600, '4h': 14400, '1d': 86400
            }.get(self.timeframe, 3600)
            self.expires_at = time.time() + ttl


@dataclass
class AggregatedSignal:
    """Aggregated signal from multiple analyzers"""
    symbol: str
    timestamp: float
    
    # Consensus
    consensus_signal: SignalStrength
    consensus_confidence: float
    
    # Component signals
    component_signals: Dict[str, MarketInsight]
    
    # Action recommendation
    recommended_action: str  # 'buy', 'sell', 'hold', 'avoid'
    position_size_pct: float  # Recommended position size 0-100%
    
    # Risk metrics
    risk_score: float  # 0-100
    volatility_forecast: float
    
    # Targets
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Expected returns
    expected_return_24h: float = 0.0
    expected_return_7d: float = 0.0


class TechnicalAnalyzer(BaseAgent):
    """
    Technical analysis agent - patterns, indicators, support/resistance
    """
    
    def __init__(self, name: str, message_bus, config: Optional[Dict] = None):
        super().__init__(name, "technical_analyzer", message_bus, config)
        
        self.timeframes = config.get('timeframes', ['1h', '4h', '1d'])
        self.symbols = config.get('symbols', ['BTC-USD', 'ETH-USD'])
        
        # Price history cache
        self.price_history: Dict[str, List[Dict]] = {}  # symbol -> OHLCV data
        self.max_history = 1000
        
        self._message_handlers = {
            'market.ohlcv': self._on_ohlcv_update,
        }
        
    async def execute_cycle(self):
        """Run technical analysis on all symbols/timeframes"""
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                await self._analyze_technical(symbol, timeframe)
                
    async def _analyze_technical(self, symbol: str, timeframe: str):
        """Perform technical analysis"""
        history = self.price_history.get(symbol, [])
        
        if len(history) < 50:
            return
            
        closes = [c['close'] for c in history[-100:]]
        highs = [c['high'] for c in history[-100:]]
        lows = [c['low'] for c in history[-100:]]
        volumes = [c['volume'] for c in history[-100:]]
        
        # Calculate indicators
        indicators = {}
        
        # RSI
        indicators['rsi'] = self._calculate_rsi(closes, 14)
        
        # Moving averages
        indicators['sma_20'] = sum(closes[-20:]) / 20
        indicators['sma_50'] = sum(closes[-50:]) / 50
        indicators['ema_12'] = self._calculate_ema(closes, 12)
        indicators['ema_26'] = self._calculate_ema(closes, 26)
        
        # MACD
        indicators['macd'] = indicators['ema_12'] - indicators['ema_26']
        
        # Bollinger Bands
        bb = self._calculate_bollinger_bands(closes, 20)
        indicators['bb_upper'] = bb['upper']
        indicators['bb_lower'] = bb['lower']
        indicators['bb_width'] = bb['width']
        
        # Volume analysis
        indicators['volume_sma'] = sum(volumes[-20:]) / 20
        indicators['volume_ratio'] = volumes[-1] / indicators['volume_sma'] if indicators['volume_sma'] > 0 else 1
        
        # Detect patterns
        patterns = self._detect_patterns(closes, highs, lows)
        
        # Key levels
        key_levels = self._calculate_key_levels(closes, highs, lows)
        
        # Generate signal
        signal, confidence = self._generate_signal(indicators, patterns, closes)
        
        # Create insight
        insight = MarketInsight(
            source=self.name,
            symbol=symbol,
            timeframe=timeframe,
            signal=signal,
            confidence=confidence,
            indicators=indicators,
            patterns_detected=patterns,
            key_levels=key_levels,
            reasoning=self._generate_reasoning(signal, indicators, patterns)
        )
        
        # Broadcast insight
        await self.send_message(
            'analysis.technical',
            {'insight': self._insight_to_dict(insight)},
            priority=AgentPriority.NORMAL
        )
        
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI"""
        if len(closes) < period + 1:
            return 50.0
            
        gains = []
        losses = []
        
        for i in range(1, period + 1):
            change = closes[-i] - closes[-i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
                
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
        
    def _calculate_ema(self, data: List[float], period: int) -> float:
        """Calculate EMA"""
        if len(data) < period:
            return data[-1] if data else 0
            
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
            
        return ema
        
    def _calculate_bollinger_bands(self, closes: List[float], period: int = 20) -> Dict:
        """Calculate Bollinger Bands"""
        if len(closes) < period:
            return {'upper': closes[-1] if closes else 0, 'lower': closes[-1] if closes else 0, 'width': 0}
            
        sma = sum(closes[-period:]) / period
        variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
        std = variance ** 0.5
        
        return {
            'upper': sma + (std * 2),
            'lower': sma - (std * 2),
            'width': (std * 4) / sma if sma > 0 else 0
        }
        
    def _detect_patterns(self, closes: List[float], highs: List[float], lows: List[float]) -> List[str]:
        """Detect chart patterns"""
        patterns = []
        
        # Need at least 20 candles
        if len(closes) < 20:
            return patterns
            
        # Double top
        recent_highs = highs[-20:]
        if len(recent_highs) >= 2:
            if abs(recent_highs[-1] - max(recent_highs[:-1])) / max(recent_highs[:-1]) < 0.02:
                patterns.append('double_top')
                
        # Double bottom
        recent_lows = lows[-20:]
        if len(recent_lows) >= 2:
            if abs(recent_lows[-1] - min(recent_lows[:-1])) / min(recent_lows[:-1]) < 0.02:
                patterns.append('double_bottom')
                
        # Higher highs / Lower lows trend
        if closes[-1] > max(closes[-10:-1]):
            patterns.append('breakout_high')
        elif closes[-1] < min(closes[-10:-1]):
            patterns.append('breakout_low')
            
        return patterns
        
    def _calculate_key_levels(self, closes: List[float], highs: List[float], lows: List[float]) -> Dict:
        """Calculate support and resistance levels"""
        return {
            'support_1': min(lows[-20:]),
            'support_2': min(lows[-50:]) if len(lows) >= 50 else min(lows),
            'resistance_1': max(highs[-20:]),
            'resistance_2': max(highs[-50:]) if len(highs) >= 50 else max(highs),
            'pivot': (max(highs[-1:]) + min(lows[-1:]) + closes[-1]) / 3 if closes else 0
        }
        
    def _generate_signal(self, indicators: Dict, patterns: List[str], closes: List[float]) -> Tuple[SignalStrength, float]:
        """Generate trading signal from indicators"""
        score = 0
        
        # RSI signals
        rsi = indicators.get('rsi', 50)
        if rsi < 30:
            score += 2
        elif rsi < 40:
            score += 1
        elif rsi > 70:
            score -= 2
        elif rsi > 60:
            score -= 1
            
        # Moving average signals
        if closes[-1] > indicators.get('sma_20', 0):
            score += 1
        if closes[-1] > indicators.get('sma_50', 0):
            score += 1
            
        # MACD
        if indicators.get('macd', 0) > 0:
            score += 1
        else:
            score -= 1
            
        # Pattern signals
        if 'double_bottom' in patterns:
            score += 2
        if 'double_top' in patterns:
            score -= 2
        if 'breakout_high' in patterns:
            score += 1
        if 'breakout_low' in patterns:
            score -= 1
            
        # Volume confirmation
        if indicators.get('volume_ratio', 1) > 1.5:
            score *= 1.2
            
        # Map score to signal
        if score >= 3:
            signal = SignalStrength.STRONG_BUY
        elif score >= 1:
            signal = SignalStrength.BUY
        elif score <= -3:
            signal = SignalStrength.STRONG_SELL
        elif score <= -1:
            signal = SignalStrength.SELL
        else:
            signal = SignalStrength.NEUTRAL
            
        confidence = min(abs(score) / 4, 1.0)
        
        return signal, confidence
        
    def _generate_reasoning(self, signal: SignalStrength, indicators: Dict, patterns: List[str]) -> str:
        """Generate human-readable reasoning"""
        reasons = []
        
        rsi = indicators.get('rsi', 50)
        if rsi < 30:
            reasons.append(f"Oversold (RSI: {rsi:.1f})")
        elif rsi > 70:
            reasons.append(f"Overbought (RSI: {rsi:.1f})")
            
        if patterns:
            reasons.append(f"Patterns: {', '.join(patterns)}")
            
        if indicators.get('volume_ratio', 1) > 1.5:
            reasons.append("High volume confirmation")
            
        return "; ".join(reasons) if reasons else "Mixed signals"
        
    def _insight_to_dict(self, insight: MarketInsight) -> Dict:
        """Convert insight to dictionary"""
        return {
            'source': insight.source,
            'symbol': insight.symbol,
            'timeframe': insight.timeframe,
            'signal': insight.signal.name,
            'confidence': insight.confidence,
            'indicators': insight.indicators,
            'patterns': insight.patterns_detected,
            'key_levels': insight.key_levels,
            'reasoning': insight.reasoning,
            'timestamp': insight.timestamp,
            'expires_at': insight.expires_at
        }
        
    async def _on_ohlcv_update(self, message: AgentMessage):
        """Handle OHLCV data updates"""
        payload = message.payload
        symbol = payload.get('symbol')
        candle = payload.get('candle')
        
        if symbol and candle:
            if symbol not in self.price_history:
                self.price_history[symbol] = []
                
            self.price_history[symbol].append(candle)
            
            # Trim history
            if len(self.price_history[symbol]) > self.max_history:
                self.price_history[symbol] = self.price_history[symbol][-self.max_history:]


class SentimentAnalyzer(BaseAgent):
    """
    Sentiment analysis agent - social media, news, on-chain metrics
    """
    
    def __init__(self, name: str, message_bus, config: Optional[Dict] = None):
        super().__init__(name, "sentiment_analyzer", message_bus, config)
        
        self.symbols = config.get('symbols', ['BTC', 'ETH'])
        self.data_sources = config.get('sources', ['twitter', 'reddit', 'news', 'onchain'])
        
        self.sentiment_cache: Dict[str, Dict] = {}
        
        self._message_handlers = {
            'sentiment.data': self._on_sentiment_data,
            'onchain.metrics': self._on_onchain_metrics,
        }
        
    async def execute_cycle(self):
        """Analyze sentiment across data sources"""
        for symbol in self.symbols:
            sentiment = await self._aggregate_sentiment(symbol)
            
            insight = MarketInsight(
                source=self.name,
                symbol=symbol,
                timeframe='1h',
                signal=sentiment['signal'],
                confidence=sentiment['confidence'],
                indicators=sentiment['metrics'],
                reasoning=sentiment['summary']
            )
            
            await self.send_message(
                'analysis.sentiment',
                {'insight': {
                    'source': insight.source,
                    'symbol': insight.symbol,
                    'signal': insight.signal.name,
                    'confidence': insight.confidence,
                    'metrics': insight.indicators,
                    'reasoning': insight.reasoning,
                    'timestamp': insight.timestamp
                }},
                priority=AgentPriority.NORMAL
            )
            
    async def _aggregate_sentiment(self, symbol: str) -> Dict:
        """Aggregate sentiment from all sources"""
        cache = self.sentiment_cache.get(symbol, {})
        
        # Social sentiment
        social_score = cache.get('social_sentiment', 0.5)
        
        # News sentiment
        news_score = cache.get('news_sentiment', 0.5)
        
        # On-chain sentiment (active addresses, transaction volume, etc.)
        onchain_score = cache.get('onchain_health', 0.5)
        
        # Weighted average
        weights = {'social': 0.3, 'news': 0.3, 'onchain': 0.4}
        composite = (
            social_score * weights['social'] +
            news_score * weights['news'] +
            onchain_score * weights['onchain']
        )
        
        # Determine signal
        if composite > 0.7:
            signal = SignalStrength.STRONG_BUY
        elif composite > 0.55:
            signal = SignalStrength.BUY
        elif composite < 0.3:
            signal = SignalStrength.STRONG_SELL
        elif composite < 0.45:
            signal = SignalStrength.SELL
        else:
            signal = SignalStrength.NEUTRAL
            
        return {
            'signal': signal,
            'confidence': abs(composite - 0.5) * 2,
            'metrics': {
                'social': social_score,
                'news': news_score,
                'onchain': onchain_score,
                'composite': composite
            },
            'summary': f"Composite sentiment: {composite:.2f} (Social: {social_score:.2f}, News: {news_score:.2f}, On-chain: {onchain_score:.2f})"
        }
        
    async def _on_sentiment_data(self, message: AgentMessage):
        """Handle incoming sentiment data"""
        payload = message.payload
        symbol = payload.get('symbol')
        source = payload.get('source')
        score = payload.get('score')
        
        if symbol and source and score is not None:
            if symbol not in self.sentiment_cache:
                self.sentiment_cache[symbol] = {}
                
            if source == 'twitter' or source == 'reddit':
                self.sentiment_cache[symbol]['social_sentiment'] = score
            elif source == 'news':
                self.sentiment_cache[symbol]['news_sentiment'] = score
                
    async def _on_onchain_metrics(self, message: AgentMessage):
        """Handle on-chain metrics"""
        payload = message.payload
        symbol = payload.get('symbol')
        metrics = payload.get('metrics', {})
        
        if symbol:
            # Calculate on-chain health score
            health = 0.5
            
            # Active addresses trend
            addr_change = metrics.get('active_addresses_change', 0)
            if addr_change > 0.1:
                health += 0.1
            elif addr_change < -0.1:
                health -= 0.1
                
            # Transaction volume trend
            tx_change = metrics.get('tx_volume_change', 0)
            if tx_change > 0.1:
                health += 0.1
            elif tx_change < -0.1:
                health -= 0.1
                
            # Exchange flows (negative = outflow = bullish)
            exchange_flow = metrics.get('exchange_netflow', 0)
            if exchange_flow < 0:
                health += 0.1
            else:
                health -= 0.05
                
            if symbol not in self.sentiment_cache:
                self.sentiment_cache[symbol] = {}
                
            self.sentiment_cache[symbol]['onchain_health'] = max(0, min(1, health))


class SignalAggregator(BaseAgent):
    """
    Aggregates signals from multiple analyzers into actionable insights
    """
    
    def __init__(self, name: str, message_bus, config: Optional[Dict] = None):
        super().__init__(name, "signal_aggregator", message_bus, config)
        
        self.symbols = config.get('symbols', ['BTC-USD', 'ETH-USD'])
        
        # Signal storage
        self.insights: Dict[str, List[MarketInsight]] = {s: [] for s in self.symbols}
        self.insight_ttl = 3600  # 1 hour
        
        # Weights for different analyzers
        self.analyzer_weights = {
            'technical_analyzer': 0.4,
            'sentiment_analyzer': 0.3,
            'onchain_analyzer': 0.3
        }
        
        self._message_handlers = {
            'analysis.technical': self._on_analysis,
            'analysis.sentiment': self._on_analysis,
            'analysis.onchain': self._on_analysis,
        }
        
    async def execute_cycle(self):
        """Aggregate signals and generate trading recommendations"""
        # Clean expired insights
        await self._cleanup_expired()
        
        # Aggregate for each symbol
        for symbol in self.symbols:
            aggregated = await self._aggregate_symbol(symbol)
            
            if aggregated:
                # Broadcast aggregated signal
                await self.send_message(
                    'signal.aggregated',
                    {
                        'signal': {
                            'symbol': aggregated.symbol,
                            'consensus': aggregated.consensus_signal.name,
                            'confidence': aggregated.consensus_confidence,
                            'action': aggregated.recommended_action,
                            'position_size_pct': aggregated.position_size_pct,
                            'risk_score': aggregated.risk_score,
                            'entry': aggregated.entry_price,
                            'stop_loss': aggregated.stop_loss,
                            'take_profit': aggregated.take_profit,
                            'expected_return_24h': aggregated.expected_return_24h,
                            'component_signals': {
                                k: {
                                    'source': v.source,
                                    'signal': v.signal.name,
                                    'confidence': v.confidence
                                }
                                for k, v in aggregated.component_signals.items()
                            }
                        }
                    },
                    priority=AgentPriority.HIGH if aggregated.consensus_confidence > 0.7 else AgentPriority.NORMAL
                )
                
    async def _cleanup_expired(self):
        """Remove expired insights"""
        now = time.time()
        for symbol in self.insights:
            self.insights[symbol] = [
                i for i in self.insights[symbol]
                if i.expires_at > now
            ]
            
    async def _aggregate_symbol(self, symbol: str) -> Optional[AggregatedSignal]:
        """Aggregate all insights for a symbol"""
        insights = self.insights.get(symbol, [])
        
        if not insights:
            return None
            
        # Group by source
        by_source: Dict[str, MarketInsight] = {}
        for insight in insights:
            by_source[insight.source] = insight
            
        if not by_source:
            return None
            
        # Calculate weighted consensus
        weighted_score = 0
        total_weight = 0
        
        signal_values = {
            SignalStrength.STRONG_BUY: 2,
            SignalStrength.BUY: 1,
            SignalStrength.NEUTRAL: 0,
            SignalStrength.SELL: -1,
            SignalStrength.STRONG_SELL: -2
        }
        
        for source, insight in by_source.items():
            weight = self.analyzer_weights.get(source, 0.2)
            score = signal_values.get(insight.signal, 0) * insight.confidence
            weighted_score += score * weight
            total_weight += weight
            
        if total_weight == 0:
            return None
            
        normalized_score = weighted_score / total_weight
        
        # Determine consensus signal
        if normalized_score > 1.2:
            consensus = SignalStrength.STRONG_BUY
        elif normalized_score > 0.5:
            consensus = SignalStrength.BUY
        elif normalized_score < -1.2:
            consensus = SignalStrength.STRONG_SELL
        elif normalized_score < -0.5:
            consensus = SignalStrength.SELL
        else:
            consensus = SignalStrength.NEUTRAL
            
        # Calculate confidence
        confidence = min(abs(normalized_score) / 2, 1.0)
        
        # Determine action
        if consensus in [SignalStrength.STRONG_BUY, SignalStrength.BUY]:
            action = 'buy'
            position_size = min(confidence * 100, 50)  # Max 50% per signal
        elif consensus in [SignalStrength.STRONG_SELL, SignalStrength.SELL]:
            action = 'sell'
            position_size = min(confidence * 100, 50)
        else:
            action = 'hold'
            position_size = 0
            
        # Calculate risk score (inverse of confidence, adjusted by volatility)
        risk_score = (1 - confidence) * 50
        
        # Get price levels from technical analysis
        entry = stop = take = None
        if 'technical_analyzer' in by_source:
            tech = by_source['technical_analyzer']
            entry = tech.indicators.get('sma_20')
            support = tech.key_levels.get('support_1')
            resistance = tech.key_levels.get('resistance_1')
            
            if action == 'buy':
                stop = support
                take = resistance
            else:
                stop = resistance
                take = support
                
        # Expected returns (simplified model)
        expected_24h = normalized_score * 0.05  # 5% per score unit
        expected_7d = expected_24h * 3
        
        return AggregatedSignal(
            symbol=symbol,
            timestamp=time.time(),
            consensus_signal=consensus,
            consensus_confidence=confidence,
            component_signals=by_source,
            recommended_action=action,
            position_size_pct=position_size,
            risk_score=risk_score,
            volatility_forecast=abs(expected_24h),
            entry_price=entry,
            stop_loss=stop,
            take_profit=take,
            expected_return_24h=expected_24h,
            expected_return_7d=expected_7d
        )
        
    async def _on_analysis(self, message: AgentMessage):
        """Handle incoming analysis from other agents"""
        payload = message.payload
        insight_dict = payload.get('insight')
        
        if insight_dict:
            symbol = insight_dict.get('symbol')
            if symbol in self.insights:
                insight = MarketInsight(
                    source=insight_dict.get('source', ''),
                    symbol=symbol,
                    timeframe=insight_dict.get('timeframe', '1h'),
                    signal=SignalStrength[insight_dict.get('signal', 'NEUTRAL')],
                    confidence=insight_dict.get('confidence', 0.5),
                    indicators=insight_dict.get('indicators', {}),
                    patterns_detected=insight_dict.get('patterns', []),
                    key_levels=insight_dict.get('key_levels', {}),
                    reasoning=insight_dict.get('reasoning', ''),
                    timestamp=insight_dict.get('timestamp', time.time()),
                    expires_at=insight_dict.get('expires_at', time.time() + 3600)
                )
                
                # Remove old insight from same source
                self.insights[symbol] = [
                    i for i in self.insights[symbol]
                    if i.source != insight.source
                ]
                
                self.insights[symbol].append(insight)


class MarketAnalysisSwarm(AgentSwarm):
    """
    Coordinated swarm of market analysis agents
    """
    
    def __init__(self, name: str, message_bus: Optional[Any] = None):
        if message_bus is None:
            from core.agent_base import get_message_bus
            message_bus = get_message_bus()
            
        super().__init__(name, message_bus)
        
    async def initialize(self, config: Optional[Dict] = None):
        """Initialize all analysis agents"""
        config = config or {}
        
        # Create analyzers
        technical = TechnicalAnalyzer(
            "TechnicalAnalyzer",
            self.message_bus,
            config.get('technical', {})
        )
        
        sentiment = SentimentAnalyzer(
            "SentimentAnalyzer",
            self.message_bus,
            config.get('sentiment', {})
        )
        
        aggregator = SignalAggregator(
            "SignalAggregator",
            self.message_bus,
            config.get('aggregator', {})
        )
        
        # Add to swarm
        await self.add_agent(technical)
        await self.add_agent(sentiment)
        await self.add_agent(aggregator)
        
        logger.info(f"Market analysis swarm initialized with {len(self.agents)} agents")
        
    async def start(self):
        """Start all analysis agents"""
        await self.start_all()
        
    async def stop(self):
        """Stop all analysis agents"""
        await self.stop_all()
