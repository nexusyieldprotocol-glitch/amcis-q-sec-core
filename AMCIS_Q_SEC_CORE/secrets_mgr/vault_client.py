"""
HashiCorp Vault Client for AMCIS
================================

Enterprise-grade Vault integration with:
- KV v2 secrets engine support
- Kubernetes authentication
- Automatic token renewal
- Dynamic database credentials
- PKI certificate management
- Transit encryption operations

Environment Variables:
    VAULT_ADDR: Vault server URL (default: http://localhost:8200)
    VAULT_TOKEN: Vault token for authentication
    VAULT_ROLE: Kubernetes auth role (for K8s auth)
    VAULT_MOUNT_PATH: Kubernetes auth mount path (default: kubernetes)
    VAULT_CACERT: Path to CA certificate for TLS
    VAULT_CLIENT_CERT: Path to client certificate for TLS
    VAULT_CLIENT_KEY: Path to client key for TLS
"""

import base64
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin

import requests
import structlog
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class VaultError(Exception):
    """Base Vault error."""
    pass


class VaultAuthError(VaultError):
    """Authentication error."""
    pass


class VaultSecretError(VaultError):
    """Secret operation error."""
    pass


class VaultConnectionError(VaultError):
    """Connection error."""
    pass


class AuthMethod(Enum):
    """Vault authentication methods."""
    TOKEN = "token"
    KUBERNETES = "kubernetes"
    APPROLE = "approle"
    USERPASS = "userpass"


@dataclass
class VaultConfig:
    """Vault client configuration."""
    addr: str = field(default_factory=lambda: os.environ.get("VAULT_ADDR", "http://localhost:8200"))
    token: Optional[str] = field(default_factory=lambda: os.environ.get("VAULT_TOKEN"))
    auth_method: AuthMethod = AuthMethod.TOKEN
    
    # Kubernetes auth settings
    k8s_role: Optional[str] = field(default_factory=lambda: os.environ.get("VAULT_ROLE"))
    k8s_mount_path: str = field(default_factory=lambda: os.environ.get("VAULT_MOUNT_PATH", "kubernetes"))
    k8s_token_path: str = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    
    # AppRole auth settings
    approle_role_id: Optional[str] = field(default_factory=lambda: os.environ.get("VAULT_ROLE_ID"))
    approle_secret_id: Optional[str] = field(default_factory=lambda: os.environ.get("VAULT_SECRET_ID"))
    
    # TLS settings
    ca_cert: Optional[str] = field(default_factory=lambda: os.environ.get("VAULT_CACERT"))
    client_cert: Optional[str] = field(default_factory=lambda: os.environ.get("VAULT_CLIENT_CERT"))
    client_key: Optional[str] = field(default_factory=lambda: os.environ.get("VAULT_CLIENT_KEY"))
    verify_tls: bool = True
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 30
    
    # Token renewal
    token_renewal_threshold: float = 0.25  # Renew when 25% of TTL remains
    auto_renew: bool = True


@dataclass
class SecretVersion:
    """Vault secret version metadata."""
    version: int
    created_time: datetime
    deletion_time: Optional[datetime]
    destroyed: bool


@dataclass
class SecretMetadata:
    """Vault secret metadata."""
    path: str
    current_version: int
    versions: Dict[int, SecretVersion]
    created_time: datetime
    updated_time: datetime
    max_versions: int
    cas_required: bool


