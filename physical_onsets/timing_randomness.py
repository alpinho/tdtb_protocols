#!/usr/bin/env python3
"""Assess whether the Expyriment stimulus-timing jitter is random or fixed.

For a small validation set, each stimulus sequence was replayed several times
offline and its physical onsets recorded. This script quantifies how far the
per-interval timing error reproduces across those repeats. If the jitter is
fixed it reproduces and could be removed by post-hoc correction; if it is
random it does not reproduce and cannot.

Two statistics are reported per modality, pooling every within-sequence pair of
repeats:

  test-retest r  Pearson correlation of the per-interval error between two
                 repeats of the same sequence. Near 0 means the jitter does not
                 reproduce (random); near 1 means it is fixed.

  variance ratio var(error_i - error_j) / mean(var(error_i), var(error_j)).
                 Near 2 is the signature of independent noise: differencing two
                 recordings doubles the variance, so a correction would add
                 noise rather than remove it. Near 0 means the jitter cancels
                 (fixed).

The per-interval error is the curated 'error' column (rendered inter-onset
interval minus its nominal, in ms). Repeats are aligned by interval position
within each sequence; unmatched or missing positions are dropped pairwise.
"""
from itertools import combinations
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

# =============================================================================
# Config
# =============================================================================
# Expyriment curated long tables (the validated batch), keyed by recording
# session. The same sequence can be recorded in more than one session and the
# sessions reuse the measurement labels 1, 2, ..., so the session must be part
# of the repeat identity. Otherwise June-measurement-1 and July-measurement-1
# collide into one apparent record.
INPUT_FILES = {
    # "june":     "curated_data_summer2025/encoding_expy_june2025_long.tsv",
    # "july":     "curated_data_summer2025/encoding_expy_july2025_long.tsv",
    "february": "curated_data_feb2026/encoding_long_st.tsv",
    "april":    "curated_data_april2026/encoding_long_st_buf-01.tsv",
}

# A sequence is one trial of a given stimulus set, modality, condition and task.
# A repeat is one recording of it, identified by (session, measurement).
SEQ_KEYS = ["subject", "modality", "condition", "task", "trial"]
MEAS_COL = "measurement"
MODALITY_COL = "modality"
ERROR_COL = "error"          # rendered inter-onset interval minus nominal (ms)
ARTEFACT_ABS_MS = 100.0      # drop |error| above this as a recording artefact

# OUT_TSV = Path("timing_randomness/timing_randomness_expy.tsv")
OUT_TSV = Path("timing_randomness/timing_randomness_psychopy.tsv")


# =============================================================================
# Load
# =============================================================================
def load_inputs(paths: dict) -> pd.DataFrame:
    """Concatenate the curated long tables, tag the session, index intervals.

    Each row gets a 'rep' identifier (session plus measurement) so repeats from
    different sessions are kept distinct, and a 'pos', the order of the interval
    within its recording, used to align the same interval across repeats.
    """
    frames = []
    for session, path in paths.items():
        d = pd.read_csv(path, sep="\t")
        d["session"] = session
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df[ERROR_COL] = pd.to_numeric(df[ERROR_COL], errors="coerce")
    df["rep"] = df["session"] + "-" + df[MEAS_COL].astype(str)
    df["pos"] = df.groupby(SEQ_KEYS + ["rep"]).cumcount()
    return df


# =============================================================================
# Scope
# =============================================================================
def describe_scope(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize the validation set: sequences, repeats, total recordings."""
    per_seq = df.groupby(SEQ_KEYS)["rep"].nunique()
    counts = per_seq.value_counts().sort_index()
    rows = [{"repeats": int(k), "n_sequences": int(v)} for k, v in counts.items()]
    rows.append({"repeats": "total", "n_sequences": int(per_seq.size)})
    print(f"Validation set: {per_seq.size} sequences, "
          f"{int(per_seq.sum())} recordings "
          f"({df[MODALITY_COL].nunique()} modalities, "
          f"{df['condition'].nunique()} conditions, {df['task'].nunique()} "
          f"tasks, {df['subject'].nunique()} stimulus sets).")
    for r in rows[:-1]:
        print(f"  {r['n_sequences']} sequences recorded {r['repeats']} times")
    return pd.DataFrame(rows)


# =============================================================================
# Randomness
# =============================================================================
def _repeat_pairs(d: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Stack the per-interval error for every within-sequence pair of repeats.

    Returns paired arrays (x, y): each element is the error of one interval in
    one repeat (x) and in another repeat of the same sequence (y).
    """
    piv = d.pivot_table(index=SEQ_KEYS + ["pos"], columns="rep",
                        values=ERROR_COL)
    xs, ys = [], []
    for mi, mj in combinations(list(piv.columns), 2):
        sub = piv[[mi, mj]].dropna()
        xs.append(sub[mi].to_numpy(dtype=float))
        ys.append(sub[mj].to_numpy(dtype=float))
    x = np.concatenate(xs) if xs else np.array([])
    y = np.concatenate(ys) if ys else np.array([])
    keep = (np.abs(x) < ARTEFACT_ABS_MS) & (np.abs(y) < ARTEFACT_ABS_MS)
    return x[keep], y[keep]


def randomness_stats(d: pd.DataFrame, modality: str) -> dict:
    """Test-retest correlation and difference-variance ratio for one modality."""
    x, y = _repeat_pairs(d)
    var_single = 0.5 * (float(np.var(x)) + float(np.var(y)))
    return {
        "Modality": modality,
        "N interval pairs": int(x.size),
        "Test-retest r": round(float(np.corrcoef(x, y)[0, 1]), 3),
        "Var single (ms^2)": round(var_single, 1),
        "Var difference (ms^2)": round(float(np.var(x - y)), 1),
        "Var ratio": round(float(np.var(x - y)) / var_single, 2),
    }


def main() -> None:
    df = load_inputs(INPUT_FILES)
    describe_scope(df)
    rows = [randomness_stats(d, mod)
            for mod, d in df.groupby(MODALITY_COL)]
    out = pd.DataFrame(rows)
    out.to_csv(OUT_TSV, sep="\t", index=False)
    print("\nRandomness across repeats (per-interval timing error):")
    print(out.to_string(index=False))
    print(f"\nWritten to {OUT_TSV}")


if __name__ == "__main__":
    main()