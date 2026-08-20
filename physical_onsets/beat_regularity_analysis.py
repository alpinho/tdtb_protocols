#!/usr/bin/env python3
"""
Beat-regularity fidelity for Music-SDTB physical-onsets long-shape tables.

Trial-level assessment of how often the rendered timing of the (critical)
auditory Beat departed from its nominal structure by more than a perceptual
amount. Unlike jittering_analysis.py, the threshold is a FRACTION of each
element's own nominal (Weber's law), not a fixed number of milliseconds, so
Standards (S) and SOAs (3S) are judged on the same relative scale.

Two fractions are evaluated:
  0.05   duration-discrimination Weber fraction for empty intervals
         (Getty 1975): the deviation becomes discriminable.
  0.086  pulse-attribution limit (Madison & Merker 2002): the anisochrony at
         which a pulse can no longer be extracted (from a fully sounded, denser
         sequence, so a lenient beat-loss reference here).

Four checks per recording, each flagged when it exceeds f * nominal:
  standard_error         any Standard deviates from its nominal S
  soa_error              any SOA deviates from its nominal 3S
  standard_internal_diff the two Standards differ from each other (range),
                         scaled by S
  soa1_soa2_diff         the two SOAs differ from each other, scaled by 3S
The first two index accuracy against nominal; the last two index internal
consistency (regularity), and need no nominal reference beyond the scaling.

Restricted to one modality x condition (default auditory Beat). Outputs, per
fraction and pooled plus per-Standard: a TSV summary, a combined two-fraction
TSV, and an RTF report.

author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Creation: July 2026
Compatibility: Python 3.10.16
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
import pandas as pd

# =============================================================================
# Configuration
# =============================================================================
TAG = ["expy1", "expy2"]  # e.g. "expy1" or ["expy1", "expy2"]
OUT_TAG = "expy"  # required when len(TAG) > 1

INPUT_FILES = {"expy1": "curated_data_summer2025/encoding_expy_june2025_long.tsv", "expy2": "curated_data_summer2025/encoding_expy_july2025_long.tsv"}

OUT_DIR = Path("beat_regularity_summer2025")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODALITY = "audio"  # critical modality
CONDITION = "beat"  # critical condition
FRACTIONS = [0.05, 0.086]  # Getty discrimination; Madison-Merker pulse loss

MEAS_COL = "measurement"
REQ_COLS_COMMON = ["task", "subject", "modality", "condition", "trial", "duration_type", "theoretical_durations", "durations"]

# RTF page geometry (US Letter), matching the other reports.
RTF_PAGE_W_TWIPS = 12240
RTF_PAGE_H_TWIPS = 15840
RTF_MARGIN_TWIPS = 1080
RTF_FONT_FS_BODY = 24
RTF_FONT_FS_TABLE = 20
RTF_FONT_FS_TITLE = 32


# =============================================================================
# I/O (mirrors jittering_analysis.py)
# =============================================================================
def require_cols(df_in: pd.DataFrame, cols: List[str], src: str) -> None:
    missing = [c for c in cols if c not in df_in.columns]
    if missing:
        raise ValueError(f"Missing required columns in {src}: {missing}")


def _ensure_measurement(df_in: pd.DataFrame) -> pd.DataFrame:
    df_work = df_in.copy()
    if MEAS_COL not in df_work.columns:
        df_work[MEAS_COL] = 1
    return df_work


def load_input_data(tag_in: str | Sequence[str], out_tag_in: str | None = None) -> tuple[pd.DataFrame, str]:
    """Load one file, or stack several with a 'session' column that keeps
    same-index recordings from different files distinct. A session column is
    used (rather than offsetting the measurement index) so that repeated
    elements within a sequence -- the two Standards, the two SOAs -- stay in
    the same recording."""
    tags = [tag_in] if isinstance(tag_in, str) else list(tag_in)
    if not tags:
        raise ValueError("TAG cannot be empty.")
    invalid = [t for t in tags if t not in INPUT_FILES]
    if invalid:
        raise ValueError(f"Unknown TAG(s): {invalid}")
    if len(tags) > 1 and (not out_tag_in or not str(out_tag_in).strip()):
        raise ValueError("When len(TAG) > 1, you must provide OUT_TAG.")
    frames = []
    for tag in tags:
        df_one = pd.read_csv(INPUT_FILES[tag], sep="\t")
        require_cols(df_one, REQ_COLS_COMMON, INPUT_FILES[tag])
        df_one = _ensure_measurement(df_one).copy()
        df_one["session"] = tag
        frames.append(df_one)
    out_tag = str(out_tag_in).strip() if len(tags) > 1 else tags[0]
    return pd.concat(frames, ignore_index=True), out_tag


# =============================================================================
# Core: per-recording flags at a fractional threshold
# =============================================================================
CHECKS = [("standard_error", "a Standard deviates from nominal S"), ("soa_error", "an SOA deviates from nominal 3S"), ("standard_internal_diff", "the two Standards disagree"), ("soa1_soa2_diff", "the two SOAs disagree")]


def _recording_table(df_in: pd.DataFrame) -> pd.DataFrame:
    """One row per recording (auditory Beat), carrying the rendered and nominal
    Standards and SOAs needed for every check."""
    df_work = _ensure_measurement(df_in).copy()
    df_work["duration_type"] = df_work["duration_type"].astype(str).str.strip().str.lower()
    df_work["modality"] = df_work["modality"].astype(str).str.lower()
    df_work["condition"] = df_work["condition"].astype(str).str.lower()
    for c in ("durations", "theoretical_durations"):
        df_work[c] = pd.to_numeric(df_work[c], errors="coerce")

    sub = df_work[(df_work["modality"] == MODALITY) & (df_work["condition"] == CONDITION)].copy()
    if "session" not in sub.columns:
        sub["session"] = "single"
    seq = ["session", "task", "subject", "trial", MEAS_COL]
    recs: List[dict] = []
    for keys, g in sub.groupby(seq, sort=False):
        st = g[g["duration_type"] == "standard"].dropna(subset=["durations", "theoretical_durations"])
        if st.empty:
            continue
        S = float(st["theoretical_durations"].iloc[0])
        std_r = st["durations"].to_numpy(dtype=float)
        std_n = st["theoretical_durations"].to_numpy(dtype=float)
        rec = dict(zip(seq, keys))
        rec["S"] = S
        rec["std_abs_err"] = np.abs(std_r - std_n)  # array
        rec["std_nom"] = std_n
        rec["std_range"] = float(std_r.max() - std_r.min()) if len(std_r) >= 2 else np.nan
        soa_r, soa_n = [], []
        for dt in ("soa1", "soa2"):
            s = g[g["duration_type"] == dt].dropna(subset=["durations", "theoretical_durations"])
            if len(s):
                soa_r.append(float(s["durations"].iloc[0]))
                soa_n.append(float(s["theoretical_durations"].iloc[0]))
        rec["soa_r"] = soa_r
        rec["soa_n"] = soa_n
        rec["soa_nom"] = soa_n[0] if soa_n else 3.0 * S
        recs.append(rec)
    return pd.DataFrame(recs)


def _flags_at_fraction(rt: pd.DataFrame, f: float) -> pd.DataFrame:
    """Boolean flags per recording at fraction f of each element's nominal."""
    out = rt[["task", "subject", "trial", MEAS_COL, "S"]].copy()

    def std_off(r):
        return bool(np.any(r["std_abs_err"] > f * r["std_nom"]))

    def std_dis(r):
        return bool(r["std_range"] > f * r["S"]) if not np.isnan(r["std_range"]) else np.nan

    def soa_off(r):
        if not r["soa_r"]:
            return np.nan
        return bool(any(abs(dr - dn) > f * dn for dr, dn in zip(r["soa_r"], r["soa_n"])))

    def soa_dis(r):
        if len(r["soa_r"]) != 2:
            return np.nan
        return bool(abs(r["soa_r"][0] - r["soa_r"][1]) > f * r["soa_nom"])

    out["standard_error"] = rt.apply(std_off, axis=1)
    out["standard_internal_diff"] = rt.apply(std_dis, axis=1)
    out["soa_error"] = rt.apply(soa_off, axis=1)
    out["soa1_soa2_diff"] = rt.apply(soa_dis, axis=1)
    return out


