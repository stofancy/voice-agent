# OpenClaw Voice - Docker image

FROM python:3.12-slim

# Install uv for fast package management
RUN pip install uv

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Create app directory
WORKDIR /app

# Copy pyproject.toml and install dependencies
COPY pyproject.toml ./

# Install Python dependencies using uv (modern, fast)
RUN uv pip install --system -e .

# Copy application code
COPY src/ ./src/

# Create directories and set ownership
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/')" || exit 1

# Run server (all config via environment variables)
CMD ["python", "-m", "uvicorn", "src.server.main:app", "--host", "0.0.0.0", "--port", "8765"]
