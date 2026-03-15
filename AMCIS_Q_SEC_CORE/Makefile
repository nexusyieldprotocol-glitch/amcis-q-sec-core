# AMCIS Q-Sec-Core Makefile
# =========================

.PHONY: help install test lint format typecheck clean docker run

.DEFAULT_GOAL := help

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install package in development mode
	pip install -e ".[dev]"

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ -v --cov=AMCIS_Q_SEC_CORE --cov-report=term-missing --cov-report=html

lint: ## Run linter
	ruff check .

lint-fix: ## Run linter with auto-fix
	ruff check . --fix

format: ## Format code
	black .
	isort .

typecheck: ## Run type checker
	mypy src/ --ignore-missing-imports

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

docker-build: ## Build Docker image
	docker build -t amcis-q-sec-core:latest .

docker-run: ## Run Docker container
	docker run -p 8080:8080 --env-file .env amcis-q-sec-core:latest

run: ## Run development server
	uvicorn src.amcis_main:app --reload --host 0.0.0.0 --port 8080

all: clean install lint typecheck test ## Run full CI pipeline
