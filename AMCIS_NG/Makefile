# AMCIS NG Makefile

.PHONY: all build test clean deploy docs

# Default target
all: build

# Build all components
build:
	@echo "Building AMCIS NG..."
	cargo build --release
	cd python/ai-ml && pip install -e .

# Build Docker images
docker-build:
	docker build -t amcis/api-gateway:latest -f services/api-gateway/Dockerfile .
	docker build -t amcis/vault-secrets:latest -f services/vault-secrets/Dockerfile .
	docker build -t amcis/threat-intel:latest -f services/threat-intel/Dockerfile .
	docker build -t amcis/soc-orchestrator:latest -f services/soc-orchestrator/Dockerfile .
	docker build -t amcis/ai-engine:latest -f python/ai-ml/Dockerfile .

# Run tests
test:
	cargo test --all
	cd python/ai-ml && pytest

# Run integration tests
test-integration:
	cd tests/integration && ./run_tests.sh

# Deploy locally with Docker Compose
deploy-local:
	cd deployments && docker-compose up -d

# Deploy to Kubernetes
deploy-k8s:
	kubectl apply -f deployments/k8s/namespace.yaml
	kubectl apply -f deployments/k8s/
	helm upgrade --install amcis deployments/helm/amcis

# Generate documentation
docs:
	cd docs && mdbook build
	cargo doc --no-deps --open

# Run linting
lint:
	cargo clippy --all-targets --all-features -- -D warnings
	cd python && flake8 amcis_*

# Format code
fmt:
	cargo fmt --all
	cd python && black amcis_*

# Security audit
audit:
	cargo audit
	cd python && safety check

# Clean build artifacts
clean:
	cargo clean
	rm -rf target/
	rm -rf python/**/build/
	rm -rf python/**/__pycache__/

# Setup development environment
setup:
	rustup target add x86_64-unknown-linux-musl
	cargo install cargo-audit cargo-tarpaulin
	pip install maturin black flake8 pytest

# Run benchmarks
bench:
	cargo bench

# Start development server
dev:
	cargo run --bin amcis-cli

# Help
help:
	@echo "AMCIS NG Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  build          - Build all Rust components"
	@echo "  docker-build   - Build Docker images"
	@echo "  test           - Run unit tests"
	@echo "  test-integration - Run integration tests"
	@echo "  deploy-local   - Deploy locally with Docker Compose"
	@echo "  deploy-k8s     - Deploy to Kubernetes"
	@echo "  docs           - Generate documentation"
	@echo "  lint           - Run linters"
	@echo "  fmt            - Format code"
	@echo "  audit          - Security audit"
	@echo "  clean          - Clean build artifacts"
	@echo "  setup          - Setup development environment"
