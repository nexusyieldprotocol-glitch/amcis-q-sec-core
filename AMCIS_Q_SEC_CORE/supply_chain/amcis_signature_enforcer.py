"""
AMCIS Signature Enforcer
=========================

Git commit signature enforcement and verification for
supply chain integrity.

Features:
- GPG signature verification
- Commit signing enforcement
- Key trust management
- Repository integrity validation

NIST Alignment: SP 800-161 (Supply Chain Risk Management)
"""

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog


class SignatureStatus(Enum):
    """Signature verification status."""
    VALID = auto()
    INVALID = auto()
    MISSING = auto()
    EXPIRED = auto()
    REVOKED = auto()
    UNKNOWN_KEY = auto()
    ERROR = auto()


class SignatureType(Enum):
    """Types of signatures."""
    GPG = auto()
    SSH = auto()
    X509 = auto()


@dataclass
class CommitSignature:
    """Git commit signature information."""
    commit_hash: str
    author: str
    committer: str
    timestamp: datetime
    signature_type: SignatureType
    signature_data: Optional[str]
    key_fingerprint: Optional[str]
    status: SignatureStatus
    verification_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "commit_hash": self.commit_hash[:16],
            "author": self.author,
            "committer": self.committer,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "signature_type": self.signature_type.name,
            "key_fingerprint": self.key_fingerprint[:16] if self.key_fingerprint else None,
            "status": self.status.name,
            "verification_message": self.verification_message
        }


@dataclass
class RepositoryPolicy:
    """Repository signature policy."""
    require_signatures: bool
    allowed_keys: List[str]
    trusted_authors: List[str]
    require_signed_merge_commits: bool
    min_signature_age_days: int
    auto_reject_expired_keys: bool


@dataclass
class VerificationResult:
    """Signature verification result."""
    repository: str
    branch: str
    commits_checked: int
    signed_commits: int
    valid_signatures: int
    invalid_signatures: int
    missing_signatures: int
    policy_violations: List[str]
    passed: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "repository": self.repository,
            "branch": self.branch,
            "commits_checked": self.commits_checked,
            "signed_commits": self.signed_commits,
            "valid_signatures": self.valid_signatures,
            "invalid_signatures": self.invalid_signatures,
            "missing_signatures": self.missing_signatures,
            "policy_violations": self.policy_violations,
            "passed": self.passed
        }


