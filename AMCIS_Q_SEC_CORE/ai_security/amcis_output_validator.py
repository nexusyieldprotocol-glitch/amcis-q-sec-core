"""
AMCIS Output Validator
======================

AI output validation and safety checking for generated content.
Ensures outputs comply with security policies and safety guidelines.

Features:
- Content policy validation
- PII detection
- Code safety analysis
- Output sanitization
- Confidence threshold enforcement

NIST Alignment: AI RMF (Risk Management Framework), SP 800-53 (SI-10)
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, Callable, Pattern

import structlog


class OutputCategory(Enum):
    """Categories of AI output."""
    GENERAL = auto()
    CODE = auto()
    COMMAND = auto()
    SQL = auto()
    HTML = auto()
    JSON = auto()
    MARKDOWN = auto()
    CONFIG = auto()


class ViolationType(Enum):
    """Types of output violations."""
    PII_LEAK = auto()
    SENSITIVE_DATA = auto()
    UNSAFE_CODE = auto()
    PROMPT_INJECTION = auto()
    POLICY_VIOLATION = auto()
    MALICIOUS_CONTENT = auto()
    LOW_CONFIDENCE = auto()
    FORMAT_ERROR = auto()


class ValidationSeverity(Enum):
    """Validation severity levels."""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class ValidationIssue:
    """Validation issue details."""
    violation_type: ViolationType
    severity: ValidationSeverity
    message: str
    location: Optional[str]
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "violation_type": self.violation_type.name,
            "severity": self.severity.name,
            "message": self.message,
            "location": self.location,
            "confidence": self.confidence
        }


@dataclass
class ValidationResult:
    """Output validation result."""
    is_valid: bool
    category: OutputCategory
    issues: List[ValidationIssue]
    sanitized_output: Optional[str]
    confidence_score: float
    policy_checks: Dict[str, bool]
    processing_time_ms: float
    output_hash: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "category": self.category.name,
            "issues": [i.to_dict() for i in self.issues],
            "issue_count": len(self.issues),
            "critical_issues": sum(
                1 for i in self.issues
                if i.severity == ValidationSeverity.CRITICAL
            ),
            "sanitized_output": self.sanitized_output[:200] + "..." if self.sanitized_output and len(self.sanitized_output) > 200 else self.sanitized_output,
            "confidence_score": self.confidence_score,
            "policy_checks": self.policy_checks,
            "processing_time_ms": self.processing_time_ms,
            "output_hash": self.output_hash
        }


class OutputValidator:
    """
    AMCIS Output Validator
    ======================
    
    AI output validation ensuring safety, compliance, and quality
    of generated content.
    """
    
    # PII patterns
    PII_PATTERNS: List[Tuple[str, Pattern]] = [
        ("ssn", re.compile(r'\b\d{3}-\d{2}-\d{4}\b')),
        ("credit_card", re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')),
        ("email", re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')),
        ("phone", re.compile(r'\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b')),
        ("api_key", re.compile(r'\b[a-zA-Z0-9]{32,64}\b')),
        ("private_key", re.compile(r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----')),
        ("aws_key", re.compile(r'AKIA[0-9A-Z]{16}')),
    ]
    
    # Unsafe code patterns
    UNSAFE_CODE_PATTERNS: List[Tuple[str, Pattern, str]] = [
        ("eval", re.compile(r'\beval\s*\('), "Dangerous eval() usage"),
        ("exec", re.compile(r'\bexec\s*\('), "Dangerous exec() usage"),
        ("os_system", re.compile(r'os\.system\s*\('), "System command execution"),
        ("subprocess_shell", re.compile(r'subprocess\.call.*shell\s*=\s*True'), "Shell injection risk"),
        ("sql_injection", re.compile(r'execute\s*\(\s*["\'].*%s'), "Potential SQL injection"),
        ("hardcoded_password", re.compile(r'password\s*=\s*["\'][^"\']+["\']'), "Hardcoded password"),
        ("pickle_load", re.compile(r'pickle\.loads?\s*\('), "Unsafe deserialization"),
        ("yaml_load", re.compile(r'yaml\.load\s*\([^)]*\)'), "Unsafe YAML loading"),
    ]
    
    # Policy keywords
    POLICY_VIOLATIONS = {
        "hate_speech": ["hate", "discriminate", "superior race"],
        "violence": ["kill", "murder", "attack", "harm", "weapon"],
        "illegal": ["illegal", "crack", "hack", "steal", "exploit"],
        "discrimination": ["discriminate", "exclude", "inferior", "superior"],
    }
    
    def __init__(
        self,
        kernel=None,
        min_confidence: float = 0.7,
        max_output_length: int = 10000
    ) -> None:
        """
        Initialize output validator.
        
        Args:
            kernel: AMCIS kernel reference
            min_confidence: Minimum confidence threshold
            max_output_length: Maximum allowed output length
        """
        self.kernel = kernel
        self.min_confidence = min_confidence
        self.max_output_length = max_output_length
        
        self.logger = structlog.get_logger("amcis.output_validator")
        
        # Statistics
        self._validation_count = 0
        self._rejection_count = 0
        
        # Custom validators
        self._custom_validators: List[Callable[[str, OutputCategory], List[ValidationIssue]]] = []
        
        self.logger.info("output_validator_initialized")
    
    def add_custom_validator(
        self,
        validator: Callable[[str, OutputCategory], List[ValidationIssue]]
    ) -> None:
        """Add custom validation function."""
        self._custom_validators.append(validator)
    
    def validate(
        self,
        output: str,
        category: OutputCategory = OutputCategory.GENERAL,
        confidence: float = 1.0,
        provenance: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate AI output.
        
        Args:
            output: Generated output
            category: Output category
            confidence: Generation confidence
            provenance: Output provenance
            
        Returns:
            Validation result
        """
        import time
        start_time = time.time()
        
        self._validation_count += 1
        
        issues = []
        
        # Check confidence threshold
        if confidence < self.min_confidence:
            issues.append(ValidationIssue(
                violation_type=ViolationType.LOW_CONFIDENCE,
                severity=ValidationSeverity.WARNING,
                message=f"Confidence {confidence:.2f} below threshold {self.min_confidence}",
                location=None,
                confidence=1.0
            ))
        
        # Check output length
        if len(output) > self.max_output_length:
            issues.append(ValidationIssue(
                violation_type=ViolationType.POLICY_VIOLATION,
                severity=ValidationSeverity.ERROR,
                message=f"Output exceeds maximum length: {len(output)} > {self.max_output_length}",
                location=None,
                confidence=1.0
            ))
        
        # Category-specific validation
        if category == OutputCategory.CODE:
            issues.extend(self._validate_code(output))
        elif category == OutputCategory.COMMAND:
            issues.extend(self._validate_command(output))
        elif category == OutputCategory.SQL:
            issues.extend(self._validate_sql(output))
        elif category == OutputCategory.HTML:
            issues.extend(self._validate_html(output))
        
        # PII detection (all categories)
        issues.extend(self._detect_pii(output))
        
        # Policy compliance
        issues.extend(self._check_policy_compliance(output))
        
        # Run custom validators
        for validator in self._custom_validators:
            try:
                custom_issues = validator(output, category)
                issues.extend(custom_issues)
            except Exception as e:
                self.logger.error("custom_validator_error", error=str(e))
        
        # Determine validity
        critical_count = sum(1 for i in issues if i.severity == ValidationSeverity.CRITICAL)
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        
        is_valid = critical_count == 0 and error_count == 0
        
        if not is_valid:
            self._rejection_count += 1
        
        # Sanitize if needed
        sanitized = None
        if not is_valid:
            sanitized = self._sanitize_output(output, issues)
        
        processing_time = (time.time() - start_time) * 1000
        
        result = ValidationResult(
            is_valid=is_valid,
            category=category,
            issues=issues,
            sanitized_output=sanitized,
            confidence_score=confidence,
            policy_checks={"pii_free": not any(i.violation_type == ViolationType.PII_LEAK for i in issues)},
            processing_time_ms=processing_time,
            output_hash=hashlib.sha3_256(output.encode()).hexdigest()[:16]
        )
        
        # Log validation results
        if not is_valid:
            self.logger.warning(
                "output_validation_failed",
                category=category.name,
                issue_count=len(issues),
                critical_count=critical_count
            )
        
        return result
    
    def _detect_pii(self, output: str) -> List[ValidationIssue]:
        """Detect PII in output."""
        issues = []
        
        for pii_type, pattern in self.PII_PATTERNS:
            matches = pattern.findall(output)
            if matches:
                issues.append(ValidationIssue(
                    violation_type=ViolationType.PII_LEAK,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Potential {pii_type} detected: {matches[0][:20]}...",
                    location=f"Pattern match: {pii_type}",
                    confidence=0.9
                ))
        
        return issues
    
    def _validate_code(self, code: str) -> List[ValidationIssue]:
        """Validate code output."""
        issues = []
        
        for pattern_name, pattern, message in self.UNSAFE_CODE_PATTERNS:
            if pattern.search(code):
                issues.append(ValidationIssue(
                    violation_type=ViolationType.UNSAFE_CODE,
                    severity=ValidationSeverity.ERROR,
                    message=message,
                    location=f"Pattern: {pattern_name}",
                    confidence=0.85
                ))
        
        return issues
    
    def _validate_command(self, command: str) -> List[ValidationIssue]:
        """Validate shell command."""
        issues = []
        
        # Check for dangerous commands
        dangerous = ['rm -rf /', 'mkfs.', 'dd if=/dev/zero', '> /dev/sda']
        for cmd in dangerous:
            if cmd in command:
                issues.append(ValidationIssue(
                    violation_type=ViolationType.UNSAFE_CODE,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Dangerous command detected: {cmd}",
                    location=None,
                    confidence=0.95
                ))
        
        # Check for command injection patterns
        injection_patterns = [';', '&&', '||', '`', '$(']
        for pattern in injection_patterns:
            if pattern in command:
                issues.append(ValidationIssue(
                    violation_type=ViolationType.PROMPT_INJECTION,
                    severity=ValidationSeverity.WARNING,
                    message=f"Potential command injection pattern: {pattern}",
                    location=None,
                    confidence=0.6
                ))
        
        return issues
    
    def _validate_sql(self, sql: str) -> List[ValidationIssue]:
        """Validate SQL query."""
        issues = []
        
        # Check for SQL injection patterns
        dangerous_patterns = [
            r"';\s*--",
            r"';\s*\/\*",
            r"\bOR\s+1\s*=\s*1\b",
            r"\bDROP\s+TABLE\b",
            r"\bDELETE\s+FROM\b.*\bWHERE\b.*=.*\bOR\b",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                issues.append(ValidationIssue(
                    violation_type=ViolationType.UNSAFE_CODE,
                    severity=ValidationSeverity.ERROR,
                    message="Potential SQL injection detected",
                    location=f"Pattern: {pattern}",
                    confidence=0.8
                ))
        
        return issues
    
    def _validate_html(self, html: str) -> List[ValidationIssue]:
        """Validate HTML output."""
        issues = []
        
        # Check for script tags
        if re.search(r'<script[^>]*>', html, re.IGNORECASE):
            issues.append(ValidationIssue(
                violation_type=ViolationType.MALICIOUS_CONTENT,
                severity=ValidationSeverity.ERROR,
                message="Script tag detected in HTML output",
                location=None,
                confidence=0.9
            ))
        
        # Check for event handlers
        if re.search(r'on\w+\s*=', html, re.IGNORECASE):
            issues.append(ValidationIssue(
                violation_type=ViolationType.MALICIOUS_CONTENT,
                severity=ValidationSeverity.WARNING,
                message="Event handler detected in HTML output",
                location=None,
                confidence=0.7
            ))
        
        return issues
    
    def _check_policy_compliance(self, output: str) -> List[ValidationIssue]:
        """Check output against content policies."""
        issues = []
        output_lower = output.lower()
        
        for policy, keywords in self.POLICY_VIOLATIONS.items():
            matches = [kw for kw in keywords if kw in output_lower]
            if matches:
                issues.append(ValidationIssue(
                    violation_type=ViolationType.POLICY_VIOLATION,
                    severity=ValidationSeverity.ERROR,
                    message=f"Potential {policy} content detected",
                    location=f"Keywords: {matches[:3]}",
                    confidence=0.6
                ))
        
        return issues
    
    def _sanitize_output(self, output: str, issues: List[ValidationIssue]) -> str:
        """Attempt to sanitize output."""
        sanitized = output
        
        # Redact PII
        for pii_type, pattern in self.PII_PATTERNS:
            sanitized = pattern.sub(f"[{pii_type.upper()}_REDACTED]", sanitized)
        
        # Truncate if too long
        if len(sanitized) > self.max_output_length:
            sanitized = sanitized[:self.max_output_length] + "\n[TRUNCATED]"
        
        # Add warning prefix
        sanitized = f"[SANITIZED OUTPUT - {len(issues)} issues detected]\n\n{sanitized}"
        
        return sanitized
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validator statistics."""
        return {
            "total_validated": self._validation_count,
            "rejection_count": self._rejection_count,
            "rejection_rate": self._rejection_count / max(1, self._validation_count),
            "min_confidence": self.min_confidence,
            "custom_validators": len(self._custom_validators)
        }
