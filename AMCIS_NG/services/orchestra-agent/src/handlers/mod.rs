//! HTTP Handlers for Orchestra Agent API

use axum::{
    routing::{get, post},
    Router, Json, extract::{State, Path},
    http::StatusCode,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::info;

use crate::models::*;
use crate::safety::SafetyGuard;
use crate::audit::AuditLedger;
use crate::scheduler::TaskScheduler;

type SharedSafety = Arc<RwLock<SafetyGuard>>;
type SharedAudit = Arc<RwLock<AuditLedger>>;
type SharedScheduler = Arc<RwLock<TaskScheduler>>;

#[derive(Clone)]
struct AppState {
    safety: SharedSafety,
    audit: SharedAudit,
    scheduler: SharedScheduler,
}

/// Create API router
pub fn create_router(
    safety: SharedSafety,
    audit: SharedAudit,
    scheduler: SharedScheduler,
) -> Router {
    let state = AppState { safety, audit, scheduler };
    
    Router::new()
        // Health
        .route("/health", get(health))
        
        // Task management
        .route("/tasks", post(submit_task))
        .route("/tasks/:id/approve", post(approve_task))
        .route("/tasks/:id/reject", post(reject_task))
        .route("/tasks/status", get(get_scheduler_status))
        
        // Agent management
        .route("/agents/register", post(register_agent))
        .route("/agents/:id/heartbeat", post(agent_heartbeat))
        
        // Audit
        .route("/audit/verify", get(verify_audit_chain))
        
        // Escalations
        .route("/escalations", get(get_escalations))
        
        .with_state(state)
}

// Health check
async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "service": "amcis-orchestra-agent",
        "version": "1.0.0-alpha",
        "status": "healthy",
        "features": [
            "human_in_the_loop",
            "immutable_audit",
            "safety_guard",
            "explainability"
        ]
    }))
}

// Task submission
#[derive(Deserialize)]
struct SubmitTaskRequest {
    task_type: TaskType,
    payload: serde_json::Value,
    priority: Option<TaskPriority>,
    affected_assets: Vec<String>,
}

#[derive(Serialize)]
struct SubmitTaskResponse {
    task_id: Uuid,
    status: String,
    requires_approval: bool,
}

