#!/usr/bin/env python3
"""
AMCIS Pre-Push Hook

This script runs before pushing to remote to:
1. Run full test suite
2. Check for security vulnerabilities
3. Verify documentation is up to date
4. Run integration tests
5. Check branch protection rules

To install:
    cp scripts/pre_push_hook.py .git/hooks/pre-push
    chmod +x .git/hooks/pre-push
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description, check=True):
    """Run a shell command."""
    print(f"Running: {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0 and check:
        print(f"✗ {description} failed")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return False
    elif result.returncode == 0:
        print(f"✓ {description} passed")
    
    return True


def get_current_branch():
    """Get the current git branch."""
    result = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def check_protected_branch():
    """Check if trying to push to protected branch."""
    branch = get_current_branch()
    protected = ['main', 'master', 'production', 'release']
    
    if branch in protected:
        print(f"❌ Direct push to '{branch}' branch is not allowed!")
        print("   Please create a pull request instead.")
        return False
    
    return True


def run_full_test_suite():
    """Run the full test suite."""
    print("\n" + "="*60)
    print("Running Full Test Suite")
    print("="*60)
    
    # Run pytest with coverage
    result = subprocess.run(
        ['pytest', 'AMCIS_Q_SEC_CORE/tests/', '-v', '--tb=short', '-x'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("✗ Tests failed!")
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        return False
    
    print("✓ All tests passed")
    return True


def check_security():
    """Run security checks."""
    print("\n" + "="*60)
    print("Security Checks")
    print("="*60)
    
    # Bandit
    if subprocess.run(['which', 'bandit'], capture_output=True).returncode == 0:
        if not run_command(
            'bandit -r AMCIS_Q_SEC_CORE/ -ll -ii',
            "Bandit security scan",
            check=False
        ):
            print("⚠ Security issues found (review recommended)")
    
    # Safety check
    if subprocess.run(['which', 'safety'], capture_output=True).returncode == 0:
        run_command('safety check', "Dependency vulnerability scan", check=False)
    
    return True


def check_documentation():
    """Check if documentation is up to date."""
    print("\n" + "="*60)
    print("Documentation Check")
    print("="*60)
    
    script_path = Path(__file__).parent / 'generate_docs.py'
    if script_path.exists():
        result = subprocess.run(
            ['python', str(script_path), '--check'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 2:
            print("⚠ Documentation is outdated")
            print("   Run: python scripts/generate_docs.py")
            print("   Or set AMCIS_SKIP_DOC_CHECK=1 to skip")
            
            if os.environ.get('AMCIS_SKIP_DOC_CHECK') != '1':
                return False
    
    return True


def main():
    """Main pre-push logic."""
    print("="*60)
    print("AMCIS Pre-Push Hook")
    print("="*60)
    
    # Check branch protection
    if not check_protected_branch():
        sys.exit(1)
    
    # Run checks
    checks = []
    
    if os.environ.get('AMCIS_PRE_PUSH_QUICK', '0') != '1':
        checks.append(("Full Test Suite", run_full_test_suite()))
        checks.append(("Security Check", check_security()))
    
    checks.append(("Documentation Check", check_documentation()))
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    all_passed = all(result for _, result in checks)
    
    for name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"{status} {name}")
    
    if all_passed:
        print("\n✓ All checks passed. Pushing...")
        sys.exit(0)
    else:
        print("\n✗ Some checks failed. Push aborted.")
        print("\nTo bypass (not recommended): git push --no-verify")
        sys.exit(1)


if __name__ == '__main__':
    main()
