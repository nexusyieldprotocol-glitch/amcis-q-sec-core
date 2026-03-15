"""
IOC Matcher
===========

Real-time IOC matching against network traffic, files, and processes.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

from .threat_feed import ThreatFeed, IOCTypes, IOC, ThreatSeverity


@dataclass
class MatchResult:
    """IOC match result."""
    matched: bool
    ioc: Optional[IOC]
    match_type: str
    match_value: str
    context: Dict[str, Any]
    timestamp: float


class IOCMatcher:
    """
    IOC Matcher Engine
    ==================
    
    Matches network traffic, files, and processes against IOC database.
    """
    
    def __init__(self, threat_feed: ThreatFeed) -> None:
        self.feed = threat_feed
        self.logger = structlog.get_logger("amcis.ioc_matcher")
        
        # Bloom filter for fast negative lookups (simplified)
        self._hash_cache: Set[str] = set()
        
        self.logger.info("ioc_matcher_initialized")
    
    def check_file(self, file_path: str, file_hash: Optional[str] = None) -> MatchResult:
        """Check file against IOCs."""
        import time
        
        # Calculate hash if not provided
        if not file_hash:
            try:
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
            except Exception:
                return MatchResult(False, None, "", "", {}, time.time())
        
        # Check hash IOCs
        ioc = self.feed.check_ioc(file_hash, IOCTypes.HASH_SHA256)
        if ioc:
            return MatchResult(
                matched=True,
                ioc=ioc,
                match_type="file_hash",
                match_value=file_hash,
                context={"file_path": file_path},
                timestamp=time.time()
            )
        
        # Check MD5
        md5_hash = hashlib.md5(open(file_path, 'rb').read()).hexdigest() if not file_hash else None
        if md5_hash:
            ioc = self.feed.check_ioc(md5_hash, IOCTypes.HASH_MD5)
            if ioc:
                return MatchResult(
                    matched=True,
                    ioc=ioc,
                    match_type="file_hash_md5",
                    match_value=md5_hash,
                    context={"file_path": file_path},
                    timestamp=time.time()
                )
        
        return MatchResult(False, None, "", "", {}, time.time())
    
    def check_network_connection(self, dst_ip: str, dst_port: int,
                                  domain: Optional[str] = None) -> List[MatchResult]:
        """Check network connection against IOCs."""
        import time
        results = []
        
        # Check IP
        ioc = self.feed.check_ioc(dst_ip, IOCTypes.IP)
        if ioc:
            results.append(MatchResult(
                matched=True,
                ioc=ioc,
                match_type="ip",
                match_value=dst_ip,
                context={"port": dst_port},
                timestamp=time.time()
            ))
        
        # Check domain
        if domain:
            ioc = self.feed.check_ioc(domain, IOCTypes.DOMAIN)
            if ioc:
                results.append(MatchResult(
                    matched=True,
                    ioc=ioc,
                    match_type="domain",
                    match_value=domain,
                    context={"ip": dst_ip, "port": dst_port},
                    timestamp=time.time()
                ))
        
        return results
    
    def check_email(self, sender: str, subject: str, 
                   body_hashes: Optional[List[str]] = None) -> List[MatchResult]:
        """Check email against IOCs."""
        import time
        results = []
        
        # Check sender
        ioc = self.feed.check_ioc(sender, IOCTypes.EMAIL)
        if ioc:
            results.append(MatchResult(
                matched=True,
                ioc=ioc,
                match_type="email_sender",
                match_value=sender,
                context={"subject": subject},
                timestamp=time.time()
            ))
        
        return results
    
    def check_process(self, process_name: str, cmdline: str,
                     connections: Optional[List[Tuple[str, int]]] = None) -> List[MatchResult]:
        """Check process against IOCs."""
        import time
        results = []
        
        # Check mutex (simplified - would need Windows API)
        # Check network connections
        if connections:
            for ip, port in connections:
                matches = self.check_network_connection(ip, port)
                results.extend(matches)
        
        return results
