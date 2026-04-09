# ── Stage 1: Build dependencies ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools (needed for asyncpg, psycopg2 compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Single pip install — all app deps ─────────────────────────────────────────
# Split into two COPY+RUN pairs so Docker layer cache skips pip install
# entirely when requirements.txt hasn't changed (fast iterative builds).
# --prefer-binary: use pre-built wheels, never compile from source
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

# Copy application code (separate layer — changes often, doesn't bust pip cache)
COPY . /app/asis/backend/

ENV PATH="/home/asis/.local/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER asis

EXPOSE 8000

CMD ["uvicorn", "asis.backend.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
