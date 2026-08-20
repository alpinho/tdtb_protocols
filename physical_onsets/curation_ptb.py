#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prepare input data for physical onset analysis. This input-data
pertains to the experiment on the 19th of February 2026, where we
tested the pre-scheduled version (ptb) of the Music-SDTB protocols.

Author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Date of creation: 16th of March 2026
Last Update: March 2026

Compatibility: Python 3.10.16
"""

import os
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------
def fix_split_eventcodes(df):
    """Collapse consecutive Tone Onset / No Tone rows summing to 96.

    When one logical event is split across consecutive rows
    (e.g. EventCode values 64 and 32), keep only the first row, set its
    EventCode to 96, and drop the following absorbed rows. All other
    columns remain as in the first row.

    This is applied to both:
    - Tone Onset
    - No Tone
    """
    if "EventCode" not in df.columns:
        raise ValueError("Input dataframe must contain an 'EventCode' column.")

    valid_types = {"Tone Onset", "No Tone"}

    df = df.copy().reset_index(drop=True)
    rows_to_drop = []
    i = 0

    while i < len(df):
        row_type = df.at[i, "type"]
        event_code = df.at[i, "EventCode"]

        if row_type not in valid_types or pd.isna(event_code) or event_code == 96:
            i += 1
            continue

        cum_sum = event_code
        j = i

        while cum_sum < 96 and (j + 1) < len(df):
            next_idx = j + 1

            if df.at[next_idx, "type"] != row_type:
                break

            next_code = df.at[next_idx, "EventCode"]
            if pd.isna(next_code):
                break

            cum_sum += next_code
            j = next_idx

        if cum_sum == 96 and j > i:
            df.at[i, "EventCode"] = 96
            rows_to_drop.extend(range(i + 1, j + 1))

        i = j + 1 if j > i else i + 1

    if rows_to_drop:
        df = df.drop(index=rows_to_drop).reset_index(drop=True)

    return df


def compute_trial_durations(df_trial):
    """Compute durations within one trial, skipping missing No Tone rows.

    For each row:
    - if type == "Tone Onset", duration is computed to the next valid
      Tone Onset later in the same trial, skipping No Tone rows.
    - if type == "No Tone", duration is missing.
    """
    onset_series = df_trial["onset_latency_ms"].where(
        df_trial["type"] == "Tone Onset",
        np.nan,
    )

    next_valid_onset = onset_series.shift(-1).bfill()
    durations = next_valid_onset - onset_series

    durations = durations.where(df_trial["type"] == "Tone Onset", np.nan)

    return durations


def print_bad_trial_info(df, n_tones_per_trial, input_path):
    """Print detailed information about incomplete or oversized trials."""
    slot_mask = df["type"].isin(["Tone Onset", "No Tone"])

    trial_sizes = (
        df.loc[slot_mask]
        .groupby("trial_id")
        .size()
    )

    bad_trials = trial_sizes[trial_sizes != n_tones_per_trial]

    if bad_trials.empty:
        return

    print("\nBad trials detected:")
    print(bad_trials.to_string())

    for trial_id in bad_trials.index:
        trial_df = df.loc[df["trial_id"] == trial_id].copy()

        print(f"\nBad trial {trial_id} in {os.path.basename(input_path)}:")
        print(
            trial_df[
                [
                    "orig_row",
                    "type",
                    "EventCode",
                    "onset_latency",
                    "onset_latency_ms",
                    "trial_id",
                    "slot_in_trial",
                ]
            ].to_string(index=False)
        )

        slot_rows = trial_df.loc[
            trial_df["type"].isin(["Tone Onset", "No Tone"]),
            [
                "orig_row",
                "type",
                "EventCode",
                "onset_latency",
                "onset_latency_ms",
                "trial_id",
                "slot_in_trial",
            ],
        ]

        print("\nRelevant event-slot rows only:")
        print(slot_rows.to_string(index=False))


def prepare_run_dataframe(input_path, sampling_rate_hz, n_tones_per_trial):
    """Load one physical-onset file and return parsed trial-slot rows."""
    df = pd.read_csv(input_path, sep="\t")
    df["orig_row"] = np.arange(len(df))

    # Repair split EventCode rows before any trial counting
    df = fix_split_eventcodes(df)

    bad_tones = df[
        (df["type"] == "Tone Onset") & (df["EventCode"] != 96)
    ]
    if not bad_tones.empty:
        print("\nTone Onset rows with EventCode != 96 after repair:")
        print(
            bad_tones[
                ["orig_row", "type", "EventCode", "latency"]
            ].to_string(index=False)
        )

    bad_no_tones = df[
        (df["type"] == "No Tone") & (df["EventCode"] != 96)
    ]
    if not bad_no_tones.empty:
        print("\nNo Tone rows with EventCode != 96 after repair:")
        print(
            bad_no_tones[
                ["orig_row", "type", "EventCode", "latency"]
            ].to_string(index=False)
        )

    # Rename original latency column
    df = df.rename(columns={"latency": "onset_latency"})

    # Insert onset latency in ms right after onset_latency
    onset_latency_ms = df["onset_latency"] * 1000.0 / sampling_rate_hz
    insert_idx = df.columns.get_loc("onset_latency") + 1
    df.insert(insert_idx, "onset_latency_ms", onset_latency_ms)

    # Use both Tone Onset and No Tone as event slots
    slot_mask = df["type"].isin(["Tone Onset", "No Tone"])
    slot_indices = df.index[slot_mask]
    n_slots = len(slot_indices)

    trial_ids = np.arange(n_slots) // n_tones_per_trial
    slot_in_trial = np.arange(n_slots) % n_tones_per_trial

    df["trial_id"] = pd.NA
    df["slot_in_trial"] = pd.NA

    df.loc[slot_indices, "trial_id"] = trial_ids
    df.loc[slot_indices, "slot_in_trial"] = slot_in_trial

    if n_slots % n_tones_per_trial != 0:
        slot_rows = df.loc[slot_mask, [
            "orig_row",
            "type",
            "EventCode",
            "onset_latency",
            "onset_latency_ms",
            "trial_id",
            "slot_in_trial",
        ]].copy()

        print("\nEvent-slot rows detected (Tone Onset + No Tone):")
        print(slot_rows.to_string())

        print("\nEvent-slot type counts:")
        print(df.loc[slot_mask, "type"].value_counts(dropna=False).to_string())

        print("\nLast 20 event-slot rows:")
        print(slot_rows.tail(20).to_string())

        print_bad_trial_info(
            df=df,
            n_tones_per_trial=n_tones_per_trial,
            input_path=input_path,
        )

        raise ValueError(
            f"Number of event-slot rows ({n_slots}) in "
            f"{os.path.basename(input_path)} is not a multiple of "
            f"{n_tones_per_trial}."
        )

    # Force missing onset latency for No Tone rows
    df.loc[df["type"] == "No Tone", "onset_latency_ms"] = np.nan

    # Compute durations within each trial, skipping No Tone rows
    onset_latency_diff_ms = pd.Series(np.nan, index=df.index, dtype="float64")

    diff_col = (
        df.loc[slot_mask]
        .groupby("trial_id", group_keys=False)
        .apply(compute_trial_durations)
    )

    insert_idx = df.columns.get_loc("onset_latency_ms") + 1
    df.insert(insert_idx, "onset_latency_diff_ms", onset_latency_diff_ms)
    df.loc[slot_mask, "onset_latency_diff_ms"] = diff_col

    # Keep all event slots except the last slot of each trial so the
    # number of rows matches the theoretical durations table
    valid_mask = slot_mask & (df["slot_in_trial"] < (n_tones_per_trial - 1))
    df_slots = df.loc[valid_mask].copy().reset_index(drop=True)

    return df, df_slots


def add_run_columns(df_base, df_slots, run_number):
    """Add onset, duration, and error columns for one run."""
    onsets_col = f"onsets_{run_number}"
    durations_col = f"durations_{run_number}"
    error_col = f"error_{run_number}"

    df_base[onsets_col] = df_slots["onset_latency_ms"].to_numpy()
    df_base[durations_col] = df_slots["onset_latency_diff_ms"].to_numpy()
    df_base[error_col] = (
        df_base[durations_col] - df_base["theoretical_durations"]
    )

    return df_base


def build_long_dataframe(df_wide, measurement_ids):
    """Convert wide prepared dataframe into long format."""
    base_cols = [
        "task",
        "subject",
        "modality",
        "condition",
        "trial",
        "theoretical_durations",
        "duration_type",
    ]

    long_dfs = []

    for measurement in measurement_ids:
        df_tmp = df_wide[base_cols].copy()
        df_tmp.insert(5, "measurement", measurement)

        df_tmp["onsets"] = df_wide[f"onsets_{measurement}"]
        df_tmp["durations"] = df_wide[f"durations_{measurement}"]
        df_tmp["error"] = df_wide[f"error_{measurement}"]

        long_dfs.append(df_tmp)

    df_long = pd.concat(long_dfs, axis=0, ignore_index=True)

    desired_cols = [
        "task",
        "subject",
        "modality",
        "condition",
        "trial",
        "measurement",
        "theoretical_durations",
        "duration_type",
        "onsets",
        "durations",
        "error",
    ]

    return df_long[desired_cols]


def build_subject_input_files(subject, input_task_stem):
    """Return the 3 input files for one subject and one task."""
    return [
        f"{subject}_audio_{input_task_stem}_01_ptb.tsv",
        f"{subject}_audio_{input_task_stem}_02_ptb.tsv",
        f"{subject}_audio_{input_task_stem}_03_ptb.tsv",
    ]


def build_theoretical_file(subject, theoretical_task_stem):
    """Return the theoretical file for one subject and one task."""
    return (
        f"theoretical_durations_{subject}_ses-01_run-01_"
        f"{theoretical_task_stem}_audio.tsv"
    )


# ---------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------
home_dir = os.path.expanduser("~")
script_dir = os.path.dirname(os.path.abspath(__file__))

input_dir = os.path.join(script_dir, "data_psychopy_ptb-st_feb2026")
theoretical_dir = os.path.join(script_dir, "theoretical_durations")
output_dir = os.path.join(script_dir, "curated_data_feb2026")

SAMPLING_RATE_HZ = 2048.0
SUBJECTS = ["sub-03", "sub-05"]

TASKS = {
    "production": {
        "input_task_stem": "prod",
        "theoretical_task_stem": "production",
        "n_tones_per_trial": 5,
    },
    "perception": {
        "input_task_stem": "percep",
        "theoretical_task_stem": "perception",
        "n_tones_per_trial": 6,
    },
    "ntfd": {
        "input_task_stem": "ntfd",
        "theoretical_task_stem": "ntfd",
        "n_tones_per_trial": 6,
    },
}

OUTPUT_FILE_WIDE = "encoding_wide_ptb.tsv"
OUTPUT_FILE_LONG = "encoding_long_ptb.tsv"

# ---------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------
if __name__ == "__main__":

    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    pd.set_option("display.max_colwidth", None)

    os.makedirs(output_dir, exist_ok=True)

    all_wide = []
    all_long = []
    all_raw_dfs = {}

    for task_name, task_cfg in TASKS.items():
        input_task_stem = task_cfg["input_task_stem"]
        theoretical_task_stem = task_cfg["theoretical_task_stem"]
        n_tones_per_trial = task_cfg["n_tones_per_trial"]

        for subject in SUBJECTS:
            input_files = build_subject_input_files(subject, input_task_stem)
            theoretical_file = build_theoretical_file(
                subject, theoretical_task_stem
            )
            theoretical_path = os.path.join(theoretical_dir, theoretical_file)

            df_theoretical = pd.read_csv(theoretical_path, sep="\t")

            if "theoretical_durations" not in df_theoretical.columns:
                if "durations" in df_theoretical.columns:
                    df_theoretical = df_theoretical.rename(
                        columns={"durations": "theoretical_durations"}
                    )
                else:
                    raise ValueError(
                        "Theoretical file must contain either "
                        "'theoretical_durations' or 'durations'."
                    )

            df_prepared = df_theoretical.copy()
            raw_dfs = {}
            measurement_ids = []

            for input_file in input_files:
                input_path = os.path.join(input_dir, input_file)

                run_str = input_file.split("_")[-2]
                run_number = int(run_str)
                measurement_ids.append(run_number)

                df_raw, df_slots = prepare_run_dataframe(
                    input_path=input_path,
                    sampling_rate_hz=SAMPLING_RATE_HZ,
                    n_tones_per_trial=n_tones_per_trial,
                )

                raw_dfs[run_number] = {
                    "raw": df_raw,
                    "slots": df_slots,
                    "file": input_file,
                }

                if len(df_prepared) != len(df_slots):
                    trial_sizes = df_raw.loc[
                        df_raw["type"].isin(["Tone Onset", "No Tone"])
                    ].groupby("trial_id").size()

                    print(f"\nRow mismatch detected for {input_file}.")
                    print(f"Task: {task_name}")
                    print(f"Theoretical rows: {len(df_prepared)}")
                    print(f"Parsed rows:       {len(df_slots)}")

                    print("\nSlot counts per trial:\n")
                    print(trial_sizes.to_string())

                    print_bad_trial_info(
                        df=df_raw,
                        n_tones_per_trial=n_tones_per_trial,
                        input_path=input_path,
                    )

                    raise ValueError(
                        f"Theoretical and physical files are not aligned for "
                        f"{input_file}."
                    )

                df_prepared = add_run_columns(
                    df_base=df_prepared,
                    df_slots=df_slots,
                    run_number=run_number,
                )

            desired_cols_wide = [
                "task",
                "subject",
                "modality",
                "condition",
                "trial",
                "theoretical_durations",
                "duration_type",
                "onsets_1",
                "durations_1",
                "error_1",
                "onsets_2",
                "durations_2",
                "error_2",
                "onsets_3",
                "durations_3",
                "error_3",
            ]

            missing_cols = [
                col for col in desired_cols_wide
                if col not in df_prepared.columns
            ]
            if missing_cols:
                raise ValueError(
                    f"Missing expected columns in final dataframe: "
                    f"{missing_cols}"
                )

            df_prepared = df_prepared[desired_cols_wide]

            df_long = build_long_dataframe(
                df_wide=df_prepared,
                measurement_ids=sorted(measurement_ids),
            )

            all_wide.append(df_prepared)
            all_long.append(df_long)
            all_raw_dfs[(task_name, subject)] = raw_dfs

    df_prepared_all = pd.concat(all_wide, axis=0, ignore_index=True)
    df_long_all = pd.concat(all_long, axis=0, ignore_index=True)

    output_path_wide = os.path.join(output_dir, OUTPUT_FILE_WIDE)
    output_path_long = os.path.join(output_dir, OUTPUT_FILE_LONG)

    df_prepared_all.to_csv(output_path_wide, sep="\t", index=False, 
                           na_rep="nan",)
    df_long_all.to_csv(output_path_long, sep="\t", index=False, 
                       na_rep="nan",)

    for task_name, subject in all_raw_dfs:
        for run_number in sorted(all_raw_dfs[(task_name, subject)]):
            print(
                f"\nOriginal dataframe "
                f"({all_raw_dfs[(task_name, subject)][run_number]['file']}):\n"
            )
            print(
                all_raw_dfs[(task_name, subject)][run_number]["raw"]
                .to_string(index=False)
            )

            print(
                f"\nParsed slot dataframe "
                f"({all_raw_dfs[(task_name, subject)][run_number]['file']}):\n"
            )
            print(
                all_raw_dfs[(task_name, subject)][run_number]["slots"]
                .to_string(index=False)
            )

    print("\nPrepared wide dataframe:\n")
    print(df_prepared_all.to_string(index=False))

    print("\nPrepared long dataframe:\n")
    print(df_long_all.to_string(index=False))

    print(f"\nSaved wide TSV output to:\n  {output_path_wide}")
    print(f"\nSaved long TSV output to:\n  {output_path_long}")