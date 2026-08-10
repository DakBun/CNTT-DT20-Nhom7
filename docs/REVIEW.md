# REVIEW toàn bộ project CNTT

**Ngày:** 2026-08-10
**Phạm vi đọc:** `src/`, `scripts/`, `notebooks/`, `docs/`, `dashboard.py`, `main.py`, `README.md`, `requirements.txt`, `.env.example`, `.gitignore`.
**Bỏ qua:** `.venv/`, `data/`, `figures/`, `__pycache__/`, `.git/` (theo yêu cầu).
**Chế độ:** READ-ONLY. Chỉ ghi file `docs/REVIEW.md`.
**Ghi chú phương pháp:** mọi `file:line` trong review này đều trỏ tới nội dung đã mở đọc trực tiếp. Giá trị nào chưa kiểm chứng được ghi rõ `[UNVERIFIED]`.

---

## Phase 1 — Inventory

Tổng cộng **23 file trong phạm vi** (không kể `__pycache__`), **2.537 dòng** (trong đó code Python ~1.107 dòng, notebook JSON 1.148 dòng, còn lại là docs/config).

### Bảng inventory

| STT | Path (tương đối project root) | LOC | Vai trò |
|----|-------------------------------|-----|---------|
| 1 | `src/config.py` | 52 | Hằng số đường dẫn (BASE_DIR/RAW_DIR/...), `SURVEY_YEARS`, `COLUMN_MAPPING` gộp schema drift |
| 2 | `src/__init__.py` | 0 | Package marker |
| 3 | `src/ingestion/survey_loader.py` | 35 | `load_single_year`/`load_all_years`: đọc CSV 3 năm, chuẩn hóa dấu nháy U+2019→', rename theo COLUMN_MAPPING |
| 4 | `src/ingestion/vn_jobs_scraper.py` | 36 | `scrape_vn_jobs` (raise NotImplementedError) + `load_manual_vn_jobs` đọc `data/external/vn_jobs_manual.csv` |
| 5 | `src/ingestion/sql_loader.py` | 75 | `load_to_sql_server`: chạy pipeline, tạo respondent_id, nạp 4 bảng SQL Server (fast_executemany) |
| 6 | `src/ingestion/__init__.py` | 0 | Package marker |
| 7 | `src/processing/cleaner.py` | 200 | Cleaning: explode multi-select, lọc outlier lương (IQR/percentile), gộp nhóm remote_work/EdLevel, xử lý missing |
| 8 | `src/processing/__init__.py` | 0 | Package marker |
| 9 | `src/analysis/analyzer.py` | 172 | 5 hàm phân tích chính: compute_summary, analyze_salary_by_group, analyze_tech_demand, analyze_remote_work, compare_vn_vs_global_skills (+ 1 hàm private dead) |
| 10 | `src/analysis/sql_analyzer.py` | 60 | 4 câu SQL demo: GROUP BY, JOIN, RANK() OVER, CTE+FULL OUTER JOIN |
| 11 | `src/analysis/__init__.py` | 0 | Package marker |
| 12 | `src/visualization/charts.py` | 144 | 5 plot (line, bar ngang, bar chồng, bar nhóm, boxplot), lưu PNG dpi=150 vào `figures/` |
| 13 | `src/visualization/__init__.py` | 0 | Package marker |
| 14 | `scripts/build_processed_cache.py` | 46 | Build `data/processed/dashboard_data.pkl` cho dashboard |
| 15 | `scripts/load_respondent_skills_only.py` | 29 | Nạp riêng bảng `respondent_skills` vào SQL Server (lặp pipeline của sql_loader) |
| 16 | `scripts/setup_sql.py` | 54 | Tạo database `DT20_CNTT` + 4 bảng quan hệ (DROP + CREATE) |
| 17 | `notebooks/BTL_DT20.ipynb` | 1148 | Notebook nộp bài: 15 cell (8 code + 7 markdown) gọi lại các module |
| 18 | `docs/CODE_REVIEW.md` | 54 | Bài review code có sẵn của nhóm |
| 19 | `dashboard.py` | 153 | Dashboard Streamlit 4 tab (Công nghệ / Lương / Từ xa / Học vấn), filter năm + quốc gia |
| 20 | `main.py` | 80 | Pipeline 5 bước: đọc → làm sạch → thống kê → vẽ 5 biểu đồ → phân tích lương/công nghệ |
| 21 | `README.md` | 145 | Tài liệu: cấu trúc, nguồn dữ liệu, cài đặt, cách chạy, trạng thái, hạn chế |
| 22 | `requirements.txt` | 11 | 11 dòng dependency |
| 23 | `.env.example` | 3 | Mẫu biến môi trường (chỉ comment, không có biến thực) |
| 24 | `.gitignore` | 40 | Bỏ qua .venv, .env, CSV thô, pickle cache, figures, log... |

