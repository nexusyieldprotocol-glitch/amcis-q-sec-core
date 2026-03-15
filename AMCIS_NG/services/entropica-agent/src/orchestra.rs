//! Orchestra Client - Integration with AMCIS Orchestra Agent

use reqwest::Client;
use serde_json::json;
use tracing::{info, debug};

pub struct OrchestraClient {
    base_url: String,
    client: Client,
}

impl OrchestraClient {
    pub fn new(base_url: &str) -> Self {
        Self {
            base_url: base_url.to_string(),
            client: Client::new(),
        }
    }

    /// Register Entropica with Orchestra
    pub async fn register_entropica(&self) -> anyhow::Result<()> {
        let payload = json!({
            "name": "ENTROPICA_MASTER",
            "agent_type": "autonomous_swarm",
            "capabilities": [
                "entropy_warfare",
                "game_theory_optimization",
                "subagent_spawning",
                "strategic_recalculation"
            ],
            "max_concurrent_tasks": 10,
        });

        let url = format!("{}/agents/register", self.base_url);
        
        match self.client.post(&url).json(&payload).send().await {
            Ok(resp) if resp.status().is_success() => {
                info!("[ORCHESTRA] Entropica registered successfully");
                Ok(())
            }
            Ok(resp) => {
                anyhow::bail!("Orchestra registration failed: {}", resp.status())
            }
            Err(e) => {
                anyhow::bail!("Orchestra connection error: {}", e)
            }
        }
    }

    /// Submit task to Orchestra
    pub async fn submit_task(&self, task_type: &str, payload: serde_json::Value) -> anyhow::Result<uuid::Uuid> {
        let body = json!({
            "task_type": task_type,
            "payload": payload,
            "priority": "High",
        });

        let url = format!("{}/tasks", self.base_url);
        
        let resp = self.client
            .post(&url)
            .json(&body)
            .send()
            .await?;
        
        if resp.status().is_success() {
            let result: serde_json::Value = resp.json().await?;
            let task_id = result["task_id"].as_str()
                .ok_or_else(|| anyhow::anyhow!("Missing task_id"))?;
            Ok(uuid::Uuid::parse_str(task_id)?)
        } else {
            anyhow::bail!("Task submission failed: {}", resp.status())
        }
    }

    /// Send heartbeat
    pub async fn heartbeat(&self, metrics: EntropicaMetrics) -> anyhow::Result<()> {
        let url = format!("{}/agents/entropica/heartbeat", self.base_url);
        
        let payload = json!({
            "active_subagents": metrics.active_subagents,
            "entropy_pool_status": metrics.entropy_pool_status,
            "strategy_convergence": metrics.strategy_convergence,
            "threat_engagement_count": metrics.threat_engagement_count,
        });

        debug!("[HEARTBEAT] Sending metrics to Orchestra");
        
        self.client
            .post(&url)
            .json(&payload)
            .send()
            .await?;
        
        Ok(())
    }

    /// Request human approval for destructive operation
    pub async fn request_human_approval(&self, task_id: uuid::Uuid, rationale: &str) -> anyhow::Result<bool> {
        let url = format!("{}/tasks/{}/request_approval", self.base_url, task_id);
        
        let payload = json!({
            "rationale": rationale,
            "requesting_agent": "ENTROPICA_MASTER",
        });

        let resp = self.client
            .post(&url)
            .json(&payload)
            .send()
            .await?;

        Ok(resp.status().is_success())
    }

    /// Emergency stop
    pub async fn emergency_stop(&self, reason: &str) -> anyhow::Result<()> {
        let url = format!("{}/simulation/emergency-stop", self.base_url);
        
        let payload = json!({
            "reason": reason,
            "initiated_by": "ENTROPICA_MASTER",
        });

        info!("[EMERGENCY] Signaling Orchestra: {}", reason);
        
        self.client
            .post(&url)
            .json(&payload)
            .send()
            .await?;
        
        Ok(())
    }
}

pub struct EntropicaMetrics {
    pub active_subagents: usize,
    pub entropy_pool_status: f64,
    pub strategy_convergence: f64,
    pub threat_engagement_count: usize,
}
