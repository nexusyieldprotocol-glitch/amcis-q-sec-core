"""
Vault Manager - Secrets Management
==================================

Secure secrets storage with support for:
- HashiCorp Vault (production)
- Encrypted file-based storage (development)

All secrets are encrypted at rest and never logged in plaintext.
"""

import os
import json
import base64
import hashlib
import getpass
from enum import Enum
from typing import Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass

import structlog
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

logger = structlog.get_logger("amcis.vault")


class SecretType(Enum):
    """Types of secrets managed by vault."""
    API_KEY = "api_key"
    PRIVATE_KEY = "private_key"
    DATABASE_PASSWORD = "db_password"
    TRADING_CONFIG = "trading_config"
    KERNEL_MASTER_KEY = "kernel_master_key"


@dataclass
class Secret:
    """Vault secret container."""
    key: str
    value: bytes
    secret_type: SecretType
    metadata: Dict[str, Any]
    version: int = 1


class VaultManager:
    """
    Vault Manager
    =============
    
    Unified interface for secrets management.
    
    Production: HashiCorp Vault
    Development: Encrypted file storage with master password
    
    Security:
    - AES-256-GCM encryption for file storage
    - PBKDF2 key derivation with 600k iterations
    - Never logs plaintext secrets
    - Automatic key rotation support
    
    Usage:
        vault = VaultManager()
        vault.initialize()
        vault.store_secret("api_key", b"secret_value", SecretType.API_KEY)
        secret = vault.get_secret("api_key")
    """
    
    def __init__(
        self,
        vault_addr: Optional[str] = None,
        vault_token: Optional[str] = None,
        storage_path: Optional[str] = None,
        use_file_backend: bool = True
    ):
        """
        Initialize vault manager.
        
        Args:
            vault_addr: HashiCorp Vault address (production)
            vault_token: Vault authentication token
            storage_path: Path for encrypted file storage (dev)
            use_file_backend: Force file-based storage
        """
        self.vault_addr = vault_addr
        self.vault_token = vault_token
        self.use_file_backend = use_file_backend or (vault_addr is None)
        self.storage_path = storage_path or ".vault/amcis_secrets.enc"
        self._master_key: Optional[bytes] = None
        self._secrets_cache: Dict[str, Secret] = {}
        self.logger = structlog.get_logger("amcis.vault")
        
        self.logger.info("vault_manager_initialized",
                        backend="file" if self.use_file_backend else "hashicorp")
    
    def initialize(self, master_password: Optional[str] = None) -> bool:
        """
        Initialize vault.
        
        Args:
            master_password: Master password for file-based storage
            
        Returns:
            True if successful
        """
        if self.use_file_backend:
            return self._init_file_backend(master_password)
        else:
            return self._init_vault_backend()
    
    def _init_file_backend(self, master_password: Optional[str] = None) -> bool:
        """Initialize encrypted file-based storage."""
        try:
            # Get master password
            if master_password is None:
                # Check environment variable
                master_password = os.environ.get('AMCIS_VAULT_PASSWORD')
                
                if master_password is None:
                    # For demo purposes, use a default (NOT FOR PRODUCTION)
                    self.logger.warning("using_default_password_not_for_production")
                    master_password = "AMCIS_SALVAGE_MODE_DEMO_KEY"
            
            # Derive encryption key from password
            salt = self._get_or_create_salt()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA3_256(),
                length=32,
                salt=salt,
                iterations=600000,  # OWASP recommendation
                backend=default_backend()
            )
            self._master_key = kdf.derive(master_password.encode())
            
            # Ensure storage directory exists
            Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing secrets if any
            if Path(self.storage_path).exists():
                self._load_secrets()
            
            self.logger.info("file_vault_initialized",
                           path=self.storage_path,
                           salt_hash=hashlib.sha3_256(salt).hexdigest()[:16])
            return True
            
        except Exception as e:
            self.logger.error("failed_to_init_file_vault", error=str(e))
            return False
    
    def _init_vault_backend(self) -> bool:
        """Initialize HashiCorp Vault backend."""
        try:
            import hvac
            
            self.vault_client = hvac.Client(
                url=self.vault_addr,
                token=self.vault_token
            )
            
            if not self.vault_client.is_authenticated():
                self.logger.error("vault_authentication_failed")
                return False
            
            self.logger.info("vault_backend_initialized", addr=self.vault_addr)
            return True
            
        except ImportError:
            self.logger.error("hvac_not_installed_fallback_to_file")
            self.use_file_backend = True
            return self._init_file_backend()
        except Exception as e:
            self.logger.error("failed_to_init_vault", error=str(e))
            return False
    
    def _get_or_create_salt(self) -> bytes:
        """Get or create salt for key derivation."""
        # Ensure parent directory exists
        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        
        salt_path = str(Path(self.storage_path).parent / "salt.bin")
        
        if Path(salt_path).exists():
            with open(salt_path, 'rb') as f:
                return f.read()
        else:
            # Generate new salt
            salt = os.urandom(32)
            with open(salt_path, 'wb') as f:
                f.write(salt)
            # Set restrictive permissions
            os.chmod(salt_path, 0o600)
            return salt
    
    def _load_secrets(self):
        """Load secrets from encrypted file."""
        try:
            with open(self.storage_path, 'rb') as f:
                encrypted_data = f.read()
            
            if len(encrypted_data) < 28:  # Nonce (12) + minimum ciphertext
                return
            
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            
            aesgcm = AESGCM(self._master_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            data = json.loads(plaintext.decode())
            
            for key, value in data.items():
                self._secrets_cache[key] = Secret(
                    key=key,
                    value=base64.b64decode(value['value']),
                    secret_type=SecretType(value['type']),
                    metadata=value.get('metadata', {}),
                    version=value.get('version', 1)
                )
            
            self.logger.debug("secrets_loaded", count=len(self._secrets_cache))
            
        except Exception as e:
            self.logger.error("failed_to_load_secrets", error=str(e))
            self._secrets_cache = {}
    
    def _save_secrets(self) -> bool:
        """Save secrets to encrypted file."""
        try:
            # Prepare data
            data = {}
            for key, secret in self._secrets_cache.items():
                data[key] = {
                    'value': base64.b64encode(secret.value).decode(),
                    'type': secret.secret_type.value,
                    'metadata': secret.metadata,
                    'version': secret.version
                }
            
            plaintext = json.dumps(data).encode()
            
            # Encrypt
            nonce = os.urandom(12)
            aesgcm = AESGCM(self._master_key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)
            
            # Write
            with open(self.storage_path, 'wb') as f:
                f.write(nonce + ciphertext)
            
            # Set restrictive permissions
            os.chmod(self.storage_path, 0o600)
            
            return True
            
        except Exception as e:
            self.logger.error("failed_to_save_secrets", error=str(e))
            return False
    
    def store_secret(
        self,
        key: str,
        value: bytes,
        secret_type: SecretType,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Store secret in vault.
        
        Args:
            key: Secret identifier
            value: Secret value (bytes)
            secret_type: Type of secret
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            if self.use_file_backend:
                # Store in encrypted file
                secret = Secret(
                    key=key,
                    value=value,
                    secret_type=secret_type,
                    metadata=metadata or {}
                )
                
                # Check if updating existing
                if key in self._secrets_cache:
                    secret.version = self._secrets_cache[key].version + 1
                
                self._secrets_cache[key] = secret
                
                if self._save_secrets():
                    self.logger.info("secret_stored",
                                   key=key,
                                   type=secret_type.value,
                                   version=secret.version)
                    return True
                return False
            
            else:
                # Store in HashiCorp Vault
                import hvac
                
                path = f"secret/amcis/{key}"
                self.vault_client.secrets.kv.v2.create_or_update_secret(
                    path=path,
                    secret={
                        'value': base64.b64encode(value).decode(),
                        'type': secret_type.value,
                        'metadata': metadata or {}
                    }
                )
                
                self.logger.info("secret_stored_in_vault",
                               key=key, type=secret_type.value)
                return True
                
        except Exception as e:
            self.logger.error("failed_to_store_secret", key=key, error=str(e))
            return False
    
    def get_secret(self, key: str) -> Optional[Secret]:
        """
        Retrieve secret from vault.
        
        Args:
            key: Secret identifier
            
        Returns:
            Secret or None
        """
        try:
            if self.use_file_backend:
                secret = self._secrets_cache.get(key)
                if secret:
                    self.logger.debug("secret_retrieved", key=key, 
                                    type=secret.secret_type.value)
                return secret
            
            else:
                import hvac
                
                path = f"secret/amcis/{key}"
                response = self.vault_client.secrets.kv.v2.read_secret_version(
                    path=path
                )
                
                data = response['data']['data']
                return Secret(
                    key=key,
                    value=base64.b64decode(data['value']),
                    secret_type=SecretType(data['type']),
                    metadata=data.get('metadata', {})
                )
                
        except Exception as e:
            self.logger.error("failed_to_get_secret", key=key, error=str(e))
            return None
    
    def delete_secret(self, key: str) -> bool:
        """Delete secret from vault."""
        try:
            if self.use_file_backend:
                if key in self._secrets_cache:
                    del self._secrets_cache[key]
                    return self._save_secrets()
                return True
            else:
                import hvac
                
                path = f"secret/amcis/{key}"
                self.vault_client.secrets.kv.v2.delete_metadata_and_all_versions(
                    path=path
                )
                return True
                
        except Exception as e:
            self.logger.error("failed_to_delete_secret", key=key, error=str(e))
            return False
    
    def rotate_key(self, key: str, new_value: bytes) -> bool:
        """Rotate a secret to new value."""
        secret = self.get_secret(key)
        if secret:
            return self.store_secret(key, new_value, secret.secret_type, 
                                   secret.metadata)
        return False
    
    def list_secrets(self, prefix: str = "") -> list:
        """List all secret keys."""
        if self.use_file_backend:
            return [k for k in self._secrets_cache.keys() if k.startswith(prefix)]
        else:
            # Would need Vault list permission
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get vault status."""
        if self.use_file_backend:
            return {
                'backend': 'encrypted_file',
                'path': self.storage_path,
                'secrets_count': len(self._secrets_cache),
                'master_key_loaded': self._master_key is not None
            }
        else:
            return {
                'backend': 'hashicorp_vault',
                'addr': self.vault_addr,
                'authenticated': self.vault_client.is_authenticated() 
                                if hasattr(self, 'vault_client') else False
            }
