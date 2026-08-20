#!/usr/bin/env python3
"""
Rhythm-fidelity analysis for Music-SDTB physical-onsets long-shape tables.

Every rendered interval is compared with its own nominal. The deviation of one
interval is (rendered duration - nominal), read from the durations column, and
is reported separately for the Standards (the S intervals) and the SOAs (the 3S
between-pair intervals), and pooled across the two. The same measure is applied
to the Beat and the Interval conditions. The Perception comparison is the deviant
probe and is excluded here; it has its own report.

Rows appear in the fixed order [standard, soa1, standard, soa2,
(standard | comparison)]; positions 0, 2 (and 4 in NTFD) are Standards, positions
1, 3 are SOAs. Position 4 is a Standard only in NTFD; in Production it is the
reproduction cue and in Perception the deviant comparison, both excluded.

Summary columns: Modality, Condition, Task, Element (Standard / Soa / All), N,
RMS (% nom), RMS (ms), Signed mean (% nom), |Dev| mean (% nom), |Dev| max
(% nom). 'all' pools: Condition 'all' = Beat and Interval; Task 'all' = the
tasks; Element 'All' = Standards and SOAs. Full column definitions and formulas
are in duration_deviation_columns.pdf.

Given TAG, this script produces:
1) Duration deviation (Standards, SOAs, and pooled; both conditions): per-element
   table, a summary by modality, condition, task, and element (TSV and RTF), and
   a figure -> duration_deviation_spacing-nominal_<tag>_*
2) Perception comparison: the probe's rendered duration vs its own nominal, one
   report per condition
   -> perception_comparison_condition-<cond>_spacing-nominal_<tag>_*

author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Creation: 29th of June 2026
Last update: July 2026

Compatibility: Python 3.10.16
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =============================================================================
# Configuration
# =============================================================================
# TAG = ["expy1", "expy2"]  # e.g. "expy1" or ["expy1", "expy2"]
# OUT_TAG = "expy"  # required when len(TAG) > 1

TAG = ["psychopy_st", "psychopy_st_buf01"] 
OUT_TAG = "psychopy"  # required when len(TAG) > 1

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

# OUT_DIR = Path("rhythm_fidelity_summer2025")  # tables and PNG figure
OUT_DIR = Path("rhythm_fidelity_winter2026")  # tables and PNG figure

# Rows appear in the fixed order
# [standard, soa1, standard, soa2, (standard | comparison)]. This head is
# required for a sequence to be measurable.
EXPECTED_HEAD = ["standard", "soa1", "standard", "soa2"]

# Nominal duration-deviation analysis (both conditions). Every duration element
# is compared with its own nominal, using its rendered within-pair duration, and
# reported separately for the standards and the SOAs. Row position -> element
# kind, in the fixed order [standard, soa1, standard, soa2, (standard |
# comparison)]. Position 4 is a standard only in NTFD; in Perception it is the
# comparison probe, which is excluded here (it has its own report).
DURATION_ROWS = {0: "standard", 1: "soa", 2: "standard", 3: "soa", 4: "standard"}

MEAS_COL = "measurement"

REQ_COLS_COMMON = [
    "task",
    "subject",
    "modality",
    "condition",
    "trial",
    "theoretical_durations",
    "duration_type",
    "onsets",
    "durations",
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
# Data loading (shared convention with jittering_analysis.py)
# =============================================================================
def require_cols(df_in: pd.DataFrame, cols: List[str], src: str) -> None:
    """Raise if required columns are missing."""
    missing = [c for c in cols if c not in df_in.columns]
    if missing:
        raise ValueError(f"Missing required columns in {src}: {missing}")


def _ensure_measurement(df_in: pd.DataFrame) -> pd.DataFrame:
    """Ensure measurement exists; if not, create it as 1."""
    df_work = df_in.copy()
    if MEAS_COL not in df_work.columns:
        df_work[MEAS_COL] = 1
    return df_work


def _stack_with_measurement_offset(
    dfs_in: Sequence[pd.DataFrame],
) -> pd.DataFrame:
    """Stack dataframes and offset repeated measurements across files.

    Each file is shifted by a single constant so that its measurement indices
    start above the maximum measurement of all previously stacked files. This
    keeps the measurement ranges of different files disjoint while preserving
    the structure within each playback.
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
        base = int(df_one[MEAS_COL].max())
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
# Perception comparison (separate report)
# =============================================================================
def compute_comparison_residuals(df_in: pd.DataFrame) -> pd.DataFrame:
    """Rendered duration of the Perception comparison vs its own nominal.

    The comparison is the deviant probe: its nominal duration is set away from
    the standard S by design. For every Perception comparison element (in any
    condition) we take its rendered within-pair duration and its deviation from
    its own nominal, signed and as a percentage of that nominal. This is kept
    apart from the Standard and SOA deviation report, since the probe is judged,
    not a fidelity reference. One row per comparison.
    """
    df_work = _ensure_measurement(df_in)
    sub = df_work[
        (df_work["task"].astype(str).str.strip().str.lower() == "perception")
        & (df_work["duration_type"].astype(str).str.strip().str.lower()
           == "comparison")
    ].copy()
    sub["durations"] = pd.to_numeric(sub["durations"], errors="coerce")
    sub["theoretical_durations"] = pd.to_numeric(
        sub["theoretical_durations"], errors="coerce")

    keep = ["task", "modality", "condition", "subject", "trial", MEAS_COL]
    recs: List[dict] = []
    for _, r in sub.iterrows():
        d, n = r["durations"], r["theoretical_durations"]
        if np.isnan(d) or np.isnan(n) or n <= 0:
            continue
        rec = {k: r[k] for k in keep}
        rec.update(nominal=n, measured=d, dev_ms=d - n, dev_pct=100.0 * (d - n) / n)
        recs.append(rec)
    cols = keep + ["nominal", "measured", "dev_ms", "dev_pct"]
    return pd.DataFrame.from_records(recs, columns=cols)