> File `.clinerules` (23 dòng) nằm ngoài danh sách phạm vi yêu cầu nhưng đã đọc để tham chiếu quy ước code (yêu cầu UTF-8 tường minh cho file có tiếng Việt — dùng trong Phase 3/5).

## Phase 2 — Kiến trúc & luồng dữ liệu

### Sơ đồ luồng dữ liệu

```text
data/raw/{2019,2022,2025}/survey_results_public.csv
        │  (1) ingestion
        ▼
  src/ingestion/survey_loader.load_all_years([2019,2022,2025])
        • đọc CSV → chuẩn hóa dấu nháy U+2019→' mọi cột object
        • rename theo COLUMN_MAPPING → concat 3 năm (211.274 dòng × 275 cột)
        ▼
  DataFrame
        │  (2) cleaning — pipeline 4 bước, lặp ở 5 nơi:
        │      main.py / build_processed_cache.py / sql_loader.py /
        │      load_respondent_skills_only.py / notebook CELL 5
        ▼
  clean_missing → normalize_remote_work → normalize_edlevel → filter_salary_outliers
        │                                                 (+ pd.cut tạo experience_group lặp 4 nơi)
        ├─────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
  (3a) main.py / notebook        (3b) build_processed_cache.py   (3c) sql_loader.py
        │                           │                              │
        ▼                           ▼                              ▼
  analyzer.py ─▶ charts.py    data/processed/dashboard_data.pkl    SQL Server (fast_executemany)
        │         │                    │                           bảng: respondents,
        │         ▼                    ▼                           respondent_skills, vn_jobs,
        │     figures/*.png        dashboard.py (Streamlit 4 tab)  vn_job_skills
        ▼                                                          │
  (main.py in stdout)                                              ▼
                                                                 sql_analyzer.py (4 câu SQL demo)

data/external/vn_jobs_manual.csv ─▶ vn_jobs_scraper.load_manual_vn_jobs()
        ├──────────────────────────────► notebook (compare_vn_vs_global_skills)
        └──────────────────────────────► sql_loader (nạp vn_jobs, vn_job_skills)
```

### Đánh giá kiến trúc

- **Phân lớp 1 chiều, không circular import** ✅: `config → survey_loader/vn_jobs_scraper`; `cleaner` độc lập; `analyzer → cleaner`; `charts → cleaner+config`; `sql_loader → survey_loader+vn_jobs_scraper+cleaner`. Không có vòng lặp import chéo.
- **Điểm đứt gãy / rủi ro 1 — thiếu pipeline chung**: toàn bộ chuỗi `load_all_years → clean_missing → normalize_remote_work → normalize_edlevel → filter_salary_outliers` được copy nguyên xi ở **5 nơi** (`main.py:32-40`, `build_processed_cache.py:38-44`, `sql_loader.py:31-35`, `load_respondent_skills_only.py:15-19`, notebook CELL 5). Việc tạo `experience_group` (bins/labels) lặp ở **4 nơi** (`sql_loader.py:36-38`, `build_processed_cache.py:47-49`, `load_respondent_skills_only.py:20-22`, notebook CELL 5). Đổi 1 bước cleaning phải sửa hàng loạt, dễ lệch kết quả giữa các nhánh.
- **Điểm đứt gãy / rủi ro 2 — không nhất quán định nghĩa "nhóm kinh nghiệm"**: helper `_bin_years_code` trong `analyzer.py:9-10` định nghĩa bins `[0,2,5,10,20,inf]` + label `"20+"`, **khác** với bins `[-1,2,5,10,20,100]` + label `"20+ năm"` dùng ở 4 nơi kia — và helper này **không được gọi** (dead). Tồn tại song song 2 chuẩn phân nhóm.
- **Điểm đứt gãy / rủi ro 3 — logic trùng giữa notebook/ và src/ hoặc dashboard**: bảng tính "gap" (chênh lệch muốn học − đã dùng) được viết tay lặp ở `dashboard.py:99-103` và notebook CELL 6/7, trong khi `analyzer.py` đã có `analyze_tech_demand` nhưng không có hàm gap dùng chung.
- **Điểm đứt gãy / rủi ro 4 — notebook có cell markdown chứa code**: CELL 6 là `markdown` nhưng `source` chứa code Python (giống hệt CELL 7). Cell này hiển thị text chứ không chạy → không "lớp vỏ mỏng" như README mô tả, đồng thời tạo bản sao logic.
- **Điểm đứt gãy / rủi ro 5 — nhánh SQL không idempotent**: `sql_loader.py` và `load_respondent_skills_only.py` dùng `if_exists="append"` cho cả 4 bảng → chạy 2 lần trùng khóa chính/bị duplicate (chi tiết Phase 4).
- **Điểm đứt gãy / rủi ro 6 — dữ liệu VN chỉ chạy ở nhánh notebook + SQL**: `main.py` không gọi `load_manual_vn_jobs`/`compare_vn_vs_global_skills`, dù docstring `main.py:2` và README gọi đây là "toàn bộ pipeline".

