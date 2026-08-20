# one_st_audio_perception_explicit.py — Audio Perception (explicit instruction)

import os, csv, re, sys, datetime
from pathlib import Path
from typing import List, Tuple, Optional

import psychopy
from psychopy import prefs
prefs.hardware['audioLib'] = ['ptb']  # PTB only; no fallback

import psychopy.visual, psychopy.event, psychopy.core
from psychopy import gui
from psychopy.hardware import keyboard

from one_stim_tracker_setup import connect_stimtracker

from utilities import perception_rating_py, play_isi_explicit, is_beat_trial, load_training_inputs, load_inputs

from stimuli_setup import (
    win, purple_cross, black_cross, gray_cross,
    audiowav_medium, get_soft_beep, soft_beep_available, soft_beep_error,
    BEEP_SOFT_FILE,
    startkey, option1, option2,
    stim_duration, intertrial, onsettime, baselinetime
)

# Optional prompts (longer/shorter + instruction text)
try:
    from stimuli_setup import text2, longer, shorter
    _HAS_LS = True
except Exception:
    _HAS_LS = False
    try:
        from stimuli_setup import text2 as _maybe_text2
    except Exception:
        _maybe_text2 = None

# Explicit variant needs the soft beep; fail LOUD and visible if absent.
if not soft_beep_available:
    reason = (
        "EXPLICIT VARIANT ABORTED: the soft beep could not be loaded.\n"
        "  Looking for : audio_stim/%s\n"
        "  Reason      : %s\n"
        "Fix: put that exact file in audio_stim/, OR set BEEP_SOFT_FILE in "
        "stimuli_setup.py to the name you actually have, then rerun."
        % (BEEP_SOFT_FILE, soft_beep_error or "file not found")
    )
    print("\n*** " + reason + " ***\n")
    try:
        psychopy.visual.TextStim(
            win, text="Soft beep missing:\n" + BEEP_SOFT_FILE +
                 "\n\nSee console / log for details.",
            color="white", height=0.05, pos=(0, 0)).draw()
        win.flip()
        psychopy.core.wait(5.0)
    except Exception:
        pass
    try:
        win.close()
    except Exception:
        pass
    raise SystemExit(reason)

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
os.makedirs("data", exist_ok=True)

# ---------- ID normalizers (strict, zero-pad) ----------
def norm_sub(s):
    s = str(s).strip()
    return s if s.lower().startswith("sub-") else f"sub-{int(s):02d}"

def norm_ses(s):
    s = str(s).strip()
    return s if s.lower().startswith(("ses-","pilotses-")) else f"ses-{int(s):02d}"

# ---------- run index extractor ----------
def _run_idx(p: Path) -> int:
    m = re.search(r"run[-_]?(\d+)", p.stem, re.I)
    return int(m.group(1)) if m else 9999

# ---------- strict loader (TSV only) ----------
def load_perception(subject_id, session_id, run_number, session_type='training'):
    # 'training' inputs ignore subject and session; 'behavioral' inputs
    # are specific to subject, session and run.
    return load_inputs('audio', 'perception', run_number, session_type,
                       subject_id, session_id)

# ---------- helpers ----------
def parse_isis(tr: dict) -> List[int]:
    """Return isi_1..isi_k as integer ms (IOI, onset→onset)."""
    items = []
    for k, v in tr.items():
        kk = str(k).strip().lower()
        m = re.fullmatch(r"isi[_-]?(\d+)", kk)
        if not m:
            continue
        val = str(v).strip()
        if val in ("", "-"):
            continue
        try:
            items.append((int(m.group(1)), int(round(float(val)))))
        except Exception:
            pass
    items.sort(key=lambda x: x[0])
    return [ms for _, ms in items]

def _extract_std_cmp_ms(trial: dict) -> Tuple[Optional[float], Optional[float]]:
    def _get_first(keys):
        for k in keys:
            if k in trial and str(trial[k]).strip() not in ("", "-"):
                try:
                    return float(trial[k])
                except Exception:
                    pass
        return None

    std = _get_first(["standard_time","std_time","std_ms","isi_std","std","standard"])
    cmp_ = _get_first(["perception_time","cmp_time","cmp_ms","isi_cmp","cmp","comparison"])
    if std is None:
        std = _get_first(["isi_1","isi1"])
    if cmp_ is None:
        cmp_ = _get_first(["isi_5","isi5","comparison_isi"])
    return std, cmp_