def summarize_comparison(per_comp: pd.DataFrame) -> pd.DataFrame:
    """Comparison duration deviation by modality, for a single condition.

    Signed deviation (bias) and RMS deviation (magnitude) from the comparison's
    own nominal, in ms and as a percentage of that nominal. One row per
    modality; the report is already restricted to one condition.
    """
    def _agg(df_in: pd.DataFrame) -> dict:
        dev = df_in["dev_ms"].to_numpy(dtype=float)
        pct = df_in["dev_pct"].to_numpy(dtype=float)
        return {
            "Modality": df_in["modality"].iloc[0],
            "N": int(len(df_in)),
            "Dev mean (ms)": round(float(np.mean(dev)), 2),
            "Dev RMS (ms)": round(float(np.sqrt(np.mean(dev ** 2))), 2),
            "Dev mean (% nom)": round(float(np.mean(pct)), 3),
            "Dev RMS (% nom)": round(float(np.sqrt(np.mean(pct ** 2))), 3),
            "Max|dev| (% nom)": round(float(np.max(np.abs(pct))), 3),
        }

    rows = [_agg(df_mod) for _, df_mod in per_comp.groupby("modality")]
    return pd.DataFrame(rows).sort_values("Modality").reset_index(drop=True)


# =============================================================================
# RTF writing (shared convention with jittering_analysis.py)
# =============================================================================
def compute_col_widths_twips(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    page_w_twips: int,
    margin_twips: int,
    twips_per_char: int = 120,
    cell_pad_twips: int = 220,
) -> List[int]:
    """Compute table column widths in twips based on string lengths."""
    n_cols = len(headers)
    usable = max(page_w_twips - 2 * margin_twips, 4000)
    max_lens = [len(str(h)) for h in headers]
    for row in rows:
        for j in range(n_cols):
            max_lens[j] = max(max_lens[j], len(str(row[j])))
    desired = [ln * twips_per_char + cell_pad_twips for ln in max_lens]
    total = sum(desired)
    if total <= usable:
        return desired
    scale = usable / total
    return [max(400, int(w * scale)) for w in desired]


def rtf_escape(text: str) -> str:
    """Escape special characters for RTF."""
    return (
        str(text).replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
    )


def write_rtf_table_report(
    outpath: Path,
    title: str,
    explanation: str,
    headers: List[str],
    rows: List[List[str]],
) -> None:
    """Write an RTF report with title, explanation, and one table."""
    col_widths = compute_col_widths_twips(
        headers=headers, rows=rows,
        page_w_twips=RTF_PAGE_W_TWIPS, margin_twips=RTF_MARGIN_TWIPS,
    )

    def table_row(cells: List[str], header: bool = False) -> str:
        row = r"\trowd\trgaph108\trleft0"
        xpos = 0
        for width in col_widths:
            xpos += width
            row += rf"\cellx{xpos}"
        for cell in cells:
            if header:
                row += (rf"\intbl\b\fs{RTF_FONT_FS_TABLE} {rtf_escape(cell)}"
                        r"\b0\cell")
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
        rf"\qc\keepn\nowidctlpar \b\fs{RTF_FONT_FS_TITLE} "
        rf"{rtf_escape(title)}\b0\fs{RTF_FONT_FS_BODY}\par"
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
    return [[str(v) for v in r.tolist()] for _, r in df_in.iterrows()]