class SignatureEnforcer:
    """
    AMCIS Signature Enforcer
    ========================
    
    Git commit signature verification and enforcement for
    supply chain security.
    """
    
    def __init__(self, kernel=None) -> None:
        """
        Initialize signature enforcer.
        
        Args:
            kernel: AMCIS kernel reference
        """
        self.kernel = kernel
        self.logger = structlog.get_logger("amcis.signature_enforcer")
        
        # Trusted keys
        self._trusted_keys: Set[str] = set()
        self._revoked_keys: Set[str] = set()
        
        # Default policy
        self._default_policy = RepositoryPolicy(
            require_signatures=True,
            allowed_keys=[],
            trusted_authors=[],
            require_signed_merge_commits=True,
            min_signature_age_days=0,
            auto_reject_expired_keys=True
        )
        
        self.logger.info("signature_enforcer_initialized")
    
    def verify_commit(self, repo_path: Path, commit_hash: str) -> CommitSignature:
        """
        Verify a single commit signature.
        
        Args:
            repo_path: Path to repository
            commit_hash: Commit hash to verify
            
        Returns:
            Signature information
        """
        try:
            # Get commit signature info
            result = subprocess.run(
                ["git", "verify-commit", commit_hash, "--verbose"],
                capture_output=True,
                text=True,
                cwd=repo_path
            )
            
            # Get commit details
            show_result = subprocess.run(
                ["git", "show", "--format=%H|%an|%ae|%cn|%ce|%at|%GK|%GS", 
                 "--no-patch", commit_hash],
                capture_output=True,
                text=True,
                cwd=repo_path
            )
            
            parts = show_result.stdout.strip().split('|')
            
            status = SignatureStatus.VALID if result.returncode == 0 else SignatureStatus.INVALID
            
            sig = CommitSignature(
                commit_hash=parts[0] if len(parts) > 0 else commit_hash,
                author=parts[1] if len(parts) > 1 else "unknown",
                committer=parts[3] if len(parts) > 3 else "unknown",
                timestamp=datetime.fromtimestamp(int(parts[5])) if len(parts) > 5 and parts[5].isdigit() else datetime.now(),
                signature_type=SignatureType.GPG,
                signature_data=None,
                key_fingerprint=parts[6] if len(parts) > 6 else None,
                status=status,
                verification_message=result.stderr if result.returncode != 0 else "Good signature"
            )
            
            # Check if key is trusted
            if sig.key_fingerprint and sig.status == SignatureStatus.VALID:
                if sig.key_fingerprint in self._revoked_keys:
                    sig.status = SignatureStatus.REVOKED
                    sig.verification_message = "Key has been revoked"
                elif self._trusted_keys and sig.key_fingerprint not in self._trusted_keys:
                    sig.status = SignatureStatus.UNKNOWN_KEY
                    sig.verification_message = "Key is not in trusted keys list"
            
            return sig
            
        except Exception as e:
            self.logger.error("verify_failed", commit=commit_hash, error=str(e))
            return CommitSignature(
                commit_hash=commit_hash,
                author="unknown",
                committer="unknown",
                timestamp=datetime.now(),
                signature_type=SignatureType.GPG,
                signature_data=None,
                key_fingerprint=None,
                status=SignatureStatus.ERROR,
                verification_message=str(e)
            )
    
    def verify_repository(
        self,
        repo_path: Path,
        branch: str = "HEAD",
        since: Optional[str] = None,
        policy: Optional[RepositoryPolicy] = None
    ) -> VerificationResult:
        """
        Verify all commits in repository.
        
        Args:
            repo_path: Path to repository
            branch: Branch to verify
            since: Only verify commits since this date
            policy: Verification policy
            
        Returns:
            Verification result
        """
        policy = policy or self._default_policy
        
        # Get commit list
        cmd = ["git", "log", branch, "--format=%H"]
        if since:
            cmd.extend(["--since", since])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=repo_path
            )
            
            commit_hashes = result.stdout.strip().split('\n')
            commit_hashes = [h for h in commit_hashes if h]
            
        except Exception as e:
            self.logger.error("commit_list_failed", error=str(e))
            return VerificationResult(
                repository=str(repo_path),
                branch=branch,
                commits_checked=0,
                signed_commits=0,
                valid_signatures=0,
                invalid_signatures=0,
                missing_signatures=0,
                policy_violations=[f"Failed to list commits: {e}"],
                passed=False
            )
        
        # Verify each commit
        violations = []
        signed = 0
        valid = 0
        invalid = 0
        missing = 0
        
        for commit_hash in commit_hashes:
            sig = self.verify_commit(repo_path, commit_hash)
            
            if sig.status == SignatureStatus.VALID:
                signed += 1
                valid += 1
            elif sig.status == SignatureStatus.MISSING:
                missing += 1
                if policy.require_signatures:
                    violations.append(f"Commit {commit_hash[:8]} is not signed")
            else:
                signed += 1
                invalid += 1
                violations.append(f"Commit {commit_hash[:8]}: {sig.status.name}")
            
            # Check author policy
            if policy.trusted_authors and sig.author not in policy.trusted_authors:
                violations.append(f"Commit {commit_hash[:8]}: Untrusted author {sig.author}")
        
        passed = len(violations) == 0
        
        if policy.require_signatures and missing > 0:
            passed = False
        
        return VerificationResult(
            repository=str(repo_path),
            branch=branch,
            commits_checked=len(commit_hashes),
            signed_commits=signed,
            valid_signatures=valid,
            invalid_signatures=invalid,
            missing_signatures=missing,
            policy_violations=violations,
            passed=passed
        )
    
    def add_trusted_key(self, fingerprint: str) -> None:
        """Add a trusted GPG key fingerprint."""
        self._trusted_keys.add(fingerprint.replace(' ', '').upper())
        self.logger.info("key_trusted", fingerprint=fingerprint[:16])
    
    def revoke_key(self, fingerprint: str) -> None:
        """Revoke a previously trusted key."""
        fingerprint = fingerprint.replace(' ', '').upper()
        self._trusted_keys.discard(fingerprint)
        self._revoked_keys.add(fingerprint)
        self.logger.warning("key_revoked", fingerprint=fingerprint[:16])
    
    def enforce_signing(self, repo_path: Path, enable: bool = True) -> bool:
        """
        Configure repository to require signed commits.
        
        Args:
            repo_path: Path to repository
            enable: Enable or disable requirement
            
        Returns:
            True if configured successfully
        """
        try:
            # Configure git hooks or settings
            if enable:
                # Set up commit-msg hook to check signatures
                hook_path = repo_path / ".git" / "hooks" / "commit-msg"
                hook_content = """#!/bin/bash
# AMCIS Signature Check
if ! git verify-commit HEAD 2>/dev/null; then
    echo "Error: Commit must be signed"
    exit 1
fi
"""
                hook_path.write_text(hook_content)
                hook_path.chmod(0o755)
                
                self.logger.info("signing_enforced", repo=str(repo_path))
            else:
                hook_path = repo_path / ".git" / "hooks" / "commit-msg"
                if hook_path.exists():
                    hook_path.unlink()
                
                self.logger.info("signing_disabled", repo=str(repo_path))
            
            return True
            
        except Exception as e:
            self.logger.error("enforce_failed", error=str(e))
            return False
    
    def get_commit_signatures(
        self,
        repo_path: Path,
        branch: str = "HEAD",
        max_count: int = 100
    ) -> List[CommitSignature]:
        """
        Get signatures for recent commits.
        
        Args:
            repo_path: Path to repository
            branch: Branch to check
            max_count: Maximum commits to retrieve
            
        Returns:
            List of commit signatures
        """
        signatures = []
        
        try:
            result = subprocess.run(
                ["git", "log", branch, f"--max-count={max_count}", "--format=%H"],
                capture_output=True,
                text=True,
                cwd=repo_path
            )
            
            for commit_hash in result.stdout.strip().split('\n'):
                if commit_hash:
                    sig = self.verify_commit(repo_path, commit_hash)
                    signatures.append(sig)
        
        except Exception as e:
            self.logger.error("get_signatures_failed", error=str(e))
        
        return signatures
    
    def generate_report(self, result: VerificationResult) -> str:
        """Generate human-readable verification report."""
        lines = [
            "=" * 60,
            "AMCIS Signature Verification Report",
            "=" * 60,
            f"Repository: {result.repository}",
            f"Branch: {result.branch}",
            f"",
            f"Commits Checked: {result.commits_checked}",
            f"Signed Commits: {result.signed_commits}",
            f"Valid Signatures: {result.valid_signatures}",
            f"Invalid Signatures: {result.invalid_signatures}",
            f"Missing Signatures: {result.missing_signatures}",
            f"",
            f"Status: {'PASSED' if result.passed else 'FAILED'}",
        ]
        
        if result.policy_violations:
            lines.extend(["", "Policy Violations:"])
            for violation in result.policy_violations[:10]:
                lines.append(f"  - {violation}")
            
            if len(result.policy_violations) > 10:
                lines.append(f"  ... and {len(result.policy_violations) - 10} more")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
