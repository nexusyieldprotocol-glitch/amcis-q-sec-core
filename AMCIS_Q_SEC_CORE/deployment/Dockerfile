# AMCIS_Q_SEC_CORE - Quantum-Secure Terminal Security Framework
# Hardened Container Image
# 
# Build: docker build -t amcis-q-sec-core:latest .
# Run:   docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE amcis-q-sec-core:latest

# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

# Security: Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim-bookworm AS runtime

# Security labels
LABEL maintainer="AMCIS Security Team <security@amcis.local>" \
      org.opencontainers.image.title="AMCIS Q-SEC CORE" \
      org.opencontainers.image.description="Quantum-Secure Terminal Security Framework" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="AMCIS" \
      security.amcis.compliance="NIST-800-53,FIPS-140-3"

# Security: Create non-root user
RUN groupadd -r amcis -g 1000 && \
    useradd -r -g amcis -u 1000 -s /sbin/nologin -d /opt/amcis amcis

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    AMCIS_HOME=/opt/amcis \
    AMCIS_CONFIG=/etc/amcis \
    PATH="/opt/venv/bin:$PATH" \
    # Security hardening
    PYTHONHASHSEED=random

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 \
    libssl3 \
    iptables \
    iproute2 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=amcis:amcis AMCIS_Q_SEC_CORE /opt/amcis/

# Create required directories
RUN mkdir -p /var/lib/amcis/{keys,logs,certs,forensics,provenance,integrity} \
    /etc/amcis \
    /var/log/amcis && \
    chown -R amcis:amcis /var/lib/amcis /var/log/amcis /opt/amcis

# Set working directory
WORKDIR /opt/amcis

# Security: Drop unnecessary capabilities
# Note: Actual cap-drop is done at runtime

# Security: Read-only root filesystem (commented for compatibility)
# VOLUME ["/tmp", "/var/log/amcis", "/var/lib/amcis"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from cli.amcis_main import cli; print('OK')" || exit 1

# Switch to non-root user
USER amcis

# Entry point
ENTRYPOINT ["python", "-m", "cli.amcis_main"]
CMD ["--help"]
