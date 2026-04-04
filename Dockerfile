# ══════════════════════════════════════════════════════════════════════════════
# GenomIQ — Autonomous Scientific Discovery Platform
# Multi-stage Docker build for production deployment
# ══════════════════════════════════════════════════════════════════════════════

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies (needed for numpy/scipy wheel compilation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Labels for container metadata
LABEL maintainer="GenomIQ Team"
LABEL description="GenomIQ — Scientific Discovery RL Environment"
LABEL version="1.0.0"

# Create non-root user (Hugging Face convention)
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV HOME=/home/user

# ── Environment variables ────────────────────────────────────────────────────

# Python runtime settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/home/user/app

# GenomIQ defaults (can be overridden at runtime)
ENV HF_TOKEN=""
ENV API_BASE_URL="https://router.huggingface.co/v1"
ENV MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"

# Gradio settings for containerized deployment
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT="7860"
ENV GRADIO_ANALYTICS_ENABLED="false"

# ── Copy application code ───────────────────────────────────────────────────

# Copy config and data files first (less likely to change)
COPY config.yaml openenv.yaml ./
COPY datasets/ ./datasets/

# Copy application source
COPY env/ ./env/
COPY server/ ./server/
COPY utils/ ./utils/
COPY gradio_app.py app_theme.py runner.py inference.py ./
COPY __init__.py ./

# Create results directory with proper permissions
RUN mkdir -p /home/user/app/results /home/user/app/logs && \
    chown -R user:user /home/user/app

EXPOSE 7860

# Switch to non-root user
USER user

# ── Default entrypoint: Launch the Gradio dashboard (serves both UI + API) ──
# Override with: docker run genomiq python -m server.app   (API-only mode)
#            or: docker run genomiq python inference.py     (baseline run)
CMD ["python", "gradio_app.py"]
