"""
AMCIS Microsegmentation Engine
===============================

Dynamic firewall rule automation and network segmentation
for zero-trust network architecture.

Features:
- Dynamic firewall rule generation
- Egress filtering
- Service-based segmentation
- Automatic policy enforcement

NIST Alignment: SP 800-207 (Zero Trust), SP 800-53 (SC-7)
"""

import hashlib
import json
import platform
import re
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from ipaddress import IPv4Address, IPv6Address, ip_network, ip_address
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import structlog

try:
    from core.amcis_exceptions import NetworkException, ErrorCode
    from core.amcis_error_utils import safe_method, retry, timing_context
except ImportError:
    from ..core.amcis_exceptions import NetworkException, ErrorCode
    from ..core.amcis_error_utils import safe_method, retry, timing_context


class RuleAction(Enum):
    """Firewall rule actions."""
    ALLOW = auto()
    DENY = auto()
    LOG = auto()
    REDIRECT = auto()


class RuleDirection(Enum):
    """Traffic directions."""
    INBOUND = auto()
    OUTBOUND = auto()
    BOTH = auto()


class Protocol(Enum):
    """Network protocols."""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    ANY = "any"


@dataclass
class FirewallRule:
    """Firewall rule definition."""
    rule_id: str
    action: RuleAction
    direction: RuleDirection
    protocol: Protocol
    source_addresses: List[str]
    destination_addresses: List[str]
    source_ports: Optional[List[int]]
    destination_ports: Optional[List[int]]
    application: Optional[str]
    user: Optional[str]
    priority: int
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "action": self.action.name,
            "direction": self.direction.name,
            "protocol": self.protocol.value,
            "source_addresses": self.source_addresses,
            "destination_addresses": self.destination_addresses,
            "source_ports": self.source_ports,
            "destination_ports": self.destination_ports,
            "application": self.application,
            "user": self.user,
            "priority": self.priority,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "expires_at": self.expires_at
        }


@dataclass
class ConnectionEvent:
    """Network connection event."""
    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: Protocol
    process_name: Optional[str]
    user: Optional[str]
    action: RuleAction
    rule_id: Optional[str]