## Phase 3 — Review từng module trong `src/`

### 3.1 `src/config.py`

### [LOW] Thụt lề lệch ở `LanguageDesireNextYear`
- File: `src/config.py:56`
- Vấn đề: Chỉ dòng `"LanguageDesireNextYear": "languages_wanted"` thụt lề 2 spaces trong khi các mapping khác 4 spaces. CODE_REVIEW.md:65 ghi "cả LanguageDesireNextYear *và* LanguageWantToWorkWith lệch" — thực tế chỉ có dòng này lệch.
- Fix:
```python
    "LanguageDesireNextYear": "languages_wanted",
```

### [LOW] `COLUMN_MAPPING` không bị khai báo trùng
- File: `src/config.py:31-61`
- Vấn đề: Tin tốt — mapping cột chỉ định nghĩa **1 lần** tại config.py, các module khác đều import từ đây (survey_loader.py:7). Không có trùng khai báo.
- Fix: (không cần)

### [LOW] Side-effect `mkdir` khi import
- File: `src/config.py:22-23`
- Vấn đề: Import `config` là tự tạo 4 thư mục (RAW/PROCESSED/EXTERNAL/FIGURES). Không gây hại nhưng là side-effect ẩn khi chỉ muốn lấy hằng số.
- Fix: (tùy chọn) chuyển vào hàm `ensure_dirs()` gọi ở entry point.

### 3.2 `src/ingestion/survey_loader.py`

### [MED] Comment tiếng Việt bị mojibake (U+FFFD) — vi phạm .clinerules
- File: `src/ingestion/survey_loader.py:23`
- Vấn đề: Comment `# Chu?n ha d?u nhy ?on ki?u in ?n (’, U+2019)...` bị hỏng mã hóa, chứa ký tự thay thế `U+FFFD` (đã kiểm tra bytes `\xef\xbf\xbd`). File bắt đầu bằng BOM `\xef\xbb\xbf`. Trái yêu cầu UTF-8 tường minh trong `.clinerules:5`.
- Fix: viết lại comment sạch UTF-8:
```python
# Chuẩn hóa dấu nháy cong kiểu in ấn (’, U+2019) về dấu nháy ASCII (') để xử lý toàn cục
```

### [LOW] Normalize dấu nháy chỉ dùng đúng 1 ký tự U+2019
- File: `src/ingestion/survey_loader.py:24-25`
- Vấn đề: Chỉ thay `’` (U+2019); các dạng nháy cong khác không xử lý. Hiện tại dữ liệu 3 năm chỉ gặp U+2019 nên chạy ổn; chỉ là điểm dễ vỡ khi thêm năm mới.
- Fix: (dự phòng) dùng regex mở rộng hoặc giữ nguyên và ghi nhận là hạn chế đã biết.

### 3.3 `src/ingestion/vn_jobs_scraper.py`

### [LOW] `scrape_vn_jobs` là code sống dở (raise NotImplementedError)
- File: `src/ingestion/vn_jobs_scraper.py:31`
- Vấn đề: Docstring chi tiết nhưng thân hàm chỉ `raise NotImplementedError`. Hợp lệ vì đã ghi rõ lý do cào không khả thi; chỉ cần đảm bảo không ai gọi nhầm.
- Fix: (giữ nguyên; nếu muốn sạch: trả DataFrame rỗng kèm warning thay vì raise).

### 3.4 `src/processing/cleaner.py`

### [MED] `clean_missing` có vòng lặp `for...pass` — code chết
- File: `src/processing/cleaner.py:242-244`
- Vấn đề: `for col in _MULTISELECT_COLS: if col in df.columns: pass` không làm gì — scaffold bỏ sót khi triển khai.
- Fix: xóa 3 dòng này.

### [LOW] Docstring `clean_missing` nói "13 cột chung" nhưng thực tế 12
- File: `src/processing/cleaner.py:216`
- Vấn đề: `_CATEGORICAL_COLS` (cleaner.py:6-19) có đúng 12 phần tử, docstring ghi 13 — lệch số.
- Fix: sửa docstring thành "12 cột chung".

### [LOW] `normalize_remote_work` / `normalize_edlevel` biến giá trị không khớp thành NaN ngầm
- File: `src/processing/cleaner.py:157`, `src/processing/cleaner.py:209`
- Vấn đề: `.map(REMOTE_WORK_GROUPS)` / `.map(EDLEVEL_GROUPS)` — giá trị không có trong dict thành `NaN` im lặng. Hiện tại 16 key remote + 17 key edlevel bao phủ đủ 3 năm nên không lỗi, nhưng thêm năm mới sẽ âm thầm mất dữ liệu.
- Fix: (dự phòng) log số giá trị không khớp thay vì NaN:
```python
unmapped = df[col].isna() & df[f"{col}_detail"].notna()
if unmapped.any():
    print(f"[WARN] {col}: {unmapped.sum()} giá trị không map được")
```

