# OpenClaw Voice - Docker image

FROM python:3.11-slim

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt ./

# Install Python dependencies (use Aliyun mirror for reliability)
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# Copy application code
COPY src/ ./src/

# Create directories
RUN mkdir -p /app/data /app/logs

# Expose port
EXPOSE 8765

# Run server (all config via environment variables)
CMD ["python", "-m", "uvicorn", "src.server.main:app", "--host", "0.0.0.0", "--port", "8765"]
