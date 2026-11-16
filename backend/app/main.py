
from contextlib import asynccontextmanager
from io import BytesIO
import os
from pathlib import Path
from urllib.parse import urlsplit

from alembic import command
from alembic.config import Config

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import router as auth_router, get_current_user
from app.ai_credentials import router as ai_credentials_router
from app.models import AIProviderCredential, User
from app import models  # Register SQLAlchemy models before table creation.
from app.history_schemas import HistoryCreate
from app.models import AnalysisHistory

from app.services.chart_service import generate_chart_data
from app.services.cleaning_service import (
    apply_cleaning,
    generate_cleaning_preview,
)
from app.services.dataset_service import inspect_dataset
from app.services.exploration_service import generate_exploration
from app.services.data_quality_service import generate_data_quality_report
from app.services.statistical_analysis_service import generate_statistical_analysis
from app.services.executive_report_service import generate_executive_report
from app.services.ml_preparation_service import prepare_classification_dataset
from app.services.ml_training_service import train_classification_models
from app.services.ml_model_service import predict_with_saved_model, list_saved_models
from app.services.ml_explainability_service import explain_prediction
from app.services.insights_service import generate_dataset_insights
from app.services.question_service import answer_dataset_question
from app.services.question_suggestion_service import generate_question_suggestions
from app.services.llm_provider_service import test_nvidia_connection
from app.services.credential_crypto_service import decrypt_api_key
from app.services.advanced_question_service import answer_advanced_dataset_question


def initialize_database():
    """Apply pending database schema migrations before serving requests."""
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(backend_dir / "alembic.ini"))
    command.upgrade(alembic_config, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="InsightFlow AI",
    description="An intelligent AI-powered data analysis platform.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(ai_credentials_router)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """Attach baseline browser security headers to every API response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    return response


def get_allowed_origins() -> list[str]:
    """Read and validate explicit browser origins from the environment."""
    configured = os.getenv("BACKEND_CORS_ORIGINS", "").strip()
    if not configured:
        # Local development defaults only; production must set this variable.
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    if not origins:
        raise RuntimeError("BACKEND_CORS_ORIGINS must contain at least one trusted origin.")

    for origin in origins:
        parsed = urlsplit(origin)
        if (
            "*" in origin
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise RuntimeError(
                "Invalid BACKEND_CORS_ORIGINS entry. Use exact origins such as https://app.example.com."
            )
        hostname = (parsed.hostname or "").lower()
        is_localhost = hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not is_localhost:
            raise RuntimeError("Non-local production CORS origins must use HTTPS.")

    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.get("/")
def root():
    return {
        "message": "Welcome to InsightFlow AI",
        "status": "running",
    }


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "application": "InsightFlow AI",
        "version": "0.1.0",
    }


@app.post("/api/v1/datasets/upload", dependencies=[Depends(get_current_user)])
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        content = await file.read(10 * 1024 * 1024 + 1)
        result = inspect_dataset(filename=file.filename or "unknown", content=content)

        record = models.DatasetRecord(
            user_id=current_user.id,
            filename=result["filename"],
            file_type=result["file_type"],
            file_size_bytes=result["file_size_bytes"],
            row_count=result["total_rows"],
            column_count=result["total_columns"],
            columns=result["columns"],
            data_types=result["data_types"],
            missing_values=result["missing_values"],
            total_missing_values=result["total_missing_values"],
            duplicate_rows=result["duplicate_rows"],
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        result["registry_id"] = record.id
        result["registered_at"] = record.created_at.isoformat()

        return {
            "message": "Dataset inspected and registered successfully",
            "dataset": result,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to register dataset metadata.") from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/explore", dependencies=[Depends(get_current_user)])
async def explore_dataset(
    file: UploadFile = File(...),
    page: int = Form(1),
    page_size: int = Form(25),
    search: str = Form(""),
):
    """Explore an uploaded dataset with search, pagination, and EDA statistics."""
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

        result = generate_exploration(
            dataframe=dataframe,
            page=page,
            page_size=page_size,
            search=search,
        )
        return {
            "message": "Dataset exploration completed successfully",
            "filename": filename,
            "exploration": result,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to explore this dataset. Check the file and try again.",
        ) from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/statistics", dependencies=[Depends(get_current_user)])
async def dataset_statistics_endpoint(file: UploadFile = File(...)):
    """Generate advanced distribution, correlation, and group-comparison statistics."""
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)
        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")
        result = generate_statistical_analysis(dataframe)
        return {"message": "Advanced statistical analysis completed", "filename": filename, "rows": int(dataframe.shape[0]), "columns": int(dataframe.shape[1]), "statistics": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to generate statistical analysis. Check the file and try again.") from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/executive-report", dependencies=[Depends(get_current_user)])
async def executive_report_endpoint(file: UploadFile = File(...)):
    """Create a concise executive report from local dataset statistics."""
    try:
        filename = file.filename or "dataset"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)
        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")
        report = generate_executive_report(dataframe, filename)
        return {"message": "Executive report generated successfully", "report": report}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to generate the executive report. Check the file and try again.") from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/quality", dependencies=[Depends(get_current_user)])
