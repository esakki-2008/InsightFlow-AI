# InsightFlow AI

**InsightFlow AI** is a full-stack data analysis workspace for dataset inspection, cleaning, exploratory analytics, statistical analysis, machine learning, AI-assisted Q&A, and report generation.

## Features

- **Dataset management:** CSV/XLSX upload, schema inspection, dataset registry, and metadata-only analysis history.
- **Data preparation:** cleaning previews, duplicate and missing-value analysis, and cleaned dataset export.
- **Analytics:** exploratory data analysis, interactive chart building, shared chart workspaces, data quality reports, and statistical analysis.
- **Machine learning:** classification preparation, model training and evaluation, saved model registry, batch prediction, and prediction explainability.
- **AI assistance:** deterministic dataset Q&A, context-aware question suggestions, dataset insights, executive reports, and optional NVIDIA-powered advanced Q&A.
- **Exports:** analytics workbooks and printable PDF reports.
- **Engineering:** FastAPI backend, SQLAlchemy database layer, Alembic migrations, security headers, configurable CORS, and automated tests.

> **Data handling:** Dataset files and raw rows are processed for analysis and are not persisted by the dataset registry/history features. Those features store metadata and analysis summaries. ML model artifacts are saved locally by the backend and are excluded from Git.

## Technology

| Layer | Stack |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, Lucide |
| Backend | Python, FastAPI, Pydantic |
| Data | Pandas, NumPy, OpenPyXL |
| Machine learning | scikit-learn, Joblib |
| Database | SQLAlchemy, SQLite by default; PostgreSQL via `DATABASE_URL` |
| Migrations | Alembic |
| Tests | pytest, HTTPX |
| CI | GitHub Actions |

## Requirements

- Python 3.12+
- Node.js 22+
- npm
- Git

## Run locally

### 1. Clone the repository

```bash
git clone https://github.com/esakki-2008/InsightFlow-AI.git
cd InsightFlow-AI
```

### 2. Set up the backend

**Windows PowerShell:**

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
$env:PYTHONPATH = "$PWD\backend"
python -m uvicorn app.main:app --reload --app-dir backend
```

The backend runs at:

- API: http://127.0.0.1:8000
- Swagger documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/v1/health

Database migrations are applied automatically when the API starts. SQLite is used by default. For PostgreSQL, set `DATABASE_URL` in the backend environment before starting the API.

### 3. Set up the frontend

In a second terminal:

```powershell
cd frontend
npm ci
```

Create `frontend/.env` using `frontend/.env.example` as a reference. Set the API base URL:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Start the development server:

```powershell
npm run dev
```

The frontend runs at http://localhost:5173.

## Tests and production build

Run backend tests from the repository root with the backend virtual environment active:

```powershell
$env:PYTHONPATH = "$PWD\backend"
pytest backend\tests -v
```

Build the frontend:

```powershell
cd frontend
npm ci
npm run build
```

GitHub Actions runs the backend test suite and frontend production build on pushes and pull requests targeting `main`.

## Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Optional SQLAlchemy database URL; SQLite is the default |
| `BACKEND_CORS_ORIGINS` | Comma-separated trusted frontend origins; local Vite origins are the development default |
| `VITE_API_URL` | Frontend API base URL; defaults to `http://127.0.0.1:8000` |

For a deployed frontend, set `VITE_API_URL` to the backend's HTTPS origin at build time. Set `BACKEND_CORS_ORIGINS` to the exact deployed frontend origin(s). Configure secrets through the hosting provider's secret/environment settings, never in source control.

The optional NVIDIA integration accepts a provider API key at request time. Do not commit keys or place them in frontend environment variables. Avoid sending confidential or personal datasets to external AI providers.

## Security notes

- Uploads are validated for supported file types, size, and dataset dimensions.
- The backend applies baseline browser security headers and configurable CORS.
- Analysis history and the dataset registry store metadata and summaries, not uploaded raw dataset contents.
- Local ML artifacts are ignored by Git; back them up securely if they are needed after redeployment.
- Review provider data-retention terms before using external AI services.
- Do not expose the API publicly without HTTPS, production CORS configuration, appropriate authentication/authorization, rate limiting, and operational monitoring.

## Repository layout

```text
InsightFlow-AI/
├── .github/workflows/   # GitHub Actions CI
├── backend/
│   ├── app/             # FastAPI application and services
│   ├── alembic/         # Database migrations
│   └── tests/           # Backend tests
└── frontend/
    └── src/             # React + TypeScript application
```

## License

No license has been added yet. Unless a license is added, reuse and redistribution are not explicitly granted.
