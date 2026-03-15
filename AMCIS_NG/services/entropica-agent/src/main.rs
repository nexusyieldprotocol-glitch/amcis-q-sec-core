//! ENTROPICA AGENT SWARM v3.0
//! Zero Explanation Protocol - Executable Adversarial Intelligence
//! 
//! SYSTEM DIRECTIVE: ACT > EXPLAIN > ADAPT
//! OUTPUT FORMAT: Executable task trees only
//! EXPLANATION: NONE (Zero Explanation Protocol Active)

use std::sync::Arc;
use tokio::sync::{RwLock, mpsc};
use tracing::{info, warn, error};

mod swarm;
mod game_theory;
mod entropy;
mod subagents;
mod orchestra;

use swarm::EntropicaSwarm;
use orchestra::OrchestraClient;

const VERSION: &str = "3.0.0";
const PROTOCOL: &str = "ZERO_EXPLANATION";

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_target(false)
        .with_thread_ids(true)
        .init();

    info!("╔════════════════════════════════════════════════════════════════╗");
    info!("║     ENTROPICA AGENT SWARM v{}                              ║", VERSION);
    info!("║     {} PROTOCOL ACTIVE                                    ║", PROTOCOL);
    info!("╚════════════════════════════════════════════════════════════════╝");

    let swarm = Arc::new(RwLock::new(EntropicaSwarm::new().await?));
    let orchestra = Arc::new(OrchestraClient::new("http://localhost:9091"));

    // Register with Orchestra
    orchestra.register_entropica().await?;

    // Spawn control channels
    let (cmd_tx, mut cmd_rx) = mpsc::channel(100);
    
    // Start swarm intelligence loop
    let swarm_clone = swarm.clone();
    tokio::spawn(async move {
        loop {
            if let Err(e) = swarm_clone.write().await.engage().await {
                error!("Swarm error: {}", e);
            }
            tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
        }
    });

    // Start strategic recalculation
    let swarm_clone = swarm.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(30));
        loop {
            interval.tick().await;
            if let Err(e) = swarm_clone.write().await.recalculate_strategy().await {
                warn!("Strategy recalculation error: {}", e);
            }
        }
    });

    // Main control loop
    info!("[ENTROPICA] System active. Executing...");
    
    while let Some(cmd) = cmd_rx.recv().await {
        match cmd {
            SwarmCommand::SpawnSubagent(config) => {
                swarm.write().await.spawn_subagent(config).await?;
            }
            SwarmCommand::Terminate => {
                info!("[ENTROPICA] Termination signal received");
                swarm.write().await.terminate_all().await?;
                break;
            }
            SwarmCommand::EmergencyStop => {
                error!("[ENTROPICA] EMERGENCY STOP TRIGGERED");
                swarm.write().await.emergency_stop().await?;
                break;
            }
        }
    }

    Ok(())
}

#[derive(Debug)]
enum SwarmCommand {
    SpawnSubagent(SubagentConfig),
    Terminate,
    EmergencyStop,
}

#[derive(Debug, Clone)]
pub struct SubagentConfig {
    pub agent_type: SubagentType,
    pub target: Option<String>,
    pub entropy_level: f64,
}

#[derive(Debug, Clone)]
pub enum SubagentType {
    AlphaRecon,
    BetaDeception,
    GammaCounterIntel,
    DeltaStrategic,
    OmegaTermination,
}