async def dataset_quality_endpoint(file: UploadFile = File(...)):
    """Generate an overall and column-level data quality report."""
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)
        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")
        report = generate_data_quality_report(dataframe)
        return {"message": "Data quality report generated successfully", "filename": filename, "report": report}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to generate the data quality report. Check the file and try again.") from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/export/analytics.xlsx", dependencies=[Depends(get_current_user)])
async def export_analytics_excel(file: UploadFile = File(...)):
    """Export a multi-sheet Excel analytics report for an uploaded dataset."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter

        filename = file.filename or "dataset"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)
        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

        report = generate_exploration(dataframe=dataframe, page=1, page_size=25, search="")
        identifier_pattern = r"(^id$|(^|[_\s-])id($|[_\s-])|uuid|guid|identifier|serial|roll[_\s-]?no|student[_\s-]?no|customer[_\s-]?no|account[_\s-]?no)"
        identifier_columns = [
            column["name"] for column in report.get("columns", [])
            if __import__("re").search(identifier_pattern, column["name"], __import__("re").IGNORECASE)
        ]
        categorical_statistics = {
            name: items for name, items in report.get("categorical_statistics", {}).items()
            if name not in identifier_columns
        }
        workbook = Workbook()
        overview = workbook.active
        overview.title = "Overview"
        overview.append(["InsightFlow AI - Analytics Report"])
        overview.append(["Source file", filename])
        overview.append(["Metric", "Value"])
        for key, value in report["overview"].items():
            if key == "categorical_columns":
                value = len(categorical_statistics)
            overview.append([key.replace("_", " ").title(), value])
        overview.append(["Identifier columns", len(identifier_columns)])
        overview.append(["Identifier fields excluded", ", ".join(identifier_columns) or "None"])

        numeric_sheet = workbook.create_sheet("Numeric Summary")
        numeric_sheet.append(["Feature", "Count", "Mean", "Median", "Std Dev", "Minimum", "Maximum"])
        for name, stats in report.get("numeric_statistics", {}).items():
            numeric_sheet.append([name, stats.get("count"), stats.get("mean"), stats.get("median"), stats.get("std"), stats.get("min"), stats.get("max")])

        outlier_sheet = workbook.create_sheet("Outliers")
        outlier_sheet.append(["Feature", "IQR Outlier Count"])
        for name, count in report.get("outlier_counts_iqr", {}).items():
            outlier_sheet.append([name, count])

        category_sheet = workbook.create_sheet("Categorical Distributions")
        category_sheet.append(["Column", "Value", "Count", "Percentage"])
        for column, items in categorical_statistics.items():
            total = sum(item.get("count", 0) for item in items)
            for item in items:
                count = item.get("count", 0)
                category_sheet.append([column, item.get("value"), count, count / total if total else 0])

        correlation_sheet = workbook.create_sheet("Correlations")
        correlation_sheet.append(["Feature", *report.get("correlation", {}).keys()])
        for feature, values in report.get("correlation", {}).items():
            correlation_sheet.append([feature, *[values.get(name) for name in report.get("correlation", {}).keys()]])

        header_fill = PatternFill("solid", fgColor="312E81")
        for sheet in workbook.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions if sheet.max_row > 1 else "A1"
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = header_fill
            for column_cells in sheet.columns:
                max_length = max((len(str(cell.value)) if cell.value is not None else 0) for cell in column_cells)
                sheet.column_dimensions[get_column_letter(column_cells[0].column)].width = min(max(max_length + 2, 12), 42)
        for row in category_sheet.iter_rows(min_row=2, min_col=4, max_col=4):
            row[0].number_format = "0.0%"

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        safe_name = filename.rsplit(".", 1)[0].replace('"', "")
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_analytics.xlsx"'},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to export the analytics workbook.") from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/insights", dependencies=[Depends(get_current_user)])
async def generate_dataset_insights_endpoint(file: UploadFile = File(...)):
    """Generate evidence-backed plain-English insights for an uploaded dataset."""
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

        insights = generate_dataset_insights(dataframe)
        return {
            "message": "Dataset insights generated successfully",
            "filename": filename,
            "insights": insights,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to generate insights for this dataset. Check the file and try again.",
        ) from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/ask", dependencies=[Depends(get_current_user)])
async def ask_dataset_question_endpoint(
    file: UploadFile = File(...),
    question: str = Form(...),
):
    """Answer a natural-language question using deterministic dataset operations."""
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

        answer = answer_dataset_question(dataframe=dataframe, question=question)
        return {
            "message": "Dataset question answered successfully",
            "filename": filename,
            "qa": answer,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to answer this question. Check the dataset and try again.",
        ) from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/suggest-questions", dependencies=[Depends(get_current_user)])
async def suggest_dataset_questions_endpoint(file: UploadFile = File(...)):
    """Profile a dataset locally and return relevant, supported question suggestions."""
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

        profile = generate_question_suggestions(dataframe)
        return {
            "message": "Dynamic dataset questions generated successfully",
            "filename": filename,
            "profile": profile,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to generate questions for this dataset. Check the file and try again.",
        ) from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/ask/advanced")
async def ask_dataset_question_advanced_endpoint(
    file: UploadFile = File(...),
    question: str = Form(...),
    credential_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Answer a dataset question using this user's saved, encrypted AI provider credential."""
    try:
        credential = (
            db.query(AIProviderCredential)
            .filter(
                AIProviderCredential.id == credential_id,
                AIProviderCredential.user_id == current_user.id,
            )
            .first()
        )
        if credential is None:
            raise HTTPException(status_code=404, detail="Saved AI provider connection not found.")
        if credential.protocol != "openai_compatible":
            raise HTTPException(status_code=400, detail="This provider protocol is not supported by Dataset Q&A yet.")
        api_key = decrypt_api_key(credential.encrypted_api_key)

        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

        answer = answer_advanced_dataset_question(
            dataframe=dataframe,
            question=question,
            api_key=api_key,
            model=credential.model_id,
            base_url=credential.base_url,
            provider_name=credential.provider_name,
            protocol=credential.protocol,
        )
        return {
            "message": "Advanced AI dataset question answered successfully",
            "filename": filename,
            "qa": answer,
        }

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to complete Advanced AI analysis. Check the model response and try again.",
        ) from exc
    finally:
        await file.close()


