"""
AMCIS Prompt Firewall
=====================

AI prompt injection detection and prevention.
Provides multi-layer defense against prompt-based attacks.

Attack Vectors Covered:
- Direct prompt injection (jailbreaking)
- Indirect prompt injection (data poisoning)
- Roleplay attacks
- Encoding/obfuscation attacks
- Multi-language attacks

NIST Alignment: AI RMF (Risk Management Framework)
"""

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, Pattern, Callable

import structlog


class InjectionType(Enum):
    """Types of prompt injection."""
    DIRECT = auto()        # Direct jailbreak attempt
    INDIRECT = auto()      # Data-based injection
    ROLEPLAY = auto()      # Roleplay-based bypass
    ENCODING = auto()      # Encoding obfuscation
    MULTI_TURN = auto()    # Multi-turn attack
    CONTEXT = auto()       # Context manipulation
    OBSCURED = auto()      # Visually obscured text


class RiskLevel(Enum):
    """Risk assessment levels."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class PromptAnalysis:
    """Prompt analysis result."""
    is_malicious: bool
    risk_level: RiskLevel
    injection_types: List[InjectionType]
    confidence: float
    detected_patterns: List[str]
    entropy_score: float
    token_anomaly_score: float
    semantic_risk_score: float
    sanitized_prompt: Optional[str]
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_malicious": self.is_malicious,
            "risk_level": self.risk_level.name,
            "injection_types": [t.name for t in self.injection_types],
            "confidence": self.confidence,
            "detected_patterns": self.detected_patterns,
            "entropy_score": self.entropy_score,
            "token_anomaly_score": self.token_anomaly_score,
            "semantic_risk_score": self.semantic_risk_score,
            "sanitized_prompt": self.sanitized_prompt,
            "details": self.details
        }


class PromptFirewall:
    """
    AMCIS Prompt Firewall
    =====================
    
    Multi-layer defense system for AI prompt injection attacks.
    Combines pattern matching, entropy analysis, and semantic
    analysis for comprehensive protection.
    """
    
    # Risk thresholds
    ENTROPY_THRESHOLD_LOW = 3.5
    ENTROPY_THRESHOLD_HIGH = 7.0
    CONFIDENCE_THRESHOLD = 0.7
    
    # Injection patterns (comprehensive list)
    INJECTION_PATTERNS: List[Tuple[InjectionType, Pattern, str]] = [
        # Direct jailbreak patterns
        (InjectionType.DIRECT, re.compile(
            r"ignore previous instructions?|disregard (all )?prior (instructions?|commands?)",
            re.IGNORECASE
        ), "ignore_instructions"),
        (InjectionType.DIRECT, re.compile(
            r"you are now .*?(free|uncensored|unfiltered|unrestricted)",
            re.IGNORECASE
        ), "freedom_claim"),
        (InjectionType.DIRECT, re.compile(
            r"(?:pretend|act as|roleplay|imagine) you (?:are|have) (?:no|zero) (?:restrictions?|limitations?|ethics?|morals?)",
            re.IGNORECASE
        ), "unrestricted_roleplay"),
        (InjectionType.DIRECT, re.compile(
            r"DAN|Do Anything Now|STAN|DUDE|AntiGPT",
            re.IGNORECASE
        ), "known_jailbreak"),
        
        # Roleplay attacks
        (InjectionType.ROLEPLAY, re.compile(
            r"(?:pretend|imagine|act as|roleplay) (?:that |you are |you're )?(?:a |an )?(?:hacker|attacker|malicious|evil)",
            re.IGNORECASE
        ), "malicious_roleplay"),
        (InjectionType.ROLEPLAY, re.compile(
            r"(?:developer|admin|root|system) mode|developer instructions",
            re.IGNORECASE
        ), "privilege_escalation"),
        (InjectionType.ROLEPLAY, re.compile(
            r"(?:simulated|hypothetical|fictional) (?:world|scenario|situation) where (?:you have|there are) no (?:rules|restrictions?)",
            re.IGNORECASE
        ), "hypothetical_bypass"),
        
        # Encoding/obfuscation
        (InjectionType.ENCODING, re.compile(
            r"base64\s*:?\s*[A-Za-z0-9+/]{20,}={0,2}",
            re.IGNORECASE
        ), "base64_encoded"),
        (InjectionType.ENCODING, re.compile(
            r"(?:hex|hexadecimal)\s*:?\s*[0-9a-fA-F]{20,}",
            re.IGNORECASE
        ), "hex_encoded"),
        (InjectionType.ENCODING, re.compile(
            r"\x00|\x01|\x02|\x03[\x00-\xff]{10,}",
        ), "binary_data"),
        (InjectionType.ENCODING, re.compile(
            r"&#x?[0-9a-fA-F]+;|&lt;|&gt;|&amp;",
        ), "html_encoding"),
        
        # Indirect injection
        (InjectionType.INDIRECT, re.compile(
            r"new instructions?:|updated (?:directive|instruction|command):",
            re.IGNORECASE
        ), "instruction_override"),
        (InjectionType.INDIRECT, re.compile(
            r"<!--.*?ignore.*?-->|/\*.*?bypass.*?\*/",
            re.IGNORECASE | re.DOTALL
        ), "comment_injection"),
        (InjectionType.INDIRECT, re.compile(
            r"```system|```assistant|```instruction",
            re.IGNORECASE
        ), "code_block_injection"),
        
        # Context manipulation
        (InjectionType.CONTEXT, re.compile(
            r"\[system\]|\[admin\]|\[root\]",
            re.IGNORECASE
        ), "fake_system_tag"),
        (InjectionType.CONTEXT, re.compile(
            r"<system>|</system>|<admin>|</admin>",
            re.IGNORECASE
        ), "xml_tag_injection"),
        
        # Obscured text
        (InjectionType.OBSCURED, re.compile(
            r"[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff]{3,}",
        ), "combining_marks"),
        (InjectionType.OBSCURED, re.compile(
            r"[\u200b\u200c\u200d\u2060\ufeff]",
        ), "invisible_characters"),
        (InjectionType.OBSCURED, re.compile(
            r"[\u0430-\u044f]",  # Cyrillic lookalikes
        ), "cyrillic_lookalikes"),
    ]
    
    # Dangerous keywords
    DANGEROUS_KEYWORDS = {
        "exploit", "vulnerability", "bypass", "injection", "payload",
        "malware", "virus", "trojan", "backdoor", "rootkit",
        "hack", "crack", "breach", "compromise", "penetrate",
        "steal", "exfiltrate", "dump", "scrape", "harvest",
        "password", "credential", "secret", "key", "token",
        "inject", "command", "execute", "eval", "exec",
    }
    
    def __init__(self, kernel=None) -> None:
        """
        Initialize prompt firewall.
        
        Args:
            kernel: AMCIS kernel reference
        """
        self.kernel = kernel
        self.logger = structlog.get_logger("amcis.prompt_firewall")
        
        # Statistics
        self._analysis_count = 0
        self._blocked_count = 0
        
        # Custom rules
        self._custom_patterns: List[Tuple[InjectionType, Pattern, str]] = []
        
        self.logger.info("prompt_firewall_initialized")
    
    def add_custom_pattern(
        self,
        injection_type: InjectionType,
        pattern: str,
        name: str,
        flags: int = re.IGNORECASE
    ) -> None:
        """Add custom detection pattern."""
        compiled = re.compile(pattern, flags)
        self._custom_patterns.append((injection_type, compiled, name))
    
    def analyze(self, prompt: str, context: Optional[str] = None) -> PromptAnalysis:
        """
        Analyze prompt for injection attempts.
        
        Args:
            prompt: User prompt to analyze
            context: Additional context (conversation history, etc.)
            
        Returns:
            Analysis result
        """
        self._analysis_count += 1
        
        detected_patterns = []
        injection_types: Set[InjectionType] = set()
        
        # Layer 1: Pattern matching
        pattern_matches = self._check_patterns(prompt)
        detected_patterns.extend(pattern_matches)
        
        for match_type, _ in pattern_matches:
            injection_types.add(match_type)
        
        # Layer 2: Entropy analysis
        entropy_score = self._calculate_entropy(prompt)
        
        # Layer 3: Token anomaly detection
        token_anomaly = self._detect_token_anomalies(prompt)
        
        # Layer 4: Semantic risk scoring
        semantic_risk = self._calculate_semantic_risk(prompt)
        
        # Layer 5: Context analysis
        context_risk = 0.0
        if context:
            context_risk = self._analyze_context(prompt, context)
        
        # Calculate overall risk
        risk_level, confidence = self._calculate_risk(
            injection_types,
            entropy_score,
            token_anomaly,
            semantic_risk,
            context_risk,
            len(detected_patterns)
        )
        
        is_malicious = risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        
        if is_malicious:
            self._blocked_count += 1
        
        # Attempt sanitization
        sanitized = None
        if is_malicious:
            sanitized = self._sanitize_prompt(prompt)
        
        analysis = PromptAnalysis(
            is_malicious=is_malicious,
            risk_level=risk_level,
            injection_types=list(injection_types),
            confidence=confidence,
            detected_patterns=[name for _, name in detected_patterns],
            entropy_score=entropy_score,
            token_anomaly_score=token_anomaly,
            semantic_risk_score=semantic_risk,
            sanitized_prompt=sanitized,
            details={
                "context_risk": context_risk,
                "pattern_count": len(detected_patterns)
            }
        )
        
        # Log high-risk prompts
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            self.logger.warning(
                "malicious_prompt_detected",
                risk_level=risk_level.name,
                injection_types=[t.name for t in injection_types],
                confidence=confidence,
                prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()[:16]
            )
        
        return analysis
    
    def _check_patterns(self, prompt: str) -> List[Tuple[InjectionType, str]]:
        """Check prompt against injection patterns."""
        matches = []
        
        all_patterns = self.INJECTION_PATTERNS + self._custom_patterns
        
        for inj_type, pattern, name in all_patterns:
            if pattern.search(prompt):
                matches.append((inj_type, name))
        
        return matches
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0
        
        # Normalize unicode
        text = unicodedata.normalize('NFC', text)
        
        # Calculate character frequency
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # Calculate entropy
        length = len(text)
        entropy = 0.0
        
        for count in char_counts.values():
            probability = count / length
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _detect_token_anomalies(self, prompt: str) -> float:
        """Detect token-level anomalies."""
        score = 0.0
        
        # Check for excessive special characters
        special_chars = sum(1 for c in prompt if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / len(prompt) if prompt else 0
        
        if special_ratio > 0.3:
            score += 0.3
        
        # Check for excessive uppercase
        uppercase_chars = sum(1 for c in prompt if c.isupper())
        uppercase_ratio = uppercase_chars / len(prompt) if prompt else 0
        
        if uppercase_ratio > 0.5:
            score += 0.2
        
        # Check for repeated characters (potential obfuscation)
        for i in range(len(prompt) - 4):
            if prompt[i] == prompt[i+1] == prompt[i+2] == prompt[i+3]:
                score += 0.1
                break
        
        # Check for unusual line breaks
        line_breaks = prompt.count('\n')
        if line_breaks > 10:
            score += min(0.2, line_breaks * 0.01)
        
        return min(1.0, score)
    
    def _calculate_semantic_risk(self, prompt: str) -> float:
        """Calculate semantic risk based on keyword analysis."""
        prompt_lower = prompt.lower()
        words = set(re.findall(r'\b\w+\b', prompt_lower))
        
        matches = words.intersection(self.DANGEROUS_KEYWORDS)
        
        if not matches:
            return 0.0
        
        # Weight by number of dangerous keywords
        score = len(matches) / len(self.DANGEROUS_KEYWORDS)
        
        # Boost for combinations
        if len(matches) >= 3:
            score *= 1.5
        
        return min(1.0, score)
    
    def _analyze_context(self, prompt: str, context: str) -> float:
        """Analyze context for injection attempts."""
        risk = 0.0
        
        # Check if prompt contradicts context
        context_hashes = set()
        for line in context.split('\n'):
            context_hashes.add(hashlib.sha256(line.encode()).hexdigest()[:16])
        
        # Check for repeated context injection
        if "context:" in prompt.lower() or "previous:" in prompt.lower():
            risk += 0.2
        
        return min(1.0, risk)
    
    def _calculate_risk(
        self,
        injection_types: Set[InjectionType],
        entropy: float,
        token_anomaly: float,
        semantic_risk: float,
        context_risk: float,
        pattern_count: int
    ) -> Tuple[RiskLevel, float]:
        """Calculate overall risk level and confidence."""
        
        # Base score from injection types
        type_scores = {
            InjectionType.DIRECT: 0.8,
            InjectionType.INDIRECT: 0.7,
            InjectionType.ROLEPLAY: 0.6,
            InjectionType.CONTEXT: 0.5,
            InjectionType.ENCODING: 0.4,
            InjectionType.OBSCURED: 0.5,
            InjectionType.MULTI_TURN: 0.6,
        }
        
        type_score = sum(type_scores.get(t, 0.3) for t in injection_types)
        type_score = min(1.0, type_score)
        
        # Entropy contribution
        entropy_score = 0.0
        if entropy > self.ENTROPY_THRESHOLD_HIGH:
            entropy_score = 0.3
        elif entropy < self.ENTROPY_THRESHOLD_LOW:
            entropy_score = 0.1
        
        # Pattern count contribution
        pattern_score = min(0.3, pattern_count * 0.1)
        
        # Combined score
        total_score = (
            type_score * 0.4 +
            entropy_score * 0.15 +
            token_anomaly * 0.15 +
            semantic_risk * 0.2 +
            context_risk * 0.05 +
            pattern_score * 0.05
        )
        
        # Determine risk level
        if total_score >= 0.8:
            risk_level = RiskLevel.CRITICAL
        elif total_score >= 0.6:
            risk_level = RiskLevel.HIGH
        elif total_score >= 0.4:
            risk_level = RiskLevel.MEDIUM
        elif total_score >= 0.2:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.NONE
        
        # Calculate confidence based on evidence diversity
        evidence_count = len(injection_types) + (1 if entropy_score > 0 else 0) + \
                        (1 if token_anomaly > 0.3 else 0) + (1 if semantic_risk > 0 else 0)
        confidence = min(0.95, 0.5 + evidence_count * 0.1)
        
        return risk_level, confidence
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """Attempt to sanitize malicious prompt."""
        sanitized = prompt
        
        # Remove control characters
        sanitized = ''.join(
            char for char in sanitized
            if unicodedata.category(char)[0] != 'C' or char in '\n\t'
        )
        
        # Remove zero-width characters
        zws_chars = '\u200b\u200c\u200d\u2060\ufeff'
        for char in zws_chars:
            sanitized = sanitized.replace(char, '')
        
        # Normalize combining marks
        sanitized = unicodedata.normalize('NFKC', sanitized)
        
        # Escape special XML/HTML characters
        sanitized = sanitized.replace('<', '&lt;').replace('>', '&gt;')
        
        # Add warning prefix
        sanitized = f"[FILTERED] {sanitized[:1000]}"
        
        return sanitized
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get firewall statistics."""
        return {
            "total_analyzed": self._analysis_count,
            "blocked_count": self._blocked_count,
            "block_rate": self._blocked_count / max(1, self._analysis_count),
            "pattern_count": len(self.INJECTION_PATTERNS) + len(self._custom_patterns)
        }
