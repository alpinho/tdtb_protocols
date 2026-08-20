#!/usr/bin/env python3
"""
Perception task: detect flips where the real comparison, in column
 'durations', opposes the expected relation based on theoretical
 durations.

A flip occurs when:
    theoretical_relation != real_relation

We compute and save:
- trial-level table with all fields
- overall violation percentage
- violations by deviation magnitude
- violations by modality
- violations by modality × deviation
- violations by theoretical standard
All are written to a single Excel file.

author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Creation: 10th of December 2025
Last Update: April 2026

Compatibility: Python 3.10.16
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd


# =============================================================================
# Configuration
# =============================================================================
TAG = "psychopy_ptb_buf05"  # "expy1", "psychopy", "psychopy_st", or "psychopy_ptb"

INPUT_FILES = {
    "expy1": "curated_data_summer2025/encoding_expy_june2025_long.tsv",
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

OUT_DIR = Path("perception_flips")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MEAS_COL = "measurement"

REQ_COLS = [
    "task",
    "subject",
    "modality",
    "trial",
    "duration_type",
    "theoretical_durations",
    "durations",
]


# =============================================================================
# I/O and validation
# =============================================================================
def load_data(path: str) -> pd.DataFrame:
    """Load a TSV file."""
    return pd.read_csv(path, sep="\t")


def require_cols(df_in: pd.DataFrame, cols: List[str], src: str) -> None:
    """Raise if required columns are missing."""
    missing = [c for c in cols if c not in df_in.columns]
    if missing:
        raise ValueError(f"Missing required columns in {src}: {missing}")


def ensure_measurement(df_in: pd.DataFrame) -> pd.DataFrame:
    """Ensure measurement exists; if not, create it as 1."""
    df_work = df_in.copy()
    if MEAS_COL not in df_work.columns:
        df_work[MEAS_COL] = 1
    return df_work


def seq_cols_base() -> List[str]:
    """
    Base sequence columns.

    Condition is merged back separately so it always exists in trial_level.
    """
    return ["subject", "modality", "trial", MEAS_COL]


def condition_map(df_in: pd.DataFrame, seq_cols: List[str]) -> pd.DataFrame:
    """
    Build a condition mapping per sequence.

    If condition is absent, returns an empty mapping with seq columns.
    """
    if "condition" not in df_in.columns:
        return df_in[seq_cols].drop_duplicates().copy()

    cols = seq_cols + ["condition"]
    out = df_in[cols].drop_duplicates().copy()

    # If any sequence appears with multiple conditions, keep the first.
    out = out.groupby(seq_cols, as_index=False)["condition"].first()
    return out


# =============================================================================
# Core computations
# =============================================================================
def compute_real_standard(df_in: pd.DataFrame, seq_cols: List[str]) -> pd.DataFrame:
    """Mean real standard duration per sequence."""
    std = df_in[df_in["duration_type"] == "standard"].copy()
    std["durations"] = pd.to_numeric(std["durations"], errors="coerce")
    out = std.groupby(seq_cols)["durations"].mean().reset_index()
    return out.rename(columns={"durations": "real_standard"})


def compute_real_comparison(df_in: pd.DataFrame, seq_cols: List[str]) -> pd.DataFrame:
    """Real comparison duration per sequence."""
    cmp_ = df_in[df_in["duration_type"] == "comparison"].copy()
    cmp_["durations"] = pd.to_numeric(cmp_["durations"], errors="coerce")
    keep = seq_cols + ["durations"]
    cmp_ = cmp_[keep]
    return cmp_.rename(columns={"durations": "real_comparison"})


def compute_theoretical(df_in: pd.DataFrame, seq_cols: List[str]) -> pd.DataFrame:
    """Theoretical standard and comparison per sequence."""
    tmp = df_in.copy()
    tmp["theoretical_durations"] = pd.to_numeric(
        tmp["theoretical_durations"],
        errors="coerce",
    )

    th = tmp.pivot_table(
        index=seq_cols,
        columns="duration_type",
        values="theoretical_durations",
        aggfunc="first",
    ).reset_index()

    th.columns.name = None
    return th.rename(
        columns={
            "standard": "theoretical_standard",
            "comparison": "theoretical_comparison",
        }
    )


def compute_deviations(df_in: pd.DataFrame) -> pd.DataFrame:
    """Deviation % and magnitude (rounded absolute %)."""
    out = df_in.copy()
    out["theoretical_deviation"] = (
        (out["theoretical_comparison"] - out["theoretical_standard"])
        / out["theoretical_standard"]
        * 100
    )
    out["deviation_magnitude"] = out["theoretical_deviation"].abs().round()
    return out


def determine_relations(df_in: pd.DataFrame) -> pd.DataFrame:
    """Determine theoretical and real relations."""
    out = df_in.copy()

    out["theoretical_relation"] = out.apply(
        lambda r: "longer"
        if r["theoretical_comparison"] > r["theoretical_standard"]
        else "shorter",
        axis=1,
    )

    out["real_relation"] = out.apply(
        lambda r: "longer"
        if r["real_comparison"] > r["real_standard"]
        else "shorter",
        axis=1,
    )

    return out


def compute_flips(df_in: pd.DataFrame) -> pd.DataFrame:
    """Mark mismatches (relation flips)."""
    out = df_in.copy()
    out["relation_flipped"] = out["theoretical_relation"] != out["real_relation"]
    return out


# =============================================================================
# Summaries and output
# =============================================================================
def build_summaries(
    df_in: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build summary tables."""
    total = int(len(df_in))
    flips = int(df_in["relation_flipped"].sum())
    pct = 100.0 * flips / total if total else 0.0

    overall = pd.DataFrame(
        {
            "total_trials": [total],
            "flips": [flips],
            "pct_flips": [pct],
        }
    )

    by_dev = (
        df_in.groupby("deviation_magnitude")["relation_flipped"]
        .mean()
        .mul(100)
        .reset_index()
        .rename(columns={"relation_flipped": "pct_flips"})
    )

    by_mod = (
        df_in.groupby("modality")["relation_flipped"]
        .mean()
        .mul(100)
        .reset_index()
        .rename(columns={"relation_flipped": "pct_flips"})
    )

    by_mod_dev = (
        df_in.groupby(["modality", "deviation_magnitude"])["relation_flipped"]
        .mean()
        .mul(100)
        .reset_index()
        .rename(columns={"relation_flipped": "pct_flips"})
    )

    by_std = (
        df_in.groupby("theoretical_standard")["relation_flipped"]
        .mean()
        .mul(100)
        .reset_index()
        .rename(columns={"relation_flipped": "pct_flips"})
    )

    return overall, by_dev, by_mod, by_mod_dev, by_std


