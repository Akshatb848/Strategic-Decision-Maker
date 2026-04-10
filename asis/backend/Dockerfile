# syntax=docker/dockerfile:1
# ── Stage 1: Build dependencies ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools (needed for asyncpg, psycopg2 compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Single pip install — all app deps ─────────────────────────────────────────
# BuildKit cache mount: the pip wheel cache persists between Docker builds on
# the same host. First build downloads packages; subsequent builds (even when
# requirements.txt changes) use cached wheels → seconds instead of hours.
# Never use --no-cache-dir with this approach — the cache IS the speedup.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --prefer-binary -r requirements.txt

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
