# AMCIS Demo Environment Dockerfile
# Production-ready container for prospect demonstrations

FROM python:3.12-slim-bookworm

# Security: Non-root user
RUN groupadd -r amcis -g 1000 && \
    useradd -r -g amcis -u 1000 -s /sbin/nologin amcis

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    AMCIS_DEMO_MODE=1 \
    AMCIS_VERSION=1.0.0-demo

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn[standard]==0.27.0 \
    pydantic==2.5.0 \
    python-multipart==0.0.6 \
    pillow==10.2.0 \
    reportlab==4.0.0

# Copy demo application
WORKDIR /app
COPY src/demo_app.py /app/
COPY config/ /app/config/

# Create directories
RUN mkdir -p /app/logs /app/data && \
    chown -R amcis:amcis /app

# Switch to non-root user
USER amcis

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run
CMD ["python", "-m", "uvicorn", "demo_app:app", "--host", "0.0.0.0", "--port", "8080"]