# ---------- timings (ms) ----------
STIM_MS = int(round(float(stim_duration) * 1000.0))
WAIT_MS = int(round(float(onsettime) * 1000.0))
INTRO_MS = 1250
CUE_MS  = 500
ITI_MS  = int(round(float(intertrial) * 1000.0))
WITHIN_BLOCK_MS = ITI_MS + CUE_MS
TTL_KEY = startkey

A_MED = "beep_440hz"

# ---------- log schema (match PTB) ----------
LLOG = [
    'subject_id','session_number','run_number','trial_number','trial_id','condition',
    'onset','duration','theoretical_isi/feedback','real_isi/feedback','rt','key'
]

# ---------- time + waits ----------
ms_now = lambda: float(psychopy.core.getTime() * 1000.0)
_KEYBOARD = keyboard.Keyboard()

def confirm_quit():
    psychopy.event.clearEvents(eventType="keyboard")
    psychopy.visual.TextStim(
        win,
        text="Quit? (y/n)",
        color=[51, 34, 136],
        colorSpace="rgb255",
        height=0.06,
        pos=(0, 0)
    ).draw()
    win.flip()

    while True:
        keys = psychopy.event.getKeys(keyList=["y", "n"])
        if "y" in keys:
            return True
        if "n" in keys:
            return False
        psychopy.core.wait(0.01)

def kill_check():
    if psychopy.event.getKeys(keyList=["escape"]):
        if confirm_quit():
            raise SystemExit

    for k, mods in psychopy.event.getKeys(keyList=['q'], modifiers=True):
        if mods.get('ctrl') or mods.get('command'):
            if confirm_quit():
                raise SystemExit

def show_run_intro(task_name, run_number):
    # Show the task name, then the run number, matching the bauto launch screens.
    for intro_text in (task_name, "Run %d" % int(run_number)):
        psychopy.event.clearEvents(eventType="keyboard")
        psychopy.visual.TextStim(
            win,
            text=intro_text,
            color=[51, 34, 136],
            colorSpace="rgb255",
            height=0.08,
            pos=(0, 0)
        ).draw()
        win.flip()
        wait_ms(INTRO_MS)
    psychopy.event.clearEvents(eventType="keyboard")

def wait_ms(ms_total: float):
    end = ms_now() + float(ms_total)
    while True:
        now = ms_now()
        rem = end - now
        if rem <= 4.0:
            break
        kill_check()
        psychopy.core.wait(0.002)
    while True:
        now = ms_now()
        rem = end - now
        if rem <= 0.4:
            break
        kill_check()
        psychopy.core.wait(0.001)
    while ms_now() < end:
        kill_check()

def _play_now(snd):
    try:
        snd.play(when=0)
    except TypeError:
        snd.play()
    except Exception:
        snd.play()

def _play_soft_beep():
    """Play one softer beep, mirroring the main beep (returns onset, duration ms)."""
    t_soft = ms_now()
    st.pulse_audio()
    _play_now(get_soft_beep())
    gray_cross.draw()
    win.flip()
    wait_ms(max(0, STIM_MS - (ms_now() - t_soft)))
    return t_soft, ms_now() - t_soft

def write_row(xw, base_list):
    b = [subject_id] + list(base_list)

    while len(b) < 12:
        b.append('-')

    def to_int_or_dash(x):
        try:
            return int(round(float(x)))
        except Exception:
            return '-'

    # shifted by +1 because subject_id is now first
    b[6] = to_int_or_dash(b[6])                      # onset
    b[7] = to_int_or_dash(b[7])                      # duration
    b[8] = to_int_or_dash(b[8])                      # theoretical
    b[9] = to_int_or_dash(b[9])                      # realized
    b[10] = to_int_or_dash(b[10]) if b[10] != '-' else '-'  # rt

    xw.writerow(b)

