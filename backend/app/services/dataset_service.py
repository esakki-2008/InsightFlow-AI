
from io import BytesIO
from pathlib import Path

import pandas as pd


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ROWS = 100_000
MAX_COLUMNS = 100

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def inspect_dataset(filename: str, content: bytes) -> dict:
    """Validate an uploaded dataset and return basic dataset statistics."""

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file format. Upload CSV, XLSX, or XLS.")

    if not content:
        raise ValueError("The uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise ValueError("File exceeds the maximum allowed size of 10 MB.")

    file_buffer = BytesIO(content)

    try:
        if extension == ".csv":
            if b"\x00" in content:
                raise ValueError("The CSV file contains invalid binary data.")

            try:
                dataframe = pd.read_csv(file_buffer, encoding="utf-8-sig", nrows=MAX_ROWS + 1)
            except UnicodeDecodeError:
                file_buffer.seek(0)
                dataframe = pd.read_csv(file_buffer, encoding="cp1252", nrows=MAX_ROWS + 1)

        elif extension == ".xlsx":
            if not content.startswith(b"PK"):
                raise ValueError("The XLSX file does not have a valid file signature.")

            dataframe = pd.read_excel(
                file_buffer,
                engine="openpyxl",
                nrows=MAX_ROWS + 1,
            )

        else:
            if not content.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
                raise ValueError("The XLS file does not have a valid file signature.")

            dataframe = pd.read_excel(
                file_buffer,
                engine="xlrd",
                nrows=MAX_ROWS + 1,
            )

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "Unable to read this dataset. Check that the file is valid and not corrupted."
        ) from exc

    if dataframe.empty:
        raise ValueError("The dataset contains no data rows.")

    if len(dataframe) > MAX_ROWS:
        raise ValueError(f"The dataset exceeds the maximum of {MAX_ROWS:,} rows.")

    if len(dataframe.columns) > MAX_COLUMNS:
        raise ValueError(f"The dataset exceeds the maximum of {MAX_COLUMNS} columns.")

    missing_values = dataframe.isna().sum()

    return {
        "filename": filename,
        "file_size_bytes": len(content),
        "file_size_kb": round(len(content) / 1024, 2),
        "file_type": extension.lstrip(".").upper(),
        "total_rows": int(len(dataframe)),
        "total_columns": int(len(dataframe.columns)),
        "columns": [str(column) for column in dataframe.columns],
        "data_types": {
            str(column): str(dtype)
            for column, dtype in dataframe.dtypes.items()
        },
        "missing_values": {
            str(column): int(count)
            for column, count in missing_values.items()
        },
        "total_missing_values": int(missing_values.sum()),
        "duplicate_rows": int(dataframe.duplicated().sum()),
    }