class VaultClient:
    """
    HashiCorp Vault Client
    ======================
    
    Production-grade Vault client with automatic token renewal,
    comprehensive error handling, and support for multiple auth methods.
    
    Example:
        >>> from amcis.secrets_mgr.vault_client import VaultClient, VaultConfig
        >>> 
        >>> # Token auth
        >>> client = VaultClient(VaultConfig(token="dev-token"))
        >>> 
        >>> # Kubernetes auth
        >>> client = VaultClient(VaultConfig(
        ...     auth_method=AuthMethod.KUBERNETES,
        ...     k8s_role="amcis-role"
        ... ))
        >>> 
        >>> # Read secret
        >>> secret = client.read_secret("secret/data/myapp")
        >>> print(secret["data"]["password"])
        >>> 
        >>> # Write secret
        >>> client.write_secret("secret/data/myapp", {"password": "newpass"})
    """
    
    def __init__(self, config: Optional[VaultConfig] = None) -> None:
        self.config = config or VaultConfig()
        self.logger = structlog.get_logger("amcis.vault")
        
        # Session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Token management
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._token_ttl: Optional[int] = None
        self._renewal_thread: Optional[threading.Thread] = None
        self._stop_renewal = threading.Event()
        self._lock = threading.RLock()
        
        # Authenticate
        self._authenticate()
        
        self.logger.info("vault_client_initialized", 
                        addr=self.config.addr,
                        auth_method=self.config.auth_method.value)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        with self._lock:
            if self._token:
                headers["X-Vault-Token"] = self._token
        return headers
    
    def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Vault."""
        url = urljoin(self.config.addr, f"/v1/{path}")
        
        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
                timeout=self.config.timeout,
                verify=self.config.verify_tls if self.config.ca_cert else True
            )
            
            if response.status_code == 204:
                return {}
            
            if response.status_code == 403:
                raise VaultAuthError("Permission denied - check token permissions")
            
            if response.status_code == 404:
                raise VaultSecretError(f"Secret not found: {path}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError as e:
            self.logger.error("vault_connection_error", error=str(e))
            raise VaultConnectionError(f"Failed to connect to Vault: {e}")
        except requests.exceptions.Timeout as e:
            self.logger.error("vault_timeout", error=str(e))
            raise VaultConnectionError(f"Vault request timed out: {e}")
        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = response.json()
            except:
                pass
            
            errors = error_data.get("errors", [str(e)])
            self.logger.error("vault_http_error", 
                            status=response.status_code,
                            errors=errors)
            raise VaultError(f"Vault API error: {errors}")
    
    def _authenticate(self) -> None:
        """Authenticate to Vault based on configured method."""
        if self.config.auth_method == AuthMethod.TOKEN:
            self._auth_token()
        elif self.config.auth_method == AuthMethod.KUBERNETES:
            self._auth_kubernetes()
        elif self.config.auth_method == AuthMethod.APPROLE:
            self._auth_approle()
        elif self.config.auth_method == AuthMethod.USERPASS:
            self._auth_userpass()
        else:
            raise VaultAuthError(f"Unsupported auth method: {self.config.auth_method}")
        
        # Start token renewal thread if auto-renew is enabled
        if self.config.auto_renew and self._token_ttl:
            self._start_renewal_thread()
    
    def _auth_token(self) -> None:
        """Authenticate with token."""
        if not self.config.token:
            raise VaultAuthError("No token provided for token auth")
        
        self._token = self.config.token
        
        # Verify token and get TTL
        try:
            result = self._make_request("GET", "auth/token/lookup-self")
            data = result.get("data", {})
            self._token_ttl = data.get("ttl", 0)
            
            # Calculate expiry
            if self._token_ttl > 0:
                self._token_expiry = datetime.now() + timedelta(seconds=self._token_ttl)
                self.logger.info("token_auth_success", 
                               ttl=self._token_ttl,
                               renewable=data.get("renewable", False))
            else:
                self.logger.info("token_auth_success", ttl="infinite")
                
        except VaultError:
            self._token = None
            raise VaultAuthError("Invalid token")
    
    def _auth_kubernetes(self) -> None:
        """Authenticate with Kubernetes service account."""
        if not self.config.k8s_role:
            raise VaultAuthError("No Kubernetes role specified")
        
        # Read service account token
        try:
            with open(self.config.k8s_token_path, "r") as f:
                jwt = f.read().strip()
        except FileNotFoundError:
            raise VaultAuthError(f"Kubernetes token not found at {self.config.k8s_token_path}")
        
        # Login to Vault
        path = f"auth/{self.config.k8s_mount_path}/login"
        data = {
            "role": self.config.k8s_role,
            "jwt": jwt
        }
        
        try:
            result = self._make_request("POST", path, data=data)
            auth_data = result.get("auth", {})
            
            self._token = auth_data.get("client_token")
            self._token_ttl = auth_data.get("lease_duration", 0)
            
            if self._token_ttl > 0:
                self._token_expiry = datetime.now() + timedelta(seconds=self._token_ttl)
            
            self.logger.info("kubernetes_auth_success",
                           role=self.config.k8s_role,
                           ttl=self._token_ttl,
                           renewable=auth_data.get("renewable", False))
                           
        except VaultError as e:
            raise VaultAuthError(f"Kubernetes auth failed: {e}")
    
    def _auth_approle(self) -> None:
        """Authenticate with AppRole."""
        if not self.config.approle_role_id:
            raise VaultAuthError("No AppRole role_id specified")
        
        data = {"role_id": self.config.approle_role_id}
        if self.config.approle_secret_id:
            data["secret_id"] = self.config.approle_secret_id
        
        try:
            result = self._make_request("POST", "auth/approle/login", data=data)
            auth_data = result.get("auth", {})
            
            self._token = auth_data.get("client_token")
            self._token_ttl = auth_data.get("lease_duration", 0)
            
            if self._token_ttl > 0:
                self._token_expiry = datetime.now() + timedelta(seconds=self._token_ttl)
            
            self.logger.info("approle_auth_success",
                           ttl=self._token_ttl,
                           renewable=auth_data.get("renewable", False))
                           
        except VaultError as e:
            raise VaultAuthError(f"AppRole auth failed: {e}")
    
    def _auth_userpass(self) -> None:
        """Authenticate with username/password."""
        raise VaultAuthError("Userpass auth not implemented - use token, kubernetes, or approle")
    
    def _start_renewal_thread(self) -> None:
        """Start background thread for token renewal."""
        def renewal_loop():
            while not self._stop_renewal.wait(timeout=60):  # Check every minute
                try:
                    self._renew_token_if_needed()
                except Exception as e:
                    self.logger.error("token_renewal_error", error=str(e))
        
        self._renewal_thread = threading.Thread(target=renewal_loop, daemon=True)
        self._renewal_thread.start()
        self.logger.info("token_renewal_thread_started")
    
    def _renew_token_if_needed(self) -> None:
        """Renew token if nearing expiry."""
        with self._lock:
            if not self._token_expiry or not self._token_ttl:
                return
            
            time_to_expiry = (self._token_expiry - datetime.now()).total_seconds()
            threshold = self._token_ttl * self.config.token_renewal_threshold
            
            if time_to_expiry < threshold:
                self.logger.info("renewing_token",
                               time_to_expiry=time_to_expiry,
                               threshold=threshold)
                
                try:
                    result = self._make_request("POST", "auth/token/renew-self")
                    auth_data = result.get("auth", {})
                    
                    self._token_ttl = auth_data.get("lease_duration", self._token_ttl)
                    self._token_expiry = datetime.now() + timedelta(seconds=self._token_ttl)
                    
                    self.logger.info("token_renewed", new_ttl=self._token_ttl)
                    
                except VaultError as e:
                    self.logger.error("token_renewal_failed", error=str(e))
                    raise
    
    def close(self) -> None:
        """Close client and stop renewal thread."""
        self._stop_renewal.set()
        if self._renewal_thread and self._renewal_thread.is_alive():
            self._renewal_thread.join(timeout=5)
        self.session.close()
        self.logger.info("vault_client_closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ====================
    # KV v2 Secrets Engine
    # ====================
    
    def read_secret(
        self,
        path: str,
        version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Read secret from KV v2.
        
        Args:
            path: Secret path (e.g., "secret/data/myapp")
            version: Specific version to read (None = latest)
        
        Returns:
            Secret data dictionary
        
        Raises:
            VaultSecretError: If secret not found
            VaultAuthError: If permission denied
        """
        params = {"version": version} if version else None
        
        result = self._make_request("GET", path, params=params)
        
        data = result.get("data", {})
        metadata = data.get("metadata", {})
        secret_data = data.get("data", {})
        
        self.logger.debug("secret_read", path=path, version=metadata.get("version"))
        
        return {
            "data": secret_data,
            "metadata": {
                "version": metadata.get("version"),
                "created_time": metadata.get("created_time"),
                "deletion_time": metadata.get("deletion_time"),
                "destroyed": metadata.get("destroyed", False)
            }
        }
    
    def write_secret(
        self,
        path: str,
        data: Dict[str, Any],
        cas: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Write secret to KV v2.
        
        Args:
            path: Secret path (e.g., "secret/data/myapp")
            data: Secret data to store
            cas: Check-and-set version (0 for new, int for specific version)
        
        Returns:
            Write result with version info
        """
        payload = {"data": data}
        if cas is not None:
            payload["options"] = {"cas": cas}
        
        result = self._make_request("POST", path, data=payload)
        
        response_data = result.get("data", {})
        version = response_data.get("version")
        
        self.logger.info("secret_written", path=path, version=version)
        
        return response_data
    
    def delete_secret(self, path: str, versions: Optional[List[int]] = None) -> None:
        """
        Delete secret versions (soft delete).
        
        Args:
            path: Secret path
            versions: Specific versions to delete (None = all)
        """
        if versions:
            payload = {"versions": versions}
            self._make_request("POST", f"{path}/delete", data=payload)
            self.logger.info("secret_versions_deleted", path=path, versions=versions)
        else:
            self._make_request("DELETE", path)
            self.logger.info("secret_deleted", path=path)
    
    def destroy_secret(self, path: str, versions: List[int]) -> None:
        """
        Permanently destroy secret versions.
        
        Args:
            path: Secret path
            versions: Versions to destroy permanently
        """
        payload = {"versions": versions}
        self._make_request("PUT", f"{path}/destroy", data=payload)
        self.logger.info("secret_versions_destroyed", path=path, versions=versions)
    
    def undelete_secret(self, path: str, versions: List[int]) -> None:
        """
        Restore deleted secret versions.
        
        Args:
            path: Secret path
            versions: Versions to restore
        """
        payload = {"versions": versions}
        self._make_request("POST", f"{path}/undelete", data=payload)
        self.logger.info("secret_versions_undeleted", path=path, versions=versions)
    
    def list_secrets(self, path: str) -> List[str]:
        """
        List secrets at path.
        
        Args:
            path: Path to list (e.g., "secret/metadata/myapp")
        
        Returns:
            List of secret keys
        """
        result = self._make_request("LIST", path)
        return result.get("data", {}).get("keys", [])
    
    def get_secret_metadata(self, path: str) -> SecretMetadata:
        """
        Get secret metadata.
        
        Args:
            path: Secret metadata path (e.g., "secret/metadata/myapp")
        
        Returns:
            SecretMetadata object
        """
        result = self._make_request("GET", path)
        data = result.get("data", {})
        
        versions = {}
        for version_num, version_data in data.get("versions", {}).items():
            versions[int(version_num)] = SecretVersion(
                version=int(version_num),
                created_time=datetime.fromisoformat(version_data["created_time"].replace("Z", "+00:00")),
                deletion_time=datetime.fromisoformat(version_data["deletion_time"].replace("Z", "+00:00")) if version_data.get("deletion_time") else None,
                destroyed=version_data.get("destroyed", False)
            )
        
        return SecretMetadata(
            path=path,
            current_version=data.get("current_version", 0),
            versions=versions,
            created_time=datetime.fromisoformat(data["created_time"].replace("Z", "+00:00")),
            updated_time=datetime.fromisoformat(data["updated_time"].replace("Z", "+00:00")),
            max_versions=data.get("max_versions", 0),
            cas_required=data.get("cas_required", False)
        )
    
    # =========================
    # Dynamic Database Credentials
    # =========================
    
    def get_database_credentials(
        self,
        role: str,
        mount_point: str = "database"
    ) -> Dict[str, str]:
        """
        Get dynamic database credentials.
        
        Args:
            role: Database role to generate credentials for
            mount_point: Database secrets engine mount point
        
        Returns:
            Dictionary with username and password
        """
        path = f"{mount_point}/creds/{role}"
        result = self._make_request("GET", path)
        
        data = result.get("data", {})
        lease_id = result.get("lease_id")
        lease_duration = result.get("lease_duration", 0)
        
        credentials = {
            "username": data.get("username"),
            "password": data.get("password"),
            "lease_id": lease_id,
            "lease_duration": lease_duration,
            "renewable": result.get("renewable", False)
        }
        
        self.logger.info("database_credentials_generated",
                        role=role,
                        username=credentials["username"],
                        lease_duration=lease_duration)
        
        return credentials
    
    def revoke_lease(self, lease_id: str) -> None:
        """
        Revoke a lease.
        
        Args:
            lease_id: Lease ID to revoke
        """
        self._make_request("PUT", "sys/leases/revoke", data={"lease_id": lease_id})
        self.logger.info("lease_revoked", lease_id=lease_id)
    
    # =========================
    # PKI Operations
    # =========================
    
    def generate_certificate(
        self,
        role: str,
        common_name: str,
        mount_point: str = "pki",
        ttl: Optional[str] = None,
        alt_names: Optional[List[str]] = None,
        ip_sans: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate PKI certificate.
        
        Args:
            role: PKI role
            common_name: Certificate common name
            mount_point: PKI mount point
            ttl: Time to live (e.g., "720h")
            alt_names: Subject alternative names
            ip_sans: IP subject alternative names
        
        Returns:
            Certificate data including private_key, certificate, ca_chain
        """
        path = f"{mount_point}/issue/{role}"
        data = {"common_name": common_name}
        
        if ttl:
            data["ttl"] = ttl
        if alt_names:
            data["alt_names"] = ",".join(alt_names)
        if ip_sans:
            data["ip_sans"] = ",".join(ip_sans)
        
        result = self._make_request("POST", path, data=data)
        
        self.logger.info("certificate_generated",
                        role=role,
                        common_name=common_name,
                        serial_number=result.get("data", {}).get("serial_number"))
        
        return result.get("data", {})
    
    # =========================
    # Health & Status
    # =========================
    
    def health(self) -> Dict[str, Any]:
        """
        Check Vault health status.
        
        Returns:
            Health status dictionary
        """
        try:
            result = self._make_request("GET", "sys/health")
            return {
                "initialized": result.get("initialized", False),
                "sealed": result.get("sealed", True),
                "standby": result.get("standby", False),
                "performance_standby": result.get("performance_standby", False),
                "replication_performance_mode": result.get("replication_performance_mode", "unknown"),
                "replication_dr_mode": result.get("replication_dr_mode", "unknown"),
                "server_time_utc": result.get("server_time_utc"),
                "version": result.get("version", "unknown")
            }
        except VaultConnectionError:
            return {"error": "connection_failed", "reachable": False}
    
    def seal_status(self) -> Dict[str, Any]:
        """Get seal status."""
        result = self._make_request("GET", "sys/seal-status")
        return result
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        with self._lock:
            return self._token is not None
    
    def token_info(self) -> Dict[str, Any]:
        """Get current token information."""
        result = self._make_request("GET", "auth/token/lookup-self")
        return result.get("data", {})
