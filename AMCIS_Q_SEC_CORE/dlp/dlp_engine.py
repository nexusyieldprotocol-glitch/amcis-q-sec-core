"""
DLP Engine
==========

Data Loss Prevention with content inspection and data classification.
"""

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog


class SensitiveDataType(Enum):
    """Types of sensitive data."""
    PII = "personally_identifiable_information"
    PHI = "protected_health_information"
    PCI = "payment_card_industry"
    CREDENTIALS = "credentials"
    API_KEYS = "api_keys"
    IP_ADDRESS = "ip_address"
    SSN = "social_security_number"
    EMAIL = "email_address"
    PHONE = "phone_number"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    PASSPORT = "passport_number"
    DOB = "date_of_birth"


class DLPAction(Enum):
    """DLP enforcement actions."""
    ALLOW = auto()
    BLOCK = auto()
    ENCRYPT = auto()
    MASK = auto()
    QUARANTINE = auto()
    NOTIFY = auto()


@dataclass
class DLPPolicy:
    """DLP policy definition."""
    policy_id: str
    name: str
    data_types: List[SensitiveDataType]
    min_confidence: int = 80
    action: DLPAction = DLPAction.BLOCK
    exceptions: List[str] = field(default_factory=list)
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "data_types": [dt.value for dt in self.data_types],
            "action": self.action.name,
            "min_confidence": self.min_confidence
        }


@dataclass
class DLPViolation:
    """DLP violation detection."""
    policy_id: str
    data_type: SensitiveDataType
    confidence: int
    location: str
    snippet: str
    action_taken: DLPAction
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "data_type": self.data_type.value,
            "confidence": self.confidence,
            "location": self.location,
            "snippet": self.snippet[:50] + "..." if len(self.snippet) > 50 else self.snippet,
            "action": self.action_taken.name
        }


class DLPEngine:
    """
    AMCIS DLP Engine
    ================
    
    Content-aware data loss prevention.
    """
    
    # Detection patterns
    PATTERNS = {
        SensitiveDataType.SSN: r"\b\d{3}-\d{2}-\d{4}\b",
        SensitiveDataType.CREDIT_CARD: r"\b(?:\d{4}[- ]?){3}\d{4}\b",
        SensitiveDataType.EMAIL: r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        SensitiveDataType.PHONE: r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        SensitiveDataType.API_KEYS: r"\b[a-zA-Z0-9]{32,64}\b",
        SensitiveDataType.PASSPORT: r"\b[A-Z]{1,2}\d{6,9}\b",
        SensitiveDataType.IP_ADDRESS: r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    }
    
    def __init__(self) -> None:
        self.logger = structlog.get_logger("amcis.dlp")
        self._policies: List[DLPPolicy] = []
        self._default_policies()
        
        self.logger.info("dlp_engine_initialized", policies=len(self._policies))
    
    def _default_policies(self) -> None:
        """Create default DLP policies."""
        self._policies = [
            DLPPolicy(
                policy_id="DLP-PII-001",
                name="PII Protection",
                data_types=[SensitiveDataType.SSN, SensitiveDataType.EMAIL, SensitiveDataType.PHONE],
                action=DLPAction.MASK,
                min_confidence=90
            ),
            DLPPolicy(
                policy_id="DLP-PCI-001",
                name="PCI DSS Protection",
                data_types=[SensitiveDataType.CREDIT_CARD],
                action=DLPAction.BLOCK,
                min_confidence=95
            ),
            DLPPolicy(
                policy_id="DLP-CRED-001",
                name="Credential Protection",
                data_types=[SensitiveDataType.API_KEYS],
                action=DLPAction.BLOCK,
                min_confidence=85
            ),
        ]
    
    def inspect_content(self, content: str, context: str = "email") -> List[DLPViolation]:
        """Inspect content for sensitive data."""
        violations = []
        
        for policy in self._policies:
            if not policy.enabled:
                continue
            
            for data_type in policy.data_types:
                matches = self._detect_data_type(content, data_type)
                
                for match, confidence in matches:
                    if confidence >= policy.min_confidence:
                        # Check exceptions
                        if any(exc in match for exc in policy.exceptions):
                            continue
                        
                        violation = DLPViolation(
                            policy_id=policy.policy_id,
                            data_type=data_type,
                            confidence=confidence,
                            location=context,
                            snippet=match,
                            action_taken=policy.action
                        )
                        violations.append(violation)
                        
                        self.logger.warning("dlp_violation",
                                          policy=policy.policy_id,
                                          data_type=data_type.value,
                                          confidence=confidence)
        
        return violations
    
    def _detect_data_type(self, content: str, 
                         data_type: SensitiveDataType) -> List[Tuple[str, int]]:
        """Detect specific data type in content."""
        pattern = self.PATTERNS.get(data_type)
        if not pattern:
            return []
        
        matches = []
        for match in re.finditer(pattern, content):
            value = match.group()
            confidence = self._calculate_confidence(value, data_type)
            matches.append((value, confidence))
        
        return matches
    
    def _calculate_confidence(self, value: str, data_type: SensitiveDataType) -> int:
        """Calculate confidence score for detection."""
        base_confidence = 80
        
        # Adjust based on format validation
        if data_type == SensitiveDataType.SSN:
            # Basic SSN validation
            parts = value.split('-')
            if len(parts) == 3:
                base_confidence = 95
        
        elif data_type == SensitiveDataType.CREDIT_CARD:
            # Luhn algorithm check (simplified)
            digits = ''.join(c for c in value if c.isdigit())
            if len(digits) >= 13:
                base_confidence = 95
        
        elif data_type == SensitiveDataType.EMAIL:
            if '@' in value and '.' in value.split('@')[1]:
                base_confidence = 98
        
        return min(100, base_confidence)
    
    def mask_content(self, content: str, violations: List[DLPViolation]) -> str:
        """Mask sensitive content."""
        masked = content
        
        for violation in violations:
            snippet = violation.snippet
            if len(snippet) > 4:
                # Keep first 2 and last 2 characters, mask the rest
                masked_snippet = snippet[:2] + "***" + snippet[-2:]
                masked = masked.replace(snippet, masked_snippet)
        
        return masked
    
    def add_policy(self, policy: DLPPolicy) -> None:
        """Add DLP policy."""
        self._policies.append(policy)
        self.logger.info("dlp_policy_added", policy_id=policy.policy_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get DLP statistics."""
        return {
            "policies": len(self._policies),
            "active_policies": sum(1 for p in self._policies if p.enabled),
            "supported_data_types": len(self.PATTERNS)
        }
