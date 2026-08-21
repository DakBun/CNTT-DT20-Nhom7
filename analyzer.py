"""Analysis utilities for cleaned survey DataFrames."""

import pandas as pd

from src.processing.cleaner import explode_multiselect


# Định nghĩa khoảng kinh nghiệm để phân nhóm YearsCode
_YEARS_CODE_BINS = [0, 2, 5, 10, 20, float("inf")]
_YEARS_CODE_LABELS = ["0-2 năm", "3-5 năm", "6-10 năm", "11-20 năm", "20+"]


# Bước kiểm tra xem cột có tồn tại không
# - Nếu có, tạo nhóm kinh nghiệm bằng pd.cut
# - Nếu thiếu, trả về None để caller biết không thể nhóm
# Giá trị NaN trong YearsCode sẽ thành "Không xác định"
def _bin_years_code(df: pd.DataFrame, years_col: str = "YearsCode") -> pd.Series | None:
    """
    Chuyển cột YearsCode thành nhóm kinh nghiệm bằng pd.cut.

    Args:
        df: DataFrame đầu vào.
        years_col: Tên cột YearsCode, mặc định "YearsCode".

    Returns:
        pd.Series nhóm kinh nghiệm, hoặc None nếu cột không tồn tại.
    """
    if years_col not in df.columns:
        return None

    # Chuyển sang numeric, NaN giữ nguyên
    numeric_years = pd.to_numeric(df[years_col], errors="coerce")

    # Cắt thành nhóm; NaN sẽ thành <NA>
    binned = pd.cut(
        numeric_years,
        bins=_YEARS_CODE_BINS,
        labels=_YEARS_CODE_LABELS,
        include_lowest=True,
    )

    # Điền nhãn cho NaN thành "Không xác định"
    return binned.cat.add_categories(["Không xác định"]).fillna("Không xác định")


def compute_summary(df: pd.DataFrame) -> dict:
    """
    Tổng hợp thống kê mô tả từ DataFrame đã làm sạch.

    Args:
        df: DataFrame đầu vào (kết quả từ load_all_years() hoặc sau
        clean_missing/filter_salary_outliers).

    Returns:
        dict: Từ điển chứa số dòng, số cột, tỷ lệ giá trị thiếu theo cột,
        thống kê lương cơ bản, và phân phối năm khảo sát.
    """
    # Đếm số dòng/cột
    n_rows = len(df)
    n_cols = df.shape[1]

    # Tính tỷ lệ thiếu theo cột
    missing_pct = df.isna().mean().round(3).to_dict()

    # Thống kê lương; nếu cột không tồn tại thì trả dict rỗng
    if "salary_usd" in df.columns:
        salary_stats = df["salary_usd"].describe().to_dict()
    else:
        salary_stats = {}

    # Phân phối năm khảo sát
    if "survey_year" in df.columns:
        year_distribution = df["survey_year"].value_counts().to_dict()
    else:
        year_distribution = {}

    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "missing_pct": missing_pct,
        "salary_stats": salary_stats,
        "year_distribution": year_distribution,
    }


def analyze_salary_by_group(df: pd.DataFrame, group_col: str, salary_col: str = "salary_usd") -> pd.DataFrame:
    """
    Tính lương trung vị theo từng nhóm trong 1 cột phân loại.

    Ví dụ nhóm hợp lệ: EdLevel, DevType, Country, YearsCode (sau khi
    gọi helper _bin_years_code() để tạo nhóm kinh nghiệm).

    Args:
        df: DataFrame đầu vào đã làm sạch.
        group_col: Tên cột nhóm cần phân tích lương.
        salary_col: Tên cột lương chuẩn hóa, mặc định "salary_usd".

    Returns:
        pd.DataFrame: Bảng lương trung vị theo survey_year và group_col,
        kèm số lượng mẫu.
    """
    # Loại bỏ dòng thiếu lương hoặc thiếu nhóm
    grouped = (
        df.dropna(subset=[salary_col, group_col])
          .groupby(["survey_year", group_col])[salary_col]
          .agg(median="median", count="count")
          .reset_index()
          .sort_values(["survey_year", "median"], ascending=[True, False])
    )
    return grouped


