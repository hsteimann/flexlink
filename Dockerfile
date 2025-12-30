# Multi-stage build for FlexLink Middleware
# Stage 1: Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy project files for dependency installation
COPY pyproject.toml uv.lock* README.md ./
COPY src/ ./src/

# Install production dependencies only
RUN uv pip install --system -e .

# Stage 2: Production runtime
FROM python:3.12-slim

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash flexlink && \
    chown -R flexlink:flexlink /app

# Install uv for runtime
RUN pip install --no-cache-dir uv

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=flexlink:flexlink src/ ./src/
COPY --chown=flexlink:flexlink config/ ./config/
COPY --chown=flexlink:flexlink pyproject.toml ./

# Create data directories with proper permissions
RUN mkdir -p data/uploads data/downloads data/samples && \
    chown -R flexlink:flexlink data/

# Switch to non-root user
USER flexlink

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Run application with uvicorn
CMD ["uvicorn", "flexlink.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
