# Kronos Euphoria Mirror — CUDA GPU Production Build
# FastAPI backend + static dashboard on port 8000
# Uses PyTorch CUDA image for GPU inference

# ---- Stage 1: Install Python dependencies ----
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime AS deps

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Production image ----
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /opt/conda/lib/python3.10/site-packages /opt/conda/lib/python3.10/site-packages

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Copy backend code
COPY backend/ ./backend/

# Copy dashboard static files
COPY dashboard/ ./dashboard/

# Copy data directory (sample OHLCV)
COPY data/ ./data/

# Set ownership to non-root user
RUN chown -R appuser:appuser /app

# Environment defaults
ENV GPU_ENABLED=true
ENV USE_MOCK_DATA=false
ENV CORS_ORIGINS=["*"]
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

USER appuser

# Run uvicorn serving API + mount static dashboard
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]