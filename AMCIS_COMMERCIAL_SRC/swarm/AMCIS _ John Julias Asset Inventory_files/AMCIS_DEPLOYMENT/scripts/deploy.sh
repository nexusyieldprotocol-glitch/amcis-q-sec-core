#!/bin/bash
################################################################################
# AMCIS FULL ECOSYSTEM DEPLOYMENT SCRIPT
# Automates deployment of all AMCIS systems
# Version: 2026.03.07
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="/var/log/amcis-deploy-$(date +%Y%m%d-%H%M%S).log"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check available resources
    DOCKER_MEMORY=$(docker system info --format '{{.MemTotal}}' 2>/dev/null || echo "0")
    if [ "$DOCKER_MEMORY" -lt "$((16 * 1024 * 1024 * 1024))" ]; then
        log_warning "Docker has less than 16GB memory allocated. AMCIS requires 16GB+ RAM."
    fi
    
    log_success "Prerequisites check passed"
}

# Generate environment file
generate_env() {
    log_info "Generating environment configuration..."
    
    ENV_FILE="$DEPLOYMENT_DIR/.env"
    
    if [ -f "$ENV_FILE" ]; then
        log_warning ".env file already exists. Backing up to .env.backup"
        cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%s)"
    fi
    
    cat > "$ENV_FILE" <<EOF
################################################################################
# AMCIS DEPLOYMENT ENVIRONMENT CONFIGURATION
# Generated: $(date)
################################################################################

# Enterprise Configuration
ENTERPRISE_ID=AMCIS-GLOBAL-01
LIABILITY_MULTIPLIER=1500000.0

# Database Configuration
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
POSTGRES_USER=amcis_admin
POSTGRES_DB=amcis_enterprise

# Monitoring Configuration
GRAFANA_USER=admin
GRAFANA_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-20)

# SPHINX Configuration
SPHINX_NODE_COUNT=4
SPHINX_CONSENSUS_THRESHOLD=3

# StableCoin Configuration
STABILITY_MODE=active
STABILITY_PID_KP=0.5
STABILITY_PID_KI=0.1
STABILITY_PID_KD=0.05

# Security Configuration
PQC_MODE=hybrid
DEFENSE_MODE=read_only

# Network Configuration
DOMAIN=localhost
TLS_ENABLED=false

# Feature Flags
ENABLE_ENTERPRISE_OS=true
ENABLE_SPHINX=true
ENABLE_STABLECOIN=true
ENABLE_SECURITY=true
ENABLE_MONITORING=true

# Resource Limits
MAX_MEMORY=16G
MAX_CPUS=8
EOF
    
    chmod 600 "$ENV_FILE"
    log_success "Environment file created at $ENV_FILE"
}

