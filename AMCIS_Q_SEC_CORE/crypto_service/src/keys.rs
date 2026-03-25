//! Key management and lifecycle

use crate::{CryptoError, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Key usage types
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum KeyUsage {
    /// Data encryption
    DataEncryption,
    /// Key encryption (wrapping)
    KeyEncryption,
    /// Digital signatures
    DigitalSignature,
    /// Authentication
    Authentication,
    /// Key exchange
    KeyExchange,
}

/// Key metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeyMetadata {
    /// Unique key identifier
    pub key_id: String,
    /// Key version
    pub version: u32,
    /// Creation timestamp
    pub created_at: u64,
    /// Expiration timestamp (0 = no expiration)
    pub expires_at: u64,
    /// Key usage
    pub usage: KeyUsage,
    /// Algorithm
    pub algorithm: String,
    /// Key state
    pub state: KeyState,
    /// Key tags
    pub tags: Vec<String>,
}

/// Key states
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum KeyState {
    /// Key is active and can be used
    Active,
    /// Key is disabled
    Disabled,
    /// Key is pending deletion
    PendingDeletion,
    /// Key has been destroyed
    Destroyed,
}

/// In-memory key store (for development/testing)
/// Production should use HSM/KMS
pub struct KeyStore {
    keys: Arc<Mutex<HashMap<String, StoredKey>>>,
}

struct StoredKey {
    metadata: KeyMetadata,
    key_material: Vec<u8>,
}

impl KeyStore {
    /// Create new key store
    pub fn new() -> Self {
        Self {
            keys: Arc::new(Mutex::new(HashMap::new())),
        }
    }
    
    /// Store a key
    pub fn store(&self, metadata: KeyMetadata, key_material: Vec<u8>) -> Result<()> {
        let mut keys = self.keys.lock()
            .map_err(|e| CryptoError::HsmError(format!("Lock failed: {:?}", e)))?;
        
        let stored = StoredKey {
            metadata,
            key_material,
        };
        
        keys.insert(stored.metadata.key_id.clone(), stored);
        Ok(())
    }
    
    /// Retrieve a key
    pub fn retrieve(&self, key_id: &str) -> Result<(KeyMetadata, Vec<u8>)> {
        let keys = self.keys.lock()
            .map_err(|e| CryptoError::HsmError(format!("Lock failed: {:?}", e)))?;
        
        let stored = keys.get(key_id)
            .ok_or_else(|| CryptoError::InvalidKey(format!("Key not found: {}", key_id)))?;
        
        // Check key state
        match stored.metadata.state {
            KeyState::Active => {},
            KeyState::Disabled => {
                return Err(CryptoError::InvalidKey("Key is disabled".to_string()));
            }
            KeyState::PendingDeletion | KeyState::Destroyed => {
                return Err(CryptoError::InvalidKey("Key is not available".to_string()));
            }
        }
        
        Ok((stored.metadata.clone(), stored.key_material.clone()))
    }
    
    /// List all keys
    pub fn list_keys(&self) -> Result<Vec<KeyMetadata>> {
        let keys = self.keys.lock()
            .map_err(|e| CryptoError::HsmError(format!("Lock failed: {:?}", e)))?;
        
        Ok(keys.values()
            .map(|k| k.metadata.clone())
            .collect())
    }
    
    /// Disable a key
    pub fn disable(&self, key_id: &str) -> Result<()> {
        let mut keys = self.keys.lock()
            .map_err(|e| CryptoError::HsmError(format!("Lock failed: {:?}", e)))?;
        
        if let Some(stored) = keys.get_mut(key_id) {
            stored.metadata.state = KeyState::Disabled;
            Ok(())
        } else {
            Err(CryptoError::InvalidKey(format!("Key not found: {}", key_id)))
        }
    }
    
    /// Schedule key for deletion
    pub fn schedule_deletion(&self, key_id: &str) -> Result<()> {
        let mut keys = self.keys.lock()
            .map_err(|e| CryptoError::HsmError(format!("Lock failed: {:?}", e)))?;
        
        if let Some(stored) = keys.get_mut(key_id) {
            stored.metadata.state = KeyState::PendingDeletion;
            // In production, set deletion date (e.g., 30 days)
            Ok(())
        } else {
            Err(CryptoError::InvalidKey(format!("Key not found: {}", key_id)))
        }
    }
    
    /// Destroy a key immediately
    pub fn destroy(&self, key_id: &str) -> Result<()> {
        let mut keys = self.keys.lock()
            .map_err(|e| CryptoError::HsmError(format!("Lock failed: {:?}", e)))?;
        
        if let Some(stored) = keys.get_mut(key_id) {
            // Overwrite key material
            let mut key_material = std::mem::take(&mut stored.key_material);
            for byte in key_material.iter_mut() {
                *byte = 0;
            }
            
            stored.metadata.state = KeyState::Destroyed;
            Ok(())
        } else {
            Err(CryptoError::InvalidKey(format!("Key not found: {}", key_id)))
        }
    }
}

impl Default for KeyStore {
    fn default() -> Self {
        Self::new()
    }
}

/// Generate unique key ID
pub fn generate_key_id() -> String {
    use rand::Rng;
    let mut rng = rand::thread_rng();
    let bytes: Vec<u8> = (0..16).map(|_| rng.gen()).collect();
    format!("key-{}", hex::encode(bytes))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_key_store() {
        let store = KeyStore::new();
        
        let metadata = KeyMetadata {
            key_id: generate_key_id(),
            version: 1,
            created_at: 0,
            expires_at: 0,
            usage: KeyUsage::DataEncryption,
            algorithm: "AES-256-GCM".to_string(),
            state: KeyState::Active,
            tags: vec!["test".to_string()],
        };
        
        let key_material = vec![0x42; 32];
        
        // Store key
        store.store(metadata.clone(), key_material.clone()).unwrap();
        
        // Retrieve key
        let (retrieved_meta, retrieved_key) = store.retrieve(&metadata.key_id).unwrap();
        assert_eq!(retrieved_meta.key_id, metadata.key_id);
        assert_eq!(retrieved_key, key_material);
        
        // Disable key
        store.disable(&metadata.key_id).unwrap();
        let result = store.retrieve(&metadata.key_id);
        assert!(result.is_err());
        
        // List keys
        let keys = store.list_keys().unwrap();
        assert_eq!(keys.len(), 1);
    }
}
