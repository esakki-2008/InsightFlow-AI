# InsightFlow AI

<p align="center">
  <strong>Turn tabular data into actionable insights.</strong><br />
  An AI-assisted workspace for data exploration, cleaning, visualization, statistical analysis, and machine learning.
</p>

<p align="center">
  <a href="https://github.com/esakki-2008/InsightFlow-AI"><img src="https://img.shields.io/badge/Project-InsightFlow%20AI-6C63FF" alt="InsightFlow AI" /></a>
  <a href="https://github.com/esakki-2008/InsightFlow-AI/actions/workflows/ci.yml"><img src="https://github.com/esakki-2008/InsightFlow-AI/actions/workflows/ci.yml/badge.svg" alt="CI status" /></a>
  <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white" alt="Python 3.12+" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/TypeScript-6-3178C6?logo=typescript&logoColor=white" alt="TypeScript 6" />
  <img src="https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License" /></a>
</p>

---

## Overview

**InsightFlow AI** is a full-stack data analysis platform that brings essential data-science workflows into one workspace. Upload a CSV or Excel dataset, understand its structure, prepare and clean the data, explore patterns, build visualizations, train machine-learning models, ask questions about computed results, and export reports.

The platform uses a **React + TypeScript** frontend and a **Python FastAPI** backend. Optional, user-configured AI provider integrations add natural-language question planning and explanations to the core analysis workflows.

## Live application