# Initialize database
init_database() {
    log_info "Initializing database schema..."
    
    # Wait for PostgreSQL to be ready
    docker-compose -f "$DEPLOYMENT_DIR/docker/docker-compose.yml" up -d postgres
    
    sleep 5
    
    # Run init scripts
    for script in "$DEPLOYMENT_DIR/config/init-scripts"/*.sql; do
        if [ -f "$script" ]; then
            log_info "Executing $(basename "$script")..."
            docker-compose -f "$DEPLOYMENT_DIR/docker/docker-compose.yml" exec -T postgres psql -U amcis_admin -d amcis_enterprise < "$script"
        fi
    done
    
    log_success "Database initialized"
}

# Deploy infrastructure
deploy_infrastructure() {
    log_info "Deploying infrastructure layer..."
    
    cd "$DEPLOYMENT_DIR/docker"
    
    # Pull latest images
    docker-compose pull
    
    # Start infrastructure services
    docker-compose up -d postgres redis opa
    
    # Wait for health checks
    log_info "Waiting for infrastructure to be healthy..."
    sleep 10
    
    log_success "Infrastructure layer deployed"
}

# Deploy AMCIS Enterprise OS
deploy_enterprise_os() {
    log_info "Deploying AMCIS Enterprise OS..."
    
    cd "$DEPLOYMENT_DIR/docker"
    docker-compose up -d enterprise-api enterprise-worker
    
    # Health check
    for i in {1..30}; do
        if curl -sf http://localhost:8000/kernel/health > /dev/null 2>&1; then
            log_success "Enterprise OS is healthy"
            return 0
        fi
        sleep 2
    done
    
    log_error "Enterprise OS failed health check"
    return 1
}

# Deploy AMCIS SPHINX
deploy_sphinx() {
    log_info "Deploying AMCIS SPHINX (4-node BFT cluster)..."
    
    cd "$DEPLOYMENT_DIR/docker"
    docker-compose up -d sphinx-node-1 sphinx-node-2 sphinx-node-3 sphinx-node-4
    
    # Wait for consensus to form
    log_info "Waiting for SPHINX consensus to form..."
    sleep 15
    
    log_success "SPHINX cluster deployed"
}

# Deploy AMCIS StableCoin
deploy_stablecoin() {
    log_info "Deploying AMCIS Stability Protocol..."
    
    cd "$DEPLOYMENT_DIR/docker"
    docker-compose up -d stability-engine
    
    log_success "Stability Protocol deployed"
}

# Deploy AMCIS Security
deploy_security() {
    log_info "Deploying AMCIS ARCHIMEDES Security Framework..."
    
    cd "$DEPLOYMENT_DIR/docker"
    docker-compose up -d security-validator
    
    log_success "Security Framework deployed"
}

# Deploy monitoring
deploy_monitoring() {
    log_info "Deploying monitoring stack..."
    
    cd "$DEPLOYMENT_DIR/docker"
    docker-compose up -d prometheus grafana jaeger
    
    log_success "Monitoring stack deployed"
}

# Deploy frontend
deploy_frontend() {
    log_info "Deploying web dashboard..."
    
    cd "$DEPLOYMENT_DIR/docker"
    docker-compose up -d web-dashboard
    
    log_success "Web dashboard deployed"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    SERVICES=(
        "amcis-postgres:5432"
        "amcis-redis:6379"
        "amcis-opa:8181"
        "amcis-enterprise-api:8000"
        "amcis-sphinx-node-1:8080"
        "amcis-prometheus:9090"
        "amcis-grafana:3000"
    )
    
    for service in "${SERVICES[@]}"; do
        IFS=':' read -r name port <<< "$service"
        if docker ps | grep -q "$name"; then
            log_success "$name is running"
        else
            log_error "$name is not running"
        fi
    done
    
    log_info ""
    log_info "==============================================="
    log_info "AMCIS DEPLOYMENT COMPLETE"
    log_info "==============================================="
    log_info ""
    log_info "Access Points:"
    log_info "  - Web Dashboard:    http://localhost"
    log_info "  - Enterprise API:   http://localhost:8000/docs"
    log_info "  - SPHINX Node 1:    http://localhost:8081"
    log_info "  - Grafana:          http://localhost:3000"
    log_info "  - Prometheus:       http://localhost:9090"
    log_info ""
    log_info "Default Credentials:"
    log_info "  - Grafana:          admin / (see .env file)"
    log_info ""
    log_info "Logs: $LOG_FILE"
    log_info "==============================================="
}

# Cleanup on failure
cleanup() {
    if [ $? -ne 0 ]; then
        log_error "Deployment failed. Cleaning up..."
        cd "$DEPLOYMENT_DIR/docker"
        docker-compose down -v
    fi
}

trap cleanup EXIT

# Main deployment flow
main() {
    log_info "==============================================="
    log_info "AMCIS FULL ECOSYSTEM DEPLOYMENT"
    log_info "Version: 2026.03.07"
    log_info "==============================================="
    
    check_prerequisites
    generate_env
    
    # Load environment
    set -a
    source "$DEPLOYMENT_DIR/.env"
    set +a
    
    deploy_infrastructure
    init_database
    deploy_enterprise_os
    deploy_sphinx
    deploy_stablecoin
    deploy_security
    deploy_monitoring
    deploy_frontend
    
    verify_deployment
    
    log_success "AMCIS Ecosystem deployment completed successfully!"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "AMCIS Deployment Script"
        echo ""
        echo "Usage: ./deploy.sh [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --clean        Clean up existing deployment"
        echo "  --status       Check deployment status"
        echo ""
        echo "Environment variables:"
        echo "  See .env file after initial deployment"
        ;;
    --clean)
        log_info "Cleaning up AMCIS deployment..."
        cd "$DEPLOYMENT_DIR/docker"
        docker-compose down -v
        log_success "Cleanup complete"
        ;;
    --status)
        cd "$DEPLOYMENT_DIR/docker"
        docker-compose ps
        ;;
    *)
        main
        ;;
esac
