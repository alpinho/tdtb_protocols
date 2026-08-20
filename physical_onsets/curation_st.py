#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prepare input data for physical onset analysis. This input-data
pertains to the experiment on the 19th of February 2026, where we
tested the standard version of the scripts in psychopy with some
improvements (st version).

Author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Date of creation: 17th of March 2026
Last Update: March 2026

Compatibility: Python 3.10.16
"""

import os
import numpy as np
import pandas as pd


TTL_BASE_CODE = 2816
FULL_TONE_CODE = 2912
TARGET_TONE_SUM = 96

EVENT_TYPE_BY_MODALITY = {
    "audio": "Tone Onset",
    "visual": "Visual&TTL Onset",
}

TTL_TYPE_BY_MODALITY = {
    "audio": "TTL",
    "visual": "TTL Onset",
}

ROLL_GAP_THRESHOLD_MS = 2000.0

TASK_SPECS = [
    {
        "task_label": "production",
        "input_task_stem": "prod",
        "n_events_per_chunk": 6,
    },
    {
        "task_label": "perception",
        "input_task_stem": "percep",
        "n_events_per_chunk": 7,
    },
    {
        "task_label": "ntfd",
        "input_task_stem": "ntfd",
        "n_events_per_chunk": 7,
    },
]


# ---------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------
def _tone_piece_value(event_code):
    """Return the tone-only part of an ST EventCode.

    In ST files, a full onset row is usually stored as 2912, which is a
    TTL base code (2816) plus the logical tone code (96). Split rows can
    therefore appear as e.g. 2880 followed by 32, corresponding to 64 +
    32 = 96.
    """
    if pd.isna(event_code):
        return np.nan

    event_code = int(event_code)
    if event_code >= TTL_BASE_CODE:
        return event_code - TTL_BASE_CODE
    return event_code


def repair_split_tone_onsets(df, event_type):
    """Collapse split ST onset rows into one logical onset row.

    Standard complete rows are kept as-is when EventCode == 2912.
    Split rows are identified among consecutive non-TTL / non-offset rows
    whose tone-only EventCode parts sum to 96. The first row is kept and
    relabeled as a full onset row with EventCode 2912.
    """
    if "EventCode" not in df.columns or "type" not in df.columns:
        raise ValueError("Input dataframe must contain 'type' and 'EventCode'.")

    df = df.copy().reset_index(drop=True)
    rows_to_drop = []
    i = 0

    excluded_types = {
        "TTL",
        "TTL Onset",
        "TTL Offset",
        "Response Event",
        "Feedback Onset",
    }

    while i < len(df):
        row_type = str(df.at[i, "type"])
        event_code = df.at[i, "EventCode"]

        if row_type == event_type and int(event_code) == FULL_TONE_CODE:
            i += 1
            continue

        if row_type in excluded_types:
            i += 1
            continue

        piece_value = _tone_piece_value(event_code)
        if pd.isna(piece_value):
            i += 1
            continue

        cum_sum = piece_value
        j = i

        while cum_sum < TARGET_TONE_SUM and (j + 1) < len(df):
            next_idx = j + 1
            next_type = str(df.at[next_idx, "type"])

            if next_type in excluded_types or next_type == event_type:
                break

            next_piece = _tone_piece_value(df.at[next_idx, "EventCode"])
            if pd.isna(next_piece):
                break

            cum_sum += next_piece
            j = next_idx

        if cum_sum == TARGET_TONE_SUM:
            df.at[i, "type"] = event_type
            df.at[i, "EventCode"] = FULL_TONE_CODE
            if j > i:
                rows_to_drop.extend(range(i + 1, j + 1))
            i = j + 1
        else:
            i += 1

    if rows_to_drop:
        df = df.drop(index=rows_to_drop).reset_index(drop=True)

    return df


def _find_previous_ttl_index(df, onset_idx, event_type, ttl_type):
    """Return the closest preceding TTL row for a given onset row."""
    idx = onset_idx - 1

    while idx >= 0:
        row_type = str(df.at[idx, "type"])

        if row_type == ttl_type:
            return idx

        if row_type == event_type:
            return None

        idx -= 1

    return None


def _append_sequence_pair(
    sequence_rows,
    df,
    onset_idx,
    event_type,
    ttl_type,
    stimulus_type,
    trial_id,
    measurement_id,
):
    """Append the TTL row and its corresponding onset row."""
    ttl_idx = _find_previous_ttl_index(
        df=df,
        onset_idx=onset_idx,
        event_type=event_type,
        ttl_type=ttl_type,
    )

    if ttl_idx is not None:
        sequence_rows.append(
            {
                "trial_id_internal": trial_id,
                "measurement": measurement_id,
                "onset": df.at[ttl_idx, "onset_latency_ms"],
                "event_type": df.at[ttl_idx, "type"],
                "stimulus_type": stimulus_type,
            }
        )

    sequence_rows.append(
        {
            "trial_id_internal": trial_id,
            "measurement": measurement_id,
            "onset": df.at[onset_idx, "onset_latency_ms"],
            "event_type": df.at[onset_idx, "type"],
            "stimulus_type": stimulus_type,
        }
    )


def _append_sequence_chunk(
    sequence_rows,
    df,
    chunk_indices,
    chunk_labels,
    event_type,
    ttl_type,
    trial_id,
    measurement_id,
):
    """Append labeled TTL/onset rows for one processed chunk."""
    for onset_idx, stim_label in zip(chunk_indices, chunk_labels):
        _append_sequence_pair(
            sequence_rows=sequence_rows,
            df=df,
            onset_idx=onset_idx,
            event_type=event_type,
            ttl_type=ttl_type,
            stimulus_type=stim_label,
            trial_id=trial_id,
            measurement_id=measurement_id,
        )


def assign_trials_with_rollover(
    df,
    event_type,
    ttl_type,
    n_events_per_chunk,
    measurement_id,
    drop_first_event=False,
    roll_gap_threshold_ms=ROLL_GAP_THRESHOLD_MS,
):
    """Assign trials using rollover chunking.

    Full chunk logic:
    1. Pick the first n_events_per_chunk onset events.
    2. Evaluate whether the last minus second-last onset is > threshold.
    3. If smaller or equal, the next chunk starts after the last event.
       If bigger, the last event becomes the first event of the next
       chunk.
    4. The last event of the chunk is not part of the final trial rows.
       Final rows come from the first n_events_per_chunk - 2 events.
       Durations are computed using the first n_events_per_chunk - 1
       events.

    Sequence labeling:
    - First n_events_per_chunk - 2 events -> encoding
    - If last_gap <= threshold:
        * second-last event -> decision
        * last event -> rest
    - If last_gap > threshold:
        * second-last event -> rest
        * last event is reused in the next chunk and is not labeled here

    Tail logic:
    - If the last remaining data equals n_events_per_chunk - 1, keep it
      as the final chunk.
    - Final rows then come from the first n_events_per_chunk - 2 events.
      Durations are computed using all remaining events.
    - The final remaining event in this tail chunk is labeled rest.
    - If the remaining data is lower than n_events_per_chunk - 1,
      discard it as spurious tail data.
    """
    onset_indices = list(df.index[df["type"] == event_type])

    if drop_first_event:
        if not onset_indices:
            raise ValueError(
                "Cannot discard the first onset row because no onset rows "
                "were found."
            )
        onset_indices = onset_indices[1:]

    min_tail_chunk = n_events_per_chunk - 1
    n_output_rows = n_events_per_chunk - 2

    if len(onset_indices) < min_tail_chunk:
        onset_rows = df.loc[df["type"] == event_type, [
            "orig_row",
            "type",
            "EventCode",
            "onset_latency",
            "onset_latency_ms",
        ]].copy()
        print(f"\n{event_type} rows detected:")
        print(onset_rows.to_string(index=False))
        raise ValueError(
            f"Not enough {event_type} rows in the input file to form one "
            f"final chunk."
        )

    df["trial_id"] = pd.NA
    df["slot_in_trial"] = pd.NA

    selected_indices = []
    selected_trial_ids = []
    selected_slots = []
    selected_durations = []
    sequence_rows = []

    start_pos = 0
    trial_id = 0

    while True:
        remaining = len(onset_indices) - start_pos

        if remaining < min_tail_chunk:
            break

        if remaining == min_tail_chunk:
            chunk_indices = onset_indices[start_pos:start_pos + min_tail_chunk]
            chunk_onsets = df.loc[chunk_indices, "onset_latency_ms"].to_numpy()

            for slot in range(n_output_rows):
                row_idx = chunk_indices[slot]
                duration_ms = chunk_onsets[slot + 1] - chunk_onsets[slot]

                selected_indices.append(row_idx)
                selected_trial_ids.append(trial_id)
                selected_slots.append(slot)
                selected_durations.append(duration_ms)

                df.at[row_idx, "trial_id"] = trial_id
                df.at[row_idx, "slot_in_trial"] = slot

            sequence_labels = ["encoding"] * n_output_rows + ["rest"]
            _append_sequence_chunk(
                sequence_rows=sequence_rows,
                df=df,
                chunk_indices=chunk_indices,
                chunk_labels=sequence_labels,
                event_type=event_type,
                ttl_type=ttl_type,
                trial_id=trial_id,
                measurement_id=measurement_id,
            )

            trial_id += 1
            break

        chunk_indices = onset_indices[start_pos:start_pos + n_events_per_chunk]
        chunk_onsets = df.loc[chunk_indices, "onset_latency_ms"].to_numpy()
        last_gap = chunk_onsets[-1] - chunk_onsets[-2]

        for slot in range(n_output_rows):
            row_idx = chunk_indices[slot]
            duration_ms = chunk_onsets[slot + 1] - chunk_onsets[slot]

            selected_indices.append(row_idx)
            selected_trial_ids.append(trial_id)
            selected_slots.append(slot)
            selected_durations.append(duration_ms)

            df.at[row_idx, "trial_id"] = trial_id
            df.at[row_idx, "slot_in_trial"] = slot

        if last_gap <= roll_gap_threshold_ms:
            sequence_labels = (
                ["encoding"] * n_output_rows + ["decision", "rest"]
            )
            _append_sequence_chunk(
                sequence_rows=sequence_rows,
                df=df,
                chunk_indices=chunk_indices,
                chunk_labels=sequence_labels,
                event_type=event_type,
                ttl_type=ttl_type,
                trial_id=trial_id,
                measurement_id=measurement_id,
            )
            start_pos += n_events_per_chunk
        else:
            kept_sequence_indices = chunk_indices[:-1]
            sequence_labels = ["encoding"] * n_output_rows + ["rest"]
            _append_sequence_chunk(
                sequence_rows=sequence_rows,
                df=df,
                chunk_indices=kept_sequence_indices,
                chunk_labels=sequence_labels,
                event_type=event_type,
                ttl_type=ttl_type,
                trial_id=trial_id,
                measurement_id=measurement_id,
            )
            start_pos += n_events_per_chunk - 1

        trial_id += 1

    df_tones = df.loc[selected_indices].copy().reset_index(drop=True)
    df_tones["trial_id"] = selected_trial_ids
    df_tones["slot_in_trial"] = selected_slots
    df_tones["onset_latency_diff_ms"] = selected_durations

    df_sequence = pd.DataFrame(sequence_rows)

    return df, df_tones, df_sequence


def prepare_st_tone_dataframe(
    input_path,
    sampling_rate_hz,
    event_type,
    ttl_type,
    n_events_per_chunk,
    measurement_id,
    drop_first_event=False,
):
    """Load one ST file and return raw + parsed onset dataframes."""
    df = pd.read_csv(input_path, sep="\t")
    df["orig_row"] = np.arange(len(df))

    df = repair_split_tone_onsets(df, event_type=event_type)
    df = df.rename(columns={"latency": "onset_latency"})

    onset_latency_ms = df["onset_latency"] * 1000.0 / sampling_rate_hz
    insert_idx = df.columns.get_loc("onset_latency") + 1
    df.insert(insert_idx, "onset_latency_ms", onset_latency_ms)

    df_raw, df_tones, df_sequence = assign_trials_with_rollover(
        df=df,
        event_type=event_type,
        ttl_type=ttl_type,
        n_events_per_chunk=n_events_per_chunk,
        measurement_id=measurement_id,
        drop_first_event=drop_first_event,
        roll_gap_threshold_ms=ROLL_GAP_THRESHOLD_MS,
    )

    return df_raw, df_tones, df_sequence


def add_run_columns(df_base, df_slots, measurement_id):
    """Add onset, duration, and error columns for one measurement."""
    onsets_col = f"onsets_{measurement_id}"
    durations_col = f"durations_{measurement_id}"
    error_col = f"error_{measurement_id}"

    if df_slots is None:
        df_base[onsets_col] = np.nan
        df_base[durations_col] = np.nan
        df_base[error_col] = np.nan
        return df_base

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


def build_trial_metadata(df_theoretical):
    """Return one metadata row per theoretical trial."""
    meta_cols = ["task", "subject", "modality", "condition", "trial"]

    df_meta = (
        df_theoretical[meta_cols]
        .drop_duplicates()
        .sort_values("trial")
        .reset_index(drop=True)
    )
    df_meta["trial_id_internal"] = np.arange(len(df_meta))

    return df_meta


def add_sequence_metadata(df_sequence, df_theoretical):
    """Add task/subject/modality/condition/trial to sequence rows."""
    desired_cols = [
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

    if df_sequence.empty:
        return pd.DataFrame(columns=desired_cols)

    df_meta = build_trial_metadata(df_theoretical)

    df_sequence = df_sequence.merge(
        df_meta,
        on="trial_id_internal",
        how="left",
    )

    return df_sequence[desired_cols]


def build_input_file(input_dir, subject, modality, task_stem, measurement_id):
    """Return one ST physical-log input path."""
    return os.path.join(
        input_dir,
        f"{subject}_{modality}_{task_stem}_{measurement_id:02d}_st.tsv",
    )


def build_theoretical_file(subject, theoretical_task_stem, modality):
    """Return the theoretical file for one subject and one task."""
    return (
        f"theoretical_durations_{subject}_ses-01_run-01_"
        f"{theoretical_task_stem}_{modality}_behav.tsv"
    )


def load_theoretical_dataframe(theoretical_path):
    """Load and standardize the theoretical durations dataframe."""
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

    return df_theoretical


def should_drop_first_event(task_label, modality, measurement_id):
    """Return whether the first onset row should be discarded."""
    return (
        task_label == "production"
        and modality == "visual"
        and measurement_id == 2
    )


# ---------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------
SAMPLING_RATE_HZ = 2048.0

home_dir = os.path.expanduser("~")
script_dir = os.path.dirname(os.path.abspath(__file__))

input_dir = os.path.join(script_dir, "data_psychopy_ptb-st_feb2026")
theoretical_dir = os.path.join(script_dir, "theoretical_durations")
output_dir = os.path.join(script_dir, "curated_data_feb2026")

SUBJECT = "sub-05"
MODALITIES = ["audio", "visual"]
EXPECTED_MEASUREMENTS = [1, 2]

OUTPUT_FILE_WIDE = "encoding_wide_st.tsv"
OUTPUT_FILE_LONG = "encoding_long_st.tsv"
OUTPUT_FILE_SEQUENCE = "sequence_long_st.tsv"


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
    all_sequence = []
    all_raw_dfs = {}

    for task_spec in TASK_SPECS:
        task_label = task_spec["task_label"]
        input_task_stem = task_spec["input_task_stem"]
        n_events_per_chunk = task_spec["n_events_per_chunk"]

        all_raw_dfs[task_label] = {}

        for modality in MODALITIES:
            event_type = EVENT_TYPE_BY_MODALITY[modality]
            ttl_type = TTL_TYPE_BY_MODALITY[modality]
            theoretical_file = build_theoretical_file(
                SUBJECT,
                task_label,
                modality,
            )
            theoretical_path = os.path.join(theoretical_dir, theoretical_file)

            df_prepared = load_theoretical_dataframe(theoretical_path)
            raw_dfs = {}
            measurement_ids = []

            for measurement_id in EXPECTED_MEASUREMENTS:
                input_file = build_input_file(
                    input_dir=input_dir,
                    subject=SUBJECT,
                    modality=modality,
                    task_stem=input_task_stem,
                    measurement_id=measurement_id,
                )
                measurement_ids.append(measurement_id)

                if os.path.exists(input_file):
                    drop_first_event = should_drop_first_event(
                        task_label=task_label,
                        modality=modality,
                        measurement_id=measurement_id,
                    )

                    df_raw, df_tones, df_sequence = prepare_st_tone_dataframe(
                        input_path=input_file,
                        sampling_rate_hz=SAMPLING_RATE_HZ,
                        event_type=event_type,
                        ttl_type=ttl_type,
                        n_events_per_chunk=n_events_per_chunk,
                        measurement_id=measurement_id,
                        drop_first_event=drop_first_event,
                    )

                    if len(df_prepared) != len(df_tones):
                        print(
                            f"\nRow mismatch detected for "
                            f"{os.path.basename(input_file)}."
                        )
                        print(f"Theoretical rows: {len(df_prepared)}")
                        print(f"Parsed rows:       {len(df_tones)}")

                        raise ValueError(
                            "Theoretical and physical files are not aligned "
                            f"for {os.path.basename(input_file)}."
                        )

                    df_prepared = add_run_columns(
                        df_base=df_prepared,
                        df_slots=df_tones,
                        measurement_id=measurement_id,
                    )

                    df_sequence = add_sequence_metadata(
                        df_sequence=df_sequence,
                        df_theoretical=df_prepared,
                    )
                    all_sequence.append(df_sequence)

                    raw_dfs[measurement_id] = {
                        "raw": df_raw,
                        "slots": df_tones,
                        "sequence": df_sequence,
                        "file": os.path.basename(input_file),
                        "found": True,
                        "modality": modality,
                        "drop_first_event": drop_first_event,
                        "event_type": event_type,
                    }
                else:
                    df_prepared = add_run_columns(
                        df_base=df_prepared,
                        df_slots=None,
                        measurement_id=measurement_id,
                    )
                    raw_dfs[measurement_id] = {
                        "raw": None,
                        "slots": None,
                        "sequence": None,
                        "file": os.path.basename(input_file),
                        "found": False,
                        "modality": modality,
                        "drop_first_event": False,
                        "event_type": event_type,
                    }

            desired_cols_wide = [
                "task",
                "subject",
                "modality",
                "condition",
                "trial",
                "theoretical_durations",
                "duration_type",
            ]

            for measurement in sorted(measurement_ids):
                desired_cols_wide.extend([
                    f"onsets_{measurement}",
                    f"durations_{measurement}",
                    f"error_{measurement}",
                ])

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
            all_raw_dfs[task_label][modality] = raw_dfs

    df_prepared_all = pd.concat(all_wide, axis=0, ignore_index=True)
    df_long_all = pd.concat(all_long, axis=0, ignore_index=True)

    if all_sequence:
        df_sequence_all = pd.concat(all_sequence, axis=0, ignore_index=True)
    else:
        df_sequence_all = pd.DataFrame(
            columns=[
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
        )

    output_path_wide = os.path.join(output_dir, OUTPUT_FILE_WIDE)
    output_path_long = os.path.join(output_dir, OUTPUT_FILE_LONG)
    output_path_sequence = os.path.join(output_dir, OUTPUT_FILE_SEQUENCE)

    df_prepared_all.to_csv(
        output_path_wide,
        sep="\t",
        index=False,
        na_rep="nan",
    )
    df_long_all.to_csv(
        output_path_long,
        sep="\t",
        index=False,
        na_rep="nan",
    )
    df_sequence_all.to_csv(
        output_path_sequence,
        sep="\t",
        index=False,
        na_rep="nan",
    )

    for task_spec in TASK_SPECS:
        task_name = task_spec["task_label"]

        for modality in MODALITIES:
            for measurement_id in sorted(all_raw_dfs[task_name][modality]):
                run_info = all_raw_dfs[task_name][modality][measurement_id]

                if not run_info["found"]:
                    print(
                        f"\nInput file not found for {task_name} "
                        f"{modality} measurement {measurement_id:02d}: "
                        f"{run_info['file']}"
                    )
                    print(
                        f"Created onsets_{measurement_id}, "
                        f"durations_{measurement_id}, and "
                        f"error_{measurement_id} with nan values."
                    )
                    continue

                if run_info["drop_first_event"]:
                    print(
                        f"\nDiscarded the first {run_info['event_type']} "
                        f"for {run_info['file']}."
                    )

                print(
                    f"\nOriginal repaired dataframe "
                    f"({run_info['file']}):\n"
                )
                print(run_info["raw"].to_string(index=False))

                print(
                    f"\nParsed onset dataframe ({run_info['file']}):\n"
                )
                print(run_info["slots"].to_string(index=False))

                print(
                    f"\nSequence dataframe ({run_info['file']}):\n"
                )
                print(run_info["sequence"].to_string(index=False))

    print("\nPrepared wide dataframe:\n")
    print(df_prepared_all.to_string(index=False))

    print("\nPrepared long dataframe:\n")
    print(df_long_all.to_string(index=False))

    print("\nSequence long dataframe:\n")
    print(df_sequence_all.to_string(index=False))

    print(f"\nSaved wide TSV output to:\n  {output_path_wide}")
    print(f"\nSaved long TSV output to:\n  {output_path_long}")
    print(f"\nSaved sequence TSV output to:\n  {output_path_sequence}")