"""Data cleaning utilities for survey DataFrames."""

import pandas as pd


_CATEGORICAL_COLS = [
    "Age",
    "Country",
    "DevType",
    "EdLevel",
    "Employment",
    "MainBranch",
    "OrgSize",
    "SOAccount",
    "SOComm",
    "SOPartFreq",
    "SOVisitFreq",
    "remote_work",
]

_MULTISELECT_COLS = [
    "languages_used",
    "databases_used",
    "webframes_used",
    "languages_wanted",
]


REMOTE_WORK_GROUPS = {
    "All or almost all the time (I'm full-time remote)": "Toàn thời gian từ xa",
    "Fully remote": "Toàn thời gian từ xa",
    "Remote": "Toàn thời gian từ xa",
    "More than half, but not all, the time": "Hybrid",
    "About half the time": "Hybrid",
    "Less than half the time, but at least one day each week": "Hybrid",
    "Hybrid (some remote, some in-person)": "Hybrid",
    "Hybrid (some in-person, leans heavy to flexibility)": "Hybrid",
    "Hybrid (some remote, leans heavy to in-person)": "Hybrid",
    "A few days each month": "Hầu như tại văn phòng",
    "Less than once per month / Never": "Hầu như tại văn phòng",
    "Full in-person": "Hầu như tại văn phòng",
    "In-person": "Hầu như tại văn phòng",
    "It's complicated": "Khác/linh hoạt",
    "Your choice (very flexible, you can come in when you want or just as needed)": "Khác/linh hoạt",
    "Không trả lời": "Không trả lời",
}


def explode_multiselect(df: pd.DataFrame, column: str, sep: str = ';') -> pd.DataFrame:
    """
    Tách 1 cột chứa nhiều giá trị nối bằng dấu ';' thành nhiều dòng (long format),
    mỗi dòng 1 giá trị. Dùng cho các cột như languages_used, databases_used,
    webframes_used. Giữ nguyên các cột khác, chỉ explode cột được chỉ định.
    Cần xử lý: giá trị NaN (không explode ra dòng rỗng), khoảng trắng thừa
    quanh dấu ';'.

    Args:
        df: DataFrame đầu vào (ví dụ: đầu ra từ load_all_years()).
        column: Tên cột cần explode (ví dụ: "languages_used").
        sep: Ký tự phân tách các giá trị trong ô, mặc định ';'.

    Returns:
        pd.DataFrame: DataFrame ở dạng long với các cột gốc được giữ lại,
        trừ cột bị explode bị thay thế bằng giá trị từng dòng.
    """
    df = df.copy()

    if column not in df.columns:
        return df

    # Tách theo sep, strip khoảng trắng thừa và loại bỏ giá trị rỗng
    df[column] = (
        df[column]
        .astype("string")
        .str.split(sep)
        .apply(lambda lst: [item.strip() for item in lst] if isinstance(lst, list) else lst)
        .apply(lambda lst: [item for item in lst if isinstance(item, str) and item] if isinstance(lst, list) else lst)
    )

    # explode đơn giản, ignore_index=True tự reset index
    df = df.explode(column, ignore_index=True)

    return df

def filter_salary_outliers(
    df: pd.DataFrame,
    salary_col: str = "salary_usd",
    method: str = "iqr",
) -> pd.DataFrame:
    """
    Lọc bỏ các dòng có giá trị lương phi thực tế (0, âm, hoặc quá lớn do nhập
    sai đơn vị). Hỗ trợ 2 phương pháp: 'iqr' (loại theo khoảng tứ phân vị) và
    'percentile' (loại theo phần trăm cao/thấp nhất, ví dụ 1%-99%). Trả về
    DataFrame đã lọc, giữ nguyên các dòng có salary_col là NaN (không lọc nhầm
    người không trả lời câu hỏi lương).

    Args:
        df: DataFrame đầu vào.
        salary_col: Tên cột lương đã chuẩn hóa, mặc định "salary_usd".
        method: Phương pháp lọc outlier: "iqr" hoặc "percentile".

    Returns:
        pd.DataFrame: DataFrame đã loại bỏ các dòng lương phi thực tế,
        giữ lại NaN.
    """
    df = df.copy()

    if salary_col not in df.columns:
        return df

    keep_mask = pd.Series(True, index=df.index)
    valid_salary = df.loc[df[salary_col].notna(), salary_col]

    if method == "iqr":
        q1 = valid_salary.quantile(0.25)
        q3 = valid_salary.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        keep_mask = df[salary_col].isna() | df[salary_col].between(lower, upper, inclusive="both")
    elif method == "percentile":
        lower = valid_salary.quantile(0.01)
        upper = valid_salary.quantile(0.99)
        keep_mask = df[salary_col].isna() | df[salary_col].between(lower, upper, inclusive="both")
    else:
        raise ValueError(
            f"Phương pháp lọc outlier không hợp lệ: {method}. Chỉ hỗ trợ 'iqr' hoặc 'percentile'."
        )

    df = df.loc[keep_mask].reset_index(drop=True)
    return df


