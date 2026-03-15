//! ML-DSA (Dilithium) Implementation
//! NIST FIPS 204 compliant digital signatures

use super::*;
use pqcrypto_dilithium::{dilithium2, dilithium3, dilithium5};
use pqcrypto_traits::sign::{PublicKey as SignPK, SecretKey as SignSK, SignedMessage as SignSM};

/// ML-DSA signature scheme
pub struct MlDsa;

/// Signature result with metadata
#[derive(Debug, Clone)]
pub struct SignatureResult {
    pub signature: Vec<u8>,
    pub message: Vec<u8>,
    pub algorithm: String,
}

impl MlDsa {
    /// Generate ML-DSA-65 keypair (recommended security level)
    pub fn keygen65() -> Result<KeyPair> {
        let (pk, sk) = dilithium3::keypair();
        Ok(KeyPair::new(
            "ML-DSA-65",
            pk.as_bytes().to_vec(),
            sk.as_bytes().to_vec(),
        ))
    }
    
    /// Generate ML-DSA-87 keypair (highest security)
    pub fn keygen87() -> Result<KeyPair> {
        let (pk, sk) = dilithium5::keypair();
        Ok(KeyPair::new(
            "ML-DSA-87",
            pk.as_bytes().to_vec(),
            sk.as_bytes().to_vec(),
        ))
    }
    
    /// Sign a message with ML-DSA-65
    pub fn sign65(message: &[u8], secret_key_bytes: &[u8]) -> Result<Vec<u8>> {
        let sk = dilithium3::SecretKey::from_bytes(secret_key_bytes)
            .map_err(|_| PqcError::InvalidKeyFormat)?;
        
        let sig = dilithium3::sign(message, &sk);
        Ok(sig.as_bytes().to_vec())
    }
    
    /// Verify a signature with ML-DSA-65
    pub fn verify65(message: &[u8], signature: &[u8], public_key_bytes: &[u8]) -> Result<bool> {
        let pk = dilithium3::PublicKey::from_bytes(public_key_bytes)
            .map_err(|_| PqcError::InvalidKeyFormat)?;
        
        let sm = dilithium3::SignedMessage::from_bytes(signature)
            .map_err(|_| PqcError::InvalidKeyFormat)?;
        
        let result = dilithium3::verify(&sm, &pk);
        Ok(result.is_ok())
    }
    
    /// Sign and verify in one operation (for testing)
    pub fn sign_and_verify65(message: &[u8], keypair: &KeyPair) -> Result<bool> {
        let signature = Self::sign65(message, &keypair.secret_key)?;
        Self::verify65(message, &signature, &keypair.public_key)
    }
    
    /// Get signature sizes
    pub fn signature_sizes() -> (usize, usize, usize) {
        (
            dilithium2::signature_bytes(),  // ~2420 bytes
            dilithium3::signature_bytes(),  // ~3293 bytes
            dilithium5::signature_bytes(),  // ~4595 bytes
        )
    }
    
    /// Get public key sizes
    pub fn public_key_sizes() -> (usize, usize, usize) {
        (
            dilithium2::public_key_bytes(),  // ~1312 bytes
            dilithium3::public_key_bytes(),  // ~1952 bytes
            dilithium5::public_key_bytes(),  // ~2592 bytes
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_dilithium65_sign_verify() {
        // Generate keypair
        let keypair = MlDsa::keygen65().expect("Keygen failed");
        
        // Message to sign
        let message = b"AMCIS Quantum-Secure Message";
        
        // Sign
        let signature = MlDsa::sign65(message, &keypair.secret_key)
            .expect("Signing failed");
        
        // Verify
        let valid = MlDsa::verify65(message, &signature, &keypair.public_key)
            .expect("Verification failed");
        
        assert!(valid, "Signature should be valid");
    }
    
    #[test]
    fn test_dilithium65_wrong_message_fails() {
        let keypair = MlDsa::keygen65().unwrap();
        let message = b"Original message";
        let wrong_message = b"Different message";
        
        let signature = MlDsa::sign65(message, &keypair.secret_key).unwrap();
        let valid = MlDsa::verify65(wrong_message, &signature, &keypair.public_key).unwrap();
        
        assert!(!valid, "Wrong message should fail verification");
    }
    
    #[test]
    fn test_dilithium65_key_sizes() {
        let (_, pk65, _) = MlDsa::public_key_sizes();
        let (_, sig65, _) = MlDsa::signature_sizes();
        
        assert_eq!(pk65, 1952);
        assert_eq!(sig65, 3293);
    }
    
    #[test]
    fn test_dilithium65_generated_key_sizes() {
        let keypair = MlDsa::keygen65().unwrap();
        assert_eq!(keypair.public_key.len(), 1952);
        assert_eq!(keypair.secret_key.len(), 4032);
    }
    
    #[test]
    fn test_sign_and_verify_convenience() {
        let keypair = MlDsa::keygen65().unwrap();
        let message = b"Test message";
        
        let valid = MlDsa::sign_and_verify65(message, &keypair).unwrap();
        assert!(valid);
    }
}
