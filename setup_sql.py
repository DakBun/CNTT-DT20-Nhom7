import pyodbc

conn = pyodbc.connect(
    r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\SQLEXPRESS;"
    r"DATABASE=master;Trusted_Connection=yes;",
    autocommit=True,
)
cursor = conn.cursor()
cursor.execute("IF DB_ID('DT20_CNTT') IS NULL CREATE DATABASE DT20_CNTT")
conn.close()

conn = pyodbc.connect(
    r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\SQLEXPRESS;"
    r"DATABASE=DT20_CNTT;Trusted_Connection=yes;",
    autocommit=True,
)
cursor = conn.cursor()
ddl = """
IF OBJECT_ID('respondent_skills') IS NOT NULL DROP TABLE respondent_skills;
IF OBJECT_ID('vn_job_skills') IS NOT NULL DROP TABLE vn_job_skills;
IF OBJECT_ID('respondents') IS NOT NULL DROP TABLE respondents;
IF OBJECT_ID('vn_jobs') IS NOT NULL DROP TABLE vn_jobs;

CREATE TABLE respondents (
    respondent_id INT PRIMARY KEY,
    survey_year INT,
    age NVARCHAR(50),
    country NVARCHAR(100),
    dev_type NVARCHAR(200),
    ed_level NVARCHAR(100),
    years_code FLOAT,
    experience_group NVARCHAR(20),
    salary_usd FLOAT,
    remote_work NVARCHAR(50)
);

CREATE TABLE respondent_skills (
    respondent_id INT FOREIGN KEY REFERENCES respondents(respondent_id),
    skill_type NVARCHAR(10),
    skill_name NVARCHAR(100)
);

CREATE TABLE vn_jobs (
    job_id INT PRIMARY KEY,
    job_title NVARCHAR(200),
    company NVARCHAR(200),
    location NVARCHAR(100),
    posted_date NVARCHAR(50)
);

CREATE TABLE vn_job_skills (
    job_id INT FOREIGN KEY REFERENCES vn_jobs(job_id),
    skill_name NVARCHAR(100)
);
"""
for stmt in ddl.split(";"):
    if stmt.strip():
        cursor.execute(stmt)
conn.close()
print("Đã tạo database + 4 bảng")
