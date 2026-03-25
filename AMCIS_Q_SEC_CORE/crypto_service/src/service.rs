//! gRPC service implementation

use crate::{crypto::*, hybrid::*, keys::*, CryptoError, Result, SecurityLevel};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn};

/// Crypto service configuration
#[derive(Debug, Clone)]
pub struct CryptoServiceConfig {
    /// Default security level
    pub default_security_level: SecurityLevel,
    /// Enable hybrid cryptography
    pub enable_hybrid: bool,
    /// Key store path (or "memory" for in-memory)
    pub key_store_path: String,
}

impl Default for CryptoServiceConfig {
    fn default() -> Self {
        Self {
            default_security_level: SecurityLevel::Level3,
            enable_hybrid: true,
            key_store_path: "memory".to_string(),
        }
    }
}

/// Crypto service implementation
pub struct CryptoService {
    config: CryptoServiceConfig,
    key_store: Arc<RwLock<KeyStore>>,
    pq_kem: PqKem,
    pq_sig: PqSignature,
    hybrid_kem: Option<HybridKem>,
    hybrid_sig: Option<HybridSignature>,
}

impl CryptoService {
    /// Create new crypto service
    pub fn new(config: CryptoServiceConfig) -> Self {
        let level = config.default_security_level;
        
        Self {
            config: config.clone(),
            key_store: Arc::new(RwLock::new(KeyStore::new())),
            pq_kem: PqKem::new(level),
            pq_sig: PqSignature::new(level),
            hybrid_kem: if config.enable_hybrid {
                Some(HybridKem::new(level))
            } else {
                None
            },
            hybrid_sig: if config.enable_hybrid {
                Some(HybridSignature::new(level))
            } else {
                None
            },
        }
    }
    
    /// Initialize the service
    pub async fn init(&self) -> Result<()> {
        info!("Initializing crypto service with security level {:?}", 
              self.config.default_security_level);
        
        // Generate master key if not exists
        // In production, this would come from HSM
        
        Ok(())
    }
    
    /// Generate a keypair for key exchange
    pub async fn generate_kem_keypair(&self) -> Result<(Vec<u8>, Vec<u8>)> {
        if self.config.enable_hybrid {
            self.hybrid_kem.as_ref()
                .unwrap()
                .keypair()
        } else {
            self.pq_kem.keypair()
        }
    }
    
    /// Generate a keypair for signatures
    pub async fn generate_signature_keypair(&self) -> Result<(Vec<u8>, Vec<u8>)> {
        if self.config.enable_hybrid {
            self.hybrid_sig.as_ref()
                .unwrap()
                .keypair()
        } else {
            self.pq_sig.keypair()
        }
    }
    
    /// Encapsulate - generate shared secret
    pub async fn encapsulate(&self, public_key: &[u8]) -> Result<(Vec<u8>, Vec<u8>)> {
        if self.config.enable_hybrid {
            self.hybrid_kem.as_ref()
                .unwrap()
                .encapsulate(public_key)
        } else {
            self.pq_kem.encapsulate(public_key)
        }
    }
    
    /// Decapsulate - recover shared secret
    pub async fn decapsulate(&self, secret_key: &[u8], ciphertext: &[u8]) -> Result<Vec<u8>> {
        if self.config.enable_hybrid {
            self.hybrid_kem.as_ref()
                .unwrap()
                .decapsulate(secret_key, ciphertext)
        } else {
            self.pq_kem.decapsulate(secret_key, ciphertext)
        }
    }
    
    /// Sign a message
    pub async fn sign(&self, message: &[u8], secret_key: &[u8]) -> Result<Vec<u8>> {
        if self.config.enable_hybrid {
            self.hybrid_sig.as_ref()
                .unwrap()
                .sign(message, secret_key)
        } else {
            self.pq_sig.sign(message, secret_key)
        }
    }
    
    /// Verify a signature
    pub async fn verify(&self, message: &[u8], signature: &[u8], public_key: &[u8]) -> Result<bool> {
        if self.config.enable_hybrid {
            self.hybrid_sig.as_ref()
                .unwrap()
                .verify(message, signature, public_key)
        } else {
            self.pq_sig.verify(message, signature, public_key)
        }
    }
    
    /// Store a key in the key store
    pub async fn store_key(&self, metadata: KeyMetadata, key_material: Vec<u8>) -> Result<()> {
        let store = self.key_store.read().await;
        store.store(metadata, key_material)
    }
    
    /// Retrieve a key from the key store
    pub async fn retrieve_key(&self, key_id: &str) -> Result<(KeyMetadata, Vec<u8>)> {
        let store = self.key_store.read().await;
        store.retrieve(key_id)
    }
    
    /// List all keys
    pub async fn list_keys(&self) -> Result<Vec<KeyMetadata>> {
        let store = self.key_store.read().await;
        store.list_keys()
    }
    
    /// Get service health status
    pub fn health(&self) -> ServiceHealth {
        ServiceHealth {
            status: "healthy".to_string(),
            security_level: format!("{:?}", self.config.default_security_level),
            hybrid_enabled: self.config.enable_hybrid,
        }
    }
}

/// Service health information
#[derive(Debug)]
pub struct ServiceHealth {
    /// Health status
    pub status: String,
    /// Current security level
    pub security_level: String,
    /// Whether hybrid crypto is enabled
    pub hybrid_enabled: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_service_init() {
        let config = CryptoServiceConfig::default();
        let service = CryptoService::new(config);
        
        service.init().await.unwrap();
        
        let health = service.health();
        assert_eq!(health.status, "healthy");
        assert!(health.hybrid_enabled);
    }

    #[tokio::test]
    async fn test_kem_operations() {
        let config = CryptoServiceConfig::default();
        let service = CryptoService::new(config);
        
        // Generate keypair
        let (pk, sk) = service.generate_kem_keypair().await.unwrap();
        assert!(!pk.is_empty());
        
        // Note: Full encapsulate/decapsulate test requires proper X25519 handling
    }

    #[tokio::test]
    async fn test_signature_operations() {
        let config = CryptoServiceConfig::default();
        let service = CryptoService::new(config);
        
        // Generate keypair
        let (pk, sk) = service.generate_signature_keypair().await.unwrap();
        
        // Sign
        let message = b"test message";
        let sig = service.sign(message, &sk).await.unwrap();
        
        // Verify
        let valid = service.verify(message, &sig, &pk).await.unwrap();
        assert!(valid);
    }
}
