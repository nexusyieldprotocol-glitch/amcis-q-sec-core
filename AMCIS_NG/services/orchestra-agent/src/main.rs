//! AMCIS Orchestra Agent
//! 
//! Central coordination hub with:
//! - Human-in-the-loop for destructive crypto operations
//! - Immutable audit trail via blockchain-backed ledger
//! - Safety-first task scheduling with agent starvation detection
//! - Explainable AI: 3-line rationale + affected assets for every decision

use tracing::{info, warn, error};
use std::sync::Arc;
use tokio::sync::RwLock;

mod models;
mod safety;
mod audit;
mod explainability;
mod handlers;
mod scheduler;

use safety::SafetyGuard;
use audit::AuditLedger;
use scheduler::TaskScheduler;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_target(true)
        .with_thread_ids(true)
        .with_env_filter("info,amcis_orchestra_agent=debug")
        .init();

    info!("╔══════════════════════════════════════════════════════════════╗");
    info!("║     AMCIS ORCHESTRA AGENT v1.0.0-alpha                      ║");
    info!("║     Safety-First Orchestration with Human Oversight         ║");
    info!("╚══════════════════════════════════════════════════════════════╝");

    let safety_guard = Arc::new(RwLock::new(SafetyGuard::new()));
    let audit_ledger = Arc::new(AuditLedger::new().await?);
    let task_scheduler = Arc::new(RwLock::new(TaskScheduler::new(
        safety_guard.clone(),
        audit_ledger.clone(),
    )));

    let app = handlers::create_router(
        safety_guard.clone(),
        audit_ledger.clone(),
        task_scheduler.clone(),
    );

    let listener = tokio::net::TcpListener::bind("0.0.0.0:9091").await?;
    info!("Orchestra Agent API listening on {}", listener.local_addr()?);

    let scheduler_handle = tokio::spawn(run_scheduler(task_scheduler));
    let monitor_handle = tokio::spawn(run_agent_monitor(safety_guard));

    axum::serve(listener, app).await?;

    scheduler_handle.abort();
    monitor_handle.abort();

    Ok(())
}

async fn run_scheduler(scheduler: Arc<RwLock<TaskScheduler>>) {
    let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(5));
    
    loop {
        interval.tick().await;
        
        if let Ok(mut sched) = scheduler.write().await {
            if let Err(e) = sched.process_task_queue().await {
                error!("Scheduler error: {}", e);
            }
        }
    }
}

async fn run_agent_monitor(safety_guard: Arc<RwLock<SafetyGuard>>) {
    let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(10));
    
    loop {
        interval.tick().await;
        
        if let Ok(mut guard) = safety_guard.write().await {
            if let Err(e) = guard.check_agent_health().await {
                warn!("Agent health check failed: {}", e);
            }
        }
    }
}