### 3.5 `src/analysis/analyzer.py`

### [MED] `_bin_years_code` là dead code và định nghĩa nhóm kinh nghiệm KHÁC chuẩn
- File: `src/analysis/analyzer.py:17-43` (bins/labels tại `:9-10`)
- Vấn đề: Hàm này không được gọi ở bất kỳ đâu (chỉ xuất hiện trong docstring `analyze_salary_by_group:91` và CODE_REVIEW.md). Bins `[0,2,5,10,20,inf]` & label `"20+"` khác hẳn chuẩn `[-1,2,5,10,20,100]` & `"20+ năm"` dùng ở sql_loader/build_processed_cache/load_respondent_skills_only/notebook → tồn tại song song 2 chuẩn phân nhóm.
- Fix: xóa `_bin_years_code` + `_YEARS_CODE_BINS/_YEARS_CODE_LABELS`; gom pd.cut vào 1 hàm chung trong cleaner.py (xem Phase 6).

### [LOW] `compare_vn_vs_global_skills` rename cột `index`→`skill` mong manh
- File: `src/analysis/analyzer.py:215-217`
- Vấn đề: `pd.concat([vn_counts, global_counts], axis=1)` — nếu 2 Series có cùng index name thì `reset_index()` ra cột mang tên đó chứ không phải `"index"`, khi đó `rename(columns={"index": "skill"})` không đổi tên đúng. Hiện tại chạy đúng (vn index name `required_skills`, global `languages_used` khác nhau → index name None → cột `"index"`).
- Fix: đặt tên index rõ ràng trước khi concat:
```python
vn_counts.index.name = "skill"
global_counts.index.name = "skill"
merged = pd.concat([vn_counts, global_counts], axis=1).fillna(0)
merged["gap"] = merged["pct_vn"] - merged["pct_global"]
return merged.sort_values("gap", ascending=False).reset_index()
```

### 3.6 `src/analysis/sql_analyzer.py`

### [LOW] Điều kiện `WHERE 1=1;` thừa
- File: `src/analysis/sql_analyzer.py:44`
- Vấn đề: `WHERE 1=1;` là còn sót khi dựng subquery, không có tác dụng.
- Fix: bỏ dòng `WHERE 1=1;`.

### 3.7 `src/visualization/charts.py`

### [MED] Double-normalize `EdLevel` làm mất cột detail gốc
- File: `src/visualization/charts.py:118` (`plot_education_distribution`) và `:149` (`plot_salary_boxplot`)
- Vấn đề: Cả 2 hàm gọi `normalize_edlevel(df, ...)` trên df đã normalize sẵn trong pipeline (main.py:39 / build cache:43). Hàm này tạo `EdLevel_detail = df[col]` từ **giá trị đã gộp** → `EdLevel_detail` không còn là chi tiết gốc. Đồng thời chạy lại thừa.
- Fix: chỉ normalize khi cột detail chưa tồn tại:
```python
def _ensure_edlevel(df, col):
    if f"{col}_detail" not in df.columns:
        from src.processing.cleaner import normalize_edlevel
        df = normalize_edlevel(df, col)
    return df
```
(thay `df = normalize_edlevel(df, education_col)` / `df = normalize_edlevel(df, group_col)` ở 2 chỗ).

> **Tổng kết Phase 3 — không phát hiện:** SettingWithCopyWarning / chained indexing (mọi hàm đều `df.copy()` trước khi gán), KeyError khi thiếu cột ở các nhánh chính (đều có guard `if col not in df.columns`), COLUMN_MAPPING trùng khai báo, hay lỗi dtype ép sai ở các cột đã làm sạch.

## Phase 4 — `dashboard.py`, `main.py`, `scripts/`

### 4.1 `dashboard.py`

### [HIGH] `import altair` nhưng thiếu `altair` trong `requirements.txt`
- File: `dashboard.py:8` (import), `requirements.txt` (không có)
- Vấn đề: Dashboard phụ thuộc `altair` nhưng requirements không liệt kê → theo đúng README `pip install -r requirements.txt` rồi `streamlit run dashboard.py` sẽ lỗi `ModuleNotFoundError: No module named 'altair'` trên máy mới.
- Fix: thêm dòng vào `requirements.txt`:
```
altair
```

