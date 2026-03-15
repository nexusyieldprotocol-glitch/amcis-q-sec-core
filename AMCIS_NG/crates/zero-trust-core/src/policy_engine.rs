//! Policy Engine - Real-time policy evaluation

use crate::{AccessRequest, AccessDecision, DeviceContext};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::{info, debug};

/// Policy definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Policy {
    pub id: String,
    pub name: String,
    pub enabled: bool,
    pub priority: i32,
    pub rules: Vec<Rule>,
    pub action: PolicyAction,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Rule {
    TimeWindow { start_hour: u8, end_hour: u8 },
    Location { allowed_countries: Vec<String> },
    DeviceTrust { min_score: f64 },
    DeviceCompliance { required: bool },
    MfaRequired,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PolicyAction {
    Allow,
    Deny { reason: String },
    RequireMfa,
    RequireApproval,
}

/// Policy engine
pub struct PolicyEngine {
    policies: Vec<Policy>,
}

impl PolicyEngine {
    pub fn new() -> Self {
        Self { policies: Vec::new() }
    }
    
    pub fn add_policy(&mut self, policy: Policy) {
        self.policies.push(policy);
        // Sort by priority (higher first)
        self.policies.sort_by(|a, b| b.priority.cmp(&a.priority));
    }
    
    pub fn evaluate(&self, request: &AccessRequest) -> AccessDecision {
        debug!("Evaluating access request for user: {}", request.user_id);
        
        for policy in &self.policies {
            if !policy.enabled {
                continue;
            }
            
            let all_rules_match = policy.rules.iter().all(|rule| {
                self.evaluate_rule(rule, request)
            });
            
            if all_rules_match {
                info!("Policy '{}' matched", policy.name);
                return match &policy.action {
                    PolicyAction::Allow => AccessDecision::Allow,
                    PolicyAction::Deny { reason } => AccessDecision::Deny(reason.clone()),
                    PolicyAction::RequireMfa => AccessDecision::RequireMfa,
                    PolicyAction::RequireApproval => AccessDecision::RequireApproval,
                };
            }
        }
        
        // Default deny
        AccessDecision::Deny("No matching policy found".to_string())
    }
    
    fn evaluate_rule(&self, rule: &Rule, request: &AccessRequest) -> bool {
        match rule {
            Rule::TimeWindow { start_hour, end_hour } => {
                let hour = request.timestamp.hour() as u8;
                hour >= *start_hour && hour <= *end_hour
            }
            Rule::Location { allowed_countries } => {
                request.location.as_ref()
                    .map(|loc| allowed_countries.contains(&loc.country))
                    .unwrap_or(false)
            }
            Rule::DeviceTrust { min_score } => {
                request.device_trust_score >= *min_score
            }
            Rule::DeviceCompliance { required } => {
                !required || request.device_compliant
            }
            Rule::MfaRequired => {
                request.mfa_verified
            }
        }
    }
    
    /// Calculate device trust score
    pub fn calculate_device_trust(device: &DeviceContext) -> f64 {
        let mut score = 100.0;
        
        // Security posture deductions
        if !device.encryption_enabled { score -= 20.0; }
        if !device.firewall_active { score -= 15.0; }
        if !device.av_installed { score -= 10.0; }
        if !device.edr_active { score -= 15.0; }
        
        // Patch level (days since last patch)
        let days_since_patch = device.patch_age_days;
        if days_since_patch > 30 { score -= 20.0; }
        else if days_since_patch > 7 { score -= 10.0; }
        
        // Compliance
        if !device.compliant { score -= 25.0; }
        
        score.max(0.0) / 100.0 // Normalize to 0.0-1.0
    }
}

/// Simplified access request for policy evaluation
pub struct AccessRequest {
    pub user_id: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub location: Option<Location>,
    pub device_trust_score: f64,
    pub device_compliant: bool,
    pub mfa_verified: bool,
}

pub struct Location {
    pub country: String,
}

pub enum AccessDecision {
    Allow,
    Deny(String),
    RequireMfa,
    RequireApproval,
}

#[derive(Default)]
pub struct DeviceContext {
    pub encryption_enabled: bool,
    pub firewall_active: bool,
    pub av_installed: bool,
    pub edr_active: bool,
    pub patch_age_days: i32,
    pub compliant: bool,
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_policy_time_window() {
        let mut engine = PolicyEngine::new();
        engine.add_policy(Policy {
            id: "1".to_string(),
            name: "Business Hours".to_string(),
            enabled: true,
            priority: 100,
            rules: vec![Rule::TimeWindow { start_hour: 9, end_hour: 17 }],
            action: PolicyAction::Allow,
        });
        
        // Test at 10 AM - should allow
        let request = AccessRequest {
            user_id: "user1".to_string(),
            timestamp: chrono::DateTime::from_timestamp(1706710800, 0).unwrap(), // 10 AM UTC
            location: None,
            device_trust_score: 0.8,
            device_compliant: true,
            mfa_verified: true,
        };
        
        match engine.evaluate(&request) {
            AccessDecision::Allow => (),
            _ => panic!("Should allow during business hours"),
        }
    }
    
    #[test]
    fn test_device_trust_calculation() {
        let device = DeviceContext {
            encryption_enabled: true,
            firewall_active: true,
            av_installed: true,
            edr_active: true,
            patch_age_days: 1,
            compliant: true,
        };
        
        let score = PolicyEngine::calculate_device_trust(&device);
        assert!(score > 0.9, "Fully compliant device should have high trust");
    }
}
