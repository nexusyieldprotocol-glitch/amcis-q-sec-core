"""
AMCIS License Generator Tool
============================

Generate cryptographically signed commercial licenses.
Usage: python -m commercial.license_generator --tier ENTERPRISE --customer "Acme Corp" --endpoints 50000

REQUIRES: Access to .access_control file for signing credentials
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .licensing import LicenseManager, LicenseTier, get_license_manager


MODULE_OPTIONS = [
    'crypto', 'core', 'edr', 'network', 'ai_security', 'supply_chain',
    'biometrics', 'cloud_sec', 'container_sec', 'compliance', 'dashboard',
    'deception', 'deployment', 'dlp', 'forensics', 'sandbox', 'secrets_mgr',
    'soar', 'threat_intel', 'waf'
]


def main():
    parser = argparse.ArgumentParser(
        description='Generate AMCIS Q-SEC CORE Commercial Licenses',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluation license
  python -m commercial.license_generator --tier EVALUATION --customer "Demo" --days 30
  
  # Enterprise license
  python -m commercial.license_generator --tier ENTERPRISE --customer "BigCorp" \\
      --endpoints 50000 --modules crypto,edr,waf,dlp --years 3
  
  # Government license with custom features
  python -m commercial.license_generator --tier GOVERNMENT --customer "DoD" \\
      --endpoints 100000 --all-modules --source-code
        """
    )
    
    parser.add_argument('--tier', required=True, 
                       choices=['EVALUATION', 'STARTER', 'PROFESSIONAL', 'ENTERPRISE', 'STRATEGIC', 'GOVERNMENT'],
                       help='License tier')
    parser.add_argument('--customer', required=True, help='Customer name/ID')
    parser.add_argument('--endpoints', type=int, default=1000, help='Maximum endpoints (default: 1000)')
    parser.add_argument('--days', type=int, default=365, help='Duration in days (default: 365)')
    parser.add_argument('--years', type=int, help='Duration in years (overrides --days)')
    parser.add_argument('--modules', help='Comma-separated module list')
    parser.add_argument('--all-modules', action='store_true', help='Enable all modules')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--source-code', action='store_true', help='Include source code access')
    parser.add_argument('--air-gapped', action='store_true', help='Generate for air-gapped deployment')
    
    args = parser.parse_args()
    
    # Calculate duration
    duration_days = args.years * 365 if args.years else args.days
    
    # Determine modules
    if args.all_modules:
        modules = MODULE_OPTIONS
    elif args.modules:
        modules = [m.strip() for m in args.modules.split(',')]
    else:
        # Default modules by tier
        tier_defaults = {
            'EVALUATION': ['crypto', 'core', 'edr', 'network', 'ai_security', 'waf', 'threat_intel'],
            'STARTER': ['core', 'edr', 'network', 'waf', 'threat_intel'],
            'PROFESSIONAL': ['crypto', 'core', 'edr', 'network', 'ai_security', 'waf', 'dlp', 'compliance', 'threat_intel'],
            'ENTERPRISE': MODULE_OPTIONS,
            'STRATEGIC': MODULE_OPTIONS,
            'GOVERNMENT': MODULE_OPTIONS
        }
        modules = tier_defaults.get(args.tier, ['core'])
    
    # Custom features
    custom_features = {}
    if args.source_code:
        custom_features['source_code'] = True
    if args.air_gapped:
        custom_features['air_gapped'] = True
    
    # Generate license
    manager = get_license_manager()
    tier_enum = LicenseTier[args.tier]
    
    try:
        license_data = manager.generate_license(
            customer_id=args.customer,
            tier=tier_enum,
            duration_days=duration_days,
            max_endpoints=args.endpoints,
            modules=modules,
            custom_features=custom_features if custom_features else None
        )
        
        # Export to file
        output_path = manager.export_license(license_data, Path(args.output) if args.output else None)
        
        # Display results
        if args.json:
            print(json.dumps(license_data.to_dict(), indent=2))
        else:
            print("=" * 60)
            print("AMCIS Q-SEC CORE - LICENSE GENERATED")
            print("=" * 60)
            print(f"License ID:      {license_data.license_id}")
            print(f"Customer:        {license_data.customer_id}")
            print(f"Tier:            {license_data.tier.name}")
            print(f"Max Endpoints:   {license_data.max_endpoints:,}")
            print(f"Modules:         {len(license_data.modules)}")
            print(f"Issued:          {datetime.fromtimestamp(license_data.issued_at)}")
            print(f"Expires:         {datetime.fromtimestamp(license_data.expires_at)}")
            print(f"Hardware Hash:   {license_data.hardware_hash[:16]}...")
            print(f"Signature:       {license_data.signature[:16]}...")
            print(f"Output File:     {output_path}")
            print("=" * 60)
            print("\nFEATURES ENABLED:")
            for feature, enabled in license_data.features.items():
                status = "✓" if enabled else "✗"
                print(f"  [{status}] {feature}")
            print("=" * 60)
        
        print(f"\nLicense file saved to: {output_path}")
        print("Distribute this file securely to the customer.")
        
    except Exception as e:
        print(f"Error generating license: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
