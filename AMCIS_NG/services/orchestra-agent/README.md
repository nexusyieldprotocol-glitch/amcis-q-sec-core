# AMCIS Orchestra Agent

Central orchestration hub for the AMCIS NG platform with safety-first design and human-in-the-loop governance.

## Core Responsibilities

| Function | Description |
|----------|-------------|
| **Agent Coordination** | Routes tasks to 2 specialist agents, manages retries via `/slash` commands |
| **Safety Enforcement** | Never executes destructive crypto ops without signed human approval |
| **Human Oversight** | Presents concise decision packages to gatekeepers for approval |
| **Audit Trail** | Immutable blockchain-backed ledger with hash chaining |
| **Explainability** | Every automated decision produces 3-line rationale + affected assets |

## Safety Constraints

- **Destructive Crypto Operations**: Require Ed25519-signed human approval
- **Parallel Key Rotations**: Limited to `MAX_PARALLEL_KEY_ROTATIONS = 2`
- **Agent Starvation**: Detected after 5 minutes, triggers reassignment
- **Retry Limits**: Max 3 attempts before safe rollback playbook

## API Endpoints

### Task Management
```
POST   /tasks              # Submit new task
POST   /tasks/:id/approve  # Human approves task (requires signature)
POST   /tasks/:id/reject   # Human rejects task
GET    /tasks/status       # Queue status
```

### Agent Management
```
POST   /agents/register        # Register new agent
POST   /agents/:id/heartbeat   # Agent health ping
```

### Audit
```
GET    /audit/verify       # Verify chain integrity
```

## Decision Package Format

```
╔══════════════════════════════════════════════════════════════════════════╗
║           AMCIS ORCHESTRA - HUMAN APPROVAL REQUIRED                      ║
╠══════════════════════════════════════════════════════════════════════════╣
║  TASK ID:       <uuid>
║  TYPE:          DestroyKey
║  CLASSIFICATION: Destructive
╠══════════════════════════════════════════════════════════════════════════╣
║  RATIONALE:
║  1. WHY:  Destructive crypto operation detected in safety classification
║  2. WHAT: Operation will impact assets: prod-db-key, api-signing-key
║  3. RISK: IRREVERSIBLE ACTION: Key destruction is permanent
╠══════════════════════════════════════════════════════════════════════════╣
║  AFFECTED ASSETS: prod-db-key, api-signing-key
║  
║  ⚠️  THIS IS A DESTRUCTIVE OPERATION THAT CANNOT BE UNDONE
╚══════════════════════════════════════════════════════════════════════════╝
```

## Integrations

- **Message Bus**: RabbitMQ for agent communication
- **Service Registry**: Agent discovery and health tracking
- **Policy Engine**: Real-time policy enforcement
- **Ticketing System**: Escalation workflow integration
- **Audit Ledger**: Blockchain-backed immutable storage

## Running

```bash
cargo run --bin amcis-orchestra-agent
```

Or via Docker Compose:
```bash
docker-compose up orchestra-agent
```
