#utilities.py

import re
import csv
from pathlib import Path

# Root of the training-session inputs, resolved from this file so that the
# protocols can be launched from any working directory.
TRAINING_INPUTS = (Path(__file__).resolve().parent.parent /
                   'inputs' / 'training-session_inputs')


def _run_idx(p):
    m = re.search(r'run[-_]?(\d+)', p.stem, re.I)
    return int(m.group(1)) if m else 9999


# Roots of the two input trees, resolved from this file so that the protocols
# can be launched from any working directory.
TRAINING_INPUTS = (Path(__file__).resolve().parent.parent /
                   'inputs' / 'training-session_inputs')
BEHAVIOURAL_INPUTS = (Path(__file__).resolve().parent.parent /
                      'inputs' / 'behavioral-sessions_inputs')


def norm_session_type(value):
    # Accept 'training'/'behavioral' (and the obvious short forms).
    v = str(value).strip().lower()
    if v in ('training', 'train', 't'):
        return 'training'
    if v in ('behavioral', 'behavioural', 'behav', 'b'):
        return 'behavioral'
    raise ValueError("session_type must be 'training' or 'behavioral', "
                     'got %r' % (value,))


def _norm_sub(s):
    s = str(s).strip()
    return s if s.lower().startswith('sub-') else 'sub-%02d' % int(s)


def _norm_ses(s):
    s = str(s).strip()
    if s.lower().startswith(('ses-', 'pilotses-')):
        return s
    return 'ses-%02d' % int(s)


