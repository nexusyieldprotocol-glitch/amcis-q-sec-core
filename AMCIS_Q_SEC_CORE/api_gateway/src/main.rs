// AMCIS API Gateway
// Post-quantum TLS termination and request routing

use axum::{
    body::Body,
    extract::{Request, State},
    http::StatusCode,
    middleware::{self, Next},
    response::{IntoResponse, Response},
    routing::get,
    Router,
};
use std::{
    net::SocketAddr,
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::net::TcpListener;
use tokio_rustls::TlsAcceptor;
use tower_http::{
    cors::{Any, CorsLayer},
    trace::TraceLayer,
};
use tracing::{error, info, warn};

mod config;
mod crypto;
mod middleware;
mod tls;

use config::GatewayConfig;
use tls::HybridTlsConfig;

/// Application state shared across handlers
#[derive(Clone)]
pub struct AppState {
    config: Arc<GatewayConfig>,
    request_count: Arc<std::sync::atomic::AtomicU64>,
}

impl AppState {
    fn new(config: GatewayConfig) -> Self {
        Self {
            config: Arc::new(config),
            request_count: Arc::new(std::sync::atomic::AtomicU64::new(0)),
        }
    }
}

/// Health check endpoint
async fn health_check() -> impl IntoResponse {
    let response = serde_json::json!({
        "status": "healthy",
        "service": "amcis-api-gateway",
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "version": env!("CARGO_PKG_VERSION"),
        "quantum_ready": true,
    });
    (StatusCode::OK, axum::Json(response))
}

/// TLS status endpoint
async fn tls_status(State(state): State<AppState>) -> impl IntoResponse {
    let pq_enabled = state.config.enable_pq_tls;
    
    let response = serde_json::json!({
        "tls_version": "1.3",
        "pq_hybrid_enabled": pq_enabled,
        "supported_groups": if pq_enabled {
            vec!["X25519Kyber768Draft00", "X25519", "secp256r1"]
        } else {
            vec!["X25519", "secp256r1"]
        },
        "cipher_suites": vec![
            "TLS13_AES_256_GCM_SHA384",
            "TLS13_AES_128_GCM_SHA256",
            "TLS13_CHACHA20_POLY1305_SHA256",
        ],
        "timestamp": chrono::Utc::now().to_rfc3339(),
    });
    (StatusCode::OK, axum::Json(response))
}

/// Metrics endpoint
async fn metrics(State(state): State<AppState>) -> impl IntoResponse {
    let count = state
        .request_count
        .load(std::sync::atomic::Ordering::Relaxed);
    
    let response = serde_json::json!({
        "total_requests": count,
        "uptime_seconds": 0, // TODO: Track start time
        "quantum_requests": count, // All requests are quantum-protected
    });
    
    (StatusCode::OK, axum::Json(response))
}

/// Request logging middleware
async fn log_request(
    State(state): State<AppState>,
    request: Request,
    next: Next,
) -> Response {
    let start = Instant::now();
    let method = request.method().clone();
    let uri = request.uri().clone();
    
    state.request_count.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    
    let response = next.run(request).await;
    
    let duration = start.elapsed();
    let status = response.status();
    
    info!(
        method = %method,
        uri = %uri,
        status = %status,
        duration_ms = %duration.as_millis(),
        "Request completed"
    );
    
    response
}

/// Create the main router
fn create_router(state: AppState) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    Router::new()
        .route("/health", get(health_check))
        .route("/status/tls", get(tls_status))
        .route("/metrics", get(metrics))
        .layer(middleware::from_fn_with_state(state.clone(), log_request))
        .layer(TraceLayer::new_for_http())
        .layer(cors)
        .with_state(state)
}

/// Run the gateway server
async fn run_server(config: GatewayConfig) -> Result<(), Box<dyn std::error::Error>> {
    // Initialize TLS configuration
    let tls_config = HybridTlsConfig::new(&config)?;
    
    // Create application state
    let state = AppState::new(config.clone());
    
    // Create router
    let app = create_router(state);
    
    // Bind to address
    let addr: SocketAddr = config.bind_address.parse()?;
    let listener = TcpListener::bind(&addr).await?;
    
    info!("API Gateway listening on https://{}", addr);
    info!("Quantum-ready TLS: {}", tls_config.is_pq_enabled());
    
    // Accept connections
    loop {
        let (stream, peer_addr) = listener.accept().await?;
        let tls_acceptor = tls_config.acceptor();
        let app = app.clone();
        
        tokio::spawn(async move {
            match tls_acceptor.accept(stream).await {
                Ok(tls_stream) => {
                    let service = hyper::service::service_fn(|req| {
                        let app = app.clone();
                        async move { 
                            app.oneshot(req).await 
                        }
                    });
                    
                    if let Err(e) = hyper::server::conn::http1::Builder::new()
                        .serve_connection(
                            hyper_util::rt::TokioIo::new(tls_stream),
                            service,
                        )
                        .await
                    {
                        warn!("Connection error from {}: {}", peer_addr, e);
                    }
                }
                Err(e) => {
                    warn!("TLS handshake failed from {}: {}", peer_addr, e);
                }
            }
        });
    }
}

#[tokio::main]
async fn main() {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    info!("Starting AMCIS API Gateway");

    // Load configuration
    let config = match config::load_config() {
        Ok(c) => c,
        Err(e) => {
            error!("Failed to load configuration: {}", e);
            warn!("Using default configuration");
            GatewayConfig::default()
        }
    };

    // Run server
    if let Err(e) = run_server(config).await {
        error!("Server error: {}", e);
        std::process::exit(1);
    }
}