def normalize_remote_work(df: pd.DataFrame, col: str = 'remote_work') -> pd.DataFrame:
    """
    Gộp các giá trị remote_work chi tiết (khác nhau giữa các năm khảo sát)
    thành 4 nhóm chung để so sánh xuyên năm: "Toàn thời gian từ xa", "Hybrid",
    "Hầu như tại văn phòng", "Khác/linh hoạt", "Không trả lời". Giữ lại bản
    chi tiết gốc ở cột `{col}_detail` để phân tích sâu hơn nếu cần, còn cột
    gốc `col` được ghi đè bằng bản đã gộp nhóm.

    Args:
        df: DataFrame đầu vào (sau clean_missing()).
        col: Tên cột remote work cần gộp nhóm, mặc định "remote_work".

    Returns:
        pd.DataFrame: DataFrame có thêm cột {col}_detail (bản gốc) và
        cột col đã được map sang 4 nhóm chung. Giá trị không có trong
        REMOTE_WORK_GROUPS giữ nguyên NaN, không raise lỗi.
    """
    df = df.copy()

    if col not in df.columns:
        return df

    df[f'{col}_detail'] = df[col]
    df[col] = df[col].map(REMOTE_WORK_GROUPS)

    return df


EDLEVEL_GROUPS = {
    "Associate degree": "Associate degree",
    "Associate degree (A.A., A.S., etc.)": "Associate degree",
    "Bachelor's degree (B.A., B.S., B.Eng., etc.)": "Bachelor's degree",
    "Bachelor's degree (BA, BS, B.Eng., etc.)": "Bachelor's degree",
    "Master's degree (M.A., M.S., M.Eng., MBA, etc.)": "Master's degree",
    "Master's degree (MA, MS, M.Eng., MBA, etc.)": "Master's degree",
    "Other doctoral degree (Ph.D, Ed.D., etc.)": "Other doctoral degree",
    "Other doctoral degree (Ph.D., Ed.D., etc.)": "Other doctoral degree",
    "Professional degree (JD, MD, Ph.D, Ed.D, etc.)": "Professional degree",
    "Professional degree (JD, MD, etc.)": "Professional degree",
    "Other (please specify):": "Khác",
    "Something else": "Khác",
    "I never completed any formal education": "Chưa qua giáo dục chính quy",
    "Primary/elementary school": "Tiểu học",
    "Secondary school (e.g. American high school, German Realschule or Gymnasium, etc.)": "Trung học",
    "Some college/university study without earning a degree": "Học ĐH chưa có bằng",
    "Không trả lời": "Không trả lời",
}


def normalize_edlevel(df: pd.DataFrame, col: str = "EdLevel") -> pd.DataFrame:
    """
    Gộp các giá trị EdLevel chi tiết (khác nhau giữa các năm khảo sát)
    thành các nhóm chung. Giữ lại bản chi tiết gốc ở cột `{col}_detail`,
    cột `col` được ghi đè bằng bản đã gộp nhóm.

    Args:
        df: DataFrame đầu vào.
        col: Tên cột trình độ học vấn, mặc định "EdLevel".

    Returns:
        pd.DataFrame: DataFrame có thêm cột {col}_detail và cột {col}
        đã map sang nhóm chuẩn. Giá trị không có trong EDLEVEL_GROUPS
        giữ nguyên NaN.
    """
    df = df.copy()

    if col not in df.columns:
        return df

    # Nếu giá trị gốc là dấu nháy đơn in ấn (U+2019) thì chuyển về ASCII
    # để khớp với key trong EDLEVEL_GROUPS
    if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == 'object':
        df[col] = df[col].astype('string').str.replace('’', "'", regex=False)

    df[f"{col}_detail"] = df[col]
    df[col] = df[col].map(EDLEVEL_GROUPS)

    return df


def clean_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Xử lý giá trị thiếu cho các cột chính (13 cột chung + salary_usd). Không
    tự ý điền giá trị cho các cột đa lựa chọn (languages_used, v.v.) vì NaN ở
    đó có nghĩa là "không trả lời", cần giữ nguyên để phân biệt với "trả lời
    rỗng".

    Args:
        df: DataFrame đầu vào (kết quả từ load_all_years() hoặc sau explode).

    Returns:
        pd.DataFrame: DataFrame đã xử lý missing theo từng nhóm cột,
        giữ nguyên cấu trúc và các cột đa lựa chọn.
    """
    df = df.copy()

    for col in _CATEGORICAL_COLS:
        if col in df.columns:
            df[col] = df[col].fillna("Không trả lời")

    years_col = 'YearsCode'
    if years_col in df.columns:
        mapped = df[years_col].replace({
            'Less than 1 year': '0',
            'More than 50 years': '51',
        })
        df[years_col] = pd.to_numeric(mapped, errors='coerce')

    for col in _MULTISELECT_COLS:
        if col in df.columns:
            pass

    return df
