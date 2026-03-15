//! Safety Guard - Enforces security constraints and human oversight

use crate::models::*;
use std::collections::HashMap;
use tokio::sync::RwLock;
use tracing::{info, warn, error};
use chrono::Utc;

/// Safety constraints for crypto operations
pub const MAX_PARALLEL_KEY_ROTATIONS: usize = 2;
pub const MAX_RETRY_ATTEMPTS: u32 = 3;
pub const AGENT_STARVATION_THRESHOLD_SECS: i64 = 300; // 5 minutes

/// Safety Guard enforces all security constraints
pub struct SafetyGuard {
    /// Track active key rotations (limited concurrency)
    active_key_rotations: RwLock<usize>,
    /// Track agent states for starvation detection
    agent_states: RwLock<HashMap<Uuid, AgentState>>,
    /// Pending destructive operations awaiting approval
    pending_approvals: RwLock<HashMap<Uuid, PendingApproval>>,
    /// Safety violations log
    violations: RwLock<Vec<SafetyViolation>>,
}

struct AgentState {
    last_heartbeat: chrono::DateTime<Utc>,
    pending_tasks: usize,
    executing_tasks: usize,
}

struct PendingApproval {
    task_id: Uuid,
    requested_at: chrono::DateTime<Utc>,
    approvers: Vec<String>,
}

#[derive(Debug, Clone)]
struct SafetyViolation {
    timestamp: chrono::DateTime<Utc>,
    violation_type: ViolationType,
    description: String,
    task_id: Option<Uuid>,
}

#[derive(Debug, Clone)]
enum ViolationType {
    ConcurrentOperationLimit,
    MissingHumanApproval,
    InvalidSignature,
    AgentStarvation,
}

impl SafetyGuard {
    pub fn new() -> Self {
        Self {
            active_key_rotations: RwLock::new(0),
            agent_states: RwLock::new(HashMap::new()),
            pending_approvals: RwLock::new(HashMap::new()),
            violations: RwLock::new(Vec::new()),
        }
    }
    
    /// Check if task can be executed safely
    pub async fn check_safety(&self, task: &Task) -> SafetyResult {
        // Rule 1: Destructive crypto ops require human approval
        if self.is_destructive_crypto_op(task) {
            if !self.has_valid_human_approval(task).await {
                return SafetyResult::RequiresHumanApproval {
                    reason: format!("Destructive operation {:?} requires signed human approval", task.task_type),
                    affected_assets: task.affected_assets.clone(),
                };
            }
        }
        
        // Rule 2: Limit parallel key rotations
        if self.is_key_rotation(task) {
            let active = *self.active_key_rotations.read().await;
            if active >= MAX_PARALLEL_KEY_ROTATIONS {
                return SafetyResult::Throttle {
                    reason: format!("Max parallel key rotations ({}) reached", MAX_PARALLEL_KEY_ROTATIONS),
                    retry_after_secs: 60,
                };
            }
        }
        
        // Rule 3: Check retry limits
        if task.retry_count >= task.max_retries {
            return SafetyResult::MaxRetriesExceeded {
                task_id: task.id,
                attempts: task.retry_count,
            };
        }
        
        // Rule 4: Verify affected assets are documented
        if task.affected_assets.is_empty() && self.requires_asset_documentation(task) {
            return SafetyResult::MissingInformation {
                field: "affected_assets".to_string(),
                reason: "High-impact operations must document affected assets".to_string(),
            };
        }
        
        SafetyResult::Safe
    }
    
    /// Mark key rotation as started/finished
    pub async fn track_key_rotation(&self, started: bool) {
        let mut active = self.active_key_rotations.write().await;
        if started {
            *active += 1;
        } else {
            *active = active.saturating_sub(1);
        }
    }
    
    /// Record human approval with signature verification
    pub async fn record_approval(
        &self,
        task_id: Uuid,
        approver: String,
        signature: String,
    ) -> Result<(), SafetyError> {
        // In production: verify Ed25519 signature
        if signature.len() < 32 {
            self.log_violation(ViolationType::InvalidSignature, 
                "Invalid approval signature length", Some(task_id)).await;
            return Err(SafetyError::InvalidSignature);
        }
        
        let mut approvals = self.pending_approvals.write().await;
        approvals.insert(task_id, PendingApproval {
            task_id,
            requested_at: Utc::now(),
            approvers: vec![approver],
        });
        
        info!("Recorded human approval for task {}", task_id);
        Ok(())
    }
    