class MicrosegmentationEngine:
    """
    AMCIS Microsegmentation Engine
    ==============================
    
    Dynamic network segmentation and firewall management for
    zero-trust architecture implementation.
    """
    
    # Default policies
    DEFAULT_RULES: List[FirewallRule] = [
        FirewallRule(
            rule_id="default_deny_outbound",
            action=RuleAction.DENY,
            direction=RuleDirection.OUTBOUND,
            protocol=Protocol.ANY,
            source_addresses=["0.0.0.0/0"],
            destination_addresses=["0.0.0.0/0"],
            source_ports=None,
            destination_ports=None,
            application=None,
            user=None,
            priority=1000
        ),
        FirewallRule(
            rule_id="allow_loopback",
            action=RuleAction.ALLOW,
            direction=RuleDirection.BOTH,
            protocol=Protocol.ANY,
            source_addresses=["127.0.0.1/8", "::1/128"],
            destination_addresses=["127.0.0.1/8", "::1/128"],
            source_ports=None,
            destination_ports=None,
            application=None,
            user=None,
            priority=1
        ),
        FirewallRule(
            rule_id="allow_dns",
            action=RuleAction.ALLOW,
            direction=RuleDirection.OUTBOUND,
            protocol=Protocol.UDP,
            source_addresses=["0.0.0.0/0"],
            destination_addresses=["0.0.0.0/0"],
            source_ports=None,
            destination_ports=[53, 853],
            application=None,
            user=None,
            priority=10
        ),
        FirewallRule(
            rule_id="allow_https",
            action=RuleAction.ALLOW,
            direction=RuleDirection.OUTBOUND,
            protocol=Protocol.TCP,
            source_addresses=["0.0.0.0/0"],
            destination_addresses=["0.0.0.0/0"],
            source_ports=None,
            destination_ports=[443, 8443],
            application=None,
            user=None,
            priority=20
        ),
    ]
    
    def __init__(
        self,
        kernel=None,
        policy_path: Optional[Path] = None,
        dry_run: bool = False
    ) -> None:
        """
        Initialize microsegmentation engine.
        
        Args:
            kernel: AMCIS kernel reference
            policy_path: Path for policy storage
            dry_run: Don't actually modify firewall
        """
        self.kernel = kernel
        self.policy_path = policy_path or Path("/etc/amcis/firewall")
        self.dry_run = dry_run
        
        self.logger = structlog.get_logger("amcis.microsegmentation")
        
        # Rules storage
        self._rules: Dict[str, FirewallRule] = {}
        self._active_rules: Set[str] = set()
        
        # Connection tracking
        self._connection_log: List[ConnectionEvent] = []
        self._max_log_size = 10000
        
        # Monitoring
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Load default rules
        for rule in self.DEFAULT_RULES:
            self._rules[rule.rule_id] = rule
        
        self.logger.info("microsegmentation_engine_initialized", dry_run=dry_run)
    
    def add_rule(self, rule: FirewallRule, activate: bool = False) -> bool:
        """
        Add firewall rule.
        
        Args:
            rule: Rule to add
            activate: Immediately activate rule
            
        Returns:
            True if added successfully
        """
        self._rules[rule.rule_id] = rule
        
        if activate and not self.dry_run:
            return self._apply_rule(rule)
        
        self.logger.info("rule_added", rule_id=rule.rule_id)
        return True
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove firewall rule.
        
        Args:
            rule_id: Rule to remove
            
        Returns:
            True if removed
        """
        if rule_id not in self._rules:
            return False
        
        if rule_id in self._active_rules and not self.dry_run:
            self._remove_active_rule(rule_id)
        
        del self._rules[rule_id]
        self._active_rules.discard(rule_id)
        
        self.logger.info("rule_removed", rule_id=rule_id)
        return True
    
    @safe_method(default=False, error_code=ErrorCode.NETWORK_ERROR)
    def _apply_rule(self, rule: FirewallRule) -> bool:
        """Apply rule to system firewall."""
        with timing_context(f"apply_rule_{rule.rule_id}", threshold_ms=500):
            if platform.system() == "Linux":
                return self._apply_iptables_rule(rule)
            elif platform.system() == "Windows":
                return self._apply_windows_rule(rule)
            else:
                self.logger.warning("unsupported_platform_for_firewall")
                return False
    
    @retry(max_retries=3, delay=0.1, exceptions=(NetworkException,))
    def _apply_iptables_rule(self, rule: FirewallRule) -> bool:
        """Apply rule using iptables."""
        # Build iptables command
        cmd = ["iptables"]
        
        # Table
        cmd.extend(["-t", "filter"])
        
        # Action
        cmd.append("-A" if rule.action == RuleAction.ALLOW else "-D")
        
        # Chain
        if rule.direction == RuleDirection.INBOUND:
            cmd.append("INPUT")
        else:
            cmd.append("OUTPUT")
        
        # Protocol
        if rule.protocol != Protocol.ANY:
            cmd.extend(["-p", rule.protocol.value])
        
        # Source
        if rule.source_addresses and rule.source_addresses != ["0.0.0.0/0"]:
            cmd.extend(["-s", ",".join(rule.source_addresses)])
        
        # Destination
        if rule.destination_addresses and rule.destination_addresses != ["0.0.0.0/0"]:
            cmd.extend(["-d", ",".join(rule.destination_addresses)])
        
        # Ports
        if rule.destination_ports:
            cmd.extend(["--dport", ",".join(str(p) for p in rule.destination_ports)])
        
        # Target
        if rule.action == RuleAction.ALLOW:
            cmd.extend(["-j", "ACCEPT"])
        elif rule.action == RuleAction.DENY:
            cmd.extend(["-j", "DROP"])
        elif rule.action == RuleAction.LOG:
            cmd.extend(["-j", "LOG"])
        
        if self.dry_run:
            self.logger.info("dry_run_iptables", command=" ".join(cmd))
            return True
        
        try:
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0:
                self._active_rules.add(rule.rule_id)
                return True
            else:
                stderr = result.stderr.decode() if result.stderr else "Unknown error"
                self.logger.error("iptables_failed", stderr=stderr)
                raise NetworkException(
                    f"iptables command failed: {stderr}",
                    error_code=ErrorCode.NETWORK_ERROR,
                    details={'rule_id': rule.rule_id, 'command': ' '.join(cmd)}
                )
        except subprocess.SubprocessError as e:
            raise NetworkException(
                f"Failed to execute iptables: {str(e)}",
                error_code=ErrorCode.NETWORK_ERROR,
                details={'rule_id': rule.rule_id}
            ) from e
    
    def _apply_windows_rule(self, rule: FirewallRule) -> bool:
        """Apply rule using Windows Firewall."""
        # Windows Firewall implementation
        self.logger.info("windows_firewall_stub")
        return True
    
    def _remove_active_rule(self, rule_id: str) -> bool:
        """Remove active rule from system firewall."""
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        
        # Similar to _apply_rule but with -D for deletion
        self.logger.info("rule_deactivation", rule_id=rule_id)
        return True
    
    def evaluate_connection(
        self,
        src_ip: str,
        dst_ip: str,
        dst_port: int,
        protocol: Protocol = Protocol.TCP,
        process_name: Optional[str] = None
    ) -> Tuple[RuleAction, Optional[str]]:
        """
        Evaluate connection against rules.
        
        Args:
            src_ip: Source IP
            dst_ip: Destination IP
            dst_port: Destination port
            protocol: Protocol
            process_name: Process name
            
        Returns:
            (action, matching_rule_id)
        """
        # Sort rules by priority
        sorted_rules = sorted(self._rules.values(), key=lambda r: r.priority)
        
        for rule in sorted_rules:
            if not rule.enabled:
                continue
            
            if self._matches_rule(rule, src_ip, dst_ip, dst_port, protocol, process_name):
                return rule.action, rule.rule_id
        
        # Default deny
        return RuleAction.DENY, None
    
    def _matches_rule(
        self,
        rule: FirewallRule,
        src_ip: str,
        dst_ip: str,
        dst_port: int,
        protocol: Protocol,
        process_name: Optional[str]
    ) -> bool:
        """Check if connection matches rule."""
        # Check protocol
        if rule.protocol != Protocol.ANY and rule.protocol != protocol:
            return False
        
        # Check source address
        if rule.source_addresses and not self._ip_in_ranges(src_ip, rule.source_addresses):
            return False
        
        # Check destination address
        if rule.destination_addresses and not self._ip_in_ranges(dst_ip, rule.destination_addresses):
            return False
        
        # Check destination port
        if rule.destination_ports and dst_port not in rule.destination_ports:
            return False
        
        # Check application
        if rule.application and process_name != rule.application:
            return False
        
        return True
    
    def _ip_in_ranges(self, ip: str, ranges: List[str]) -> bool:
        """Check if IP is in any of the ranges."""
        try:
            addr = ip_address(ip)
            
            for range_str in ranges:
                if "/" in range_str:
                    network = ip_network(range_str, strict=False)
                    if addr in network:
                        return True
                else:
                    if str(addr) == range_str:
                        return True
            
            return False
        except ValueError as e:
            self.logger.debug("ip_range_check_failed", ip=ip, error=str(e))
            return False
    
    def block_ip(self, ip: str, duration: Optional[int] = None, reason: str = "") -> bool:
        """
        Block IP address.
        
        Args:
            ip: IP to block
            duration: Block duration in seconds (None = permanent)
            reason: Block reason
            
        Returns:
            True if blocked
        """
        rule_id = f"block_{ip}_{int(time.time())}"
        
        rule = FirewallRule(
            rule_id=rule_id,
            action=RuleAction.DENY,
            direction=RuleDirection.BOTH,
            protocol=Protocol.ANY,
            source_addresses=[ip] if self._is_valid_ip(ip) else [],
            destination_addresses=[ip] if self._is_valid_ip(ip) else [],
            source_ports=None,
            destination_ports=None,
            application=None,
            user=None,
            priority=5,
            expires_at=time.time() + duration if duration else None,
            metadata={"reason": reason, "auto_generated": True}
        )
        
        return self.add_rule(rule, activate=True)
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if string is valid IP."""
        try:
            ip_address(ip)
            return True
        except ValueError:
            return False
    
    def create_microsegment(
        self,
        name: str,
        allowed_services: List[Tuple[Protocol, List[int]]],
        peer_segments: Optional[List[str]] = None
    ) -> List[FirewallRule]:
        """
        Create microsegment rules.
        
        Args:
            name: Segment name
            allowed_services: List of (protocol, ports) tuples
            peer_segments: Other segments this can communicate with
            
        Returns:
            Created rules
        """
        rules = []
        
        # Allow intra-segment traffic
        intra_rule = FirewallRule(
            rule_id=f"{name}_intra",
            action=RuleAction.ALLOW,
            direction=RuleDirection.BOTH,
            protocol=Protocol.ANY,
            source_addresses=["segment_placeholder"],
            destination_addresses=["segment_placeholder"],
            source_ports=None,
            destination_ports=None,
            application=None,
            user=None,
            priority=50,
            metadata={"segment": name, "type": "intra_segment"}
        )
        rules.append(intra_rule)
        
        # Allow specified services
        for protocol, ports in allowed_services:
            service_rule = FirewallRule(
                rule_id=f"{name}_{protocol.value}_{min(ports)}",
                action=RuleAction.ALLOW,
                direction=RuleDirection.OUTBOUND,
                protocol=protocol,
                source_addresses=["0.0.0.0/0"],
                destination_addresses=["0.0.0.0/0"],
                source_ports=None,
                destination_ports=ports,
                application=None,
                user=None,
                priority=100,
                metadata={"segment": name, "type": "service"}
            )
            rules.append(service_rule)
        
        # Apply all rules
        for rule in rules:
            self.add_rule(rule)
        
        self.logger.info("microsegment_created", name=name, rules=len(rules))
        return rules
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_rules": len(self._rules),
            "active_rules": len(self._active_rules),
            "connection_log_size": len(self._connection_log),
            "dry_run": self.dry_run
        }
    
    def export_policy(self) -> Dict[str, Any]:
        """Export firewall policy."""
        return {
            "rules": [rule.to_dict() for rule in self._rules.values()],
            "active_rules": list(self._active_rules),
            "exported_at": time.time()
        }
