"""
AMCIS Q-SEC CORE - Commercial License Management
================================================

Enterprise-grade license enforcement with hardware fingerprinting,
cryptographic validation, and tamper detection.

Copyright (c) 2026 AMCIS Security Corporation
All rights reserved. Commercial use requires valid license.
"""

import hashlib
import hmac
import json
import platform
import secrets
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Optional, List, Set, Tuple
import structlog


class LicenseTier(Enum):
    """Commercial license tiers."""
    EVALUATION = auto()      # 30-day trial
    STARTER = auto()         # SMB
    PROFESSIONAL = auto()    # Mid-market
    ENTERPRISE = auto()      # Large enterprise
    STRATEGIC = auto()       # Global/custom
    GOVERNMENT = auto()      # Classified/air-gapped


class LicenseStatus(Enum):
    """License validation states."""
    VALID = auto()
    EXPIRED = auto()
    REVOKED = auto()
    HARDWARE_MISMATCH = auto()
    TAMPERED = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class LicenseMetadata:
    """Immutable license metadata."""
    license_id: str
    customer_id: str
    tier: LicenseTier
    issued_at: float
    expires_at: float
    max_endpoints: int
    modules: Tuple[str, ...]
    features: Dict[str, bool]
    hardware_hash: str
    signature: str
    
    def to_dict(self) -> Dict:
        return {
            'license_id': self.license_id,
            'customer_id': self.customer_id,
            'tier': self.tier.name,
            'issued_at': self.issued_at,
            'expires_at': self.expires_at,
            'max_endpoints': self.max_endpoints,
            'modules': list(self.modules),
            'features': self.features,
            'hardware_hash': self.hardware_hash,
            'signature': self.signature
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LicenseMetadata':
        return cls(
            license_id=data['license_id'],
            customer_id=data['customer_id'],
            tier=LicenseTier[data['tier']],
            issued_at=data['issued_at'],
            expires_at=data['expires_at'],
            max_endpoints=data['max_endpoints'],
            modules=tuple(data['modules']),
            features=data['features'],
            hardware_hash=data['hardware_hash'],
            signature=data['signature']
        )


class HardwareFingerprint:
    """
    Device hardware fingerprinting for license binding.
    Creates unique device identifier from system characteristics.
    """
    
    __slots__ = ('logger', '_cached_fingerprint')
    
    def __init__(self):
        self.logger = structlog.get_logger("amcis.license.hardware")
        self._cached_fingerprint: Optional[str] = None
    
    def generate(self, salt: Optional[str] = None) -> str:
        """Generate hardware-bound fingerprint."""
        if self._cached_fingerprint:
            return self._cached_fingerprint
        
        # Collect system characteristics
        components = [
            platform.node(),
            platform.machine(),
            platform.processor() or "unknown",
            platform.system(),
            platform.release(),
            str(platform.architecture()),
            salt or ""
        ]
        
        # Create stable hash
        combined = "|".join(components).encode('utf-8')
        fingerprint = hashlib.sha3_256(combined).hexdigest()[:32]
        
        self._cached_fingerprint = fingerprint
        self.logger.debug("hardware_fingerprint_generated", fingerprint=fingerprint[:8])
        return fingerprint
    
    def verify(self, stored_hash: str, tolerance: int = 0) -> bool:
        """
        Verify current hardware against stored fingerprint.
        
        Args:
            stored_hash: Previously stored hardware hash
            tolerance: Number of component changes allowed (0 = exact match)
        """
        current = self.generate()
        if tolerance == 0:
            return hmac.compare_digest(current, stored_hash)
        
        # Calculate similarity for fuzzy matching
        matches = sum(1 for a, b in zip(current, stored_hash) if a == b)
        similarity = matches / len(current)
        return similarity >= (1.0 - (tolerance * 0.1))


class LicenseManager:
    """
    AMCIS Commercial License Manager
    ================================
    
    Manages license lifecycle, validation, and enforcement.
    All operations are cryptographically secured.
    """
    
    # License signing key - In production, load from HSM
    _SIGNING_KEY = b"fcfc8548f089e4c2d9ff4994aae59eff39aa7e99f78443c49688cceed5b346be"
    
    # License storage
    _LICENSE_PATH = Path.home() / ".amcis" / "license.dat"
    
    __slots__ = ('logger', '_hardware', '_cached_license', '_endpoints_count')
    
    def __init__(self):
        self.logger = structlog.get_logger("amcis.license.manager")
        self._hardware = HardwareFingerprint()
        self._cached_license: Optional[LicenseMetadata] = None
        self._endpoints_count: int = 0
    
    def generate_license(
        self,
        customer_id: str,
        tier: LicenseTier,
        duration_days: int,
        max_endpoints: int,
        modules: List[str],
        custom_features: Optional[Dict[str, bool]] = None
    ) -> LicenseMetadata:
        """
        Generate a new commercial license.
        
        Args:
            customer_id: Unique customer identifier
            tier: License tier (STARTER, ENTERPRISE, etc.)
            duration_days: Validity period
            max_endpoints: Maximum allowed endpoints
            modules: Enabled module names
            custom_features: Optional feature flags
            
        Returns:
            Signed license metadata
        """
        license_id = f"AMC-{secrets.token_hex(8).upper()}"
        issued_at = time.time()
        expires_at = issued_at + (duration_days * 86400)
        
        # Get hardware hash (for device-bound licenses)
        hardware_hash = self._hardware.generate()
        
        # Default features by tier
        features = self._get_default_features(tier)
        if custom_features:
            features.update(custom_features)
        
        # Create unsigned metadata
        metadata = LicenseMetadata(
            license_id=license_id,
            customer_id=customer_id,
            tier=tier,
            issued_at=issued_at,
            expires_at=expires_at,
            max_endpoints=max_endpoints,
            modules=tuple(modules),
            features=features,
            hardware_hash=hardware_hash,
            signature=""  # Will be filled
        )
        
        # Sign the license
        signature = self._sign_license(metadata)
        
        # Return signed license
        signed_metadata = LicenseMetadata(
            license_id=license_id,
            customer_id=customer_id,
            tier=tier,
            issued_at=issued_at,
            expires_at=expires_at,
            max_endpoints=max_endpoints,
            modules=tuple(modules),
            features=features,
            hardware_hash=hardware_hash,
            signature=signature
        )
        
        self.logger.info(
            "license_generated",
            license_id=license_id,
            customer_id=customer_id,
            tier=tier.name
        )
        
        return signed_metadata
    
    def validate(self, license_data: Optional[LicenseMetadata] = None) -> Tuple[LicenseStatus, Optional[str]]:
        """
        Validate license status.
        
        Returns:
            Tuple of (status, error_message)
        """
        metadata = license_data or self._load_stored_license()
        
        if not metadata:
            return LicenseStatus.UNKNOWN, "No license found"
        
        # Verify signature
        if not self._verify_signature(metadata):
            self.logger.critical("license_tampering_detected", license_id=metadata.license_id)
            return LicenseStatus.TAMPERED, "License has been tampered with"
        
        # Check expiration
        if time.time() > metadata.expires_at:
            self.logger.warning("license_expired", license_id=metadata.license_id)
            return LicenseStatus.EXPIRED, f"License expired on {datetime.fromtimestamp(metadata.expires_at)}"
        
        # Verify hardware binding
        if not self._hardware.verify(metadata.hardware_hash):
            self.logger.error("hardware_mismatch", license_id=metadata.license_id)
            return LicenseStatus.HARDWARE_MISMATCH, "License bound to different hardware"
        
        # Check revocation list
        if self._is_revoked(metadata.license_id):
            return LicenseStatus.REVOKED, "License has been revoked"
        
        self._cached_license = metadata
        return LicenseStatus.VALID, None
    
    def check_module_access(self, module_name: str) -> bool:
        """Check if current license allows access to module."""
        status, _ = self.validate()
        if status != LicenseStatus.VALID:
            return False
        
        if not self._cached_license:
            return False
        
        return module_name in self._cached_license.modules
    
    def check_endpoint_limit(self, current_count: int) -> bool:
        """Check if within endpoint limit."""
        self._endpoints_count = current_count
        
        status, _ = self.validate()
        if status != LicenseStatus.VALID:
            return False
        
        if not self._cached_license:
            return False
        
        return current_count <= self._cached_license.max_endpoints
    
    def get_feature(self, feature_name: str) -> bool:
        """Check if feature is enabled."""
        status, _ = self.validate()
        if status != LicenseStatus.VALID:
            return False
        
        if not self._cached_license:
            return False
        
        return self._cached_license.features.get(feature_name, False)
    
    def export_license(self, metadata: LicenseMetadata, path: Optional[Path] = None) -> Path:
        """Export license to file."""
        target_path = path or self._LICENSE_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Encrypt before storing
        encrypted = self._encrypt_license(metadata)
        
        with open(target_path, 'wb') as f:
            f.write(encrypted)
        
        # Set restrictive permissions
        import stat
        target_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        
        self.logger.info("license_exported", path=str(target_path))
        return target_path
    
    def _sign_license(self, metadata: LicenseMetadata) -> str:
        """Cryptographically sign license metadata."""
        # Create canonical representation
        data = f"{metadata.license_id}:{metadata.customer_id}:{metadata.issued_at}:{metadata.expires_at}:{metadata.hardware_hash}"
        
        # HMAC-SHA3-256 signature
        signature = hmac.new(
            self._SIGNING_KEY,
            data.encode(),
            hashlib.sha3_256
        ).hexdigest()
        
        return signature
    
    def _verify_signature(self, metadata: LicenseMetadata) -> bool:
        """Verify license signature."""
        expected = self._sign_license(metadata)
        return hmac.compare_digest(expected, metadata.signature)
    
    def _load_stored_license(self) -> Optional[LicenseMetadata]:
        """Load license from storage."""
        if not self._LICENSE_PATH.exists():
            return None
        
        try:
            with open(self._LICENSE_PATH, 'rb') as f:
                encrypted = f.read()
            
            decrypted = self._decrypt_license(encrypted)
            return LicenseMetadata.from_dict(json.loads(decrypted))
        except Exception as e:
            self.logger.error("license_load_failed", error=str(e))
            return None
    
    def _encrypt_license(self, metadata: LicenseMetadata) -> bytes:
        """Encrypt license for storage."""
        # In production, use proper encryption (Fernet, AES-GCM)
        # This is simplified for demonstration
        data = json.dumps(metadata.to_dict()).encode()
        
        # XOR with derived key (NOT for production - use proper crypto)
        key = hashlib.sha3_256(self._SIGNING_KEY).digest()
        encrypted = bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))
        
        return encrypted
    
    def _decrypt_license(self, encrypted: bytes) -> str:
        """Decrypt license from storage."""
        key = hashlib.sha3_256(self._SIGNING_KEY).digest()
        decrypted = bytes(a ^ b for a, b in zip(encrypted, key * (len(encrypted) // len(key) + 1)))
        return decrypted.decode()
    
    def _is_revoked(self, license_id: str) -> bool:
        """Check if license is in revocation list."""
        # In production, check CRL or OCSP
        revoked_list = self._load_revocation_list()
        return license_id in revoked_list
    
    def _load_revocation_list(self) -> Set[str]:
        """Load certificate revocation list."""
        # Stub - would fetch from server
        return set()
    
    def _get_default_features(self, tier: LicenseTier) -> Dict[str, bool]:
        """Get default features for license tier."""
        base_features = {
            'pqc_crypto': False,
            'ai_security': False,
            'advanced_edr': False,
            'waf': False,
            'dlp': False,
            'compliance': False,
            'soar': False,
            'threat_intel': False,
            'biometrics': False,
            'support_24x7': False,
            'dedicated_tam': False,
            'source_code': False
        }
        
        tier_features = {
            LicenseTier.EVALUATION: {
                'pqc_crypto': True, 'ai_security': True, 'advanced_edr': True,
                'waf': True, 'dlp': False, 'compliance': False, 'soar': False,
                'threat_intel': True, 'biometrics': False, 'support_24x7': False
            },
            LicenseTier.STARTER: {
                'pqc_crypto': False, 'ai_security': False, 'advanced_edr': True,
                'waf': True, 'dlp': False, 'compliance': False, 'soar': False,
                'threat_intel': True, 'biometrics': False, 'support_24x7': False
            },
            LicenseTier.PROFESSIONAL: {
                'pqc_crypto': True, 'ai_security': True, 'advanced_edr': True,
                'waf': True, 'dlp': True, 'compliance': True, 'soar': False,
                'threat_intel': True, 'biometrics': False, 'support_24x7': True
            },
            LicenseTier.ENTERPRISE: {
                'pqc_crypto': True, 'ai_security': True, 'advanced_edr': True,
                'waf': True, 'dlp': True, 'compliance': True, 'soar': True,
                'threat_intel': True, 'biometrics': True, 'support_24x7': True,
                'dedicated_tam': True
            },
            LicenseTier.STRATEGIC: {
                'pqc_crypto': True, 'ai_security': True, 'advanced_edr': True,
                'waf': True, 'dlp': True, 'compliance': True, 'soar': True,
                'threat_intel': True, 'biometrics': True, 'support_24x7': True,
                'dedicated_tam': True, 'source_code': True
            },
            LicenseTier.GOVERNMENT: {
                'pqc_crypto': True, 'ai_security': True, 'advanced_edr': True,
                'waf': True, 'dlp': True, 'compliance': True, 'soar': True,
                'threat_intel': True, 'biometrics': True, 'support_24x7': True,
                'dedicated_tam': True, 'source_code': True
            }
        }
        
        base_features.update(tier_features.get(tier, {}))
        return base_features


# Global license manager instance
_license_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """Get or create global license manager."""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


def require_license(module: Optional[str] = None, feature: Optional[str] = None):
    """Decorator to require valid license for function."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            manager = get_license_manager()
            status, error = manager.validate()
            
            if status != LicenseStatus.VALID:
                raise RuntimeError(f"License validation failed: {error}")
            
            if module and not manager.check_module_access(module):
                raise RuntimeError(f"Module '{module}' not licensed")
            
            if feature and not manager.get_feature(feature):
                raise RuntimeError(f"Feature '{feature}' not available in current license")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
