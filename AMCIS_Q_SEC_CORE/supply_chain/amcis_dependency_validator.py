"""
AMCIS Dependency Validator
===========================

Dependency security validation with CVE scanning and
vulnerability assessment.

Features:
- CVE database integration (stub)
- Vulnerability scanning
- License compliance checking
- Update availability checking

NIST Alignment: SP 800-161 (Supply Chain Risk Management)
"""

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog


class Severity(Enum):
    """Vulnerability severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class VulnStatus(Enum):
    """Vulnerability status."""
    AFFECTED = auto()
    FIXED = auto()
    NOT_AFFECTED = auto()
    UNDER_INVESTIGATION = auto()


@dataclass
class Vulnerability:
    """Vulnerability information."""
    cve_id: str
    description: str
    severity: Severity
    cvss_score: Optional[float]
    affected_versions: List[str]
    fixed_versions: List[str]
    references: List[str]
    published_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cve_id": self.cve_id,
            "description": self.description[:200] if self.description else None,
            "severity": self.severity.value,
            "cvss_score": self.cvss_score,
            "affected_versions": self.affected_versions,
            "fixed_versions": self.fixed_versions,
            "references": self.references[:3],
            "published_date": self.published_date.isoformat() if self.published_date else None
        }


@dataclass
class DependencyIssue:
    """Dependency issue."""
    package_name: str
    current_version: str
    issue_type: str  # 'vulnerability', 'outdated', 'license', 'yanked'
    severity: Severity
    details: str
    remediation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "package_name": self.package_name,
            "current_version": self.current_version,
            "issue_type": self.issue_type,
            "severity": self.severity.value,
            "details": self.details,
            "remediation": self.remediation
        }


@dataclass
class VulnerabilityReport:
    """Vulnerability scan report."""
    scan_time: datetime
    total_packages: int
    vulnerable_packages: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    issues: List[DependencyIssue]
    summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scan_time": self.scan_time.isoformat(),
            "total_packages": self.total_packages,
            "vulnerable_packages": self.vulnerable_packages,
            "severity_counts": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count
            },
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary
        }


class DependencyValidator:
    """
    AMCIS Dependency Validator
    ==========================
    
    Dependency security validation with vulnerability scanning
    and compliance checking.
    """
    
    # Known vulnerable packages (example data)
    KNOWN_VULNERABILITIES: Dict[str, List[Vulnerability]] = {
        "requests": [
            Vulnerability(
                cve_id="CVE-2018-18074",
                description="The Requests package before 2.20.0 sends an HTTP Authorization header",
                severity=Severity.MEDIUM,
                cvss_score=5.3,
                affected_versions=["<2.20.0"],
                fixed_versions=[">=2.20.0"],
                references=["https://nvd.nist.gov/vuln/detail/CVE-2018-18074"]
            )
        ],
        "urllib3": [
            Vulnerability(
                cve_id="CVE-2021-33503",
                description="urllib3 before 1.26.5 allows injection of arbitrary HTTP headers",
                severity=Severity.HIGH,
                cvss_score=7.5,
                affected_versions=["<1.26.5"],
                fixed_versions=[">=1.26.5"],
                references=["https://nvd.nist.gov/vuln/detail/CVE-2021-33503"]
            )
        ],
        "django": [
            Vulnerability(
                cve_id="CVE-2022-28346",
                description="Potential SQL injection in Django",
                severity=Severity.CRITICAL,
                cvss_score=9.8,
                affected_versions=[">=2.2,<2.2.28", ">=3.2,<3.2.13", ">=4.0,<4.0.4"],
                fixed_versions=[">=2.2.28", ">=3.2.13", ">=4.0.4"],
                references=["https://nvd.nist.gov/vuln/detail/CVE-2022-28346"]
            )
        ],
    }
    
    def __init__(self, kernel=None) -> None:
        """
        Initialize dependency validator.
        
        Args:
            kernel: AMCIS kernel reference
        """
        self.kernel = kernel
        self.logger = structlog.get_logger("amcis.dependency_validator")
        
        # Cache for vulnerability data
        self._vuln_cache: Dict[str, List[Vulnerability]] = {}
        
        self.logger.info("dependency_validator_initialized")
    
    def validate_project(self, project_path: Path) -> VulnerabilityReport:
        """
        Validate project dependencies.
        
        Args:
            project_path: Path to project
            
        Returns:
            Validation report
        """
        issues = []
        
        # Detect and parse dependencies
        if (project_path / "requirements.txt").exists():
            issues.extend(self._validate_python_requirements(project_path))
        
        if (project_path / "package.json").exists():
            issues.extend(self._validate_npm_dependencies(project_path))
        
        # Calculate statistics
        total_packages = len(issues)
        vulnerable_packages = len(set(i.package_name for i in issues if i.issue_type == "vulnerability"))
        
        critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == Severity.HIGH)
        medium_count = sum(1 for i in issues if i.severity == Severity.MEDIUM)
        low_count = sum(1 for i in issues if i.severity == Severity.LOW)
        
        # Generate summary
        if critical_count > 0:
            summary = f"CRITICAL: {critical_count} critical vulnerabilities found. Immediate action required."
        elif high_count > 0:
            summary = f"HIGH: {high_count} high severity issues found. Review recommended."
        elif medium_count > 0:
            summary = f"MEDIUM: {medium_count} medium severity issues found."
        elif low_count > 0:
            summary = f"LOW: {low_count} low severity issues found."
        else:
            summary = "No issues found. Dependencies appear secure."
        
        report = VulnerabilityReport(
            scan_time=datetime.utcnow(),
            total_packages=total_packages,
            vulnerable_packages=vulnerable_packages,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            issues=issues,
            summary=summary
        )
        
        self.logger.info(
            "validation_complete",
            total_packages=total_packages,
            vulnerable_packages=vulnerable_packages,
            critical_count=critical_count
        )
        
        return report
    
    def _validate_python_requirements(self, project_path: Path) -> List[DependencyIssue]:
        """Validate Python requirements."""
        issues = []
        
        req_file = project_path / "requirements.txt"
        if not req_file.exists():
            return issues
        
        with open(req_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Parse package specification
                match = re.match(r'^([a-zA-Z0-9_-]+)\s*==?\s*([^;\s]+)', line)
                if match:
                    package_name = match.group(1).lower()
                    version = match.group(2)
                    
                    # Check for known vulnerabilities
                    vulns = self.KNOWN_VULNERABILITIES.get(package_name, [])
                    
                    for vuln in vulns:
                        if self._version_affected(version, vuln.affected_versions):
                            issues.append(DependencyIssue(
                                package_name=package_name,
                                current_version=version,
                                issue_type="vulnerability",
                                severity=vuln.severity,
                                details=f"{vuln.cve_id}: {vuln.description[:100]}...",
                                remediation=f"Upgrade to {', '.join(vuln.fixed_versions)}"
                            ))
        
        return issues
    
    def _validate_npm_dependencies(self, project_path: Path) -> List[DependencyIssue]:
        """Validate npm dependencies."""
        issues = []
        
        package_file = project_path / "package.json"
        if not package_file.exists():
            return issues
        
        try:
            with open(package_file) as f:
                package_data = json.load(f)
            
            # Check for npm audit
            try:
                result = subprocess.run(
                    ["npm", "audit", "--json"],
                    capture_output=True,
                    text=True,
                    cwd=project_path,
                    timeout=60
                )
                
                if result.returncode == 0:
                    audit_data = json.loads(result.stdout)
                    
                    for vuln in audit_data.get("vulnerabilities", {}).values():
                        issues.append(DependencyIssue(
                            package_name=vuln.get("name", "unknown"),
                            current_version=vuln.get("range", "unknown"),
                            issue_type="vulnerability",
                            severity=Severity(vuln.get("severity", "UNKNOWN").upper()),
                            details=vuln.get("via", [{}])[0].get("title", "Unknown vulnerability"),
                            remediation=f"Run 'npm audit fix' to resolve"
                        ))
            
            except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as e:
                self.logger.warning("npm_audit_failed", error=str(e))
        
        except Exception as e:
            self.logger.warning("npm_validation_failed", error=str(e))
        
        return issues
    
    def _version_affected(self, version: str, affected_ranges: List[str]) -> bool:
        """Check if version is in affected range."""
        # Simplified version comparison
        for range_spec in affected_ranges:
            # Handle common range formats
            if range_spec.startswith('<='):
                return self._compare_versions(version, range_spec[2:]) <= 0
            elif range_spec.startswith('<'):
                return self._compare_versions(version, range_spec[1:]) < 0
            elif range_spec.startswith('>='):
                return self._compare_versions(version, range_spec[2:]) >= 0
            elif range_spec.startswith('>'):
                return self._compare_versions(version, range_spec[1:]) > 0
        
        return False
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns -1, 0, or 1."""
        try:
            # Normalize versions
            v1_parts = [int(x) for x in re.split(r'[.-]', v1.split(',')[0]) if x.isdigit()][:4]
            v2_parts = [int(x) for x in re.split(r'[.-]', v2.split(',')[0]) if x.isdigit()][:4]
            
            # Pad with zeros
            while len(v1_parts) < 4:
                v1_parts.append(0)
            while len(v2_parts) < 4:
                v2_parts.append(0)
            
            for p1, p2 in zip(v1_parts, v2_parts):
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1
            
            return 0
        except (ValueError, IndexError):
            return 0
    
    def check_outdated(self, project_path: Path) -> List[DependencyIssue]:
        """
        Check for outdated dependencies.
        
        Args:
            project_path: Path to project
            
        Returns:
            List of outdated dependencies
        """
        issues = []
        
        # Python pip list --outdated
        if (project_path / "requirements.txt").exists():
            try:
                result = subprocess.run(
                    ["pip", "list", "--outdated", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    outdated = json.loads(result.stdout)
                    for pkg in outdated:
                        issues.append(DependencyIssue(
                            package_name=pkg["name"],
                            current_version=pkg["version"],
                            issue_type="outdated",
                            severity=Severity.LOW,
                            details=f"Latest version: {pkg['latest_version']}",
                            remediation=f"Upgrade to {pkg['latest_version']}"
                        ))
            except Exception as e:
                self.logger.warning("outdated_check_failed", error=str(e))
        
        return issues
    
    def generate_remediation_plan(self, report: VulnerabilityReport) -> List[Dict[str, Any]]:
        """
        Generate remediation plan from report.
        
        Args:
            report: Vulnerability report
            
        Returns:
            Remediation steps
        """
        plan = []
        
        # Group by severity
        critical = [i for i in report.issues if i.severity == Severity.CRITICAL]
        high = [i for i in report.issues if i.severity == Severity.HIGH]
        
        for issue in critical + high:
            plan.append({
                "priority": "IMMEDIATE" if issue.severity == Severity.CRITICAL else "HIGH",
                "package": issue.package_name,
                "action": issue.remediation or "Review and update",
                "details": issue.details
            })
        
        return plan
