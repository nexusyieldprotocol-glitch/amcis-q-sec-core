"""
API Gateway
===========

API security gateway with authentication, rate limiting, and WAF.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
import time

import structlog

from .waf_engine import WAFEngine, HTTPRequest, WAFDecision


@dataclass
class APIKey:
    """API key entity."""
    key_id: str
    key_hash: str
    owner: str
    created_at: float
    expires_at: float
    rate_limit: int = 1000  # requests per hour
    permissions: List[str] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        return time.time() < self.expires_at


class APIGateway:
    """
    AMCIS API Gateway
    =================
    
    Secure API gateway with WAF integration, authentication, and rate limiting.
    """
    
    def __init__(self) -> None:
        self.logger = structlog.get_logger("amcis.api_gateway")
        self.waf = WAFEngine()
        
        self._api_keys: Dict[str, APIKey] = {}
        self._request_counts: Dict[str, List[float]] = {}  # key_id -> timestamps
        self._auth_handlers: List[Callable[[str], Optional[APIKey]]] = []
        
        self.logger.info("api_gateway_initialized")
    
    def register_api_key(self, key_id: str, key_hash: str, owner: str,
                        permissions: Optional[List[str]] = None) -> APIKey:
        """Register new API key."""
        key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            owner=owner,
            created_at=time.time(),
            expires_at=time.time() + (90 * 86400),  # 90 days
            permissions=permissions or ["read"]
        )
        
        self._api_keys[key_id] = key
        self.logger.info("api_key_registered", key_id=key_id, owner=owner)
        return key
    
    def authenticate_request(self, api_key: str) -> Optional[APIKey]:
        """Authenticate API request."""
        # Check built-in keys
        for key in self._api_keys.values():
            if key.key_hash == api_key and key.is_valid():
                return key
        
        # Check custom handlers
        for handler in self._auth_handlers:
            result = handler(api_key)
            if result:
                return result
        
        return None
    
    def check_rate_limit(self, key_id: str, limit: int = 1000) -> bool:
        """Check if request is within rate limit."""
        now = time.time()
        window = 3600  # 1 hour
        
        if key_id not in self._request_counts:
            self._request_counts[key_id] = []
        
        # Clean old entries
        self._request_counts[key_id] = [
            t for t in self._request_counts[key_id]
            if now - t < window
        ]
        
        # Check limit
        if len(self._request_counts[key_id]) >= limit:
            return False
        
        # Record request
        self._request_counts[key_id].append(now)
        return True
    
    def process_request(self, request: HTTPRequest, 
                       api_key: Optional[str] = None) -> Dict[str, Any]:
        """Process API request through security checks."""
        result = {
            "allowed": False,
            "waf_decision": None,
            "auth_status": None,
            "rate_limited": False
        }
        
        # WAF check
        waf_decision = self.waf.inspect_request(request)
        result["waf_decision"] = waf_decision
        
        if not waf_decision.allowed:
            result["reason"] = "waf_blocked"
            self.logger.warning("api_request_blocked_by_waf",
                              source=request.client_ip,
                              rules=[r.rule_id for r in waf_decision.matched_rules])
            return result
        
        # Authentication
        if api_key:
            key = self.authenticate_request(api_key)
            if not key:
                result["reason"] = "invalid_api_key"
                return result
            
            result["auth_status"] = key
            
            # Rate limiting
            if not self.check_rate_limit(key.key_id, key.rate_limit):
                result["rate_limited"] = True
                result["reason"] = "rate_limited"
                return result
        
        result["allowed"] = True
        return result
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key."""
        if key_id in self._api_keys:
            del self._api_keys[key_id]
            self.logger.info("api_key_revoked", key_id=key_id)
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get gateway statistics."""
        return {
            "registered_keys": len(self._api_keys),
            "active_keys": sum(1 for k in self._api_keys.values() if k.is_valid()),
            "waf_rules": self.waf.get_statistics()["total_rules"]
        }
