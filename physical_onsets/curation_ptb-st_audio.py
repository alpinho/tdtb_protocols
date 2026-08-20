#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prepare input data for physical-onset analysis.

This input data pertains to the experiment on the 2nd of April 2026,
where we tested the auditory protocols developed in psychopy
for both the ptb and the standard versions.

Author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Date of creation: 21st of April 2026
Last Update: April 2026

Compatibility: Python 3.10.16
"""

import os
import re
import pandas as pd


# ---------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------
def extract_measurement(in_path, drop_every, parser_tag, task_tag):
    """Extract onsets and durations from one measurement file."""
    df = pd.read_csv(in_path, sep="\t")

    df["latency_ms"] = (
        df["latency"] / SAMPLING_RATE_HZ
    ) * 1000.0

    is_sensor = df["markerLabel"] == "sensor"

    if parser_tag == "ONEST":
        keep_mask = is_sensor & (df["eventCode"].shift(1) == 11)

    elif parser_tag == "PTB":
        if "Percep_PTB" in task_tag:
            keep_mask = is_sensor
        else:
            keep_mask = is_sensor & (df["eventCode"].shift(1) != 12)

        # Remove only a very specific startup artifact:
        # two leading sensor rows before the first TTL, with identical
        # eventCode 32 or 64.
        ttl_rows = df.index[df["eventCode"] == 12]
        if len(ttl_rows) > 0:
            first_ttl_idx = ttl_rows[0]
            pre_ttl = df.loc[:first_ttl_idx - 1]

            if len(pre_ttl) >= 2:
                first_two = pre_ttl.iloc[:2]

                first_two_are_sensor = (
                    (first_two["markerLabel"] == "sensor").all()
                )
                first_two_same_code = (
                    first_two["eventCode"].iloc[0]
                    == first_two["eventCode"].iloc[1]
                )
                first_two_code_ok = (
                    first_two["eventCode"].iloc[0] in (32, 64)
                )

                if (
                    first_two_are_sensor
                    and first_two_same_code
                    and first_two_code_ok
                ):
                    drop_idx = first_two.index
                    keep_mask.loc[drop_idx] = False

    else:
        raise ValueError(f"Unknown parser tag: {parser_tag}")

    df_sel = df[keep_mask].copy()
    df_sel["orig_idx"] = df_sel.index

    # PTB special rule for Production and NTFD:
    # if original row i is preceded by 12 and rows i,i+1 are 64/32 or
    # 32/64, row i is already excluded by the base PTB rule; exclude
    # only row i+1.
    if parser_tag == "PTB" and "Percep_PTB" not in task_tag:
        codes = df["eventCode"]
        forbidden_first = codes.shift(1).eq(12) & (
            ((codes == 64) & (codes.shift(-1) == 32))
            | ((codes == 32) & (codes.shift(-1) == 64))
        )
        forbidden_second_idx = set(
            df.index[forbidden_first.shift(1, fill_value=False)]
        )

        if forbidden_second_idx:
            df_sel = df_sel[
                ~df_sel["orig_idx"].isin(forbidden_second_idx)
            ].copy()

    # General rule:
    # if adjacent kept rows are 64/32 or 32/64, keep the first and
    # discard the second. Do this left-to-right, non-overlapping.
    codes = df_sel["eventCode"].to_numpy()
    orig_idx = df_sel["orig_idx"].to_numpy()

    keep_rows = [True] * len(df_sel)

    i = 0
    n_rows = len(df_sel)
    while i < n_rows - 1:
        curr_code = codes[i]
        next_code = codes[i + 1]
        curr_idx = orig_idx[i]
        next_idx = orig_idx[i + 1]

        is_adjacent = next_idx == curr_idx + 1
        is_alt_pair = (
            (curr_code == 64 and next_code == 32)
            or (curr_code == 32 and next_code == 64)
        )

        if is_adjacent and is_alt_pair:
            keep_rows[i + 1] = False
            i += 2
        else:
            i += 1

    df_sel = df_sel.loc[keep_rows].copy()

    onsets = df_sel["latency_ms"].reset_index(drop=True)

    df_out = pd.DataFrame({"onsets": onsets})
    df_out["durations"] = (
        df_out["onsets"].shift(-1) - df_out["onsets"]
    )

    df_out = df_out.iloc[:-1].copy()

    keep = (df_out.index + 1) % drop_every != 0
    df_out = df_out[keep].reset_index(drop=True)

    return df_out


def extract_sequence_measurement_onest(in_path):
    """Extract full-trial ONEST onsets for sequence_long output."""
    df = pd.read_csv(in_path, sep="\t").copy()

    df["latency_ms"] = (
        df["latency"] / SAMPLING_RATE_HZ
    ) * 1000.0

    rows = []
    i = 0
    n_rows = len(df)

    while i < n_rows:
        code = df.at[i, "eventCode"]
        label = df.at[i, "markerLabel"]

        if label == "TTL" and code in (11, 12):
            j = i + 1

            # Keep only TTL events that have a following sensor row.
            if j < n_rows and df.at[j, "markerLabel"] == "sensor":
                rows.append({
                    "onset": df.at[i, "latency_ms"],
                    "event_type": "TTL",
                    "event_code": code
                })
                rows.append({
                    "onset": df.at[j, "latency_ms"],
                    "event_type": "sensor",
                    "event_code": code
                })

                # If two consecutive sensors occur, discard the second.
                if (
                    j + 1 < n_rows
                    and df.at[j + 1, "markerLabel"] == "sensor"
                ):
                    i = j + 2
                else:
                    i = j + 1
            else:
                i += 1
        else:
            i += 1

    return pd.DataFrame(rows)


def get_measurement_number(fname):
    """Return leading number before first underscore."""
    match = re.match(r"^(\d+)_", fname)
    if match is None:
        raise ValueError(
            f"Could not extract leading number from filename: {fname}"
        )
    return int(match.group(1))


def get_buf_tag(fname):
    """Return buf tag such as buf-01."""
    match = re.search(r"(buf-\d+)", fname)
    if match is None:
        raise ValueError(f"Could not extract buf tag from filename: {fname}")
    return match.group(1)


def set_task_column(df, task_name):
    """Set task column, inserting it first if missing."""
    df = df.copy()

    if "task" in df.columns:
        df["task"] = task_name
    else:
        df.insert(0, "task", task_name)

    return df


def reorder_long_columns(df):
    """Place measurement after trial."""
    df = df.copy()

    if "measurement" not in df.columns:
        return df

    cols = list(df.columns)
    cols.remove("measurement")

    if "trial" in cols:
        trial_idx = cols.index("trial")
        cols.insert(trial_idx + 1, "measurement")
    else:
        cols.insert(0, "measurement")

    return df[cols]


def process_task(task_tag, task_name, theoretical_file, drop_every,
                 buf_tag, parser_tag):
    """Process one task for one buffer tag."""
    theo_path = os.path.join(theoretical_dir, theoretical_file)
    df_theo = pd.read_csv(theo_path, sep="\t")

    task_files = [
        fname for fname in os.listdir(input_dir)
        if task_tag in fname
        and buf_tag in fname
        and fname.endswith(".tsv")
    ]

    if not task_files:
        raise ValueError(
            f"No files found for task {task_name} and buffer {buf_tag}."
        )

    fnames = sorted(task_files, key=get_measurement_number)

    df_wide = set_task_column(df_theo, task_name)
    long_parts = []

    for meas_idx, fname in enumerate(fnames, start=1):
        in_path = os.path.join(input_dir, fname)
        df_meas = extract_measurement(
            in_path, drop_every, parser_tag, task_tag
        )

        if len(df_theo) != len(df_meas):
            raise ValueError(
                "Length mismatch between theoretical rows and "
                f"extracted data for {fname}: {len(df_theo)} "
                f"theoretical rows vs {len(df_meas)} extracted rows."
            )

        df_wide[f"onsets_{meas_idx}"] = df_meas["onsets"]
        df_wide[f"durations_{meas_idx}"] = df_meas["durations"]
        df_wide[f"error_{meas_idx}"] = (
            df_wide[f"durations_{meas_idx}"]
            - df_wide["theoretical_durations"]
        )

        df_long_part = set_task_column(df_theo, task_name)
        df_long_part["measurement"] = meas_idx
        df_long_part["onsets"] = df_meas["onsets"]
        df_long_part["durations"] = df_meas["durations"]
        df_long_part["error"] = (
            df_long_part["durations"]
            - df_long_part["theoretical_durations"]
        )
        long_parts.append(df_long_part)

    df_long = pd.concat(long_parts, ignore_index=True)
    df_long = reorder_long_columns(df_long)

    return df_wide, df_long


def get_buf_tags(parser_tag):
    """Return sorted buffer tags for one parser family."""
    return sorted({
        get_buf_tag(fname)
        for fname in os.listdir(input_dir)
        if (
            (
                f"Prod_{parser_tag}" in fname
                or f"Percep_{parser_tag}" in fname
                or f"NTFD_{parser_tag}" in fname
            )
            and fname.endswith(".tsv")
        )
    })


def split_sequence_into_trials(df_meas, task_name, fname):
    """Split extracted ONEST sequence rows into trials."""
    if len(df_meas) % 2 != 0:
        raise ValueError(
            f"Odd number of sequence rows in {fname}."
        )

    pair_codes = df_meas["event_code"].iloc[::2].to_list()
    trials = []

    if task_name == "Production":
        i = 0
        n_codes = len(pair_codes)

        while i < n_codes:
            chunk6 = pair_codes[i:i + 6]
            chunk5 = pair_codes[i:i + 5]

            if len(chunk6) == 6 and chunk6 == [11, 11, 11, 11, 11, 12]:
                trials.append(chunk6)
                i += 6
            elif len(chunk5) == 5 and chunk5 == [11, 11, 11, 11, 11]:
                trials.append(chunk5)
                i += 5
            else:
                raise ValueError(
                    "Could not parse Production trial structure in "
                    f"{fname} near event-pair {i + 1}."
                )

    elif task_name == "Perception":
        n_codes = len(pair_codes)
        if n_codes % 6 != 0:
            raise ValueError(
                f"Unexpected number of event pairs for Perception in {fname}."
            )

        for i in range(0, n_codes, 6):
            chunk = pair_codes[i:i + 6]
            if chunk != [11, 11, 11, 11, 11, 11]:
                raise ValueError(
                    "Could not parse Perception trial structure in "
                    f"{fname} near event-pair {i + 1}."
                )
            trials.append(chunk)

    elif task_name == "NTFD":
        i = 0
        n_codes = len(pair_codes)

        while i < n_codes:
            chunk7 = pair_codes[i:i + 7]
            chunk6 = pair_codes[i:i + 6]

            if len(chunk7) == 7 and chunk7 == [11, 11, 11, 11, 11, 11, 12]:
                trials.append(chunk7)
                i += 7
            elif len(chunk6) == 6 and chunk6 == [11, 11, 11, 11, 11, 11]:
                trials.append(chunk6)
                i += 6
            else:
                raise ValueError(
                    "Could not parse NTFD trial structure in "
                    f"{fname} near event-pair {i + 1}."
                )

    else:
        raise ValueError(f"Unknown task: {task_name}")

    return trials


def get_trial_stimulus_types(task_name, trial_codes):
    """Return stimulus labels for one trial."""
    if task_name == "Production":
        if trial_codes == [11, 11, 11, 11, 11, 12]:
            return (
                ["encoding"] * 4
                + ["decision"]
                + ["rest"]
            )
        if trial_codes == [11, 11, 11, 11, 11]:
            return (
                ["encoding"] * 4
                + ["rest"]
            )

    elif task_name == "Perception":
        if trial_codes == [11, 11, 11, 11, 11, 11]:
            return (
                ["encoding"] * 5
                + ["rest"]
            )

    elif task_name == "NTFD":
        if trial_codes == [11, 11, 11, 11, 11, 11, 12]:
            return (
                ["encoding"] * 5
                + ["decision"]
                + ["rest"]
            )
        if trial_codes == [11, 11, 11, 11, 11, 11]:
            return (
                ["encoding"] * 5
                + ["rest"]
            )

    raise ValueError(
        "Could not assign stimulus types for "
        f"{task_name} with trial_codes {trial_codes}."
    )


def build_sequence_template_onest(df_theo, task_name, df_meas, fname):
    """Build sequence template for one ONEST measurement."""
    base_cols = ["subject", "modality", "condition", "trial"]
    df_trials = df_theo[base_cols].drop_duplicates().reset_index(drop=True)

    trial_codes_list = split_sequence_into_trials(
        df_meas, task_name, fname
    )

    if len(df_trials) != len(trial_codes_list):
        raise ValueError(
            "Number of extracted trials does not match theoretical "
            f"trials for {fname}: {len(df_trials)} theoretical trials "
            f"vs {len(trial_codes_list)} extracted trials."
        )

    rows = []
    task_label = task_name.lower()

    for idx, trial_row in df_trials.iterrows():
        trial_codes = trial_codes_list[idx]
        stim_types = get_trial_stimulus_types(task_name, trial_codes)

        for stimulus_type in stim_types:
            rows.append({
                "task": task_label,
                "subject": trial_row["subject"],
                "modality": trial_row["modality"],
                "condition": trial_row["condition"],
                "trial": trial_row["trial"],
                "stimulus_type": stimulus_type,
                "event_type": "TTL",
            })
            rows.append({
                "task": task_label,
                "subject": trial_row["subject"],
                "modality": trial_row["modality"],
                "condition": trial_row["condition"],
                "trial": trial_row["trial"],
                "stimulus_type": stimulus_type,
                "event_type": "sensor",
            })

    return pd.DataFrame(rows)


def process_task_sequence_onest(task_tag, task_name, theoretical_file,
                                buf_tag):
    """Process one task into full-trial sequence_long for ONEST."""
    theo_path = os.path.join(theoretical_dir, theoretical_file)
    df_theo = pd.read_csv(theo_path, sep="\t")

    task_files = [
        fname for fname in os.listdir(input_dir)
        if task_tag in fname
        and buf_tag in fname
        and fname.endswith(".tsv")
    ]

    if not task_files:
        raise ValueError(
            f"No files found for task {task_name} and buffer {buf_tag}."
        )

    fnames = sorted(task_files, key=get_measurement_number)
    long_parts = []

    for meas_idx, fname in enumerate(fnames, start=1):
        in_path = os.path.join(input_dir, fname)
        df_meas = extract_sequence_measurement_onest(in_path)

        df_template = build_sequence_template_onest(
            df_theo, task_name, df_meas, fname
        )

        if len(df_template) != len(df_meas):
            raise ValueError(
                "Length mismatch between expected sequence rows and "
                f"extracted data for {fname}: {len(df_template)} "
                f"expected rows vs {len(df_meas)} extracted rows."
            )

        df_long_part = df_template.copy()
        df_long_part["measurement"] = meas_idx
        df_long_part["onset"] = df_meas["onset"].to_numpy()

        if not (df_long_part["event_type"] == df_meas["event_type"]).all():
            raise ValueError(
                f"Event-type mismatch while processing {fname}."
            )

        long_parts.append(df_long_part)

    df_long = pd.concat(long_parts, ignore_index=True)
    df_long = reorder_long_columns(df_long)

    cols = [
        "task",
        "subject",
        "modality",
        "condition",
        "trial",
        "measurement",
        "onset",
        "event_type",
        "stimulus_type",
    ]
    return df_long[cols]


# ---------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------
SAMPLING_RATE_HZ = 2048.0

script_dir = os.path.dirname(os.path.abspath(__file__))

input_dir = os.path.join(
    script_dir,
    "data_psychopy_ptb-st_audio-only_april2026"
)
theoretical_dir = os.path.join(script_dir, "theoretical_durations")
output_dir = os.path.join(script_dir, "curated_data_april2026")

# ---------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------
if __name__ == "__main__":
    parser_specs = [
        {
            "parser_tag": "ONEST",
            "output_prefix": "st"
        },
        {
            "parser_tag": "PTB",
            "output_prefix": "ptb"
        }
    ]

    os.makedirs(output_dir, exist_ok=True)

    for parser_spec in parser_specs:
        parser_tag = parser_spec["parser_tag"]
        output_prefix = parser_spec["output_prefix"]

        buf_tags = get_buf_tags(parser_tag)

        if not buf_tags:
            print(f"No files found for parser tag '{parser_tag}'.")
            continue

        for buf_tag in buf_tags:
            prod_wide, prod_long = process_task(
                task_tag=f"Prod_{parser_tag}",
                task_name="Production",
                theoretical_file=(
                    "theoretical_durations_sub-05_ses-01_run-01_"
                    "production_audio_behav.tsv"
                ),
                drop_every=5,
                buf_tag=buf_tag,
                parser_tag=parser_tag
            )

            percep_wide, percep_long = process_task(
                task_tag=f"Percep_{parser_tag}",
                task_name="Perception",
                theoretical_file=(
                    "theoretical_durations_sub-05_ses-01_run-01_"
                    "perception_audio_behav.tsv"
                ),
                drop_every=6,
                buf_tag=buf_tag,
                parser_tag=parser_tag
            )

            ntfd_wide, ntfd_long = process_task(
                task_tag=f"NTFD_{parser_tag}",
                task_name="NTFD",
                theoretical_file=(
                    "theoretical_durations_sub-05_ses-01_run-01_"
                    "ntfd_audio_behav.tsv"
                ),
                drop_every=6,
                buf_tag=buf_tag,
                parser_tag=parser_tag
            )

            df_wide = pd.concat(
                [prod_wide, percep_wide, ntfd_wide],
                ignore_index=True
            )

            df_long = pd.concat(
                [prod_long, percep_long, ntfd_long],
                ignore_index=True
            )
            df_long = reorder_long_columns(df_long)

            out_path_wide = os.path.join(
                output_dir,
                f"encoding_wide_{output_prefix}_{buf_tag}.tsv"
            )
            df_wide.to_csv(out_path_wide, sep="\t", index=False)

            out_path_long = os.path.join(
                output_dir,
                f"encoding_long_{output_prefix}_{buf_tag}.tsv"
            )
            df_long.to_csv(out_path_long, sep="\t", index=False)

            print(f"Saved: {out_path_wide}")
            print(f"Saved: {out_path_long}")

            if parser_tag == "ONEST":
                prod_seq = process_task_sequence_onest(
                    task_tag="Prod_ONEST",
                    task_name="Production",
                    theoretical_file=(
                        "theoretical_durations_sub-05_ses-01_run-01_"
                        "production_audio_behav.tsv"
                    ),
                    buf_tag=buf_tag
                )

                percep_seq = process_task_sequence_onest(
                    task_tag="Percep_ONEST",
                    task_name="Perception",
                    theoretical_file=(
                        "theoretical_durations_sub-05_ses-01_run-01_"
                        "perception_audio_behav.tsv"
                    ),
                    buf_tag=buf_tag
                )

                ntfd_seq = process_task_sequence_onest(
                    task_tag="NTFD_ONEST",
                    task_name="NTFD",
                    theoretical_file=(
                        "theoretical_durations_sub-05_ses-01_run-01_"
                        "ntfd_audio_behav.tsv"
                    ),
                    buf_tag=buf_tag
                )

                df_sequence = pd.concat(
                    [prod_seq, percep_seq, ntfd_seq],
                    ignore_index=True
                )
                df_sequence = reorder_long_columns(df_sequence)

                out_path_seq = os.path.join(
                    output_dir,
                    f"sequence_long_{output_prefix}_{buf_tag}.tsv"
                )
                df_sequence.to_csv(out_path_seq, sep="\t", index=False)

                print(f"Saved: {out_path_seq}")