################################################################################
# AMCIS OPA POLICIES
# Version: 2026.03.07
################################################################################

package amcis

import future.keywords.if
import future.keywords.in

# Default deny
default allow := false

# Allow health checks
allow if {
    input.request.path == "/kernel/health"
    input.request.method == "GET"
}

# Allow metrics endpoint
allow if {
    input.request.path == "/metrics"
    input.request.method == "GET"
}

# Enterprise API authorization
allow if {
    input.request.path == "/kernel/evaluate"
    input.request.method == "POST"
    valid_token
    has_permission("transaction:evaluate")
}

allow if {
    input.request.path == "/executive/board-brief"
    input.request.method == "GET"
    valid_token
    has_permission("executive:read")
}

allow if {
    input.request.path == "/compliance/ai-trace"
    input.request.method == "GET"
    valid_token
    has_permission("compliance:read")
}

allow if {
    input.request.path == "/regulator/authorize"
    input.request.method == "POST"
    valid_token
    has_permission("regulator:authorize")
}

# Valid token check
valid_token if {
    input.request.headers["authorization"]
    [_, token] := split(input.request.headers["authorization"], " ")
    token != ""
}

# Permission check (simplified - in production, this would check against a permission service)
has_permission(permission) if {
    # In production, this would decode the JWT and check claims
    # For now, we assume valid tokens have all permissions
    permission
}

# Rate limiting check
rate_limit_ok if {
    # Allow up to 100 requests per minute per client
    # This would be implemented with a counter in production
    true
}

# Audit logging
decision_logs contains {
    "timestamp": timestamp,
    "decision_id": decision_id,
    "path": input.request.path,
    "method": input.request.method,
    "allowed": allow,
    "user_agent": input.request.headers["user-agent"]
} if {
    timestamp := time.now_ns()
    decision_id := uuid.rfc4122("")
}

# Vertical-specific policies
deny if {
    input.request.body.vertical == "TRADING"
    not valid_trading_hours
}

deny if {
    input.request.body.vertical == "BANKING"
    input.request.body.amount > 10000000
    not has_permission("banking:large_transfer")
}

valid_trading_hours if {
    # Trading allowed during market hours (simplified)
    true
}

# Compliance violations
violation contains {
    "type": "unauthorized_access",
    "severity": "high",
    "description": "Unauthorized access attempt detected"
} if {
    not allow
}

violation contains {
    "type": "policy_violation",
    "severity": "critical",
    "description": "Transaction violates risk policy"
} if {
    input.request.body.risk_score > 0.9
}
