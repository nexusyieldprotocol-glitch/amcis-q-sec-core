//! Entropy Pool - Cryptographic randomness for unpredictability

use rand::{Rng, SeedableRng};
use rand::rngs::StdRng;
use sha3::{Sha3_256, Digest};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

/// Entropy pool for generating unpredictable behavior patterns
#[derive(Clone)]
pub struct EntropyPool {
    state: Arc<Mutex<EntropyState>>,
}

struct EntropyState {
    rng: StdRng,
    entropy_budget: f64,
    reseed_counter: u64,
}

impl EntropyPool {
    pub fn new() -> Self {
        let seed = Self::generate_seed();
        
        Self {
            state: Arc::new(Mutex::new(EntropyState {
                rng: StdRng::from_seed(seed),
                entropy_budget: 1.0,
                reseed_counter: 0,
            })),
        }
    }

    /// Get current entropy level (0.0 - 1.0)
    pub fn level(&self) -> f64 {
        self.state.lock().unwrap().entropy_budget
    }

    /// Consume entropy budget
    pub fn consume(&self, amount: f64) -> bool {
        let mut state = self.state.lock().unwrap();
        
        if state.entropy_budget >= amount {
            state.entropy_budget -= amount;
            true
        } else {
            false
        }
    }

    /// Reseed entropy pool
    pub fn reseed(&self) {
        let mut state = self.state.lock().unwrap();
        let new_seed = Self::generate_seed();
        state.rng = StdRng::from_seed(new_seed);
        state.entropy_budget = 1.0;
        state.reseed_counter += 1;
    }

    /// Generate random decision (true/false) based on probability
    pub fn decide(&self, probability: f64) -> bool {
        let mut state = self.state.lock().unwrap();
        state.rng.gen::<f64>() < probability
    }

    /// Generate random delay for timing obfuscation
    pub fn random_delay_ms(&self, min: u64, max: u64) -> u64 {
        let mut state = self.state.lock().unwrap();
        state.rng.gen_range(min..=max)
    }

    /// Generate chaotic but deterministic pattern
    pub fn chaotic_sequence(&self, length: usize) -> Vec<f64> {
        let mut state = self.state.lock().unwrap();
        (0..length)
            .map(|_| state.rng.gen::<f64>())
            .collect()
    }

    /// Generate seed from multiple entropy sources
    fn generate_seed() -> [u8; 32] {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        
        let mut hasher = Sha3_256::new();
        hasher.update(timestamp.to_be_bytes());
        hasher.update(b"ENTROPICA_v3_SEED");
        
        // In production: add quantum RNG, atmospheric noise, etc.
        
        let result = hasher.finalize();
        let mut seed = [0u8; 32];
        seed.copy_from_slice(&result);
        seed
    }
}

/// Timing obfuscation utilities
pub struct TimingObfuscation;

impl TimingObfuscation {
    /// Add random jitter to operation timing
    pub async fn jitter(base_duration_ms: u64, jitter_percent: f64) {
        let jitter_amount = (base_duration_ms as f64 * jitter_percent) as u64;
        let delay = rand::random::<u64>() % (jitter_amount * 2);
        
        tokio::time::sleep(tokio::time::Duration::from_millis(
            base_duration_ms + delay
        )).await;
    }

    /// Execute with randomized timing
    pub async fn execute_with_entropy<F, Fut>(f: F, entropy_pool: &EntropyPool) 
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future,
    {
        let delay = entropy_pool.random_delay_ms(10, 100);
        tokio::time::sleep(tokio::time::Duration::from_millis(delay)).await;
        f().await;
    }
}

/// Pattern obfuscation - make actions unpredictable
pub struct PatternObfuscation;

impl PatternObfuscation {
    /// Randomize scan order
    pub fn shuffle_targets<T>(targets: &mut Vec<T>, entropy_pool: &EntropyPool) {
        use rand::seq::SliceRandom;
        let mut state = entropy_pool.state.lock().unwrap();
        targets.shuffle(&mut state.rng);
    }

    /// Generate decoy traffic patterns
    pub fn generate_decoy_pattern(base_pattern: &[u8], entropy_pool: &EntropyPool) -> Vec<u8> {
        let noise = entropy_pool.chaotic_sequence(base_pattern.len());
        base_pattern
            .iter()
            .zip(noise.iter())
            .map(|(b, n)| b ^ (n * 255.0) as u8)
            .collect()
    }
}