# =============================================================================
# Output runners
# =============================================================================
def _run_comparison(df: pd.DataFrame, tag_label: str, out_dir: Path) -> None:
    """Perception comparison vs own nominal, one report per condition."""
    out_dir.mkdir(parents=True, exist_ok=True)
    per_comp = compute_comparison_residuals(df)
    if per_comp.empty:
        print("No Perception comparison elements found; skipping comparison "
              "outputs.")
        return

    print(f"\nPerception comparison outputs in {out_dir}/:")
    for condition, sub in per_comp.groupby("condition"):
        sub = sub.copy()
        summary = summarize_comparison(sub)
        prefix = (f"perception_comparison_condition-{condition}_"
                  f"spacing-nominal_{tag_label}")
        per_path = out_dir / f"{prefix}_per_trial.tsv"
        sub.round(4).to_csv(per_path, sep="\t", index=False)
        summary_tsv = out_dir / f"{prefix}_summary.tsv"
        summary.to_csv(summary_tsv, sep="\t", index=False)
        summary_rtf = out_dir / f"{prefix}_summary.rtf"
        explanation = (
            "Rendering fidelity of the Perception comparison, the deviant probe "
            "whose nominal duration is set away from the standard S by design, "
            f"for the {condition} condition. For each comparison element we take "
            "its rendered within-pair duration and its deviation from its own "
            "nominal, reported as a signed bias (mean) and a magnitude (RMS), in "
            "ms and as a percentage of that nominal. This is kept separate from "
            "the Standard and SOA deviation report, since the "
            "probe is judged, not a fidelity reference. One row per modality."
        )
        write_rtf_table_report(summary_rtf, f"Perception Comparison Rendering "
                               f"({condition.capitalize()})", explanation,
                               summary.columns.tolist(),
                               table_df_to_rtf_rows(summary))
        for p in (per_path, summary_tsv, summary_rtf):
            print(f"- {p.name}")


# =============================================================================
# Nominal duration-deviation metric (standards and SOAs, both conditions)
# =============================================================================
def compute_duration_deviations(df_in: pd.DataFrame) -> pd.DataFrame:
    """Per-element deviation of each rendered duration from its own nominal.

    Every duration element (each standard and each SOA) is compared with its
    own nominal, using the rendered within-pair duration (the durations column,
    anchored at the element's first onset). The same measure is applied to the
    Beat and the Interval conditions, and each element is tagged by kind
    ('standard' or 'soa') so the two can be reported separately. The Perception
    comparison (position 4 in Perception) is the probe and is excluded here; it
    has its own report. Returns one row per element.
    """
    df_work = _ensure_measurement(df_in)
    sub = df_work.copy()
    sub["durations"] = pd.to_numeric(sub["durations"], errors="coerce")
    sub["theoretical_durations"] = pd.to_numeric(
        sub["theoretical_durations"], errors="coerce")

    seq_cols = ["task", "modality", "condition", "subject", "trial", MEAS_COL]
    recs: List[dict] = []
    for keys, grp in sub.groupby(seq_cols, sort=False):
        types = (grp["duration_type"].astype(str).str.strip().str.lower()
                 .tolist())
        if types[:4] != EXPECTED_HEAD:
            continue
        dur = grp["durations"].to_numpy(dtype=float)           # within-pair (ms)
        nom = grp["theoretical_durations"].to_numpy(dtype=float)
        base = dict(zip(seq_cols, keys))
        for pos, kind in DURATION_ROWS.items():
            if pos >= len(types):
                continue
            if types[pos] == "comparison":     # probe -> comparison report
                continue
            d, n = dur[pos], nom[pos]
            if np.isnan(d) or np.isnan(n) or n <= 0:
                continue
            r = d - n
            recs.append({**base, "pos": pos, "kind": kind,
                         "element": types[pos], "nominal": n, "measured": d,
                         "dev_ms": r, "dev_pct": 100.0 * r / n})

    cols = seq_cols + ["pos", "kind", "element", "nominal", "measured",
                       "dev_ms", "dev_pct"]
    return pd.DataFrame.from_records(recs, columns=cols)


