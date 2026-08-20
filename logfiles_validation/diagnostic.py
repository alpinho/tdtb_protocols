#!/usr/bin/env python3
"""
Diagnostic script of log files.

Note: For dataset expy, it only applies to behavioral sessions.

Author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Date of creation: 22nd of April 2026
Last Update: April 2026

Compatibility: Python 3.10.16
"""

import csv
import os
import re

# ######################## FUNCTIONS ##################################


SUBJECTS = [
    3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    21, 22, 23, 24, 25, 26, 27, 28, 29, 32, 34, 35, 38, 39, 40,
    41, 42, 43, 44, 45, 46, 47,
]

EXCLUDED_EXPY_FILES = {
    "music-sdtb_09_202206291718.xpd",
}


def safe_float(value):
    """Convert value to float, returning None if not possible."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_rows(file_path, encoding):
    """Return non-empty csv rows."""
    rows = []

    with open(file_path, "r", encoding=encoding, newline="") as fobj:
        reader = csv.reader(fobj)

        for row_idx, row in enumerate(reader, start=1):
            if not row:
                continue

            rows.append((row_idx, row))

    return rows


def is_data_row(row, header_first_col):
    """Return True for non-header, non-comment data rows."""
    if not row:
        return False

    if row[0].startswith("#"):
        return False

    if row[0] == header_first_col:
        return False

    return True


def required_indices_present(row, indices):
    """Return True if all required indices exist in row."""
    valid = [idx for idx in indices if idx is not None]

    if not valid:
        return True

    return len(row) > max(valid)


def get_path_subject_session(file_path):
    """Return subject and session numbers parsed from path."""
    match = re.search(r"sub-(\d+).*?ses-(\d+)", file_path)

    if match is None:
        return None, None

    return int(match.group(1)), int(match.group(2))


def use_expy_legacy_layout(subj, ses):
    """Return True for expy files with legacy layout."""
    if subj == 7:
        return True

    if subj == 8 and ses in {1, 2}:
        return True

    if subj == 9 and ses == 1:
        return True

    return False


def get_active_config(file_path, config):
    """Return file-specific config, handling expy legacy layouts."""
    active = config.copy()

    if config.get("dataset_name") != "expy":
        return active

    subj, ses = get_path_subject_session(file_path)
    active["path_subject"] = subj
    active["path_session"] = ses

    if use_expy_legacy_layout(subj, ses):
        active["session_idx"] = None
        active["run_idx"] = 1
        active["run_offset"] = 1
        active["session_id_idx"] = 0
        active["block_idx"] = None
        active["trial_number_idx"] = 2
        active["trial_label_idx"] = 3
        active["event_idx"] = 4
        active["duration_idx"] = 6
        active["theoretical_idx"] = 7
        active["realized_idx"] = 8
        active["rt_idx"] = 9
    else:
        active["session_idx"] = 1
        active["run_idx"] = 2
        active["run_offset"] = 0

    return active


def get_field(row, idx):
    """Return row value at idx or empty string."""
    if idx is None:
        return ""

    if len(row) <= idx:
        return ""

    return row[idx]


def get_session_value(row, config):
    """Return session value for current row."""
    if config.get("session_idx") is None:
        if config.get("path_session") is None:
            return ""
        return str(config["path_session"])

    return get_field(row, config["session_idx"])


def get_block_value(row, config):
    """Return block value for current row."""
    if config.get("block_idx") is None:
        return get_session_value(row, config)

    return get_field(row, config["block_idx"])


def is_isi_event(row, event_idx, isi_mode):
    """Return True if row corresponds to an ISI event."""
    if len(row) <= event_idx:
        return False

    event = row[event_idx].lower()

    if isi_mode == "startswith_isi":
        return event.startswith("isi_")

    if isi_mode == "startswith_interval":
        return event.startswith("interval_")

    return False


def is_feedback_event(row, event_idx):
    """Return True if the event column is feedback."""
    return len(row) > event_idx and row[event_idx].lower() == "feedback"


def is_beep_or_rect_event(row, event_idx):
    """Return True if the event column contains beep or rect."""
    if len(row) <= event_idx:
        return False

    event = row[event_idx].lower()
    return "beep" in event or "rect" in event


def get_prev_stimduration(
    rows,
    start_idx,
    duration_idx,
    header_first_col,
):
    """Return duration from previous valid row as float."""
    for idx in range(start_idx - 1, -1, -1):
        prev_row = rows[idx][1]

        if not is_data_row(prev_row, header_first_col):
            continue

        if len(prev_row) <= duration_idx:
            continue

        stimduration = safe_float(prev_row[duration_idx])

        if stimduration is None:
            continue

        return stimduration

    return None


def get_isi_records(file_path, config):
    """Extract ISI-event records and their differences."""
    records = []
    active = get_active_config(file_path, config)
    rows = get_rows(file_path, active["encoding"])

    for row_idx, row in rows:
        if not is_data_row(row, active["header_first_col"]):
            continue

        if not is_isi_event(
            row,
            active["event_idx"],
            active["isi_mode"],
        ):
            continue

        if not required_indices_present(
            row,
            [
                active["theoretical_idx"],
                active["realized_idx"],
                active["event_idx"],
                active["trial_label_idx"],
                active["trial_number_idx"],
                active["block_idx"],
                active["session_id_idx"],
            ],
        ):
            continue

        theoretical = safe_float(row[active["theoretical_idx"]])
        realized = safe_float(row[active["realized_idx"]])

        if theoretical is None or realized is None:
            continue

        diff = realized - theoretical

        record = {
            "file": os.path.basename(file_path),
            "line": row_idx,
            "session_id": get_field(row, active["session_id_idx"]),
            "block": get_block_value(row, active),
            "trial_number": get_field(row, active["trial_number_idx"]),
            "trial_label": get_field(row, active["trial_label_idx"]),
            "event": get_field(row, active["event_idx"]),
            "theoretical": theoretical,
            "realized": realized,
            "diff": diff,
            "abs_diff": abs(diff),
        }
        records.append(record)

    return records


def get_feedback_rt_stimduration_records(file_path, config):
    """Extract feedback records for RT + stimduration = duration."""
    records = []
    active = get_active_config(file_path, config)
    rows = get_rows(file_path, active["encoding"])

    for idx, (row_idx, row) in enumerate(rows):
        if not is_data_row(row, active["header_first_col"]):
            continue

        if not is_feedback_event(row, active["event_idx"]):
            continue

        if not required_indices_present(
            row,
            [
                active["duration_idx"],
                active["rt_idx"],
                active["event_idx"],
                active["trial_label_idx"],
                active["trial_number_idx"],
                active["block_idx"],
                active["session_id_idx"],
            ],
        ):
            continue

        duration = safe_float(row[active["duration_idx"]])
        rt = safe_float(row[active["rt_idx"]])

        if rt is None:
            continue

        stimduration = get_prev_stimduration(
            rows,
            idx,
            active["duration_idx"],
            active["header_first_col"],
        )

        if duration is None or stimduration is None:
            continue

        expected = rt + stimduration
        diff = duration - expected

        record = {
            "file": os.path.basename(file_path),
            "line": row_idx,
            "session_id": get_field(row, active["session_id_idx"]),
            "block": get_block_value(row, active),
            "trial_number": get_field(row, active["trial_number_idx"]),
            "trial_label": get_field(row, active["trial_label_idx"]),
            "event": get_field(row, active["event_idx"]),
            "duration": duration,
            "rt": rt,
            "stimduration": stimduration,
            "expected": expected,
            "diff": diff,
            "abs_diff": abs(diff),
        }
        records.append(record)

    return records


def get_feedback_rt_minus_duration_records(file_path, config):
    """Extract feedback records for RT - Duration."""
    records = []
    active = get_active_config(file_path, config)
    rows = get_rows(file_path, active["encoding"])

    for row_idx, row in rows:
        if not is_data_row(row, active["header_first_col"]):
            continue

        if not is_feedback_event(row, active["event_idx"]):
            continue

        if not required_indices_present(
            row,
            [
                active["duration_idx"],
                active["rt_idx"],
                active["event_idx"],
                active["trial_label_idx"],
                active["trial_number_idx"],
                active["block_idx"],
                active["session_id_idx"],
            ],
        ):
            continue

        duration = safe_float(row[active["duration_idx"]])
        rt = safe_float(row[active["rt_idx"]])

        if duration is None or rt is None:
            continue

        diff = rt - duration

        record = {
            "file": os.path.basename(file_path),
            "line": row_idx,
            "session_id": get_field(row, active["session_id_idx"]),
            "block": get_block_value(row, active),
            "trial_number": get_field(row, active["trial_number_idx"]),
            "trial_label": get_field(row, active["trial_label_idx"]),
            "event": get_field(row, active["event_idx"]),
            "duration": duration,
            "rt": rt,
            "diff": diff,
            "abs_diff": abs(diff),
        }
        records.append(record)

    return records


def get_feedback_duration_stimduration_records(file_path, config):
    """Extract feedback records for Duration + stimduration = Real ISI."""
    records = []
    active = get_active_config(file_path, config)
    rows = get_rows(file_path, active["encoding"])

    for idx, (row_idx, row) in enumerate(rows):
        if not is_data_row(row, active["header_first_col"]):
            continue

        if not is_feedback_event(row, active["event_idx"]):
            continue

        if not required_indices_present(
            row,
            [
                active["duration_idx"],
                active["realized_idx"],
                active["rt_idx"],
                active["event_idx"],
                active["trial_label_idx"],
                active["trial_number_idx"],
                active["block_idx"],
                active["session_id_idx"],
            ],
        ):
            continue

        duration = safe_float(row[active["duration_idx"]])
        real_isi = safe_float(row[active["realized_idx"]])
        rt = safe_float(row[active["rt_idx"]])

        if rt is None:
            continue

        stimduration = get_prev_stimduration(
            rows,
            idx,
            active["duration_idx"],
            active["header_first_col"],
        )

        if duration is None or real_isi is None or stimduration is None:
            continue

        expected = duration + stimduration
        diff = real_isi - expected

        record = {
            "file": os.path.basename(file_path),
            "line": row_idx,
            "session_id": get_field(row, active["session_id_idx"]),
            "block": get_block_value(row, active),
            "trial_number": get_field(row, active["trial_number_idx"]),
            "trial_label": get_field(row, active["trial_label_idx"]),
            "event": get_field(row, active["event_idx"]),
            "duration": duration,
            "real_isi": real_isi,
            "rt": rt,
            "stimduration": stimduration,
            "expected": expected,
            "diff": diff,
            "abs_diff": abs(diff),
        }
        records.append(record)

    return records


def get_beep_rect_stimduration_records(file_path, config):
    """Extract beep/rect records for stimduration vs 80."""
    records = []
    active = get_active_config(file_path, config)
    rows = get_rows(file_path, active["encoding"])

    for row_idx, row in rows:
        if not is_data_row(row, active["header_first_col"]):
            continue

        if not is_beep_or_rect_event(row, active["event_idx"]):
            continue

        if not required_indices_present(
            row,
            [
                active["duration_idx"],
                active["event_idx"],
                active["trial_label_idx"],
                active["trial_number_idx"],
                active["block_idx"],
                active["session_id_idx"],
            ],
        ):
            continue

        stimduration = safe_float(row[active["duration_idx"]])

        if stimduration is None:
            continue

        expected = 80.0
        diff = stimduration - expected

        record = {
            "file": os.path.basename(file_path),
            "line": row_idx,
            "session_id": get_field(row, active["session_id_idx"]),
            "block": get_block_value(row, active),
            "trial_number": get_field(row, active["trial_number_idx"]),
            "trial_label": get_field(row, active["trial_label_idx"]),
            "event": get_field(row, active["event_idx"]),
            "stimduration": stimduration,
            "expected": expected,
            "diff": diff,
            "abs_diff": abs(diff),
        }
        records.append(record)

    return records


def get_expy_task_name(file_path, encoding):
    """Return task name from xpd header."""
    with open(file_path, "r", encoding=encoding) as fobj:
        for line in fobj:
            if line.startswith("#e Task:"):
                task = line.split(":", 1)[1].strip()
                task = task.replace(" - behavioral session", "")
                return task

    return None


def is_expy_training_file(file_path, config):
    """Return True if expy logfile is a training session."""
    task_name = get_expy_task_name(file_path, config["encoding"])

    if task_name is None:
        return False

    return "training session" in task_name.lower()


def is_expy_excluded_file(file_path):
    """Return True if expy logfile is explicitly excluded."""
    return os.path.basename(file_path) in EXCLUDED_EXPY_FILES


def get_expy_subject_session_run(file_path, config):
    """Return subject, session and run from first valid data row."""
    active = get_active_config(file_path, config)
    rows = get_rows(file_path, active["encoding"])

    for _, row in rows:
        if not is_data_row(row, active["header_first_col"]):
            continue

        if not required_indices_present(
            row,
            [
                active["session_id_idx"],
                active["run_idx"],
            ],
        ):
            continue

        subj = get_field(row, active["session_id_idx"])
        ses = get_session_value(row, active)
        run = get_field(row, active["run_idx"])

        subj_num = safe_float(subj)
        ses_num = safe_float(ses)
        run_num = safe_float(run)

        if subj_num is None or ses_num is None or run_num is None:
            continue

        run_num = int(run_num) + active.get("run_offset", 0)

        return int(subj_num), int(ses_num), run_num

    return None, None, None


def parse_task_name(task_name):
    """Return modality and protocol tags from task name."""
    if task_name is None:
        return None, None

    task_low = task_name.lower()

    if "visual" in task_low:
        modality = "visual"
    elif "auditory" in task_low or "audio" in task_low:
        modality = "audio"
    else:
        modality = None

    if "production" in task_low:
        protocol = "production"
    elif "perception" in task_low:
        protocol = "perception"
    elif "non-temporal" in task_low or "notemporal" in task_low:
        protocol = "notemporal"
    else:
        protocol = None

    return modality, protocol


def infer_psychopy_task_name(file_path, config):
    """Infer april2026 task from log filename and/or content."""
    base = os.path.basename(file_path).lower()

    if "prod" in base or "production" in base:
        protocol = "production"
    elif "percep" in base or "perception" in base:
        protocol = "perception"
    elif "notemp" in base or "ntfd" in base:
        protocol = "notemporal"
    else:
        protocol = None

    rows = get_rows(file_path, config["encoding"])
    modality = None

    for _, row in rows:
        if not is_data_row(row, config["header_first_col"]):
            continue

        if len(row) <= config["event_idx"]:
            continue

        event = row[config["event_idx"]].lower()

        if "beep" in event:
            modality = "audio"
            break

        if "rect" in event:
            modality = "visual"
            break

    if modality is None or protocol is None:
        return None

    if modality == "audio":
        mod_name = "Auditory"
    else:
        mod_name = "Visual"

    if protocol == "production":
        prot_name = "Production"
    elif protocol == "perception":
        prot_name = "Perception"
    else:
        prot_name = "Non-Temporal"

    return f"{mod_name} {prot_name}"


def get_psychopy_fixed_subject_session_run():
    """Return fixed subject, session and run for april2026 inputs."""
    return 5, 1, 1


def get_input_tsv_path(file_path, config):
    """Return matching behavioral-session input TSV path."""
    dataset_name = config["dataset_name"]

    if dataset_name == "expy":
        task_name = get_expy_task_name(file_path, config["encoding"])
        subj, ses, run = get_expy_subject_session_run(file_path, config)
    elif dataset_name == "april2026":
        task_name = infer_psychopy_task_name(file_path, config)
        subj, ses, run = get_psychopy_fixed_subject_session_run()
    else:
        return None

    modality, protocol = parse_task_name(task_name)

    if subj is None or ses is None or run is None:
        return None

    if modality is None or protocol is None:
        return None

    ses_dir = os.path.join(
        config["input_tsv_root"],
        f"sub-{subj:02d}",
        f"ses-{ses:02d}",
    )

    input_dir = os.path.join(
        ses_dir,
        f"inputs_{protocol}_sub-{subj:02d}_ses-{ses:02d}",
        modality,
    )

    fname = f"{modality}_{protocol}_run-{run:02d}.tsv"
    tsv_path = os.path.join(input_dir, fname)

    if not os.path.isfile(tsv_path):
        return None

    return tsv_path


def load_input_trial_map(tsv_path):
    """Return trial_number -> trial_id from input TSV."""
    trial_map = {}

    with open(tsv_path, "r", encoding="utf-8", newline="") as fobj:
        reader = csv.DictReader(fobj, delimiter="\t")

        for row in reader:
            trial_number = row["trial_number"].strip()
            trial_id = row["trial_id"].strip()

            if trial_id == "baseline":
                continue

            if trial_number == "-" or not trial_number:
                continue

            trial_map[trial_number] = trial_id

    return trial_map


def load_log_trial_map(file_path, config):
    """Return log trial info grouped by trial_number."""
    active = get_active_config(file_path, config)
    rows = get_rows(file_path, active["encoding"])
    trial_map = {}

    for row_idx, row in rows:
        if not is_data_row(row, active["header_first_col"]):
            continue

        if not required_indices_present(
            row,
            [
                active["trial_number_idx"],
                active["trial_label_idx"],
            ],
        ):
            continue

        trial_number = get_field(row, active["trial_number_idx"]).strip()
        trial_id = get_field(row, active["trial_label_idx"]).strip()

        if trial_number == "-" or not trial_number:
            continue

        if trial_number not in trial_map:
            trial_map[trial_number] = {
                "trial_ids": set(),
                "first_line": row_idx,
            }

        trial_map[trial_number]["trial_ids"].add(trial_id)

    return trial_map


def get_input_log_trialid_records(file_path, config):
    """Compare input TSV trial_id with logfile trial_id."""
    records = []

    input_tsv = get_input_tsv_path(file_path, config)

    if input_tsv is None:
        return records

    expected_map = load_input_trial_map(input_tsv)
    observed_map = load_log_trial_map(file_path, config)

    if config["dataset_name"] == "expy":
        task_name = get_expy_task_name(file_path, config["encoding"])
        subj, ses, run = get_expy_subject_session_run(file_path, config)
    elif config["dataset_name"] == "april2026":
        task_name = infer_psychopy_task_name(file_path, config)
        subj, ses, run = get_psychopy_fixed_subject_session_run()
    else:
        return records

    for trial_number in sorted(expected_map, key=lambda x: int(x)):
        expected_trial_id = expected_map[trial_number]

        if trial_number not in observed_map:
            observed_trial_id = "MISSING"
            line = ""
            diff = 1
        else:
            observed_ids = sorted(observed_map[trial_number]["trial_ids"])
            observed_trial_id = "|".join(observed_ids)
            line = observed_map[trial_number]["first_line"]

            if len(observed_ids) == 1 and observed_ids[0] == expected_trial_id:
                diff = 0
            else:
                diff = 1

        record = {
            "file": os.path.basename(file_path),
            "input_file": os.path.basename(input_tsv),
            "line": line,
            "task": task_name,
            "subject_id": subj,
            "session_number": ses,
            "run_number": run,
            "trial_number": trial_number,
            "expected_trial_id": expected_trial_id,
            "observed_trial_id": observed_trial_id,
            "diff": diff,
            "abs_diff": abs(diff),
        }
        records.append(record)

    return records


def count_bins(abs_diffs):
    """Count absolute differences across predefined intervals."""
    bins = {
        "exactly 0 ms": 0,
        "0 < |diff| <= 1 ms": 0,
        "1 < |diff| <= 5 ms": 0,
        "5 < |diff| <= 10 ms": 0,
        "|diff| > 10 ms": 0,
    }

    for diff in abs_diffs:
        if diff == 0:
            bins["exactly 0 ms"] += 1
        elif diff <= 1:
            bins["0 < |diff| <= 1 ms"] += 1
        elif diff <= 5:
            bins["1 < |diff| <= 5 ms"] += 1
        elif diff <= 10:
            bins["5 < |diff| <= 10 ms"] += 1
        else:
            bins["|diff| > 10 ms"] += 1

    return bins


def write_line(text, fobj=None):
    """Print line and optionally write it to file."""
    print(text)
    if fobj is not None:
        fobj.write(text + "\n")


def summarize_block(title, records, viol_text, fobj=None):
    """Generic numeric summary block."""
    total = len(records)

    write_line("=" * 60, fobj)
    write_line(title, fobj)
    write_line("=" * 60, fobj)

    if total == 0:
        write_line("No valid events were found.", fobj)
        write_line("", fobj)
        return

    abs_diffs = [rec["abs_diff"] for rec in records]
    bins = count_bins(abs_diffs)

    n_viol = sum(1 for diff in abs_diffs if diff != 0)
    pct_viol = 100 * n_viol / total

    write_line(f"Total valid events: {total}", fobj)
    write_line(
        f"Violations ({viol_text}): {n_viol} "
        f"({pct_viol:.2f}%)",
        fobj
    )
    write_line("", fobj)

    for label, count in bins.items():
        pct = 100 * count / total
        write_line(f"{label}: {count} events ({pct:.2f}%)", fobj)

    write_line("", fobj)


def summarize_match_block(title, records, viol_text, fobj=None):
    """Summary block for exact string matches."""
    total = len(records)

    write_line("=" * 60, fobj)
    write_line(title, fobj)
    write_line("=" * 60, fobj)

    if total == 0:
        write_line("No valid events were found.", fobj)
        write_line("", fobj)
        return

    n_viol = sum(1 for rec in records if rec["diff"] != 0)
    pct_viol = 100 * n_viol / total
    n_ok = total - n_viol
    pct_ok = 100 * n_ok / total

    write_line(f"Total valid events: {total}", fobj)
    write_line(
        f"Violations ({viol_text}): {n_viol} "
        f"({pct_viol:.2f}%)",
        fobj
    )
    write_line(
        f"Exact matches: {n_ok} ({pct_ok:.2f}%)",
        fobj
    )
    write_line("", fobj)


def get_flagged(records, threshold=5.0):
    """Return records above threshold."""
    flagged = [rec for rec in records if rec["abs_diff"] > threshold]
    flagged.sort(key=lambda rec: (rec["file"], rec["line"]))
    return flagged


def get_mismatches(records):
    """Return records with non-zero diff."""
    flagged = [rec for rec in records if rec["diff"] != 0]
    flagged.sort(
        key=lambda rec: (
            rec["file"],
            rec["subject_id"],
            rec["session_number"],
            rec["run_number"],
            int(rec["trial_number"]),
        )
    )
    return flagged


def save_flagged_tsv(records, out_path, threshold=5.0):
    """Save flagged records to TSV."""
    flagged = get_flagged(records, threshold=threshold)

    if not flagged:
        return

    keys = list(flagged[0].keys())

    with open(out_path, "w", encoding="utf-8", newline="") as fobj:
        writer = csv.writer(fobj, delimiter="\t")
        writer.writerow(keys)

        for rec in flagged:
            writer.writerow([rec[key] for key in keys])


def save_mismatch_tsv(records, out_path):
    """Save mismatch records to TSV."""
    flagged = get_mismatches(records)

    if not flagged:
        return

    keys = list(flagged[0].keys())

    with open(out_path, "w", encoding="utf-8", newline="") as fobj:
        writer = csv.writer(fobj, delimiter="\t")
        writer.writerow(keys)

        for rec in flagged:
            writer.writerow([rec[key] for key in keys])


def get_csv_files(input_dir):
    """Return sorted csv files in input directory."""
    files = []

    for name in os.listdir(input_dir):
        if name.lower().endswith(".csv"):
            files.append(os.path.join(input_dir, name))

    return sorted(files)


def get_expy_files(input_dir):
    """Return xpd files under allowed subjects and ses-0* folders."""
    files = []

    for subj in SUBJECTS:
        subj_dir = os.path.join(input_dir, f"sub-{subj:02d}")

        if not os.path.isdir(subj_dir):
            continue

        session_names = sorted(os.listdir(subj_dir))

        for ses_name in session_names:
            if not re.fullmatch(r"ses-0\d+", ses_name):
                continue

            ses_dir = os.path.join(subj_dir, ses_name)

            if not os.path.isdir(ses_dir):
                continue

            for name in sorted(os.listdir(ses_dir)):
                if name.lower().endswith(".xpd"):
                    file_path = os.path.join(ses_dir, name)

                    if is_expy_excluded_file(file_path):
                        continue

                    if is_expy_training_file(
                        file_path,
                        dataset_map["expy"],
                    ):
                        continue

                    files.append(file_path)

    return files


def get_input_files(input_dir, dataset, config):
    """Return input files for the selected dataset."""
    if dataset == "expy":
        return get_expy_files(input_dir)

    if config["file_ext"] == ".csv":
        return get_csv_files(input_dir)

    return []


# ######################### INPUTS ####################################

home = os.path.expanduser("~")
gitrepo = os.path.join(home, "mygit", "music_sdtb",
                       "music-sdtb_protocols")

dataset_map = {
    "nov2025": {
        "dataset_name": "nov2025",
        "input_dir": os.path.join(
            gitrepo, "psychopy_protocols", "data",
            "pilot_stimtracker_nov2025"
        ),
        "output_dir": "results_nov2025",
        "file_ext": ".csv",
        "encoding": "utf-8",
        "header_first_col": "session_id",
        "session_id_idx": 0,
        "block_idx": 1,
        "trial_number_idx": 2,
        "trial_label_idx": 3,
        "event_idx": 4,
        "duration_idx": 6,
        "theoretical_idx": 7,
        "realized_idx": 8,
        "rt_idx": 9,
        "isi_mode": "startswith_isi",
    },
    "feb2026": {
        "dataset_name": "feb2026",
        "input_dir": os.path.join(
            gitrepo, "psychopy_protocols", "data",
            "pilot_stimtracker_feb2026"
        ),
        "output_dir": "results_feb2026",
        "file_ext": ".csv",
        "encoding": "utf-8",
        "header_first_col": "session_id",
        "session_id_idx": 0,
        "block_idx": 1,
        "trial_number_idx": 2,
        "trial_label_idx": 3,
        "event_idx": 4,
        "duration_idx": 6,
        "theoretical_idx": 7,
        "realized_idx": 8,
        "rt_idx": 9,
        "isi_mode": "startswith_isi",
    },
    "april2026": {
        "dataset_name": "april2026",
        "input_dir": os.path.join(
            gitrepo, "psychopy_protocols", "april2_testing",
            "data"
        ),
        "input_tsv_root": os.path.join(
            gitrepo, "psychopy_protocols", "april2_testing",
            "behavioral-sessions_inputs"
        ),
        "output_dir": "results_april2026",
        "file_ext": ".csv",
        "encoding": "utf-8",
        "header_first_col": "session_id",
        "session_id_idx": 0,
        "block_idx": 1,
        "trial_number_idx": 2,
        "trial_label_idx": 3,
        "event_idx": 4,
        "duration_idx": 6,
        "theoretical_idx": 7,
        "realized_idx": 8,
        "rt_idx": 9,
        "isi_mode": "startswith_isi",
    },
    "expy": {
        "dataset_name": "expy",
        "input_dir": os.path.join(
            gitrepo, "expy_protocols", "data", "behavses_data"
        ),
        "input_tsv_root": os.path.join(
            gitrepo, "expy_protocols", "behavioral-sessions_inputs"
        ),
        "output_dir": "results_expy",
        "file_ext": ".xpd",
        "encoding": "cp1252",
        "header_first_col": "subject_id",
        "session_id_idx": 0,
        "session_idx": 1,
        "run_idx": 2,
        "run_offset": 0,
        "block_idx": 1,
        "trial_number_idx": 3,
        "trial_label_idx": 4,
        "event_idx": 5,
        "duration_idx": 7,
        "theoretical_idx": 8,
        "realized_idx": 9,
        "rt_idx": 10,
        "isi_mode": "startswith_interval",
    },
}

dataset = "april2026"
config = dataset_map[dataset]
input_dir = config["input_dir"]

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(script_dir, config["output_dir"])

REPORT_FILE = os.path.join(OUTPUT_DIR, "isi_diagnostics_report.txt")
ISI_FLAGGED_FILE = os.path.join(
    OUTPUT_DIR, "isi_events_above_5ms.tsv"
)
RT_STIMDURATION_FLAGGED_FILE = os.path.join(
    OUTPUT_DIR,
    "rt_plus_stimduration_eq_duration_violations_above_5ms.tsv"
)
RT_MINUS_DURATION_FLAGGED_FILE = os.path.join(
    OUTPUT_DIR,
    "rt_minus_duration_violations_above_5ms.tsv"
)
DURATION_STIMDURATION_FLAGGED_FILE = os.path.join(
    OUTPUT_DIR,
    "duration_plus_stimduration_eq_real_isi_violations_above_5ms.tsv"
)
BEEP_RECT_STIMDURATION_FLAGGED_FILE = os.path.join(
    OUTPUT_DIR,
    "stimduration_eq_80_beep_rect_violations_above_5ms.tsv"
)
INPUT_LOG_TRIALID_FLAGGED_FILE = os.path.join(
    OUTPUT_DIR,
    "input_trialid_eq_log_trialid_violations.tsv"
)

# ########################## RUN ######################################
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Dataset: {dataset}")
    print(f"Input dir: {input_dir}")
    print(f"Output dir: {OUTPUT_DIR}")
    print("")

    all_files = get_input_files(input_dir, dataset, config)

    all_isi_records = []
    all_rt_duration_records = []
    all_duration_stimduration_records = []
    all_beep_rect_stimduration_records = []
    all_input_log_trialid_records = []

    for file_path in all_files:
        all_isi_records.extend(get_isi_records(file_path, config))

        if dataset == "expy":
            all_rt_duration_records.extend(
                get_feedback_rt_minus_duration_records(
                    file_path,
                    config
                )
            )
        else:
            all_rt_duration_records.extend(
                get_feedback_rt_stimduration_records(file_path, config)
            )

        all_duration_stimduration_records.extend(
            get_feedback_duration_stimduration_records(
                file_path,
                config
            )
        )
        all_beep_rect_stimduration_records.extend(
            get_beep_rect_stimduration_records(file_path, config)
        )

        if dataset in {"expy", "april2026"}:
            all_input_log_trialid_records.extend(
                get_input_log_trialid_records(file_path, config)
            )

    with open(REPORT_FILE, "w", encoding="utf-8") as report_fobj:
        summarize_block(
            "Theoretical and Real ISI diff",
            all_isi_records,
            "diff != 0",
            fobj=report_fobj
        )

        if dataset == "expy":
            summarize_block(
                "RT - Duration",
                all_rt_duration_records,
                "rt != duration",
                fobj=report_fobj
            )
        else:
            summarize_block(
                "RT + stimduration = duration",
                all_rt_duration_records,
                "duration != rt + stimduration",
                fobj=report_fobj
            )

        summarize_block(
            "Duration + stimduration = Real ISI",
            all_duration_stimduration_records,
            "real_isi != duration + stimduration",
            fobj=report_fobj
        )

        summarize_block(
            "Stimduration = 80 for beep/rect events",
            all_beep_rect_stimduration_records,
            "stimduration != 80",
            fobj=report_fobj
        )

        if dataset in {"expy", "april2026"}:
            summarize_match_block(
                "Input trial_id = log trial_id",
                all_input_log_trialid_records,
                "log trial_id != input trial_id",
                fobj=report_fobj
            )

    save_flagged_tsv(
        all_isi_records,
        ISI_FLAGGED_FILE,
        threshold=5.0
    )

    if dataset == "expy":
        save_flagged_tsv(
            all_rt_duration_records,
            RT_MINUS_DURATION_FLAGGED_FILE,
            threshold=5.0
        )
    else:
        save_flagged_tsv(
            all_rt_duration_records,
            RT_STIMDURATION_FLAGGED_FILE,
            threshold=5.0
        )

    save_flagged_tsv(
        all_duration_stimduration_records,
        DURATION_STIMDURATION_FLAGGED_FILE,
        threshold=5.0
    )

    save_flagged_tsv(
        all_beep_rect_stimduration_records,
        BEEP_RECT_STIMDURATION_FLAGGED_FILE,
        threshold=5.0
    )

    if dataset in {"expy", "april2026"}:
        save_mismatch_tsv(
            all_input_log_trialid_records,
            INPUT_LOG_TRIALID_FLAGGED_FILE
        )

    print(f"Number of files inspected: {len(all_files)}")
    print(f"Saved report: {REPORT_FILE}")

    if os.path.exists(ISI_FLAGGED_FILE):
        print(f"Saved flagged events: {ISI_FLAGGED_FILE}")

    if dataset == "expy":
        if os.path.exists(RT_MINUS_DURATION_FLAGGED_FILE):
            print("Saved flagged events: "
                  f"{RT_MINUS_DURATION_FLAGGED_FILE}")
    else:
        if os.path.exists(RT_STIMDURATION_FLAGGED_FILE):
            print("Saved flagged events: "
                  f"{RT_STIMDURATION_FLAGGED_FILE}")

    if os.path.exists(DURATION_STIMDURATION_FLAGGED_FILE):
        print("Saved flagged events: "
              f"{DURATION_STIMDURATION_FLAGGED_FILE}")

    if os.path.exists(BEEP_RECT_STIMDURATION_FLAGGED_FILE):
        print("Saved flagged events: "
              f"{BEEP_RECT_STIMDURATION_FLAGGED_FILE}")

    if os.path.exists(INPUT_LOG_TRIALID_FLAGGED_FILE):
        print("Saved flagged events: "
              f"{INPUT_LOG_TRIALID_FLAGGED_FILE}")