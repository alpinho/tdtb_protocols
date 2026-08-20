#!/usr/bin/env python3
"""
Build a long-format table of theoretical durations from a TSV file.

Edit the INPUTS section below to set:
    - task        (logical name: 'production', 'perception', 'ntfd')
    - subject
    - session
    - modality
    - tsv_file (auto-built from these)
    - output_file (optional; default: script folder + tagged name)

Note: for task='ntfd', the label used in paths / filenames is 'notemporal'.

author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Creation: 9th of December 2025
Last Update: March 2026

Compatibility: Python 3.10.16
"""

import os
import pandas as pd
from pathlib import Path


# ======= CONFIG FOR EACH TASK =============

TASK_DURATION_SPECS = {
    "production": {
        "isi_cols": ["isi_1", "isi_2", "isi_3", "isi_4"],
        "duration_types": ["standard", "soa1", "standard", "soa2"],
    },
    "perception": {
        "isi_cols": ["isi_1", "isi_2", "isi_3", "isi_4", "isi_5"],
        # Final ISI is the comparison interval
        "duration_types": ["standard", "soa1", "standard", "soa2", "comparison"],
    },
    "ntfd": {
        "isi_cols": ["isi_1", "isi_2", "isi_3", "isi_4", "isi_5"],
        "duration_types": ["standard", "soa1", "standard", "soa2", "standard"],
    },
}

# Mapping from logical task name to label used in paths / filenames
TASK_PATH_LABEL = {
    "production": "production",
    "perception": "perception",
    "ntfd": "notemporal",
}


# ======= FUNCTIONS =============

def extract_condition(trial_id: str) -> str:
    """
    Extract condition from trial_id.

    Rule:
      - If last two characters are digits, drop them.
      - Otherwise keep entire string.

    Examples
    --------
    'interval05' -> 'interval'
    'beat03'     -> 'beat'
    'baseline'   -> 'baseline'
    """
    trial_id = str(trial_id)
    if len(trial_id) >= 2 and trial_id[-2:].isdigit():
        return trial_id[:-2]
    return trial_id


def build_long_table(df, task, subject, modality):
    """
    Create long-format table with theoretical durations.

    Output columns:
        task, subject, modality, condition, trial,
        theoretical_durations, duration_type
    """

    if task not in TASK_DURATION_SPECS:
        raise ValueError(
            f"Unknown task '{task}'. "
            f"Known tasks: {list(TASK_DURATION_SPECS.keys())}"
        )

    isi_cols = TASK_DURATION_SPECS[task]["isi_cols"]
    duration_types = TASK_DURATION_SPECS[task]["duration_types"]

    if len(isi_cols) != len(duration_types):
        raise ValueError(
            f"Mismatch in config for task '{task}': "
            f"{len(isi_cols)} isi_cols vs {len(duration_types)} duration_types."
        )

    rows = []

    for _, row in df.iterrows():
        trial_number = str(row.get("trial_number", "")).strip()
        # Skip baseline or rows with missing trial_number
        if trial_number in ("", "-", "nan"):
            continue

        trial = int(trial_number)
        condition = extract_condition(row.get("trial_id", ""))

        for col_name, dur_type in zip(isi_cols, duration_types):
            value = row.get(col_name, "")

            if isinstance(value, str):
                value = value.strip()
                if value in ("", "-"):
                    continue

            try:
                duration = float(value)
            except Exception:
                continue

            rows.append(
                {
                    "task": task,
                    "subject": subject,
                    "modality": modality,
                    "condition": condition,
                    "trial": trial,
                    "theoretical_durations": duration,
                    "duration_type": dur_type,
                }
            )

    return pd.DataFrame(rows)


def main():
    input_path = Path(tsv_file)

    # Folder where this script lives
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # If output not specified: default to script folder + tagged name
    if output_file is None:
        output_name = (
            "theoretical_durations_sub-%02d_%s_%s_%s.tsv"
            % (subject, session_label, task, modality)
        )
        output_path = os.path.join(script_dir, output_name)
    else:
        output_path = output_file

    # Load TSV
    df = pd.read_csv(input_path, sep="\t")

    # Process
    out_df = build_long_table(df, task, subject, modality)

    # Always write TSV
    out_df.to_csv(output_path, sep="\t", index=False)

    print(f"\nSaved TSV output to:\n  {output_path}\n")


# ======= INPUTS ================

# <-- EDIT THESE -->
subject = 3               # e.g. 3
session_type = 'imaging'  # 'behavioral' or 'imaging'
session = 1               # e.g. 1 (int)
run_number = 1            # e.g. 1 (int)
task = "ntfd"             # 'production', 'perception', or 'ntfd'
modality = "audio"        # e.g. 'audio', 'visual'

sestype_tag = {'behavioral': 'behav', 'imaging': 'img'}

# ------------------

# Build BIDS-like session and run labels, e.g. 'ses-01_run-01'
session_label = "ses-%02d" % session
run_label = "run-%02d" % run_number

# Get label used in filenames/dirs (e.g. 'notemporal' for task='ntfd')
task_path_label = TASK_PATH_LABEL.get(task, task)

# Path to input TSV, relative to project root (parent of parent of script)
tsv_file = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "expy_protocols",
    session_type + "-sessions_inputs",
    "sub-%02d" % subject,
    session_label,
    "inputs_%s_sub-%02d_%s" % (task_path_label, subject, session_label),
    modality,
    "%s_%s_run-%02d.tsv" % (modality, task_path_label, run_number),
)

# Output file name (TSV).
# If None → automatic name in script folder, e.g.:
#   theoretical_durations_sub-03_ses-01_run-01_ntfd_audio.tsv
output_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'theoretical_durations')
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(
    output_dir,
    'theoretical_durations_sub-%02d_%s_%s_%s_%s_%s.tsv' %
    (subject, session_label, run_label, task, modality, 
     sestype_tag[session_type])
)

# ========= RUN =================

if __name__ == "__main__":
    main()
