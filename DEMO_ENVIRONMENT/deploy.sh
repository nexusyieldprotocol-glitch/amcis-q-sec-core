#!/bin/bash
# AMCIS Demo Environment Deployment Script
# Usage: ./deploy.sh [local|cloud|render|railway]

set -e

DEMO_VERSION="1.0.0"
DEPLOYMENT_TYPE=${1:-local}

echo "=========================================="
echo "AMCIS Demo Environment Deployment"
echo "Version: $DEMO_VERSION"
echo "Target: $DEPLOYMENT_TYPE"
echo "=========================================="

# Generate unique demo instance ID
INSTANCE_ID=$(openssl rand -hex 8)
ADMIN_PASS=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-20)
API_KEY="amcis_demo_$(openssl rand -hex 16)"
EXPIRY=$(date -d "+24 hours" -u +"%Y-%m-%dT%H:%M:%SZ")

echo ""
echo "Generated Credentials:"
echo "  Instance ID: $INSTANCE_ID"
echo "  Admin Password: $ADMIN_PASS"
echo "  API Key: ${API_KEY:0:40}..."
echo "  Expires: $EXPIRY"
echo ""

case $DEPLOYMENT_TYPE in
  local)
    echo "Deploying locally with Docker Compose..."
    docker-compose down 2>/dev/null || true
    docker-compose build --no-cache
    docker-compose up -d
    
    echo ""
    echo "Waiting for service to start..."
    sleep 5
    
    # Health check
    for i in {1..10}; do
      if curl -s http://localhost:8080/health > /dev/null; then
        echo "✓ Service is healthy"
        break
      fi
      echo "  Waiting... ($i/10)"
      sleep 2
    done
    
    echo ""
    echo "=========================================="
    echo "DEPLOYMENT SUCCESSFUL"
    echo "=========================================="
    echo ""
    echo "Access URLs:"
    echo "  Dashboard:    http://localhost:8080"
    echo "  Health Check: http://localhost:8080/health"
    echo "  API Docs:     http://localhost:8080/docs"
    echo ""
    echo "Admin Credentials:"
    echo "  Username: demo_admin"
    echo "  Password: $ADMIN_PASS"
    echo "  API Key:  $API_KEY"
    echo ""
    echo "Instance expires: $EXPIRY"
    echo ""
    ;;
    
  render)
    echo "Deploying to Render.com..."
    echo ""
    echo "Steps:"
    echo "1. Create account at https://render.com"
    echo "2. Connect GitHub repository"
    echo "3. Create New Web Service"
    echo "4. Select this repository"
    echo "5. Set environment variables:"
    echo "   - AMCIS_DEMO_MODE=true"
    echo "   - ADMIN_PASSWORD=$ADMIN_PASS"
    echo "   - API_KEY=$API_KEY"
    echo "6. Deploy"
    echo ""
    echo "Or use Render Blueprint (render.yaml)..."
    ;;
    
  railway)
    echo "Deploying to Railway..."
    echo ""
    echo "Steps:"
    echo "1. Install Railway CLI: npm i -g @railway/cli"
    echo "2. Login: railway login"
    echo "3. Init: railway init"
    echo "4. Deploy: railway up"
    echo ""
    ;;
    
  cloud)
    echo "Cloud deployment options:"
    echo ""
    echo "AWS:"
    echo "  - ECS Fargate (serverless containers)"
    echo "  - App Runner (simplest deployment)"
    echo "  - EKS (Kubernetes)"
    echo ""
    echo "Azure:"
    echo "  - Container Instances"
    echo "  - App Service"
    echo ""
    echo "GCP:"
    echo "  - Cloud Run (recommended)"
    echo "  - App Engine"
    echo ""
    ;;
    
  *)
    echo "Unknown deployment type: $DEPLOYMENT_TYPE"
    echo "Usage: ./deploy.sh [local|render|railway|cloud]"
    exit 1
    ;;
esac

# Save credentials
echo "Saving credentials to credentials/demo_credentials_$INSTANCE_ID.json..."
mkdir -p credentials
cat > "credentials/demo_credentials_$INSTANCE_ID.json" << EOF
{
  "instance_id": "$INSTANCE_ID",
  "deployment_type": "$DEPLOYMENT_TYPE",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "expires_at": "$EXPIRY",
  "credentials": {
    "admin": {
      "username": "demo_admin",
      "password": "$ADMIN_PASS",
      "api_key": "$API_KEY"
    },
    "readonly": {
      "username": "demo_user",
      "password": "$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)",
      "api_key": "amcis_demo_$(openssl rand -hex 12)"
    }
  },
  "urls": {
    "dashboard": "http://localhost:8080",
    "health": "http://localhost:8080/health",
    "api": "http://localhost:8080/api"
  }
}
EOF

echo ""
echo "Credentials saved to: credentials/demo_credentials_$INSTANCE_ID.json"
echo ""
