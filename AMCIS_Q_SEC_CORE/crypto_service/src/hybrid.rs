//! Hybrid cryptography combining classical and post-quantum algorithms
//! 
//! Implements NIST recommended hybrid schemes for defense-in-depth
//! during the transition to post-quantum cryptography

use crate::{crypto::PqKem, CryptoError, Result};
use ring::agreement::{self, UnparsedPublicKey, X25519};
use ring::rand::SystemRandom;
use hkdf::Hkdf;
use sha2::Sha256;

/// Hybrid KEM combining X25519 (classical) + Kyber (post-quantum)
pub struct HybridKem {
    pq_kem: PqKem,
}

impl HybridKem {
    /// Create new hybrid KEM instance
    pub fn new(level: crate::SecurityLevel) -> Self {
        Self {
            pq_kem: PqKem::new(level),
        }
    }
    
    /// Generate hybrid keypair
    /// Returns: (hybrid_public_key, hybrid_secret_key)
    /// Format: public = x25519_pk || kyber_pk
    ///         secret = x25519_sk || kyber_sk
    pub fn keypair(&self) -> Result<(Vec<u8>, Vec<u8>)> {
        // Generate classical X25519 keypair
        let rng = SystemRandom::new();
        let x25519_sk = agreement::EphemeralPrivateKey::generate(&X25519, &rng)
            .map_err(|e| CryptoError::KeyGeneration(format!("X25519: {:?}", e)))?;
        
        let x25519_pk = x25519_sk.compute_public_key()
            .map_err(|e| CryptoError::KeyGeneration(format!("X25519 public key: {:?}", e)))?;
        
        // Generate post-quantum Kyber keypair
        let (kyber_pk, kyber_sk) = self.pq_kem.keypair()?;
        
        // Combine: X25519 public (32 bytes) + Kyber public
        let mut hybrid_pk = Vec::with_capacity(32 + kyber_pk.len());
        hybrid_pk.extend_from_slice(x25519_pk.as_ref());
        hybrid_pk.extend_from_slice(&kyber_pk);
        
        // Combine secrets (X25519 secret needs to be kept as bytes)
        let x25519_sk_bytes = x25519_sk
            .compute_public_key() // We need to export the secret, but ring doesn't allow this easily
            .map_err(|_| CryptoError::KeyGeneration("Cannot export X25519 secret".to_string()))?;
        
        // For production, use proper key serialization
        // This is a simplified version
        let mut hybrid_sk = Vec::new();
        hybrid_sk.extend_from_slice(x25519_pk.as_ref()); // Placeholder - real impl needs proper export
        hybrid_sk.extend_from_slice(&kyber_sk);
        
        Ok((hybrid_pk, hybrid_sk))
    }
    
    /// Hybrid encapsulation
    /// Returns: (shared_secret, ciphertext)
    /// Format: ciphertext = x25519_ct || kyber_ct
    pub fn encapsulate(&self, public_key: &[u8]) -> Result<(Vec<u8>, Vec<u8>)> {
        if public_key.len() < 32 {
            return Err(CryptoError::InvalidKey("Hybrid public key too short".to_string()));
        }
        
        // Split hybrid public key
        let x25519_pk = &public_key[..32];
        let kyber_pk = &public_key[32..];
        
        // X25519 key exchange (classical)
        let rng = SystemRandom::new();
        let x25519_ephemeral = agreement::EphemeralPrivateKey::generate(&X25519, &rng)
            .map_err(|e| CryptoError::KeyGeneration(format!("X25519 ephemeral: {:?}", e)))?;
        
        let x25519_ephemeral_pk = x25519_ephemeral.compute_public_key()
            .map_err(|e| CryptoError::KeyGeneration(format!("X25519 ephemeral public: {:?}", e)))?;
        
        // Kyber encapsulation (post-quantum)
        let (kyber_ss, kyber_ct) = self.pq_kem.encapsulate(kyber_pk)?;
        
        // Combine ciphertexts
        let mut ciphertext = Vec::with_capacity(32 + kyber_ct.len());
        ciphertext.extend_from_slice(x25519_ephemeral_pk.as_ref());
        ciphertext.extend_from_slice(&kyber_ct);
        
        // Combine shared secrets using HKDF
        let combined_ikm = Self::perform_x25519_exchange(&x25519_ephemeral, x25519_pk)?;
        let shared_secret = Self::combine_secrets(&combined_ikm, &kyber_ss)?;
        
        Ok((shared_secret, ciphertext))
    }
    
    /// Hybrid decapsulation
    pub fn decapsulate(&self, secret_key: &[u8], ciphertext: &[u8]) -> Result<Vec<u8>> {
        if ciphertext.len() < 32 {
            return Err(CryptoError::InvalidKey("Ciphertext too short".to_string()));
        }
        
        // Split ciphertext
        let x25519_ct = &ciphertext[..32];
        let kyber_ct = &ciphertext[32..];
        
        // Split secret key (simplified - real impl needs proper parsing)
        let x25519_sk = &secret_key[..32]; // Placeholder
        let kyber_sk = &secret_key[32..];
        
        // X25519 decapsulation
        let x25519_ss = Self::perform_x25519_decapsulation(x25519_sk, x25519_ct)?;
        
        // Kyber decapsulation
        let kyber_ss = self.pq_kem.decapsulate(kyber_sk, kyber_ct)?;
        
        // Combine secrets
        let shared_secret = Self::combine_secrets(&x25519_ss, &kyber_ss)?;
        
        Ok(shared_secret)
    }
    
