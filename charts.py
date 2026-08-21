"""Visualization utilities for analysis results."""

import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

from src.config import FIGURES_DIR
from src.processing.cleaner import normalize_edlevel


def plot_salary_trend(
    df: pd.DataFrame,
    output_path: str | Path,
    salary_col: str = "salary_usd",
    group_col: str | None = None,
) -> None:
    """
    Vẽ biểu đồ xu hướng lương trung vị theo năm.

    - Nếu ``group_col`` là ``None``: vẽ 1 đường trung vị chung theo ``survey_year``.
    - Nếu có ``group_col``: vẽ nhiều đường, mỗi nhóm 1 đường, kèm chú giải.

    Args:
        df: DataFrame đầu vào đã làm sạch.
        output_path: Đường dẫn lưu ảnh đầu ra.
                         Ví dụ: ``FIGURES_DIR / "salary_trend.png"``.
        salary_col: Tên cột lương chuẩn hóa.
        group_col: Cột phân nhóm thêm (ví dụ ``DevType``, ``Country``).
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    if group_col is None:
        trend = df.groupby("survey_year")[salary_col].median()
        ax.plot(trend.index, trend.values, marker="o")
    else:
        for key, sub in df.groupby(group_col):
            trend = sub.groupby("survey_year")[salary_col].median()
            ax.plot(trend.index, trend.values, marker="o", label=str(key))
        ax.legend(fontsize=8, loc="best")

    ax.set_xlabel("Năm khảo sát")
    ax.set_ylabel("Lương trung vị (USD)")
    ax.set_title("Xu hướng lương trung vị theo năm")
    fig.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)


def plot_tech_popularity(
    df: pd.DataFrame,
    column: str,
    output_path: str | Path,
    top_n: int = 20,
) -> None:
    """
    Vẽ biểu đồ cột ngang thể hiện top N công nghệ phổ biến nhất.

    Args:
        df: DataFrame dạng long, ví dụ kết quả ``explode_multiselect()``.
        column: Tên cột chứa tên công nghệ đã explode.
        output_path: Đường dẫn lưu ảnh đầu ra.
                         Ví dụ: ``FIGURES_DIR / "tech_popularity.png"``.
        top_n: Số lượng công nghệ hiển thị.
    """
    counts = df[column].dropna().value_counts().head(top_n)
    fig, ax = plt.subplots(figsize=(8, max(4, top_n * 0.3)))
    ax.barh(counts.index[::-1], counts.values[::-1])
    ax.set_xlabel("Số lượt sử dụng")
    ax.set_title(f"Top {top_n} công nghệ phổ biến nhất — {column}")
    fig.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)


def plot_remote_work_distribution(
    df: pd.DataFrame,
    output_path: str | Path,
    remote_col: str = "remote_work",
) -> None:
    """
    Vẽ biểu đồ phân phối hình thức làm việc từ xa theo năm.

    Args:
        df: DataFrame đầu vào đã làm sạch.
        output_path: Đường dẫn lưu ảnh đầu ra.
                         Ví dụ: ``FIGURES_DIR / "remote_work.png"``.
        remote_col: Tên cột biểu thị làm việc từ xa.
    """
    pct = (
        df.groupby("survey_year")[remote_col]
        .value_counts(normalize=True)
        .unstack()
        .fillna(0)
        * 100
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    pct.plot(kind="bar", stacked=True, ax=ax)
    ax.set_xlabel("Năm khảo sát")
    ax.set_ylabel("Tỷ lệ (%)")
    ax.set_title("Phân bố hình thức làm việc từ xa theo năm")
    ax.legend(fontsize=8, bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)


def plot_education_distribution(
    df: pd.DataFrame,
    output_path: str | Path,
    education_col: str = "EdLevel",
) -> None:
    """
    Vẽ biểu đồ phân bố trình độ học vấn theo năm.

    Args:
        df: DataFrame đầu vào đã làm sạch.
        output_path: Đường dẫn lưu ảnh đầu ra.
                         Ví dụ: ``FIGURES_DIR / "education.png"``.
        education_col: Tên cột trình độ học vấn.
    """
    df = normalize_edlevel(df, education_col)

    counts = df.groupby(["survey_year", education_col]).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(9, 5))
    counts.plot(kind="bar", ax=ax)
    ax.set_xlabel("Năm khảo sát")
    ax.set_ylabel("Số lượng phản hồi")
    ax.set_title("Phân bố trình độ học vấn theo năm")
    ax.legend(fontsize=7, bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)


def plot_salary_boxplot(
    df: pd.DataFrame,
    output_path: str | Path,
    group_col: str,
    salary_col: str = "salary_usd",
    top_n: int = 8,
) -> None:
    """
    Vẽ biểu đồ hộp lương theo nhóm, chỉ giữ lại ``top_n`` nhóm đông nhất.

    Args:
        df: DataFrame đầu vào đã làm sạch.
        output_path: Đường dẫn lưu ảnh đầu ra.
                         Ví dụ: ``FIGURES_DIR / "salary_box.png"``.
        group_col: Cột dùng để phân nhóm, ví dụ ``EdLevel``.
        salary_col: Tên cột lương chuẩn hóa.
        top_n: Số nhóm giữ lại dựa trên tần suất xuất hiện.
    """
    df = normalize_edlevel(df, group_col)

    top_groups = df[group_col].value_counts().head(top_n).index
    sub = df[df[group_col].isin(top_groups) & df[salary_col].notna()]

    # Chỉ giữ nhóm thực sự có dữ liệu lương, tránh pandas boxplot lỗi rỗng
    if sub.empty:
        return
    valid_groups = sub[group_col].value_counts().index
    sub = sub[sub[group_col].isin(valid_groups)]

    fig, ax = plt.subplots(figsize=(9, 5))
    sub.boxplot(column=salary_col, by=group_col, ax=ax, rot=35, grid=False)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=35, ha="right")
    ax.set_xlabel(group_col)
    ax.set_ylabel("Lương (USD)")
    ax.set_title(f"Phân phối lương theo {group_col} (top {top_n} nhóm đông nhất)")
    plt.suptitle("")
    fig.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)

