#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prepare input data for physical onset analysis. This input-data
pertains to the experiment in July 2025, where we
tested the version of the scripts in expyriment with the TTL pulse.

Author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Date of creation: 18th of March 2026
Last Update: March 2026

Compatibility: Python 3.10.16
"""

import os
import re

import pandas as pd


# ---------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------
def append_physical_columns(theoretical_df, physical_path, suffix):
    physical_df = pd.read_csv(physical_path, sep="\t")

    physical_encoding_df = (
        physical_df.loc[
            physical_df["type"] == "encoding",
            ["onsetLatency_ms", "onset2onset_durations_ms"],
        ]
        .reset_index(drop=True)
        .copy()
    )

    if len(theoretical_df) != len(physical_encoding_df):
        raise ValueError(
            f"Mismatch rows ({len(theoretical_df)} vs "
            f"{len(physical_encoding_df)})"
        )

    theoretical_df[f"onsets_{suffix}"] = physical_encoding_df[
        "onsetLatency_ms"
    ]
    theoretical_df[f"durations_{suffix}"] = physical_encoding_df[
        "onset2onset_durations_ms"
    ]
    theoretical_df[f"error_{suffix}"] = (
        theoretical_df[f"durations_{suffix}"]
        - theoretical_df["theoretical_durations"]
    )

    return theoretical_df


def append_physical_columns_from_df(theoretical_df, physical_df, suffix):
    if "type" in physical_df.columns:
        physical_encoding_df = (
            physical_df.loc[
                physical_df["type"] == "encoding",
                ["onsetLatency_ms", "onset2onset_durations_ms"],
            ]
            .reset_index(drop=True)
            .copy()
        )
    else:
        physical_encoding_df = (
            physical_df[
                ["onsetLatency_ms", "onset2onset_durations_ms"]
            ]
            .reset_index(drop=True)
            .copy()
        )

    if len(physical_encoding_df) > len(theoretical_df):
        raise ValueError(
            f"Mismatch rows ({len(theoretical_df)} vs "
            f"{len(physical_encoding_df)})"
        )

    physical_encoding_df = physical_encoding_df.reindex(
        range(len(theoretical_df))
    )

    theoretical_df[f"onsets_{suffix}"] = physical_encoding_df[
        "onsetLatency_ms"
    ]
    theoretical_df[f"durations_{suffix}"] = physical_encoding_df[
        "onset2onset_durations_ms"
    ]
    theoretical_df[f"error_{suffix}"] = (
        theoretical_df[f"durations_{suffix}"]
        - theoretical_df["theoretical_durations"]
    )

    return theoretical_df


def build_wide_dataframe(theoretical_path, physical_paths):
    theoretical_df = pd.read_csv(theoretical_path, sep="\t")
    theoretical_df = theoretical_df.reset_index(drop=True).copy()

    for idx, physical_path in enumerate(physical_paths, start=1):
        theoretical_df = append_physical_columns(
            theoretical_df, physical_path, idx
        )

    return theoretical_df


def resolve_path(base_dir, filename, fallback_dir):
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        path = os.path.join(fallback_dir, filename)
    return path


def build_long_dataframe(wide_df):
    base_cols = [
        col for col in wide_df.columns
        if not re.match(r"^(onsets|durations|error)_\d+$", col)
    ]

    measurement_ids = sorted(
        {
            int(col.split("_")[-1])
            for col in wide_df.columns
            if re.match(r"^onsets_\d+$", col)
        }
    )

    long_dfs = []

    insert_at = base_cols.index("theoretical_durations")
    cols_before = base_cols[:insert_at]
    cols_after = base_cols[insert_at:]

    for measurement in measurement_ids:
        onset_col = f"onsets_{measurement}"
        dur_col = f"durations_{measurement}"
        err_col = f"error_{measurement}"

        tmp_df = wide_df[base_cols].copy()
        tmp_df.insert(insert_at, "measurement", measurement)
        tmp_df["onsets"] = wide_df[onset_col]
        tmp_df["durations"] = wide_df[dur_col]
        tmp_df["error"] = wide_df[err_col]

        ordered_cols = (
            cols_before
            + ["measurement"]
            + cols_after
            + ["onsets", "durations", "error"]
        )
        tmp_df = tmp_df[ordered_cols]
        long_dfs.append(tmp_df)

    long_df = pd.concat(long_dfs, axis=0, ignore_index=True)
    return long_df


# ---------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))

input_dir = os.path.join(script_dir, "data_expy2_july2025")
theoretical_dir = os.path.join(script_dir, "theoretical_durations")
output_dir = os.path.join(script_dir, "curated_data_summer2025")

OUTPUT_FILE_WIDE = "encoding_expy_july2025_wide.tsv"
OUTPUT_FILE_LONG = "encoding_expy_july2025_long.tsv"


# ---------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(output_dir, exist_ok=True)

    blocks = [
        {
            "theoretical_filename": (
                "theoretical_durations_sub-03_ses-01_run-01_"
                "production_audio_img.tsv"
            ),
            "physical_filenames": [
                "AuditoryProduction_P03_S1R1_1.tsv",
                "AuditoryProduction_P03_S1R1_2.tsv",
                "AuditoryProduction_P03_S1R1_3.tsv",
            ],
        },
        {
            "theoretical_filename": (
                "theoretical_durations_sub-03_ses-01_run-01_"
                "production_visual_img.tsv"
            ),
            "physical_filenames": [
                "VisualProduction_P03_S1R1_1.tsv",
                "VisualProduction_P03_S1R1_2.tsv",
                "VisualProduction_P03_S1R1_3.tsv",
            ],
        },
    ]

    wide_dfs = []

    # -------------------------
    # Production
    # -------------------------
    for block in blocks:
        theoretical_path = resolve_path(
            theoretical_dir,
            block["theoretical_filename"],
            script_dir,
        )

        physical_paths = [
            resolve_path(input_dir, f, script_dir)
            for f in block["physical_filenames"]
        ]

        wide_df = build_wide_dataframe(theoretical_path, physical_paths)
        wide_dfs.append(wide_df)

    # -------------------------
    # VA production
    # -------------------------
    va_paths = [
        resolve_path(
            input_dir,
            "VAProduction_P03_S1R1_1.tsv",
            script_dir,
        ),
        resolve_path(
            input_dir,
            "VAProduction_P03_S1R1_2.tsv",
            script_dir,
        ),
    ]

    production_audio_df = wide_dfs[0]
    production_visual_df = wide_dfs[1]

    for idx, va_path in enumerate(va_paths, start=4):
        va_df = pd.read_csv(va_path, sep="\t")

        va_encoding_df = va_df.loc[va_df["type"] == "encoding"].copy()
        va_encoding_df = va_encoding_df.reset_index(drop=True)

        visual_phys_df = (
            va_encoding_df.loc[va_encoding_df["stimType"] == "Visual"]
            .reset_index(drop=True)
            .copy()
        )
        audio_phys_df = (
            va_encoding_df.loc[va_encoding_df["stimType"] == "Auditory"]
            .reset_index(drop=True)
            .copy()
        )

        production_audio_df = append_physical_columns_from_df(
            production_audio_df,
            audio_phys_df,
            idx,
        )

        # Discard visual data from VAProduction_P03_S1R1_2.tsv
        if os.path.basename(va_path) == "VAProduction_P03_S1R1_2.tsv":
            production_visual_df[f"onsets_{idx}"] = pd.NA
            production_visual_df[f"durations_{idx}"] = pd.NA
            production_visual_df[f"error_{idx}"] = pd.NA
        else:
            production_visual_df = append_physical_columns_from_df(
                production_visual_df,
                visual_phys_df,
                idx,
            )

    wide_dfs[0] = production_audio_df
    wide_dfs[1] = production_visual_df

    # -------------------------
    # NTFD
    # -------------------------
    ntfd_path = resolve_path(
        input_dir,
        "VANTFD_P03_S1R1_1.tsv",
        script_dir,
    )

    ntfd_df = pd.read_csv(ntfd_path, sep="\t")

    th_audio_path = resolve_path(
        theoretical_dir,
        "theoretical_durations_sub-03_ses-01_run-01_ntfd_audio_img.tsv",
        script_dir,
    )
    th_visual_path = resolve_path(
        theoretical_dir,
        "theoretical_durations_sub-03_ses-01_run-01_ntfd_visual_img.tsv",
        script_dir,
    )

    th_audio = pd.read_csv(th_audio_path, sep="\t")
    th_visual = pd.read_csv(th_visual_path, sep="\t")

    visual_phys = (
        ntfd_df.loc[
            (ntfd_df["type"] == "encoding")
            & (ntfd_df["stimType"] == "Visual")
        ]
        .reset_index(drop=True)
        .copy()
    )
    audio_phys = (
        ntfd_df.loc[
            (ntfd_df["type"] == "encoding")
            & (ntfd_df["stimType"] == "Auditory")
        ]
        .reset_index(drop=True)
        .copy()
    )

    ntfd_audio_df = append_physical_columns_from_df(
        th_audio.reset_index(drop=True).copy(),
        audio_phys,
        1,
    )
    ntfd_visual_df = append_physical_columns_from_df(
        th_visual.reset_index(drop=True).copy(),
        visual_phys,
        1,
    )

    wide_dfs.append(ntfd_audio_df)
    wide_dfs.append(ntfd_visual_df)

    # -------------------------
    # Save wide
    # -------------------------
    final_wide_df = pd.concat(wide_dfs, axis=0, ignore_index=True)
    final_wide_df = final_wide_df.replace(r"^\s*$", pd.NA, regex=True)

    output_path = os.path.join(output_dir, OUTPUT_FILE_WIDE)
    final_wide_df.to_csv(
        output_path,
        sep="\t",
        index=False,
        na_rep="nan",
    )

    # -------------------------
    # Save long
    # -------------------------
    final_long_df = build_long_dataframe(final_wide_df)

    output_path_long = os.path.join(output_dir, OUTPUT_FILE_LONG)
    final_long_df.to_csv(
        output_path_long,
        sep="\t",
        index=False,
        na_rep="nan",
    )