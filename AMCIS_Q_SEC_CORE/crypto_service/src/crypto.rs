//! Core cryptographic operations
//! 
//! Implements NIST FIPS 203 (ML-KEM/Kyber) and FIPS 204 (ML-DSA/Dilithium)

use crate::{CryptoError, Result, SecurityLevel};
use pqcrypto_kyber::{kyber768, kyber1024};
use pqcrypto_dilithium::{dilithium3, dilithium5};
use pqcrypto_traits::{kem, sign};
use rand::rngs::OsRng;
use rand::RngCore;

/// Post-quantum KEM (Key Encapsulation Mechanism)
pub struct PqKem {
    level: SecurityLevel,
}

impl PqKem {
    /// Create new KEM instance
    pub fn new(level: SecurityLevel) -> Self {
        Self { level }
    }
    
    /// Generate keypair
    pub fn keypair(&self) -> Result<(Vec<u8>, Vec<u8>)> {
        match self.level {
            SecurityLevel::Level1 | SecurityLevel::Level3 => {
                let (pk, sk) = kyber768::keypair();
                Ok((pk.as_bytes().to_vec(), sk.as_bytes().to_vec()))
            }
            SecurityLevel::Level5 => {
                let (pk, sk) = kyber1024::keypair();
                Ok((pk.as_bytes().to_vec(), sk.as_bytes().to_vec()))
            }
        }
    }
    
    /// Encapsulate - generate shared secret and ciphertext
    pub fn encapsulate(&self, public_key: &[u8]) -> Result<(Vec<u8>, Vec<u8>)> {
        match self.level {
            SecurityLevel::Level1 | SecurityLevel::Level3 => {
                let pk = kyber768::PublicKey::from_bytes(public_key)
                    .map_err(|e| CryptoError::InvalidKey(format!("Kyber768: {:?}", e)))?;
                let (ss, ct) = kyber768::encapsulate(&pk);
                Ok((ss.as_bytes().to_vec(), ct.as_bytes().to_vec()))
            }
            SecurityLevel::Level5 => {
                let pk = kyber1024::PublicKey::from_bytes(public_key)
                    .map_err(|e| CryptoError::InvalidKey(format!("Kyber1024: {:?}", e)))?;
                let (ss, ct) = kyber1024::encapsulate(&pk);
                Ok((ss.as_bytes().to_vec(), ct.as_bytes().to_vec()))
            }
        }
    }
    
    /// Decapsulate - recover shared secret from ciphertext
    pub fn decapsulate(&self, secret_key: &[u8], ciphertext: &[u8]) -> Result<Vec<u8>> {
        match self.level {
            SecurityLevel::Level1 | SecurityLevel::Level3 => {
                let sk = kyber768::SecretKey::from_bytes(secret_key)
                    .map_err(|e| CryptoError::InvalidKey(format!("Kyber768: {:?}", e)))?;
                let ct = kyber768::Ciphertext::from_bytes(ciphertext)
                    .map_err(|e| CryptoError::Decryption(format!("Invalid ciphertext: {:?}", e)))?;
                let ss = kyber768::decapsulate(&ct, &sk);
                Ok(ss.as_bytes().to_vec())
            }
            SecurityLevel::Level5 => {
                let sk = kyber1024::SecretKey::from_bytes(secret_key)
                    .map_err(|e| CryptoError::InvalidKey(format!("Kyber1024: {:?}", e)))?;
                let ct = kyber1024::Ciphertext::from_bytes(ciphertext)
                    .map_err(|e| CryptoError::Decryption(format!("Invalid ciphertext: {:?}", e)))?;
                let ss = kyber1024::decapsulate(&ct, &sk);
                Ok(ss.as_bytes().to_vec())
            }
        }
    }
}

/// Post-quantum Signature scheme
pub struct PqSignature {
    level: SecurityLevel,
}

impl PqSignature {
    /// Create new signature instance
    pub fn new(level: SecurityLevel) -> Self {
        Self { level }
    }
    
    /// Generate keypair
    pub fn keypair(&self) -> Result<(Vec<u8>, Vec<u8>)> {
        match self.level {
            SecurityLevel::Level1 | SecurityLevel::Level3 => {
                let (pk, sk) = dilithium3::keypair();
                Ok((pk.as_bytes().to_vec(), sk.as_bytes().to_vec()))
            }
            SecurityLevel::Level5 => {
                let (pk, sk) = dilithium5::keypair();
                Ok((pk.as_bytes().to_vec(), sk.as_bytes().to_vec()))
            }
        }
    }
    
    /// Sign message
    pub fn sign(&self, message: &[u8], secret_key: &[u8]) -> Result<Vec<u8>> {
        match self.level {
            SecurityLevel::Level1 | SecurityLevel::Level3 => {
                let sk = dilithium3::SecretKey::from_bytes(secret_key)
                    .map_err(|e| CryptoError::InvalidKey(format!("Dilithium3: {:?}", e)))?;
                let sig = dilithium3::sign(message, &sk);
                Ok(sig.as_bytes().to_vec())
            }
            SecurityLevel::Level5 => {
                let sk = dilithium5::SecretKey::from_bytes(secret_key)
                    .map_err(|e| CryptoError::InvalidKey(format!("Dilithium5: {:?}", e)))?;
                let sig = dilithium5::sign(message, &sk);
                Ok(sig.as_bytes().to_vec())
            }
        }
    }
    