@app.post("/api/v1/ai/providers/nvidia/test", dependencies=[Depends(get_current_user)])
async def test_nvidia_provider_endpoint(
    api_key: str = Form(...),
    model: str = Form("meta/llama-3.3-70b-instruct"),
):
    """Test a user-supplied NVIDIA API key without persisting it."""
    try:
        return test_nvidia_connection(api_key=api_key, model=model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/ml/prepare", dependencies=[Depends(get_current_user)])
async def prepare_ml_dataset(
    file: UploadFile = File(...),
    target_column: str = Form("Label"),
    test_size: float = Form(0.2),
    random_state: int = Form(42),
):
    """Validate a binary classification target and prepare a stratified split."""
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

        prepared = prepare_classification_dataset(
            dataframe=dataframe,
            target_column=target_column,
            test_size=test_size,
            random_state=random_state,
        )
        return {
            "message": "ML dataset preparation completed successfully",
            "filename": filename,
            "preparation": prepared["summary"],
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to prepare this dataset for machine learning.",
        ) from exc
    finally:
        await file.close()




@app.post("/api/v1/ml/train", dependencies=[Depends(get_current_user)])
async def train_ml_models(
    file: UploadFile = File(...),
    target_column: str = Form("Label"),
    test_size: float = Form(0.2),
    random_state: int = Form(42),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Train baseline binary classifiers and evaluate on a stratified holdout set."""
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

        prepared = prepare_classification_dataset(
            dataframe=dataframe,
            target_column=target_column,
            test_size=test_size,
            random_state=random_state,
        )
        training = train_classification_models(
            prepared=prepared,
            random_state=random_state,
            user_id=current_user.id,
        )
        model_record = models.MLModelRecord(
            id=training["model_id"],
            user_id=current_user.id,
            dataset_filename=filename,
            target_column=prepared["summary"]["target_column"],
            feature_count=training["feature_count"],
            test_rows=training["test_rows"],
            class_labels=training["class_labels"],
            model_names=training["saved_models"],
            metrics=[
                {
                    "model": item["model"],
                    "accuracy": item["accuracy"],
                    "precision_macro": item["precision_macro"],
                    "recall_macro": item["recall_macro"],
                    "f1_macro": item["f1_macro"],
                }
                for item in training["results"]
            ],
        )
        db.add(model_record)
        db.commit()
        return {
            "message": "Classification models trained and metadata registered successfully",
            "filename": filename,
            "preparation": prepared["summary"],
            "training": training,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to train classification models on this dataset.",
        ) from exc
    finally:
        await file.close()


@app.get("/api/v1/ml/models", dependencies=[Depends(get_current_user)])
def get_saved_ml_models(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return saved model bundles enriched with persistent database metadata."""
    try:
        result = list_saved_models(user_id=current_user.id)
        records = {
            record.id: record
            for record in db.query(models.MLModelRecord).filter(models.MLModelRecord.user_id == current_user.id).all()
        }
        for item in result.get("models", []):
            record = records.get(item["model_id"])
            if record:
                item.update({
                    "dataset_filename": record.dataset_filename,
                    "test_rows": record.test_rows,
                    "metrics": record.metrics or [],
                    "registered_at": record.created_at.isoformat(),
                })
        result["registered_models"] = len(records)
        result["storage_note"] = "Model binaries remain in the backend artifact directory; database stores metadata only."
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/ml/predict", dependencies=[Depends(get_current_user)])
async def predict_with_trained_model(
    file: UploadFile = File(...),
    model_id: str = Form(...),
    model_name: str = Form("Random Forest"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Predict labels for a new dataset using a previously saved model."""
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

        owned_model = db.query(models.MLModelRecord).filter(models.MLModelRecord.id == model_id, models.MLModelRecord.user_id == current_user.id).first()
        if owned_model is None:
            raise HTTPException(status_code=404, detail="Saved model not found.")
        result = predict_with_saved_model(
            user_id=current_user.id,
            dataframe=dataframe,
            model_id=model_id,
            model_name=model_name,
        )
        return {
            "message": "Predictions generated successfully",
            "filename": filename,
            "prediction": result,
        }

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to generate predictions. Check the model ID and dataset.",
        ) from exc
    finally:
        await file.close()


@app.post("/api/v1/ml/explain", dependencies=[Depends(get_current_user)])
async def explain_saved_model_prediction(
    file: UploadFile = File(...),
    model_id: str = Form(...),
    model_name: str = Form("Random Forest"),
    row_index: int = Form(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Explain one prediction using local median-replacement sensitivity."""
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

        owned_model = db.query(models.MLModelRecord).filter(models.MLModelRecord.id == model_id, models.MLModelRecord.user_id == current_user.id).first()
        if owned_model is None:
            raise HTTPException(status_code=404, detail="Saved model not found.")
        explanation = explain_prediction(
            user_id=current_user.id,
            dataframe=dataframe,
            model_id=model_id,
            model_name=model_name,
            row_index=row_index,
        )
        return {
            "message": "Prediction explanation generated successfully",
            "filename": filename,
            "explanation": explanation,
        }

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to explain this prediction. Check the model and dataset.",
        ) from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/chart", dependencies=[Depends(get_current_user)])
async def build_dataset_chart(
    file: UploadFile = File(...),
    x_column: str = Form(...),
    y_column: str = Form(""),
    chart_type: str = Form("bar"),
    aggregation: str = Form("sum"),
    filter_column: str = Form(""),
    filter_value: str = Form(""),
    filter_min: str = Form(""),
    filter_max: str = Form(""),
):
    """Return chart-ready aggregates calculated from the full uploaded dataset."""
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)
        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]
        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
            except UnicodeDecodeError:
                dataframe = pd.read_csv(BytesIO(content), encoding="cp1252")
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

        chart = generate_chart_data(
            dataframe=dataframe,
            x_column=x_column,
            y_column=y_column,
            chart_type=chart_type,
            aggregation=aggregation,
            filter_column=filter_column,
            filter_value=filter_value,
            filter_min=filter_min,
            filter_max=filter_max,
        )
        return {"message": "Chart data generated successfully", "filename": filename, "chart": chart}

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to generate chart data for this dataset.",
        ) from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/clean/preview", dependencies=[Depends(get_current_user)])