### [MED] Logic tính bảng "gap" bị lặp với notebook (không dùng hàm chung)
- File: `dashboard.py:99-103`
- Vấn đề: `value_counts(normalize=True)` → `pd.concat(...).fillna(0)` → `gap = pct_wanted - pct_used` → `rename(columns={"index": "tech"})` được viết tay, trùng với notebook CELL 6/7. Cùng nỗi lo rename cột `index` mong manh như `analyzer.py:217`.
- Fix: đưa về 1 hàm `compute_tech_gap(df)` trong `analyzer.py`, cả dashboard và notebook cùng gọi.
```python
def compute_tech_gap(df, used_col="languages_used", wanted_col="languages_wanted"):
    used = df[used_col].dropna().value_counts(normalize=True).mul(100).rename("pct_used")
    wanted = df[wanted_col].dropna().value_counts(normalize=True).mul(100).rename("pct_wanted")
    gap = pd.concat([used, wanted], axis=1).fillna(0)
    gap.index.name = "tech"
    gap["gap"] = gap["pct_wanted"] - gap["pct_used"]
    return gap.sort_values("gap", ascending=False).reset_index()
```

### [LOW] Dashboard không guard trường hợp `view` rỗng sau filter
- File: `dashboard.py:47-49` (lọc năm/quốc gia) → các tab sau đó
- Vấn đề: Nếu tổ hợp năm+quốc gia không có dòng nào, `explode_multiselect` và `analyze_tech_demand` trả về frame rỗng; Altair vẽ trên dữ liệu rỗng có thể lỗi. `[UNVERIFIED]` hành vi chính xác của altair trên empty data (chưa chạy thử).
- Fix: thêm guard đầu `main()`:
```python
if view.empty:
    st.warning("Không có dữ liệu cho bộ lọc đã chọn.")
    return
```

### [LOW] Error message cache hardcode tên file Windows `.venv\Scripts\python.exe`
- File: `dashboard.py:28-29`
- Vấn đề: Nhắc chạy `.venv\Scripts\python.exe scripts\build_processed_cache.py` — chỉ đúng trên Windows; trên macOS/Linux đường dẫn khác.
- Fix: dùng đường dẫn tương đối thân thiện: `python scripts\\build_processed_cache.py`.

### [LOW] Chỉ `load_data` được cache, các bước explode/analyze chạy lại mỗi lần tương tác
- File: `dashboard.py:23-32` (`@st.cache_data` chỉ trên `load_data`)
- Vấn đề: `explode_multiselect` (copy toàn df) gọi lại mỗi khi đổi filter → chậm trên ~200k dòng. Chấp nhận được với quy mô hiện tại.
- Fix: (tùy chọn) thêm `@st.cache_data` cho hàm explode/kết quả top-N.

### 4.2 `main.py`

### [MED] Docstring/README gọi là "toàn bộ pipeline" nhưng không chạy phần VN và SQL
- File: `main.py:2` (docstring), `main.py:29-97` (thân main)
- Vấn đề: Pipeline không gọi `load_manual_vn_jobs`/`compare_vn_vs_global_skills` (VN) và không nạp SQL; "toàn bộ quy trình" chỉ đúng với nhánh pandas/charts.
- Fix: hoặc thêm bước in `compare_vn_vs_global_skills` vào cuối `main()`, hoặc sửa docstring/README cho chính xác.

### 4.3 `scripts/build_processed_cache.py`

### [LOW] Import `explode_multiselect` không dùng
- File: `scripts/build_processed_cache.py:12-18`
- Vấn đề: import `explode_multiselect` nhưng `main()` không dùng tới.
- Fix: bỏ tên import thừa.

### [MED] `experience_group` tính lại (pd.cut) tại đây — lần thứ 4 trong repo
- File: `scripts/build_processed_cache.py:47-49`
- Vấn đề: Bins/labels copy thứ 4 (xem Phase 2); nếu đổi chuẩn phân nhóm phải sửa đồng bộ 4 chỗ.
- Fix: gọi chung hàm `add_experience_group(df)` trong cleaner.py.

### 4.4 `scripts/load_respondent_skills_only.py`

### [HIGH] Hardcode `assert len(df) == 202739` — dễ vỡ khi cleaning đổi, assert bị tắt ở `python -O`
- File: `scripts/load_respondent_skills_only.py:26`
- Vấn đề: Gắn cứng macro số dòng + dùng `assert` (bị bỏ qua ở `-O`). Nếu đổi bước cleaning, con số lệch và `respondent_id` không khớp bảng `respondents` đã có — rủi ro dữ liệu sai.
- Fix: dùng `if` + raise rõ ràng:
```python
if len(df) != 202739:
    raise RuntimeError(f"Số dòng lệch: {len(df)} != 202739 — dừng, tránh lệch respondent_id")
```

### [HIGH] Nhân bản toàn bộ pipeline + CONN_STR từ `sql_loader.py` (kém bảo trì)
- File: `scripts/load_respondent_skills_only.py:10-13, 15-24`
- Vấn đề: copy lại load→clean→pd.cut→respondent_id và connection string của `sql_loader.py:16-19,31-40`. Đổi pipeline/conn ở 1 nơi không phản ánh nơi kia → dễ lệch dữ liệu nạp SQL với phần còn lại.
- Fix: tái sử dụng `sql_loader`:
```python
from src.ingestion.sql_loader import CONN_STR, load_to_sql_server
# hoặc tách hàm build_respondent_skills() ra dùng chung
```

