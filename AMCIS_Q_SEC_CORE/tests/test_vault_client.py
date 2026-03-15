"""
Tests for Vault Client
======================

These tests require a running Vault instance in dev mode.
For CI/CD, use the Docker Compose setup.

Environment Variables:
    VAULT_ADDR: Vault URL (default: http://localhost:8200)
    VAULT_TOKEN: Vault token (default: dev-token)
    SKIP_VAULT_TESTS: Set to skip integration tests
"""

import os
import unittest
from unittest.mock import Mock, patch

import pytest

# Skip all tests if SKIP_VAULT_TESTS is set
skip_vault_tests = pytest.mark.skipif(
    os.environ.get("SKIP_VAULT_TESTS") == "1",
    reason="Vault tests disabled via SKIP_VAULT_TESTS"
)

try:
    from secrets_mgr.vault_client import (
        VaultClient,
        VaultConfig,
        VaultError,
        VaultAuthError,
        VaultSecretError,
        VaultConnectionError,
        AuthMethod
    )
    VAULT_CLIENT_AVAILABLE = True
except ImportError:
    VAULT_CLIENT_AVAILABLE = False


# Mark all tests to skip if vault client not available
pytestmark = pytest.mark.skipif(
    not VAULT_CLIENT_AVAILABLE,
    reason="Vault client not available"
)


class TestVaultConfig(unittest.TestCase):
    """Test Vault configuration."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = VaultConfig()
        self.assertEqual(config.addr, "http://localhost:8200")
        self.assertIsNone(config.token)
        self.assertEqual(config.auth_method, AuthMethod.TOKEN)
        self.assertEqual(config.max_retries, 3)
    
    def test_config_from_env(self):
        """Test configuration from environment variables."""
        with patch.dict(os.environ, {
            "VAULT_ADDR": "https://vault.example.com",
            "VAULT_TOKEN": "test-token",
            "VAULT_ROLE": "test-role",
            "VAULT_MAX_RETRIES": "5"
        }):
            config = VaultConfig()
            self.assertEqual(config.addr, "https://vault.example.com")
            self.assertEqual(config.token, "test-token")
            self.assertEqual(config.k8s_role, "test-role")
    
    def test_k8s_auth_config(self):
        """Test Kubernetes auth configuration."""
        config = VaultConfig(
            auth_method=AuthMethod.KUBERNETES,
            k8s_role="amcis-role",
            k8s_mount_path="k8s-auth"
        )
        self.assertEqual(config.auth_method, AuthMethod.KUBERNETES)
        self.assertEqual(config.k8s_role, "amcis-role")
        self.assertEqual(config.k8s_mount_path, "k8s-auth")


class TestVaultClientUnit(unittest.TestCase):
    """Unit tests for Vault client (no Vault required)."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        with patch.object(VaultClient, '_authenticate') as mock_auth:
            config = VaultConfig(token="test-token")
            client = VaultClient(config)
            self.assertEqual(client.config, config)
            mock_auth.assert_called_once()
    
    def test_invalid_auth_method(self):
        """Test invalid authentication method."""
        config = VaultConfig(auth_method="invalid")  # type: ignore
        with self.assertRaises(VaultAuthError):
            VaultClient(config)
    
    def test_missing_token(self):
        """Test missing token for token auth."""
        config = VaultConfig(token=None, auth_method=AuthMethod.TOKEN)
        with self.assertRaises(VaultAuthError):
            VaultClient(config)
    
    def test_context_manager(self):
        """Test context manager."""
        with patch.object(VaultClient, '_authenticate'):
            config = VaultConfig(token="test-token")
            with VaultClient(config) as client:
                self.assertIsInstance(client, VaultClient)


