#!/usr/bin/env python3
"""
Jitter analyses for Music-SDTB physical-onsets long-shape tables.
Given TAG ("expy" or "psychopy"), this script produces:
1) Signed jitter figure (violin + legend + summary table)
2) Absolute jitter figure (violin + legend + summary table)
3) RTF table:
   - Standard Error >{THRESHOLD_MS}ms by Group
4) RTF table:
   - Standard Internal Difference >{THRESHOLD_MS}ms by Group
5) RTF table:
   - SOA Error >{THRESHOLD_MS}ms Grouped by Standard
6) RTF table:
   - SOA1-SOA2 Difference >{THRESHOLD_MS}ms

author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Creation: 10th of December 2025
Last Update: July 2026

Compatibility: Python 3.10.16
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D


# =============================================================================
# Configuration
# =============================================================================
TAG = ["expy1", "expy2"]   # e.g. "expy1" or ["expy1", "expy2"]
OUT_TAG = "expy"  # required when len(TAG) > 1

INPUT_FILES = {
    "expy1": "curated_data_summer2025/encoding_expy_june2025_long.tsv",
    "expy2": "curated_data_summer2025/encoding_expy_july2025_long.tsv",
    "psychopy": "curated_data_nov2025/encoding_psychopy.tsv",
    "psychopy_st": "curated_data_feb2026/encoding_long_st.tsv",
    "psychopy_ptb": "curated_data_feb2026/encoding_long_ptb.tsv",
    "psychopy_st_buf01": "curated_data_april2026/encoding_long_st_buf-01.tsv",
    "psychopy_ptb_buf01": "curated_data_april2026/encoding_long_ptb_buf-01.tsv",
    "psychopy_st_buf05": "curated_data_april2026/encoding_long_st_buf-05.tsv",
    "psychopy_ptb_buf05": "curated_data_april2026/encoding_long_ptb_buf-05.tsv",
    "psychopy_st_buf08": "curated_data_april2026/encoding_long_st_buf-08.tsv",
    "psychopy_ptb_buf08": "curated_data_april2026/encoding_long_ptb_buf-08.tsv",
}

OUT_DIR = Path("jitter_results_summer2025")  # RTF tables and PNG figures

TOP_AXES = 0.86
THRESHOLD_MS = 20

STANDARD_LABELS = {"standard"}
SOA_LABELS = {"soa1", "soa2"}
MEAS_COL = "measurement"

REQ_COLS_COMMON = [
    "task",
    "subject",
    "modality",
    "condition",
    "trial",
    "theoretical_durations",
    "duration_type",
    "durations",
    "error",
]

# RTF (Letter portrait, margins)
RTF_PAGE_W_TWIPS = 12240
RTF_PAGE_H_TWIPS = 15840
RTF_MARGIN_TWIPS = 1080

# RTF font sizes (half-points)
RTF_FONT_FS_BODY = 24
RTF_FONT_FS_TABLE = 20
RTF_FONT_FS_TITLE = 32


# =============================================================================
# Helpers
# =============================================================================
def require_cols(df_in: pd.DataFrame, cols: List[str], src: str) -> None:
    """Raise if required columns are missing."""
    missing = [c for c in cols if c not in df_in.columns]
    if missing:
        raise ValueError(f"Missing required columns in {src}: {missing}")


def make_summary_signed(df_in: pd.DataFrame) -> pd.DataFrame:
    """Signed error summary by task and modality."""
    out = (
        df_in.groupby(["task", "modality"])["error"]
        .agg(mean="mean", std="std", min_error="min", max_error="max")
        .reset_index()
    )
    return out.round(3)


def make_summary_abs(df_in: pd.DataFrame) -> pd.DataFrame:
    """Absolute error summary by task and modality."""
    tmp = df_in.copy()
    tmp["abs_error"] = tmp["error"].abs()
    out = (
        tmp.groupby(["task", "modality"])["abs_error"]
        .agg(mean="mean", std="std", abs_max="max")
        .reset_index()
    )
    return out.round(3)


def plot_with_table(
    df_in: pd.DataFrame,
    y_col: str,
    y_label: str,
    summary_df: pd.DataFrame,
    outpath: Path,
    description: str,
    top_axes: float,
) -> None:
    """Create two violins + legend row + summary table row."""
    sns.set(style="whitegrid")
    fig = plt.figure(figsize=(11, 6))

    fig.text(
        0.5,
        0.985,
        description,
        ha="center",
        va="top",
        fontsize=10,
        wrap=True,
    )

    gs = GridSpec(
        nrows=3,
        ncols=2,
        height_ratios=[3.0, 0.35, 1.15],
        hspace=0.35,
        wspace=0.3,
        figure=fig,
    )

    ax_left = fig.add_subplot(gs[0, 0])
    ax_right = fig.add_subplot(gs[0, 1])
    ax_leg = fig.add_subplot(gs[1, :])
    ax_tab = fig.add_subplot(gs[2, :])

    ax_leg.axis("off")
    ax_tab.axis("off")

    modalities = sorted(df_in["modality"].dropna().unique())
    axes = [ax_left, ax_right]

    for ax, mod in zip(axes, modalities):
        sub = df_in[df_in["modality"] == mod]
        task_order = sorted(sub["task"].dropna().unique())
        sns.violinplot(
            data=sub,
            x="task",
            y=y_col,
            order=task_order,
            inner="box",
            cut=0,
            ax=ax,
        )

        # Place markers at the same integer positions seaborn uses for
        # `order`, avoiding any dependence on tick-label text/order.
        x_pos = list(range(len(task_order)))
        means = sub.groupby("task")[y_col].mean().reindex(task_order)
        meds = sub.groupby("task")[y_col].median().reindex(task_order)

        ax.scatter(x_pos, means.values, marker="D", s=45, color="black",
                   zorder=3)
        ax.scatter(
            x_pos,
            meds.values,
            marker="s",
            s=40,
            facecolor="white",
            edgecolor="black",
            linewidth=0.6,
            zorder=4,
        )

        ax.set_title(f"Modality: {mod}")
        ax.set_xlabel("Task")
        ax.set_ylabel(y_label if ax is ax_left else "")

    if len(modalities) == 2:
        ymin = min(ax_left.get_ylim()[0], ax_right.get_ylim()[0])
        ymax = max(ax_left.get_ylim()[1], ax_right.get_ylim()[1])
        ax_left.set_ylim(ymin, ymax)
        ax_right.set_ylim(ymin, ymax)
    else:
        ax_right.axis("off")

    legend_items = [
        Line2D([0], [0], marker="D", linestyle="None", color="black",
               label="Mean"),
        Line2D([0], [0], marker="s", linestyle="None",
               markerfacecolor="white", markeredgecolor="black",
               label="Median"),
    ]
    ax_leg.legend(handles=legend_items, loc="center", ncol=2, frameon=False)

    table = ax_tab.table(
        cellText=summary_df.values,
        colLabels=summary_df.columns,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.2)

    fig.subplots_adjust(top=top_axes, bottom=0.08)
    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _ensure_measurement(df_in: pd.DataFrame) -> pd.DataFrame:
    """Ensure measurement exists; if not, create it as 1."""
    df_work = df_in.copy()
    if MEAS_COL not in df_work.columns:
        df_work[MEAS_COL] = 1
    return df_work


def _standard_only(df_in: pd.DataFrame) -> pd.DataFrame:
    """Return only STANDARD rows (duration_type == 'standard')."""
    return df_in[
        df_in["duration_type"].astype(str).str.strip().str.lower().isin(
            STANDARD_LABELS
        )
    ].copy()


def _soa_only(df_in: pd.DataFrame) -> pd.DataFrame:
    """Return only SOA rows (duration_type in {'soa1', 'soa2'})."""
    return df_in[
        df_in["duration_type"].astype(str).str.strip().str.lower().isin(
            SOA_LABELS
        )
    ].copy()


def standard_error_threshold_table(
    df_in: pd.DataFrame,
    threshold_ms: float,
) -> pd.DataFrame:
    """
    Sequences with any STANDARD having |error| > threshold.
    Denominator excludes sequences where STANDARD error is all-NaN.
    """
    df_work = _ensure_measurement(df_in)
    df_std = _standard_only(df_work)

    if df_std.empty:
        raise ValueError("No STANDARD rows found. Check duration_type.")

    df_std["theoretical_durations"] = pd.to_numeric(
        df_std["theoretical_durations"],
        errors="coerce",
    )

    seq_cols = [
        "task",
        "modality",
        "condition",
        "subject",
        "trial",
        MEAS_COL,
    ]

    def all_nan(series: pd.Series) -> bool:
        return series.isna().all()

    def max_abs_ignore_nan(series: pd.Series) -> float:
        arr = series.to_numpy(dtype=float)
        return float(np.nanmax(np.abs(arr)))

    seq = (
        df_std.groupby(seq_cols)
        .agg(
            std_val=("theoretical_durations", "first"),
            all_nan_error=("error", all_nan),
            max_abs_error=("error", max_abs_ignore_nan),
        )
        .reset_index()
    )

    seq = seq[~seq["all_nan_error"]].copy()
    seq["exceeds"] = seq["max_abs_error"] > float(threshold_ms)

    grp = ["task", "modality", "condition", "std_val"]
    out = (
        seq.groupby(grp)["exceeds"]
        .agg(n_trials="size", n_exceeds="sum")
        .reset_index()
    )

    thr_int = int(threshold_ms)
    n_col = f"N Error > {thr_int}ms"
    out[n_col] = (
        out["n_exceeds"].astype(int).astype(str)
        + " / "
        + out["n_trials"].astype(int).astype(str)
    )

    pct = 100.0 * out["n_exceeds"] / out["n_trials"]
    out["Percent (%)"] = pct.round(2).map(lambda x: f"{x:.2f}%")

    out = out.rename(
        columns={
            "task": "Task",
            "modality": "Modality",
            "condition": "Condition",
            "std_val": "Standard",
        }
    )

    out = out[
        ["Task", "Modality", "Condition", "Standard", n_col, "Percent (%)"]
    ].sort_values(["Task", "Modality", "Condition", "Standard"])

    return out


def standard_internal_diff_table(
    df_in: pd.DataFrame,
    threshold_ms: float,
) -> pd.DataFrame:
    """
    Sequences where standard durations differ internally by > threshold.
    Metric: max(standard durations) - min(standard durations).
    Denominator excludes sequences where standard durations are all-NaN.
    """
    df_work = _ensure_measurement(df_in)
    df_std = _standard_only(df_work)

    if df_std.empty:
        raise ValueError("No STANDARD rows found. Check duration_type.")

    df_std["theoretical_durations"] = pd.to_numeric(
        df_std["theoretical_durations"],
        errors="coerce",
    )
    df_std["durations"] = pd.to_numeric(df_std["durations"], errors="coerce")

    seq_cols = [
        "task",
        "modality",
        "condition",
        "subject",
        "trial",
        MEAS_COL,
    ]

    def all_nan(series: pd.Series) -> bool:
        return series.isna().all()

    def range_ignore_nan(series: pd.Series) -> float:
        arr = series.to_numpy(dtype=float)
        if np.isnan(arr).all():
            return float("nan")
        return float(np.nanmax(arr) - np.nanmin(arr))

    seq = (
        df_std.groupby(seq_cols)
        .agg(
            std_val=("theoretical_durations", "first"),
            all_nan_dur=("durations", all_nan),
            std_range=("durations", range_ignore_nan),
        )
        .reset_index()
    )

    seq = seq[~seq["all_nan_dur"]].copy()
    seq["exceeds"] = seq["std_range"] > float(threshold_ms)

    grp = ["task", "modality", "condition", "std_val"]
    out = (
        seq.groupby(grp)["exceeds"]
        .agg(n_trials="size", n_exceeds="sum")
        .reset_index()
    )

    thr_int = int(threshold_ms)
    n_col = f"N Diff > {thr_int}ms"
    out[n_col] = (
        out["n_exceeds"].astype(int).astype(str)
        + " / "
        + out["n_trials"].astype(int).astype(str)
    )

    pct = 100.0 * out["n_exceeds"] / out["n_trials"]
    out["Percent (%)"] = pct.round(2).map(lambda x: f"{x:.2f}%")

    out = out.rename(
        columns={
            "task": "Task",
            "modality": "Modality",
            "condition": "Condition",
            "std_val": "Standard",
        }
    )

    out = out[
        ["Task", "Modality", "Condition", "Standard", n_col, "Percent (%)"]
    ].sort_values(["Task", "Modality", "Condition", "Standard"])

    return out


def soa_error_threshold_table(
    df_in: pd.DataFrame,
    threshold_ms: float,
) -> pd.DataFrame:
    """
    Sequences with any SOA (SOA1 or SOA2) having |error| > threshold.
    Grouped by Standard (theoretical standard duration from STANDARD rows).
    Denominator excludes sequences where SOA error is all-NaN.
    """
    df_work = _ensure_measurement(df_in)

    df_std = _standard_only(df_work)
    if df_std.empty:
        raise ValueError("No STANDARD rows found. Check duration_type.")
    df_std["theoretical_durations"] = pd.to_numeric(
        df_std["theoretical_durations"],
        errors="coerce",
    )

    df_soa = _soa_only(df_work)
    if df_soa.empty:
        raise ValueError("No SOA rows found. Check duration_type.")

    seq_cols = [
        "task",
        "modality",
        "condition",
        "subject",
        "trial",
        MEAS_COL,
    ]

    std_map = (
        df_std.groupby(seq_cols)["theoretical_durations"]
        .first()
        .rename("Standard")
        .reset_index()
    )

    df_soa = df_soa.copy()
    df_soa["error"] = pd.to_numeric(df_soa["error"], errors="coerce")
    df_soa = df_soa.merge(std_map, on=seq_cols, how="left")

    def all_nan(series: pd.Series) -> bool:
        return series.isna().all()

    def max_abs_ignore_nan(series: pd.Series) -> float:
        arr = series.to_numpy(dtype=float)
        return float(np.nanmax(np.abs(arr)))

    seq = (
        df_soa.groupby(seq_cols + ["Standard"])
        .agg(
            all_nan_soa=("error", all_nan),
            max_abs_soa=("error", max_abs_ignore_nan),
        )
        .reset_index()
    )

    seq = seq[~seq["all_nan_soa"]].copy()
    seq = seq[seq["Standard"].notna()].copy()
    seq["exceeds"] = seq["max_abs_soa"] > float(threshold_ms)

    grp = ["task", "modality", "condition", "Standard"]
    out = (
        seq.groupby(grp)["exceeds"]
        .agg(n_trials="size", n_exceeds="sum")
        .reset_index()
    )

    thr_int = int(threshold_ms)
    n_col = f"N SOA Error > {thr_int}ms"
    out[n_col] = (
        out["n_exceeds"].astype(int).astype(str)
        + " / "
        + out["n_trials"].astype(int).astype(str)
    )

    pct = 100.0 * out["n_exceeds"] / out["n_trials"]
    out["Percent (%)"] = pct.round(2).map(lambda x: f"{x:.2f}%")

    out = out.rename(
        columns={
            "task": "Task",
            "modality": "Modality",
            "condition": "Condition",
        }
    )

    out = out[
        ["Task", "Modality", "Condition", "Standard", n_col, "Percent (%)"]
    ].sort_values(["Task", "Modality", "Condition", "Standard"])

    return out


def soa_pair_diff_table(
    df_in: pd.DataFrame,
    threshold_ms: float,
) -> pd.DataFrame:
    """
    Sequences where |SOA1 - SOA2| > threshold.
    This does not depend on SOA error relative to the standard.
    Note: Expected to hold for interval conditions, but beat trials are
    included as requested.
    """
    df_work = _ensure_measurement(df_in)

    df_std = _standard_only(df_work)
    if df_std.empty:
        raise ValueError("No STANDARD rows found. Check duration_type.")
    df_std["theoretical_durations"] = pd.to_numeric(
        df_std["theoretical_durations"],
        errors="coerce",
    )

    df_soa = _soa_only(df_work)
    if df_soa.empty:
        raise ValueError("No SOA rows found. Check duration_type.")
    df_soa["durations"] = pd.to_numeric(df_soa["durations"], errors="coerce")

    seq_cols = [
        "task",
        "modality",
        "condition",
        "subject",
        "trial",
        MEAS_COL,
    ]

    std_map = (
        df_std.groupby(seq_cols)["theoretical_durations"]
        .first()
        .rename("Standard")
        .reset_index()
    )

    soa_wide = (
        df_soa.pivot_table(
            index=seq_cols,
            columns="duration_type",
            values="durations",
            aggfunc="first",
        )
        .reset_index()
    )

    if "soa1" not in soa_wide.columns or "soa2" not in soa_wide.columns:
        raise ValueError("Both SOA1 and SOA2 must be present per sequence.")

    soa_wide["soa_diff"] = (soa_wide["soa1"] - soa_wide["soa2"]).abs()
    soa_wide = soa_wide.merge(std_map, on=seq_cols, how="left")
    soa_wide = soa_wide.dropna(subset=["soa_diff", "Standard"])

    soa_wide["exceeds"] = soa_wide["soa_diff"] > float(threshold_ms)

    grp = ["task", "modality", "condition", "Standard"]
    out = (
        soa_wide.groupby(grp)["exceeds"]
        .agg(n_trials="size", n_exceeds="sum")
        .reset_index()
    )

    thr_int = int(threshold_ms)
    n_col = f"N |SOA1-SOA2| > {thr_int}ms"
    out[n_col] = (
        out["n_exceeds"].astype(int).astype(str)
        + " / "
        + out["n_trials"].astype(int).astype(str)
    )

    pct = 100.0 * out["n_exceeds"] / out["n_trials"]
    out["Percent (%)"] = pct.round(2).map(lambda x: f"{x:.2f}%")

    out = out.rename(
        columns={
            "task": "Task",
            "modality": "Modality",
            "condition": "Condition",
        }
    )

    out = out[
        ["Task", "Modality", "Condition", "Standard", n_col, "Percent (%)"]
    ].sort_values(["Task", "Modality", "Condition", "Standard"])

    return out


def compute_col_widths_twips(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    page_w_twips: int,
    margin_twips: int,
    min_w: Dict[int, int],
    max_w: Dict[int, int],
    twips_per_char: int = 120,
    cell_pad_twips: int = 220,
) -> List[int]:
    """
    Compute table column widths in twips based on string lengths.
    This aims to keep most cells on one line, within page width.
    """
    n_cols = len(headers)
    usable = page_w_twips - 2 * margin_twips
    usable = max(usable, 4000)

    max_lens = [len(str(h)) for h in headers]
    for row in rows:
        for j in range(n_cols):
            max_lens[j] = max(max_lens[j], len(str(row[j])))

    desired: List[int] = []
    for j, ln in enumerate(max_lens):
        w = ln * twips_per_char + cell_pad_twips
        if j in min_w:
            w = max(w, min_w[j])
        if j in max_w:
            w = min(w, max_w[j])
        desired.append(int(w))

    total = sum(desired)
    if total <= usable:
        return desired

    scale = usable / total
    scaled = [max(400, int(w * scale)) for w in desired]

    for j in range(n_cols):
        if j in min_w and scaled[j] < min_w[j]:
            scaled[j] = min_w[j]

    overflow = sum(scaled) - usable
    if overflow > 0:
        order = sorted(range(n_cols), key=lambda k: scaled[k], reverse=True)
        idx = 0
        while overflow > 0 and idx < len(order):
            j = order[idx]
            floor = min_w.get(j, 400)
            reducible = scaled[j] - floor
            if reducible > 0:
                delta = min(reducible, overflow)
                scaled[j] -= delta
                overflow -= delta
            else:
                idx += 1

    return scaled


def rtf_escape(text: str) -> str:
    """Escape special characters for RTF."""
    return (
        str(text)
        .replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
    )


def rtf_write_centered_paragraph(
    text: str,
    font_fs: int,
    bold: bool = False,
    no_wrap: bool = True,
) -> str:
    """Create a centered RTF paragraph with anti-wrapping hints."""
    b_on = r"\b" if bold else ""
    b_off = r"\b0" if bold else ""
    keep = r"\keepn" if no_wrap else ""
    nowid = r"\nowidctlpar" if no_wrap else ""
    return (
        rf"\qc{keep}{nowid} {b_on}\fs{font_fs} {rtf_escape(text)}"
        rf"{b_off}\fs{RTF_FONT_FS_BODY}\par"
    )


def write_rtf_table_report(
    outpath: Path,
    title: str,
    explanation: str,
    headers: List[str],
    rows: List[List[str]],
) -> None:
    """Write an RTF report with title, explanation, and one table."""
    min_w = {0: 900, 1: 1100, 2: 1300, 3: 1300, 4: 1700, 5: 900}
    max_w = {0: 1800, 1: 2000, 2: 2600, 3: 2000, 4: 3200, 5: 1400}

    col_widths = compute_col_widths_twips(
        headers=headers,
        rows=rows,
        page_w_twips=RTF_PAGE_W_TWIPS,
        margin_twips=RTF_MARGIN_TWIPS,
        min_w=min_w,
        max_w=max_w,
        twips_per_char=120,
        cell_pad_twips=220,
    )

    def table_row(cells: List[str], header: bool = False) -> str:
        row = r"\trowd\trgaph108\trleft0"
        xpos = 0
        for width in col_widths:
            xpos += width
            row += rf"\cellx{xpos}"
        for cell in cells:
            if header:
                row += (
                    rf"\intbl\b\fs{RTF_FONT_FS_TABLE} {rtf_escape(cell)}"
                    r"\b0\cell"
                )
            else:
                row += rf"\intbl\fs{RTF_FONT_FS_TABLE} {rtf_escape(cell)}\cell"
        row += r"\row"
        return row

    lines: List[str] = []
    lines.append(r"{\rtf1\ansi\deff0")
    lines.append(r"{\fonttbl{\f0\fswiss Arial;}}")
    lines.append(rf"\paperw{RTF_PAGE_W_TWIPS}\paperh{RTF_PAGE_H_TWIPS}")
    lines.append(
        rf"\margl{RTF_MARGIN_TWIPS}\margr{RTF_MARGIN_TWIPS}"
        rf"\margt{RTF_MARGIN_TWIPS}\margb{RTF_MARGIN_TWIPS}"
    )
    lines.append(rf"\f0\fs{RTF_FONT_FS_BODY}")

    lines.append(
        rtf_write_centered_paragraph(
            text=title,
            font_fs=RTF_FONT_FS_TITLE,
            bold=True,
            no_wrap=True,
        )
    )
    lines.append(r"\par")
    lines.append(rf"{rtf_escape(explanation)}\par")
    lines.append(r"\par")

    lines.append(table_row(headers, header=True))
    for row in rows:
        lines.append(table_row(row, header=False))

    lines.append("}")
    outpath.write_text("\n".join(lines), encoding="utf-8")


def table_df_to_rtf_rows(df_in: pd.DataFrame) -> List[List[str]]:
    """Convert a DataFrame into an RTF row list (strings only)."""
    rows: List[List[str]] = []
    for _, r in df_in.iterrows():
        rows.append([str(v) for v in r.tolist()])
    return rows


def _stack_with_measurement_offset(
    dfs_in: Sequence[pd.DataFrame],
) -> pd.DataFrame:
    """Stack dataframes and offset repeated measurements across files.

    Each file is shifted by a single constant so that its measurement
    indices start above the maximum measurement of all previously stacked
    files. This keeps the measurement ranges of different files disjoint
    (so the same sequence recorded in two files is treated as separate
    measurements) while preserving the structure within each playback:
    all rows of a given (subject, trial, measurement) -- including the two
    standard durations of a beat sequence -- keep the same measurement and
    therefore stay in the same downstream group.

    Note: the previous per-row offset, accumulated over a key that several
    rows of one playback shared, split those rows into different
    measurements and is replaced here.
    """
    stacked: List[pd.DataFrame] = []
    base = 0

    for df_one in dfs_in:
        df_one = _ensure_measurement(df_one).copy()
        df_one[MEAS_COL] = (
            pd.to_numeric(df_one[MEAS_COL], errors="coerce")
            .fillna(1)
            .astype(int)
            + base
        )
        base = int(df_one[MEAS_COL].max())  # next file starts above this max
        stacked.append(df_one)

    return pd.concat(stacked, ignore_index=True)


def load_input_data(
    tag_in: str | Sequence[str],
    out_tag_in: str | None = None,
) -> tuple[pd.DataFrame, str]:
    """Load one file or stack multiple files with adjusted measurement."""
    if isinstance(tag_in, str):
        tags = [tag_in]
    else:
        tags = list(tag_in)

    if not tags:
        raise ValueError("TAG cannot be empty.")

    invalid = [tag for tag in tags if tag not in INPUT_FILES]
    if invalid:
        raise ValueError(f"Unknown TAG(s): {invalid}")

    if len(tags) > 1:
        if not out_tag_in or not str(out_tag_in).strip():
            raise ValueError("When len(TAG) > 1, you must provide OUT_TAG.")
        dfs = []
        for tag in tags:
            in_path = INPUT_FILES[tag]
            df_one = pd.read_csv(in_path, sep="\t")
            require_cols(df_one, REQ_COLS_COMMON, in_path)
            dfs.append(df_one)
        return _stack_with_measurement_offset(dfs), str(out_tag_in).strip()

    in_path = INPUT_FILES[tags[0]]
    df = pd.read_csv(in_path, sep="\t")
    require_cols(df, REQ_COLS_COMMON, in_path)
    return df, tags[0]


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    """Run the full jitter analysis for the configured TAG."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df, tag_label = load_input_data(TAG, OUT_TAG)

    thr_int = int(THRESHOLD_MS)

    # -------------------------------------------------------------------------
    # Figures
    # -------------------------------------------------------------------------
    signed = make_summary_signed(df).rename(
        columns={
            "mean": "Mean error (ms)",
            "std": "SD (ms)",
            "min_error": "Min error (ms)",
            "max_error": "Max error (ms)",
        }
    )

    plot_with_table(
        df_in=df,
        y_col="error",
        y_label="Error (ms)",
        summary_df=signed,
        outpath=OUT_DIR / f"jitter_figures_{tag_label}_signed.png",
        description=(
            "Signed temporal error of real Standard vs programmed Standard."
        ),
        top_axes=TOP_AXES,
    )

    df_abs = df.copy()
    df_abs["abs_error"] = df_abs["error"].abs()

    abs_sum = make_summary_abs(df_abs).rename(
        columns={
            "mean": "Mean |error| (ms)",
            "std": "SD (ms)",
            "abs_max": "Max |error| (ms)",
        }
    )

    plot_with_table(
        df_in=df_abs,
        y_col="abs_error",
        y_label="|Error| (ms)",
        summary_df=abs_sum,
        outpath=OUT_DIR / f"jitter_figures_{tag_label}_abs.png",
        description=(
            "Absolute temporal error (|error|), summarizing the magnitude of "
            "timing deviations of Standards irrespective of direction."
        ),
        top_axes=TOP_AXES,
    )

    # -------------------------------------------------------------------------
    # RTF 1: Standard error
    # -------------------------------------------------------------------------
    tbl_std_err = standard_error_threshold_table(df_in=df, threshold_ms=THRESHOLD_MS)
    title_std_err = f"Standard Error >{thr_int}ms by Group"
    expl_std_err = (
        "The percentage of sequences where there is at least one standard "
        f"with an error bigger than {thr_int}ms."
    )
    rtf_std_err = OUT_DIR / f"standard_error_{tag_label}_{thr_int}ms.rtf"
    write_rtf_table_report(
        outpath=rtf_std_err,
        title=title_std_err,
        explanation=expl_std_err,
        headers=tbl_std_err.columns.tolist(),
        rows=table_df_to_rtf_rows(tbl_std_err),
    )

    # -------------------------------------------------------------------------
    # RTF 2: Standard internal difference
    # -------------------------------------------------------------------------
    tbl_int = standard_internal_diff_table(df_in=df, threshold_ms=THRESHOLD_MS)
    title_int = f"Standard Internal Difference >{thr_int}ms by Group"
    expl_int = (
        "Trials where standard durations differ by more than "
        f"{thr_int}ms internally, regardless of their error relative to the "
        "programmed standard."
    )
    rtf_int = OUT_DIR / f"standard_internal_diff_{tag_label}_{thr_int}ms.rtf"
    write_rtf_table_report(
        outpath=rtf_int,
        title=title_int,
        explanation=expl_int,
        headers=tbl_int.columns.tolist(),
        rows=table_df_to_rtf_rows(tbl_int),
    )

    # -------------------------------------------------------------------------
    # RTF 3: SOA error grouped by Standard
    # -------------------------------------------------------------------------
    tbl_soa = soa_error_threshold_table(df_in=df, threshold_ms=THRESHOLD_MS)
    title_soa = f"SOA Error >{thr_int}ms Grouped by Standard"
    expl_soa = (
        "Trials where there is at least one SOA (SOA1 or SOA2) with an error "
        f"bigger than {thr_int}ms."
    )
    rtf_soa = OUT_DIR / f"soa_error_{tag_label}_{thr_int}ms.rtf"
    write_rtf_table_report(
        outpath=rtf_soa,
        title=title_soa,
        explanation=expl_soa,
        headers=tbl_soa.columns.tolist(),
        rows=table_df_to_rtf_rows(tbl_soa),
    )

    # -------------------------------------------------------------------------
    # RTF 4: SOA1-SOA2 difference (ASCII hyphen, include beat trials)
    # -------------------------------------------------------------------------
    tbl_soa_diff = soa_pair_diff_table(df_in=df, threshold_ms=THRESHOLD_MS)
    title_soa_diff = f"SOA1-SOA2 Difference >{thr_int}ms"
    expl_soa_diff = (
        "Trials where difference between SOAs is bigger than "
        f"{thr_int}ms, regardless the error of each SOA relative to their "
        "Standard. Note: this should be the case for all interval conditions. "
        "In most of the cases, the programmed SOAs allowed for differences "
        "bigger than 300ms on average, but for one ntfd auditory interval "
        "condition this difference was 34ms. With the jittering, this "
        "difference may become less than 20ms."
    )
    rtf_soa_diff = OUT_DIR / f"soa1_soa2_diff_{tag_label}_{thr_int}ms.rtf"
    write_rtf_table_report(
        outpath=rtf_soa_diff,
        title=title_soa_diff,
        explanation=expl_soa_diff,
        headers=tbl_soa_diff.columns.tolist(),
        rows=table_df_to_rtf_rows(tbl_soa_diff),
    )

    print("\nSaved outputs:")
    print(f"- {rtf_std_err}")
    print(f"- {rtf_int}")
    print(f"- {rtf_soa}")
    print(f"- {rtf_soa_diff}")


if __name__ == "__main__":
    main()