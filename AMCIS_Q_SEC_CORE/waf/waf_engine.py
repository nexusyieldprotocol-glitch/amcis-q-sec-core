"""
WAF Engine
==========

Web Application Firewall with OWASP Top 10 protection.
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable
from urllib.parse import urlparse, parse_qs

import structlog


class WAFAction(Enum):
    ALLOW = auto()
    BLOCK = auto()
    LOG = auto()
    RATE_LIMIT = auto()
    CHALLENGE = auto()


class AttackType(Enum):
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    LFI = "local_file_inclusion"
    RFI = "remote_file_inclusion"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    XML_EXTERNAL_ENTITY = "xxe"
    NOSQL_INJECTION = "nosql_injection"
    LDAP_INJECTION = "ldap_injection"


@dataclass
class WAFRule:
    """WAF rule definition."""
    rule_id: str
    name: str
    description: str
    attack_type: AttackType
    pattern: str  # Regex pattern
    action: WAFAction
    severity: int = 5  # 1-10
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "attack_type": self.attack_type.value,
            "action": self.action.name,
            "severity": self.severity,
            "enabled": self.enabled
        }


@dataclass
class HTTPRequest:
    """HTTP request representation."""
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, List[str]]
    body: str
    client_ip: str
    user_agent: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent[:50] if self.user_agent else ""
        }


@dataclass
class WAFDecision:
    """WAF inspection decision."""
    allowed: bool
    action: WAFAction
    matched_rules: List[WAFRule]
    attack_types: List[AttackType]
    severity: int
    log_data: Dict[str, Any]


class WAFEngine:
    """
    AMCIS WAF Engine
    ================
    
    OWASP Top 10 protection with customizable rules.
    """
    
    # Default OWASP Top 10 rules
    DEFAULT_RULES = [
        # SQL Injection
        WAFRule(
            rule_id="OWASP-SQL-001",
            name="SQL Injection - Basic",
            description="Detects basic SQL injection attempts",
            attack_type=AttackType.SQL_INJECTION,
            pattern=r"(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(from|into|table|database)\b)|(--|;--|;#|/\*|\*/)",
            action=WAFAction.BLOCK,
            severity=9
        ),
        # XSS
        WAFRule(
            rule_id="OWASP-XSS-001",
            name="Cross-Site Scripting",
            description="Detects XSS attempts",
            attack_type=AttackType.XSS,
            pattern=r"(<script|javascript:|on\w+\s*=|alert\(|document\.cookie|document\.location)",
            action=WAFAction.BLOCK,
            severity=8
        ),
        # Path Traversal
        WAFRule(
            rule_id="OWASP-PT-001",
            name="Path Traversal",
            description="Detects directory traversal attempts",
            attack_type=AttackType.PATH_TRAVERSAL,
            pattern=r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/)",
            action=WAFAction.BLOCK,
            severity=7
        ),
        # Command Injection
        WAFRule(
            rule_id="OWASP-CI-001",
            name="Command Injection",
            description="Detects command injection attempts",
            attack_type=AttackType.COMMAND_INJECTION,
            pattern=r"(;|\||&&|\$\(|`|\b(sh|bash|cmd|powershell|python|perl)\b)",
            action=WAFAction.BLOCK,
            severity=9
        ),
        # Local File Inclusion
        WAFRule(
            rule_id="OWASP-LFI-001",
            name="Local File Inclusion",
            description="Detects LFI attempts",
            attack_type=AttackType.LFI,
            pattern=r"(file://|/etc/passwd|/etc/shadow|/proc/self|\\x00\.)",
            action=WAFAction.BLOCK,
            severity=7
        ),
        # NoSQL Injection
        WAFRule(
            rule_id="OWASP-NOSQL-001",
            name="NoSQL Injection",
            description="Detects NoSQL injection patterns",
            attack_type=AttackType.NOSQL_INJECTION,
            pattern=r"(\$where|\$ne|\$gt|\$lt|\$regex|\$exists)",
            action=WAFAction.BLOCK,
            severity=8
        ),
    ]
    
    def __init__(self) -> None:
        self.logger = structlog.get_logger("amcis.waf")
        self._rules: List[WAFRule] = self.DEFAULT_RULES.copy()
        self._custom_rules: List[WAFRule] = []
        self._blocked_ips: set = set()
        self._rate_limits: Dict[str, List[float]] = {}  # IP -> timestamps
        
        self.logger.info("waf_engine_initialized", rules=len(self._rules))
    
    def inspect_request(self, request: HTTPRequest) -> WAFDecision:
        """Inspect HTTP request for attacks."""
        matched_rules = []
        attack_types = set()
        max_severity = 0
        
        # Check all rules
        for rule in self._rules:
            if not rule.enabled:
                continue
            
            # Check in path
            if self._match_rule(rule, request.path):
                matched_rules.append(rule)
                attack_types.add(rule.attack_type)
                max_severity = max(max_severity, rule.severity)
                continue
            
            # Check in query params
            for param_values in request.query_params.values():
                for value in param_values:
                    if self._match_rule(rule, value):
                        matched_rules.append(rule)
                        attack_types.add(rule.attack_type)
                        max_severity = max(max_severity, rule.severity)
                        break
            
            # Check in body
            if self._match_rule(rule, request.body):
                matched_rules.append(rule)
                attack_types.add(rule.attack_type)
                max_severity = max(max_severity, rule.severity)
            
            # Check in headers
            for header_value in request.headers.values():
                if self._match_rule(rule, header_value):
                    matched_rules.append(rule)
                    attack_types.add(rule.attack_type)
                    max_severity = max(max_severity, rule.severity)
                    break
        
        # Check IP blocklist
        if request.client_ip in self._blocked_ips:
            return WAFDecision(
                allowed=False,
                action=WAFAction.BLOCK,
                matched_rules=[],
                attack_types=[],
                severity=10,
                log_data={"reason": "blocked_ip", "ip": request.client_ip}
            )
        
        # Check rate limiting
        if self._check_rate_limit(request.client_ip):
            return WAFDecision(
                allowed=False,
                action=WAFAction.RATE_LIMIT,
                matched_rules=[],
                attack_types=[],
                severity=5,
                log_data={"reason": "rate_limit", "ip": request.client_ip}
            )
        
        # Determine action
        if matched_rules:
            actions = [r.action for r in matched_rules]
            if WAFAction.BLOCK in actions:
                final_action = WAFAction.BLOCK
                allowed = False
            elif WAFAction.CHALLENGE in actions:
                final_action = WAFAction.CHALLENGE
                allowed = False
            else:
                final_action = WAFAction.LOG
                allowed = True
            
            self.logger.warning("waf_attack_detected",
                              attack_types=[a.value for a in attack_types],
                              client_ip=request.client_ip,
                              path=request.path)
        else:
            final_action = WAFAction.ALLOW
            allowed = True
        
        return WAFDecision(
            allowed=allowed,
            action=final_action,
            matched_rules=matched_rules,
            attack_types=list(attack_types),
            severity=max_severity,
            log_data=request.to_dict()
        )
    
    def _match_rule(self, rule: WAFRule, content: str) -> bool:
        """Check if content matches rule pattern."""
        if content is None:
            return False
        # Handle list values (e.g., some headers may have lists)
        if isinstance(content, list):
            content = ", ".join(str(c) for c in content)
        content = str(content)
        try:
            return bool(re.search(rule.pattern, content, re.IGNORECASE))
        except re.error:
            return False
    
    def _check_rate_limit(self, client_ip: str, max_requests: int = 100,
                         window_seconds: int = 60) -> bool:
        """Check if IP has exceeded rate limit."""
        import time
        now = time.time()
        
        if client_ip not in self._rate_limits:
            self._rate_limits[client_ip] = []
        
        # Clean old entries
        self._rate_limits[client_ip] = [
            t for t in self._rate_limits[client_ip]
            if now - t < window_seconds
        ]
        
        # Add current request
        self._rate_limits[client_ip].append(now)
        
        return len(self._rate_limits[client_ip]) > max_requests
    
    def add_custom_rule(self, rule: WAFRule) -> None:
        """Add custom WAF rule."""
        self._custom_rules.append(rule)
        self._rules.append(rule)
        self.logger.info("waf_rule_added", rule_id=rule.rule_id)
    
    def block_ip(self, ip: str) -> None:
        """Block IP address."""
        self._blocked_ips.add(ip)
        self.logger.warning("ip_blocked", ip=ip)
    
    def unblock_ip(self, ip: str) -> None:
        """Unblock IP address."""
        self._blocked_ips.discard(ip)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get WAF statistics."""
        return {
            "total_rules": len(self._rules),
            "default_rules": len(self.DEFAULT_RULES),
            "custom_rules": len(self._custom_rules),
            "blocked_ips": len(self._blocked_ips)
        }
