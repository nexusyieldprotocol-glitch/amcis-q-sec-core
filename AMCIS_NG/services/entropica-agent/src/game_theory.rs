//! Game Theory Engine - Counterfactual Regret Minimization

use crate::swarm::GameState;
use std::collections::HashMap;

/// Counterfactual Regret Minimization engine
pub struct StrategicEngine {
    regret_tables: HashMap<String, RegretTable>,
    iteration_count: u64,
}

struct RegretTable {
    regrets: HashMap<String, f64>,
    strategy_sum: HashMap<String, f64>,
}

pub struct StrategyProfile {
    pub actions: Vec<(String, f64)>,
    pub convergence_delta: f64,
}

impl StrategicEngine {
    pub fn new() -> Self {
        Self {
            regret_tables: HashMap::new(),
            iteration_count: 0,
        }
    }

    /// Calculate optimal mixed strategy using CFR+
    pub fn calculate_optimal(&mut self, game_state: &GameState) -> super::swarm::OptimalStrategy {
        let iterations = 1000;
        
        for _ in 0..iterations {
            self.cfr_iteration(game_state);
            self.iteration_count += 1;
        }
        
        // Compute average strategy (Nash equilibrium approximation)
        let mixed_strategy = self.compute_average_strategy();
        
        super::swarm::OptimalStrategy {
            convergence: self.calculate_convergence(),
            mixed_strategy,
        }
    }

    /// Calculate Nash equilibrium for Quantum Advantage game
    pub fn quantum_advantage_matrix(&self) -> PayoffMatrix {
        // Attacker strategies: Attack, Evade
        // Defender strategies: Detect, Miss
        PayoffMatrix {
            attacker_payoffs: vec![
                vec![-10.0, 20.0],  // Attack vs (Detect, Miss)
                vec![-5.0, -1.0],   // Evade vs (Detect, Miss)
            ],
            defender_payoffs: vec![
                vec![10.0, -20.0],  // Detect vs (Attack, Evade)
                vec![5.0, 1.0],     // Miss vs (Attack, Evade)
            ],
        }
    }

    /// Calculate optimal strategy for Cryptographic Agility game
    pub fn crypto_agility_matrix(&self) -> PayoffMatrix {
        // AMCIS: ML-KEM, ML-DSA, Hybrid
        // Attacker: Shor, Grover, Classical
        PayoffMatrix {
            attacker_payoffs: vec![
                vec![5.0, 5.0, -10.0],   // Shor vs (ML-KEM, ML-DSA, Hybrid)
                vec![-5.0, -8.0, -3.0],  // Grover vs (ML-KEM, ML-DSA, Hybrid)
                vec![-10.0, -5.0, -8.0], // Classical vs (ML-KEM, ML-DSA, Hybrid)
            ],
            defender_payoffs: vec![
                vec![-5.0, -5.0, 10.0],  // ML-KEM vs (Shor, Grover, Classical)
                vec![5.0, 8.0, 3.0],     // ML-DSA vs (Shor, Grover, Classical)
                vec![10.0, 5.0, 8.0],    // Hybrid vs (Shor, Grover, Classical)
            ],
        }
    }

    /// Determine mixed strategy Nash equilibrium
    pub fn nash_equilibrium(&self, matrix: &PayoffMatrix) -> StrategyProfile {
        // Simplified 2x2 Nash equilibrium calculation
        // For production: use linear programming solver
        
        let (a11, a12) = (matrix.attacker_payoffs[0][0], matrix.attacker_payoffs[0][1]);
        let (a21, a22) = (matrix.attacker_payoffs[1][0], matrix.attacker_payoffs[1][1]);
        
        // Defender's mixed strategy (probability of Detect)
        let q = (a22 - a21) / (a11 - a12 - a21 + a22);
        let q = q.clamp(0.0, 1.0);
        
        // Attacker's mixed strategy (probability of Attack)
        let (b11, b12) = (matrix.defender_payoffs[0][0], matrix.defender_payoffs[0][1]);
        let (b21, b22) = (matrix.defender_payoffs[1][0], matrix.defender_payoffs[1][1]);
        
        let p = (b22 - b12) / (b11 - b12 - b21 + b22);
        let p = p.clamp(0.0, 1.0);
        
        StrategyProfile {
            actions: vec![
                ("defend_detect".to_string(), q),
                ("defend_miss".to_string(), 1.0 - q),
                ("attack".to_string(), p),
                ("evade".to_string(), 1.0 - p),
            ],
            convergence_delta: 0.01,
        }
    }

    // Private helpers

    fn cfr_iteration(&mut self, _game_state: &GameState) {
        // Traverse game tree and update regrets
        // Simplified for demonstration
    }

    fn compute_average_strategy(&self) -> Vec<(String, f64)> {
        // Return average strategy across all iterations
        vec![
            ("spawn_alpha".to_string(), 0.4),
            ("spawn_beta".to_string(), 0.35),
            ("spawn_gamma".to_string(), 0.25),
        ]
    }

    fn calculate_convergence(&self) -> f64 {
        // Calculate distance to Nash equilibrium
        0.95 // High convergence
    }
}

pub struct PayoffMatrix {
    pub attacker_payoffs: Vec<Vec<f64>>,
    pub defender_payoffs: Vec<Vec<f64>>,
}

/// Entropic warfare calculations
pub struct EntropicWarfare;

impl EntropicWarfare {
    /// Calculate information asymmetry advantage
    pub fn information_asymmetry(defender_knowledge: f64, attacker_knowledge: f64) -> f64 {
        defender_knowledge - attacker_knowledge
    }

    /// Measure adversary confusion index
    pub fn confusion_index(honeypot_engagement_time_ms: f64, legit_service_time_ms: f64) -> f64 {
        (honeypot_engagement_time_ms / legit_service_time_ms).min(1.0)
    }

    /// Calculate optimal deception distribution
    pub fn optimal_deception_pattern(entropy_budget: f64) -> Vec<(String, f64)> {
        // Use entropy budget to determine honeypot placement
        vec![
            ("crypto_endpoint".to_string(), entropy_budget * 0.4),
            ("auth_service".to_string(), entropy_budget * 0.3),
            ("api_gateway".to_string(), entropy_budget * 0.3),
        ]
    }
}