def _cli_exp_info():
    args = sys.argv[1:]
    if len(args) >= 4 and not args[0].lstrip("+-").isdigit():
        args = args[1:]
    if len(args) < 3:
        return None
    stim_tracker = args[3].strip().lower() if len(args) >= 4 else 'n'
    session_type = args[4].strip().lower() if len(args) >= 5 else 'training'
    if stim_tracker not in ('y', 'n'):
        raise ValueError("StimTracker argument must be 'y' or 'n'")
    try:
        subject_id, session_number, run_number = (str(int(a)) for a in args[:3])
    except ValueError as exc:
        raise ValueError(
            "Usage: python one_st_audio_perception.py [pc_type] "
            "<subject_number> <session_number> <run_number> [stimtracker_y_or_n]"
        ) from exc
    return {
        'StimTracker? (y/n)': stim_tracker,
        'subject_id': subject_id,
        'session_number': session_number,
        'run_number': run_number,
        'session_type': session_type,
    }

def _stimtracker_enabled(value):
    return str(value).strip().lower() == 'y'

# ---------- UI / CLI ----------
expInfo = _cli_exp_info()
if expInfo is None:
    expInfo = {'StimTracker? (y/n)': 'n', 'subject_id':'05','session_number':'01','run_number':'1','session_type':'training'}
    dlg = gui.DlgFromDict(expInfo, title='Audio Perception (explicit)')
    if not dlg.OK:
        psychopy.core.quit()

from stimuli_setup import hide_cursor
hide_cursor()

use_hw = _stimtracker_enabled(expInfo['StimTracker? (y/n)'])
st = connect_stimtracker(enabled=use_hw, dummy=not use_hw, verbose=True)

cond_file, conditions = load_perception(expInfo['subject_id'], expInfo['session_number'], expInfo['run_number'], expInfo['session_type'])

# ---------- logger ----------
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
MODALITY = "audio"
TASK = "perception"
CODED = "st"
csv_path = HERE / "data" / (
    f"{MODALITY}_{TASK}_{CODED}-{int(expInfo['subject_id']):02d}"
    f"_ses-{int(expInfo['session_number']):02d}"
    f"_run-{int(expInfo['run_number']):02d}"
    f"_explicit_{stamp}.csv"
)
xf = open(csv_path, "a", encoding="utf-8", newline="")
xw = csv.writer(xf)

if xf.tell() == 0:
    now_str = datetime.datetime.now().strftime("%a %b %d %Y %H:%M:%S")
    pyver = sys.version.split()[0]
    mainfile = Path(__file__).name
    xf.write(f"#Python {pyver}, coding: UTF-8\n")
    xf.write(f"#date: {now_str}\n")
    xf.write("#--EXPERIMENT INFO\n")
    xf.write(f"#st_enabled: {str(use_hw).lower()}\n")
    xf.write(f"#e mainfile: {mainfile}\n")
    xf.write("#e Task: st audio PERCEPTION (explicit)\n")
    xf.write(f"#e conditions: {cond_file.name}\n")
    xf.write("#--SUBJECT INFO\n")
    xf.write(f"#s id: {int(expInfo['subject_id'])}\n")
    xw.writerow(LLOG)

# ---------- RUN ----------
subject_id = int(expInfo["subject_id"])
session_id = int(expInfo["session_number"])
block_no = int(expInfo["run_number"])

_score_keys, _score_stds, _score_cmps = [], [], []

