//! AMCIS Crypto Service
//! 
//! Post-quantum cryptographic service implementing NIST FIPS 203-205 standards.
//! Provides hybrid cryptography combining classical and post-quantum algorithms.

#![warn(missing_docs)]
#![warn(unsafe_code)]

pub mod crypto;
pub mod hybrid;
pub mod keys;
pub mod service;

use thiserror::Error;

/// Crypto service errors
#[derive(Error, Debug)]
pub enum CryptoError {
    /// Key generation failed
    #[error("Key generation failed: {0}")]
    KeyGeneration(String),
    
    /// Encryption failed
    #[error("Encryption failed: {0}")]
    Encryption(String),
    
    /// Decryption failed
    #[error("Decryption failed: {0}")]
    Decryption(String),
    
    /// Invalid key
    #[error("Invalid key: {0}")]
    InvalidKey(String),
    
    /// Algorithm not supported
    #[error("Algorithm not supported: {0}")]
    UnsupportedAlgorithm(String),
    
    /// HSM operation failed
    #[error("HSM operation failed: {0}")]
    HsmError(String),
    
    /// Validation failed
    #[error("Validation failed: {0}")]
    ValidationError(String),
}

/// Result type for crypto operations
pub type Result<T> = std::result::Result<T, CryptoError>;

/// Security levels as defined by NIST
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SecurityLevel {
    /// NIST Level 1 (128-bit classical security)
    Level1,
    /// NIST Level 3 (192-bit classical security)
    Level3,
    /// NIST Level 5 (256-bit classical security)
    Level5,
}

impl SecurityLevel {
    /// Get Kyber variant for this security level
    pub fn kyber_variant(&self) -> &'static str {
        match self {
            SecurityLevel::Level1 => "Kyber512",
            SecurityLevel::Level3 => "Kyber768",
            SecurityLevel::Level5 => "Kyber1024",
        }
    }
    
    /// Get Dilithium variant for this security level
    pub fn dilithium_variant(&self) -> &'static str {
        match self {
            SecurityLevel::Level1 => "Dilithium2",
            SecurityLevel::Level3 => "Dilithium3",
            SecurityLevel::Level5 => "Dilithium5",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_security_level() {
        assert_eq!(SecurityLevel::Level3.kyber_variant(), "Kyber768");
        assert_eq!(SecurityLevel::Level5.dilithium_variant(), "Dilithium5");
    }
}
