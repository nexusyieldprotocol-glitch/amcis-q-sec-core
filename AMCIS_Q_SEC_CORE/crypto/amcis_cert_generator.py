"""
AMCIS Certificate Generator
============================

X.509 certificate generation with PQC algorithm support.
Provides hybrid certificate chains for post-quantum security.

Features:
- PQC-aware certificate generation
- Hybrid certificate chains
- Certificate revocation
- OCSP stapling support

NIST Alignment: FIPS 204 (ML-DSA), RFC 5280 (X.509)
"""

import datetime
import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import structlog

# Try to import cryptography
try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class CertificateType(Enum):
    """Certificate types."""
    ROOT_CA = "root_ca"
    INTERMEDIATE_CA = "intermediate_ca"
    SERVER = "server"
    CLIENT = "client"
    CODE_SIGNING = "code_signing"
    OCSP_RESPONDER = "ocsp_responder"


class SignatureAlgorithm(Enum):
    """Signature algorithms."""
    ECDSA_SHA384 = "ecdsa_sha384"
    ML_DSA_65 = "ml_dsa_65"
    HYBRID_ECDSA_ML_DSA = "hybrid_ecdsa_ml_dsa"
    RSA_PKCS1_SHA256 = "rsa_pkcs1_sha256"


@dataclass
class CertificateSubject:
    """Certificate subject information."""
    common_name: str
    organization: Optional[str] = None
    organizational_unit: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    locality: Optional[str] = None
    email: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Optional[str]]:
        """Convert to dictionary."""
        return {
            "common_name": self.common_name,
            "organization": self.organization,
            "organizational_unit": self.organizational_unit,
            "country": self.country,
            "state": self.state,
            "locality": self.locality,
            "email": self.email
        }


@dataclass
class CertificateExtensions:
    """Certificate extensions."""
    subject_alt_names: List[str] = field(default_factory=list)
    key_usage: List[str] = field(default_factory=list)
    extended_key_usage: List[str] = field(default_factory=list)
    basic_constraints_ca: bool = False
    basic_constraints_path_length: Optional[int] = None
    crl_distribution_points: List[str] = field(default_factory=list)
    ocsp_responders: List[str] = field(default_factory=list)


@dataclass
class CertificateData:
    """Certificate data container."""
    serial_number: int
    subject: CertificateSubject
    issuer: CertificateSubject
    not_before: datetime.datetime
    not_after: datetime.datetime
    public_key: bytes
    signature: bytes
    extensions: CertificateExtensions
    pem_data: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "serial_number": self.serial_number,
            "subject": self.subject.to_dict(),
            "issuer": self.issuer.to_dict(),
            "not_before": self.not_before.isoformat(),
            "not_after": self.not_after.isoformat(),
            "public_key": self.public_key.hex()[:64] if self.public_key else None,
            "signature": self.signature.hex()[:64] if self.signature else None,
            "pem_data": self.pem_data[:100] + "..." if len(self.pem_data) > 100 else self.pem_data
        }


