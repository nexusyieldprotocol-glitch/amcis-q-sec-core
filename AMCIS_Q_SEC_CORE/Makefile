# AMCIS Q-SEC Core Makefile
.PHONY: all build test clean docker deploy

# Default target
all: build

# Build all services
build:
	@echo "Building Rust services..."
	cargo build --workspace --release
	@echo "Building Go auth service..."
	cd auth_service && go build -o amcis-auth-service
	@echo "Build complete!"

# Build individual services
crypto:
	cargo build --release -p amcis-crypto-service

auth:
	cd auth_service && go build -o amcis-auth-service

gateway:
	cargo build --release -p amcis-api-gateway

# Run tests
test:
	@echo "Running Rust tests..."
	cargo test --workspace
	@echo "Running Go tests..."
	cd auth_service && go test -v ./...

# Run static analysis
lint:
	@echo "Running cargo clippy..."
	cargo clippy --workspace -- -D warnings
	@echo "Running go vet..."
	cd auth_service && go vet ./...

# Security audit
audit:
	@echo "Running cargo audit..."
	cargo audit
	@echo "Running govulncheck..."
	cd auth_service && govulncheck ./...

# Clean build artifacts
clean:
	cargo clean
	rm -f auth_service/amcis-auth-service

# Docker build
docker:
	@echo "Building Docker images..."
	docker-compose build

# Docker run
docker-up:
	docker-compose up -d

# Docker stop
docker-down:
	docker-compose down

# Run development stack
dev:
	@echo "Starting development stack..."
	@echo "Note: Run each service in separate terminals"
	@echo "1. cargo run --release -p amcis-crypto-service"
	@echo "2. cd auth_service && go run main.go"
	@echo "3. cargo run --release -p amcis-api-gateway"

# Generate certificates for testing
certs:
	@echo "Generating test certificates..."
	mkdir -p certs
	openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem \
		-days 365 -nodes -subj "/CN=localhost"
	@echo "Certificates generated in certs/"

# Install dependencies
deps:
	@echo "Installing Rust dependencies..."
	rustup update
	cargo fetch
	@echo "Installing Go dependencies..."
	cd auth_service && go mod download
	@echo "Installing tools..."
	cargo install cargo-audit
	go install golang.org/x/vuln/cmd/govulncheck@latest

# Format code
fmt:
	cargo fmt --all
	cd auth_service && go fmt ./...

# Help
help:
	@echo "AMCIS Q-SEC Core Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  build      - Build all services"
	@echo "  crypto     - Build crypto service only"
	@echo "  auth       - Build auth service only"
	@echo "  gateway    - Build API gateway only"
	@echo "  test       - Run all tests"
	@echo "  lint       - Run static analysis"
	@echo "  audit      - Run security audit"
	@echo "  clean      - Clean build artifacts"
	@echo "  docker     - Build Docker images"
	@echo "  docker-up  - Start Docker stack"
	@echo "  docker-down - Stop Docker stack"
	@echo "  dev        - Show development commands"
	@echo "  certs      - Generate test certificates"
	@echo "  deps       - Install dependencies"
	@echo "  fmt        - Format code"
	@echo "  help       - Show this help"