def summarize(rt: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pooled and per-Standard percentages for every check and fraction."""
    pooled_rows: List[dict] = []
    per_std_rows: List[dict] = []
    flags = {f: _flags_at_fraction(rt, f) for f in FRACTIONS}

    for key, label in CHECKS:
        row = {"Check": label}
        n_check = None
        for f in FRACTIONS:
            v = flags[f][key].dropna()
            n_check = len(v)
            row[f"{f*100:.1f}%"] = round(100.0 * v.mean(), 1)
        row["N"] = n_check
        pooled_rows.append(row)

    for S in sorted(rt["S"].dropna().unique()):
        for key, label in CHECKS:
            row = {"Standard (ms)": int(round(S)), "Check": label}
            for f in FRACTIONS:
                fl = flags[f]
                v = fl[fl["S"] == S][key].dropna()
                row[f"{f*100:.1f}%"] = round(100.0 * v.mean(), 1) if len(v) else np.nan
            per_std_rows.append(row)
    return pd.DataFrame(pooled_rows), pd.DataFrame(per_std_rows)


# =============================================================================
# RTF output (mirrors jittering_analysis.py)
# =============================================================================
def rtf_escape(text: str) -> str:
    return str(text).replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def write_rtf_table_report(outpath: Path, title: str, explanation: str, headers: List[str], rows: List[List[str]]) -> None:
    usable = RTF_PAGE_W_TWIPS - 2 * RTF_MARGIN_TWIPS
    first = 4200
    rest = (usable - first) // max(1, len(headers) - 1)
    widths = [first] + [rest] * (len(headers) - 1)

    def table_row(cells, header=False):
        r = r"\trowd\trgaph108\trleft0"
        x = 0
        for w in widths:
            x += w
            r += rf"\cellx{x}"
        for c in cells:
            if header:
                r += rf"\intbl\b\fs{RTF_FONT_FS_TABLE} {rtf_escape(c)}\b0\cell"
            else:
                r += rf"\intbl\fs{RTF_FONT_FS_TABLE} {rtf_escape(c)}\cell"
        return r + r"\row"

    lines = [r"{\rtf1\ansi\deff0", r"{\fonttbl{\f0\fswiss Arial;}}", rf"\paperw{RTF_PAGE_W_TWIPS}\paperh{RTF_PAGE_H_TWIPS}", rf"\margl{RTF_MARGIN_TWIPS}\margr{RTF_MARGIN_TWIPS}" rf"\margt{RTF_MARGIN_TWIPS}\margb{RTF_MARGIN_TWIPS}", rf"\f0\fs{RTF_FONT_FS_BODY}", rf"\qc\b\fs{RTF_FONT_FS_TITLE} {rtf_escape(title)}" rf"\b0\fs{RTF_FONT_FS_BODY}\par", r"\par", rf"{rtf_escape(explanation)}\par", r"\par", table_row(headers, header=True)]
    lines += [table_row(r) for r in rows]
    lines.append("}")
    outpath.write_text("\n".join(lines), encoding="utf-8")


def _rows(df_in: pd.DataFrame) -> List[List[str]]:
    return [[str(v) for v in r.tolist()] for _, r in df_in.iterrows()]


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    df, tag_label = load_input_data(TAG, OUT_TAG)
    rt = _recording_table(df)
    if rt.empty:
        raise ValueError(f"No {MODALITY} {CONDITION} recordings found.")
    pooled, per_std = summarize(rt)

    prefix = f"beat_regularity_{MODALITY}-{CONDITION}_{tag_label}"
    pooled.to_csv(OUT_DIR / f"{prefix}_pooled.tsv", sep="\t", index=False)
    per_std.to_csv(OUT_DIR / f"{prefix}_by_standard.tsv", sep="\t", index=False)

    thr_ms = "; ".join(f"{f*100:.1f}% = {f*459:.0f}-{f*663:.0f} ms (Standard), " f"{f*1377:.0f}-{f*1989:.0f} ms (SOA)" for f in FRACTIONS)
    explanation = f"Percentage of {MODALITY} {CONDITION} recordings in which each check exceeded a threshold set to a fraction of the element's own nominal (Weber's law), rather than a fixed millisecond value. Fractions: 5% (Getty 1975, duration-discrimination limit) and 8.6% (Madison & Merker 2002, pulse-attribution limit). In ms: {thr_ms}. The Standard checks scale by S, the SOA checks by 3S."
    write_rtf_table_report(OUT_DIR / f"{prefix}_pooled.rtf", f"Beat Regularity ({MODALITY} {CONDITION}): trials exceeding " "perceptual thresholds", explanation, list(pooled.columns), _rows(pooled))

    print(f"N recordings: {len(rt)}")
    print(pooled.to_string(index=False))
    print(f"\nOutputs in {OUT_DIR}/: {prefix}_pooled.tsv, " f"{prefix}_by_standard.tsv, {prefix}_pooled.rtf")


if __name__ == "__main__":
    main()