    /// Check for agent starvation and trigger reassignments
    pub async fn check_agent_health(&mut self) -> Result<(), SafetyError> {
        let states = self.agent_states.read().await;
        let now = Utc::now();
        
        for (agent_id, state) in states.iter() {
            let secs_since_heartbeat = now.signed_duration_since(state.last_heartbeat).num_seconds();
            
            // Detect starvation: has pending but not executing
            if state.pending_tasks > 0 && state.executing_tasks == 0 {
                if secs_since_heartbeat > AGENT_STARVATION_THRESHOLD_SECS {
                    warn!("Agent {} appears starved ({}s since heartbeat)", agent_id, secs_since_heartbeat);
                    self.log_violation(ViolationType::AgentStarvation,
                        &format!("Agent {} starvation detected", agent_id), None).await;
                    
                    // Trigger escalation
                    return Err(SafetyError::AgentStarvation(*agent_id));
                }
            }
        }
        
        Ok(())
    }
    
    /// Update agent heartbeat
    pub async fn update_agent_heartbeat(&self, agent_id: Uuid, pending: usize, executing: usize) {
        let mut states = self.agent_states.write().await;
        states.insert(agent_id, AgentState {
            last_heartbeat: Utc::now(),
            pending_tasks: pending,
            executing_tasks: executing,
        });
    }
    
    /// Trigger safe rollback playbook
    pub async fn trigger_rollback(&self, task_id: Uuid) -> RollbackPlan {
        warn!("Triggering rollback for task {}", task_id);
        
        RollbackPlan {
            task_id,
            steps: vec![
                RollbackStep::StopOperation,
                RollbackStep::RestoreState,
                RollbackStep::VerifyIntegrity,
                RollbackStep::NotifyOperators,
            ],
            estimated_duration_secs: 30,
        }
    }
    
    // Helper methods
    
    fn is_destructive_crypto_op(&self, task: &Task) -> bool {
        matches!(task.task_type, 
            TaskType::DestroyKey | 
            TaskType::RotateMasterKey |
            TaskType::SealVault
        )
    }
    
    fn is_key_rotation(&self, task: &Task) -> bool {
        matches!(task.task_type, 
            TaskType::RotateMasterKey | TaskType::RotateDataKey
        )
    }
    
    fn requires_asset_documentation(&self, task: &Task) -> bool {
        matches!(task.safety_classification,
            SafetyClassification::Destructive | SafetyClassification::Critical
        )
    }
    
    async fn has_valid_human_approval(&self, task: &Task) -> bool {
        let approvals = self.pending_approvals.read().await;
        approvals.contains_key(&task.id)
    }
    
    async fn log_violation(&self, vtype: ViolationType, desc: &str, task_id: Option<Uuid>) {
        let mut violations = self.violations.write().await;
        violations.push(SafetyViolation {
            timestamp: Utc::now(),
            violation_type: vtype,
            description: desc.to_string(),
            task_id,
        });
        error!("SAFETY VIOLATION: {:?} - {}", vtype, desc);
    }
}

pub enum SafetyResult {
    Safe,
    RequiresHumanApproval {
        reason: String,
        affected_assets: Vec<String>,
    },
    Throttle {
        reason: String,
        retry_after_secs: u64,
    },
    MaxRetriesExceeded {
        task_id: Uuid,
        attempts: u32,
    },
    MissingInformation {
        field: String,
        reason: String,
    },
}

#[derive(Debug)]
pub enum SafetyError {
    InvalidSignature,
    AgentStarvation(Uuid),
    ConcurrentLimitExceeded,
}

pub struct RollbackPlan {
    pub task_id: Uuid,
    pub steps: Vec<RollbackStep>,
    pub estimated_duration_secs: u64,
}

pub enum RollbackStep {
    StopOperation,
    RestoreState,
    VerifyIntegrity,
    NotifyOperators,
}
