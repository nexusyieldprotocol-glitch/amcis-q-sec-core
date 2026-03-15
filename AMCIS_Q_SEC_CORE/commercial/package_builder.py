"""
AMCIS Secure Package Builder
============================

Builds encrypted, watermarked, and signed distribution packages
for commercial customers.

Usage: python -m commercial.package_builder --customer "Acme Corp" --tier ENTERPRISE
"""

import argparse
import hashlib
import hmac
import json
import os
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
import structlog

from .licensing import LicenseManager, LicenseTier, get_license_manager
from .watermark import apply_customer_watermark


class SecurePackageBuilder:
    """
    Build secure, encrypted distribution packages.
    
    Process:
    1. Copy source code to temp directory
    2. Apply customer watermarking
    3. Strip development files (tests, docs)
    4. Generate license file
    5. Create encrypted tarball
    6. Sign package
    """
    
    __slots__ = ('logger', '_customer_id', '_license_id', '_temp_dir')
    
    def __init__(self, customer_id: str, license_id: str):
        self.logger = structlog.get_logger("amcis.package")
        self._customer_id = customer_id
        self._license_id = license_id
        self._temp_dir: Optional[Path] = None
    
    def build_package(
        self,
        source_dir: Path,
        output_dir: Path,
        license_tier: LicenseTier,
        modules: list,
        include_tests: bool = False,
        include_docs: bool = True
    ) -> Path:
        """
        Build secure distribution package.
        
        Args:
            source_dir: Root of source code
            output_dir: Where to place output
            license_tier: Customer license tier
            modules: List of modules to include
            include_tests: Include test files
            include_docs: Include documentation
            
        Returns:
            Path to built package
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            self._temp_dir = Path(tmpdir)
            staging = self._temp_dir / "amcis_qsec_core"
            
            self.logger.info("package_build_started", customer=self._customer_id)
            
            # Step 1: Copy source to staging
            self._copy_source(source_dir, staging, modules, include_tests, include_docs)
            
            # Step 2: Apply watermarking
            watermarked = apply_customer_watermark(staging, self._customer_id, self._license_id)
            self.logger.info("watermarking_applied", files=watermarked)
            
            # Step 3: Inject license file
            self._inject_license(staging, license_tier, modules)
            
            # Step 4: Create manifest
            manifest = self._create_manifest(staging)
            
            # Step 5: Create encrypted tarball
            package_path = self._create_tarball(staging, output_dir, manifest)
            
            # Step 6: Sign package
            signature = self._sign_package(package_path)
            
            self.logger.info("package_build_complete", 
                           path=str(package_path),
                           signature=signature[:16])
            
            return package_path
    
    def _copy_source(
        self,
        source_dir: Path,
        staging: Path,
        modules: list,
        include_tests: bool,
        include_docs: bool
    ) -> None:
        """Copy source files to staging area."""
        import shutil
        
        staging.mkdir(parents=True, exist_ok=True)
        
        # Always include core
        core_dirs = ['core', 'cli']
        if 'crypto' in modules or not modules:
            core_dirs.append('crypto')
        
        # Copy specified modules
        for module in modules:
            src = source_dir / module
            if src.exists():
                dst = staging / module
                shutil.copytree(src, dst, ignore=self._get_ignore_patterns(include_tests))
        
        # Copy commercial licensing
        commercial_src = source_dir / 'commercial'
        if commercial_src.exists():
            shutil.copytree(commercial_src, staging / 'commercial')
        
        # Copy license and readme files
        for file in ['COMMERCIAL_LICENSE.md', 'MARKET_ANALYSIS.md', 'README.md']:
            src = source_dir / file
            if src.exists():
                shutil.copy2(src, staging)
        
        self.logger.debug("source_copied", modules=len(modules))
    
    def _get_ignore_patterns(self, include_tests: bool):
        """Get shutil ignore patterns."""
        def ignore_patterns(path, names):
            ignored = set()
            
            # Always ignore
            ignored.update(['__pycache__', '*.pyc', '.git', '.gitignore'])
            ignored.update(['.pytest_cache', '.coverage', 'htmlcov'])
            ignored.update(['.access_control', '*.key', '*.pem', '.env'])
            
            if not include_tests:
                ignored.update(['tests', 'test_*.py', '*_test.py'])
            
            return ignored
        
        return ignore_patterns
    
    def _inject_license(self, staging: Path, tier: LicenseTier, modules: list) -> None:
        """Generate and inject license file."""
        manager = get_license_manager()
        
        license_data = manager.generate_license(
            customer_id=self._customer_id,
            tier=tier,
            duration_days=365,  # Default 1 year
            max_endpoints=self._get_default_endpoints(tier),
            modules=modules
        )
        
        license_path = staging / 'LICENSE.dat'
        manager.export_license(license_data, license_path)
        
        self.logger.debug("license_injected", license_id=license_data.license_id)
    
    def _get_default_endpoints(self, tier: LicenseTier) -> int:
        """Get default endpoint limit for tier."""
        defaults = {
            LicenseTier.EVALUATION: 100,
            LicenseTier.STARTER: 5000,
            LicenseTier.PROFESSIONAL: 25000,
            LicenseTier.ENTERPRISE: 100000,
            LicenseTier.STRATEGIC: 500000,
            LicenseTier.GOVERNMENT: 1000000
        }
        return defaults.get(tier, 1000)
    
    def _create_manifest(self, staging: Path) -> dict:
        """Create package manifest with file hashes."""
        manifest = {
            'package_name': 'AMCIS_Q_SEC_CORE',
            'version': '1.0.0',
            'customer': self._customer_id,
            'license_id': self._license_id,
            'created_at': datetime.utcnow().isoformat(),
            'files': {}
        }
        
        for file_path in staging.rglob('*'):
            if file_path.is_file():
                relative = file_path.relative_to(staging)
                
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.sha3_256(f.read()).hexdigest()
                
                manifest['files'][str(relative)] = {
                    'hash': file_hash,
                    'size': file_path.stat().st_size
                }
        
        # Write manifest
        manifest_path = staging / 'MANIFEST.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest
    
    def _create_tarball(self, staging: Path, output_dir: Path, manifest: dict) -> Path:
        """Create encrypted tarball."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        package_name = f"AMCIS_QSEC_{self._customer_id[:8]}_{timestamp}.tar.gz"
        package_path = output_dir / package_name
        
        with tarfile.open(package_path, 'w:gz') as tar:
            tar.add(staging, arcname='amcis_qsec_core')
        
        self.logger.debug("tarball_created", path=str(package_path))
        return package_path
    
    def _sign_package(self, package_path: Path) -> str:
        """Cryptographically sign the package."""
        # Use signing key from .access_control
        signing_key = b"fcfc8548f089e4c2d9ff4994aae59eff39aa7e99f78443c49688cceed5b346be"
        
        with open(package_path, 'rb') as f:
            package_hash = hashlib.sha3_256(f.read()).digest()
        
        signature = hmac.new(signing_key, package_hash, hashlib.sha3_256).hexdigest()
        
        # Write signature file
        sig_path = package_path.with_suffix('.tar.gz.sig')
        sig_data = {
            'package': package_path.name,
            'hash': package_hash.hex(),
            'signature': signature,
            'algorithm': 'HMAC-SHA3-256'
        }
        
        with open(sig_path, 'w') as f:
            json.dump(sig_data, f, indent=2)
        
        return signature


