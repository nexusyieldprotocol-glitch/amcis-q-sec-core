//! Explainability Module - 3-line rationale for every automated decision

use crate::models::*;
use tracing::info;

/// Generates human-readable explanations for all automated decisions
pub struct ExplainabilityEngine;

impl ExplainabilityEngine {
    /// Generate 3-line rationale for a task assignment decision
    pub fn explain_task_assignment(task: &Task, assigned_agent: &Agent) -> ThreeLineRationale {
        let why = format!(
            "Agent {} selected based on capability match {:?} and current load {}/{} concurrent tasks",
            assigned_agent.name,
            task.task_type,
            assigned_agent.current_load,
            assigned_agent.max_concurrent_tasks
        );
        
        let what = format!(
            "Task {:?} (priority: {:?}) will execute on agent {}, affecting {} assets",
            task.task_type,
            task.priority,
            assigned_agent.id,
            task.affected_assets.len()
        );
        
        let risk = format!(
            "Risk level: {:?}. Requires human approval: {}. Max retries: {}",
            task.safety_classification,
            task.requires_human_approval,
            task.max_retries
        );
        
        ThreeLineRationale {
            line1_why: why,
            line2_what: what,
            line3_risk: risk,
        }
    }
    
    /// Generate rationale for human approval request
    pub fn explain_approval_request(task: &Task) -> ThreeLineRationale {
        let why = format!(
            "Destructive crypto operation {:?} detected in safety classification {:?}",
            task.task_type,
            task.safety_classification
        );
        
        let what = format!(
            "Operation will impact assets: {}. Estimated blast radius: {} systems",
            task.affected_assets.join(", "),
            task.affected_assets.len()
        );
        
        let risk = format!(
            "IRREVERSIBLE ACTION: {}. Verify all backups current before approval.",
            match task.task_type {
                TaskType::DestroyKey => "Key destruction is permanent",
                TaskType::RotateMasterKey => "Master key rotation affects all encrypted data",
                TaskType::SealVault => "Vault seal will lock all secrets",
                _ => "High-impact operation requires oversight",
            }
        );
        
        ThreeLineRationale {
            line1_why: why,
            line2_what: what,
            line3_risk: risk,
        }
    }
    
    /// Generate rationale for retry decision
    pub fn explain_retry(task: &Task, attempt: u32, error: &str) -> ThreeLineRationale {
        let why = format!(
            "Task {} failed with error: {}. Attempt {}/{}.",
            task.id,
            error.chars().take(50).collect::<String>(),
            attempt,
            task.max_retries
        );
        
        let what = format!(
            "Automatic retry scheduled with exponential backoff. Next attempt in {} seconds.",
            2_u64.pow(attempt)
        );
        
        let risk = format!(
            "Retry risk: LOW (idempotent operation). Escalation if attempt {} fails.",
            task.max_retries
        );
        
        ThreeLineRationale {
            line1_why: why,
            line2_what: what,
            line3_risk: risk,
        }
    }
    
    /// Generate rationale for rollback trigger
    pub fn explain_rollback(task: &Task, failure_reason: &str) -> ThreeLineRationale {
        let why = format!(
            "Task {} reached max retries ({}) or critical failure: {}",
            task.id,
            task.max_retries,
            failure_reason
        );
        
        let what = format!(
            "Safe rollback playbook initiated. Steps: stop operation, restore state, verify integrity, notify operators."
        );
        
        let risk = format!(
            "Affected assets undergoing recovery: {}. Estimated recovery time: 30 seconds.",
            task.affected_assets.join(", ")
        );
        
        ThreeLineRationale {
            line1_why: why,
            line2_what: what,
            line3_risk: risk,
        }
    }
    
    /// Generate rationale for agent starvation detection
    pub fn explain_starvation(agent: &Agent, pending_secs: i64) -> ThreeLineRationale {
        let why = format!(
            "Agent {} has {} pending tasks but 0 executing for {} seconds (threshold: {}s)",
            agent.name,
            agent.current_load,
            pending_secs,
            300 // AGENT_STARVATION_THRESHOLD_SECS
        );
        
        let what = format!(
            "Tasks will be reassigned to healthy agents. Agent {} marked for health check.",
            agent.id
        );
        
        let risk = format!(
            "SLA impact: MEDIUM. Task queue depth may increase during reassignment window."
        );
        
        ThreeLineRationale {
            line1_why: why,
            line2_what: what,
            line3_risk: risk,
        }
    }
    
    /// Generate rationale for policy enforcement
    pub fn explain_policy_enforcement(policy_id: &str, decision: &str, reason: &str) -> ThreeLineRationale {
        let why = format!(
            "Policy {} triggered enforcement action based on rule evaluation",
            policy_id
        );
        
        let what = format!(
            "Decision: {}. Reason: {}",
            decision,
            reason
        );
        
        let risk = format!(
            "Policy enforcement is automated with audit trail. Human escalation available if contested."
        );
        
        ThreeLineRationale {
            line1_why: why,
            line2_what: what,
            line3_risk: risk,
        }
    }
    
    /// Log decision with full explainability
    pub fn log_decision(context: &str, rationale: &ThreeLineRationale, assets: &[String]) {
        info!("╔══════════════════════════════════════════════════════════════════╗");
        info!("║  ORCHESTRA DECISION: {}", context);
        info!("╠══════════════════════════════════════════════════════════════════╣");
        info!("║  WHY:  {}", rationale.line1_why);
        info!("║  WHAT: {}", rationale.line2_what);
        info!("║  RISK: {}", rationale.line3_risk);
        info!("║  ASSETS: {}", assets.join(", "));
        info!("╚══════════════════════════════════════════════════════════════════╝");
    }
}

/// Formatted decision package for human gatekeeper
pub struct DecisionPackageFormatter;

impl DecisionPackageFormatter {
    pub fn format_for_human(task: &Task, rationale: &ThreeLineRationale) -> String {
        format!(
            r#"
╔══════════════════════════════════════════════════════════════════════════╗
║           AMCIS ORCHESTRA - HUMAN APPROVAL REQUIRED                      ║
╠══════════════════════════════════════════════════════════════════════════╣
║  TASK ID:       {task_id}
║  TYPE:          {task_type:?}
║  CLASSIFICATION: {safety:?}
║  CREATED:       {created}
╠══════════════════════════════════════════════════════════════════════════╣
║  RATIONALE:
║  1. {why}
║  2. {what}
║  3. {risk}
╠══════════════════════════════════════════════════════════════════════════╣
║  AFFECTED ASSETS: {assets}
║  
║  ⚠️  THIS IS A DESTRUCTIVE OPERATION THAT CANNOT BE UNDONE
║  
║  TO APPROVE: Sign with your Ed25519 key and POST to /approve/{task_id}
║  TO REJECT:  POST to /reject/{task_id} with reason
╚══════════════════════════════════════════════════════════════════════════╝
"#,
            task_id = task.id,
            task_type = task.task_type,
            safety = task.safety_classification,
            created = task.created_at,
            why = rationale.line1_why,
            what = rationale.line2_what,
            risk = rationale.line3_risk,
            assets = if task.affected_assets.is_empty() { 
                "NONE SPECIFIED - REJECT RECOMMENDED".to_string() 
            } else { 
                task.affected_assets.join(", ") 
            },
        )
    }
}
