# InsightFlow AI

**InsightFlow AI** is an intelligent data analysis platform being developed to help users explore datasets, clean data, generate visual insights, and apply machine learning through a unified interface.

> **Development status:** Early development. The backend foundation is in place; frontend and analytical features are planned.

## Vision

Make data analytics more accessible by combining reliable, reproducible data processing with machine learning and optional AI-powered explanations.

## Planned Features

- Upload CSV and Excel datasets.
- Inspect dataset structure, columns, missing values, and data types.
- Clean and preprocess data.
- Perform exploratory data analysis (EDA).
- Generate visualizations and statistical summaries.
- Train and evaluate machine learning models.
- Provide AI-assisted explanations of analytical results.
- Optionally connect to a locally hosted language model through Ollama.
- Keep numerical calculations deterministic and distinguish computed results from AI-generated explanations.

Features above are planned and should not be considered implemented until they are documented as complete.

## Technology Stack

| Area | Technologies |
|---|---|
| Backend API | Python, FastAPI, Pydantic |
| Data processing | Pandas, NumPy, OpenPyXL |
| Machine learning | Scikit-learn, XGBoost (planned) |
| Frontend | React, TypeScript, Vite, Tailwind CSS (planned) |
| Database | PostgreSQL, SQLAlchemy (planned) |
| Optional AI / retrieval | Ollama, FAISS, Sentence Transformers (planned) |
| Testing | Pytest, Vitest (planned) |

The core platform is intended to work without requiring a paid LLM API. Any external or local generative-AI integration will be optional.

## Repository Structure

```text
InsightFlow-AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── docs/
├── frontend/
└── .gitignore
```

## Getting Started

### Requirements

- Python 3.12 or later
- Git

### 1. Clone the repository

```bash
git clone https://github.com/esakki-2008/InsightFlow-AI.git
cd InsightFlow-AI
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python -m venv backend/.venv
source backend/.venv/bin/activate
```

### 3. Install backend dependencies

```bash
python -m pip install -r backend/requirements.txt
```

### 4. Start the backend API

Run this command from the repository root:

```bash
python -m uvicorn app.main:app --reload --app-dir backend
```

The API will be available at:

- API root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/api/v1/health
- Interactive API docs: http://127.0.0.1:8000/docs

## Development Roadmap

- [x] Initialize repository and project structure
- [x] Set up Python virtual environment and backend dependencies
- [x] Create initial FastAPI application
- [x] Add root and health-check endpoints
- [ ] Initialize React + TypeScript frontend
- [ ] Implement dataset upload and validation
- [ ] Build data profiling and cleaning services
- [ ] Add exploratory data analysis and visualizations
- [ ] Add machine learning workflows and evaluation
- [ ] Add optional AI-assisted analysis
- [ ] Add automated tests, documentation, and deployment configuration

## Security and Data Handling

- Never commit API keys, passwords, access tokens, or other secrets.
- Keep local environment files and private datasets out of version control.
- Validate uploaded files and enforce safe file-size and type limits.
- Do not treat AI-generated explanations as a substitute for verified calculations.
- Do not use the project for security-critical or other high-stakes decisions without appropriate validation.

## Contributing

Contributions, suggestions, and bug reports are welcome. Please open an issue to discuss substantial changes before submitting a pull request.

## License

No open-source license has been selected yet. Until a license is added, the repository's contents are not explicitly licensed for reuse, modification, or distribution.