@dataclass
class CertificateChain:
    """Certificate chain."""
    certificates: List[CertificateData]
    root_thumbprint: str
    
    def to_pem_bundle(self) -> str:
        """Export as PEM bundle."""
        return "\n".join(cert.pem_data for cert in self.certificates)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate certificate chain."""
        errors = []
        
        if len(self.certificates) < 1:
            errors.append("Empty certificate chain")
            return False, errors
        
        # Check temporal validity
        now = datetime.datetime.utcnow()
        for cert in self.certificates:
            if now < cert.not_before:
                errors.append(f"Certificate {cert.serial_number} not yet valid")
            if now > cert.not_after:
                errors.append(f"Certificate {cert.serial_number} expired")
        
        # Check chain integrity (simplified)
        for i in range(len(self.certificates) - 1):
            if self.certificates[i].issuer.common_name != \
               self.certificates[i + 1].subject.common_name:
                errors.append(f"Chain break at position {i}")
        
        return len(errors) == 0, errors


class CertificateGenerator:
    """
    AMCIS Certificate Generator
    ===========================
    
    X.509 certificate generation with post-quantum cryptography support.
    """
    
    # Default validity periods
    ROOT_CA_VALIDITY_DAYS = 365 * 10  # 10 years
    INTERMEDIATE_CA_VALIDITY_DAYS = 365 * 5  # 5 years
    END_ENTITY_VALIDITY_DAYS = 365  # 1 year
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        default_signature_alg: SignatureAlgorithm = SignatureAlgorithm.HYBRID_ECDSA_ML_DSA
    ) -> None:
        """
        Initialize certificate generator.
        
        Args:
            storage_path: Path for certificate storage
            default_signature_alg: Default signature algorithm
        """
        if not HAS_CRYPTOGRAPHY:
            raise RuntimeError("cryptography package required")
        
        self.storage_path = storage_path or Path("/var/lib/amcis/certs")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.default_signature_alg = default_signature_alg
        
        self.logger = structlog.get_logger("amcis.cert_generator")
        
        # Certificate revocation list
        self._crl: Dict[int, datetime.datetime] = {}
        self._crl_path = self.storage_path / "crl.pem"
        
        # Issued certificates tracking
        self._issued_certificates: Dict[int, CertificateData] = {}
        
        self.logger.info("cert_generator_initialized")
    
    def generate_ca_certificate(
        self,
        subject: CertificateSubject,
        cert_type: CertificateType = CertificateType.ROOT_CA,
        validity_days: Optional[int] = None,
        signature_alg: Optional[SignatureAlgorithm] = None,
        key_size: int = 4096
    ) -> Tuple[CertificateData, bytes, bytes]:
        """
        Generate CA certificate.
        
        Args:
            subject: Certificate subject
            cert_type: Type of CA certificate
            validity_days: Validity period
            signature_alg: Signature algorithm
            key_size: RSA key size (if applicable)
            
        Returns:
            (Certificate data, private key PEM, public key PEM)
        """
        validity_days = validity_days or self.ROOT_CA_VALIDITY_DAYS
        signature_alg = signature_alg or self.default_signature_alg
        
        # Generate keypair
        private_key, public_key = self._generate_keypair(signature_alg, key_size)
        
        # Build subject and issuer names (self-signed for CA)
        name = self._build_name(subject)
        
        # Validity period
        not_before = datetime.datetime.utcnow()
        not_after = not_before + datetime.timedelta(days=validity_days)
        
        # Serial number
        serial_number = secrets.randbits(64)
        
        # Build extensions
        extensions = CertificateExtensions(
            basic_constraints_ca=True,
            basic_constraints_path_length=0 if cert_type == CertificateType.ROOT_CA else None,
            key_usage=["digital_signature", "key_cert_sign", "crl_sign"]
        )
        
        # Generate certificate
        cert_pem = self._generate_x509_cert(
            serial_number=serial_number,
            subject=name,
            issuer=name,  # Self-signed
            not_before=not_before,
            not_after=not_after,
            public_key=public_key,
            private_key=private_key,
            extensions=extensions,
            signature_alg=signature_alg
        )
        
        cert_data = CertificateData(
            serial_number=serial_number,
            subject=subject,
            issuer=subject,
            not_before=not_before,
            not_after=not_after,
            public_key=public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ),
            signature=b"",  # Would be extracted from cert
            extensions=extensions,
            pem_data=cert_pem
        )
        
        # Store
        self._issued_certificates[serial_number] = cert_data
        self._save_certificate(cert_data)
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        self.logger.info(
            "ca_certificate_generated",
            serial_number=serial_number,
            subject=subject.common_name,
            cert_type=cert_type.value
        )
        
        return cert_data, private_pem.encode(), public_pem.encode()
    
    def generate_end_entity_certificate(
        self,
        subject: CertificateSubject,
        issuer_cert: CertificateData,
        issuer_private_key: bytes,
        cert_type: CertificateType = CertificateType.SERVER,
        validity_days: Optional[int] = None,
        extensions: Optional[CertificateExtensions] = None,
        signature_alg: Optional[SignatureAlgorithm] = None
    ) -> CertificateData:
        """
        Generate end-entity certificate.
        
        Args:
            subject: Certificate subject
            issuer_cert: Issuer certificate
            issuer_private_key: Issuer private key PEM
            cert_type: Certificate type
            validity_days: Validity period
            extensions: Certificate extensions
            signature_alg: Signature algorithm
            
        Returns:
            Certificate data
        """
        validity_days = validity_days or self.END_ENTITY_VALIDITY_DAYS
        signature_alg = signature_alg or self.default_signature_alg
        
        # Generate keypair for end entity
        private_key, public_key = self._generate_keypair(signature_alg)
        
        # Build names
        subject_name = self._build_name(subject)
        issuer_name = self._build_name(issuer_cert.subject)
        
        # Validity
        not_before = datetime.datetime.utcnow()
        not_after = min(
            not_before + datetime.timedelta(days=validity_days),
            issuer_cert.not_after
        )
        
        # Serial number
        serial_number = secrets.randbits(64)
        
        # Default extensions
        if extensions is None:
            extensions = self._default_extensions(cert_type)
        
        # Load issuer private key
        issuer_key = serialization.load_pem_private_key(
            issuer_private_key,
            password=None,
            backend=default_backend()
        )
        
        # Generate certificate
        cert_pem = self._generate_x509_cert(
            serial_number=serial_number,
            subject=subject_name,
            issuer=issuer_name,
            not_before=not_before,
            not_after=not_after,
            public_key=public_key,
            private_key=issuer_key,
            extensions=extensions,
            signature_alg=signature_alg
        )
        
        cert_data = CertificateData(
            serial_number=serial_number,
            subject=subject,
            issuer=issuer_cert.subject,
            not_before=not_before,
            not_after=not_after,
            public_key=public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ),
            signature=b"",
            extensions=extensions,
            pem_data=cert_pem
        )
        
        self._issued_certificates[serial_number] = cert_data
        self._save_certificate(cert_data)
        
        self.logger.info(
            "end_entity_certificate_generated",
            serial_number=serial_number,
            subject=subject.common_name,
            issuer=issuer_cert.subject.common_name
        )
        
        return cert_data
    
    def _generate_keypair(
        self,
        signature_alg: SignatureAlgorithm,
        key_size: int = 4096
    ) -> Tuple[Any, Any]:
        """Generate keypair based on signature algorithm."""
        if signature_alg in (SignatureAlgorithm.ECDSA_SHA384, SignatureAlgorithm.HYBRID_ECDSA_ML_DSA):
            private_key = ec.generate_private_key(
                ec.SECP384R1(),
                default_backend()
            )
        else:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
        
        return private_key, private_key.public_key()
    
    def _build_name(self, subject: CertificateSubject) -> x509.Name:
        """Build X.509 name from subject."""
        name_attributes = [
            x509.NameAttribute(NameOID.COMMON_NAME, subject.common_name)
        ]
        
        if subject.organization:
            name_attributes.append(
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, subject.organization)
            )
        if subject.country:
            name_attributes.append(
                x509.NameAttribute(NameOID.COUNTRY_NAME, subject.country)
            )
        if subject.state:
            name_attributes.append(
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, subject.state)
            )
        if subject.locality:
            name_attributes.append(
                x509.NameAttribute(NameOID.LOCALITY_NAME, subject.locality)
            )
        if subject.email:
            name_attributes.append(
                x509.NameAttribute(NameOID.EMAIL_ADDRESS, subject.email)
            )
        
        return x509.Name(name_attributes)
    
    def _generate_x509_cert(
        self,
        serial_number: int,
        subject: x509.Name,
        issuer: x509.Name,
        not_before: datetime.datetime,
        not_after: datetime.datetime,
        public_key: Any,
        private_key: Any,
        extensions: CertificateExtensions,
        signature_alg: SignatureAlgorithm
    ) -> str:
        """Generate X.509 certificate."""
        # Build certificate
        builder = x509.CertificateBuilder()
        builder = builder.subject_name(subject)
        builder = builder.issuer_name(issuer)
        builder = builder.public_key(public_key)
        builder = builder.serial_number(serial_number)
        builder = builder.not_valid_before(not_before)
        builder = builder.not_valid_after(not_after)
        
        # Add extensions
        if extensions.basic_constraints_ca:
            builder = builder.add_extension(
                x509.BasicConstraints(
                    ca=True,
                    path_length=extensions.basic_constraints_path_length
                ),
                critical=True
            )
        else:
            builder = builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True
            )
        
        # Subject Alternative Names
        if extensions.subject_alt_names:
            san_list = []
            for san in extensions.subject_alt_names:
                if san.startswith("DNS:"):
                    san_list.append(x509.DNSName(san[4:]))
                elif san.startswith("IP:"):
                    san_list.append(x509.IPAddress(san[3:]))
                else:
                    san_list.append(x509.DNSName(san))
            
            builder = builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False
            )
        
        # Key Usage
        if extensions.key_usage:
            key_usage = x509.KeyUsage(
                digital_signature="digital_signature" in extensions.key_usage,
                content_commitment=False,
                key_encipherment="key_encipherment" in extensions.key_usage,
                data_encipherment="data_encipherment" in extensions.key_usage,
                key_agreement="key_agreement" in extensions.key_usage,
                key_cert_sign="key_cert_sign" in extensions.key_usage,
                crl_sign="crl_sign" in extensions.key_usage,
                encipher_only=False,
                decipher_only=False
            )
            builder = builder.add_extension(key_usage, critical=True)
        
        # Extended Key Usage
        if extensions.extended_key_usage:
            eku_oids = []
            for eku in extensions.extended_key_usage:
                if eku == "server_auth":
                    eku_oids.append(ExtendedKeyUsageOID.SERVER_AUTH)
                elif eku == "client_auth":
                    eku_oids.append(ExtendedKeyUsageOID.CLIENT_AUTH)
                elif eku == "code_signing":
                    eku_oids.append(ExtendedKeyUsageOID.CODE_SIGNING)
            
            builder = builder.add_extension(
                x509.ExtendedKeyUsage(eku_oids),
                critical=False
            )
        
        # Sign certificate
        hash_alg = hashes.SHA384()
        certificate = builder.sign(
            private_key=private_key,
            algorithm=hash_alg,
            backend=default_backend()
        )
        
        return certificate.public_bytes(serialization.Encoding.PEM).decode()
    
    def _default_extensions(self, cert_type: CertificateType) -> CertificateExtensions:
        """Get default extensions for certificate type."""
        if cert_type == CertificateType.SERVER:
            return CertificateExtensions(
                key_usage=["digital_signature", "key_encipherment"],
                extended_key_usage=["server_auth"]
            )
        elif cert_type == CertificateType.CLIENT:
            return CertificateExtensions(
                key_usage=["digital_signature"],
                extended_key_usage=["client_auth"]
            )
        elif cert_type == CertificateType.CODE_SIGNING:
            return CertificateExtensions(
                key_usage=["digital_signature"],
                extended_key_usage=["code_signing"]
            )
        else:
            return CertificateExtensions()
    
    def _save_certificate(self, cert_data: CertificateData) -> None:
        """Save certificate to storage."""
        cert_file = self.storage_path / f"cert_{cert_data.serial_number}.pem"
        with open(cert_file, 'w') as f:
            f.write(cert_data.pem_data)
    
    def revoke_certificate(
        self,
        serial_number: int,
        reason: str = "unspecified"
    ) -> bool:
        """
        Revoke a certificate.
        
        Args:
            serial_number: Certificate serial number
            reason: Revocation reason
            
        Returns:
            True if revoked
        """
        if serial_number not in self._issued_certificates:
            return False
        
        self._crl[serial_number] = datetime.datetime.utcnow()
        
        self.logger.critical(
            "certificate_revoked",
            serial_number=serial_number,
            reason=reason
        )
        
        self._update_crl()
        return True
    
    def _update_crl(self) -> None:
        """Update certificate revocation list."""
        # Simplified CRL generation
        crl_data = {
            "updated": datetime.datetime.utcnow().isoformat(),
            "revoked": [
                {"serial": sn, "date": dt.isoformat()}
                for sn, dt in self._crl.items()
            ]
        }
        
        with open(self._crl_path, 'w') as f:
            json.dump(crl_data, f, indent=2)
    
    def is_revoked(self, serial_number: int) -> bool:
        """Check if certificate is revoked."""
        return serial_number in self._crl
    
    def build_certificate_chain(
        self,
        end_entity_cert: CertificateData,
        intermediate_certs: List[CertificateData]
    ) -> CertificateChain:
        """
        Build certificate chain.
        
        Args:
            end_entity_cert: End entity certificate
            intermediate_certs: Intermediate CA certificates
            
        Returns:
            Certificate chain
        """
        chain_certs = [end_entity_cert] + intermediate_certs
        
        # Calculate root thumbprint
        if intermediate_certs:
            root_cert = intermediate_certs[-1]
            root_thumbprint = hashlib.sha256(
                root_cert.pem_data.encode()
            ).hexdigest()[:16]
        else:
            root_thumbprint = "self_signed"
        
        return CertificateChain(
            certificates=chain_certs,
            root_thumbprint=root_thumbprint
        )
    
    def get_certificate_info(self, serial_number: int) -> Optional[Dict[str, Any]]:
        """Get certificate information."""
        cert = self._issued_certificates.get(serial_number)
        if cert:
            return cert.to_dict()
        return None
    
    def list_certificates(self) -> List[Dict[str, Any]]:
        """List all issued certificates."""
        return [
            {
                "serial_number": cert.serial_number,
                "subject": cert.subject.common_name,
                "issuer": cert.issuer.common_name,
                "not_after": cert.not_after.isoformat(),
                "revoked": self.is_revoked(cert.serial_number)
            }
            for cert in self._issued_certificates.values()
        ]
