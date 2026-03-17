#!/usr/bin/env python3
"""
AMCIS Master Test Suite
Consolidates and tests all AMCIS Python modules
"""

import ast
import sys
import os
from pathlib import Path
import subprocess
import json
from datetime import datetime

class TestResult:
    def __init__(self, name, status, message="", errors=None):
        self.name = name
        self.status = status  # PASS/FAIL/SKIP
        self.message = message
        self.errors = errors or []
        
    def to_dict(self):
        return {
            'name': self.name,
            'status': self.status,
            'message': self.message,
            'errors': self.errors
        }

class AMCISTestSuite:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.results = []
        self.summary = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0
        }
        
    def run_all_tests(self):
        """Run all test categories"""
        print("="*80)
        print("AMCIS MASTER TEST SUITE")
        print(f"Started: {datetime.now().isoformat()}")
        print(f"Base Path: {self.base_path}")
        print("="*80)
        
        # Test 1: Python Syntax
        print("\n[1/5] Testing Python Module Syntax...")
        self._test_python_syntax()
        
        # Test 2: Database Schemas
        print("\n[2/5] Testing Database Schemas...")
        self._test_database_schemas()
        
        # Test 3: Docker Compose
        print("\n[3/5] Testing Docker Compose...")
        self._test_docker_compose()
        
        # Test 4: Import Tests
        print("\n[4/5] Testing Module Imports...")
        self._test_imports()
        
        # Test 5: Dependencies
        print("\n[5/5] Checking Dependencies...")
        self._test_dependencies()
        
        # Generate Report
        self._generate_report()
        
    def _test_python_syntax(self):
        """Test all Python files for syntax errors"""
        python_files = list(self.base_path.rglob("*.py"))
        
        for py_file in python_files:
            relative_path = py_file.relative_to(self.base_path)
            
            # Skip __pycache__ and venv
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                    
                # Parse to check syntax
                ast.parse(source)
                
                self.results.append(TestResult(
                    name=f"Syntax: {relative_path}",
                    status="PASS",
                    message="Valid Python syntax"
                ))
                self.summary['passed'] += 1
                
            except SyntaxError as e:
                self.results.append(TestResult(
                    name=f"Syntax: {relative_path}",
                    status="FAIL",
                    message=f"Syntax error at line {e.lineno}: {e.msg}"
                ))
                self.summary['failed'] += 1
            except Exception as e:
                self.results.append(TestResult(
                    name=f"Syntax: {relative_path}",
                    status="FAIL",
                    message=str(e)
                ))
                self.summary['failed'] += 1
                
        self.summary['total'] += len([r for r in self.results if 'Syntax:' in r.name])
        print(f"  Tested {len([r for r in self.results if 'Syntax:' in r.name])} Python files")
        
    def _test_database_schemas(self):
        """Test SQL schema files"""
        sql_files = list(self.base_path.rglob("*.sql"))
        
        for sql_file in sql_files:
            relative_path = sql_file.relative_to(self.base_path)
            
            try:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Basic SQL validation checks
                issues = []
                
                # Check for common SQL keywords
                if 'CREATE TABLE' not in content.upper() and 'CREATE INDEX' not in content.upper():
                    if content.strip():  # Non-empty file
                        issues.append("No CREATE TABLE or CREATE INDEX found")
                        
                # Check for unclosed quotes (basic)
                single_quotes = content.count("'")
                if single_quotes % 2 != 0:
                    issues.append("Unclosed single quotes detected")
                    
                if issues:
                    self.results.append(TestResult(
                        name=f"SQL: {relative_path}",
                        status="WARNING",
                        message="; ".join(issues)
                    ))
                else:
                    self.results.append(TestResult(
                        name=f"SQL: {relative_path}",
                        status="PASS",
                        message="SQL structure appears valid"
                    ))
                    self.summary['passed'] += 1
                    
            except Exception as e:
                self.results.append(TestResult(
                    name=f"SQL: {relative_path}",
                    status="FAIL",
                    message=str(e)
                ))
                self.summary['failed'] += 1
                
        self.summary['total'] += len([r for r in self.results if 'SQL:' in r.name])
        print(f"  Tested {len([r for r in self.results if 'SQL:' in r.name])} SQL files")
        
    def _test_docker_compose(self):
        """Test docker-compose files"""
        dc_files = list(self.base_path.rglob("docker-compose*.yml")) + \
                   list(self.base_path.rglob("docker-compose*.yaml"))
        
        for dc_file in dc_files:
            relative_path = dc_file.relative_to(self.base_path)
            
            try:
                # Try to validate with docker-compose config
                result = subprocess.run(
                    ['docker-compose', '-f', str(dc_file), 'config'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    self.results.append(TestResult(
                        name=f"Docker: {relative_path}",
                        status="PASS",
                        message="Valid docker-compose configuration"
                    ))
                    self.summary['passed'] += 1
                else:
                    self.results.append(TestResult(
                        name=f"Docker: {relative_path}",
                        status="FAIL",
                        message=result.stderr[:200]
                    ))
                    self.summary['failed'] += 1
                    
            except FileNotFoundError:
                # Docker not available, do basic YAML check
                try:
                    import yaml
                    with open(dc_file, 'r') as f:
                        yaml.safe_load(f)
                    self.results.append(TestResult(
                        name=f"Docker: {relative_path}",
                        status="PASS",
                        message="Valid YAML (docker not available for full validation)"
                    ))
                    self.summary['passed'] += 1
                except Exception as e:
                    self.results.append(TestResult(
                        name=f"Docker: {relative_path}",
                        status="FAIL",
                        message=str(e)
                    ))
                    self.summary['failed'] += 1
            except Exception as e:
                self.results.append(TestResult(
                    name=f"Docker: {relative_path}",
                    status="FAIL",
                    message=str(e)
                ))
                self.summary['failed'] += 1
                
        self.summary['total'] += len([r for r in self.results if 'Docker:' in r.name])
        print(f"  Tested {len([r for r in self.results if 'Docker:' in r.name])} Docker files")
        
    def _test_imports(self):
        """Test key module imports"""
        test_modules = [
            ('AGENT_FINANCE.core.agent_base', 'core/agent_base.py'),
            ('AGENT_FINANCE.core.risk_manager', 'core/risk_manager.py'),
            ('AGENT_FINANCE.core.portfolio_manager', 'core/portfolio_manager.py'),
            ('AGENT_FINANCE.agents.arbitrage_agent', 'agents/arbitrage_agent.py'),
            ('AGENT_FINANCE.agents.market_maker_agent', 'agents/market_maker_agent.py'),
            ('AGENT_FINANCE.exchanges.binance_connector', 'exchanges/binance_connector.py'),
            ('AGENT_FINANCE.api.trading_api', 'api/trading_api.py'),
        ]
        
        # Add base path to Python path temporarily
        sys.path.insert(0, str(self.base_path))
        sys.path.insert(0, str(self.base_path / 'AGENT_FINANCE'))
        
        for module_name, file_path in test_modules:
            full_path = self.base_path / 'AGENT_FINANCE' / file_path
            
            if not full_path.exists():
                self.results.append(TestResult(
                    name=f"Import: {module_name}",
                    status="SKIP",
                    message=f"File not found: {file_path}"
                ))
                self.summary['skipped'] += 1
                continue
                
            try:
                # Try importing the module
                module_parts = module_name.split('.')
                module = __import__(module_name, fromlist=module_parts[-1])
                
                self.results.append(TestResult(
                    name=f"Import: {module_name}",
                    status="PASS",
                    message="Module imports successfully"
                ))
                self.summary['passed'] += 1
                
            except ImportError as e:
                self.results.append(TestResult(
                    name=f"Import: {module_name}",
                    status="FAIL",
                    message=f"Import error: {str(e)}"
                ))
                self.summary['failed'] += 1
            except Exception as e:
                self.results.append(TestResult(
                    name=f"Import: {module_name}",
                    status="FAIL",
                    message=f"Error: {str(e)}"
                ))
                self.summary['failed'] += 1
                
        self.summary['total'] += len([r for r in self.results if 'Import:' in r.name])
        print(f"  Tested {len([r for r in self.results if 'Import:' in r.name])} module imports")
        
    def _test_dependencies(self):
        """Check for required dependencies"""
        required_packages = [
            ('fastapi', 'FastAPI web framework'),
            ('uvicorn', 'ASGI server'),
            ('pydantic', 'Data validation'),
            ('aiohttp', 'Async HTTP client'),
            ('asyncpg', 'PostgreSQL driver'),
            ('redis', 'Redis client'),
            ('web3', 'Ethereum Web3 library'),
            ('ccxt', 'Crypto exchange trading'),
            ('numpy', 'Numerical computing'),
            ('pandas', 'Data analysis'),
        ]
        
        for package, description in required_packages:
            try:
                __import__(package)
                self.results.append(TestResult(
                    name=f"Dep: {package}",
                    status="PASS",
                    message=f"{description} - installed"
                ))
                self.summary['passed'] += 1
            except ImportError:
                self.results.append(TestResult(
                    name=f"Dep: {package}",
                    status="FAIL",
                    message=f"{description} - NOT installed (pip install {package})"
                ))
                self.summary['failed'] += 1
                
        self.summary['total'] += len([r for r in self.results if 'Dep:' in r.name])
        print(f"  Tested {len([r for r in self.results if 'Dep:' in r.name])} dependencies")
        
    def _generate_report(self):
        """Generate master test report"""
        report_path = self.base_path / 'MASTER_TEST_REPORT.md'
        
        report = f"""# AMCIS MASTER TEST REPORT

**Generated:** {datetime.now().isoformat()}  
**Base Path:** {self.base_path}

---

## SUMMARY

| Metric | Count |
|--------|-------|
| **Total Tests** | {self.summary['total']} |
| **Passed** | {self.summary['passed']} ✅ |
| **Failed** | {self.summary['failed']} ❌ |
| **Skipped** | {self.summary['skipped']} ⏭️ |
| **Success Rate** | {(self.summary['passed'] / max(self.summary['total'], 1) * 100):.1f}% |

---

## DETAILED RESULTS

### Python Syntax Tests

| File | Status | Message |
|------|--------|---------|
"""
        
        # Add Python syntax results
        for result in self.results:
            if 'Syntax:' in result.name:
                status_icon = "✅" if result.status == "PASS" else "❌"
                report += f"| {result.name.replace('Syntax: ', '')} | {status_icon} {result.status} | {result.message} |\n"
                
        report += """
### SQL Schema Tests

| File | Status | Message |
|------|--------|---------|
"""
        
        # Add SQL results
        for result in self.results:
            if 'SQL:' in result.name:
                status_icon = "✅" if result.status in ["PASS", "WARNING"] else "❌"
                report += f"| {result.name.replace('SQL: ', '')} | {status_icon} {result.status} | {result.message} |\n"
                
        report += """
### Docker Compose Tests

| File | Status | Message |
|------|--------|---------|
"""
        
        # Add Docker results
        for result in self.results:
            if 'Docker:' in result.name:
                status_icon = "✅" if result.status == "PASS" else "❌"
                report += f"| {result.name.replace('Docker: ', '')} | {status_icon} {result.status} | {result.message} |\n"
                
        report += """
### Module Import Tests

| Module | Status | Message |
|--------|--------|---------|
"""
        
        # Add Import results
        for result in self.results:
            if 'Import:' in result.name:
                status_icon = "✅" if result.status == "PASS" else ("⏭️" if result.status == "SKIP" else "❌")
                report += f"| {result.name.replace('Import: ', '')} | {status_icon} {result.status} | {result.message} |\n"
                
        report += """
### Dependency Tests

| Package | Status | Description |
|---------|--------|-------------|
"""
        
        # Add Dependency results
        for result in self.results:
            if 'Dep:' in result.name:
                status_icon = "✅" if result.status == "PASS" else "❌"
                report += f"| {result.name.replace('Dep: ', '')} | {status_icon} {result.status} | {result.message} |\n"
                
        # Add errors and fixes section
        report += """
---

## ERRORS & FIXES NEEDED

"""
        
        failed_tests = [r for r in self.results if r.status == "FAIL"]
        if failed_tests:
            report += "### Failed Tests\n\n"
            for result in failed_tests:
                report += f"- **{result.name}**: {result.message}\n"
        else:
            report += "✅ **No failed tests!**\n"
            
        # Add final consolidated structure
        report += """
---

## CONSOLIDATED PROJECT STRUCTURE

```
AMCIS_UNIFIED/
├── AGENT_FINANCE/              # Financial AI Agent System (REVENUE ENGINE)
│   ├── agents/
│   │   ├── arbitrage_agent.py       # Cross-exchange arbitrage
│   │   ├── market_maker_agent.py    # Market making bot
│   │   ├── trading_agent.py         # Algorithmic trading
│   │   └── yield_agent.py           # DeFi yield farming
│   ├── core/
│   │   ├── agent_base.py            # Base agent framework
│   │   ├── risk_manager.py          # Risk controls
│   │   ├── portfolio_manager.py     # Capital allocation
│   │   └── treasury.py              # Treasury management
│   ├── exchanges/
│   │   ├── binance_connector.py     # Binance API
│   │   ├── uniswap_connector.py     # DeFi/Web3 integration
│   │   └── base.py                  # Exchange base class
│   ├── api/
│   │   ├── trading_api.py           # FastAPI REST endpoints
│   │   └── main.py                  # API server
│   ├── database/
│   │   └── schemas.sql              # PostgreSQL schema
│   ├── docker-compose.yml           # Infrastructure
│   ├── requirements.txt             # Python dependencies
│   └── README.md                    # Documentation
│
├── AMCIS_NG/                   # Next Generation Platform
│   ├── omega/                       # Quantum kill-chain
│   ├── python/ai-ml/               # ML/AI modules
│   └── simulations/                 # Security simulations
│
├── AMCIS_Q_SEC_CORE/           # Quantum Security Core
│   ├── ai_security/                 # AI security modules
│   ├── cli/                         # Command line interface
│   ├── commercial/                  # Licensing/commercial
│   ├── compliance/                  # Compliance engines
│   └── core/                        # Core security engine
│
└── MASTER_TEST_REPORT.md       # This report
```

---

## RECOMMENDED ACTIONS

1. **Install Missing Dependencies:**
   ```bash
   pip install -r AGENT_FINANCE/requirements.txt
   ```

2. **Start Infrastructure:**
   ```bash
   cd AGENT_FINANCE
   docker-compose up -d
   ```

3. **Run API Server:**
   ```bash
   python api/trading_api.py
   ```

4. **Access Dashboard:**
   - API: http://localhost:8080
   - Health: http://localhost:8080/health

---

## NOTES

- All Python syntax tests validate AST parsing
- Docker tests require Docker Desktop or docker-compose
- Import tests require dependencies to be installed
- SQL tests validate basic structure (not execution)

"""
        
        # Write report
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print(f"\n{'='*80}")
        print(f"TEST COMPLETE")
        print(f"Report saved to: {report_path}")
        print(f"Total: {self.summary['total']} | Passed: {self.summary['passed']} | Failed: {self.summary['failed']} | Skipped: {self.summary['skipped']}")
        print(f"Success Rate: {(self.summary['passed'] / max(self.summary['total'], 1) * 100):.1f}%")
        print(f"{'='*80}")
        
        return report_path


if __name__ == '__main__':
    # Run tests on AMCIS_UNIFIED
    base_path = r'C:\Users\L337B\AMCIS_UNIFIED'
    suite = AMCISTestSuite(base_path)
    suite.run_all_tests()
