# =============================================================================
# Khan Parcel — Multi-stage Dockerfile
# =============================================================================
# Stage 1: Build dependencies
# Stage 2: Production runtime
# =============================================================================

# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps for building (GDAL, GEOS, PROJ for PostGIS, weasyprint deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libffi-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install Python deps into a virtualenv so we can copy it cleanly
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install ".[dev]"

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.dev \
    PATH="/opt/venv/bin:$PATH"

# Runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    gdal-bin \
    libgdal34 \
    libgeos3.12.1 \
    libproj25 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r khanparcel && useradd -r -g khanparcel -d /app -s /sbin/nologin khanparcel

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy application code
COPY . .

# Collect static files (if any)
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Create media directory
RUN mkdir -p /app/media /app/staticfiles /app/logs \
    && chown -R khanparcel:khanparcel /app

USER khanparcel

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/healthz/ || exit 1

EXPOSE 8000

# Default command: gunicorn with uvicorn workers (ASGI)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
