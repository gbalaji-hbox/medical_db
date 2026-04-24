# HBox Medical ETL

FastAPI backend + React dashboard for running and monitoring six medical-data ETL pipelines.

---

## Production — Docker (recommended)

### Architecture

```
Browser → nginx :80 ─┬─ /           → React SPA (static files)
                     └─ /api/*      → FastAPI :8000 (internal network, never public)
```

Both services share a Docker bridge network. The backend port is never exposed to the host.

### 1. Create your env file

```bash
cp .env.example .env
```

Edit `.env` and set a strong `JWT_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Build and start

```bash
docker compose up --build -d
```

- Frontend (nginx) → **http://localhost**
- Backend API docs → **http://localhost/api/docs** (proxied through nginx)

### 3. Stop

```bash
docker compose down
```

Data (SQLite DB + encryption key) persists in the `api_data` Docker volume across restarts.

---

## Local Development (no Docker)

### Backend

```bash
# Activate virtual environment
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / Mac

# Install dependencies (first time)
pip install -r requirements.txt -r api_requirements.txt

# Configure — copy example and set JWT_SECRET_KEY
cp .env.example .creds/.env
# edit .creds/.env

# Run with auto-reload
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI → **http://localhost:8000/docs**

### Frontend

```bash
cd frontend
npm install          # first time only
npm run dev
```

Dashboard → **http://localhost:8080**

Vite automatically proxies all `/api/*` requests to `http://localhost:8000` — no CORS issues, same behaviour as production nginx.

---

## Environment Variables

Place in `.env` (Docker) or `.creds/.env` (local dev). The backend loads whichever exists.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | **Yes** | — | Signs JWT tokens. Generate with `secrets.token_hex(32)`. |
| `DB_PATH` | No | `/data/api.db` (Docker) | SQLite database file path |
| `ENCRYPTION_KEY_FILE` | No | Next to `DB_PATH` | Fernet key — auto-generated on first boot |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins |
| `MEDICAL_DB_ROOT` | No | `/app` (Docker) | Root path used by SSC and XHI pipeline scripts |

---

## Running a Pipeline Manually (local only)

Always run from the project root with the venv activated:

```bash
python src/MCA/scripts/main.py
python src/HCT/scripts/main.py
python src/SSC/scripts/main.py
python src/CAM/scripts/main.py
python src/CIM/scripts/main.py
python src/XHI/scripts/main.py
```

Place input files in the module directory (e.g. `src/MCA/`) before running.

---

## Module → EHR Mapping

| Module | EHR System | Clinic |
|--------|-----------|--------|
| MCA | CGM APRIMA | Main cardiology practice |
| HCT | NextGen | Heart Center of N TX |
| SSC | Athena Health | — |
| CAM | Epic (Henry Ford) | Henry Ford Health |
| CIM | Epic (Henry Ford) | Henry Ford Health |
| XHI | DrChrono | — |

---

## API Authentication

**JWT (browser / frontend)**
1. `POST /api/auth/login` → copy `access_token`
2. Send as `Authorization: Bearer <token>` — expires in 30 min
3. Frontend silently refreshes using the 7-day refresh token

**API key (automation)**
1. Admin: `POST /api/auth/keys` → copy the key (shown once only)
2. Send as `X-Api-Key: <key>` header on every request

---

## Project Structure

```
.
├── Dockerfile                 Backend — multi-stage, non-root user
├── docker-compose.yml         Full stack: api + nginx frontend on internal network
├── .env.example               Copy to .env, set JWT_SECRET_KEY
├── requirements.txt           Pipeline Python dependencies
├── api_requirements.txt       FastAPI + server dependencies
├── src/
│   ├── api/                   FastAPI application
│   │   ├── main.py            Entry point, middleware, routes
│   │   ├── auth.py            JWT + API key auth
│   │   ├── config.py          All env vars and path resolution
│   │   ├── db.py              SQLite helpers
│   │   ├── models.py          Pydantic models
│   │   └── routers/           Per-module endpoints (mca, hct, ssc, cam, cim, xhi)
│   ├── MCA/  HCT/  SSC/
│   ├── CAM/  CIM/  XHI/       Pipeline scripts + EHR templates
│   └── samples/               Pre-built 5-row sample input files
└── frontend/
    ├── Dockerfile             Multi-stage: Node build → nginx runner
    ├── nginx.conf             Proxy, security headers, SPA fallback, gzip
    ├── vite.config.ts         Dev server with /api proxy
    └── src/                   React 18 + TypeScript + shadcn/ui
```
