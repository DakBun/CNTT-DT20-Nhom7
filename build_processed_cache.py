"""Build cache dữ liệu đã xử lý cho dashboard (định dạng Pickle)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.config import PROCESSED_DIR
from src.ingestion.survey_loader import load_all_years
from src.processing.cleaner import (
    clean_missing,
    explode_multiselect,
    filter_salary_outliers,
    normalize_edlevel,
    normalize_remote_work,
)

COLS = [
    "survey_year",
    "Country",
    "EdLevel",
    "DevType",
    "YearsCode",
    "experience_group",
    "salary_usd",
    "remote_work",
    "OrgSize",
    "Age",
    "languages_used",
    "languages_wanted",
]


def main() -> None:
    print("Đang đọc dữ liệu...")
    df = load_all_years([2019, 2022, 2025])

    print("Đang làm sạch...")
    df = clean_missing(df)
    df = normalize_remote_work(df)
    df = normalize_edlevel(df)
    df = filter_salary_outliers(df)

    print("Đang tạo nhóm kinh nghiệm...")
    bins = [-1, 2, 5, 10, 20, 100]
    labels = ["0-2 năm", "3-5 năm", "6-10 năm", "11-20 năm", "20+ năm"]
    df["experience_group"] = pd.cut(df["YearsCode"], bins=bins, labels=labels)

    out = PROCESSED_DIR / "dashboard_data.pkl"
    out.parent.mkdir(parents=True, exist_ok=True)
    df[COLS].to_pickle(out)
    print(f"Đã lưu cache: {df[COLS].shape} -> {out}")


if __name__ == "__main__":
    main()
