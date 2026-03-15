//! AMCIS Zero Trust Core
//! 
//! Implements Zero Trust Architecture:
//! - Continuous identity verification
//! - Device trust scoring
//! - Behavioral biometrics
//! - Micro-segmentation
//! - Just-in-time privilege elevation

#![warn(missing_docs)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::IpAddr;
use uuid::Uuid;

pub mod identity;
pub mod device_trust;
pub mod segmentation;
pub mod policy;

/// Identity with continuous verification
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Identity {
    pub id: Uuid,
    pub username: String,
    pub email: String,
    pub roles: Vec<String>,
    pub trust_score: f64,
    pub last_verified: chrono::DateTime<chrono::Utc>,
    pub mfa_enabled: bool,
    pub biometric_enrolled: bool,
}

/// Device context for trust evaluation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceContext {
    pub device_id: String,
    pub device_type: DeviceType,
    pub os_version: String,
    pub patch_level: String,
    pub security_posture: SecurityPosture,
    pub location: Option<GeoLocation>,
    pub ip_address: IpAddr,
}

/// Device types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DeviceType {
    Workstation,
    Server,
    Mobile,
    IoT,
    OT,
    Unknown,
}

/// Security posture assessment
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityPosture {
    pub score: f64,
    pub encryption_enabled: bool,
    pub firewall_active: bool,
    pub av_installed: bool,
    pub edr_active: bool,
    pub compliance_status: ComplianceStatus,
}

/// Compliance status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ComplianceStatus {
    Compliant,
    NonCompliant(Vec<String>),
    Unknown,
}

/// Geo location
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeoLocation {
    pub country: String,
    pub city: String,
    pub lat: f64,
    pub lon: f64,
}

/// Access request
#[derive(Debug, Clone)]
pub struct AccessRequest {
    pub identity: Identity,
    pub device: DeviceContext,
    pub resource: String,
    pub action: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// Access decision
#[derive(Debug, Clone)]
pub enum AccessDecision {
    Allow,
    Deny(String),
    Challenge(Vec<ChallengeType>),
    Elevate(Vec<String>),
}

/// Challenge types
#[derive(Debug, Clone)]
pub enum ChallengeType {
    Mfa,
    Biometric,
    Password,
    HardwareToken,
}

/// Zero Trust Engine
pub struct ZeroTrustEngine {
    policies: Vec<Box<dyn policy::Policy>>,
}

impl ZeroTrustEngine {
    /// Create new engine
    pub fn new() -> Self {
        Self {
            policies: Vec::new(),
        }
    }
    
    /// Evaluate access request
    pub fn evaluate(&self, request: &AccessRequest) -> AccessDecision {
        // Check all policies
        for policy in &self.policies {
            match policy.evaluate(request) {
                policy::PolicyResult::Allow => continue,
                policy::PolicyResult::Deny(reason) => return AccessDecision::Deny(reason),
                policy::PolicyResult::Challenge(challenges) => {
                    return AccessDecision::Challenge(challenges)
                }
            }
        }
        
        AccessDecision::Allow
    }
}

/// Calculate device trust score
pub fn calculate_device_trust(device: &DeviceContext) -> f64 {
    let mut score = 100.0;
    
    // Deduct for security issues
    if !device.security_posture.encryption_enabled {
        score -= 20.0;
    }
    if !device.security_posture.firewall_active {
        score -= 15.0;
    }
    if !device.security_posture.av_installed {
        score -= 10.0;
    }
    if !device.security_posture.edr_active {
        score -= 15.0;
    }
    
    match device.security_posture.compliance_status {
        ComplianceStatus::Compliant => (),
        ComplianceStatus::NonCompliant(_) => score -= 30.0,
        ComplianceStatus::Unknown => score -= 10.0,
    }
    
    score.max(0.0)
}