def summarize_duration_deviations(per_element: pd.DataFrame) -> pd.DataFrame:
    """Deviation summary by modality, condition, task, and element kind.

    Grouping columns: Modality; Condition (beat/interval/all); Task
    (production/perception/ntfd/all); Element (Standard/Soa/All). Value columns:
    N, RMS (% nom), RMS (ms), Signed mean (% nom), |Dev| mean (% nom),
    |Dev| max (% nom). Column definitions and formulas are documented in
    duration_deviation_columns.pdf.
    """
    pe = per_element.copy()

    def _agg(df_in: pd.DataFrame, mod: str, cond: str, task: str,
             kind_label: str) -> dict:
        p = df_in["dev_pct"].to_numpy(dtype=float)     # p_i = 100*(d-n)/n
        e = df_in["dev_ms"].to_numpy(dtype=float)      # e_i = d - n  (ms)
        return {
            "Modality": mod,
            "Condition": cond,
            "Task": task,
            "Element": kind_label,
            "N": int(len(df_in)),
            "RMS (% nom)": round(float(np.sqrt(np.mean(p ** 2))), 3),
            "RMS (ms)": round(float(np.sqrt(np.mean(e ** 2))), 2),
            "Signed mean (% nom)": round(float(np.mean(p)), 3),
            "|Dev| mean (% nom)": round(float(np.mean(np.abs(p))), 3),
            "|Dev| max (% nom)": round(float(np.max(np.abs(p))), 3),
        }

    # (kind selector, Element label): 'all' pools Standards and SOAs.
    kinds = [("standard", "Standard"), ("soa", "Soa"), ("all", "All")]

    rows: List[dict] = []
    for mod, d_mod in pe.groupby("modality"):
        for sel, label in kinds:
            d_kind = d_mod if sel == "all" else d_mod[d_mod["kind"] == sel]
            if d_kind.empty:
                continue
            for (cond, task), d_tc in d_kind.groupby(["condition", "task"]):
                rows.append(_agg(d_tc, mod, cond, task, label))
            for cond, d_c in d_kind.groupby("condition"):
                rows.append(_agg(d_c, mod, cond, "all", label))   # pool tasks
            rows.append(_agg(d_kind, mod, "all", "all", label))   # pool all
    return pd.DataFrame(rows)


def plot_duration_deviations(per_element: pd.DataFrame,
                             out_path: Path) -> None:
    """Violin/box of per-element deviation (% of nominal) by modality and kind."""
    pe = per_element.copy()
    groups: List[np.ndarray] = []
    labels: List[str] = []
    for mod in sorted(pe["modality"].unique()):
        for kind in ("standard", "soa"):
            vals = pe[(pe["modality"] == mod) & (pe["kind"] == kind)]["dev_pct"]
            vals = vals.dropna().to_numpy(dtype=float)
            if vals.size:
                groups.append(vals)
                labels.append(f"{mod}\n{kind}")
    if not groups:
        return
    fig, ax = plt.subplots(figsize=(1.6 * len(groups) + 1.0, 4.2))
    ax.violinplot(groups, showmeans=False, showextrema=False)
    ax.boxplot(groups, widths=0.15, showfliers=False,
               medianprops=dict(color="black"))
    ax.axhline(0.0, color="0.6", lw=0.8, ls="--")
    ax.set_xticks(range(1, len(groups) + 1))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Deviation from nominal (% of nominal)")
    ax.set_title("Rendered duration deviations by element (standard vs SOA)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _run_duration_deviations(df: pd.DataFrame, tag_label: str,
                             out_dir: Path) -> None:
    """Standards-and-SOAs nominal-deviation report (both conditions)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    per_element = compute_duration_deviations(df)
    if per_element.empty:
        print("No duration elements found; skipping deviation outputs.")
        return

    summary = summarize_duration_deviations(per_element)
    prefix = f"duration_deviation_spacing-nominal_{tag_label}"

    per_elem_path = out_dir / f"{prefix}_per_element.tsv"
    per_element.round(4).to_csv(per_elem_path, sep="\t", index=False)
    summary_tsv = out_dir / f"{prefix}_summary.tsv"
    summary.to_csv(summary_tsv, sep="\t", index=False)

    summary_rtf = out_dir / f"{prefix}_summary.rtf"
    explanation = (
        "Deviation of each rendered interval from its own nominal, applied to "
        "the Beat and Interval conditions and reported for the Standards, the "
        "SOAs, and the two pooled (Element). Grouping columns: Modality; "
        "Condition (beat/interval/all); Task (production/perception/ntfd/all); "
        "Element (Standard/Soa/All). Value columns: N, RMS (% nom), RMS (ms), "
        "Signed mean (% nom), |Dev| mean (% nom), |Dev| max (% nom). Column "
        "definitions and formulas are given in duration_deviation_columns.pdf. "
        "The Perception comparison is the probe and is excluded here; it has "
        "its own report."
    )
    write_rtf_table_report(
        summary_rtf, "Duration Rendering Fidelity (Standards, SOAs, Pooled)",
        explanation, summary.columns.tolist(),
        table_df_to_rtf_rows(summary))

    fig_path = out_dir / f"{prefix}.png"
    plot_duration_deviations(per_element, fig_path)

    print(f"\nDuration-deviation outputs in {out_dir}/:")
    for p in (per_elem_path, summary_tsv, summary_rtf, fig_path):
        print(f"- {p.name}")


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    """Run the duration-deviation and Perception comparison reports."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df, tag_label = load_input_data(TAG, OUT_TAG)
    _run_duration_deviations(df, tag_label, OUT_DIR / "duration_deviation")
    _run_comparison(df, tag_label, OUT_DIR / "comparison")


if __name__ == "__main__":
    main()