### [MED] `to_sql(..., if_exists="append")` không idempotent
- File: `scripts/load_respondent_skills_only.py:33`
- Vấn đề: Chạy lại sẽ append trùng `respondent_skills`; nếu chạy `load_to_sql_server` trước đó thì trùng cả `respondents` → PK violation.
- Fix: kiểm tra count hiện tại trước khi append, hoặc dùng `if_exists="replace"` khi chỉ load bảng này.

### 4.5 `scripts/setup_sql.py`

### [MED] Cắt DDL bằng `split(";")` dễ vỡ nếu có `;` trong nội dung
- File: `scripts/setup_sql.py:56-58`
- Vấn đề: `for stmt in ddl.split(";")` — hiện DDL không có `;` nội bộ nên chạy đúng, nhưng thêm comment/giá trị chứa `;` sẽ vỡ.
- Fix: (dự phòng) chạy cả khối qua một lần `cursor.execute(ddl)` hoặc tách từng câu `CREATE TABLE` rõ ràng.

### [LOW] Thông tin kết nối SQL cứng 3 nơi, không qua `.env`
- File: `scripts/setup_sql.py:3-7`, `src/ingestion/sql_loader.py:16-19`, `scripts/load_respondent_skills_only.py:11`
- Vấn đề: Server/DB/Driver viết cứng ở 3 file; `python-dotenv` có trong requirements nhưng không dùng ở đâu, `.env.example` trống. Đổi môi trường (LocalDB, instance khác) phải sửa 3 chỗ.
- Fix: đưa `CONN_STR` + server vào `src/config.py` đọc từ env với default:
```python
# config.py
import os
SQL_SERVER = os.getenv("SQL_SERVER", r"localhost\SQLEXPRESS")
SQL_DRIVER = os.getenv("SQL_DRIVER", "ODBC Driver 17 for SQL Server")
SQL_DB = os.getenv("SQL_DB", "DT20_CNTT")
CONN_STR = f"mssql+pyodbc://{SQL_SERVER}/{SQL_DB}?driver={SQL_DRIVER.replace(' ', '+')}&trusted_connection=yes"
```

## Phase 5 — Docs & config

### 5.1 README vs code thực tế — các chỗ lệch

### [MED] README nói database "tự tạo nếu chưa có" nhưng `load_to_sql_server` không tự tạo DB
- File: `README.md:167`; code `src/ingestion/sql_loader.py:29` (`create_engine` → `to_sql`)
- Vấn đề: README ghi "database DT20_CNTT (tự tạo nếu chưa có)". Thực tế `sqlalchemy.create_engine` + `to_sql` không tạo database (chỉ tạo bảng trong DB đã có); phải chạy `setup_sql.py` trước, nếu không sẽ lỗi "Cannot open database DT20_CNTT".
- Fix: sửa README thành "phải chạy `scripts/setup_sql.py` lần đầu để tạo database + 4 bảng".

### [MED] README gọi `main.py` là "chạy toàn bộ pipeline" nhưng không gồm phần VN và SQL
- File: `README.md:118`; `main.py:29-97`
- Vấn đề: `main.py` không gọi `load_manual_vn_jobs`/`compare_vn_vs_global_skills`, không nạp SQL — chỉ nhánh pandas/charts. Gây hiểu nhầm phạm vi.
- Fix: thêm câu giải thích "pipeline pandas; phần VN xem notebook, phần SQL xem sql_loader".

### [MED] README gọi notebook là "lớp vỏ mỏng gọi lại các module" nhưng notebook có logic nội tuyến + cell dư
- File: `README.md:140`; `notebooks/BTL_DT20.ipynb` CELL 6 (markdown chứa code), CELL 7 (gap logic viết tay)
- Vấn đề: Notebook không thuần "lớp vỏ mỏng": bảng gap được viết tay thay vì gọi hàm, và cell 6 là markdown chứa code (không chạy).
- Fix: sửa notebook dùng `compute_tech_gap()` (đề xuất Phase 4) và xóa cell 6.

### [LOW] README mô tả cấu trúc khớp phần lớn; numeric 88.883/73.268/49.123 = 211.274 khớp output notebook
- File: `README.md:113`, `notebooks/BTL_DT20.ipynb` CELL 3 output
- Vấn đề: Không có lệch về số liệu; xác nhận khớp.
- Fix: (không cần)

### 5.2 `requirements.txt`

### [HIGH] Thiếu `altair` và `nbconvert` mà README/code sử dụng
- File: `requirements.txt` (danh sách); `dashboard.py:8` (altair); `README.md:146` (lệnh `nbconvert`)
- Vấn đề: `altair` bắt buộc cho dashboard nhưng thiếu → dashboard không cài được trên máy mới. `nbconvert` được README dùng để chạy notebook nhưng cũng thiếu.
- Fix: thêm 2 dòng:
```
altair
nbconvert
```