try:
    show_run_intro("Audio Perception", block_no)

    # TTL -> WAIT -> CUE
    psychopy.event.clearEvents(eventType="keyboard")
    purple_cross.draw(); win.flip()
    while True:
        kill_check()
        if psychopy.event.getKeys(keyList=[TTL_KEY]):
            break
        psychopy.core.wait(0.01)
    t_ttl_ms = ms_now()

    black_cross.draw(); win.flip()
    load2_ms = ms_now() - t_ttl_ms
    wait_ms(max(0, WAIT_MS - load2_ms - CUE_MS))

    t_cue_ms = ms_now()
    gray_cross.draw(); win.flip()
    load3_ms = ms_now() - t_cue_ms
    wait_ms(max(0, CUE_MS - load3_ms))

    write_row(xw, [session_id, block_no, "-", "ttl", "-", t_ttl_ms, ms_now()-t_ttl_ms, "-", "-", "-", "-"])

    N = len(conditions)

    for i, tr in enumerate(conditions, start=1):
        kill_check()
        psychopy.event.clearEvents(eventType="keyboard")

        trial_label = str(tr.get("trial_id", f"t{i}"))
        is_baseline = trial_label.strip().lower() == "baseline"

        tnum_field = str(tr.get("trial_number", "")).strip()
        if is_baseline:
            tnum = "-"
        else:
            tnum = int(tnum_field) if tnum_field not in ("", "-") else i

        last = (i == N)
        next_is_baseline = (str(conditions[i].get("trial_id","")).strip().lower() == "baseline") if not last else False

        # ---- baseline ----
        if is_baseline:
            base_ms = int(round(float(baselinetime) * 1000.0))
            t_base_ms = ms_now()
            black_cross.draw(); win.flip()
            wait_ms(base_ms)
            write_row(xw, [session_id, block_no, "-", "baseline", "-", t_base_ms, ms_now()-t_base_ms, "-", "-", "-", "-"])

            # cue after baseline (not part of baseline)
            if not last:
                t_fix3_ms = ms_now()
                gray_cross.draw(); win.flip()
                load3_ms = ms_now() - t_fix3_ms
                wait_ms(max(0, CUE_MS - load3_ms))
            continue

        # ---- beep train ----
        isis = parse_isis(tr)  # IOIs (onset→onset), ms

        # Explicit variant: subdivide each on-beat multiple of the unit (isi_1)
        # with softer beeps. Non-beat trials and the (sub-unit) probe isi_5 are
        # never exact multiples >= 2, so they pass through unchanged.
        is_beat = is_beat_trial(trial_label)
        base_unit = (isis[0] if isis else 0)

        # keep state for measuring (Expyriment meaning)
        prev_on_ms: Optional[float] = None
        prev_off_ms: Optional[float] = None
        prev_dur_ms: Optional[float] = None

        # First beep
        t_on = ms_now()
        st.pulse_audio()
        _play_now(audiowav_medium)

        gray_cross.draw()
        win.flip()

        wait_ms(STIM_MS - (ms_now() - t_on))  # compensate for flip-related latency

        t_off = ms_now()
        dur_ms = t_off - t_on

        write_row(xw, [session_id, block_no, tnum, trial_label, A_MED,
                    t_on, dur_ms, "-", "-", "-", "-"])

        prev_on_ms, prev_off_ms, prev_dur_ms = t_on, t_off, dur_ms
        # For each isi_k: play/measure the interval (in the explicit variant a 3T
        # on-beat interval is split into 3 sub-intervals marked by softer beeps),
        # then play the medium beep that terminates it.
        for k, th_ioi_ms in enumerate(isis, start=1):
            # Interval after the preceding beep (preceding onset/duration measured).
            play_isi_explicit(
                k, th_ioi_ms, prev_on_ms, prev_dur_ms, base_unit, is_beat,
                _play_soft_beep,
                lambda *row: write_row(xw, [session_id, block_no, tnum,
                                            trial_label, *row]),
                wait_ms, ms_now)

            # next beep onset (measured) — terminates interval_k
            t_on2 = ms_now()
            st.pulse_audio()
            _play_now(audiowav_medium)

            gray_cross.draw()
            win.flip()

            wait_ms(STIM_MS - (ms_now() - t_on2))  # compensate for flip-related latency

            t_off2 = ms_now()
            dur2 = t_off2 - t_on2

            write_row(xw, [session_id, block_no, tnum, trial_label, A_MED,
                        t_on2, dur2, "-", "-", "-", "-"])

            prev_on_ms, prev_off_ms, prev_dur_ms = t_on2, t_off2, dur2
        # ---- feedback window (PTB-parity semantics) ----
        FB_MS = 2000

        last_beep_on = prev_on_ms
        last_beep_off = prev_off_ms   # feedback onset anchor (measured beep offset)

        # reset RT clock at the anchor moment (we are at/after last_beep_off here)
        _KEYBOARD.clearEvents()
        rt0_ms = ms_now()
        _KEYBOARD.clock.reset()

        # show response screen immediately (does not define onset; onset is last_beep_off by design)
        if _HAS_LS:
            try:
                text2.draw(); longer.draw(); shorter.draw()
            except Exception:
                pass
        elif _maybe_text2 is not None:
            _maybe_text2.draw()
        win.flip()

        t_fb_ms = last_beep_off
        t_deadline = t_fb_ms + FB_MS

        key = None
        rt_ms = None

        while ms_now() < t_deadline and key is None:
            kill_check()
            evs = _KEYBOARD.getKeys([option1, option2], waitRelease=False, clear=False)
            if evs:
                e = min(evs, key=lambda x: x.rt if x.rt is not None else float("inf"))
                if e.rt is not None:
                    key = e.name
                    rt_ms = int(round(e.rt * 1000.0))   # ms since clock reset (~since beep offset)
                    st.pulse_audio()  # ST: mark RT-defining key
                    break
            psychopy.core.wait(0.002)

        # termination rule:
        # - no response: end at deadline
        # - response: log interval to response onset
        if key is None:
            response_onset_ms = t_deadline
            end_ms = t_deadline

            now_ms = ms_now()
            if now_ms < end_ms:
                wait_ms(end_ms - now_ms)
        else:
            response_onset_ms = rt0_ms + float(rt_ms)

            # keep the old behavioural waiting rule if you still want the same post-response pause
            end_ms = response_onset_ms + float(STIM_MS)

            now_ms = ms_now()
            if now_ms < end_ms:
                wait_ms(end_ms - now_ms)

        # duration = last beep offset -> response onset
        # realized = last beep onset -> response onset
        fb_dur_ms = response_onset_ms - t_fb_ms
        fb_realized_ms = response_onset_ms - last_beep_on

        write_row(xw, [session_id, block_no, tnum, trial_label, "feedback",
                    t_fb_ms, fb_dur_ms, FB_MS + STIM_MS, fb_realized_ms,
                    (rt_ms if rt_ms is not None else "-"), key or "-"])
        # scoring collect
        std_ms, cmp_ms = _extract_std_cmp_ms(tr)
        _score_keys.append(key if key is not None else None)
        _score_stds.append(std_ms)
        _score_cmps.append(cmp_ms)

        # ---- ITI + optional pre-cue ----
        t_wb_ms = ms_now()
        black_cross.draw(); win.flip()
        load2_ms = ms_now() - t_wb_ms

        if not last:
            if next_is_baseline:
                wait_ms(max(0, WITHIN_BLOCK_MS - load2_ms))
            else:
                wait_ms(max(0, WITHIN_BLOCK_MS - load2_ms - CUE_MS))
                t_fix3_ms = ms_now()
                gray_cross.draw(); win.flip()
                load3_ms = ms_now() - t_fix3_ms
                wait_ms(max(0, CUE_MS - load3_ms))
        else:
            wait_ms(max(0, WITHIN_BLOCK_MS - load2_ms))

        write_row(xw, [session_id, block_no, "-", "fixcross", "-",
                       t_wb_ms, ms_now()-t_wb_ms, "-", "-", "-", "-"])

    # ---- score ----
    score_pct, _ = perception_rating_py(_score_keys, _score_stds, _score_cmps)
   
    msg = f"Your score is {score_pct:.2f}%."
    psychopy.event.clearEvents(eventType="keyboard")
    psychopy.visual.TextStim(win, text=msg, color="yellow", height=0.07, pos=(0,0)).draw()
    win.flip()
    psychopy.core.wait(2.0)

    t_sum_ms = ms_now()
    write_row(xw, [session_id, block_no, "-", "score", "-", t_sum_ms, 0, "-", "-", "-", f"{score_pct:.2f}%"])

    try:
        st.close()
    except Exception:
        pass

    win.close()
    xf.close()
    print("Using:", cond_file)
    print("Wrote log:", csv_path)

except SystemExit:
    try:
        xf.close()
    except Exception:
        pass
    try:
        win.close()
    except Exception:
        pass
    try:
        st.close()
    except Exception:
        pass
    print("Run aborted by user.")
    sys.exit(0)
