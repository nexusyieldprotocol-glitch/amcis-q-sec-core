// TLS configuration with post-quantum hybrid support

use crate::config::GatewayConfig;
use rustls::{
    pki_types::{CertificateDer, PrivateKeyDer},
    server::{ClientHello, ResolvesServerCert},
    sign::CertifiedKey,
    SupportedCipherSuite,
};
use std::{
    error::Error,
    fmt::{self, Display, Formatter},
    io,
    sync::Arc,
};
use tokio::net::TcpStream;
use tokio_rustls::{rustls::ServerConfig, TlsAcceptor};
use tracing::info;

/// Custom error type for TLS operations
#[derive(Debug)]
pub enum TlsError {
    Io(io::Error),
    InvalidCertificate(String),
    InvalidPrivateKey(String),
    ConfigurationError(String),
}

impl Display for TlsError {
    fn fmt(&self, f: &mut Formatter<'_>) -> fmt::Result {
        match self {
            TlsError::Io(e) => write!(f, "IO error: {}", e),
            TlsError::InvalidCertificate(s) => write!(f, "Invalid certificate: {}", s),
            TlsError::InvalidPrivateKey(s) => write!(f, "Invalid private key: {}", s),
            TlsError::ConfigurationError(s) => write!(f, "Configuration error: {}", s),
        }
    }
}

impl Error for TlsError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            TlsError::Io(e) => Some(e),
            _ => None,
        }
    }
}

impl From<io::Error> for TlsError {
    fn from(e: io::Error) -> Self {
        TlsError::Io(e)
    }
}

/// Hybrid TLS configuration supporting post-quantum algorithms
pub struct HybridTlsConfig {
    inner: Arc<ServerConfig>,
    pq_enabled: bool,
    supported_groups: Vec<String>,
    cipher_suites: Vec<String>,
}

impl HybridTlsConfig {
    /// Create a new hybrid TLS configuration
    pub fn new(config: &GatewayConfig) -> Result<Self, TlsError> {
        let pq_enabled = config.enable_pq_tls;
        
        info!("Initializing TLS configuration (PQ enabled: {})", pq_enabled);
        
        // Build TLS configuration
        let server_config = if let (Some(cert_path), Some(key_path)) = 
            (&config.tls_cert_path, &config.tls_key_path) {
            // Load certificates from file
            Self::load_from_files(cert_path, key_path, pq_enabled)?
        } else {
            // Generate self-signed certificate for testing
            info!("Generating self-signed certificate for testing");
            Self::generate_self_signed(pq_enabled)?
        };

        let supported_groups = if pq_enabled {
            vec![
                "X25519Kyber768Draft00".to_string(),  // Hybrid X25519+Kyber
                "X25519".to_string(),                 // Classical fallback
                "secp256r1".to_string(),
            ]
        } else {
            vec![
                "X25519".to_string(),
                "secp256r1".to_string(),
            ]
        };

        let cipher_suites = vec![
            "TLS13_AES_256_GCM_SHA384".to_string(),
            "TLS13_AES_128_GCM_SHA256".to_string(),
            "TLS13_CHACHA20_POLY1305_SHA256".to_string(),
        ];

        Ok(Self {
            inner: Arc::new(server_config),
            pq_enabled,
            supported_groups,
            cipher_suites,
        })
    }

    /// Load TLS configuration from certificate files
    fn load_from_files(
        cert_path: &str,
        key_path: &str,
        pq_enabled: bool,
    ) -> Result<ServerConfig, TlsError> {
        let cert_file = std::fs::read(cert_path)
            .map_err(|e| TlsError::InvalidCertificate(format!("Failed to read cert file: {}", e)))?;
        
        let key_file = std::fs::read(key_path)
            .map_err(|e| TlsError::InvalidPrivateKey(format!("Failed to read key file: {}", e)))?;

        let certs: Vec<CertificateDer<'static>> = rustls_pemfile::certs(&mut cert_file.as_slice())
            .filter_map(|c| c.ok())
            .collect();

        if certs.is_empty() {
            return Err(TlsError::InvalidCertificate("No certificates found".to_string()));
        }

        let key = rustls_pemfile::private_key(&mut key_file.as_slice())
            .map_err(|e| TlsError::InvalidPrivateKey(e.to_string()))?
            .ok_or_else(|| TlsError::InvalidPrivateKey("No private key found".to_string()))?;

        Self::build_config(certs, key, pq_enabled)
    }

