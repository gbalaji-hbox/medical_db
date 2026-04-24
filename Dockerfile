FROM python:3.11-slim

WORKDIR /app

# System deps for openpyxl, cryptography, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt api_requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r api_requirements.txt

# Copy source (raw data files are gitignored and won't be present)
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create runtime dirs that the scripts write to
RUN mkdir -p \
    src/MCA/output src/MCA/cleaned \
    src/HCT/output src/HCT/cleaned \
    src/SSC/output src/SSC/cleaned \
    src/CAM/output src/CAM/cleaned \
    src/CIM/output src/CIM/cleaned \
    src/XHI/output src/XHI/cleaned

ENV MEDICAL_DB_ROOT=/app
ENV DB_PATH=/data/api.db
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# --workers 1: in-memory job store is singleton; multiple workers lose job state
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
