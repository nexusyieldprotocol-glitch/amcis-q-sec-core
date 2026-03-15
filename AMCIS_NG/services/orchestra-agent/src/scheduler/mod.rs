//! Task Scheduler - Coordinates agent assignments with safety checks

use crate::models::*;
use crate::safety::{SafetyGuard, SafetyResult};
use crate::audit::AuditLedger;
use crate::explainability::{ExplainabilityEngine, DecisionPackageFormatter};
use std::collections::VecDeque;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn, error};
use chrono::Utc;
use uuid::Uuid;

/// Task scheduler with safety-first execution
pub struct TaskScheduler {
    task_queue: VecDeque<Task>,
    assigned_tasks: Vec<Task>,
    completed_tasks: Vec<Task>,
    failed_tasks: Vec<Task>,
    
    safety_guard: Arc<RwLock<SafetyGuard>>,
    audit_ledger: Arc<RwLock<AuditLedger>>,
    
    /// Registered agents
    agents: Vec<Agent>,
    
    /// Pending human approvals
    pending_approvals: Vec<DecisionPackage>,
}

impl TaskScheduler {
    pub fn new(
        safety_guard: Arc<RwLock<SafetyGuard>>,
        audit_ledger: Arc<RwLock<AuditLedger>>,
    ) -> Self {
        Self {
            task_queue: VecDeque::new(),
            assigned_tasks: Vec::new(),
            completed_tasks: Vec::new(),
            failed_tasks: Vec::new(),
            safety_guard,
            audit_ledger,
            agents: Vec::new(),
            pending_approvals: Vec::new(),
        }
    }
    
    /// Submit new task to queue
    pub async fn submit_task(&mut self, mut task: Task) -> Result<Uuid, SchedulerError> {
        // Enrich task with safety classification if not set
        if task.safety_classification == SafetyClassification::Normal {
            task.safety_classification = self.classify_task_safety(&task);
        }
        
        let task_id = task.id;
        
        // Log task creation
        {
            let mut ledger = self.audit_ledger.write().await;
            ledger.record_task_event(&task, AuditEntryType::TaskCreated).await;
        }
        
        self.task_queue.push_back(task);
        info!("Task {} submitted to queue (queue depth: {})", task_id, self.task_queue.len());
        
        Ok(task_id)
    }
    
    /// Process task queue
    pub async fn process_task_queue(&mut self) -> Result<(), SchedulerError> {
        let mut to_process = Vec::new();
        
        // Collect tasks that are ready (respecting priority)
        while let Some(task) = self.task_queue.pop_front() {
            to_process.push(task);
        }
        
        // Sort by priority
        to_process.sort_by_key(|t| t.priority.clone() as i32);
        
        for mut task in to_process {
            match self.process_single_task(&mut task).await {
                Ok(_) => {}
                Err(e) => {
                    warn!("Task {} processing failed: {:?}", task.id, e);
                    self.handle_task_failure(task, &e.to_string()).await;
                }
            }
        }
        
        Ok(())
    }
    
    async fn process_single_task(&mut self, task: &mut Task) -> Result<(), SchedulerError> {
        let guard = self.safety_guard.read().await;
        
        // Safety check
        match guard.check_safety(task).await {
            SafetyResult::Safe => {
                drop(guard);
                self.execute_task(task).await
            }
            SafetyResult::RequiresHumanApproval { reason, affected_assets } => {
                drop(guard);
                self.request_human_approval(task, reason, affected_assets).await
            }
            SafetyResult::Throttle { reason, retry_after_secs } => {
                warn!("Task {} throttled: {} (retry after {}s)", task.id, reason, retry_after_secs);
                task.status = TaskStatus::Pending;
                self.task_queue.push_back(task.clone());
                Ok(())
            }
            SafetyResult::MaxRetriesExceeded { task_id, attempts } => {
                error!("Task {} max retries exceeded after {} attempts", task_id, attempts);
                Err(SchedulerError::MaxRetriesExceeded(task_id))
            }
            SafetyResult::MissingInformation { field, reason } => {
                warn!("Task {} missing {}: {}", task.id, field, reason);
                Err(SchedulerError::InvalidTask(format!("Missing {}: {}", field, reason)))
            }
        }
    }
    
    async fn execute_task(&mut self, task: &mut Task) -> Result<(), SchedulerError> {
        // Find capable agent
        let agent = self.find_capable_agent(task)
            .ok_or_else(|| SchedulerError::NoCapableAgent(task.task_type.clone()))?;
        
        task.assigned_agent = Some(agent.id);
        task.status = TaskStatus::Assigned;
        task.started_at = Some(Utc::now());
        
        // Generate explainability
        let rationale = ExplainabilityEngine::explain_task_assignment(task, &agent);
        ExplainabilityEngine::log_decision("TASK ASSIGNMENT", &rationale, &task.affected_assets);
        
        // Log assignment
        {
            let mut ledger = self.audit_ledger.write().await;
            ledger.record_task_event(task, AuditEntryType::TaskAssigned).await;
        }
        
        // Track key rotation if applicable
        if matches!(task.task_type, TaskType::RotateMasterKey | TaskType::RotateDataKey) {
            let mut guard = self.safety_guard.write().await;
            guard.track_key_rotation(true).await;
        }
        
        // Simulate execution (in production: call agent RPC)
        info!("Executing task {} on agent {}", task.id, agent.id);
        
        // Move to assigned list
        self.assigned_tasks.push(task.clone());
        
        Ok(())
    }
    
