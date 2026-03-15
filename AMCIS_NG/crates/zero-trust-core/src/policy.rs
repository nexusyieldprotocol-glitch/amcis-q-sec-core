//! Policy engine for Zero Trust

use super::*;

/// Policy evaluation result
pub enum PolicyResult {
    Allow,
    Deny(String),
    Challenge(Vec<ChallengeType>),
}

/// Policy trait
pub trait Policy: Send + Sync {
    /// Evaluate request against policy
    fn evaluate(&self, request: &AccessRequest) -> PolicyResult;
    
    /// Get policy name
    fn name(&self) -> &str;
}

/// Time-based access policy
pub struct TimeBasedPolicy {
    allowed_hours: Vec<u8>,
    timezone: chrono::FixedOffset,
}

impl TimeBasedPolicy {
    /// Create new time-based policy
    pub fn new(allowed_hours: Vec<u8>, timezone: chrono::FixedOffset) -> Self {
        Self {
            allowed_hours,
            timezone,
        }
    }
}

impl Policy for TimeBasedPolicy {
    fn evaluate(&self, request: &AccessRequest) -> PolicyResult {
        let local_time = request.timestamp.with_timezone(&self.timezone);
        let hour = local_time.hour() as u8;
        
        if self.allowed_hours.contains(&hour) {
            PolicyResult::Allow
        } else {
            PolicyResult::Deny("Access denied outside business hours".to_string())
        }
    }
    
    fn name(&self) -> &str {
        "time_based"
    }
}

/// Location-based policy
pub struct LocationPolicy {
    allowed_countries: Vec<String>,
    blocked_countries: Vec<String>,
}

impl LocationPolicy {
    /// Create location policy
    pub fn new(allowed: Vec<String>, blocked: Vec<String>) -> Self {
        Self {
            allowed_countries: allowed,
            blocked_countries: blocked,
        }
    }
}

impl Policy for LocationPolicy {
    fn evaluate(&self, request: &AccessRequest) -> PolicyResult {
        if let Some(ref location) = request.device.location {
            if self.blocked_countries.contains(&location.country) {
                return PolicyResult::Deny(format!(
                    "Access blocked from country: {}",
                    location.country
                ));
            }
            
            if !self.allowed_countries.is_empty() 
                && !self.allowed_countries.contains(&location.country) {
                return PolicyResult::Deny(format!(
                    "Access not allowed from country: {}",
                    location.country
                ));
            }
        }
        
        PolicyResult::Allow
    }
    
    fn name(&self) -> &str {
        "location"
    }
}

/// Device trust policy
pub struct DeviceTrustPolicy {
    min_trust_score: f64,
    require_encryption: bool,
    require_edr: bool,
}

impl DeviceTrustPolicy {
    /// Create device trust policy
    pub fn new(min_score: f64, require_encryption: bool, require_edr: bool) -> Self {
        Self {
            min_trust_score: min_score,
            require_encryption,
            require_edr,
        }
    }
}

impl Policy for DeviceTrustPolicy {
    fn evaluate(&self, request: &AccessRequest) -> PolicyResult {
        let trust_score = calculate_device_trust(&request.device);
        
        if trust_score < self.min_trust_score {
            return PolicyResult::Deny(format!(
                "Device trust score {} below minimum {}",
                trust_score, self.min_trust_score
            ));
        }
        
        if self.require_encryption && !request.device.security_posture.encryption_enabled {
            return PolicyResult::Challenge(vec![ChallengeType::Mfa]);
        }
        
        if self.require_edr && !request.device.security_posture.edr_active {
            return PolicyResult::Deny("EDR required but not active".to_string());
        }
        
        PolicyResult::Allow
    }
    
    fn name(&self) -> &str {
        "device_trust"
    }
}
