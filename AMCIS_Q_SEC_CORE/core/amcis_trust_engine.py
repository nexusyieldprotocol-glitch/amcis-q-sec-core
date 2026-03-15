"""
AMCIS Trust Engine - Zero-Trust Execution Scoring
==================================================

Implements trust scoring for command execution based on:
- Signature validation
- Origin reputation
- Behavioral analysis
- Environmental factors

NIST Alignment: SP 800-207 (Zero Trust Architecture)
"""

import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

import structlog

from .amcis_exceptions import TrustException, ErrorCode
from .amcis_error_utils import safe_method, validate_not_none, validate_not_empty, timing_context


class TrustFactor(Enum):
    """Trust evaluation factors."""
    SIGNATURE_VALID = "signature_valid"
    ORIGIN_VERIFIED = "origin_verified"
    BEHAVIOR_NORMAL = "behavior_normal"
    CODE_REPUTATION = "code_reputation"
    ENVIRONMENT_SECURE = "environment_secure"


@dataclass
class TrustScore:
    """Trust score result container."""
    overall_score: float  # 0.0 to 1.0
    threshold: float
    passed: bool
    factor_scores: Dict[TrustFactor, float]
    details: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "overall_score": self.overall_score,
            "threshold": self.threshold,
            "passed": self.passed,
            "factor_scores": {k.value: v for k, v in self.factor_scores.items()},
            "details": self.details,
            "timestamp": self.timestamp
        }


@dataclass
class ExecutionContext:
    """Context for command execution."""
    command: str
    arguments: List[str]
    working_directory: Path
    environment: Dict[str, str]
    user_id: int
    session_id: str
    parent_process: Optional[int] = None


