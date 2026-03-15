#!/bin/sh
# Vault Initialization Script for AMCIS Development
# ==================================================

set -e

echo "Waiting for Vault to be ready..."
until vault status > /dev/null 2>&1; do
  sleep 1
done

echo "Vault is ready. Initializing..."

# Enable KV v2 secrets engine
vault secrets enable -version=2 -path=secret kv || true
vault secrets enable -version=2 -path=amcis kv || true

# Create basic secret structure
vault kv put amcis/database \
  username=amcis \
  password=amcis \
  host=postgres \
  port=5432 \
  database=amcis

vault kv put amcis/redis \
  url=redis://redis:6379/0

vault kv put amcis/api \
  secret_key=dev-secret-key-change-in-production \
  jwt_secret=dev-jwt-secret-change-in-production

# Enable AppRole auth method
vault auth enable approle || true

# Create a policy for AMCIS
cat << EOF | vault policy write amcis-policy -
path "amcis/*" {
  capabilities = ["read", "list"]
}

path "secret/*" {
  capabilities = ["read", "list"]
}
EOF

# Create an AppRole for AMCIS
vault write auth/approle/role/amcis \
  token_policies=amcis-policy \
  token_ttl=1h \
  token_max_ttl=4h

# Get the RoleID
ROLE_ID=$(vault read -field=role_id auth/approle/role/amcis/role-id)
echo "AppRole RoleID: $ROLE_ID"

# Generate a SecretID
SECRET_ID=$(vault write -field=secret_id -f auth/approle/role/amcis/secret-id)
echo "AppRole SecretID: $SECRET_ID"

echo "Vault initialization complete!"
echo ""
echo "To login with AppRole:"
echo "  vault write auth/approle/login role_id=$ROLE_ID secret_id=$SECRET_ID"
