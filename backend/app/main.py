
from io import BytesIO

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.services.chart_service import generate_chart_data
from app.services.cleaning_service import (
    apply_cleaning,
    generate_cleaning_preview,
)
from app.services.dataset_service import inspect_dataset
from app.services.exploration_service import generate_exploration
from app.services.ml_preparation_service import prepare_classification_dataset
from app.services.ml_training_service import train_classification_models
from app.services.ml_model_service import predict_with_saved_model, list_saved_models
from app.services.ml_explainability_service import explain_prediction
from app.services.insights_service import generate_dataset_insights
from app.services.question_service import answer_dataset_question
from app.services.question_suggestion_service import generate_question_suggestions
from app.services.llm_provider_service import test_nvidia_connection
from app.services.advanced_question_service import answer_advanced_dataset_question


app = FastAPI(
    title="InsightFlow AI",
    description="An intelligent AI-powered data analysis platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.post("/api/v1/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    try:
        content = await file.read(10 * 1024 * 1024 + 1)

        result = inspect_dataset(
            filename=file.filename or "unknown",
            content=content,
        )

        return {
            "message": "Dataset inspected successfully",
            "dataset": result,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    finally:
        await file.close()


@app.post("/api/v1/datasets/explore")
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


@app.post("/api/v1/datasets/insights")
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


@app.post("/api/v1/datasets/ask")
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


@app.post("/api/v1/datasets/suggest-questions")
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
    api_key: str = Form(...),
    model: str = Form("nvidia/nemotron-3.5-lightning-30b-a3b"),
):
    """Answer a dataset question using NVIDIA planning and validated local Pandas execution."""
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

        answer = answer_advanced_dataset_question(
            dataframe=dataframe,
            question=question,
            api_key=api_key,
            model=model,
        )
        return {
            "message": "Advanced AI dataset question answered successfully",
            "filename": filename,
            "qa": answer,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to complete Advanced AI analysis. Check the model response and try again.",
        ) from exc
    finally:
        await file.close()


@app.post("/api/v1/ai/providers/nvidia/test")
async def test_nvidia_provider_endpoint(
    api_key: str = Form(...),
    model: str = Form("meta/llama-3.3-70b-instruct"),
):
    """Test a user-supplied NVIDIA API key without persisting it."""
    try:
        return test_nvidia_connection(api_key=api_key, model=model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/ml/prepare")
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




@app.post("/api/v1/ml/train")
async def train_ml_models(
    file: UploadFile = File(...),
    target_column: str = Form("Label"),
    test_size: float = Form(0.2),
    random_state: int = Form(42),
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
        )
        return {
            "message": "Classification models trained and evaluated successfully",
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


@app.get("/api/v1/ml/models")
def get_saved_ml_models():
    """Return metadata for models currently saved on this backend instance."""
    try:
        return list_saved_models()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/ml/predict")
async def predict_with_trained_model(
    file: UploadFile = File(...),
    model_id: str = Form(...),
    model_name: str = Form("Random Forest"),
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

        result = predict_with_saved_model(
            dataframe=dataframe,
            model_id=model_id,
            model_name=model_name,
        )
        return {
            "message": "Predictions generated successfully",
            "filename": filename,
            "prediction": result,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to generate predictions. Check the model ID and dataset.",
        ) from exc
    finally:
        await file.close()


@app.post("/api/v1/ml/explain")
async def explain_saved_model_prediction(
    file: UploadFile = File(...),
    model_id: str = Form(...),
    model_name: str = Form("Random Forest"),
    row_index: int = Form(0),
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

        explanation = explain_prediction(
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

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to explain this prediction. Check the model and dataset.",
        ) from exc
    finally:
        await file.close()


@app.post("/api/v1/datasets/chart")
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


@app.post("/api/v1/datasets/clean/preview")
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


@app.post("/api/v1/datasets/clean/apply")
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