def analyze_tech_demand(df: pd.DataFrame, column: str, top_n: int = 15) -> pd.DataFrame:
    """
    Thống kê nhu cầu công nghệ từ cột đã explode dạng long.

    Args:
        df: DataFrame dạng long từ explode_multiselect, ví dụ cột
        `languages_used` đã explode.
        column: Tên cột công nghệ cần phân tích.
        top_n: Số lượng công nghệ hiển thị.

    Returns:
        pd.DataFrame: Bảng xếp hạng công nghệ theo tần suất xuất hiện.
    """
    # Đếm tần suất, loại bỏ NaN
    counts = df[column].dropna().value_counts().head(top_n)

    # Đưa về DataFrame chuẩn
    result = counts.reset_index()
    result.columns = [column, "count"]

    # Tính tỷ lệ phần trăm
    total = len(df[column].dropna())
    result["pct"] = (result["count"] / total * 100).round(1)

    return result


def analyze_remote_work(df: pd.DataFrame, group_col: str | None = None) -> pd.DataFrame:
    """
    Thống kê xu hướng làm việc từ xa theo năm, có thể nhóm thêm theo một cột.

    Args:
        df: DataFrame đầu vào đã làm sạch.
        group_col: Tên cột phân nhóm thêm, ví dụ "OrgSize".

    Returns:
        pd.DataFrame: Bảng tỷ lệ remote_work theo từng nhóm.
    """
    # Nếu không có group_col thì chỉ nhóm theo năm
    keys = ["survey_year"]
    if group_col is not None:
        keys.append(group_col)

    # value_counts normalize=True để ra tỷ lệ phần trăm
    grouped = (
        df.groupby(keys)["remote_work"]
          .value_counts(normalize=True)
          .rename("pct")
          .reset_index()
    )

    # Đổi tỷ lệ sang dạng chuỗi phần trăm nếu muốn dễ đọc
    grouped["pct"] = (grouped["pct"] * 100).round(1)

    return grouped


def compare_vn_vs_global_skills(
    vn_df: pd.DataFrame,
    global_df: pd.DataFrame,
    vn_skill_col: str = "required_skills",
    global_skill_col: str = "languages_used",
) -> pd.DataFrame:
    """
    So sánh tần suất kỹ năng giữa dữ liệu VN và dữ liệu toàn cầu.

    Cả 2 cột đầu vào đều là dạng multi-select ngăn cách bằng ';'.
    Hàm sẽ explode, tính % tần suất từng kỹ năng ở mỗi bên, rồi merge
    và tính chênh lệch (VN - global).

    Args:
        vn_df: DataFrame chứa dữ liệu tin tuyển dụng VN (ví dụ đầu ra từ
            ``load_manual_vn_jobs()``).
        global_df: DataFrame chứa dữ liệu khảo sát toàn cầu đã explode
            hoặc chưa, chỉ cần có cột ``global_skill_col``.
        vn_skill_col: Tên cột kỹ năng trong ``vn_df``, mặc định
            ``required_skills``.
        global_skill_col: Tên cột kỹ năng trong ``global_df``, mặc định
            ``languages_used``.

    Returns:
        pd.DataFrame: Bảng đã sort theo chênh lệch giảm dần, gồm các cột
        ``pct_vn``, ``pct_global``, ``gap``.
    """
    vn_exploded = explode_multiselect(vn_df, vn_skill_col)
    global_exploded = explode_multiselect(global_df, global_skill_col)

    vn_counts = (
        vn_exploded[vn_skill_col]
        .dropna()
        .value_counts(normalize=True)
        .mul(100)
        .rename("pct_vn")
    )
    global_counts = (
        global_exploded[global_skill_col]
        .dropna()
        .value_counts(normalize=True)
        .mul(100)
        .rename("pct_global")
    )

    merged = pd.concat([vn_counts, global_counts], axis=1).fillna(0)
    merged["gap"] = merged["pct_vn"] - merged["pct_global"]
    return merged.sort_values("gap", ascending=False).reset_index().rename(columns={"index": "skill"})
