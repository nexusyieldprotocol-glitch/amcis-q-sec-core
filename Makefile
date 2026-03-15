# AMCIS Unified Makefile
# =======================

.PHONY: help install test lint typecheck format clean docker-up docker-down deploy

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
RED := \033[31m
YELLOW := \033[33m
RESET := \033[0m

help: ## Show this help message
	@echo "$(BLUE)AMCIS Unified Build System$(RESET)"
	@echo "=========================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# =============================================================================
# Installation
# =============================================================================

install: ## Install dependencies
	@echo "$(BLUE)Installing dependencies...$(RESET)"
	cd AMCIS_Q_SEC_CORE && pip install -e ".[dev]"
	@echo "$(GREEN)Installation complete!$(RESET)"

install-prod: ## Install production dependencies only
	@echo "$(BLUE)Installing production dependencies...$(RESET)"
	cd AMCIS_Q_SEC_CORE && pip install -e .
	@echo "$(GREEN)Installation complete!$(RESET)"

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(RESET)"
	cd AMCIS_Q_SEC_CORE && pytest tests/ -v --tb=short
	@echo "$(GREEN)Tests complete!$(RESET)"

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(RESET)"
	cd AMCIS_Q_SEC_CORE && pytest tests/ -v --tb=short \
		--cov=AMCIS_Q_SEC_CORE \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-report=xml
	@echo "$(GREEN)Coverage report generated!$(RESET)"

test-fast: ## Run tests without coverage (faster)
	@echo "$(BLUE)Running tests (fast mode)...$(RESET)"
	cd AMCIS_Q_SEC_CORE && pytest tests/ -v --tb=short -x
	@echo "$(GREEN)Tests complete!$(RESET)"

test-file: ## Run specific test file (use: make test-file FILE=test_crypto.py)
	@echo "$(BLUE)Running $(FILE)...$(RESET)"
	cd AMCIS_Q_SEC_CORE && pytest tests/$(FILE) -v

test-nist-csf: ## Run NIST CSF tests
	@echo "$(BLUE)Running NIST CSF tests...$(RESET)"
	cd AMCIS_Q_SEC_CORE && pytest tests/test_nist_csf.py -v
	@echo "$(GREEN)NIST CSF tests complete!$(RESET)"

# =============================================================================
# Linting & Formatting
# =============================================================================

lint: ## Run all linters
	@echo "$(BLUE)Running linters...$(RESET)"
	cd AMCIS_Q_SEC_CORE && ruff check .
	@echo "$(GREEN)Linting complete!$(RESET)"

lint-fix: ## Run linters with auto-fix
	@echo "$(BLUE)Running linters with auto-fix...$(RESET)"
	cd AMCIS_Q_SEC_CORE && ruff check . --fix
	@echo "$(GREEN)Linting complete!$(RESET)"

format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(RESET)"
	cd AMCIS_Q_SEC_CORE && black .
	@echo "$(GREEN)Formatting complete!$(RESET)"

format-check: ## Check code formatting
	@echo "$(BLUE)Checking code formatting...$(RESET)"
	cd AMCIS_Q_SEC_CORE && black --check .
	@echo "$(GREEN)Formatting check complete!$(RESET)"

isort: ## Sort imports
	@echo "$(BLUE)Sorting imports...$(RESET)"
	cd AMCIS_Q_SEC_CORE && isort .
	@echo "$(GREEN)Import sorting complete!$(RESET)"

# =============================================================================
# Type Checking
# =============================================================================

typecheck: ## Run mypy type checking
	@echo "$(BLUE)Running type checker...$(RESET)"
	cd AMCIS_Q_SEC_CORE && mypy src/ --ignore-missing-imports
	@echo "$(GREEN)Type checking complete!$(RESET)"

typecheck-strict: ## Run mypy with strict mode
	@echo "$(BLUE)Running strict type checker...$(RESET)"
	cd AMCIS_Q_SEC_CORE && mypy src/ --strict
	@echo "$(GREEN)Type checking complete!$(RESET)"

# =============================================================================
# Security
# =============================================================================

security-check: ## Run security checks
	@echo "$(BLUE)Running security checks...$(RESET)"
	cd AMCIS_Q_SEC_CORE && bandit -r src/ -f json -o bandit-report.json || true
	cd AMCIS_Q_SEC_CORE && safety check || true
	@echo "$(GREEN)Security checks complete!$(RESET)"
	@echo "Reports saved to bandit-report.json and safety-report.json"

# =============================================================================
# Docker
# =============================================================================

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(RESET)"
	docker-compose build
	@echo "$(GREEN)Docker build complete!$(RESET)"

docker-up: ## Start all services with Docker Compose
	@echo "$(BLUE)Starting Docker services...$(RESET)"
	docker-compose up -d
	@echo "$(GREEN)Services started!$(RESET)"
	@echo "API: http://localhost:8080"
	@echo "Grafana: http://localhost:3000"
	@echo "Vault: http://localhost:8200"

docker-down: ## Stop all Docker services
	@echo "$(BLUE)Stopping Docker services...$(RESET)"
	docker-compose down
	@echo "$(GREEN)Services stopped!$(RESET)"

docker-logs: ## View Docker logs
	@echo "$(BLUE)Viewing logs...$(RESET)"
	docker-compose logs -f

docker-clean: ## Clean up Docker containers and volumes
	@echo "$(YELLOW)Cleaning up Docker resources...$(RESET)"
	docker-compose down -v
	docker system prune -f
	@echo "$(GREEN)Docker cleanup complete!$(RESET)"

docker-shell: ## Open shell in running container
	@echo "$(BLUE)Opening shell in amcis-core...$(RESET)"
	docker-compose exec amcis-core /bin/bash

# =============================================================================
# Database
# =============================================================================

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(RESET)"
	cd AMCIS_Q_SEC_CORE && alembic upgrade head
	@echo "$(GREEN)Migrations complete!$(RESET)"

db-rollback: ## Rollback database migrations
	@echo "$(YELLOW)Rolling back database migrations...$(RESET)"
	cd AMCIS_Q_SEC_CORE && alembic downgrade -1
	@echo "$(GREEN)Rollback complete!$(RESET)"

db-reset: ## Reset database (DANGER: All data will be lost)
	@echo "$(RED)WARNING: This will delete all data!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ $$confirm = y ] || exit 1
	cd AMCIS_Q_SEC_CORE && alembic downgrade base
	cd AMCIS_Q_SEC_CORE && alembic upgrade head
	@echo "$(GREEN)Database reset complete!$(RESET)"

db-backup: ## Backup database
	@echo "$(BLUE)Backing up database...$(RESET)"
	pg_dump -h localhost -U amcis amcis > backup-$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup complete!$(RESET)"

db-restore: ## Restore database from backup (use: make db-restore FILE=backup.sql)
	@echo "$(BLUE)Restoring database from $(FILE)...$(RESET)"
	psql -h localhost -U amcis amcis < $(FILE)
	@echo "$(GREEN)Restore complete!$(RESET)"

db-seed: ## Seed database with test data
	@echo "$(BLUE)Seeding database...$(RESET)"
	cd AMCIS_Q_SEC_CORE && python scripts/seed_db.py
	@echo "$(GREEN)Database seeded!$(RESET)"

# =============================================================================
# Development
# =============================================================================

dev: ## Start development server
	@echo "$(BLUE)Starting development server...$(RESET)"
	cd AMCIS_Q_SEC_CORE && uvicorn src.amcis_main:app --reload --host 0.0.0.0 --port 8080

run: ## Run production server
	@echo "$(BLUE)Starting production server...$(RESET)"
	cd AMCIS_Q_SEC_CORE && gunicorn src.amcis_main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080

docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(RESET)"
	cd AMCIS_Q_SEC_CORE && mkdocs build
	@echo "$(GREEN)Documentation generated!$(RESET)"

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Starting documentation server...$(RESET)"
	cd AMCIS_Q_SEC_CORE && mkdocs serve

# =============================================================================
# Testing & CI
# =============================================================================

ci: lint typecheck test ## Run all CI checks
	@echo "$(GREEN)All CI checks passed!$(RESET)"

pre-commit: format isort lint typecheck test-fast ## Run pre-commit hooks
	@echo "$(GREEN)Pre-commit checks complete!$(RESET)"

# =============================================================================
# Deployment
# =============================================================================

deploy-staging: ## Deploy to staging
	@echo "$(BLUE)Deploying to staging...$(RESET)"
	kubectl apply -k k8s/overlays/staging
	kubectl rollout status deployment/amcis-core -n amcis-staging
	@echo "$(GREEN)Staging deployment complete!$(RESET)"

deploy-prod: ## Deploy to production
	@echo "$(YELLOW)Deploying to PRODUCTION...$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ $$confirm = y ] || exit 1
	kubectl apply -k k8s/overlays/production
	kubectl rollout status deployment/amcis-core -n amcis-production
	@echo "$(GREEN)Production deployment complete!$(RESET)"

k8s-rollback: ## Rollback Kubernetes deployment
	@echo "$(YELLOW)Rolling back deployment...$(RESET)"
	kubectl rollout undo deployment/amcis-core -n amcis
	@echo "$(GREEN)Rollback complete!$(RESET)"

# =============================================================================
# Utilities
# =============================================================================

clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(RESET)"
	cd AMCIS_Q_SEC_CORE && rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)Cleanup complete!$(RESET)"

requirements: ## Generate requirements.txt from pyproject.toml
	@echo "$(BLUE)Generating requirements...$(RESET)"
	cd AMCIS_Q_SEC_CORE && pip-compile pyproject.toml -o requirements.txt
	@echo "$(GREEN)Requirements generated!$(RESET)"

health: ## Check system health
	@echo "$(BLUE)Checking system health...$(RESET)"
	@curl -s http://localhost:8080/health/live | jq .
	@curl -s http://localhost:8080/health/ready | jq .
	@echo "$(GREEN)Health check complete!$(RESET)"

vault-init: ## Initialize Vault
	@echo "$(BLUE)Initializing Vault...$(RESET)"
	@docker-compose exec vault vault operator init -key-shares=5 -key-threshold=3
	@echo "$(YELLOW)SAVE THE UNSEAL KEYS AND ROOT TOKEN!$(RESET)"

vault-unseal: ## Unseal Vault
	@echo "$(BLUE)Unsealing Vault...$(RESET)"
	@docker-compose exec vault vault operator unseal

# =============================================================================
# All-in-one commands
# =============================================================================

all: clean install lint typecheck test ## Run full build pipeline
	@echo "$(GREEN)Full build pipeline complete!$(RESET)"

setup: install db-migrate db-seed ## Initial project setup
	@echo "$(GREEN)Setup complete! You can now run 'make dev' to start the server.$(RESET)"
