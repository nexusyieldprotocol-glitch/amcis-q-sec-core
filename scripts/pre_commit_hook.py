#!/usr/bin/env python3
"""
AMCIS Pre-Commit Hook

This script runs as a git pre-commit hook to:
1. Run code formatting checks
2. Run linting
3. Run type checking
4. Run security scans
5. Generate/update documentation
6. Run tests on staged files

To install:
    cp scripts/pre_commit_hook.py .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

Or use with pre-commit framework:
    pre-commit install
"""

import os
import sys
import subprocess
import re
from pathlib import Path
from typing import List, Tuple, Optional


class Colors:
    """Terminal colors for output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")


def print_success(text: str):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def run_command(cmd: List[str], description: str, check: bool = True) -> Tuple[int, str, str]:
    """Run a shell command and return results."""
    print(f"Running: {description}...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0 and check:
            print_error(f"{description} failed")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
        elif result.returncode == 0:
            print_success(f"{description} passed")
        
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print_error(f"{description} timed out")
        return 1, "", "Timeout"
    except Exception as e:
        print_error(f"{description} error: {e}")
        return 1, "", str(e)


def get_staged_python_files() -> List[str]:
    """Get list of staged Python files."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
        capture_output=True,
        text=True
    )
    
    files = []
    for line in result.stdout.strip().split('\n'):
        if line.endswith('.py') and not line.startswith('test_'):
            if Path(line).exists():
                files.append(line)
    
    return files