class TrustEngine:
    """
    AMCIS Trust Evaluation Engine
    =============================
    
    Implements zero-trust execution scoring with configurable trust factors.
    Fail-closed design: commands blocked if trust score below threshold.
    """
    
    # Default trust thresholds
    DEFAULT_THRESHOLD = 0.6
    CRITICAL_THRESHOLD = 0.8
    
    # Weight factors for trust calculation
    FACTOR_WEIGHTS: Dict[TrustFactor, float] = {
        TrustFactor.SIGNATURE_VALID: 0.30,
        TrustFactor.ORIGIN_VERIFIED: 0.20,
        TrustFactor.BEHAVIOR_NORMAL: 0.25,
        TrustFactor.CODE_REPUTATION: 0.15,
        TrustFactor.ENVIRONMENT_SECURE: 0.10,
    }
    
    # Known good signatures cache
    _verified_signatures: Set[str] = set()
    _suspicious_patterns: List[re.Pattern] = [
        re.compile(r'(?:eval|exec)\s*\(', re.IGNORECASE),
        re.compile(r'`.*?`'),  # Command substitution
        re.compile(r'\$\(.*\)'),  # Subshell
        re.compile(r'base64\s+(-d|--decode)'),
        re.compile(r'curl.*\|.*(bash|sh|zsh)', re.IGNORECASE),
        re.compile(r'wget.*\|.*(bash|sh|zsh)', re.IGNORECASE),
        re.compile(r'/dev/(tcp|udp)/'),
        re.compile(r'bash.*-c.*curl', re.IGNORECASE),  # bash executing curl
        re.compile(r'sh.*-c.*curl', re.IGNORECASE),
        re.compile(r'nc\s+-e', re.IGNORECASE),  # netcat with execute
        re.compile(r'python.*-c', re.IGNORECASE),  # python one-liner
        re.compile(r'perl.*-e', re.IGNORECASE),
        re.compile(r'ruby.*-e', re.IGNORECASE),
        re.compile(r'\|.*bash', re.IGNORECASE),  # piping to bash
    ]
    
    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        kernel=None
    ) -> None:
        """
        Initialize trust engine.
        
        Args:
            threshold: Minimum trust score for execution (0.0-1.0)
            kernel: AMCIS kernel reference
        """
        self.threshold = threshold
        self.kernel = kernel
        self.logger = structlog.get_logger("amcis.trust_engine")
        
        # Behavioral baseline
        self._command_history: List[Dict[str, Any]] = []
        self._baseline_frequency: Dict[str, int] = {}
        
        # Reputation cache
        self._reputation_cache: Dict[str, Tuple[float, float]] = {}  # score, timestamp
        self._reputation_ttl = 3600  # seconds
        
        # Trusted certificate authorities
        self._trusted_cas: List[str] = []
        self._load_trusted_cas()
        
        self.logger.info("trust_engine_initialized", threshold=threshold)
    
    @safe_method(error_code=ErrorCode.TRUST_VIOLATION, log=True)
    def _load_trusted_cas(self) -> None:
        """Load trusted certificate authorities."""
        # Load from system or configuration
        ca_paths = [
            "/etc/ssl/certs",
            "/etc/pki/tls/certs",
            "/usr/local/share/certs",
        ]
        
        for ca_path in ca_paths:
            path = Path(ca_path)
            if path.exists():
                self._trusted_cas.append(str(path))
    
    async def evaluate(
        self,
        context: ExecutionContext,
        strict_mode: bool = False
    ) -> TrustScore:
        """
        Evaluate trust score for command execution.
        
        Args:
            context: Execution context
            strict_mode: Use stricter evaluation criteria
            
        Returns:
            Trust score result
            
        Raises:
            TrustException: If trust evaluation fails critically
        """
        validate_not_none(context, "context")
        validate_not_empty(context.command, "context.command")
        
        threshold = self.CRITICAL_THRESHOLD if strict_mode else self.threshold
        
        factor_scores: Dict[TrustFactor, float] = {}
        details: Dict[str, Any] = {
            "command_hash": hashlib.sha256(
                context.command.encode()
            ).hexdigest()[:16],
            "evaluation_duration_ms": 0.0
        }
        
        with timing_context("trust_evaluation", threshold_ms=500.0):
            # Evaluate each trust factor
            factor_scores[TrustFactor.SIGNATURE_VALID] = await self._check_signature(
                context, details
            )
            factor_scores[TrustFactor.ORIGIN_VERIFIED] = await self._verify_origin(
                context, details
            )
            factor_scores[TrustFactor.BEHAVIOR_NORMAL] = await self._analyze_behavior(
                context, details
            )
            factor_scores[TrustFactor.CODE_REPUTATION] = await self._check_reputation(
                context, details
            )
            factor_scores[TrustFactor.ENVIRONMENT_SECURE] = await self._check_environment(
                context, details
            )
            
            # Calculate weighted overall score
            overall_score = sum(
                factor_scores[factor] * self.FACTOR_WEIGHTS[factor]
                for factor in TrustFactor
            )
            
            # Adjust for suspicious patterns
            suspicion_score = self._detect_suspicious_patterns(context)
            if suspicion_score > 0:
                overall_score *= (1.0 - suspicion_score * 0.5)
                details["suspicion_penalty"] = suspicion_score
            
            # Clamp to valid range
            overall_score = max(0.0, min(1.0, overall_score))
        
        result = TrustScore(
            overall_score=overall_score,
            threshold=threshold,
            passed=overall_score >= threshold,
            factor_scores=factor_scores,
            details=details
        )
        
        self.logger.info(
            "trust_evaluation_complete",
            command=context.command[:50],
            score=overall_score,
            passed=result.passed,
            correlation_id=context.session_id
        )
        
        return result
    
    async def _check_signature(
        self,
        context: ExecutionContext,
        details: Dict[str, Any]
    ) -> float:
        """
        Verify code signature authenticity.
        
        Args:
            context: Execution context
            details: Details dictionary to populate
            
        Returns:
            Signature trust score (0.0-1.0)
            
        Raises:
            TrustException: If signature verification fails critically
        """
        command_path = self._resolve_command_path(context.command)
        
        if command_path is None:
            details["signature_status"] = "command_not_found"
            return 0.5  # Neutral for scripts
        
        # Check cache first
        path_hash = hashlib.sha256(str(command_path).encode()).hexdigest()
        if path_hash in self._verified_signatures:
            details["signature_status"] = "cache_verified"
            return 1.0
        
        try:
            # Platform-specific signature verification
            if os.name == 'nt':  # Windows
                score = await self._verify_windows_signature(command_path, details)
            else:  # Unix-like
                score = await self._verify_unix_signature(command_path, details)
            
            if score >= 0.9:
                self._verified_signatures.add(path_hash)
            
            return score
            
        except TrustException:
            raise
        except Exception as e:
            self.logger.warning(
                "signature_verification_error",
                path=str(command_path),
                error=str(e)
            )
            raise TrustException(
                f"Signature verification failed: {e}",
                error_code=ErrorCode.AUTHENTICATION_FAILED,
                details={"path": str(command_path), "error": str(e)}
            ) from e
    
    @safe_method(error_code=ErrorCode.TRUST_VIOLATION, log=True)
    def _resolve_command_path(self, command: str) -> Optional[Path]:
        """Resolve command to absolute path."""
        # Check if already absolute
        cmd_path = Path(command)
        if cmd_path.is_absolute() and cmd_path.exists():
            return cmd_path
        
        # Search in PATH
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        for directory in path_dirs:
            full_path = Path(directory) / command
            if full_path.exists():
                return full_path
        
        return None
    
    async def _verify_windows_signature(
        self,
        path: Path,
        details: Dict[str, Any]
    ) -> float:
        """Verify Windows Authenticode signature."""
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-Command",
                 f"Get-AuthenticodeSignature -FilePath '{path}' | "
                 f"Select-Object -ExpandProperty Status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            status = result.stdout.strip()
            details["windows_signature_status"] = status
            
            if status == "Valid":
                return 1.0
            elif status == "NotSigned":
                return 0.3
            else:
                return 0.0
                
        except Exception as e:
            details["signature_error"] = str(e)
            raise TrustException(
                f"Windows signature verification failed: {e}",
                error_code=ErrorCode.AUTHENTICATION_FAILED,
                details={"path": str(path)}
            ) from e
    
    async def _verify_unix_signature(
        self,
        path: Path,
        details: Dict[str, Any]
    ) -> float:
        """Verify Unix signature (gpg, etc.)."""
        # Check for detached signature file
        sig_path = Path(str(path) + ".sig")
        
        if not sig_path.exists():
            details["signature_status"] = "no_signature_file"
            return 0.3
        
        try:
            result = subprocess.run(
                ["gpg", "--verify", str(sig_path), str(path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                details["signature_status"] = "gpg_valid"
                return 1.0
            else:
                details["signature_status"] = "gpg_invalid"
                raise TrustException(
                    "GPG signature verification failed",
                    error_code=ErrorCode.AUTHENTICATION_FAILED,
                    details={"path": str(path), "status": "gpg_invalid"}
                )
                
        except TrustException:
            raise
        except FileNotFoundError:
            # GPG not available
            details["signature_status"] = "gpg_not_available"
            return 0.5
        except Exception as e:
            details["signature_error"] = str(e)
            raise TrustException(
                f"Unix signature verification failed: {e}",
                error_code=ErrorCode.AUTHENTICATION_FAILED,
                details={"path": str(path)}
            ) from e
    
    async def _verify_origin(
        self,
        context: ExecutionContext,
        details: Dict[str, Any]
    ) -> float:
        """
        Verify origin of command.
        
        Args:
            context: Execution context
            details: Details dictionary
            
        Returns:
            Origin trust score
        """
        # Check if from trusted package manager
        command_path = self._resolve_command_path(context.command)
        
        if command_path is None:
            details["origin_status"] = "unknown_command"
            return 0.5
        
        path_str = str(command_path)
        
        # Trusted system directories
        trusted_prefixes = [
            "/usr/bin",
            "/usr/sbin",
            "/bin",
            "/sbin",
            "/usr/local/bin",
            "C:\\Windows\\System32",
            "C:\\Windows\\SysWOW64",
        ]
        
        for prefix in trusted_prefixes:
            if path_str.startswith(prefix):
                details["origin_status"] = "system_directory"
                return 0.9
        
        # Check if from known package manager
        if "/nix/store/" in path_str or "/home/linuxbrew/" in path_str:
            details["origin_status"] = "reproducible_package"
            return 0.85
        
        details["origin_path"] = path_str
        return 0.5
    
    async def _analyze_behavior(
        self,
        context: ExecutionContext,
        details: Dict[str, Any]
    ) -> float:
        """
        Analyze behavioral patterns.
        
        Args:
            context: Execution context
            details: Details dictionary
            
        Returns:
            Behavior trust score
        """
        command_key = context.command.split('/')[-1].split('\\')[-1]
        
        # Update frequency baseline
        self._baseline_frequency[command_key] = \
            self._baseline_frequency.get(command_key, 0) + 1
        
        # Check for unusual patterns
        frequency = self._baseline_frequency.get(command_key, 0)
        total_commands = sum(self._baseline_frequency.values())
        
        if total_commands > 100:
            frequency_ratio = frequency / total_commands
            
            if frequency_ratio > 0.1:  # Very common command
                details["behavior_status"] = "common_command"
                return 0.9
            elif frequency_ratio < 0.001:  # Rare command
                details["behavior_status"] = "rare_command"
                return 0.6
        
        details["behavior_status"] = "normal_frequency"
        return 0.75
    
    async def _check_reputation(
        self,
        context: ExecutionContext,
        details: Dict[str, Any]
    ) -> float:
        """
        Check code reputation from threat intelligence.
        
        Args:
            context: Execution context
            details: Details dictionary
            
        Returns:
            Reputation score
            
        Raises:
            TrustException: If reputation check fails critically
        """
        command_path = self._resolve_command_path(context.command)
        if command_path is None:
            return 0.5
        
        # Calculate file hash for reputation lookup
        try:
            import hashlib
            hasher = hashlib.sha256()
            with open(command_path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            file_hash = hasher.hexdigest()
            
            details["file_hash"] = file_hash[:16]
            
            # Check cache
            if file_hash in self._reputation_cache:
                score, timestamp = self._reputation_cache[file_hash]
                if time.time() - timestamp < self._reputation_ttl:
                    details["reputation_source"] = "cache"
                    return score
            
            # In production, query threat intelligence feed
            # For now, use local heuristics
            score = self._local_reputation_heuristics(command_path)
            self._reputation_cache[file_hash] = (score, time.time())
            
            details["reputation_source"] = "local_heuristics"
            return score
            
        except TrustException:
            raise
        except Exception as e:
            self.logger.warning("reputation_check_failed", error=str(e))
            raise TrustException(
                f"Reputation check failed: {e}",
                error_code=ErrorCode.TRUST_VIOLATION,
                details={"path": str(command_path)}
            ) from e
    
    @safe_method(default=0.5, error_code=ErrorCode.TRUST_VIOLATION, log=True)
    def _local_reputation_heuristics(self, path: Path) -> float:
        """Apply local heuristics for reputation scoring."""
        score = 0.5
        
        # Check file age
        try:
            stat = path.stat()
            age_days = (time.time() - stat.st_mtime) / 86400
            
            if age_days > 365:
                score += 0.2  # Well-established
            elif age_days < 1:
                score -= 0.3  # Very new
        except Exception:
            pass
        
        # Check file permissions
        try:
            mode = path.stat().st_mode
            if mode & 0o002:  # World-writable
                score -= 0.4
            if mode & 0o4000:  # SUID
                score -= 0.1  # Slight penalty, needs extra scrutiny
        except Exception:
            pass
        
        return max(0.0, min(1.0, score))
    
    async def _check_environment(
        self,
        context: ExecutionContext,
        details: Dict[str, Any]
    ) -> float:
        """
        Check environmental security factors.
        
        Args:
            context: Execution context
            details: Details dictionary
            
        Returns:
            Environment security score
            
        Raises:
            TrustException: If policy violation detected
        """
        score = 1.0
        issues = []
        
        # Check for privileged execution
        if context.user_id == 0 or (
            os.name == 'nt' and 
            context.environment.get('__COMPAT_LAYER') == 'RunAsAdmin'
        ):
            score -= 0.2
            issues.append("privileged_execution")
        
        # Check LD_PRELOAD (Linux)
        if 'LD_PRELOAD' in context.environment:
            score -= 0.5
            issues.append("ld_preload_set")
            raise TrustException(
                "LD_PRELOAD detected - potential code injection risk",
                error_code=ErrorCode.POLICY_VIOLATION,
                details={"issues": issues, "score": max(0.0, score)}
            )
        
        # Check for suspicious PATH entries
        path = context.environment.get('PATH', '')
        if '.' in path.split(os.pathsep):
            score -= 0.2
            issues.append("path_contains_dot")
        
        # Check temp directory execution
        temp_dirs = ['/tmp', '/var/tmp', 'C:\\Temp', 'C:\\Windows\\Temp']
        cwd = str(context.working_directory)
        if any(cwd.startswith(d) for d in temp_dirs):
            score -= 0.1
            issues.append("temp_directory_execution")
        
        details["environment_issues"] = issues
        return max(0.0, score)
    
    def _detect_suspicious_patterns(self, context: ExecutionContext) -> float:
        """
        Detect suspicious command patterns.
        
        Args:
            context: Execution context
            
        Returns:
            Suspicion score (0.0-1.0)
            
        Raises:
            TrustException: If critical suspicious patterns detected
        """
        full_command = ' '.join([context.command] + context.arguments)
        
        matches = 0
        for pattern in self._suspicious_patterns:
            if pattern.search(full_command):
                matches += 1
        
        suspicion_score = min(1.0, matches * 0.25)
        
        # Raise exception for highly suspicious patterns
        if suspicion_score >= 0.75:
            raise TrustException(
                "Critical suspicious patterns detected",
                error_code=ErrorCode.POLICY_VIOLATION,
                details={"suspicion_score": suspicion_score, "command": full_command[:100]}
            )
        
        return suspicion_score
    
    def update_threshold(self, new_threshold: float) -> None:
        """Update trust threshold."""
        validate_not_none(new_threshold, "new_threshold")
        self.threshold = max(0.0, min(1.0, new_threshold))
        self.logger.info("threshold_updated", new_threshold=self.threshold)
    
    def get_trust_report(self) -> Dict[str, Any]:
        """Generate trust engine status report."""
        return {
            "threshold": self.threshold,
            "verified_signatures_count": len(self._verified_signatures),
            "command_history_size": len(self._command_history),
            "reputation_cache_size": len(self._reputation_cache),
            "baseline_commands": len(self._baseline_frequency)
        }
