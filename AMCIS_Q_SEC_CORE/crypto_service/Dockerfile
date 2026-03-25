# Multi-stage build for AMCIS Crypto Service
FROM rust:1.75-bookworm AS builder

# Install dependencies
RUN apt-get update && apt-get install -y \
    libssl-dev \
    pkg-config \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Cargo files first for caching
COPY Cargo.toml Cargo.lock ./

# Create dummy main for dependency caching
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release && rm -rf src

# Copy actual source
COPY . .

# Build release
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy binary
COPY --from=builder /app/target/release/amcis-crypto-service /usr/local/bin/

# Create non-root user
RUN useradd -m -s /bin/bash amcis
USER amcis

EXPOSE 50051

ENTRYPOINT ["amcis-crypto-service"]
CMD ["--listen", "0.0.0.0:50051"]