### [LOW] Package thừa, không được import: `seaborn`, `openpyxl`, `python-dotenv`; `numpy` chỉ dùng gián tiếp
- File: `requirements.txt:2,9,8`
- Vấn đề: `seaborn`/`openpyxl`/`python-dotenv` không được import ở bất kỳ file nào trong phạm vi (đã tìm `import`). `numpy` chỉ là dependency gián tiếp của pandas. `requests`/`beautifulsoup4`/`lxml` chỉ phục vụ `scrape_vn_jobs` chưa triển khai.
- Fix: bỏ `seaborn`, `openpyxl`, `python-dotenv` (hoặc giữ `python-dotenv` nếu áp dụng Fix Phase 4.5 dùng `.env`); `pyodbc` vẫn cố ý không thêm (đã ghi chú README).

### 5.3 `.gitignore`

### [LOW] BOM + pattern lặp; nhưng chặn đúng `data/` và `.env`
- File: `.gitignore:1` (BOM), `.gitignore:14` (`.env`), `.gitignore:17` + `:34` (`data/raw/*.csv`), `:48` (`data/processed/*.pkl`), `:37` (`figures/`)
- Vấn đề: `.env` có chặn ✅; `data/raw/*.csv` + `data/raw/*/*.csv` chặn CSV thô ✅; `data/processed/*.pkl` chặn cache dashboard ✅; `figures/` chặn ✅. `data/external/vn_jobs_manual.csv` KHÔNG bị chặn — đúng ý đồ vì README nói file này được commit. Chỉ còn lỗi thẩm mỹ: BOM dòng 1 và pattern `data/raw/*.csv`/`data/raw/*/*.csv` gần trùng.
- Fix: (tùy chọn) bỏ BOM; gộp thành `data/raw/` nếu muốn chặn cả cây.

### 5.4 `.env.example`

### [LOW] `.env.example` trống, không có code nào nạp biến môi trường
- File: `.env.example:1-3`
- Vấn đề: Chỉ có comment, không khai báo biến nào; `python-dotenv` không được dùng. Nếu áp dụng Fix Phase 4.5 (CONN_STR từ env) thì cần điền đầy đủ ở đây:
```
SQL_SERVER=localhost\SQLEXPRESS
SQL_DRIVER=ODBC Driver 17 for SQL Server
SQL_DB=DT20_CNTT
```

### 5.5 `docs/CODE_REVIEW.md` (bài review có sẵn) — một số chi tiết sai

### [LOW] CODE_REVIEW ghi "experience_group (pd.cut) lặp ở 3 nơi (main.py, build_processed_cache.py, notebook)" — sai
- File: `docs/CODE_REVIEW.md:61`
- Vấn đề: `main.py` **không** có `pd.cut`; thực tế pd.cut xuất hiện ở 4 nơi: `sql_loader.py:36-38`, `build_processed_cache.py:47-49`, `load_respondent_skills_only.py:20-22`, notebook CELL 5.
- Fix: cập nhật lại danh sách vị trí lặp.

### [LOW] CODE_REVIEW ghi "Indentation lệch config.py (dòng LanguageDesireNextYear, LanguageWantToWorkWith)" — chỉ 1 dòng lệch
- File: `docs/CODE_REVIEW.md:65`; `src/config.py:56-57`
- Vấn đề: Chỉ `LanguageDesireNextYear` (dòng 56) thụt lề 2 spaces; `LanguageWantToWorkWith` (dòng 57) đã thụt 4 spaces đúng.
- Fix: sửa lại mô tả.

## Phase 6 — Tổng hợp

### 6.1 Top 10 vấn đề (xếp theo mức độ nghiêm trọng × phạm vi ảnh hưởng)

