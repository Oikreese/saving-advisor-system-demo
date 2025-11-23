FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy requirements and install dependencies using uv
COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY frontend/ ./frontend/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose gRPC port
EXPOSE 50051

# Set PYTHONPATH for gRPC generated code
ENV PYTHONPATH=/app:/app/app/grpc_services/generated

# Health check (gRPC health check would require grpc_health_probe)
# For now, we'll skip HTTP health check since this is a gRPC server
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#   CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); grpc.channel_ready_future(channel).result(timeout=5)" || exit 1

# Run the gRPC server
CMD ["python", "app/main.py"]