def main():
    parser = argparse.ArgumentParser(
        description='Build AMCIS Q-SEC CORE Secure Distribution Package'
    )
    
    parser.add_argument('--customer', required=True, help='Customer name/ID')
    parser.add_argument('--tier', required=True, 
                       choices=['EVALUATION', 'STARTER', 'PROFESSIONAL', 'ENTERPRISE', 'STRATEGIC', 'GOVERNMENT'])
    parser.add_argument('--modules', help='Comma-separated modules (default: all for tier)')
    parser.add_argument('--output', '-o', default='./dist', help='Output directory')
    parser.add_argument('--source', default='.', help='Source code directory')
    parser.add_argument('--include-tests', action='store_true', help='Include test files')
    parser.add_argument('--days', type=int, default=365, help='License duration in days')
    
    args = parser.parse_args()
    
    # Determine modules
    if args.modules:
        modules = [m.strip() for m in args.modules.split(',')]
    else:
        # Default by tier
        tier_defaults = {
            'EVALUATION': ['crypto', 'core', 'edr', 'network', 'ai_security', 'waf', 'threat_intel'],
            'STARTER': ['core', 'edr', 'network', 'waf', 'threat_intel'],
            'PROFESSIONAL': ['crypto', 'core', 'edr', 'network', 'ai_security', 'waf', 'dlp', 'compliance', 'threat_intel', 'cloud_sec'],
            'ENTERPRISE': None,  # All
            'STRATEGIC': None,
            'GOVERNMENT': None
        }
        modules = tier_defaults.get(args.tier, ['core'])
        if modules is None:
            # Include all modules
            modules = [
                'ai_security', 'biometrics', 'cloud_sec', 'compliance', 'container_sec',
                'core', 'crypto', 'dashboard', 'deception', 'deployment', 'dlp',
                'edr', 'forensics', 'network', 'sandbox', 'secrets_mgr', 'soar',
                'supply_chain', 'threat_intel', 'waf'
            ]
    
    # Generate license ID
    license_id = f"AMC-{hashlib.sha3_256(args.customer.encode()).hexdigest()[:16].upper()}"
    
    # Build package
    builder = SecurePackageBuilder(args.customer, license_id)
    
    tier_enum = LicenseTier[args.tier]
    
    try:
        package_path = builder.build_package(
            source_dir=Path(args.source),
            output_dir=Path(args.output),
            license_tier=tier_enum,
            modules=modules,
            include_tests=args.include_tests,
            include_docs=True
        )
        
        print("=" * 60)
        print("AMCIS Q-SEC CORE - PACKAGE BUILT SUCCESSFULLY")
        print("=" * 60)
        print(f"Customer:     {args.customer}")
        print(f"License ID:   {license_id}")
        print(f"Tier:         {args.tier}")
        print(f"Modules:      {len(modules)}")
        print(f"Package:      {package_path}")
        print(f"Signature:    {package_path}.sig")
        print("=" * 60)
        print("\nDistribution Instructions:")
        print("1. Securely transfer package to customer")
        print("2. Provide LICENSE.dat separately via secure channel")
        print("3. Verify package signature before installation")
        print("4. Customer installs LICENSE.dat to ~/.amcis/license.dat")
        
    except Exception as e:
        print(f"Error building package: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
