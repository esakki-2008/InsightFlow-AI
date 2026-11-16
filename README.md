# InsightFlow AI

<p align="center">
  <strong>An AI-powered workspace for exploring, preparing, analyzing, and modeling tabular data.</strong>
  <br />
  Turn CSV and Excel datasets into clear insights, visualizations, machine-learning predictions, and shareable reports.
</p>

<p align="center">
  <a href="https://github.com/esakki-2008/InsightFlow-AI/actions/workflows/ci.yml"><img src="https://github.com/esakki-2008/InsightFlow-AI/actions/workflows/ci.yml/badge.svg" alt="InsightFlow AI CI" /></a>
  <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white" alt="Python 3.12+" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/TypeScript-6-3178C6?logo=typescript&logoColor=white" alt="TypeScript 6" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/License-Not%20specified-lightgrey" alt="License not specified" />
</p>

---

## Overview

**InsightFlow AI** is a full-stack data analysis platform designed to bring common data-science workflows into one workspace. Import a tabular dataset, inspect its structure, prepare and clean the data, explore patterns, train machine-learning models, ask questions about the results, and export reports.

The application combines a **React + TypeScript** frontend with a **Python FastAPI** backend. It is built for hands-on dataset analysis, with optional NVIDIA-powered natural-language explanations as an additional AI capability.

## Key capabilities

| Workspace | What it does |
|---|---|
| **Dataset Explorer** | Upload CSV and Excel files, inspect columns and data types, and review dataset summaries. |
| **Data Cleaning** | Preview cleaning operations, inspect missing values and duplicates, apply transformations, and export cleaned data. |
| **Exploratory Data Analysis** | Review descriptive statistics, distributions, relationships, filters, and dataset insights. |
| **Chart Builder** | Create visualizations and organize them in a shared chart workspace. |
| **Statistical Analysis** | Run supported statistical analyses to investigate patterns and relationships in the data. |
| **Machine Learning** | Prepare classification data, train supported models, and inspect evaluation metrics, confusion matrices, and feature importance. |
| **Batch Prediction** | Run predictions on multiple records, review confidence information where available, and export prediction results. |
| **Prediction Explainability** | Inspect feature sensitivity to understand how changing an input can affect a model prediction. This is sensitivity analysis, not a causal explanation. |
| **AI Data Assistant** | Ask dataset questions, explore suggested questions, and generate data-grounded insights and executive summaries. |
| **Reports & Exports** | Export analytics workbooks, data-quality reports, executive reports, and results in supported PDF/CSV formats. |
| **Registries & History** | Keep dataset metadata, analysis history, and saved ML model records organized. |

### Machine-learning models

The ML workspace includes support for commonly used classification algorithms, including:

- Random Forest
- Logistic Regression
- Decision Tree

Model evaluation surfaces relevant metrics and visual diagnostics, such as confusion matrices and feature-importance information where supported by the selected model.

## Architecture

```text
┌──────────────────────────────────┐
│        React + TypeScript        │
│       Vite · Tailwind CSS        │
└────────────────┬─────────────────┘
                 │ HTTP / REST
┌────────────────▼─────────────────┐
│           FastAPI API            │
│ Routes · Validation · Services   │
└───────┬──────────────────┬───────┘
        │                  │
┌───────▼────────┐  ┌──────▼────────────┐
│ Data & ML      │  │ SQLAlchemy        │
│ Pandas         │  │ SQLite / Postgres │
│ NumPy          │  │ Alembic           │
│ scikit-learn   │  └───────────────────┘
│ Joblib         │
└────────────────┘
        │
┌───────▼───────────────────────────┐
│ Optional NVIDIA-powered advanced │
│ question planning and explanation│
└──────────────────────────────────┘
```

## Technology stack

| Area | Technologies |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Lucide |
| Backend | Python 3.12+, FastAPI, Pydantic, Uvicorn |
| Data processing | Pandas, NumPy, OpenPyXL |
| Machine learning | scikit-learn, Joblib |
| Persistence | SQLAlchemy, SQLite (default), PostgreSQL (configurable) |
| Database migrations | Alembic |
| Testing | pytest, HTTPX |
| Code quality | ESLint, TypeScript compiler |
| Continuous integration | GitHub Actions |

## Getting started

### Prerequisites

Install the following before running the project:

- Git
- Python 3.12 or newer
- Node.js 22 or newer
- npm

### 1. Clone the repository

```bash
git clone https://github.com/esakki-2008/InsightFlow-AI.git
cd InsightFlow-AI
```

### 2. Configure and start the backend

Create a virtual environment and install the Python dependencies.