| Component | URL |
|---|---|
| Web application | [insightflow-ai-zeta.vercel.app](https://insightflow-ai-zeta.vercel.app/) |
| Backend API | [insightflow-ai-backend-2us8.onrender.com](https://insightflow-ai-backend-2us8.onrender.com) |
| Interactive API documentation | [Swagger UI](https://insightflow-ai-backend-2us8.onrender.com/docs) |

> **Deployment note:** The backend currently uses a free Render instance, which may spin down after inactivity. The first request after an idle period can take longer to respond. Review the deployment and storage considerations in [Security and deployment considerations](#security-and-deployment-considerations).

## Features

| Area | Capabilities |
|---|---|
| **Dataset explorer** | Upload CSV and Excel files, inspect columns and data types, and review dataset summaries. |
| **Data preparation** | Preview cleaning operations, inspect missing values and duplicates, apply transformations, and export cleaned data. |
| **Exploratory data analysis** | Explore descriptive statistics, distributions, relationships, filters, and dataset insights. |
| **Visualization** | Build charts and organize them in a shared chart workspace. |
| **Statistical analysis** | Run supported statistical analyses to investigate patterns and relationships. |
| **Machine learning** | Prepare classification datasets, train supported models, and inspect evaluation metrics and diagnostics. |
| **Batch prediction** | Generate predictions for multiple records and export prediction results. |
| **Prediction explainability** | Explore feature sensitivity to understand how changes to an input affect a prediction. This is sensitivity analysis, not proof of causation. |
| **AI data assistant** | Ask questions about datasets, explore suggested questions, and generate explanations grounded in computed analysis results. |
| **Reports and exports** | Export supported analytics workbooks, data-quality reports, executive reports, PDF files, and CSV results. |
| **Dataset registry and history** | Organize dataset metadata, analysis history, and saved machine-learning model records. |
| **Account security** | Email/password authentication, account-scoped resources, encrypted provider credentials, and rate-limited authentication endpoints. |

### Supported machine-learning algorithms

The ML workspace includes support for classification algorithms such as:

- Random Forest
- Logistic Regression
- Decision Tree

Available evaluation information can include classification metrics, confusion matrices, and feature-importance details, depending on the selected model.

## Architecture

```text
┌──────────────────────────────────────┐
│          React + TypeScript          │
│       Vite · Tailwind CSS · UI       │
└──────────────────┬───────────────────┘
                   │ HTTP / REST
┌──────────────────▼───────────────────┐
│              FastAPI                 │
│       Routes · Validation · Services │
└──────────┬─────────────────┬─────────┘
           │                 │
┌──────────▼─────────┐  ┌────▼──────────────┐
│ Data & ML          │  │ Persistence       │
│ Pandas · NumPy     │  │ SQLAlchemy        │
│ scikit-learn       │  │ SQLite / Postgres │
│ Joblib             │  │ Alembic           │
└────────────────────┘  └───────────────────┘
           │
┌──────────▼────────────────────────────┐
│ Optional external AI provider APIs   │
│ for question planning and explanation│
└──────────────────────────────────────┘
```

## Technology stack

| Layer | Technologies |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Lucide |
| Backend | Python 3.12+, FastAPI, Pydantic, Uvicorn |
| Data processing | Pandas, NumPy, OpenPyXL |
| Machine learning | scikit-learn, Joblib |
| Database and ORM | SQLAlchemy, SQLite (default), PostgreSQL (configurable) |
| Migrations | Alembic |
| Testing | pytest, HTTPX |
| Code quality | ESLint, TypeScript compiler |
| CI | GitHub Actions |

## Getting started

### Prerequisites

- Git
- Python 3.12 or newer
- Node.js 22 or newer
- npm

### 1. Clone the repository

```bash
git clone https://github.com/esakki-2008/InsightFlow-AI.git
cd InsightFlow-AI
```

### 2. Set up the backend

Create a virtual environment, install dependencies, and configure a private JWT secret.

**Windows PowerShell**

```powershell
$env:INSIGHTFLOW_JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(48))"
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
$env:PYTHONPATH = "$PWD\backend"
python -m uvicorn app.main:app --reload --app-dir backend
```

**macOS / Linux**

```bash
export INSIGHTFLOW_JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
export PYTHONPATH="$PWD/backend"
python -m uvicorn app.main:app --reload --app-dir backend
```

The backend starts at `http://127.0.0.1:8000`.

| Resource | Local URL |
|---|---|
| API base | http://127.0.0.1:8000 |
| Swagger UI | http://127.0.0.1:8000/docs |
| Health check | http://127.0.0.1:8000/api/v1/health |

Database migrations are applied when the application starts. SQLite is used by default. To use PostgreSQL, set `DATABASE_URL` before starting the backend.

### 3. Set up the frontend

Open a second terminal:

```bash
cd frontend
npm ci
```

Create `frontend/.env` using `frontend/.env.example` as a reference:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Start the development server:

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Configuration

Configure environment variables in your local environment or hosting provider's secret manager. Do not commit real credentials.

| Variable | Component | Purpose |
|---|---|---|
| `DATABASE_URL` | Backend | SQLAlchemy database connection. SQLite is used when no external database is configured. |
| `INSIGHTFLOW_JWT_SECRET` | Backend | Private signing secret for access tokens; use a strong, stable value of at least 32 characters. |
| `BACKEND_CORS_ORIGINS` | Backend | Comma-separated list of exact allowed frontend origins. Remote origins should use HTTPS. |
| `REDIS_URL` | Backend | Shared Redis connection used for authentication rate limiting; required in production mode. |
| `INSIGHTFLOW_ENV` | Backend | Set to `production` for production deployment. |
| `VITE_API_URL` | Frontend | Backend API base URL used by the Vite application. |

For deployment, set `VITE_API_URL` to the backend HTTPS origin and configure `BACKEND_CORS_ORIGINS` with the exact frontend origin(s). Keep provider keys, encryption keys, database credentials, and signing secrets in the hosting provider's environment/secrets configuration. Never expose them in frontend code.

## Development and quality checks

Run the following checks before submitting changes.

### Backend tests

From the repository root, with the backend virtual environment activated:

```powershell
$env:PYTHONPATH = "$PWD\backend"
pytest backend\tests -v --ignore=backend\tests\test_live_provider_smoke.py
```

### Frontend lint and production build

```bash
cd frontend
npm run lint
npm run build
```

### Dependency audit

```bash
npm audit
```

The GitHub Actions workflow runs backend tests and the frontend production build for pushes and pull requests targeting `main`.

## Data handling and AI provider integrations

InsightFlow AI processes uploaded dataset content to perform the requested analysis. The dataset registry and analysis-history features store metadata and analysis summaries rather than uploaded raw dataset rows.

### Optional Advanced AI workflow

The Advanced AI question workflow uses the provider selected in the authenticated user's Settings workspace. Supported integrations include OpenAI-compatible chat completions, Google's native Gemini Interactions API (stateless requests with `store=false`), and Anthropic's native Messages API.

At a high level:

1. Dataset column names, inferred data types, and the user's question are sent to the selected provider for query planning.
2. The user's question and computed analysis results (such as aggregates, counts, or correlations) are sent to generate an explanation.
3. Dataset rows are processed locally by the application and are not sent as part of this workflow.

Use this feature only when you have reviewed the selected provider's terms and are comfortable sharing the information described above. Avoid using external AI integrations with confidential, regulated, or personal data unless you have appropriate authorization and safeguards.

Provider API keys are encrypted at rest on the backend, scoped to the account that saved them, and represented in the frontend only by masked metadata. Optional provider-specific HTTP headers can be configured as a JSON object in Settings; they are encrypted at rest and are not returned by the API. The feature is optional: standard local analysis workflows can be used without an external AI provider.

### OpenCode Console compatibility

OpenCode Console can be configured as an OpenAI-compatible provider:

- Pay-as-you-go endpoint: `https://opencode.ai/inference/openai/v1/chat/completions`
- OpenCode Go endpoint: `https://opencode.ai/inference/go/openai/v1/chat/completions`

Use an API key and model ID available to external clients in OpenCode. For OpenCode Go, configure an `x-opencode-session` custom header with a stable session ID. OpenCode's free-tier chat models may be limited to use within OpenCode; check the provider's current terms and model availability.

### Optional live provider tests

The standard backend test suite uses mocked provider responses and does not require real API keys. An opt-in smoke-test module is available:

```powershell
$env:PYTHONPATH = "$PWD\backend"
$env:INSIGHTFLOW_LIVE_PROVIDER_TESTS = "1"
# Configure only the provider variables you intend to test:
# INSIGHTFLOW_LIVE_OPENAI_API_KEY, INSIGHTFLOW_LIVE_OPENAI_BASE_URL, INSIGHTFLOW_LIVE_OPENAI_MODEL
# INSIGHTFLOW_LIVE_GEMINI_API_KEY, INSIGHTFLOW_LIVE_GEMINI_MODEL
# INSIGHTFLOW_LIVE_ANTHROPIC_API_KEY, INSIGHTFLOW_LIVE_ANTHROPIC_MODEL
python -m pytest backend\tests\test_live_provider_smoke.py -q
```

These tests are skipped by default and make real requests that may consume provider credits or quota. Keep all credentials in your local environment; never commit them or share terminal output containing secrets.

## Security and deployment considerations

The application includes:

- Email registration and login with Argon2 password hashing.
- Short-lived JWT bearer tokens and authenticated account-profile access.
- Account-scoped private dataset, history, registry, machine-learning, and AI-provider operations.
- Upload validation for supported formats, file size, and dataset dimensions.
- Baseline HTTP security headers and configurable CORS.
- Database schema migrations.
- Rate-limited login and registration; production mode requires shared Redis rate limiting.
- Encrypted-at-rest saved provider credentials and custom headers.

The root and health endpoints are intentionally public. Legacy records with nullable owner references may remain unassigned until an explicit ownership migration is selected. These application safeguards are not a substitute for an independent security assessment.

**Before using the service with sensitive data or exposing it to public production traffic**, configure and verify HTTPS, strong stable secrets, exact CORS origins, managed PostgreSQL, reachable Redis, database backups, monitoring and alerting, hosting-level request/body limits, and recovery procedures.

**Model artifact persistence:** ML model artifacts are saved locally by the backend and excluded from Git. On hosts with ephemeral filesystems, artifacts may not survive restarts or redeployments. Configure persistent storage or external object storage before relying on saved models in production.

A successful deployment does not by itself establish that every production workflow, security boundary, backup, or recovery procedure has been independently verified.

## Repository structure

```text
InsightFlow-AI/
├── .github/
│   └── workflows/
│       └── ci.yml
├── backend/
│   ├── app/                 # FastAPI application, routes, and services
│   ├── alembic/             # Database migrations
│   ├── tests/               # Backend automated tests
│   └── requirements.txt
├── frontend/
│   ├── src/                 # React + TypeScript application
│   ├── .env.example
│   ├── package.json
│   └── package-lock.json
├── LICENSE
└── README.md
```

## Project status

InsightFlow AI is an actively developed project with core dataset exploration, cleaning, visualization, statistical analysis, machine-learning, AI-assisted insight, registry, history, and reporting workflows.

Features and deployment configuration may evolve. Please review the documentation and security considerations before using the application with sensitive or business-critical data.

## Contributing

Contributions, bug reports, and feature suggestions are welcome.

1. Fork the repository.
2. Create a focused feature branch.
3. Implement your change and add or update tests where appropriate.
4. Run the backend tests, frontend lint, and production build.
5. Open a pull request describing the change and its motivation.

Please avoid including credentials, private datasets, generated model artifacts, or other sensitive information in issues and pull requests.

## License

This project is licensed under the [MIT License](./LICENSE).

---

<p align="center">
  Built to make data analysis more accessible, understandable, and actionable.
</p>

## Application Screenshots

### Screenshot 2026-11-17 174649

![Screenshot 2026-11-17 174649](docs/screenshots/Screenshot%202026-11-17%20174649.png)

### Screenshot 2026-11-17 174636

![Screenshot 2026-11-17 174636](docs/screenshots/Screenshot%202026-11-17%20174636.png)

### Screenshot 2026-11-17 174727

![Screenshot 2026-11-17 174727](docs/screenshots/Screenshot%202026-11-17%20174727.png)

### Screenshot 2026-11-17 174744

![Screenshot 2026-11-17 174744](docs/screenshots/Screenshot%202026-11-17%20174744.png)

### Screenshot 2026-11-17 174807

![Screenshot 2026-11-17 174807](docs/screenshots/Screenshot%202026-11-17%20174807.png)

### Screenshot 2026-11-17 174831

![Screenshot 2026-11-17 174831](docs/screenshots/Screenshot%202026-11-17%20174831.png)

### Screenshot 2026-11-17 174849

![Screenshot 2026-11-17 174849](docs/screenshots/Screenshot%202026-11-17%20174849.png)

### Screenshot 2026-11-17 174925

![Screenshot 2026-11-17 174925](docs/screenshots/Screenshot%202026-11-17%20174925.png)

### Screenshot 2026-11-17 174946

![Screenshot 2026-11-17 174946](docs/screenshots/Screenshot%202026-11-17%20174946.png)

### Screenshot 2026-11-17 175012

![Screenshot 2026-11-17 175012](docs/screenshots/Screenshot%202026-11-17%20175012.png)

### Screenshot 2026-11-17 175038

![Screenshot 2026-11-17 175038](docs/screenshots/Screenshot%202026-11-17%20175038.png)

### Screenshot 2026-11-17 175057

![Screenshot 2026-11-17 175057](docs/screenshots/Screenshot%202026-11-17%20175057.png)

### Screenshot 2026-11-17 175119

![Screenshot 2026-11-17 175119](docs/screenshots/Screenshot%202026-11-17%20175119.png)

### Screenshot 2026-11-17 175137

![Screenshot 2026-11-17 175137](docs/screenshots/Screenshot%202026-11-17%20175137.png)