| # | Mức | Vấn đề | Ảnh hưởng |
|---|-----|--------|-----------|
| 1 | HIGH | Thiếu `altair` trong requirements nhưng `dashboard.py:8` import → dashboard không chạy trên máy mới cài theo README | Toàn bộ nhánh dashboard |
| 2 | HIGH | Pipeline cleaning copy ở 5 nơi (`main.py`, `build_processed_cache.py`, `sql_loader.py`, `load_respondent_skills_only.py`, notebook) + `experience_group` pd.cut ở 4 nơi → đổi 1 bước dễ lệch kết quả giữa các nhánh | Toàn bộ project |
| 3 | HIGH | SQL load không idempotent: `if_exists="append"` ở `sql_loader.py:53,69,76,84` và `load_respondent_skills_only.py:33` → chạy 2 lần bị trùng/PK violation | Nhánh SQL |
| 4 | MED | `load_respondent_skills_only.py:26` hardcode `assert len(df)==202739` (tắt khi `python -O`) + nhân bản pipeline/CONN_STR từ sql_loader | Nhánh SQL (dữ liệu sai âm thầm) |
| 5 | MED | Tồn tại 2 chuẩn nhóm kinh nghiệm: `_bin_years_code` (`analyzer.py:9-10`, dead) vs bins `[-1,2,5,10,20,100]` ở 4 nơi → kết quả "lương theo kinh nghiệm" có thể khác nhau tùy chỗ chạy | Phân tích lương |
| 6 | MED | Logic bảng gap lặp ở `dashboard.py:99-103` + notebook CELL 6/7 (và CELL 6 là markdown chứa code không chạy) — không dùng hàm chung | Dashboard + notebook |
| 7 | MED | `charts.py:118,149` double-normalize EdLevel → mất `EdLevel_detail` gốc khi vẽ lại | figures/ + notebook |
| 8 | MED | README lệch code: "database tự tạo nếu chưa có" (`README.md:167`), "main.py chạy toàn bộ pipeline" (`:118`) không gồm VN/SQL, notebook "lớp vỏ mỏng" (`:140`) không đúng | Tài liệu/người dùng |
| 9 | MED | Connection string SQL cứng 3 nơi (`sql_loader.py:16-19`, `load_respondent_skills_only.py:11`, `setup_sql.py:3-7`); `python-dotenv` & `.env.example` không được dùng | Bảo trì / môi trường khác |
| 10 | LOW | Dead code: `clean_missing` `for...pass` (`cleaner.py:242-244`), `WHERE 1=1` (`sql_analyzer.py:44`), import thừa `explode_multiselect` (`build_processed_cache.py:12-18`), `scrape_vn_jobs` (`vn_jobs_scraper.py:31`) | Vệ sinh code |

### 6.2 Thứ tự fix (theo thứ tự phụ thuộc — cái trước phải xong trước)

1. **Gom pipeline + `add_experience_group()` vào `cleaner.py`** (1 hàm duy nhất) → thay 5 chỗ copy. *Phải làm trước mọi thứ vì các fix khác (SQL, notebook, dashboard) đều trỏ vào đây; sau khi gom, con số 202.739 cần tính lại từ hàm chung.*
2. **Thêm `altair` (+ `nbconvert`) vào `requirements.txt`** — fix 1 dòng, gỡ ngay rủi ro dashboard không cài được.
3. **Sửa nhánh SQL**: `load_to_sql_server()` đổi `if_exists="append"` → kiểm tra count/delete-trước-khi-insert; `load_respondent_skills_only.py` gọi hàm chung của sql_loader và thay `assert` bằng `if/raise`. *Phụ thuộc mục 1 (dùng pipeline chung).*
4. **Xóa `_bin_years_code` + `_YEARS_CODE_BINS`**, đảm bảo chỉ còn 1 chuẩn phân nhóm. *Phụ thuộc mục 1.*
5. **Thêm `compute_tech_gap()` vào `analyzer.py`** → dùng chung dashboard + notebook; xóa CELL 6 (markdown chứa code).
6. **Fix double-normalize** trong `charts.py` (`_ensure_edlevel`).
7. **Đưa CONN_STR/server vào `config.py` đọc từ env** + điền `.env.example`; sửa `setup_sql.py` dùng chung.
8. **Cập nhật README + CODE_REVIEW.md** cho khớp code thực tế (DB setup, phạm vi main.py, notebook, danh sách pd.cut).
9. **Dọn dead code nhỏ** (mục 10 bảng trên) và sửa mojibake comment `survey_loader.py:23`.

### 6.3 Vấn đề hệ thống (lặp ở nhiều module)

- **Không có hàm pipeline chung** — gốc rễ của nhiều rủi ro: cleaning copy 5 chỗ, pd.cut 4 chỗ, gap logic 2 chỗ, connection string 3 chỗ, notebook nội tuyến. Đây là vấn đề kiến trúc lớn nhất, cần ưu tiên xử lý trước.
- **Không có thử nghiệm/smoke test**: không có test nào verify cleaning pipeline, mapping cột, hay số dòng 202.739 — `assert` cứng trong script SQL là "test" duy nhất và lại dễ vỡ. Nên thêm test nhỏ cho `cleaner.explode_multiselect` / `filter_salary_outliers` / `normalize_*` trên dữ liệu giả.
- **Một chuẩn dữ liệu nhưng nhiều nơi tính lại**: `experience_group`, `remote_work`/`EdLevel` normalization được chạy lại nhiều lần trên cùng df (main, cache, sql, notebook) — tăng chi phí và rủi ro lệch.
- **Tiếng Việt & mã hóa**: 6 file trong `src/`/`scripts/` bắt đầu bằng BOM, 1 comment đã mojibake (`survey_loader.py:23`) — vi phạm `.clinerules:5`; cần kiểm tra lại toàn bộ chuỗi hiển thị trước khi commit.

---

*Kết thúc review. Toàn bộ nội dung chỉ ghi vào `docs/REVIEW.md`; không sửa bất kỳ file nào khác trong project.*

