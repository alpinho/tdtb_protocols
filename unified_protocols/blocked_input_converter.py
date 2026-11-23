# Convert selected task inputs to a blocked design
# CLI: python blocked_input_converter.py <subject_number>

import sys
import csv
import io
import os
import tempfile
from pathlib import Path

# ============================== PATHS =================================

ROOT = Path(__file__).resolve().parent
# Locate the same config reader used by the input generator
sys.path.append(str(ROOT / 'expy_protocols'))

from confparser import load_config

INPUTS_FOLDER = ROOT / 'inputs' / 'behavioral-sessions_inputs'
OUTPUTS_FOLDER = INPUTS_FOLDER
CONFIG_FILE = ROOT / 'expy_protocols' / 'behavsess_config.ini'


# ============================ SETTINGS ================================

TASKS_TO_CONVERT = {
    "audio_production": True,
    "audio_perception": False,
    "audio_notemporal": False,
    "visual_production": False,
    "visual_perception": False,
    "visual_notemporal": False,
}

# Durations are read in milliseconds from CONFIG_FILE


# ============================= FUNCTIONS ==============================

# Read the timing values required by the original onset formula
def load_settings():
    config = load_config(str(CONFIG_FILE))
    keys = ('WAIT', 'stim_duration', 'feedback_duration',
            'within_block_duration', 'baseline_duration', 'between_tasks_duration')
    settings = {key: config[key] for key in keys}
    if any(type(value) is not int or value < 0 for value in settings.values()):
        raise ValueError('Timing settings must be nonnegative integer milliseconds.')
    return settings


# Identify the row as beat, interval, or baseline from its trial ID
def condition(row):
    label = row['trial_id']
    if label == 'baseline':
        return label
    for prefix in ('beat', 'interval'):
        if label.startswith(prefix) and label[len(prefix):].isdigit():
            return prefix
    raise ValueError('Unsupported trial ID: %s; random NTFD trials need a separate design.' % label)


# Calculate each row's scheduled onset and the scheduled end of the run
def calculate_onsets(rows, task, settings):
    # Original randomization.py:create_onsets formula; feature columns are excluded
    onset = settings['WAIT' if task.startswith('audio_') else 'between_tasks_duration']
    result = []
    for row in rows:
        # Record this row's start before advancing to the next row
        result.append(str(onset))
        if condition(row) == 'baseline':
            # Baseline duration comes from config; its TSV fields remain '-'
            onset += settings['baseline_duration']
        else:
            # Add the trial ISIs and fixed periods. Do not add the cue separately
            onset += sum(int(value) for key, value in row.items() if key.startswith('isi_'))
            onset += sum(settings[key] for key in
                         ('stim_duration', 'feedback_duration', 'within_block_duration'))
    return result, onset


# Collect complete rows and place all baselines between the two conditions
def group_rows(rows):
    bins = {'beat': [], 'interval': [], 'baseline': []}
    first = None
    for row in rows:
        kind = condition(row)
        # Copy rows so later renumbering cannot change the original data
        bins[kind].append(dict(row))
        if first is None and kind != 'baseline':
            first = kind
    if any(not group for group in bins.values()):
        raise ValueError('Run must contain beat, interval, and baseline rows.')
    other = 'interval' if first == 'beat' else 'beat'
    # Preserve the original first condition and the order within each list
    return bins[first] + bins['baseline'] + bins[other]