async def preview_dataset_cleaning(file: UploadFile = File(...)):
    try:
        filename = file.filename or "unknown"
        content = await file.read(10 * 1024 * 1024 + 1)

        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]

        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content))
            except UnicodeDecodeError:
                dataframe = pd.read_csv(
                    BytesIO(content),
                    encoding="cp1252",
                )
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError(
                "Unsupported file type. Upload CSV, XLSX, or XLS."
            )

        result = generate_cleaning_preview(dataframe)

        return {
            "message": "Cleaning preview generated successfully",
            "filename": filename,
            "cleaning_preview": result,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    finally:
        await file.close()


@app.post("/api/v1/datasets/clean/apply", dependencies=[Depends(get_current_user)])
async def apply_dataset_cleaning(
    file: UploadFile = File(...),
    confirm: bool = Form(False),
):
    try:
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Cleaning was not approved. Set confirm=true to proceed.",
            )

        filename = file.filename or "dataset.csv"
        content = await file.read(10 * 1024 * 1024 + 1)

        inspect_dataset(filename=filename, content=content)

        extension = filename.lower().rsplit(".", 1)[-1]

        if extension == "csv":
            try:
                dataframe = pd.read_csv(BytesIO(content))
            except UnicodeDecodeError:
                dataframe = pd.read_csv(
                    BytesIO(content),
                    encoding="cp1252",
                )
        elif extension in ("xlsx", "xls"):
            dataframe = pd.read_excel(BytesIO(content))
        else:
            raise ValueError(
                "Unsupported file type. Upload CSV, XLSX, or XLS."
            )

        cleaned_dataframe, report = apply_cleaning(dataframe)

        csv_content = cleaned_dataframe.to_csv(
            index=False
        ).encode("utf-8-sig")

        return StreamingResponse(
            BytesIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    'attachment; filename="cleaned_dataset.csv"'
                ),
                "X-Cleaning-Rows-Removed": str(
                    report["duplicate_rows_removed"]
                ),
            },
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    finally:
        await file.close()


