"""SQL Server ingestion utilities."""

import pandas as pd
import sqlalchemy

from src.ingestion.survey_loader import load_all_years
from src.ingestion.vn_jobs_scraper import load_manual_vn_jobs
from src.processing.cleaner import (
    clean_missing,
    filter_salary_outliers,
    normalize_remote_work,
    normalize_edlevel,
    explode_multiselect,
)

CONN_STR = (
    r"mssql+pyodbc://localhost\SQLEXPRESS/DT20_CNTT"
    r"?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
)


def load_to_sql_server():
    """
    Nạp dữ liệu đã làm sạch vào SQL Server: bảng respondents +
    respondent_skills (từ khảo sát), vn_jobs + vn_job_skills (từ tin
    tuyển dụng VN thu thập thủ công). Dùng fast_executemany để nạp nhanh
    với dữ liệu lớn (~1-2 triệu dòng ở respondent_skills).
    """
    engine = sqlalchemy.create_engine(CONN_STR, fast_executemany=True)

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

    respondents = df[[
        "respondent_id", "survey_year", "Age", "Country",
        "DevType", "EdLevel", "YearsCode", "experience_group",
        "salary_usd", "remote_work",
    ]].copy()
    respondents.columns = [
        "respondent_id", "survey_year", "age", "country",
        "dev_type", "ed_level", "years_code",
        "experience_group", "salary_usd", "remote_work",
    ]
    respondents.to_sql(
        "respondents", engine, if_exists="append", index=False, chunksize=1000
    )
    print(f"Đã nạp {len(respondents)} dòng vào respondents")

    used = explode_multiselect(df[["respondent_id", "languages_used"]], "languages_used")
    used = used.dropna(subset=["languages_used"])
    used = used.rename(columns={"languages_used": "skill_name"})
    used["skill_type"] = "used"

    wanted = explode_multiselect(df[["respondent_id", "languages_wanted"]], "languages_wanted")
    wanted = wanted.dropna(subset=["languages_wanted"])
    wanted = wanted.rename(columns={"languages_wanted": "skill_name"})
    wanted["skill_type"] = "wanted"

    skills = pd.concat([used, wanted], ignore_index=True)
    skills[["respondent_id", "skill_type", "skill_name"]].to_sql(
        "respondent_skills", engine, if_exists="append", index=False, chunksize=2000
    )
    print(f"Đã nạp {len(skills)} dòng vào respondent_skills")

    vn_df = load_manual_vn_jobs().reset_index(drop=True)
    vn_df["job_id"] = vn_df.index + 1
    vn_df[["job_id", "job_title", "company", "location", "posted_date"]].to_sql(
        "vn_jobs", engine, if_exists="append", index=False
    )
    print(f"Đã nạp {len(vn_df)} dòng vào vn_jobs")

    vn_skills = explode_multiselect(vn_df[["job_id", "required_skills"]], "required_skills")
    vn_skills = vn_skills.dropna(subset=["required_skills"])
    vn_skills = vn_skills.rename(columns={"required_skills": "skill_name"})
    vn_skills[["job_id", "skill_name"]].to_sql(
        "vn_job_skills", engine, if_exists="append", index=False
    )
    print(f"Đã nạp {len(vn_skills)} dòng vào vn_job_skills")

    return engine