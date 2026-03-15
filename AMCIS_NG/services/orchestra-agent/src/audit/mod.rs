//! Immutable Audit Ledger - Blockchain-backed tamper-proof audit trail

use crate::models::*;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha3::{Sha3_256, Digest};
use uuid::Uuid;
use tracing::{info, debug};

/// Immutable audit entry with hash chaining
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEntry {
    pub entry_id: Uuid,
    pub timestamp: DateTime<Utc>,
    pub entry_type: AuditEntryType,
    pub actor: String,
    pub action: String,
    pub resource: String,
    pub details: serde_json::Value,
    pub previous_hash: String,
    pub entry_hash: String,
    pub signature: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AuditEntryType {
    TaskCreated,
    TaskAssigned,
    TaskStarted,
    TaskCompleted,
    TaskFailed,
    TaskRolledBack,
    HumanApprovalRequested,
    HumanApprovalGranted,
    HumanApprovalRejected,
    PolicyApplied,
    SafetyViolation,
    EscalationTriggered,
    AgentRegistered,
    AgentDeregistered,
    AgentStarvationDetected,
}

/// Audit Ledger maintains the immutable chain
pub struct AuditLedger {
    entries: Vec<AuditEntry>,
    last_hash: String,
}

impl AuditLedger {
    pub async fn new() -> anyhow::Result<Self> {
        let genesis_hash = Self::calculate_genesis_hash();
        info!("Initializing Audit Ledger with genesis hash: {}", &genesis_hash[..16]);
        
        Ok(Self {
            entries: Vec::new(),
            last_hash: genesis_hash,
        })
    }
    
    /// Record a new audit entry with hash chaining
    pub async fn record(&mut self, entry_type: AuditEntryType, actor: &str, action: &str, 
                       resource: &str, details: serde_json::Value) -> AuditEntry {
        let entry_id = Uuid::new_v4();
        let timestamp = Utc::now();
        
        // Calculate hash from previous hash + current data
        let entry_hash = self.calculate_hash(&entry_id, &timestamp, &entry_type, 
                                              actor, action, resource, &details);
        
        let entry = AuditEntry {
            entry_id,
            timestamp,
            entry_type,
            actor: actor.to_string(),
            action: action.to_string(),
            resource: resource.to_string(),
            details,
            previous_hash: self.last_hash.clone(),
            entry_hash: entry_hash.clone(),
            signature: None,
        };
        
        // In production: Sign with orchestra agent's Ed25519 key
        // entry.signature = Some(self.sign_entry(&entry));
        
        self.entries.push(entry.clone());
        self.last_hash = entry_hash;
        
        debug!("Audit entry recorded: {} -> {}", entry_id, &entry_hash[..16]);
        entry
    }
    
    /// Record task lifecycle event
    pub async fn record_task_event(&mut self, task: &Task, event_type: AuditEntryType) -> AuditEntry {
        let details = serde_json::json!({
            "task_id": task.id,
            "task_type": format!("{:?}", task.task_type),
            "priority": format!("{:?}", task.priority),
            "assigned_agent": task.assigned_agent,
            "safety_classification": format!("{:?}", task.safety_classification),
            "affected_assets": task.affected_assets,
            "retry_count": task.retry_count,
        });
        
        self.record(
            event_type,
            "orchestra_agent",
            &format!("{:?}", task.task_type),
            &task.id.to_string(),
            details,
        ).await
    }
    
    /// Record human approval event
    pub async fn record_human_approval(&mut self, task_id: Uuid, approver: &str, 
                                       approved: bool, reason: Option<&str>) -> AuditEntry {
        let details = serde_json::json!({
            "task_id": task_id,
            "approver": approver,
            "decision": if approved { "approved" } else { "rejected" },
            "reason": reason,
        });
        
        self.record(
            if approved { AuditEntryType::HumanApprovalGranted } else { AuditEntryType::HumanApprovalRejected },
            approver,
            if approved { "APPROVE" } else { "REJECT" },
            &task_id.to_string(),
            details,
        ).await
    }
    
    /// Record safety violation
    pub async fn record_safety_violation(&mut self, violation_type: &str, description: &str,
                                          task_id: Option<Uuid>) -> AuditEntry {
        let details = serde_json::json!({
            "violation_type": violation_type,
            "description": description,
            "task_id": task_id,
        });
        
        self.record(
            AuditEntryType::SafetyViolation,
            "safety_guard",
            "SAFETY_VIOLATION",
            &task_id.map(|id| id.to_string()).unwrap_or_default(),
            details,
        ).await
    }
    
    /// Verify chain integrity
    pub fn verify_chain(&self) -> ChainVerificationResult {
        let mut current_hash = self.calculate_genesis_hash();
        
        for (i, entry) in self.entries.iter().enumerate() {
            // Check previous hash matches
            if entry.previous_hash != current_hash {
                return ChainVerificationResult::Broken {
                    at_index: i,
                    expected: current_hash,
                    found: entry.previous_hash.clone(),
                };
            }
            
            // Verify entry hash
            let expected_hash = self.calculate_hash(
                &entry.entry_id, &entry.timestamp, &entry.entry_type,
                &entry.actor, &entry.action, &entry.resource, &entry.details
            );
            
            if entry.entry_hash != expected_hash {
                return ChainVerificationResult::Tampered {
                    at_index: i,
                    entry_id: entry.entry_id,
                };
            }
            
            current_hash = entry.entry_hash.clone();
        }
        
        ChainVerificationResult::Valid {
            entry_count: self.entries.len(),
            last_hash: current_hash,
        }
    }
    
    /// Export entries for external storage (blockchain anchor)
    pub fn export_for_anchor(&self) -> Vec<AnchorEntry> {
        self.entries.iter().map(|e| AnchorEntry {
            timestamp: e.timestamp,
            entry_hash: e.entry_hash.clone(),
            previous_hash: e.previous_hash.clone(),
        }).collect()
    }
    
    /// Get entries by type
    pub fn get_entries_by_type(&self, entry_type: AuditEntryType) -> Vec<&AuditEntry> {
        self.entries.iter()
            .filter(|e| std::mem::discriminant(&e.entry_type) == std::mem::discriminant(&entry_type))
            .collect()
    }
    
    // Private helpers
    
    fn calculate_hash(&self, entry_id: &Uuid, timestamp: &DateTime<Utc>, 
                      entry_type: &AuditEntryType, actor: &str, action: &str,
                      resource: &str, details: &serde_json::Value) -> String {
        let data = format!(
            "{}:{}:{:?}:{}:{}:{}:{}:{}",
            entry_id, timestamp, entry_type, actor, action, resource, 
            details, self.last_hash
        );
        
        let mut hasher = Sha3_256::new();
        hasher.update(data.as_bytes());
        format!("{:x}", hasher.finalize())
    }
    
    fn calculate_genesis_hash() -> String {
        let mut hasher = Sha3_256::new();
        hasher.update(b"AMCIS_ORCHESTRA_AUDIT_LEDGER_GENESIS_2024");
        format!("{:x}", hasher.finalize())
    }
}

pub enum ChainVerificationResult {
    Valid { entry_count: usize, last_hash: String },
    Broken { at_index: usize, expected: String, found: String },
    Tampered { at_index: usize, entry_id: Uuid },
}

#[derive(Debug, Clone, Serialize)]
pub struct AnchorEntry {
    pub timestamp: DateTime<Utc>,
    pub entry_hash: String,
    pub previous_hash: String,
}
