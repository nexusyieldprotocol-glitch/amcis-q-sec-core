"""
AMCIS DNS Tunnel Detector
=========================

DNS tunneling detection using entropy analysis, frequency analysis,
and behavioral pattern recognition.

Detection Methods:
- Shannon entropy analysis
- Query frequency analysis
- Domain generation algorithm (DGA) detection
- Payload size analysis
- NXDOMAIN ratio analysis

NIST Alignment: SP 800-53 (SI-4 Information System Monitoring)
"""

import math
import re
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog


class DNSTunnelIndicator(Enum):
    """DNS tunneling indicators."""
    HIGH_ENTROPY = auto()
    LONG_SUBDOMAIN = auto()
    HIGH_QUERY_FREQUENCY = auto()
    NXDOMAIN_FLOOD = auto()
    DGA_PATTERN = auto()
    PAYLOAD_LIKE = auto()
    SUSPICIOUS_TLD = auto()


@dataclass
class DNSQuery:
    """DNS query record."""
    timestamp: float
    query_name: str
    query_type: str
    client_ip: str
    response_code: Optional[int] = None
    response_ips: List[str] = field(default_factory=list)
    packet_size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "query_name": self.query_name,
            "query_type": self.query_type,
            "client_ip": self.client_ip,
            "response_code": self.response_code,
            "response_ips": self.response_ips,
            "packet_size": self.packet_size
        }


@dataclass
class TunnelAlert:
    """DNS tunneling alert."""
    client_ip: str
    indicators: List[DNSTunnelIndicator]
    confidence: float
    query_count: int
    sample_domains: List[str]
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "client_ip": self.client_ip,
            "indicators": [i.name for i in self.indicators],
            "confidence": self.confidence,
            "query_count": self.query_count,
            "sample_domains": self.sample_domains,
            "timestamp": self.timestamp
        }