def _history_item(record: AnalysisHistory) -> dict:
    """Serialize one history row without exposing uploaded dataset contents."""
    return {
        "id": record.id,
        "filename": record.filename,
        "analysis_type": record.analysis_type,
        "row_count": record.row_count,
        "column_count": record.column_count,
        "summary": record.summary or {},
        "created_at": record.created_at.isoformat(),
        "notes": record.notes,
    }


@app.post("/api/v1/history", status_code=201, dependencies=[Depends(get_current_user)])
def create_analysis_history(payload: HistoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Persist analysis metadata and a compact result summary, never raw dataset rows."""
    import json

    summary_size = len(json.dumps(payload.summary, ensure_ascii=False, default=str).encode("utf-8"))
    if summary_size > 100_000:
        raise HTTPException(status_code=413, detail="Summary is too large. Keep it under 100 KB.")

    record = AnalysisHistory(
        user_id=current_user.id,
        filename=payload.filename,
        analysis_type=payload.analysis_type,
        row_count=payload.row_count,
        column_count=payload.column_count,
        summary=payload.summary,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"message": "Analysis history saved successfully", "item": _history_item(record)}


@app.get("/api/v1/history", dependencies=[Depends(get_current_user)])
def list_analysis_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return paginated analysis history, newest first."""
    query = db.query(AnalysisHistory).filter(AnalysisHistory.user_id == current_user.id)
    total = query.count()
    records = (
        query.order_by(AnalysisHistory.created_at.desc(), AnalysisHistory.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [_history_item(record) for record in records],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/v1/history/{history_id}", dependencies=[Depends(get_current_user)])
def get_analysis_history(history_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return one saved analysis record."""
    record = db.query(AnalysisHistory).filter(AnalysisHistory.id == history_id, AnalysisHistory.user_id == current_user.id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis history record not found.")
    return {"item": _history_item(record)}


@app.delete("/api/v1/history/{history_id}", dependencies=[Depends(get_current_user)])
def delete_analysis_history(history_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete one saved analysis record."""
    record = db.query(AnalysisHistory).filter(AnalysisHistory.id == history_id, AnalysisHistory.user_id == current_user.id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis history record not found.")
    db.delete(record)
    db.commit()
    return {"message": "Analysis history deleted successfully", "id": history_id}


@app.get("/api/v1/datasets/registry", dependencies=[Depends(get_current_user)])
def list_dataset_registry(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List registered dataset metadata, newest first. Source files and rows are never stored."""
    query = db.query(models.DatasetRecord).filter(models.DatasetRecord.user_id == current_user.id)
    total = query.count()
    records = (
        query.order_by(models.DatasetRecord.created_at.desc(), models.DatasetRecord.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [_dataset_registry_item(record) for record in records],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/v1/datasets/registry/{dataset_id}", dependencies=[Depends(get_current_user)])
def get_dataset_registry_item(dataset_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(models.DatasetRecord).filter(models.DatasetRecord.id == dataset_id, models.DatasetRecord.user_id == current_user.id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Dataset registry record not found.")
    return {"item": _dataset_registry_item(record)}


@app.delete("/api/v1/datasets/registry/{dataset_id}", dependencies=[Depends(get_current_user)])
def delete_dataset_registry_item(dataset_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(models.DatasetRecord).filter(models.DatasetRecord.id == dataset_id, models.DatasetRecord.user_id == current_user.id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Dataset registry record not found.")
    db.delete(record)
    db.commit()
    return {"message": "Dataset registry record deleted successfully", "id": dataset_id}


def _dataset_registry_item(record: models.DatasetRecord) -> dict:
    return {
        "id": record.id,
        "filename": record.filename,
        "file_type": record.file_type,
        "file_size_bytes": record.file_size_bytes,
        "row_count": record.row_count,
        "column_count": record.column_count,
        "columns": record.columns or [],
        "data_types": record.data_types or {},
        "missing_values": record.missing_values or {},
        "total_missing_values": record.total_missing_values,
        "duplicate_rows": record.duplicate_rows,
        "created_at": record.created_at.isoformat(),
    }