    /// Verify signature
    pub fn verify(&self, message: &[u8], signature: &[u8], public_key: &[u8]) -> Result<bool> {
        match self.level {
            SecurityLevel::Level1 | SecurityLevel::Level3 => {
                let pk = dilithium3::PublicKey::from_bytes(public_key)
                    .map_err(|e| CryptoError::InvalidKey(format!("Dilithium3: {:?}", e)))?;
                let sig = dilithium3::SignedMessage::from_bytes(signature)
                    .map_err(|e| CryptoError::ValidationError(format!("Invalid signature: {:?}", e)))?;
                Ok(dilithium3::verify(&sig, &pk).is_ok())
            }
            SecurityLevel::Level5 => {
                let pk = dilithium5::PublicKey::from_bytes(public_key)
                    .map_err(|e| CryptoError::InvalidKey(format!("Dilithium5: {:?}", e)))?;
                let sig = dilithium5::SignedMessage::from_bytes(signature)
                    .map_err(|e| CryptoError::ValidationError(format!("Invalid signature: {:?}", e)))?;
                Ok(dilithium5::verify(&sig, &pk).is_ok())
            }
        }
    }
}

/// Envelope encryption using AES-256-GCM
pub struct EnvelopeEncryption {
    /// Master key for wrapping (should come from HSM/KMS)
    master_key: Vec<u8>,
}

impl EnvelopeEncryption {
    /// Create new envelope encryption instance
    pub fn new(master_key: Vec<u8>) -> Self {
        Self { master_key }
    }
    
    /// Generate data encryption key (DEK)
    pub fn generate_dek(&self) -> Vec<u8> {
        let mut dek = vec![0u8; 32]; // AES-256
        OsRng.fill_bytes(&mut dek);
        dek
    }
    
    /// Wrap DEK with master key
    pub fn wrap_key(&self, dek: &[u8]) -> Result<Vec<u8>> {
        use aes_gcm::{
            aead::{Aead, KeyInit},
            Aes256Gcm, Nonce,
        };
        use sha2::{Sha256, Digest};
        
        // Derive wrapping key from master key
        let mut hasher = Sha256::new();
        hasher.update(&self.master_key);
        hasher.update(b"key-wrapping");
        let wrapping_key = hasher.finalize();
        
        let cipher = Aes256Gcm::new_from_slice(&wrapping_key)
            .map_err(|e| CryptoError::Encryption(format!("Key init failed: {:?}", e)))?;
        
        let nonce_bytes = {
            let mut bytes = vec![0u8; 12];
            OsRng.fill_bytes(&mut bytes);
            bytes
        };
        let nonce = Nonce::from_slice(&nonce_bytes);
        
        let ciphertext = cipher.encrypt(nonce, dek)
            .map_err(|e| CryptoError::Encryption(format!("Wrap failed: {:?}", e)))?;
        
        // Return nonce || ciphertext
        let mut result = nonce_bytes;
        result.extend_from_slice(&ciphertext);
        Ok(result)
    }
    
    /// Unwrap DEK with master key
    pub fn unwrap_key(&self, wrapped_key: &[u8]) -> Result<Vec<u8>> {
        use aes_gcm::{
            aead::{Aead, KeyInit},
            Aes256Gcm, Nonce,
        };
        use sha2::{Sha256, Digest};
        
        if wrapped_key.len() < 12 {
            return Err(CryptoError::Decryption("Invalid wrapped key".to_string()));
        }
        
        // Derive wrapping key
        let mut hasher = Sha256::new();
        hasher.update(&self.master_key);
        hasher.update(b"key-wrapping");
        let wrapping_key = hasher.finalize();
        
        let cipher = Aes256Gcm::new_from_slice(&wrapping_key)
            .map_err(|e| CryptoError::Decryption(format!("Key init failed: {:?}", e)))?;
        
        let nonce = Nonce::from_slice(&wrapped_key[..12]);
        let ciphertext = &wrapped_key[12..];
        
        let plaintext = cipher.decrypt(nonce, ciphertext)
            .map_err(|e| CryptoError::Decryption(format!("Unwrap failed: {:?}", e)))?;
        
        Ok(plaintext)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kyber_keypair() {
        let kem = PqKem::new(SecurityLevel::Level3);
        let (pk, sk) = kem.keypair().unwrap();
        assert!(!pk.is_empty());
        assert!(!sk.is_empty());
    }

    #[test]
    fn test_kyber_encapsulate_decapsulate() {
        let kem = PqKem::new(SecurityLevel::Level3);
        let (pk, sk) = kem.keypair().unwrap();
        
        let (ss1, ct) = kem.encapsulate(&pk).unwrap();
        let ss2 = kem.decapsulate(&sk, &ct).unwrap();
        
        assert_eq!(ss1, ss2);
    }

    #[test]
    fn test_dilithium_sign_verify() {
        let sig = PqSignature::new(SecurityLevel::Level3);
        let (pk, sk) = sig.keypair().unwrap();
        
        let message = b"Test message for signing";
        let signature = sig.sign(message, &sk).unwrap();
        
        let valid = sig.verify(message, &signature, &pk).unwrap();
        assert!(valid);
    }

    #[test]
    fn test_envelope_encryption() {
        let master_key = vec![0x42; 32]; // Test key
        let envelope = EnvelopeEncryption::new(master_key);
        
        let dek = envelope.generate_dek();
        let wrapped = envelope.wrap_key(&dek).unwrap();
        let unwrapped = envelope.unwrap_key(&wrapped).unwrap();
        
        assert_eq!(dek, unwrapped);
    }
}
