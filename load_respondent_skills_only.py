import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.survey_loader import load_all_years
from src.processing.cleaner import clean_missing, filter_salary_outliers, normalize_remote_work, normalize_edlevel, explode_multiselect
import pandas as pd
import sqlalchemy

engine = sqlalchemy.create_engine(
    r"mssql+pyodbc://localhost\SQLEXPRESS/DT20_CNTT?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes",
    fast_executemany=True
)

df = load_all_years([2019, 2022, 2025])
df = clean_missing(df)
df = normalize_remote_work(df)
df = normalize_edlevel(df)
df = filter_salary_outliers(df)
bins = [-1, 2, 5, 10, 20, 100]
labels = ["0-2 năm", "3-5 năm", "6-10 năm", "11-20 năm", "20+ năm"]
df["experience_group"] = pd.cut(df["YearsCode"], bins=bins, labels=labels)
df = df.reset_index(drop=True)
df["respondent_id"] = df.index + 1

assert len(df) == 202739, f"Số dòng không khớp: {len(df)} != 202739 — DỪNG, respondent_id sẽ không khớp bảng respondents đã có"

used = explode_multiselect(df[["respondent_id", "languages_used"]], "languages_used").dropna(subset=["languages_used"])
used = used.rename(columns={"languages_used": "skill_name"}); used["skill_type"] = "used"
wanted = explode_multiselect(df[["respondent_id", "languages_wanted"]], "languages_wanted").dropna(subset=["languages_wanted"])
wanted = wanted.rename(columns={"languages_wanted": "skill_name"}); wanted["skill_type"] = "wanted"
skills = pd.concat([used, wanted], ignore_index=True)
skills[["respondent_id", "skill_type", "skill_name"]].to_sql("respondent_skills", engine, if_exists="append", index=False, chunksize=2000)
print("XONG - đã nạp:", len(skills))