"""SQL analysis utilities for already-loaded data in SQL Server."""

import pandas as pd


def salary_by_edlevel_sql(engine) -> pd.DataFrame:
    """GROUP BY: lương trung bình theo trình độ học vấn."""
    query = """
    SELECT ed_level, AVG(salary_usd) AS avg_salary, COUNT(*) AS n
    FROM respondents
    WHERE salary_usd IS NOT NULL
    GROUP BY ed_level
    ORDER BY avg_salary DESC;
    """
    return pd.read_sql(query, engine)


def salary_by_skill_sql(engine) -> pd.DataFrame:
    """JOIN: lương trung bình của người dùng từng công nghệ (>500 mẫu)."""
    query = """
    SELECT rs.skill_name, AVG(r.salary_usd) AS avg_salary, COUNT(*) AS n
    FROM respondents r
    JOIN respondent_skills rs ON r.respondent_id = rs.respondent_id
    WHERE rs.skill_type = 'used' AND r.salary_usd IS NOT NULL
    GROUP BY rs.skill_name
    HAVING COUNT(*) > 500
    ORDER BY avg_salary DESC;
    """
    return pd.read_sql(query, engine)


def tech_rank_by_year_sql(engine) -> pd.DataFrame:
    """Window function: xếp hạng top 10 công nghệ mỗi năm bằng RANK()."""
    query = """
    SELECT survey_year, skill_name, cnt,
           RANK() OVER (PARTITION BY survey_year ORDER BY cnt DESC) AS rank_in_year
    FROM (
        SELECT r.survey_year, rs.skill_name, COUNT(*) AS cnt
        FROM respondents r
        JOIN respondent_skills rs ON r.respondent_id = rs.respondent_id
        WHERE rs.skill_type = 'used'
        GROUP BY r.survey_year, rs.skill_name
    ) t
    WHERE 1=1;
    """
    df = pd.read_sql(query, engine)
    return df[df["rank_in_year"] <= 10].sort_values(["survey_year", "rank_in_year"])


def compare_vn_vs_global_sql(engine) -> pd.DataFrame:
    """CTE + FULL OUTER JOIN: so sánh % kỹ năng VN jobs vs khảo sát toàn cầu."""
    query = """
    WITH vn_pct AS (
        SELECT skill_name, COUNT(*) * 100.0 / (SELECT COUNT(*) FROM vn_job_skills) AS pct_vn
        FROM vn_job_skills GROUP BY skill_name
    ),
    global_pct AS (
        SELECT skill_name, COUNT(*) * 100.0 / (SELECT COUNT(*) FROM respondent_skills WHERE skill_type='used') AS pct_global
        FROM respondent_skills WHERE skill_type = 'used' GROUP BY skill_name
    )
    SELECT COALESCE(v.skill_name, g.skill_name) AS skill_name,
           ISNULL(v.pct_vn, 0) AS pct_vn,
           ISNULL(g.pct_global, 0) AS pct_global,
           ISNULL(v.pct_vn, 0) - ISNULL(g.pct_global, 0) AS gap
    FROM vn_pct v
    FULL OUTER JOIN global_pct g ON v.skill_name = g.skill_name
    ORDER BY gap DESC;
    """
    return pd.read_sql(query, engine)