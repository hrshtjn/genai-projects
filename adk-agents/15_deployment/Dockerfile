# -----------------------------------------------------------------
# Dockerfile — ADK agent for GKE deployment
# -----------------------------------------------------------------
# Build context: the 15_deployment/ directory (where main.py lives)
#
# Security practices applied:
# - Non-root user (myuser) runs the process
# - No dev tools or caches in the image (--no-cache-dir)
# - PORT injected at runtime via env var, not hardcoded
# -----------------------------------------------------------------

FROM python:3.13-slim

WORKDIR /app

# Install dependencies first (separate layer — cached on rebuilds
# unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user and hand over ownership of /app
RUN adduser --disabled-password --gecos "" myuser && \
    chown -R myuser:myuser /app

# Copy the rest of the source code
COPY . .

# Switch to non-root user
USER myuser

# Ensure local pip binaries are on PATH for this user
ENV PATH="/home/myuser/.local/bin:$PATH"

# PORT is set by GKE at runtime. Default 8080 matches the K8s Service.
ENV PORT=8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