# Validate one run and prepare its blocked TSV in memory. Do not write files here
def prepare_file(path, task, settings):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        header, rows = reader.fieldnames, list(reader)
    # Check the column layout before reading trial timing values
    count = 4 if task.endswith('_production') else 5
    expected = ['onsets', 'trial_number', 'trial_id'] + ['isi_%d' % i for i in range(1, count + 1)]
    if not header or header[:len(expected)] != expected or len(set(header)) != len(header):
        raise ValueError('Unexpected columns: %s' % path)
    extra = 1 if task.endswith('_notemporal') else 0
    if len(header) != len(expected) + extra:
        raise ValueError('Unexpected extra columns: %s' % path)
    # Check complete rows, baseline placeholders, and positive stimulus intervals
    number = 0
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError('Incomplete row: %s' % path)
        if condition(row) == 'baseline':
            if any(row[key] != '-' for key in header if key not in ('onsets', 'trial_id')):
                raise ValueError('Invalid baseline placeholders: %s' % path)
        else:
            number += 1
            if int(row['trial_number']) != number:
                raise ValueError('Unexpected original trial numbering: %s' % path)
            if any(int(row[key]) <= 0 for key in expected[3:]):
                raise ValueError('ISIs must be positive integers: %s' % path)
    # Confirm that this config reproduces the original input schedule exactly
    original_onsets, original_end = calculate_onsets(rows, task, settings)
    for index, (row, onset) in enumerate(zip(rows, original_onsets), 1):
        if row['onsets'] != onset:
            raise ValueError('%s row %d: onset %s != expected %s; check generation config'
                             % (path, index, row['onsets'], onset))
    # Build the blocked order. Stop if the input is already in that order
    blocked = group_rows(rows)
    if [condition(r) for r in rows] == [condition(r) for r in blocked]:
        raise ValueError('Already blocked: %s' % path)
    number = 0
    # Update onset and presentation number only. Baselines keep trial number '-'
    onsets, end = calculate_onsets(blocked, task, settings)
    for row, onset in zip(blocked, onsets):
        row['onsets'] = onset
        if condition(row) != 'baseline':
            number += 1
            row['trial_number'] = str(number)
    # Verify unchanged trial content, duplicate counts, and total scheduled duration
    preserved = [key for key in header if key not in ('onsets', 'trial_number')]
    original_values = sorted(tuple(row[key] for key in preserved) for row in rows)
    blocked_values = sorted(tuple(row[key] for key in preserved) for row in blocked)
    if original_values != blocked_values or original_end != end:
        raise ValueError('Preservation check failed: %s' % path)
    # Retain the input column order when assembling the output TSV
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=header, delimiter='\t', lineterminator='\n')
    writer.writeheader()
    writer.writerows(blocked)
    return buffer.getvalue().encode('utf-8')


# Write a complete temporary file, then give it the required output filename
def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=str(path.parent), prefix='.blocked-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(name, str(path))
    finally:
        # Remove an unfinished temporary file if writing or replacement failed
        if os.path.exists(name):
            os.unlink(name)


# Prepare all enabled runs, then save each original and write its blocked version
def convert_subject(subject):
    # Select the task switches marked True
    valid = {m + '_' + t for m in ('audio', 'visual')
             for t in ('production', 'perception', 'notemporal')}
    if set(TASKS_TO_CONVERT) != valid or any(type(v) is not bool for v in TASKS_TO_CONVERT.values()):
        raise ValueError('TASKS_TO_CONVERT must contain six boolean settings.')
    enabled = [task for task, value in TASKS_TO_CONVERT.items() if value]
    if not enabled:
        raise ValueError('No tasks enabled.')
    # Resolve the subject folder and retain its session/task structure in outputs
    source_root, output_root = Path(INPUTS_FOLDER).resolve(), Path(OUTPUTS_FOLDER).resolve()
    subject_dir = source_root / ('sub-%02d' % subject)
    if not subject_dir.is_dir():
        raise ValueError('Subject folder not found: %s' % subject_dir)
    settings = load_settings()
    prepared = []
    for task in enabled:
        # Search all behavioral sessions. Exclude saved unblocked originals
        matches = sorted(subject_dir.glob('ses-*/inputs_*/%s/%s_run*.tsv' % (task.split('_')[0], task)))
        matches = [path for path in matches if not path.stem.endswith('_unblocked')]
        if not matches:
            raise ValueError('No behavioral runs found for %s' % task)
        for source in matches:
            # Stop before writing if an original or separate output already exists
            unblocked = source.with_name(source.stem + '_unblocked.tsv')
            if unblocked.exists():
                raise ValueError('Saved original already exists: %s' % unblocked)
            destination = output_root / source.relative_to(source_root)
            if destination != source and destination.exists():
                raise ValueError('Output already exists: %s' % destination)
            prepared.append((source, destination, source.read_bytes(), prepare_file(source, task, settings)))
    # All runs pass validation before any input is replaced
    for source, destination, original, converted in prepared:
        if source.read_bytes() != original:
            raise ValueError('Source changed during conversion: %s' % source)
        unblocked = source.with_name(source.stem + '_unblocked.tsv')
        if unblocked.exists():
            raise ValueError('Saved original already exists: %s' % unblocked)
        # Preserve the original beside the new file using the '_unblocked' suffix
        source.rename(unblocked)
        try:
            atomic_write(destination, converted)
        except OSError:
            # Restore this run's original filename if the blocked write fails
            unblocked.rename(source)
            raise
        print('Converted: %s' % destination)
    print('Baseline per row: %d ms; PsychoPy baselinetime must match in seconds.' % settings['baseline_duration'])

# ============================ CONVERSION ==============================

if __name__ == '__main__':
    try:
        # Read the subject number supplied on the command line
        if len(sys.argv) != 2:
            raise ValueError('Usage: python blocked_input_converter.py <subject_number>')
        subject_number = int(sys.argv[1])
        convert_subject(subject_number)
    except (ValueError, OSError, KeyError) as error:
        # Report the reason for stopping without continuing to another file
        sys.exit('Conversion stopped: %s' % error)
