//! Utility functions for PQC operations

use super::*;

/// Initialize RNG
pub fn init_rng() -> Result<()> {
    Ok(())
}

/// Secure random bytes
pub fn random_bytes(len: usize) -> Vec<u8> {
    use rand::RngCore;
    let mut bytes = vec![0u8; len];
    rand::thread_rng().fill_bytes(&mut bytes);
    bytes
}

/// Hash with SHA3-256
pub fn sha3_256(data: &[u8]) -> Vec<u8> {
    use sha3::{Sha3_256, Digest};
    let mut hasher = Sha3_256::new();
    hasher.update(data);
    hasher.finalize().to_vec()
}

/// Hash with BLAKE3
pub fn blake3_hash(data: &[u8]) -> Vec<u8> {
    blake3::hash(data).as_bytes().to_vec()
}
