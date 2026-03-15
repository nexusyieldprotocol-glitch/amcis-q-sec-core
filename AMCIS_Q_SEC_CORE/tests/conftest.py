"""
Pytest configuration and shared fixtures for AMCIS test suite
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory"""
    return Path(__file__).parent / "data"

@pytest.fixture
def sample_security_event():
    """Provide a sample security event for testing"""
    return {
        "timestamp": "2026-03-15T12:00:00Z",
        "severity": "high",
        "source_ip": "192.168.1.100",
        "event_type": "authentication_failure",
        "description": "Multiple failed login attempts"
    }

@pytest.fixture
def mock_vault_client():
    """Mock Vault client for testing"""
    class MockVaultClient:
        def __init__(self):
            self.secrets = {}
        
        def read(self, path):
            return {"data": self.secrets.get(path, {})}
        
        def write(self, path, data):
            self.secrets[path] = data
            return True
    
    return MockVaultClient()

@pytest.fixture
def temp_database():
    """Provide temporary database for testing"""
    import sqlite3
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        conn = sqlite3.connect(f.name)
        yield conn
        conn.close()
