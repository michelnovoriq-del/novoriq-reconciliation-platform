from pathlib import Path
from typing import Any

import pandas as pd


def _load_dataframe(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False, skip_blank_lines=False)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, dtype=str, keep_default_na=False)
    raise ValueError("Only CSV and Excel files are supported.")


def count_rows(file_path: str) -> int:
    return len(_load_dataframe(file_path))


def preview_file(file_path: str, limit: int = 5) -> tuple[list[str], list[dict[str, Any]]]:
    df = _load_dataframe(file_path)
    return list(df.columns), df.head(limit).to_dict(orient="records")


def read_rows(file_path: str) -> list[dict[str, Any]]:
    return _load_dataframe(file_path).to_dict(orient="records")


def read_file(file_path: str) -> tuple[list[str], list[dict[str, Any]]]:
    df = _load_dataframe(file_path)
    return list(df.columns), df.to_dict(orient="records")