@skip_vault_tests
class TestVaultClientIntegration(unittest.TestCase):
    """Integration tests requiring running Vault."""
    
    @classmethod
    def setUpClass(cls):
        """Set up Vault client for tests."""
        cls.vault_addr = os.environ.get("VAULT_ADDR", "http://localhost:8200")
        cls.vault_token = os.environ.get("VAULT_TOKEN", "dev-token")
        
        try:
            cls.client = VaultClient(VaultConfig(
                addr=cls.vault_addr,
                token=cls.vault_token
            ))
        except VaultConnectionError:
            raise unittest.SkipTest("Vault not available")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up Vault client."""
        if hasattr(cls, 'client'):
            cls.client.close()
    
    def test_health(self):
        """Test health check."""
        health = self.client.health()
        self.assertIn("initialized", health)
        self.assertIn("sealed", health)
        self.assertIn("version", health)
    
    def test_is_authenticated(self):
        """Test authentication status."""
        self.assertTrue(self.client.is_authenticated())
    
    def test_token_info(self):
        """Test token information."""
        info = self.client.token_info()
        self.assertIn("policies", info)
        self.assertIn("ttl", info)
    
    def test_write_and_read_secret(self):
        """Test writing and reading secrets."""
        path = "secret/data/test/mysecret"
        data = {"password": "test123", "username": "admin"}
        
        # Write secret
        result = self.client.write_secret(path, data)
        self.assertIn("version", result)
        
        # Read secret
        secret = self.client.read_secret(path)
        self.assertEqual(secret["data"]["password"], "test123")
        self.assertEqual(secret["data"]["username"], "admin")
        self.assertIn("metadata", secret)
    
    def test_read_nonexistent_secret(self):
        """Test reading non-existent secret."""
        with self.assertRaises(VaultSecretError):
            self.client.read_secret("secret/data/test/nonexistent")
    
    def test_write_secret_versioning(self):
        """Test secret versioning."""
        path = "secret/data/test/versioned"
        
        # Write first version
        result1 = self.client.write_secret(path, {"v": "1"})
        version1 = result1["version"]
        
        # Write second version
        result2 = self.client.write_secret(path, {"v": "2"})
        version2 = result2["version"]
        
        self.assertEqual(version2, version1 + 1)
        
        # Read specific versions
        secret_v1 = self.client.read_secret(path, version=version1)
        secret_v2 = self.client.read_secret(path, version=version2)
        
        self.assertEqual(secret_v1["data"]["v"], "1")
        self.assertEqual(secret_v2["data"]["v"], "2")
    
    def test_delete_and_undelete_secret(self):
        """Test secret deletion and restoration."""
        path = "secret/data/test/deletable"
        
        # Write secret
        self.client.write_secret(path, {"key": "value"})
        
        # Delete specific version
        self.client.delete_secret(path, versions=[1])
        
        # Undelete
        self.client.undelete_secret(path, versions=[1])
        
        # Should be readable again
        secret = self.client.read_secret(path, version=1)
        self.assertEqual(secret["data"]["key"], "value")
    
    def test_list_secrets(self):
        """Test listing secrets."""
        # Create some test secrets
        self.client.write_secret("secret/data/test/list/a", {"key": "a"})
        self.client.write_secret("secret/data/test/list/b", {"key": "b"})
        
        # List
        keys = self.client.list_secrets("secret/metadata/test/list")
        self.assertIn("a", keys)
        self.assertIn("b", keys)
    
    def test_get_secret_metadata(self):
        """Test getting secret metadata."""
        path = "secret/data/test/meta"
        self.client.write_secret(path, {"key": "value"})
        
        metadata = self.client.get_secret_metadata("secret/metadata/test/meta")
        self.assertEqual(metadata.path, "secret/metadata/test/meta")
        self.assertGreater(metadata.current_version, 0)
        self.assertIn(metadata.current_version, metadata.versions)
    
    def test_write_with_cas(self):
        """Test write with check-and-set."""
        path = "secret/data/test/cas"
        
        # First write (CAS 0 means new)
        self.client.write_secret(path, {"v": "1"}, cas=0)
        
        # Write with correct version
        self.client.write_secret(path, {"v": "2"}, cas=1)
        
        # Read to verify
        secret = self.client.read_secret(path)
        self.assertEqual(secret["data"]["v"], "2")


class TestVaultErrorHandling(unittest.TestCase):
    """Test error handling."""
    
    def test_vault_error(self):
        """Test base Vault error."""
        error = VaultError("test error")
        self.assertEqual(str(error), "test error")
    
    def test_vault_auth_error(self):
        """Test authentication error."""
        error = VaultAuthError("auth failed")
        self.assertIsInstance(error, VaultError)
    
    def test_vault_secret_error(self):
        """Test secret error."""
        error = VaultSecretError("secret not found")
        self.assertIsInstance(error, VaultError)
    
    def test_vault_connection_error(self):
        """Test connection error."""
        error = VaultConnectionError("connection failed")
        self.assertIsInstance(error, VaultError)


class TestVaultClientMocked(unittest.TestCase):
    """Tests with mocked HTTP responses."""
    
    def setUp(self):
        """Set up mocked client."""
        with patch.object(VaultClient, '_authenticate'):
            self.client = VaultClient(VaultConfig(token="test-token"))
    
    def tearDown(self):
        """Clean up."""
        self.client.close()
    
    @patch.object(VaultClient, '_make_request')
    def test_read_secret_mocked(self, mock_request):
        """Test read secret with mock."""
        mock_request.return_value = {
            "data": {
                "data": {"password": "secret"},
                "metadata": {"version": 1}
            }
        }
        
        result = self.client.read_secret("secret/data/test")
        
        self.assertEqual(result["data"]["password"], "secret")
        mock_request.assert_called_once_with("GET", "secret/data/test", params=None)
    
    @patch.object(VaultClient, '_make_request')
    def test_write_secret_mocked(self, mock_request):
        """Test write secret with mock."""
        mock_request.return_value = {
            "data": {"version": 2}
        }
        
        result = self.client.write_secret("secret/data/test", {"key": "value"})
        
        self.assertEqual(result["version"], 2)
        mock_request.assert_called_once_with(
            "POST", "secret/data/test",
            data={"data": {"key": "value"}}
        )
    
    @patch.object(VaultClient, '_make_request')
    def test_health_mocked(self, mock_request):
        """Test health with mock."""
        mock_request.return_value = {
            "initialized": True,
            "sealed": False,
            "version": "1.15.0"
        }
        
        health = self.client.health()
        
        self.assertTrue(health["initialized"])
        self.assertFalse(health["sealed"])
        self.assertEqual(health["version"], "1.15.0")


if __name__ == "__main__":
    unittest.main()