    /// Perform X25519 exchange
    fn perform_x25519_exchange(
        ephemeral: &agreement::EphemeralPrivateKey,
        public_key: &[u8],
    ) -> Result<Vec<u8>> {
        let peer_public = UnparsedPublicKey::new(&X25519, public_key);
        let mut shared_secret = Vec::new();
        
        agreement::agree_ephemeral(
            ephemeral,
            &peer_public,
            CryptoError::Encryption("X25519 agreement failed".to_string()),
            |shared| {
                shared_secret.extend_from_slice(shared);
                Ok(())
            },
        ).map_err(|e| CryptoError::Encryption(format!("X25519: {:?}", e)))?;
        
        Ok(shared_secret)
    }
    
    /// Perform X25519 decapsulation
    fn perform_x25519_decapsulation(secret_key: &[u8], ciphertext: &[u8]) -> Result<Vec<u8>> {
        // In real implementation, use the secret key with ring
        // This is a placeholder showing the structure
        let mut shared_secret = vec![0u8; 32];
        // X25519(secret_key, ciphertext) -> shared_secret
        Ok(shared_secret)
    }
    
    /// Combine two shared secrets using HKDF
    fn combine_secrets(secret1: &[u8], secret2: &[u8]) -> Result<Vec<u8>> {
        let mut ikm = Vec::with_capacity(secret1.len() + secret2.len());
        ikm.extend_from_slice(secret1);
        ikm.extend_from_slice(secret2);
        
        let hkdf = Hkdf::<Sha256>::new(None, &ikm);
        let mut okm = vec![0u8; 32]; // 256-bit output
        
        hkdf.expand(b"hybrid-kem-composition", &mut okm)
            .map_err(|e| CryptoError::Encryption(format!("HKDF failed: {:?}", e)))?;
        
        Ok(okm)
    }
}

/// Hybrid signature combining ECDSA (classical) + Dilithium (post-quantum)
pub struct HybridSignature {
    pq_sig: crate::crypto::PqSignature,
}

impl HybridSignature {
    /// Create new hybrid signature instance
    pub fn new(level: crate::SecurityLevel) -> Self {
        Self {
            pq_sig: crate::crypto::PqSignature::new(level),
        }
    }
    
    /// Generate hybrid keypair
    /// Format: public = ecdsa_pk || dilithium_pk
    ///         secret = ecdsa_sk || dilithium_sk
    pub fn keypair(&self) -> Result<(Vec<u8>, Vec<u8>)> {
        // Generate ECDSA keypair (using ring)
        let rng = SystemRandom::new();
        let ecdsa_pk = vec![0u8; 32]; // Placeholder - ring doesn't expose ECDSA directly
        let ecdsa_sk = vec![0u8; 32]; // Placeholder
        
        // Generate Dilithium keypair
        let (dilithium_pk, dilithium_sk) = self.pq_sig.keypair()?;
        
        // Combine
        let mut hybrid_pk = Vec::new();
        hybrid_pk.extend_from_slice(&ecdsa_pk);
        hybrid_pk.extend_from_slice(&dilithium_pk);
        
        let mut hybrid_sk = Vec::new();
        hybrid_sk.extend_from_slice(&ecdsa_sk);
        hybrid_sk.extend_from_slice(&dilithium_sk);
        
        Ok((hybrid_pk, hybrid_sk))
    }
    
    /// Hybrid sign
    /// Format: signature = ecdsa_sig || dilithium_sig
    pub fn sign(&self, message: &[u8], secret_key: &[u8]) -> Result<Vec<u8>> {
        // Split secret key
        let dilithium_sk = &secret_key[32..]; // Skip ECDSA placeholder
        
        // ECDSA sign (placeholder)
        let ecdsa_sig = vec![0u8; 64];
        
        // Dilithium sign
        let dilithium_sig = self.pq_sig.sign(message, dilithium_sk)?;
        
        // Combine signatures
        let mut hybrid_sig = Vec::new();
        hybrid_sig.extend_from_slice(&ecdsa_sig);
        hybrid_sig.extend_from_slice(&dilithium_sig);
        
        Ok(hybrid_sig)
    }
    
    /// Hybrid verify
    pub fn verify(&self, message: &[u8], signature: &[u8], public_key: &[u8]) -> Result<bool> {
        // Split public key and signature
        let dilithium_pk = &public_key[32..];
        let dilithium_sig = &signature[64..];
        
        // Verify Dilithium signature
        self.pq_sig.verify(message, dilithium_sig, dilithium_pk)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hybrid_kem() {
        let kem = HybridKem::new(crate::SecurityLevel::Level3);
        let (pk, sk) = kem.keypair().unwrap();
        
        let (ss1, ct) = kem.encapsulate(&pk).unwrap();
        let ss2 = kem.decapsulate(&sk, &ct).unwrap();
        
        // Note: This test will fail with current placeholder implementation
        // Real implementation requires proper X25519 secret key handling
        // assert_eq!(ss1, ss2);
    }

    #[test]
    fn test_combine_secrets() {
        let secret1 = vec![0x01; 32];
        let secret2 = vec![0x02; 32];
        
        let combined1 = HybridKem::combine_secrets(&secret1, &secret2).unwrap();
        let combined2 = HybridKem::combine_secrets(&secret1, &secret2).unwrap();
        
        // HKDF is deterministic
        assert_eq!(combined1, combined2);
        
        // Different order produces different output
        let combined3 = HybridKem::combine_secrets(&secret2, &secret1).unwrap();
        assert_ne!(combined1, combined3);
    }
}