def _pick_run(in_dir, modality, task, run_number):
    files = sorted(in_dir.glob('%s_%s_run*.tsv' % (modality, task)),
                   key=_run_idx)
    if not files:
        files = sorted(in_dir.glob('*.tsv'), key=_run_idx)
    if not files:
        raise FileNotFoundError('No .tsv file in %s' % in_dir)

    idx = int(run_number) - 1
    if idx < 0 or idx >= len(files):
        raise IndexError('run_number %s invalid; have %d runs'
                         % (run_number, len(files)))

    pick = files[idx]
    with open(pick, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    return pick, rows


def load_inputs(modality, task, run_number, session_type='behavioral',
                subject_id=None, session_id=None):
    # Load one run of the inputs, from either input tree.
    #
    # session_type = 'training': the inputs are agnostic to subject and
    # session, but not to run. They live in
    # <training-session_inputs>/inputs_<task>/<modality>.
    #
    # session_type = 'behavioral': the inputs are specific to subject,
    # session and run. They live in
    # <behavioral-sessions_inputs>/sub-XX/ses-XX/inputs_<task>*/<modality>.
    #
    # This mirrors _load_inputs() of the Expyriment protocols, which
    # switches on setting['sesstype'] in the same way.
    #
    # modality: 'audio' or 'visual'; task: 'production', 'perception' or
    # 'notemporal'.
    if norm_session_type(session_type) == 'training':
        in_dir = TRAINING_INPUTS / ('inputs_' + task) / modality
        if not in_dir.is_dir():
            raise FileNotFoundError('Missing training inputs: %s' % in_dir)
        return _pick_run(in_dir, modality, task, run_number)

    ses_dir = (BEHAVIOURAL_INPUTS / _norm_sub(subject_id) /
               _norm_ses(session_id))
    if not ses_dir.is_dir():
        core = _norm_ses(session_id).split('-')[-1]
        alt = BEHAVIOURAL_INPUTS / _norm_sub(subject_id) / ('pilotses-%s' % core)
        if not alt.is_dir():
            raise FileNotFoundError('Missing session dir: %s' % ses_dir)
        ses_dir = alt

    in_dir = None
    for d in sorted(ses_dir.glob('inputs_%s*' % task)):
        if (d / modality).is_dir():
            in_dir = d / modality
            break
    if in_dir is None:
        raise FileNotFoundError('No inputs_%s*/%s under %s'
                                % (task, modality, ses_dir))
    return _pick_run(in_dir, modality, task, run_number)


def load_training_inputs(modality, task, run_number):
    # Kept for backward compatibility.
    return load_inputs(modality, task, run_number, 'training')


from stimuli_setup import option1, option2, stim_duration, BEEP_SOFT_CONDITION

#==================== UNIVERSAL SCORING ====================
production_min_ratio = 0.88
production_max_ratio = 1.12

notemporal_min_rt_ms = 100
notemporal_max_rt_ms = 700


def _finalize_score(flags, score=None):
    out = list(flags)
    if score is not None:
        out.extend(score)
    pct = round((out.count(1) / len(out)) * 100, 2) if out else 0.0
    return pct, out


def production_rating_py(reaction_times, standard_times, score=None, add_stim_duration=False, stimulus_duration_ms=None):
    if stimulus_duration_ms is None:
        stimulus_duration_ms = float(stim_duration) * 1000.0

    out = []
    for rt, st in zip(reaction_times, standard_times):
        if rt is None or st is None:
            out.append(0)
            continue
        try:
            produced_interval = float(rt) + float(stimulus_duration_ms) if add_stim_duration else float(rt)
            ratio = produced_interval / float(st)
            out.append(1 if (production_min_ratio < ratio < production_max_ratio) else 0)
        except Exception:
            out.append(0)

    return _finalize_score(out, score=score)


def perception_rating_py(keys, standard_times, comparison_times, score=None):
    out = []
    for key, standard_time, comparison_time in zip(keys, standard_times, comparison_times):
        if key is None or standard_time is None or comparison_time is None:
            out.append(0)
            continue
        try:
            standard_time = float(standard_time)
            comparison_time = float(comparison_time)
        except Exception:
            out.append(0)
            continue

        if key == option1:
            out.append(1 if comparison_time > standard_time else 0)
        elif key == option2:
            out.append(1 if comparison_time < standard_time else 0)
        else:
            out.append(0)

    return _finalize_score(out, score=score)


def notemporal_rating_py(targets, reaction_times, key_presses, option1_targets, option2_targets, score=None):
    option1_targets = set(option1_targets)
    option2_targets = set(option2_targets)

    out = []
    for target, rt, key in zip(targets, reaction_times, key_presses):
        try:
            ok_rt = rt is not None and (notemporal_min_rt_ms < float(rt) < notemporal_max_rt_ms)
        except Exception:
            ok_rt = False

        if key == option1:
            out.append(1 if (target in option1_targets and ok_rt) else 0)
        elif key == option2:
            out.append(1 if (target in option2_targets and ok_rt) else 0)
        else:
            out.append(0)

    return _finalize_score(out, score=score)


#-------------------- fdfdfdfdfdf --------------------

#============== EXPLICIT-INSTRUCTION SUBDIVISION (shared) ==============
SUBINTERVAL_TAG = "_sub"
SOFT_BEEP_CONDITION = BEEP_SOFT_CONDITION  # tracks BEEP_SOFT_FILE name
SOFT_STIM_CONDITION = SOFT_BEEP_CONDITION
TARGET_TRIAL_PREFIX = "beat"


def is_beat_trial(trial_label):
    """True for trials whose long intervals get subdivided in the explicit variant."""
    return str(trial_label).strip().lower().startswith(TARGET_TRIAL_PREFIX)


def play_isi_explicit_stim(k, ioims, t_stim, stim_dur, base_unit, is_beat,
                           play_soft_stim, log_event, wait_ms, ms_now,
                           soft_stim_condition=SOFT_STIM_CONDITION):
    """Present/log one inter-onset interval for the explicit variant.

    For a beat trial, an IOI that is an exact integer multiple n >= 2 of
    base_unit (the on-beat unit isi_1 = T) is split into n sub-intervals of
    base_unit, each internal boundary marked by a softer stimulus. Otherwise
    the IOI is played/logged unchanged. The time from the main stimulus onset
    to the next stimulus onset is preserved exactly (= ioims).

    Dependencies are injected so this stays free of PsychoPy/window globals:
        play_soft_stim() -> (onset_ms, duration_ms): present one soft stimulus.
        log_event(condition, onset, duration, theoretical, realized, rt, key):
            write one .csv row for the current trial.
        wait_ms(ms), ms_now(): timing helpers from the calling script.
    """
    label = "interval_%d" % k
    if is_beat and base_unit and ioims % base_unit == 0 \
            and ioims // base_unit >= 2:
        n_sub = ioims // base_unit
        for s in range(1, n_sub + 1):
            if s == 1:
                # First sub-interval follows the main stimulus.
                ref_onset, ref_dur = t_stim, stim_dur
            else:
                t_soft, soft_dur = play_soft_stim()
                log_event(soft_stim_condition, t_soft, soft_dur, '-', '-', '-', '-')
                ref_onset, ref_dur = t_soft, soft_dur
            t_sub = ms_now()
            wait_ms(max(0.0, float(base_unit) - float(ref_dur)))
            sub_dur = ms_now() - t_sub
            log_event(label + SUBINTERVAL_TAG + str(s), t_sub, sub_dur,
                      float(base_unit), ms_now() - ref_onset, '-', '-')
    else:
        t_interval = ms_now()
        wait_ms(max(0.0, float(ioims) - float(stim_dur)))
        interval_dur = ms_now() - t_interval
        log_event(label, t_interval, interval_dur, float(ioims),
                  ms_now() - t_stim, '-', '-')


def play_isi_explicit(k, ioims, t_beep, audio_dur, base_unit, is_beat,
                      play_soft_beep, log_event, wait_ms, ms_now,
                      soft_condition=SOFT_BEEP_CONDITION):
    """Audio-compatible wrapper for the generic explicit subdivision helper."""
    return play_isi_explicit_stim(
        k, ioims, t_beep, audio_dur, base_unit, is_beat,
        play_soft_beep, log_event, wait_ms, ms_now,
        soft_stim_condition=soft_condition)
