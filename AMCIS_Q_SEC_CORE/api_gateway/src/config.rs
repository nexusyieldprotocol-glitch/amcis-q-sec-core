// Gateway configuration

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GatewayConfig {
    /// Address to bind the server
    pub bind_address: String,
    
    /// Path to TLS certificate
    pub tls_cert_path: Option<String>,
    
    /// Path to TLS private key
    pub tls_key_path: Option<String>,
    
    /// Enable post-quantum hybrid TLS
    pub enable_pq_tls: bool,
    
    /// Backend service URLs
    pub backends: Vec<BackendConfig>,
    
    /// Rate limiting configuration
    pub rate_limit: RateLimitConfig,
    
    /// JWT validation configuration
    pub jwt: JwtConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendConfig {
    pub name: String,
    pub url: String,
    pub path_prefix: String,
    pub health_check: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimitConfig {
    pub requests_per_second: u32,
    pub burst_size: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JwtConfig {
    pub enabled: bool,
    pub public_key_path: Option<String>,
    pub issuer: String,
    pub audience: String,
}

impl Default for GatewayConfig {
    fn default() -> Self {
        Self {
            bind_address: "0.0.0.0:8443".to_string(),
            tls_cert_path: None,
            tls_key_path: None,
            enable_pq_tls: true,
            backends: vec![
                BackendConfig {
                    name: "api".to_string(),
                    url: "http://localhost:8080".to_string(),
                    path_prefix: "/api/v1".to_string(),
                    health_check: Some("/health".to_string()),
                },
            ],
            rate_limit: RateLimitConfig {
                requests_per_second: 1000,
                burst_size: 2000,
            },
            jwt: JwtConfig {
                enabled: true,
                public_key_path: None,
                issuer: "amcis-auth".to_string(),
                audience: "amcis-api".to_string(),
            },
        }
    }
}

/// Load configuration from file or environment
pub fn load_config() -> Result<GatewayConfig, Box<dyn std::error::Error>> {
    // First, try to load from file
    if let Ok(content) = std::fs::read_to_string("config.toml") {
        let config: GatewayConfig = toml::from_str(&content)?;
        return Ok(config);
    }
    
    // Otherwise, build from environment variables
    let mut config = GatewayConfig::default();
    
    if let Ok(addr) = std::env::var("AMCIS_BIND_ADDRESS") {
        config.bind_address = addr;
    }
    
    if let Ok(cert) = std::env::var("AMCIS_TLS_CERT") {
        config.tls_cert_path = Some(cert);
    }
    
    if let Ok(key) = std::env::var("AMCIS_TLS_KEY") {
        config.tls_key_path = Some(key);
    }
    
    if let Ok(pq) = std::env::var("AMCIS_ENABLE_PQ") {
        config.enable_pq_tls = pq.parse().unwrap_or(true);
    }
    
    Ok(config)
}