**Windows PowerShell**

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
$env:PYTHONPATH = "$PWD\backend"
python -m uvicorn app.main:app --reload --app-dir backend
```

**macOS / Linux**

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
export PYTHONPATH="$PWD/backend"
python -m uvicorn app.main:app --reload --app-dir backend
```

The backend is available at:

| Resource | URL |
|---|---|
| API base | http://127.0.0.1:8000 |
| Swagger UI | http://127.0.0.1:8000/docs |
| Health check | http://127.0.0.1:8000/api/v1/health |

Database migrations are applied when the application starts. SQLite is the default database. To use PostgreSQL, configure `DATABASE_URL` before starting the backend.

### 3. Configure and start the frontend

Open a **second terminal**:

```powershell
cd frontend
npm ci
```

Create `frontend/.env` using `frontend/.env.example` as the reference and configure the backend URL:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Start the Vite development server:

```powershell
npm run dev
```

Open the frontend at http://localhost:5173.

## Quality checks

Run these commands before submitting changes.

### Backend tests

From the repository root, with the backend virtual environment activated:

```powershell
$env:PYTHONPATH = "$PWD\backend"
pytest backend\tests -v
```

### Frontend lint and production build

```powershell
cd frontend
npm run lint
npm run build
```

### Dependency security audit

```powershell
npm audit
```

The GitHub Actions workflow runs the backend test suite and frontend production build on pushes and pull requests targeting `main`.

## Configuration

| Variable | Component | Description |
|---|---|---|
| `DATABASE_URL` | Backend | SQLAlchemy database connection string. SQLite is used when no external database is configured. |
| `BACKEND_CORS_ORIGINS` | Backend | Comma-separated list of allowed frontend origins. |
| `VITE_API_URL` | Frontend | Backend API base URL used by the Vite application. |

For deployment, set `VITE_API_URL` to the backend's HTTPS origin and configure `BACKEND_CORS_ORIGINS` with the exact frontend origin(s). Store credentials and API keys in your hosting provider's environment/secrets configuration. **Never commit secrets to the repository or expose provider keys in frontend code.**

## Data handling and privacy

InsightFlow AI processes uploaded dataset content for the requested analysis. The dataset registry and analysis-history features store metadata and analysis summaries rather than the uploaded raw dataset rows. ML model artifacts are saved locally by the backend and are excluded from Git; they may not survive an ephemeral hosting environment or redeployment.

### Optional NVIDIA-powered Advanced AI

The optional Advanced AI question workflow uses an external NVIDIA service for parts of question planning and explanation:

1. Dataset column names and inferred data types, together with the user's question, are sent for query planning.
2. The user's question and the computed analysis result (for example, aggregates, counts, or correlations) are sent to generate the explanation.
3. Dataset rows are processed locally by the application; raw dataset rows are not sent as part of this workflow.

Do not use this feature with confidential, regulated, or personal data unless you have reviewed the provider's terms and are comfortable sharing the information described above. The feature is optional; use the standard local analysis workflows when external processing is not appropriate.

## Security considerations

The project includes:

- File upload validation for supported formats, file size, and dataset dimensions.
- Baseline HTTP security headers.
- Configurable CORS origins.
- Database schema migrations.
- Automated backend tests and frontend build checks.

These controls are not a substitute for a complete production security deployment. Before exposing the application publicly, implement and verify appropriate authentication and authorization, rate limiting, HTTPS, secret management, database backups, logging, monitoring, and production-specific upload/storage controls.

## Repository structure

```text
InsightFlow-AI/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions pipeline
├── backend/
│   ├── app/                    # FastAPI application, routes, and services
│   ├── alembic/                # Database migrations
│   ├── tests/                  # Backend automated tests
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── src/                    # React + TypeScript application
│   ├── .env.example            # Frontend environment template
│   ├── package.json
│   └── package-lock.json
└── README.md
```

## Current project status

InsightFlow AI includes the core dataset analysis, cleaning, visualization, machine-learning, AI-assisted insight, registry, history, and reporting workflows. The backend test suite and frontend production build are integrated into GitHub Actions.

The project is an actively developed release candidate. Review the deployment and security considerations above before using it with sensitive data or exposing it to public traffic.

## Contributing

Contributions, bug reports, and improvement ideas are welcome.

1. Fork the repository.
2. Create a focused feature branch.
3. Make your changes and add or update tests where appropriate.
4. Run the backend tests, frontend lint, and production build.
5. Open a pull request with a clear description of the change.

## License

No license has been added to this repository yet. Until a license is included, the project remains subject to the default copyright rules; do not assume that reuse, modification, or redistribution is permitted.