def get_staged_files() -> List[str]:
    """Get list of all staged files."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
        capture_output=True,
        text=True
    )
    
    return [f for f in result.stdout.strip().split('\n') if f]


def check_code_formatting(files: List[str]) -> bool:
    """Check code formatting with Black."""
    print_header("Code Formatting Check")
    
    if not files:
        print("No Python files to check")
        return True
    
    # Check if black is installed
    result = subprocess.run(['which', 'black'], capture_output=True)
    if result.returncode != 0:
        print_warning("Black not installed, skipping format check")
        return True
    
    cmd = ['black', '--check', '--diff'] + files
    returncode, stdout, stderr = run_command(cmd, "Black format check", check=False)
    
    if returncode != 0:
        print_error("Code is not properly formatted")
        print("\nRun the following to fix:")
        print(f"  black {' '.join(files)}")
        return False
    
    return True


def run_linter(files: List[str]) -> bool:
    """Run Ruff linter on staged files."""
    print_header("Linting")
    
    if not files:
        print("No Python files to lint")
        return True
    
    # Check if ruff is installed
    result = subprocess.run(['which', 'ruff'], capture_output=True)
    if result.returncode != 0:
        print_warning("Ruff not installed, trying flake8...")
        cmd = ['flake8'] + files
    else:
        cmd = ['ruff', 'check'] + files
    
    returncode, stdout, stderr = run_command(cmd, "Linter", check=False)
    
    if returncode != 0:
        print_error("Linting errors found")
        if stdout:
            print(stdout)
        return False
    
    return True


def run_type_checker(files: List[str]) -> bool:
    """Run mypy type checker."""
    print_header("Type Checking")
    
    if not files:
        print("No Python files to check")
        return True
    
    # Check if mypy is installed
    result = subprocess.run(['which', 'mypy'], capture_output=True)
    if result.returncode != 0:
        print_warning("mypy not installed, skipping type check")
        return True
    
    cmd = ['mypy', '--ignore-missing-imports'] + files
    returncode, stdout, stderr = run_command(cmd, "Type check", check=False)
    
    if returncode != 0:
        print_warning("Type checking issues found (non-blocking)")
        if stdout:
            print(stdout)
        # Don't block commit for type issues, just warn
        return True
    
    return True


def run_security_scan(files: List[str]) -> bool:
    """Run security scans on staged files."""
    print_header("Security Scan")
    
    if not files:
        print("No Python files to scan")
        return True
    
    # Bandit scan
    result = subprocess.run(['which', 'bandit'], capture_output=True)
    if result.returncode == 0:
        cmd = ['bandit', '-r'] + files + ['-ll']
        returncode, stdout, stderr = run_command(cmd, "Bandit security scan", check=False)
        
        if returncode != 0:
            print_error("Security issues found!")
            if stdout:
                print(stdout)
            return False
    else:
        print_warning("Bandit not installed, skipping security scan")
    
    return True


def check_import_sorting(files: List[str]) -> bool:
    """Check import sorting with isort."""
    print_header("Import Sorting Check")
    
    if not files:
        print("No Python files to check")
        return True
    
    result = subprocess.run(['which', 'isort'], capture_output=True)
    if result.returncode != 0:
        print_warning("isort not installed, skipping import check")
        return True
    
    cmd = ['isort', '--check-only', '--diff'] + files
    returncode, stdout, stderr = run_command(cmd, "Import sort check", check=False)
    
    if returncode != 0:
        print_error("Imports are not properly sorted")
        print("\nRun the following to fix:")
        print(f"  isort {' '.join(files)}")
        return False
    
    return True


def generate_documentation() -> bool:
    """Generate/update documentation."""
    print_header("Documentation Generation")
    
    script_path = Path(__file__).parent / 'generate_docs.py'
    if not script_path.exists():
        print_warning("Documentation generator not found")
        return True
    
    cmd = ['python', str(script_path), '--source-dir', 'AMCIS_Q_SEC_CORE', '--output-dir', 'docs/api']
    returncode, stdout, stderr = run_command(cmd, "Documentation generation", check=False)
    
    if returncode == 0:
        # Stage generated documentation
        subprocess.run(['git', 'add', 'docs/api/'], capture_output=True)
        print_success("Documentation updated and staged")
    
    return True  # Don't block commit on doc generation


def run_tests_on_staged(files: List[str]) -> bool:
    """Run tests related to staged files."""
    print_header("Running Tests")
    
    if not files:
        print("No Python files to test")
        return True
    
    # Find related test files
    test_files = []
    for f in files:
        # Convert module path to test path
        test_file = f.replace('.py', '_test.py').replace('.py', '_tests.py')
        test_path = Path('tests') / test_file
        if test_path.exists():
            test_files.append(str(test_path))
    
    if not test_files:
        print("No test files found for staged changes")
        return True
    
    # Check if pytest is installed
    result = subprocess.run(['which', 'pytest'], capture_output=True)
    if result.returncode != 0:
        print_warning("pytest not installed, skipping tests")
        return True
    
    cmd = ['pytest'] + test_files + ['-v', '--tb=short', '-x']
    returncode, stdout, stderr = run_command(cmd, "Tests", check=False)
    
    if returncode != 0:
        print_error("Tests failed!")
        if stdout:
            print(stdout)
        return False
    
    return True


def check_commit_message() -> bool:
    """Check commit message format."""
    print_header("Commit Message Check")
    
    # Get the commit message from the COMMIT_EDITMSG file or git log
    commit_msg_file = Path('.git/COMMIT_EDITMSG')
    if commit_msg_file.exists():
        message = commit_msg_file.read_text()
    else:
        # Try to get from git
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=%B'],
            capture_output=True,
            text=True
        )
        message = result.stdout
    
    # Check message length
    lines = message.strip().split('\n')
    if not lines or not lines[0]:
        print_error("Commit message is empty")
        return False
    
    # Check subject line length (conventional commits recommends 50, allow 72)
    subject = lines[0]
    if len(subject) > 72:
        print_error(f"Subject line too long ({len(subject)} > 72 chars)")
        return False
    
    # Check for conventional commit format (optional but recommended)
    conventional_pattern = r'^(feat|fix|docs|style|refactor|test|chore|ci|perf)(\(.+\))?: .+'
    if not re.match(conventional_pattern, subject):
        print_warning("Consider using conventional commit format:")
        print("  type(scope): description")
        print("\nTypes: feat, fix, docs, style, refactor, test, chore, ci, perf")
    
    print_success("Commit message format OK")
    return True


def check_large_files() -> bool:
    """Check for large files being committed."""
    print_header("Large File Check")
    
    # Get staged files with sizes
    result = subprocess.run(
        ['git', 'diff', '--cached', '--numstat', '--diff-filter=ACM'],
        capture_output=True,
        text=True
    )
    
    max_size_mb = 10
    large_files = []
    
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) >= 3:
            file_path = parts[2]
            try:
                size = Path(file_path).stat().st_size
                size_mb = size / (1024 * 1024)
                if size_mb > max_size_mb:
                    large_files.append((file_path, size_mb))
            except:
                pass
    
    if large_files:
        print_error(f"Large files detected (> {max_size_mb}MB):")
        for f, size in large_files:
            print(f"  {f}: {size:.2f} MB")
        print("\nConsider using Git LFS for large files")
        return False
    
    print_success("No large files detected")
    return True


def main():
    """Main pre-commit hook logic."""
    print(f"{Colors.BOLD}AMCIS Pre-Commit Hook{Colors.ENDC}")
    print(f"Working directory: {os.getcwd()}")
    
    # Get staged files
    staged_python_files = get_staged_python_files()
    all_staged_files = get_staged_files()
    
    print(f"\nStaged Python files: {len(staged_python_files)}")
    print(f"Total staged files: {len(all_staged_files)}")
    
    if not all_staged_files:
        print("\nNo staged files. Commit aborted.")
        sys.exit(1)
    
    results = []
    
    # Run checks
    results.append(("Code Formatting", check_code_formatting(staged_python_files)))
    results.append(("Import Sorting", check_import_sorting(staged_python_files)))
    results.append(("Linting", run_linter(staged_python_files)))
    results.append(("Type Checking", run_type_checker(staged_python_files)))
    results.append(("Security Scan", run_security_scan(staged_python_files)))
    results.append(("Large Files", check_large_files()))
    results.append(("Commit Message", check_commit_message()))
    
    # Optional checks (can be slow)
    if os.environ.get('AMCIS_PRE_COMMIT_FULL', '0') == '1':
        results.append(("Tests", run_tests_on_staged(staged_python_files)))
        results.append(("Documentation", generate_documentation()))
    
    # Summary
    print_header("Summary")
    
    failed = []
    for name, passed in results:
        if passed:
            print_success(name)
        else:
            print_error(name)
            failed.append(name)
    
    if failed:
        print(f"\n{Colors.FAIL}{'='*60}{Colors.ENDC}")
        print(f"{Colors.FAIL}COMMIT REJECTED{Colors.ENDC}")
        print(f"{Colors.FAIL}Failed checks: {', '.join(failed)}{Colors.ENDC}")
        print(f"{Colors.FAIL}{'='*60}{Colors.ENDC}")
        
        print("\nTo bypass pre-commit hooks (not recommended):")
        print("  git commit --no-verify")
        
        sys.exit(1)
    else:
        print(f"\n{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}ALL CHECKS PASSED{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
        
        # Stage any auto-generated documentation
        if os.environ.get('AMCIS_PRE_COMMIT_FULL', '0') == '1':
            subprocess.run(['git', 'add', 'docs/api/'], capture_output=True)
        
        sys.exit(0)


if __name__ == '__main__':
    main()