class DNSTunnelDetector:
    """
    AMCIS DNS Tunnel Detector
    =========================
    
    Multi-factor DNS tunneling detection using statistical
    and behavioral analysis.
    """
    
    # Detection thresholds
    ENTROPY_THRESHOLD = 4.0  # Shannon entropy
    SUBDOMAIN_LENGTH_THRESHOLD = 30  # Characters
    QUERY_FREQUENCY_THRESHOLD = 60  # Queries per minute
    NXDOMAIN_RATIO_THRESHOLD = 0.7  # 70% NXDOMAIN
    UNIQUE_DOMAINS_THRESHOLD = 50  # Unique domains per window
    
    # Analysis window
    ANALYSIS_WINDOW_SECONDS = 300  # 5 minutes
    
    # Suspicious TLDs often used for tunneling
    SUSPICIOUS_TLDS = {
        '.tk', '.ml', '.ga', '.cf', '.gq',  # Free domains
        '.bit', '.eth', '.crypto',  # Blockchain domains
    }
    
    # Base64-like character distribution
    BASE64_CHARS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    
    def __init__(self, kernel=None) -> None:
        """
        Initialize DNS tunnel detector.
        
        Args:
            kernel: AMCIS kernel reference
        """
        self.kernel = kernel
        self.logger = structlog.get_logger("amcis.dns_tunnel_detector")
        
        # Query storage
        self._queries: List[DNSQuery] = []
        self._max_queries = 100000
        
        # Per-client statistics
        self._client_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "queries": [],
            "domains": set(),
            "nxdomains": 0,
            "total": 0
        })
        
        # Alerts
        self._alerts: List[TunnelAlert] = []
        self._max_alerts = 1000
        
        # Whitelist
        self._whitelist: Set[str] = set()
        
        # Callbacks
        self._alert_callbacks: List[Any] = []
        
        self.logger.info("dns_tunnel_detector_initialized")
    
    def add_query(self, query: DNSQuery) -> Optional[TunnelAlert]:
        """
        Process DNS query and detect tunneling.
        
        Args:
            query: DNS query to process
            
        Returns:
            Alert if tunneling detected
        """
        # Add to storage
        self._queries.append(query)
        while len(self._queries) > self._max_queries:
            self._queries.pop(0)
        
        # Update client stats
        stats = self._client_stats[query.client_ip]
        stats["queries"].append(query)
        stats["domains"].add(query.query_name)
        stats["total"] += 1
        
        if query.response_code == 3:  # NXDOMAIN
            stats["nxdomains"] += 1
        
        # Clean old queries
        cutoff = time.time() - self.ANALYSIS_WINDOW_SECONDS
        stats["queries"] = [q for q in stats["queries"] if q.timestamp > cutoff]
        
        # Analyze for tunneling
        return self._analyze_client(query.client_ip)
    
    def _analyze_client(self, client_ip: str) -> Optional[TunnelAlert]:
        """Analyze client for DNS tunneling."""
        stats = self._client_stats[client_ip]
        queries = stats["queries"]
        
        if len(queries) < 10:  # Need minimum sample size
            return None
        
        indicators = []
        scores = []
        
        # Check entropy
        entropy_score = self._check_entropy(queries)
        if entropy_score > 0:
            indicators.append(DNSTunnelIndicator.HIGH_ENTROPY)
            scores.append(entropy_score)
        
        # Check subdomain length
        length_score = self._check_subdomain_length(queries)
        if length_score > 0:
            indicators.append(DNSTunnelIndicator.LONG_SUBDOMAIN)
            scores.append(length_score)
        
        # Check query frequency
        freq_score = self._check_query_frequency(queries)
        if freq_score > 0:
            indicators.append(DNSTunnelIndicator.HIGH_QUERY_FREQUENCY)
            scores.append(freq_score)
        
        # Check NXDOMAIN ratio
        nxdomain_score = self._check_nxdomain_ratio(stats)
        if nxdomain_score > 0:
            indicators.append(DNSTunnelIndicator.NXDOMAIN_FLOOD)
            scores.append(nxdomain_score)
        
        # Check DGA pattern
        dga_score = self._check_dga_pattern(queries)
        if dga_score > 0:
            indicators.append(DNSTunnelIndicator.DGA_PATTERN)
            scores.append(dga_score)
        
        # Check payload-like patterns
        payload_score = self._check_payload_patterns(queries)
        if payload_score > 0:
            indicators.append(DNSTunnelIndicator.PAYLOAD_LIKE)
            scores.append(payload_score)
        
        # Check suspicious TLDs
        tld_score = self._check_suspicious_tlds(queries)
        if tld_score > 0:
            indicators.append(DNSTunnelIndicator.SUSPICIOUS_TLD)
            scores.append(tld_score)
        
        # Calculate overall confidence
        if indicators:
            # More indicators = higher confidence
            confidence = min(0.95, 0.4 + len(indicators) * 0.1 + max(scores) * 0.3)
            
            # Sample suspicious domains
            sample_domains = list(stats["domains"])[:5]
            
            alert = TunnelAlert(
                client_ip=client_ip,
                indicators=indicators,
                confidence=confidence,
                query_count=len(queries),
                sample_domains=sample_domains
            )
            
            self._alerts.append(alert)
            while len(self._alerts) > self._max_alerts:
                self._alerts.pop(0)
            
            self.logger.warning(
                "dns_tunnel_detected",
                client_ip=client_ip,
                indicators=[i.name for i in indicators],
                confidence=confidence
            )
            
            return alert
        
        return None
    
    def _check_entropy(self, queries: List[DNSQuery]) -> float:
        """Check subdomain entropy."""
        entropies = []
        
        for query in queries:
            # Get subdomain (everything before last 2 parts)
            parts = query.query_name.split('.')
            if len(parts) > 2:
                subdomain = '.'.join(parts[:-2])
                if len(subdomain) > 10:
                    entropy = self._calculate_entropy(subdomain)
                    entropies.append(entropy)
        
        if not entropies:
            return 0.0
        
        avg_entropy = statistics.mean(entropies)
        
        if avg_entropy > self.ENTROPY_THRESHOLD:
            return min(1.0, (avg_entropy - self.ENTROPY_THRESHOLD) / 2.0)
        
        return 0.0
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy."""
        if not text:
            return 0.0
        
        freq = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1
        
        length = len(text)
        entropy = 0.0
        
        for count in freq.values():
            p = count / length
            entropy -= p * math.log2(p)
        
        return entropy
    
    def _check_subdomain_length(self, queries: List[DNSQuery]) -> float:
        """Check for unusually long subdomains."""
        long_count = 0
        
        for query in queries:
            parts = query.query_name.split('.')
            if len(parts) > 2:
                subdomain = '.'.join(parts[:-2])
                if len(subdomain) > self.SUBDOMAIN_LENGTH_THRESHOLD:
                    long_count += 1
        
        ratio = long_count / len(queries)
        
        if ratio > 0.3:
            return min(1.0, ratio)
        
        return 0.0
    
    def _check_query_frequency(self, queries: List[DNSQuery]) -> float:
        """Check query frequency."""
        if len(queries) < 2:
            return 0.0
        
        time_span = queries[-1].timestamp - queries[0].timestamp
        if time_span < 60:  # Less than a minute
            time_span = 60
        
        queries_per_minute = (len(queries) / time_span) * 60
        
        if queries_per_minute > self.QUERY_FREQUENCY_THRESHOLD:
            return min(1.0, queries_per_minute / self.QUERY_FREQUENCY_THRESHOLD / 2)
        
        return 0.0
    
    def _check_nxdomain_ratio(self, stats: Dict[str, Any]) -> float:
        """Check NXDOMAIN ratio."""
        if stats["total"] < 20:
            return 0.0
        
        ratio = stats["nxdomains"] / stats["total"]
        
        if ratio > self.NXDOMAIN_RATIO_THRESHOLD:
            return min(1.0, (ratio - self.NXDOMAIN_RATIO_THRESHOLD) * 2)
        
        return 0.0
    
    def _check_dga_pattern(self, queries: List[DNSQuery]) -> float:
        """Check for domain generation algorithm patterns."""
        domains = [q.query_name for q in queries]
        
        # Check for algorithmic patterns
        unique_domains = set(domains)
        
        if len(unique_domains) < self.UNIQUE_DOMAINS_THRESHOLD:
            return 0.0
        
        # Check character distribution
        consonant_vowel_ratio = self._analyze_character_distribution(unique_domains)
        
        if consonant_vowel_ratio > 2.5:  # High consonant ratio typical of DGAs
            return min(1.0, (consonant_vowel_ratio - 2.5) / 2)
        
        return 0.0
    
    def _analyze_character_distribution(self, domains: Set[str]) -> float:
        """Analyze character distribution for DGA detection."""
        consonants = set('bcdfghjklmnpqrstvwxyz')
        vowels = set('aeiou')
        
        consonant_count = 0
        vowel_count = 0
        
        for domain in domains:
            for char in domain.lower():
                if char in consonants:
                    consonant_count += 1
                elif char in vowels:
                    vowel_count += 1
        
        if vowel_count == 0:
            return 10.0
        
        return consonant_count / vowel_count
    
    def _check_payload_patterns(self, queries: List[DNSQuery]) -> float:
        """Check for payload-like patterns in subdomains."""
        base64_like = 0
        
        for query in queries:
            parts = query.query_name.split('.')
            if len(parts) > 2:
                subdomain = '.'.join(parts[:-2])
                # Check if subdomain looks like base64
                if len(subdomain) > 20:
                    base64_chars = sum(1 for c in subdomain if c in self.BASE64_CHARS)
                    if base64_chars / len(subdomain) > 0.9:
                        base64_like += 1
        
        ratio = base64_like / len(queries)
        
        if ratio > 0.2:
            return min(1.0, ratio * 2)
        
        return 0.0
    
    def _check_suspicious_tlds(self, queries: List[DNSQuery]) -> float:
        """Check for suspicious TLDs."""
        suspicious_count = 0
        
        for query in queries:
            for tld in self.SUSPICIOUS_TLDS:
                if query.query_name.endswith(tld):
                    suspicious_count += 1
                    break
        
        ratio = suspicious_count / len(queries)
        
        if ratio > 0.3:
            return min(1.0, ratio)
        
        return 0.0
    
    def whitelist_domain(self, domain: str) -> None:
        """Add domain to whitelist."""
        self._whitelist.add(domain)
        self.logger.info("domain_whitelisted", domain=domain)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            "total_queries": len(self._queries),
            "monitored_clients": len(self._client_stats),
            "total_alerts": len(self._alerts),
            "whitelisted_domains": len(self._whitelist)
        }
    
    def get_recent_alerts(self, count: int = 100) -> List[TunnelAlert]:
        """Get recent tunneling alerts."""
        return self._alerts[-count:] if self._alerts else []
