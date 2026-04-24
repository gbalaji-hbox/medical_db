# ── Stage 1: compile dependencies ────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt api_requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install \
        -r requirements.txt \
        -r api_requirements.txt

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.11-slim AS runner

# Non-root application user
RUN groupadd --gid 1001 appgroup \
    && useradd  --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Copy installed packages from builder (no gcc in runtime image)
COPY --from=builder /install /usr/local

# Copy source (raw data files are gitignored — not present at build time)
COPY src/     ./src/
COPY scripts/ ./scripts/

# Create runtime directories and hand ownership to appuser
RUN mkdir -p \
        /data \
        src/MCA/output src/MCA/cleaned \
        src/HCT/output src/HCT/cleaned \
        src/SSC/output src/SSC/cleaned \
        src/CAM/output src/CAM/cleaned \
        src/CIM/output src/CIM/cleaned \
        src/XHI/output src/XHI/cleaned \
    && chown -R appuser:appgroup /app /data

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MEDICAL_DB_ROOT=/app \
    DB_PATH=/data/api.db \
    ENCRYPTION_KEY_FILE=/data/encryption.key

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# --workers 1: in-memory job store is a singleton; multiple workers lose job state
CMD ["python", "-m", "uvicorn", "src.api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
