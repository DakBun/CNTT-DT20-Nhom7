# Bài review code dự án Phân tích thị trường việc làm ngành CNTT (DT20)

**Danh sách file đã đọc:** .clinerules, .gitignore, README.md, main.py, dashboard.py, requirements.txt, src/config.py, src/ingestion/*, src/processing/cleaner.py, src/analysis/*, src/visualization/charts.py, scripts/*, data/DATA_DICTIONARY.md, notebooks/BTL_DT20.ipynb

---

## 1. Tổng quan dự án

Dự án phân tích thị trường việc làm CNTT từ 3 kỳ Stack Overflow Developer Survey (2019, 2022, 2025). Gộp được 211.274 dòng x 275 cột, sau lọc outlier còn 202.739 dòng. Kết hợp 5 tin tuyển dụng VN thu thập thủ công. Sản phẩm: pipeline 4 lớp, main.py, notebook nộp bài, dashboard Streamlit, phần mở rộng SQL Server.

## 2. Kiến trúc và luồng dữ liệu

CSV -> [ingestion] survey_loader.py -> [processing] cleaner.py -> [analysis] analyzer.py -> [visualization] charts.py -> figures/ (5 PNG). Dữ liệu chảy một chiều. Lớp sau chỉ gọi lớp trước. Khác MVC: không có vòng lặp giao diện.

## 3. Giải thích từng module

**src/config.py**: Hằng số đường dẫn (pathlib), SURVEY_YEARS (dict năm→CSV), COLUMN_MAPPING (gộp tên cột schema drift). Không phụ thuộc file nào.

**src/ingestion/survey_loader.py**: load_single_year(year) đọc CSV, chuẩn hóa dấu nháy U+2019→' cho mọi cột object, thêm survey_year. load_all_years(years) gọi load_single_year, rename theo COLUMN_MAPPING, concat, reset_index. Phụ thuộc: config.py.

**src/ingestion/vn_jobs_scraper.py**: scrape_vn_jobs() raise NotImplementedError (cào tự động không khả thi). load_manual_vn_jobs() đọc CSV, trả về 5 dòng. Phụ thuộc: config.py.

**src/ingestion/sql_loader.py**: load_to_sql_server() chạy pipeline, tạo respondent_id, explode kỹ năng, nạp 4 bảng SQL Server (fast_executemany). Phụ thuộc: survey_loader, vn_jobs_scraper, cleaner, config.

**src/processing/cleaner.py**: explode_multiselect() split 'Python;Java;SQL'→3 dòng, NaN giữ nguyên. filter_salary_outliers() IQR (Q1-1.5*IQR đến Q3+1.5*IQR) hoặc percentile, giữ NaN. normalize_remote_work() map 16 giá trị→4 nhóm. normalize_edlevel() map 17 giá trị→11 nhóm. clean_missing() fillna 'Không trả lời' cho 12 cột, parse YearsCode (map 'Less than 1 year'→0, 'More than 50 years'→51, to_numeric).

**src/analysis/analyzer.py**: compute_summary()→dict, analyze_salary_by_group()→median theo nhóm+năm, analyze_tech_demand()→tần suất+%, analyze_remote_work()→tỷ lệ %, compare_vn_vs_global_skills()→gap. Phụ thuộc: cleaner.py (explode_multiselect).

**src/analysis/sql_analyzer.py**: 4 câu SQL: salary_by_edlevel_sql (GROUP BY), salary_by_skill_sql (JOIN), tech_rank_by_year_sql (RANK() OVER), compare_vn_vs_global_sql (CTE+FULL JOIN).

**src/visualization/charts.py**: 5 plot: line (salary trend), bar ngang (tech popularity), bar chồng (remote work), bar nhóm (education), boxplot (salary). Lưu PNG dpi=150. Phụ thuộc: config.py, cleaner.py (normalize_edlevel).

**main.py**: Entry point 5 bước: (1) đọc, (2) làm sạch, (3) thống kê, (4) vẽ 5 biểu đồ, (5) phân tích. In tiến độ [1/5]→[5/5].

**dashboard.py**: Streamlit @st.cache_data load dashboard_data.pkl. Sidebar filter (năm+quốc gia). 4 metrics. 4 tab Altair (Công nghệ / Lương / Làm việc từ xa / Học vấn).

## 4. Quyết định kỹ thuật quan trọng

**COLUMN_MAPPING**: Schema drift - ConvertedComp (2019) vs ConvertedCompYearly (2022/2025), LanguageWorkedWith vs LanguageHaveWorkedWith. Nếu không mapping, 3 năm có cột riêng, không gộp được.

**Chuẩn hóa dấu nháy ở ingestion**: Dấu nháy cong U+2019 trong 'Bachelor's degree' làm map() không khớp key. Đặt ở ingestion xử lý 1 lần cho mọi cột.

**IQR và giữ NaN**: IQR không giả định phân phối chuẩn. Giữ NaN vì NaN = không trả lời lương, lọc bỏ mất thông tin nhóm.

**Gộp remote_work 4 nhóm**: 2019 hỏi tần suất, 2022/2025 hỏi loại hình - 2 cách hỏi khác nhau.

**Bảng gap**: % trên toàn bộ. Cách cũ (top 15 mỗi bên rồi merge) tạo pct_used=0 giả cho công nghệ ngoài top 15.

**SQL Server bridge table**: Multi-select vi phạm 1NF, không JOIN/GROUP BY. Bridge table mỗi dòng=1 kỹ năng/1 người.

## 5. Cách chạy từng phần

- main.py (3-4 ph): `.venv\Scripts\python.exe main.py`
- Notebook (3-5 ph): `.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace notebooks\BTL_DT20.ipynb`
- Dashboard: build cache `.venv\Scripts\python.exe scripts\build_processed_cache.py` rồi `.venv\Scripts\python.exe -m streamlit run dashboard.py`
- SQL Server: cài pyodbc+sqlalchemy, chạy setup_sql.py, rồi load_to_sql_server()

## 6. Điểm yếu đã biết

- Cỡ mẫu VN jobs chỉ 5 tin (minh họa).
- experience_group (pd.cut) lặp ở 3 nơi (main.py, build_processed_cache.py, notebook) — cần gom vào cleaner.py.
- Cào ITviec/TopCV không khả thi (HTML thô không dữ liệu, không API).
- Tỷ lệ không trả lời cao: remote_work 19-31%, salary_usd ~46%.
- 2022 không tách hybrid chi tiết.
- Indentation lệch config.py (dòng LanguageDesireNextYear, LanguageWantToWorkWith).
- `_bin_years_code` trong analyzer.py không được gọi.

## 7. Câu hỏi vấn đáp (15 câu)

1. **Số cột tăng 275→277?** normalize_* mỗi hàm thêm _detail, 275+2=277.
2. **Dữ liệu bao nhiêu dòng?** 211.274 gốc, 202.739 sau lọc outlier.
3. **COLUMN_MAPPING?** Gộp tên cột schema drift qua 3 năm.
4. **Chuẩn hóa dấu nháy ở ingestion?** Xử lý 1 lần, tránh map() không khớp key.
5. **explode_multiselect?** Split 'Python;Java;SQL'→3 dòng. NaN giữ nguyên.
6. **Giữ NaN lọc lương?** NaN=không trả lời, lọc bỏ mất thông tin nhóm.
7. **IQR vs percentile?** IQR: Q1-1.5*IQR đến Q3+1.5*IQR. Percentile: 1%-99%.
8. **Gộp remote_work 4 nhóm?** 2019 hỏi tần suất, 2022/2025 hỏi loại hình.
9. **Bảng gap?** % trên toàn bộ, pct_wanted-pct_used. Gap dương=nhu cầu vượt dùng.
10. **analyze_salary_by_group?** Lương trung vị theo nhóm+năm, kèm count.
11. **analyze_remote_work?** Tỷ lệ % remote_work theo năm.
12. **Bridge table?** Multi-select vi phạm 1NF, không JOIN/GROUP BY.
13. **RANK() OVER?** PARTITION BY survey_year, top 10 mỗi năm.
14. **CTE+FULL JOIN?** CTE tính % riêng, FULL JOIN lấy cả 1 bên có.
15. **Altair thay st.bar_chart?** st.bar_chart tự chọn trục sai (vùng âm).