async fn submit_task(
    State(state): State<AppState>,
    Json(req): Json<SubmitTaskRequest>,
) -> Result<Json<SubmitTaskResponse>, StatusCode> {
    let mut task = Task::new(req.task_type, req.payload)
        .with_assets(req.affected_assets);
    
    if let Some(priority) = req.priority {
        task.priority = priority;
    }
    
    let requires_approval = task.requires_human_approval;
    
    let mut scheduler = state.scheduler.write().await;
    match scheduler.submit_task(task).await {
        Ok(task_id) => Ok(Json(SubmitTaskResponse {
            task_id,
            status: if requires_approval { "awaiting_human_approval".to_string() } else { "queued".to_string() },
            requires_approval,
        })),
        Err(e) => {
            tracing::error!("Failed to submit task: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// Human approval
#[derive(Deserialize)]
struct ApprovalRequest {
    approver: String,
    signature: String,
}

async fn approve_task(
    State(state): State<AppState>,
    Path(task_id): Path<Uuid>,
    Json(req): Json<ApprovalRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let mut scheduler = state.scheduler.write().await;
    
    match scheduler.handle_approval(task_id, true, req.approver, req.signature).await {
        Ok(_) => Ok(Json(serde_json::json!({
            "task_id": task_id,
            "status": "approved",
            "message": "Task approved and queued for execution"
        }))),
        Err(e) => {
            tracing::error!("Approval failed: {}", e);
            Err(StatusCode::NOT_FOUND)
        }
    }
}

#[derive(Deserialize)]
struct RejectionRequest {
    approver: String,
    reason: String,
}

async fn reject_task(
    State(state): State<AppState>,
    Path(task_id): Path<Uuid>,
    Json(req): Json<RejectionRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let mut scheduler = state.scheduler.write().await;
    
    match scheduler.handle_approval(task_id, false, req.approver, req.reason).await {
        Ok(_) => Ok(Json(serde_json::json!({
            "task_id": task_id,
            "status": "rejected",
            "message": "Task rejected by human gatekeeper"
        }))),
        Err(e) => {
            tracing::error!("Rejection failed: {}", e);
            Err(StatusCode::NOT_FOUND)
        }
    }
}

// Scheduler status
#[derive(Serialize)]
struct SchedulerStatusResponse {
    queued: usize,
    assigned: usize,
    completed: usize,
    failed: usize,
    pending_human_approvals: usize,
}

async fn get_scheduler_status(
    State(state): State<AppState>,
) -> Json<SchedulerStatusResponse> {
    let scheduler = state.scheduler.read().await;
    let status = scheduler.get_status();
    
    Json(SchedulerStatusResponse {
        queued: status.queued,
        assigned: status.assigned,
        completed: status.completed,
        failed: status.failed,
        pending_human_approvals: status.pending_approvals,
    })
}

// Agent registration
#[derive(Deserialize)]
struct RegisterAgentRequest {
    name: String,
    agent_type: AgentType,
    capabilities: Vec<Capability>,
    max_concurrent_tasks: u32,
}

async fn register_agent(
    State(state): State<AppState>,
    Json(req): Json<RegisterAgentRequest>,
) -> Json<serde_json::Value> {
    let agent = Agent {
        id: Uuid::new_v4(),
        name: req.name,
        agent_type: req.agent_type,
        status: AgentStatus::Online,
        capabilities: req.capabilities,
        last_heartbeat: Utc::now(),
        current_load: 0,
        max_concurrent_tasks: req.max_concurrent_tasks,
        metadata: serde_json::json!({}),
    };
    
    let agent_id = agent.id;
    
    let mut scheduler = state.scheduler.write().await;
    scheduler.register_agent(agent);
    
    info!("Agent {} registered", agent_id);
    
    Json(serde_json::json!({
        "agent_id": agent_id,
        "status": "registered",
        "message": "Agent successfully registered with orchestra"
    }))
}

// Agent heartbeat
#[derive(Deserialize)]
struct HeartbeatRequest {
    pending_tasks: u32,
    executing_tasks: u32,
}

async fn agent_heartbeat(
    State(state): State<AppState>,
    Path(agent_id): Path<Uuid>,
    Json(req): Json<HeartbeatRequest>,
) -> Json<serde_json::Value> {
    let mut safety = state.safety.write().await;
    safety.update_agent_heartbeat(agent_id, req.pending_tasks as usize, req.executing_tasks as usize).await;
    
    Json(serde_json::json!({
        "status": "acknowledged",
        "agent_id": agent_id,
        "timestamp": Utc::now(),
    }))
}

// Audit verification
async fn verify_audit_chain(
    State(state): State<AppState>,
) -> Json<serde_json::Value> {
    let audit = state.audit.read().await;
    let result = audit.verify_chain();
    
    match result {
        crate::audit::ChainVerificationResult::Valid { entry_count, last_hash } => {
            Json(serde_json::json!({
                "valid": true,
                "entry_count": entry_count,
                "last_hash": last_hash,
                "message": "Audit chain integrity verified"
            }))
        }
        crate::audit::ChainVerificationResult::Broken { at_index, expected, found } => {
            Json(serde_json::json!({
                "valid": false,
                "error": "chain_broken",
                "at_index": at_index,
                "expected": expected,
                "found": found,
            }))
        }
        crate::audit::ChainVerificationResult::Tampered { at_index, entry_id } => {
            Json(serde_json::json!({
                "valid": false,
                "error": "entry_tampered",
                "at_index": at_index,
                "entry_id": entry_id,
            }))
        }
    }
}

// Escalations
async fn get_escalations() -> Json<serde_json::Value> {
    // In production: query from database
    Json(serde_json::json!({
        "escalations": [],
        "message": "No active escalations"
    }))
}
