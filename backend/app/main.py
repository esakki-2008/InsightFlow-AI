
from io import BytesIO

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.services.cleaning_service import (
    apply_cleaning,
    generate_cleaning_preview,
)
from app.services.dataset_service import inspect_dataset
from app.services.exploration_service import generate_exploration
from app.services.ml_preparation_service import prepare_classification_dataset


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
