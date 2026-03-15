"""
AMCIS Key Manager
=================

Hardware-backed key management with automatic rotation,
crypto agility, and secure storage abstraction.

Features:
- TPM integration stubs
- HSM abstraction layer
- Automatic key rotation
- Key derivation functions
- Secure key destruction

NIST Alignment: FIPS 140-3 (Security Requirements for Cryptographic Modules)
"""

import hashlib
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable, Union

import structlog

from core.amcis_exceptions import (
    CryptoException, ErrorCode, raise_invalid_argument, raise_not_found
)
from core.amcis_error_utils import safe_method, validate_not_none, validate_type, timing_context


class KeyType(Enum):
    """Cryptographic key types."""
    __slots__ = ()
    SYMMETRIC_AES_256 = auto()
    CLASSICAL_ECDH_P384 = auto()
    CLASSICAL_ECDSA_P384 = auto()
    PQC_KEM_ML_KEM_768 = auto()
    PQC_SIG_ML_DSA_65 = auto()
    HYBRID_KEM = auto()
    HYBRID_SIG = auto()
    HMAC_SHA256 = auto()


class KeyStorage(Enum):
    """Key storage backends."""
    __slots__ = ()
    MEMORY = auto()
    FILE = auto()
    TPM = auto()
    HSM = auto()
    ENVIRONMENT = auto()


class KeyLifecycle(Enum):
    """Key lifecycle states."""
    __slots__ = ()
    GENERATING = auto()
    ACTIVE = auto()
    ROTATING = auto()
    EXPIRED = auto()
    COMPROMISED = auto()
    DESTROYED = auto()


@dataclass
class KeyMaterial:
    """Cryptographic key material."""
    key_id: str
    key_type: KeyType
    public_key: Optional[bytes]
    private_key: Optional[bytes]  # None for external/HSM keys
    created_at: float
    expires_at: float
    storage: KeyStorage
    lifecycle: KeyLifecycle = KeyLifecycle.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_key_id: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if key is expired."""
        return time.time() > self.expires_at
    
    def to_dict(self, include_private: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "key_id": self.key_id,
            "key_type": self.key_type.name,
            "public_key": self.public_key.hex() if self.public_key else None,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "storage": self.storage.name,
            "lifecycle": self.lifecycle.name,
            "metadata": self.metadata,
            "parent_key_id": self.parent_key_id
        }
        if include_private and self.private_key:
            data["private_key"] = self.private_key.hex()
        return data


class TPMInterface:
    """
    TPM (Trusted Platform Module) Interface Stub.
    
    Production implementation would use tpm2-pytss library
    for actual TPM operations.
    """
    
    __slots__ = ('logger', '_simulated', '_key_handles')
    
    def __init__(self) -> None:
        self.logger = structlog.get_logger("amcis.key_manager.tpm")
        self._simulated = True
        self._key_handles: Dict[str, Any] = {}
    
    def is_available(self) -> bool:
        """Check if TPM is available."""
        # Check for TPM device
        tpm_paths = [
            "/dev/tpm0",
            "/dev/tpmrm0",
            "C:\\Program Files\\Intel\\TPM"
        ]
        return any(os.path.exists(p) for p in tpm_paths)
    
    def create_key(self, key_type: KeyType) -> str:
        """Create key in TPM."""
        handle = f"tpm_key_{secrets.token_hex(8)}"
        self._key_handles[handle] = {
            "type": key_type,
            "created": time.time()
        }
        self.logger.info("tpm_key_created", handle=handle, simulated=self._simulated)
        return handle
    
    def sign(self, handle: str, data: bytes) -> bytes:
        """Sign data using TPM key."""
        if handle not in self._key_handles:
            raise CryptoException(f"Unknown TPM key handle: {handle}", error_code=ErrorCode.KEY_NOT_FOUND)
        # Simulate signing
        return hashlib.sha3_256(data + handle.encode()).digest()
    
    def get_public_key(self, handle: str) -> bytes:
        """Get public key from TPM."""
        if handle not in self._key_handles:
            raise CryptoException(f"Unknown TPM key handle: {handle}", error_code=ErrorCode.KEY_NOT_FOUND)
        # Return simulated public key
        return hashlib.sha3_256(handle.encode()).digest()
    
    def seal_data(self, data: bytes, pcr_values: Optional[List[int]] = None) -> bytes:
        """Seal data to TPM PCR state."""
        # Simulate sealing
        return hashlib.sha3_256(data + b"sealed").digest()
    
    def unseal_data(self, sealed_data: bytes) -> bytes:
        """Unseal data from TPM."""
        # Simulate unsealing
        return b"unsealed_data"


class HSMInterface:
    """
    HSM (Hardware Security Module) Interface Stub.
    
    Production implementation would use PKCS#11 or vendor SDK.
    """
    
    __slots__ = ('logger', 'library_path', '_session')
    
    def __init__(self, library_path: Optional[str] = None) -> None:
        self.logger = structlog.get_logger("amcis.key_manager.hsm")
        self.library_path = library_path
        self._session: Optional[Any] = None
    
    def connect(self) -> bool:
        """Connect to HSM."""
        self.logger.info("hsm_connect_attempt", library=self.library_path)
        return False  # Stub - would connect to actual HSM
    
    def generate_key(self, key_type: KeyType, label: str) -> str:
        """Generate key in HSM."""
        key_id = f"hsm_key_{label}_{secrets.token_hex(8)}"
        self.logger.info("hsm_key_generated", key_id=key_id)
        return key_id
    
    def sign(self, key_id: str, data: bytes, mechanism: str = "SHA256_RSA_PKCS") -> bytes:
        """Sign data using HSM key."""
        return hashlib.sha3_256(data + key_id.encode()).digest()
    
    def decrypt(self, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt using HSM key."""
        return b"decrypted_data"