    async fn request_human_approval(&mut self, task: &mut Task, 
                                    reason: String, assets: Vec<String>) -> Result<(), SchedulerError> {
        task.status = TaskStatus::AwaitingHumanApproval;
        task.requires_human_approval = true;
        task.human_approval_status = HumanApprovalStatus::Pending;
        
        let rationale = ExplainabilityEngine::explain_approval_request(task);
        
        let package = DecisionPackage::new(task, DecisionType::ApproveKeyRotation, rationale.clone());
        
        // Log approval request
        {
            let mut ledger = self.audit_ledger.write().await;
            ledger.record_task_event(task, AuditEntryType::HumanApprovalRequested).await;
        }
        
        // Format for human display
        let formatted = DecisionPackageFormatter::format_for_human(task, &rationale);
        warn!("{}", formatted);
        
        self.pending_approvals.push(package);
        
        // Return task to queue waiting for approval
        self.task_queue.push_back(task.clone());
        
        Ok(())
    }
    
    /// Handle human approval response
    pub async fn handle_approval(&mut self, task_id: Uuid, approved: bool, 
                                  approver: String, signature: String) -> Result<(), SchedulerError> {
        // Find task
        if let Some(task) = self.task_queue.iter_mut().find(|t| t.id == task_id) {
            if approved {
                task.human_approval_status = HumanApprovalStatus::Approved { 
                    approver: approver.clone(), 
                    signature 
                };
                task.status = TaskStatus::Approved;
                
                // Record in safety guard
                let mut guard = self.safety_guard.write().await;
                guard.record_approval(task_id, approver.clone(), signature).await?;
                
                // Log approval
                {
                    let mut ledger = self.audit_ledger.write().await;
                    ledger.record_human_approval(task_id, &approver, true, None).await;
                }
                
                info!("Task {} approved by {}", task_id, approver);
            } else {
                task.human_approval_status = HumanApprovalStatus::Rejected { 
                    approver: approver.clone(), 
                    reason: "Human rejected".to_string() 
                };
                task.status = TaskStatus::Rejected;
                
                // Log rejection
                {
                    let mut ledger = self.audit_ledger.write().await;
                    ledger.record_human_approval(task_id, &approver, false, Some("Human rejected")).await;
                }
                
                warn!("Task {} rejected by {}", task_id, approver);
            }
            
            Ok(())
        } else {
            Err(SchedulerError::TaskNotFound(task_id))
        }
    }
    
    async fn handle_task_failure(&mut self, mut task: Task, error: &str) {
        task.retry_count += 1;
        
        if task.retry_count < task.max_retries {
            // Generate retry rationale
            let rationale = ExplainabilityEngine::explain_retry(&task, task.retry_count, error);
            ExplainabilityEngine::log_decision("TASK RETRY", &rationale, &task.affected_assets);
            
            // Re-queue with delay
            task.status = TaskStatus::Pending;
            self.task_queue.push_back(task);
        } else {
            // Trigger rollback
            let rationale = ExplainabilityEngine::explain_rollback(&task, error);
            ExplainabilityEngine::log_decision("ROLLBACK TRIGGERED", &rationale, &task.affected_assets);
            
            task.status = TaskStatus::RollingBack;
            
            let mut guard = self.safety_guard.write().await;
            let _rollback_plan = guard.trigger_rollback(task.id).await;
            
            task.status = TaskStatus::RolledBack;
            self.failed_tasks.push(task);
        }
    }
    
    fn find_capable_agent(&self, task: &Task) -> Option<Agent> {
        self.agents.iter()
            .filter(|a| a.status == AgentStatus::Online)
            .filter(|a| a.current_load < a.max_concurrent_tasks)
            .min_by_key(|a| a.current_load)
            .cloned()
    }
    
    fn classify_task_safety(&self, task: &Task) -> SafetyClassification {
        match task.task_type {
            TaskType::DestroyKey | TaskType::SealVault => SafetyClassification::Destructive,
            TaskType::RotateMasterKey => SafetyClassification::Critical,
            TaskType::RotateDataKey => SafetyClassification::Sensitive,
            TaskType::QuarantineDevice | TaskType::BlockTraffic => SafetyClassification::Sensitive,
            _ => SafetyClassification::Normal,
        }
    }
    
    /// Register a new agent
    pub fn register_agent(&mut self, agent: Agent) {
        info!("Registering agent {} ({:?})", agent.name, agent.agent_type);
        self.agents.push(agent);
    }
    
    /// Get queue status
    pub fn get_status(&self) -> SchedulerStatus {
        SchedulerStatus {
            queued: self.task_queue.len(),
            assigned: self.assigned_tasks.len(),
            completed: self.completed_tasks.len(),
            failed: self.failed_tasks.len(),
            pending_approvals: self.pending_approvals.len(),
        }
    }
}

#[derive(Debug)]
pub enum SchedulerError {
    NoCapableAgent(TaskType),
    TaskNotFound(Uuid),
    MaxRetriesExceeded(Uuid),
    InvalidTask(String),
    SafetyViolation(String),
}

impl std::fmt::Display for SchedulerError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NoCapableAgent(tt) => write!(f, "No capable agent for task type {:?}", tt),
            Self::TaskNotFound(id) => write!(f, "Task {} not found", id),
            Self::MaxRetriesExceeded(id) => write!(f, "Task {} max retries exceeded", id),
            Self::InvalidTask(msg) => write!(f, "Invalid task: {}", msg),
            Self::SafetyViolation(msg) => write!(f, "Safety violation: {}", msg),
        }
    }
}

impl std::error::Error for SchedulerError {}

pub struct SchedulerStatus {
    pub queued: usize,
    pub assigned: usize,
    pub completed: usize,
    pub failed: usize,
    pub pending_approvals: usize,
}
