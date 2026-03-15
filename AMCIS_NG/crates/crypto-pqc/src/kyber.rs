//! ML-KEM (Kyber) Implementation
//! NIST FIPS 203 compliant key encapsulation mechanism

use super::*;
use pqcrypto_kyber::{kyber512, kyber768, kyber1024};

/// ML-KEM key encapsulation
pub struct MlKem;

impl MlKem {
    /// Generate a new ML-KEM-768 keypair
    pub fn keygen768() -> Result<KeyPair> {
        let (pk, sk) = kyber768::keypair();
        Ok(KeyPair::new(
            "ML-KEM-768",
            pk.as_bytes().to_vec(),
            sk.as_bytes().to_vec(),
        ))
    }
    
    /// Generate a new ML-KEM-1024 keypair
    pub fn keygen1024() -> Result<KeyPair> {
        let (pk, sk) = kyber1024::keypair();
        Ok(KeyPair::new(
            "ML-KEM-1024",
            pk.as_bytes().to_vec(),
            sk.as_bytes().to_vec(),
        ))
    }
    
    /// Encapsulate - generate shared secret and ciphertext for ML-KEM-768
    pub fn encapsulate768(public_key_bytes: &[u8]) -> Result<KemResult> {
        let pk = kyber768::PublicKey::from_bytes(public_key_bytes)
            .map_err(|_| PqcError::InvalidKeyFormat)?;
        
        let (ct, ss) = kyber768::encapsulate(&pk);
        
        Ok(KemResult {
            ciphertext: ct.as_bytes().to_vec(),
            shared_secret: ss.as_bytes().to_vec(),
        })
    }
    
    /// Decapsulate - recover shared secret from ciphertext for ML-KEM-768
    pub fn decapsulate768(ciphertext: &[u8], secret_key_bytes: &[u8]) -> Result<Vec<u8>> {
        let sk = kyber768::SecretKey::from_bytes(secret_key_bytes)
            .map_err(|_| PqcError::InvalidKeyFormat)?;
        
        let ct = kyber768::Ciphertext::from_bytes(ciphertext)
            .map_err(|_| PqcError::InvalidKeyFormat)?;
        
        let ss = kyber768::decapsulate(&ct, &sk);
        Ok(ss.as_bytes().to_vec())
    }
    
    /// Get key sizes for ML-KEM-768
    pub fn key_sizes_768() -> (usize, usize, usize) {
        (
            kyber768::public_key_bytes(),   // 1184
            kyber768::secret_key_bytes(),   // 2400
            kyber768::ciphertext_bytes(),   // 1088
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_kyber768_full_roundtrip() {
        // Generate keypair
        let keypair = MlKem::keygen768().expect("Keygen failed");
        
        // Encapsulate
        let encap = MlKem::encapsulate768(&keypair.public_key)
            .expect("Encapsulation failed");
        
        // Decapsulate
        let decap = MlKem::decapsulate768(&encap.ciphertext, &keypair.secret_key)
            .expect("Decapsulation failed");
        
        // Verify shared secrets match
        assert_eq!(encap.shared_secret, decap, "Shared secrets should match!");
    }
    
    #[test]
    fn test_kyber768_key_sizes() {
        let (pk_size, sk_size, ct_size) = MlKem::key_sizes_768();
        assert_eq!(pk_size, 1184);
        assert_eq!(sk_size, 2400);
        assert_eq!(ct_size, 1088);
    }
    
    #[test]
    fn test_kyber768_generated_key_sizes() {
        let keypair = MlKem::keygen768().unwrap();
        assert_eq!(keypair.public_key.len(), 1184);
        assert_eq!(keypair.secret_key.len(), 2400);
    }
    
    #[test]
    fn test_kyber768_shared_secret_size() {
        let keypair = MlKem::keygen768().unwrap();
        let encap = MlKem::encapsulate768(&keypair.public_key).unwrap();
        assert_eq!(encap.shared_secret.len(), 32); // 256 bits
    }
}
