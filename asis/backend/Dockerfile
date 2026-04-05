# ── Stage 1: Build dependencies ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 1: Heavy deps (litellm) — cached independently, rarely changes ──────
COPY requirements-heavy.txt .
RUN pip install --user --no-cache-dir --prefer-binary -r requirements-heavy.txt

# ── Layer 2: App deps — changes more often but installs fast ──────────────────
COPY requirements.txt .
RUN pip install --user --no-cache-dir --prefer-binary -r requirements.txt

# ── Stage 2: Production image ─────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Security: non-root user
RUN useradd --create-home --shell /bin/bash asis && \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /home/asis/.local

WORKDIR /app

# Copy application code
COPY . /app/asis/backend/

ENV PATH="/home/asis/.local/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER asis

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health')" 2>/dev/null || exit 1

CMD ["uvicorn", "asis.backend.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
