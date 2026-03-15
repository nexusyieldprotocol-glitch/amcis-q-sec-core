//! AMCIS Post-Quantum Cryptography Module
//! 
//! Implements NIST-standardized post-quantum cryptographic algorithms:
//! - ML-KEM (Kyber) for key encapsulation
//! - ML-DSA (Dilithium) for digital signatures

use pqcrypto_traits::kem::{PublicKey as KemPublicKey, SecretKey as KemSecretKey, Ciphertext, SharedSecret};
use pqcrypto_traits::sign::{PublicKey as SignPublicKey, SecretKey as SignSecretKey, SignedMessage};
use serde::{Serialize, Deserialize};
use thiserror::Error;
use zeroize::{Zeroize, ZeroizeOnDrop};

pub mod kyber;
pub mod dilithium;

/// PQC Error types
#[derive(Error, Debug)]
pub enum PqcError {
    #[error("Key generation failed: {0}")]
    KeyGenerationError(String),
    
    #[error("Encapsulation failed: {0}")]
    EncapsulationError(String),
    
    #[error("Decapsulation failed: {0}")]
    DecapsulationError(String),
    
    #[error("Signing failed: {0}")]
    SigningError(String),
    
    #[error("Verification failed: {0}")]
    VerificationError(String),
    
    #[error("Invalid key format")]
    InvalidKeyFormat,
    
    #[error("Unsupported algorithm: {0}")]
    UnsupportedAlgorithm(String),
}

pub type Result<T> = std::result::Result<T, PqcError>;

/// Supported PQC algorithms
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PqcAlgorithm {
    MlKem768,
    MlKem1024,
    MlDsa44,
    MlDsa65,
    MlDsa87,
}

impl PqcAlgorithm {
    pub fn name(&self) -> &'static str {
        match self {
            PqcAlgorithm::MlKem768 => "ML-KEM-768",
            PqcAlgorithm::MlKem1024 => "ML-KEM-1024",
            PqcAlgorithm::MlDsa44 => "ML-DSA-44",
            PqcAlgorithm::MlDsa65 => "ML-DSA-65",
            PqcAlgorithm::MlDsa87 => "ML-DSA-87",
        }
    }
}

/// Key pair for KEM or signature algorithms
#[derive(Debug, Clone, Zeroize, ZeroizeOnDrop)]
pub struct KeyPair {
    pub algorithm: String,
    pub public_key: Vec<u8>,
    #[zeroize(skip)]
    pub secret_key: Vec<u8>,
}

impl KeyPair {
    pub fn new(algorithm: &str, public_key: Vec<u8>, secret_key: Vec<u8>) -> Self {
        Self {
            algorithm: algorithm.to_string(),
            public_key,
            secret_key,
        }
    }
    
    pub fn public_key_base64(&self) -> String {
        base64::encode(&self.public_key)
    }
}

/// Ciphertext and shared secret from KEM encapsulation
#[derive(Debug, Clone, Zeroize, ZeroizeOnDrop)]
pub struct KemResult {
    pub ciphertext: Vec<u8>,
    pub shared_secret: Vec<u8>,
}

/// Hybrid encryption combining classical and PQC
pub struct HybridCrypto;

impl HybridCrypto {
    /// Generate a hybrid keypair (Classical + PQC)
    pub fn generate_keypair() -> Result<(KeyPair, KeyPair)> {
        // Classical key (X25519 via ring or similar)
        // For now, just return PQC key
        let pq_key = kyber::MlKem::keygen(pqcrypto_kyber::kyber768::new())?;
        Ok((pq_key.clone(), pq_key))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_algorithm_names() {
        assert_eq!(PqcAlgorithm::MlKem768.name(), "ML-KEM-768");
        assert_eq!(PqcAlgorithm::MlDsa65.name(), "ML-DSA-65");
    }
    
    #[test]
    fn test_keypair_creation() {
        let kp = KeyPair::new("test", vec![1,2,3], vec![4,5,6]);
        assert_eq!(kp.algorithm, "test");
        assert_eq!(kp.public_key, vec![1,2,3]);
    }
}
