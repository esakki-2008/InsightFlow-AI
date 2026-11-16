import pandas as pd
import pytest

from app.services.cleaning_service import generate_cleaning_preview
from app.services.dataset_service import inspect_dataset
from app.services.question_service import answer_dataset_question


def test_inspect_dataset_accepts_valid_csv():
    content = b"name,score\nAda,91\nLinus,88\n"

    result = inspect_dataset("students.csv", content)

    assert result["total_rows"] == 2
    assert result["total_columns"] == 2
    assert result["filename"] == "students.csv"


def test_inspect_dataset_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported file format"):
        inspect_dataset("students.txt", b"name\nAda\n")


def test_inspect_dataset_rejects_empty_file():
    with pytest.raises(ValueError, match="empty"):
        inspect_dataset("empty.csv", b"")


def test_cleaning_preview_detects_duplicates_and_missing_values():
    frame = pd.DataFrame({
        " score ": [10.0, 10.0, None],
        "group": ["A", "A", "B"],
    })

    result = generate_cleaning_preview(frame)

    assert result["summary"]["duplicate_rows_detected"] == 1
    assert result["summary"]["missing_values_after"] == 0
    assert result["preview"]["columns"] == ["score", "group"]
    # Preview generation must not mutate the uploaded dataframe.
    assert frame.columns.tolist() == [" score ", "group"]
    assert frame[" score "].isna().sum() == 1


def test_dataset_question_returns_row_and_column_counts():
    frame = pd.DataFrame({"name": ["Ada", "Linus"], "score": [91, 88]})

    result = answer_dataset_question(frame, "How many rows are there?")

    assert result["query_type"] == "row_count"
    assert result["result"] == {"rows": 2, "columns": 2}


def test_dataset_question_reports_duplicate_rows():
    frame = pd.DataFrame({"name": ["Ada", "Ada"], "score": [91, 91]})

    result = answer_dataset_question(frame, "How many duplicate rows?")

    assert result["query_type"] == "duplicates"
    assert result["result"]["duplicate_rows"] == 1


def test_dataset_question_rejects_blank_question():
    frame = pd.DataFrame({"score": [91]})

    with pytest.raises(ValueError, match="Enter a question"):
        answer_dataset_question(frame, "   ")
