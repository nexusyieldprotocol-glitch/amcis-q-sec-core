"""
AMCIS Secrets Manager Module
============================

Provides enterprise-grade secrets management with support for:
- Local encrypted storage
- HashiCorp Vault integration
- Automatic key rotation
- Audit logging

Usage:
    >>> from secrets_mgr import SecretsManager, VaultClient, VaultConfig
    >>> 
    >>> # Local secrets manager
    >>> local_mgr = SecretsManager()
    >>> local_mgr.set_secret("api_key", "secret123")
    >>> 
    >>> # Vault-backed secrets manager
    >>> vault_client = VaultClient(VaultConfig(token="dev-token"))
    >>> vault_mgr = SecretsManager(vault_client=vault_client)
    >>> vault_mgr.set_secret("api_key", "secret123", use_vault=True)
"""

from .secrets_manager import Secret, SecretsManager
from .vault_client import (
    VaultClient,
    VaultConfig,
    VaultError,
    VaultAuthError,
    VaultSecretError,
    VaultConnectionError,
    AuthMethod,
    SecretMetadata,
    SecretVersion
)

__all__ = [
    # Local secrets manager
    "Secret",
    "SecretsManager",
    
    # Vault client
    "VaultClient",
    "VaultConfig",
    "VaultError",
    "VaultAuthError",
    "VaultSecretError",
    "VaultConnectionError",
    "AuthMethod",
    "SecretMetadata",
    "SecretVersion",
]

__version__ = "1.0.0"
