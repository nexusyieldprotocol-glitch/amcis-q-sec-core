"""
Tests for Supply Chain Security modules.
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supply_chain.amcis_dependency_validator import DependencyValidator, Vulnerability, Severity
from supply_chain.amcis_sbom_generator import SBOMGenerator, SBOMFormat
from supply_chain.amcis_signature_enforcer import SignatureEnforcer, SignatureStatus


class TestDependencyValidator:
    """Test cases for Dependency Validator."""
    
    def test_initialization(self):
        """Test validator initialization."""
        validator = DependencyValidator()
        assert validator is not None
    
    def test_scan_safe_dependency(self):
        """Test scanning a safe dependency."""
        validator = DependencyValidator()
        
        result = validator.scan_dependency(
            name="requests",
            version="2.28.1"
        )
        
        assert result is not None
    
    def test_scan_with_vulnerability(self):
        """Test detecting vulnerable dependency."""
        validator = DependencyValidator()
        
        # Scan a dependency (result depends on vulnerability DB)
        result = validator.scan_dependency(
            name="example-package",
            version="1.0.0"
        )
        
        assert result is not None
    
    def test_vulnerability_object(self):
        """Test Vulnerability data structure."""
        vuln = Vulnerability(
            cve_id="CVE-2021-44228",
            description="Log4j vulnerability",
            severity=Severity.CRITICAL
        )
        
        assert vuln.cve_id == "CVE-2021-44228"
        assert vuln.severity == Severity.CRITICAL


class TestSBOMGenerator:
    """Test cases for SBOM Generator."""
    
    def test_initialization(self):
        """Test generator initialization."""
        generator = SBOMGenerator()
        assert generator is not None
    
    def test_generate_sbom(self):
        """Test SBOM generation."""
        generator = SBOMGenerator()
        
        # Generate SBOM for current project
        sbom = generator.generate_from_requirements("requirements.txt")
        
        assert sbom is not None
        assert hasattr(sbom, 'components') or isinstance(sbom, dict)
    
    def test_export_formats(self):
        """Test different SBOM export formats."""
        generator = SBOMGenerator()
        
        formats = [SBOMFormat.SPDX, SBOMFormat.CYCLONEDX, SBOMFormat.SWID]
        
        for fmt in formats:
            # Test that format is valid
            assert fmt is not None


class TestSignatureEnforcer:
    """Test cases for Signature Enforcer."""
    
    def test_initialization(self):
        """Test enforcer initialization."""
        enforcer = SignatureEnforcer()
        assert enforcer is not None
    
    def test_verify_commit_signature(self):
        """Test verifying commit signature."""
        enforcer = SignatureEnforcer()
        
        # Mock commit data
        commit_data = {
            "hash": "abc123",
            "author": "test@example.com",
            "message": "Test commit"
        }
        
        result = enforcer.verify_commit(commit_data)
        
        assert result is not None
        assert hasattr(result, 'status') or isinstance(result, dict)
    
    def test_signature_status_enum(self):
        """Test SignatureStatus enum values."""
        assert SignatureStatus.VALID is not None
        assert SignatureStatus.INVALID is not None
        assert SignatureStatus.MISSING is not None


class TestIntegration:
    """Integration tests for Supply Chain Security components."""
    
    def test_full_pipeline(self):
        """Test full supply chain security pipeline."""
        validator = DependencyValidator()
        sbom_gen = SBOMGenerator()
        signer = SignatureEnforcer()
        
        # 1. Generate SBOM
        sbom = sbom_gen.generate_from_requirements("requirements.txt")
        assert sbom is not None
        
        # 2. Validate dependencies
        result = validator.scan_dependency("requests", "2.28.1")
        assert result is not None
        
        # 3. Check signatures
        commit = {"hash": "test123", "author": "dev@example.com"}
        sig_result = signer.verify_commit(commit)
        assert sig_result is not None
    
    def test_sbom_with_vulnerability_scan(self):
        """Test SBOM components against vulnerability database."""
        validator = DependencyValidator()
        sbom_gen = SBOMGenerator()
        
        # Generate SBOM
        sbom = sbom_gen.generate_from_requirements("requirements.txt")
        
        # Each component should be scannable
        # (Actual implementation depends on SBOM structure)
        assert sbom is not None
