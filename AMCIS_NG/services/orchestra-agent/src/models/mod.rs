//! Core data models for Orchestra Agent

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Agent registration and state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Agent {
    pub id: Uuid,
    pub name: String,
    pub agent_type: AgentType,
    pub status: AgentStatus,
    pub capabilities: Vec<Capability>,
    pub last_heartbeat: DateTime<Utc>,
    pub current_load: u32,
    pub max_concurrent_tasks: u32,
    pub metadata: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AgentType {
    CryptoPqc,
    NetworkGuard,
    EndpointShield,
    ThreatIntel,
    Vault,
    Compliance,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum AgentStatus {
    Online,
    Busy,
    Offline,
    Error,
    Starving,  // Has pending tasks but not executing
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Capability {
    KemKeygen,
    KemEncapsulate,
    KemDecapsulate,
    SignKeygen,
    SignMessage,
    VerifySignature,
    ThreatScan,
    PolicyEnforce,
    SecretStore,
    AuditWrite,
}

/// Task definition with safety metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: Uuid,
    pub task_type: TaskType,
    pub priority: TaskPriority,
    pub payload: serde_json::Value,
    pub assigned_agent: Option<Uuid>,
    pub status: TaskStatus,
    pub created_at: DateTime<Utc>,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub retry_count: u32,
    pub max_retries: u32,
    pub requires_human_approval: bool,
    pub human_approval_status: HumanApprovalStatus,
    pub safety_classification: SafetyClassification,
    pub affected_assets: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum TaskType {
    // Crypto operations
    RotateMasterKey,
    RotateDataKey,
    DestroyKey,
    SealVault,
    UnsealVault,
    
    // Policy operations
    UpdatePolicy,
    RevokeCertificate,
    QuarantineDevice,
    BlockTraffic,
    
    // System operations
    DeployAgent,
    UpdateAgent,
    RollbackDeployment,
    BackupAuditLog,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TaskPriority {
    Critical = 0,
    High = 1,
    Normal = 2,
    Low = 3,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum TaskStatus {
    Pending,
    AwaitingHumanApproval,
    Approved,
    Rejected,
    Assigned,
    Running,
    Completed,
    Failed,
    RollingBack,
    RolledBack,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum HumanApprovalStatus {
    NotRequired,
    Pending,
    Approved { approver: String, signature: String },
    Rejected { approver: String, reason: String },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum SafetyClassification {
    Safe,           // No risk, auto-execute
    Normal,         // Standard checks
    Sensitive,      // Extra logging
    Destructive,    // Requires human approval
    Critical,       // Requires 2-person approval
}

/// Human decision package for gatekeeper review
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionPackage {
    pub package_id: Uuid,
    pub task_id: Uuid,
    pub decision_type: DecisionType,
    pub summary: String,
    pub rationale: ThreeLineRationale,
    pub affected_assets: Vec<String>,
    pub risk_score: f64,
    pub proposed_action: String,
    pub rollback_plan: String,
    pub created_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DecisionType {
    ApproveKeyRotation,
    ApproveKeyDestruction,
    ApprovePolicyChange,
    ApproveQuarantine,
    ForceRollback,
}

/// Required explainability format
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreeLineRationale {
    pub line1_why: String,      // Why this decision was made
    pub line2_what: String,     // What will happen
    pub line3_risk: String,     // Risk assessment
}

/// Policy delta for real-time updates
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyDelta {
    pub delta_id: Uuid,
    pub policy_id: String,
    pub change_type: ChangeType,
    pub old_value: Option<serde_json::Value>,
    pub new_value: Option<serde_json::Value>,
    pub effective_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ChangeType {
    Create,
    Update,
    Delete,
    Enable,
    Disable,
}

/// Telemetry from agents
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Telemetry {
    pub agent_id: Uuid,
    pub timestamp: DateTime<Utc>,
    pub metrics: Vec<Metric>,
    pub alerts: Vec<Alert>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Metric {
    pub name: String,
    pub value: f64,
    pub unit: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alert {
    pub severity: AlertSeverity,
    pub message: String,
    pub source: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AlertSeverity {
    Info,
    Warning,
    Error,
    Critical,
}

/// Escalation event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EscalationEvent {
    pub event_id: Uuid,
    pub event_type: EscalationType,
    pub description: String,
    pub related_task_id: Option<Uuid>,
    pub severity: AlertSeverity,
    pub created_at: DateTime<Utc>,
    pub acknowledged: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EscalationType {
    AgentStarvation,
    SafetyViolation,
    HumanApprovalTimeout,
    MaxRetriesExceeded,
    ConcurrentOperationLimit,
    RollbackTriggered,
}

impl Task {
    pub fn new(task_type: TaskType, payload: serde_json::Value) -> Self {
        Self {
            id: Uuid::new_v4(),
            task_type,
            priority: TaskPriority::Normal,
            payload,
            assigned_agent: None,
            status: TaskStatus::Pending,
            created_at: Utc::now(),
            started_at: None,
            completed_at: None,
            retry_count: 0,
            max_retries: 3,
            requires_human_approval: false,
            human_approval_status: HumanApprovalStatus::NotRequired,
            safety_classification: SafetyClassification::Normal,
            affected_assets: Vec::new(),
        }
    }
    
    pub fn with_safety(mut self, classification: SafetyClassification) -> Self {
        self.safety_classification = classification;
        self.requires_human_approval = matches!(
            classification, 
            SafetyClassification::Destructive | SafetyClassification::Critical
        );
        self
    }
    
    pub fn with_assets(mut self, assets: Vec<String>) -> Self {
        self.affected_assets = assets;
        self
    }
}

impl DecisionPackage {
    pub fn new(task: &Task, decision_type: DecisionType, rationale: ThreeLineRationale) -> Self {
        Self {
            package_id: Uuid::new_v4(),
            task_id: task.id,
            decision_type,
            summary: format!("{:?} for task {:?}", decision_type, task.task_type),
            rationale,
            affected_assets: task.affected_assets.clone(),
            risk_score: 0.0,
            proposed_action: String::new(),
            rollback_plan: String::new(),
            created_at: Utc::now(),
            expires_at: Utc::now() + chrono::Duration::hours(24),
        }
    }
}