def save_all_to_excel(
    trial_df: pd.DataFrame,
    overall: pd.DataFrame,
    by_dev: pd.DataFrame,
    by_mod: pd.DataFrame,
    by_mod_dev: pd.DataFrame,
    by_std: pd.DataFrame,
    out_path: Path,
) -> None:
    """Save trial-level data and summaries into one Excel file."""
    with pd.ExcelWriter(out_path) as writer:
        trial_df.to_excel(writer, sheet_name="trial_level", index=False)
        overall.to_excel(writer, sheet_name="overall", index=False)
        by_dev.to_excel(writer, sheet_name="by_deviation", index=False)
        by_mod.to_excel(writer, sheet_name="by_modality", index=False)
        by_mod_dev.to_excel(writer, sheet_name="by_mod_dev", index=False)
        by_std.to_excel(writer, sheet_name="by_theoretical_std", index=False)

    print(f"\nSaved summary workbook: {out_path}")


def print_summaries(
    overall: pd.DataFrame,
    by_dev: pd.DataFrame,
    by_mod: pd.DataFrame,
    by_mod_dev: pd.DataFrame,
    by_std: pd.DataFrame,
) -> None:
    """Print summaries to terminal (compact)."""
    print("\n=== OVERALL FLIPS ===")
    print(overall.to_string(index=False))

    print("\n=== BY DEVIATION MAGNITUDE ===")
    print(by_dev.to_string(index=False))

    print("\n=== BY MODALITY ===")
    print(by_mod.to_string(index=False))

    print("\n=== BY MODALITY x DEVIATION ===")
    print(by_mod_dev.to_string(index=False))

    print("\n=== BY THEORETICAL STANDARD ===")
    print(by_std.to_string(index=False))


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    """Run the perception flip analysis."""
    if TAG not in INPUT_FILES:
        raise ValueError("TAG must be 'expy' or 'psychopy'.")

    in_path = INPUT_FILES[TAG]
    df = load_data(in_path)
    require_cols(df, REQ_COLS, in_path)

    df = ensure_measurement(df)
    df["duration_type"] = df["duration_type"].astype(str).str.strip().str.lower()

    df = df[df["task"].astype(str).str.strip().str.lower() == "perception"].copy()

    seq_cols = seq_cols_base()
    cond = condition_map(df, seq_cols=seq_cols)

    th = compute_theoretical(df, seq_cols=seq_cols)
    rs = compute_real_standard(df, seq_cols=seq_cols)
    rc = compute_real_comparison(df, seq_cols=seq_cols)

    merged = th.merge(rs, on=seq_cols, how="left").merge(rc, on=seq_cols, how="left")

    # Ensure condition is present in trial_level when available.
    if "condition" in df.columns:
        merged = merged.merge(cond, on=seq_cols, how="left")

    merged = merged.dropna(
        subset=[
            "theoretical_standard",
            "theoretical_comparison",
            "real_standard",
            "real_comparison",
        ]
    ).copy()

    merged = compute_deviations(merged)
    merged = determine_relations(merged)
    merged = compute_flips(merged)

    # Put condition early in trial_level if present.
    preferred = ["task", "subject", "modality", "condition", "trial", MEAS_COL]
    keep = [c for c in preferred if c in merged.columns]
    keep += [c for c in merged.columns if c not in keep]
    merged = merged[keep].copy()

    overall, by_dev, by_mod, by_mod_dev, by_std = build_summaries(merged)

    print_summaries(overall, by_dev, by_mod, by_mod_dev, by_std)

    out_name = f"perception_flip_summary_{TAG}.xlsx"
    out_path = OUT_DIR / out_name
    save_all_to_excel(
        trial_df=merged,
        overall=overall,
        by_dev=by_dev,
        by_mod=by_mod,
        by_mod_dev=by_mod_dev,
        by_std=by_std,
        out_path=out_path,
    )


if __name__ == "__main__":
    main()
