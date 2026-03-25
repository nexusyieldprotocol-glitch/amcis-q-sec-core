#!/bin/bash
################################################################################
# AMCIS DEPLOYMENT VERIFICATION SCRIPT
# Version: 2026.03.07
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DEPLOYMENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERBOSE=${VERBOSE:-false}
TIMEOUT=${TIMEOUT:-60}

# Counters
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Functions
log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS_COUNT++)) || true
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL_COUNT++)) || true
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARN_COUNT++)) || true
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check command exists
check_command() {
    if command -v "$1" &> /dev/null; then
        log_pass "$1 is installed"
        if [ "$VERBOSE" = true ]; then
            log_info "  Version: $($1 --version 2>/dev/null | head -1 || echo 'N/A')"
        fi
        return 0
    else
        log_fail "$1 is not installed"
        return 1
    fi
}

# Check Docker container
check_container() {
    local name=$1
    local port=${2:-}
    
    if docker ps | grep -q "$name"; then
        if [ -n "$port" ]; then
            if curl -sf "http://localhost:$port/health" > /dev/null 2>&1 || \
               curl -sf "http://localhost:$port/kernel/health" > /dev/null 2>&1 || \
               curl -sf "http://localhost:$port" > /dev/null 2>&1; then
                log_pass "$name is running and healthy (port $port)"
            else
                log_warn "$name is running but health check failed"
            fi
        else
            log_pass "$name is running"
        fi
    else
        log_fail "$name is not running"
    fi
}

# Check Kubernetes resource
check_k8s_resource() {
    local type=$1
    local name=$2
    local namespace=${3:-amcis-system}
    
    if kubectl get "$type" -n "$namespace" "$name" > /dev/null 2>&1; then
        local status=$(kubectl get "$type" -n "$namespace" "$name" -o jsonpath='{.status.phase}' 2>/dev/null || echo 'Unknown')
        if [ "$status" = "Running" ] || [ "$status" = "Active" ] || [ "$status" = "Bound" ]; then
            log_pass "$type/$name in $namespace is $status"
        else
            log_warn "$type/$name in $namespace status: $status"
        fi
    else
        log_fail "$type/$name not found in namespace $namespace"
    fi
}

# Verify prerequisites
verify_prerequisites() {
    log_info "Checking prerequisites..."
    
    check_command docker
    check_command docker-compose
    check_command kubectl
    check_command curl
    check_command jq
    
    echo ""
}

# Verify Docker deployment
verify_docker() {
    log_info "Verifying Docker deployment..."
    
    check_container "amcis-postgres" 5432
    check_container "amcis-redis" 6379
    check_container "amcis-opa" 8181
    check_container "amcis-enterprise-api" 8000
    check_container "amcis-sphinx-node-1" 8081
    check_container "amcis-prometheus" 9090
    check_container "amcis-grafana" 3000
    
    echo ""
}

# Verify Kubernetes deployment
verify_kubernetes() {
    log_info "Verifying Kubernetes deployment..."
    
    # Check namespace
    if kubectl get namespace amcis-system > /dev/null 2>&1; then
        log_pass "Namespace amcis-system exists"
    else
        log_fail "Namespace amcis-system not found"
        return
    fi
    
    # Check deployments
    check_k8s_resource "deployment" "enterprise-api"
    check_k8s_resource "statefulset" "postgres"
    check_k8s_resource "statefulset" "sphinx-node"
    
    # Check services
    check_k8s_resource "service" "enterprise-api"
    check_k8s_resource "service" "postgres"
    check_k8s_resource "service" "sphinx"
    
    # Check PVCs
    check_k8s_resource "pvc" "postgres-data"
    
    echo ""
}

# Verify endpoints
verify_endpoints() {
    log_info "Verifying service endpoints..."
    
    local endpoints=(
        "http://localhost:8000/kernel/health:Enterprise API"
        "http://localhost:8081/health:SPHINX Node 1"
        "http://localhost:9090/-/healthy:Prometheus"
        "http://localhost:3000/api/health:Grafana"
    )
    
    for endpoint in "${endpoints[@]}"; do
        IFS=':' read -r url name <<< "$endpoint"
        if curl -sf "$url" > /dev/null 2>&1; then
            log_pass "$name endpoint is accessible"
        else
            log_fail "$name endpoint is not accessible"
        fi
    done
    
    echo ""
}

# Verify security
verify_security() {
    log_info "Verifying security configuration..."
    
    # Check if environment file has secure permissions
    if [ -f "$DEPLOYMENT_DIR/.env" ]; then
        local perms=$(stat -c %a "$DEPLOYMENT_DIR/.env" 2>/dev/null || stat -f %Lp "$DEPLOYMENT_DIR/.env" 2>/dev/null)
        if [ "$perms" = "600" ] || [ "$perms" = "0600" ]; then
            log_pass ".env file has secure permissions (600)"
        else
            log_warn ".env file permissions are $perms (should be 600)"
        fi
    fi
    
    # Check for default passwords
    if [ -f "$DEPLOYMENT_DIR/.env" ]; then
        if grep -q "changeme\|password123\|admin123" "$DEPLOYMENT_DIR/.env" 2>/dev/null; then
            log_warn "Default passwords detected in .env file"
        else
            log_pass "No default passwords detected"
        fi
    fi
    
    echo ""
}

# Performance check
verify_performance() {
    log_info "Checking performance metrics..."
    
    # Check API response time
    local start_time=$(date +%s%N)
    if curl -sf "http://localhost:8000/kernel/health" > /dev/null 2>&1; then
        local end_time=$(date +%s%N)
        local duration=$(( (end_time - start_time) / 1000000 ))
        if [ $duration -lt 1000 ]; then
            log_pass "API response time: ${duration}ms (< 1s)"
        else
            log_warn "API response time: ${duration}ms (should be < 1s)"
        fi
    else
        log_fail "Cannot measure API response time"
    fi
    
    echo ""
}

# Generate report
generate_report() {
    log_info "==============================================="
    log_info "AMCIS VERIFICATION REPORT"
    log_info "==============================================="
    log_info "Total Checks: $((PASS_COUNT + FAIL_COUNT + WARN_COUNT))"
    log_pass "Passed: $PASS_COUNT"
    log_fail "Failed: $FAIL_COUNT"
    log_warn "Warnings: $WARN_COUNT"
    log_info "==============================================="
    
    if [ $FAIL_COUNT -eq 0 ]; then
        log_info "Status: ALL CHECKS PASSED"
        return 0
    else
        log_info "Status: VERIFICATION FAILED"
        return 1
    fi
}

# Main
main() {
    log_info "AMCIS Deployment Verification"
    log_info "Version: 2026.03.07"
    echo ""
    
    verify_prerequisites
    verify_docker
    verify_kubernetes
    verify_endpoints
    verify_security
    verify_performance
    
    generate_report
}

# Handle arguments
case "${1:-}" in
    --verbose|-v)
        VERBOSE=true
        main
        ;;
    --docker-only)
        verify_docker
        generate_report
        ;;
    --k8s-only)
        verify_kubernetes
        generate_report
        ;;
    *)
        main
        ;;
esac