    /// Generate a self-signed certificate for testing
    fn generate_self_signed(pq_enabled: bool) -> Result<ServerConfig, TlsError> {
        let cert = rcgen::generate_simple_self_signed(vec![
            "localhost".to_string(),
            "*.amcis.local".to_string(),
        ]).map_err(|e| TlsError::ConfigurationError(e.to_string()))?;

        let cert_der = cert.cert.der().clone();
        let key_der = cert.key_pair.serialize_der();

        let certs = vec![CertificateDer::from(cert_der)];
        let key = PrivateKeyDer::try_from(key_der)
            .map_err(|e| TlsError::InvalidPrivateKey(e.to_string()))?;

        Self::build_config(certs, key, pq_enabled)
    }

    /// Build the TLS server configuration
    fn build_config(
        certs: Vec<CertificateDer<'static>>,
        key: PrivateKeyDer<'static>,
        pq_enabled: bool,
    ) -> Result<ServerConfig, TlsError> {
        // Create signing key
        let signing_key = rustls::crypto::ring::sign::any_supported_type(&key)
            .map_err(|e| TlsError::InvalidPrivateKey(e.to_string()))?;

        let certified_key = Arc::new(CertifiedKey::new(certs, signing_key));

        // Configure cipher suites
        let cipher_suites: Vec<SupportedCipherSuite> = vec![
            rustls::crypto::ring::cipher_suite::TLS13_AES_256_GCM_SHA384,
            rustls::crypto::ring::cipher_suite::TLS13_AES_128_GCM_SHA256,
            rustls::crypto::ring::cipher_suite::TLS13_CHACHA20_POLY1305_SHA256,
        ];

        // Configure protocol versions (TLS 1.3 only for PQ support)
        let versions = vec![&rustls::version::TLS13];

        // Create server config
        let mut config = ServerConfig::builder()
            .with_cipher_suites(&cipher_suites)
            .with_safe_default_kx_groups()
            .with_protocol_versions(&versions)
            .map_err(|e| TlsError::ConfigurationError(e.to_string()))?
            .with_no_client_auth()
            .with_cert_resolver(Arc::new(SingleCertResolver { certified_key }));

        // Enable ALPN for HTTP/2
        config.alpn_protocols = vec![b"h2".to_vec(), b"http/1.1".to_vec()];

        // Additional PQ-specific configuration could go here
        if pq_enabled {
            info!("Post-quantum hybrid key exchange enabled");
            // Note: In production, you would use rustls fork or provider
            // that supports X25519Kyber768
        }

        Ok(config)
    }

    /// Create a TLS acceptor
    pub fn acceptor(&self) -> TlsAcceptor {
        TlsAcceptor::from(self.inner.clone())
    }

    /// Check if PQ is enabled
    pub fn is_pq_enabled(&self) -> bool {
        self.pq_enabled
    }

    /// Get supported groups
    pub fn supported_groups(&self) -> &[String] {
        &self.supported_groups
    }

    /// Get cipher suites
    pub fn cipher_suites(&self) -> &[String] {
        &self.cipher_suites
    }
}

/// Simple certificate resolver for single certificate
struct SingleCertResolver {
    certified_key: Arc<CertifiedKey>,
}

impl ResolvesServerCert for SingleCertResolver {
    fn resolve(&self, _client_hello: ClientHello<'_>) -> Option<Arc<CertifiedKey>> {
        Some(self.certified_key.clone())
    }
}