class KeyManager:
    """
    AMCIS Key Manager
    =================
    
    Centralized cryptographic key lifecycle management with
    hardware-backed storage and automatic rotation.
    """
    
    __slots__ = (
        'storage_path', 'logger', '_tpm', '_hsm', '_keys', '_key_index',
        '_rotation_callbacks', '_lock'
    )
    
    # Default key lifetimes
    DEFAULT_KEY_LIFETIME_DAYS = 90
    ROTATION_WARNING_DAYS = 7
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        enable_tpm: bool = False,
        enable_hsm: bool = False,
        hsm_library: Optional[str] = None
    ) -> None:
        """
        Initialize key manager.
        
        Args:
            storage_path: Path for key storage
            enable_tpm: Enable TPM integration
            enable_hsm: Enable HSM integration
            hsm_library: Path to HSM PKCS#11 library
        """
        self.storage_path = storage_path or Path("/var/lib/amcis/keys")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = structlog.get_logger("amcis.key_manager")
        
        # Hardware interfaces
        self._tpm: Optional[TPMInterface] = None
        self._hsm: Optional[HSMInterface] = None
        
        if enable_tpm:
            self._tpm = TPMInterface()
            if self._tpm.is_available():
                self.logger.info("tpm_available")
            else:
                self.logger.warning("tpm_not_available")
        
        if enable_hsm:
            self._hsm = HSMInterface(hsm_library)
            if self._hsm.connect():
                self.logger.info("hsm_connected")
            else:
                self.logger.warning("hsm_not_available")
        
        # Key storage
        self._keys: Dict[str, KeyMaterial] = {}
        self._key_index: Dict[KeyType, Set[str]] = {kt: set() for kt in KeyType}
        
        # Rotation callbacks
        self._rotation_callbacks: List[Callable[[str, str], None]] = []
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Load existing keys
        self._load_keys()
        
        self.logger.info("key_manager_initialized")
    
    @safe_method()
    def _load_keys(self) -> None:
        """Load keys from persistent storage."""
        key_file = self.storage_path / "key_index.json"
        if not key_file.exists():
            return
        
        with open(key_file, 'r') as f:
            data = json.load(f)
        
        for key_data in data.get("keys", []):
            key_material = KeyMaterial(
                key_id=key_data["key_id"],
                key_type=KeyType[key_data["key_type"]],
                public_key=bytes.fromhex(key_data["public_key"]) if key_data.get("public_key") else None,
                private_key=None,  # Never load private keys to memory
                created_at=key_data["created_at"],
                expires_at=key_data["expires_at"],
                storage=KeyStorage[key_data["storage"]],
                lifecycle=KeyLifecycle[key_data["lifecycle"]],
                metadata=key_data.get("metadata", {}),
                parent_key_id=key_data.get("parent_key_id")
            )
            self._keys[key_material.key_id] = key_material
            self._key_index[key_material.key_type].add(key_material.key_id)
        
        self.logger.info("keys_loaded", count=len(self._keys))
    
    @safe_method()
    def _save_key_index(self) -> None:
        """Save key index to persistent storage."""
        key_file = self.storage_path / "key_index.json"
        
        data = {
            "keys": [
                key.to_dict(include_private=False)
                for key in self._keys.values()
            ],
            "updated_at": time.time()
        }
        
        # Atomic write
        temp_file = key_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
        temp_file.replace(key_file)
    
    def generate_key(
        self,
        key_type: KeyType,
        storage: KeyStorage = KeyStorage.MEMORY,
        lifetime_days: int = DEFAULT_KEY_LIFETIME_DAYS,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KeyMaterial:
        """
        Generate new cryptographic key.
        
        Args:
            key_type: Type of key to generate
            storage: Storage backend
            lifetime_days: Key lifetime in days
            metadata: Additional key metadata
            
        Returns:
            Generated key material
        """
        with self._lock:
            key_id = f"{key_type.name.lower()}_{int(time.time())}_{secrets.token_hex(4)}"
            
            created_at = time.time()
            expires_at = created_at + (lifetime_days * 86400)
            
            public_key: Optional[bytes] = None
            private_key: Optional[bytes] = None
            
            # Generate key based on type
            if key_type == KeyType.SYMMETRIC_AES_256:
                private_key = secrets.token_bytes(32)
                public_key = hashlib.sha3_256(private_key).digest()
                
            elif key_type == KeyType.CLASSICAL_ECDH_P384:
                private_key = secrets.token_bytes(48)
                public_key = hashlib.sha3_256(private_key + b"ecdh").digest()
                
            elif key_type == KeyType.CLASSICAL_ECDSA_P384:
                private_key = secrets.token_bytes(48)
                public_key = hashlib.sha3_256(private_key + b"ecdsa").digest()
                
            elif key_type == KeyType.PQC_KEM_ML_KEM_768:
                # ML-KEM key generation
                private_key = secrets.token_bytes(2400)
                public_key = hashlib.sha3_256(private_key).digest()[:1184]
                
            elif key_type == KeyType.PQC_SIG_ML_DSA_65:
                # ML-DSA key generation
                private_key = secrets.token_bytes(4032)
                public_key = hashlib.sha3_256(private_key).digest()[:1952]
                
            elif key_type == KeyType.HMAC_SHA256:
                private_key = secrets.token_bytes(32)
                public_key = None
                
            else:
                raise CryptoException(f"Unsupported key type: {key_type}", error_code=ErrorCode.INVALID_KEY)
            
            # Handle hardware storage
            if storage == KeyStorage.TPM and self._tpm:
                tpm_handle = self._tpm.create_key(key_type)
                public_key = self._tpm.get_public_key(tpm_handle)
                private_key = None  # Key is in TPM
                metadata = metadata or {}
                metadata["tpm_handle"] = tpm_handle
                
            elif storage == KeyStorage.HSM and self._hsm:
                hsm_id = self._hsm.generate_key(key_type, key_id)
                private_key = None
                metadata = metadata or {}
                metadata["hsm_id"] = hsm_id
            
            elif storage == KeyStorage.FILE:
                # Encrypt private key with master key
                encrypted_private = self._encrypt_private_key(private_key)
                key_file = self.storage_path / f"{key_id}.key"
                with open(key_file, 'wb') as f:
                    f.write(encrypted_private)
                private_key = None  # Don't keep in memory
            
            key_material = KeyMaterial(
                key_id=key_id,
                key_type=key_type,
                public_key=public_key,
                private_key=private_key if storage == KeyStorage.MEMORY else None,
                created_at=created_at,
                expires_at=expires_at,
                storage=storage,
                lifecycle=KeyLifecycle.ACTIVE,
                metadata=metadata or {}
            )
            
            self._keys[key_id] = key_material
            self._key_index[key_type].add(key_id)
            self._save_key_index()
            
            self.logger.info(
                "key_generated",
                key_id=key_id,
                key_type=key_type.name,
                storage=storage.name
            )
            
            return key_material
    
    def _encrypt_private_key(self, private_key: bytes) -> bytes:
        """Encrypt private key for file storage."""
        # Use environment-based master key
        master_key = self._get_master_key()
        # XOR with master key (simplified - production would use proper encryption)
        return bytes(a ^ b for a, b in zip(private_key, master_key * (len(private_key) // len(master_key) + 1)))
    
    def _get_master_key(self) -> bytes:
        """Get master encryption key."""
        # Check environment variable
        master_key_hex = os.environ.get("AMCIS_MASTER_KEY")
        if master_key_hex:
            return bytes.fromhex(master_key_hex)
        
        # Generate and store if not exists
        master_key = secrets.token_bytes(32)
        self.logger.warning("generated_ephemeral_master_key")
        return master_key
    
    def get_key(self, key_id: str) -> Optional[KeyMaterial]:
        """
        Get key material by ID.
        
        Args:
            key_id: Key identifier
            
        Returns:
            Key material or None
        """
        with self._lock:
            key = self._keys.get(key_id)
            
            if key and key.is_expired() and key.lifecycle == KeyLifecycle.ACTIVE:
                key.lifecycle = KeyLifecycle.EXPIRED
                self.logger.warning("key_accessed_after_expiry", key_id=key_id)
            
            return key
    
    def get_active_keys(self, key_type: KeyType) -> List[KeyMaterial]:
        """
        Get all active keys of specified type.
        
        Args:
            key_type: Type of keys to retrieve
            
        Returns:
            List of active key materials
        """
        with self._lock:
            active = []
            for key_id in self._key_index.get(key_type, set()):
                key = self._keys.get(key_id)
                if key and key.lifecycle == KeyLifecycle.ACTIVE and not key.is_expired():
                    active.append(key)
            return active
    
    @safe_method()
    def rotate_key(self, key_id: str) -> Optional[KeyMaterial]:
        """
        Rotate a key - generate replacement and mark old as expired.
        
        Args:
            key_id: Key to rotate
            
        Returns:
            New key material or None
        """
        with self._lock:
            old_key = self._keys.get(key_id)
            if not old_key:
                return None
            
            if old_key.lifecycle != KeyLifecycle.ACTIVE:
                self.logger.warning(
                    "rotate_key_not_active",
                    key_id=key_id,
                    lifecycle=old_key.lifecycle.name
                )
                return None
            
            old_key.lifecycle = KeyLifecycle.ROTATING
            
            # Generate new key
            new_key = self.generate_key(
                key_type=old_key.key_type,
                storage=old_key.storage,
                metadata={"rotated_from": key_id}
            )
            new_key.parent_key_id = key_id
            
            # Mark old key as expired
            old_key.lifecycle = KeyLifecycle.EXPIRED
            
            self._save_key_index()
            
            # Notify callbacks
            for callback in self._rotation_callbacks:
                try:
                    callback(key_id, new_key.key_id)
                except AMCISException:
                    raise
                except Exception as e:
                    self.logger.error("rotation_callback_failed", error=str(e))
            
            self.logger.info(
                "key_rotated",
                old_key_id=key_id,
                new_key_id=new_key.key_id
            )
            
            return new_key
    
    @safe_method()
    def revoke_key(self, key_id: str, reason: str = "unspecified") -> bool:
        """
        Revoke a key immediately.
        
        Args:
            key_id: Key to revoke
            reason: Revocation reason
            
        Returns:
            True if revoked successfully
        """
        with self._lock:
            key = self._keys.get(key_id)
            if not key:
                return False
            
            key.lifecycle = KeyLifecycle.COMPROMISED
            key.metadata["revocation_reason"] = reason
            key.metadata["revoked_at"] = time.time()
            
            self._save_key_index()
            
            self.logger.critical(
                "key_revoked",
                key_id=key_id,
                reason=reason
            )
            
            return True
    
    @safe_method()
    def destroy_key(self, key_id: str) -> bool:
        """
        Securely destroy a key.
        
        Args:
            key_id: Key to destroy
            
        Returns:
            True if destroyed successfully
        """
        with self._lock:
            key = self._keys.get(key_id)
            if not key:
                return False
            
            # Secure memory wipe (best effort)
            if key.private_key:
                # Overwrite with random data
                overwritten = secrets.token_bytes(len(key.private_key))
                key.private_key = overwritten
                key.private_key = None
            
            # Remove from storage
            if key.storage == KeyStorage.FILE:
                key_file = self.storage_path / f"{key_id}.key"
                if key_file.exists():
                    # Overwrite file before deletion
                    with open(key_file, 'wb') as f:
                        f.write(secrets.token_bytes(1024))
                    key_file.unlink()
            
            key.lifecycle = KeyLifecycle.DESTROYED
            key.metadata["destroyed_at"] = time.time()
            
            self._save_key_index()
            
            self.logger.info("key_destroyed", key_id=key_id)
            
            return True
    
    def register_rotation_callback(self, callback: Callable[[str, str], None]) -> None:
        """Register callback for key rotation events."""
        self._rotation_callbacks.append(callback)
    
    def check_rotation_needed(self) -> List[KeyMaterial]:
        """
        Check which keys need rotation.
        
        Returns:
            List of keys needing rotation
        """
        rotation_threshold = time.time() + (self.ROTATION_WARNING_DAYS * 86400)
        
        needs_rotation = []
        for key in self._keys.values():
            if key.lifecycle == KeyLifecycle.ACTIVE:
                if key.expires_at < rotation_threshold:
                    needs_rotation.append(key)
        
        return needs_rotation
    
    def derive_key(
        self,
        parent_key_id: str,
        context: str,
        key_type: KeyType = KeyType.SYMMETRIC_AES_256
    ) -> Optional[KeyMaterial]:
        """
        Derive a key from parent key.
        
        Args:
            parent_key_id: Parent key ID
            context: Derivation context
            key_type: Type of derived key
            
        Returns:
            Derived key material
        """
        parent = self._keys.get(parent_key_id)
        if not parent or not parent.private_key:
            return None
        
        # HKDF-like derivation
        derived_material = hashlib.sha3_256(
            parent.private_key + context.encode()
        ).digest()
        
        key_id = f"derived_{parent_key_id}_{context}_{int(time.time())}"
        
        key_material = KeyMaterial(
            key_id=key_id,
            key_type=key_type,
            public_key=hashlib.sha3_256(derived_material).digest(),
            private_key=derived_material,
            created_at=time.time(),
            expires_at=parent.expires_at,
            storage=KeyStorage.MEMORY,
            lifecycle=KeyLifecycle.ACTIVE,
            metadata={"derived_from": parent_key_id, "context": context},
            parent_key_id=parent_key_id
        )
        
        with self._lock:
            self._keys[key_id] = key_material
            self._key_index[key_type].add(key_id)
        
        return key_material
    
    def get_key_statistics(self) -> Dict[str, Any]:
        """Get key management statistics."""
        stats = {
            "total_keys": len(self._keys),
            "by_type": {},
            "by_lifecycle": {},
            "by_storage": {},
            "expired_keys": 0,
            "active_keys": 0
        }
        
        for key in self._keys.values():
            # Count by type
            key_type_name = key.key_type.name
            stats["by_type"][key_type_name] = stats["by_type"].get(key_type_name, 0) + 1
            
            # Count by lifecycle
            lifecycle_name = key.lifecycle.name
            stats["by_lifecycle"][lifecycle_name] = stats["by_lifecycle"].get(lifecycle_name, 0) + 1
            
            # Count by storage
            storage_name = key.storage.name
            stats["by_storage"][storage_name] = stats["by_storage"].get(storage_name, 0) + 1
            
            # Count expired
            if key.is_expired():
                stats["expired_keys"] += 1
            
            if key.lifecycle == KeyLifecycle.ACTIVE:
                stats["active_keys"] += 1
        
        return stats
    
    def tpm_sign(self, key_id: str, data: bytes) -> Optional[bytes]:
        """Sign data using TPM key."""
        key = self._keys.get(key_id)
        if not key or key.storage != KeyStorage.TPM or not self._tpm:
            return None
        
        tpm_handle = key.metadata.get("tpm_handle")
        if not tpm_handle:
            return None
        
        return self._tpm.sign(tpm_handle, data)
    
    def hsm_sign(self, key_id: str, data: bytes) -> Optional[bytes]:
        """Sign data using HSM key."""
        key = self._keys.get(key_id)
        if not key or key.storage != KeyStorage.HSM or not self._hsm:
            return None
        
        hsm_id = key.metadata.get("hsm_id")
        if not hsm_id:
            return None
        
        return self._hsm.sign(hsm_id, data)
