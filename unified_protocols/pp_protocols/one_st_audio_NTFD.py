# one_st_audio_NTFD.py — Audio No-Temporal
MODALITY, TASK, FAMILY = "audio", "NTFD", "st" 
import os, csv, re, sys
from pathlib import Path

import psychopy

from psychopy import prefs
prefs.hardware['audioLib'] = ['ptb']  # PTB only; no fallback

import psychopy.visual, psychopy.event, psychopy.core
from psychopy import gui

from one_stim_tracker_setup import connect_stimtracker

try:
    import psychtoolbox as ptb
    _HAS_PTB = True
except Exception:
    _HAS_PTB = False

from stimuli_setup import (
    win, purple_cross, black_cross, gray_cross,
    text,
    audiowav_medium, beep_220hz, beep_880hz,
    startkey, option1, option2,
    stim_duration, intertrial, onsettime, baselinetime
)

from utilities import notemporal_rating_py, load_inputs

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
os.makedirs("data", exist_ok=True)

def norm_sub(s):
    s = str(s).strip()
    if s.lower().startswith("sub-"):
        return s
    return f"sub-{int(s):02d}"

def norm_ses(s):
    s = str(s).strip()
    if s.lower().startswith(("ses-","pilotses-")):
        return s
    return f"ses-{int(s):02d}"

def _run_idx(p):
    m = re.search(r"run[-_]?(\d+)", p.stem, re.I)
    return int(m.group(1)) if m else 9999

def load_notemp_strict(subject_id, session_id, run_number, session_type='behavioral'):
    # 'training' inputs ignore subject and session; 'behavioral' inputs
    # are specific to subject, session and run.
    return load_inputs('audio', 'notemporal', run_number, session_type,
                       subject_id, session_id)

def resolve_target(trial: dict) -> str:
    raw = (trial.get('target') or trial.get('target_stim') or trial.get('audiowav_target') or
           trial.get('comparison') or trial.get('relation') or trial.get('target_shape') or '')
    s = str(raw).strip().lower().split('/')[-1].split('\\')[-1]
    for ext in ('.wav','.mp3','.flac'):
        if s.endswith(ext):
            s = s[:-len(ext)]
    s = s.replace('audiowav_','').replace('beep_','').replace('beep','').replace('-','').replace('_','')
    if '220' in s or s in ('low','lower'):
        return 'low'
    if '880' in s or s in ('high','higher'):
        return 'high'
    return 'high'

def isi_list_dynamic_ms(trial: dict):
    items=[]
    for k,v in trial.items():
        m = re.match(r'^\s*isi[_\-]?(\d+)\s*$', str(k).strip().lower())
        if m and str(v).strip():
            try:
                val = float(v)
                if val < 0:
                    val = 0.0
            except:
                val = 0.0
            items.append((int(m.group(1)), val))
    items.sort(key=lambda x:x[0])
    return [val for _,val in items]

STIM_MS = int(round(float(stim_duration) * 1000.0))
WAIT_MS = int(round(float(onsettime) * 1000.0))
INTRO_MS = 1250
CUE_MS  = int(round(0.50 * 1000.0))
ITI_MS  = int(round(float(intertrial) * 1000.0))
WITHIN_BLOCK_MS = ITI_MS + CUE_MS
TTL_KEY = startkey

A_MED, A_LOW, A_HIGH = "beep_440hz", "beep_220hz", "beep_880hz"

LLOG = [
    'subject_id','session_number','run_number','trial_number','trial_id','condition',
    'onset','duration','theoretical_isi/feedback','real_isi/feedback','rt','key'
]

FEEDBACK_TONE_BY_KEY = {
    option1: 'high',
    option2: 'low',
}

def _cli_exp_info():
    args = sys.argv[1:]
    if len(args) >= 4 and not args[0].lstrip("+-").isdigit():
        args = args[1:]
    if len(args) < 3:
        return None
    stim_tracker = args[3].strip().lower() if len(args) >= 4 else 'n'
    session_type = args[4].strip().lower() if len(args) >= 5 else 'behavioral'
    if stim_tracker not in ('y', 'n'):
        raise ValueError("StimTracker argument must be 'y' or 'n'")
    try:
        subject_id, session_number, run_number = (str(int(a)) for a in args[:3])
    except ValueError as exc:
        raise ValueError(
            "Usage: python one_st_audio_NTFD.py [pc_type] "
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

expInfo = _cli_exp_info()
if expInfo is None:
    expInfo = {'StimTracker? (y/n)' : 'n', 'subject_id':'05','session_number':'01','run_number':'1','session_type':'behavioral'}
    dlg = gui.DlgFromDict(expInfo, title='Audio Notemporal')
    if not dlg.OK:
        psychopy.core.quit()

from stimuli_setup import hide_cursor
hide_cursor()

use_hw = _stimtracker_enabled(expInfo['StimTracker? (y/n)'])
st = connect_stimtracker(enabled=use_hw, dummy=not use_hw, verbose=True)

cond_file, conditions = load_notemp_strict(expInfo["subject_id"], expInfo["session_number"], expInfo["run_number"], expInfo['session_type'])

import datetime
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
MODALITY = "audio"
TASK = "NTFD"
CODED = "st"
csv_path = HERE / "data" / (
    f"{MODALITY}_{TASK}_{CODED}-{int(expInfo['subject_id']):02d}"
    f"_ses-{int(expInfo['session_number']):02d}"
    f"_run-{int(expInfo['run_number']):02d}"
    f"_{stamp}.csv"
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
    xf.write(f"#e Task: st audio NTFD\n")
    xf.write(f"#e conditions: {cond_file.name}\n")
    xf.write("#--SUBJECT INFO\n")
    xf.write(f"#s id: {int(expInfo['subject_id'])}\n")
    xw.writerow(LLOG)

ms_now = lambda: float(psychopy.core.getTime()*1000.0)

from psychopy.hardware import keyboard
_KEYBOARD = keyboard.Keyboard()

if _HAS_PTB:
    _PTB0 = ptb.GetSecs()
    _CORE0 = ms_now()
    def _ptb_secs_to_ms(sec):
        return _CORE0 + (sec - _PTB0) * 1000.0
else:
    def _ptb_secs_to_ms(sec):
        return None

def _play_with_hw_time(snd):
    t0_sec = None
    try:
        t0_sec = snd.play(when=0)
    except TypeError:
        snd.play()
    except Exception:
        snd.play()

    if t0_sec in (None, '-', 0):
        for attr in ('getStartTime', 't0', 'tStart'):
            try:
                v = getattr(snd, attr)
                v = v() if callable(v) else v
                if isinstance(v, (int, float)) and v > 0:
                    t0_sec = v
                    break
            except Exception:
                pass

    if _HAS_PTB and isinstance(t0_sec, (int, float)) and t0_sec > 0:
        return _ptb_secs_to_ms(t0_sec)
    return None

def confirm_quit():
    psychopy.event.clearEvents(eventType='keyboard')
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
        keys = psychopy.event.getKeys(keyList=['y', 'n'])
        if 'y' in keys:
            return True
        if 'n' in keys:
            return False
        psychopy.core.wait(0.01)

def kill_check():
    if psychopy.event.getKeys(keyList=['escape']):
        if confirm_quit():
            raise SystemExit

    for k, mods in psychopy.event.getKeys(keyList=['q'], modifiers=True):
        if mods.get('ctrl') or mods.get('command'):
            if confirm_quit():
                raise SystemExit

def show_run_intro(task_name, run_number):
    # Show the task name, then the run number, matching the bauto launch screens.
    for intro_text in (task_name, "Run %d" % int(run_number)):
        psychopy.event.clearEvents(eventType='keyboard')
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
    psychopy.event.clearEvents(eventType='keyboard')

def wait_ms(ms_total):
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

def write_row(base_list):
    b = [subject_id] + list(base_list)

    while len(b) < 12:
        b.append('-')

    def to_int_or_dash(x):
        try:
            return int(round(float(x)))
        except Exception:
            return '-'

    # new indexes because subject_id was added at the front
    b[6] = to_int_or_dash(b[6])   # onset
    b[7] = to_int_or_dash(b[7])   # duration
    b[8] = to_int_or_dash(b[8])   # theoretical
    b[9] = to_int_or_dash(b[9])   # realized

    if b[10] != '-':
        b[10] = to_int_or_dash(b[10])  # rt

    xw.writerow(b)

subject_id = int(expInfo["subject_id"])
session_id = int(expInfo["session_number"])
block_no = int(expInfo["run_number"])
_score_targets, _score_rts, _score_keys = [], [], []

try:
    show_run_intro("Audio NTFD", block_no)

    psychopy.event.clearEvents(eventType='keyboard')
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

    t_fix3_ms = ms_now()
    gray_cross.draw(); win.flip()
    load3_ms = ms_now() - t_fix3_ms
    wait_ms(max(0, CUE_MS - load3_ms))

    write_row([session_id, block_no, '-', 'ttl', '-', t_ttl_ms, ms_now()-t_ttl_ms, '-', '-', '-', '-'])

    for i, trial in enumerate(conditions, start=1):
        kill_check()
        psychopy.event.clearEvents(eventType='keyboard')

        tnum_field = str(trial.get('trial_number', '')).strip()
        is_baseline = str(trial.get('trial_id','')).strip().lower() == 'baseline'
        if tnum_field and tnum_field != '-' and not is_baseline:
            tnum = int(tnum_field)
        elif not is_baseline:
            tnum = i
        else:
            tnum = '-'

        trial_label = trial.get('trial_id', f't{i}')
        last = (i == len(conditions))
        next_is_baseline = (str(conditions[i].get('trial_id','')).strip().lower() == 'baseline') if not last else False

        if is_baseline:
            t_base_ms = ms_now()
            black_cross.draw(); win.flip()
            load2_ms = ms_now() - t_base_ms
            base_ms = int(round(float(baselinetime)*1000.0))
            if not last:
                wait_ms(max(0, base_ms - load2_ms - CUE_MS))
                t_fix3_ms = ms_now(); gray_cross.draw(); win.flip()
                load3_ms = ms_now() - t_fix3_ms
                wait_ms(max(0, CUE_MS - load3_ms))
            else:
                wait_ms(max(0, base_ms - load2_ms))
            write_row([session_id, block_no, '-', 'baseline', '-', t_base_ms, ms_now()-t_base_ms, '-', '-', '-', '-'])
            continue

        isi_ms_list = isi_list_dynamic_ms(trial)

        for j, isi_ms in enumerate(isi_ms_list, 1):
            t_beep_ms = ms_now()
            st.pulse_audio()
            _play_with_hw_time(audiowav_medium)

            gray_cross.draw(); win.flip()
            wait_ms(max(0, STIM_MS - (ms_now()-t_beep_ms))) #due to flip-related latency

            audio_duration_ms = ms_now() - t_beep_ms

            write_row([session_id, block_no, tnum, trial_label, A_MED,
                       t_beep_ms, audio_duration_ms, '-', '-', '-', '-'])

            t_int_ms = ms_now()
            wait_ms(max(0, int(round(isi_ms)) - audio_duration_ms))
            interval_clock_duration = ms_now() - t_int_ms
            realized_soft = ms_now() - t_beep_ms

            write_row([session_id, block_no, tnum, trial_label, f"interval_{j}",
                       t_int_ms, interval_clock_duration, int(round(isi_ms)), realized_soft, '-', '-'])

        # ---------- TARGET ----------
        label = resolve_target(trial)

        t_tar_ms = ms_now()
        st.pulse_audio()

        if label == 'low':
            beep_220hz.stop()
            _play_with_hw_time(beep_220hz)
            ev = A_LOW
        else:
            beep_880hz.stop()
            _play_with_hw_time(beep_880hz)
            ev = A_HIGH

        gray_cross.draw(); win.flip()
        wait_ms(max(0, STIM_MS - (ms_now() - t_tar_ms)))  # compensate for flip-related latency

        target_cpu_dur_ms = ms_now() - t_tar_ms

        write_row([session_id, block_no, tnum, trial_label, ev,
                   t_tar_ms, target_cpu_dur_ms, '-', '-', '-', '-'])

        # feedback onset and RT zero anchored to target offset meaning
        target_offset_ms = t_tar_ms + STIM_MS

        now_ms = ms_now()
        if now_ms < target_offset_ms:
            wait_ms(target_offset_ms - now_ms)

        # ---------- FEEDBACK ----------
        FB_MS = 2000
        t_feedback_ms = target_offset_ms

        _KEYBOARD.clearEvents()
        rt0_ms = ms_now()
        _KEYBOARD.clock.reset()
        psychopy.event.clearEvents(eventType='keyboard')

        gray_cross.draw(); win.flip()

        key = None
        rt_ms = None
        deadline_ms = t_feedback_ms + FB_MS

        while ms_now() < deadline_ms and key is None:
            kill_check()
            evs = _KEYBOARD.getKeys([option1, option2], waitRelease=False, clear=False)
            if evs:
                evk = min(evs, key=lambda e: e.rt if e.rt is not None else float('inf'))
                if evk.rt is not None:
                    key = evk.name
                    rt_ms = int(round(evk.rt * 1000.0))

                    st.pulse_audio()

                    choice = FEEDBACK_TONE_BY_KEY.get(key, None)
                    if choice == 'low':
                        beep_880hz.stop(); beep_220hz.stop()
                        beep_220hz.play()
                        wait_ms(STIM_MS)
                        beep_220hz.stop()
                    elif choice == 'high':
                        beep_220hz.stop(); beep_880hz.stop()
                        beep_880hz.play()
                        wait_ms(STIM_MS)
                        beep_880hz.stop()
                    break

            psychopy.core.wait(0.002)

        if key is None:
            fb_end_ms = t_feedback_ms + FB_MS
            now_ms = ms_now()
            if now_ms < fb_end_ms:
                wait_ms(fb_end_ms - now_ms)

            # duration = target offset -> response-window deadline
            feedback_duration_ms = FB_MS

            # realized = target onset -> response-window deadline
            feedback_realized_ms = STIM_MS + FB_MS

        else:
            # response onset is measured from keyboard reset time rt0_ms + keyboard rt since that reset time
            response_onset_ms = rt0_ms + rt_ms

            # duration = target offset -> response onset
            feedback_duration_ms = response_onset_ms - t_feedback_ms

            # realized = target onset -> response onset
            feedback_realized_ms = response_onset_ms - t_tar_ms

            fb_end_ms = response_onset_ms + STIM_MS
            now_ms = ms_now()
            if now_ms < fb_end_ms:
                wait_ms(fb_end_ms - now_ms)

        write_row([session_id, block_no, tnum, trial_label, 'feedback',
                t_feedback_ms, feedback_duration_ms, FB_MS + STIM_MS, feedback_realized_ms,
                (rt_ms if rt_ms is not None else '-'), (key if key is not None else '-')])

        _score_targets.append(label)
        _score_rts.append(feedback_duration_ms if rt_ms is not None else None)
        _score_keys.append(key if key is not None else None)

        t_wb_ms = ms_now()
        black_cross.draw(); win.flip()
        load2_ms = ms_now() - t_wb_ms
        if not last:
            if next_is_baseline:
                wait_ms(max(0, WITHIN_BLOCK_MS - load2_ms))
            else:
                wait_ms(max(0, WITHIN_BLOCK_MS - load2_ms - CUE_MS))
                t_fix3_ms = ms_now(); gray_cross.draw(); win.flip()
                load3_ms = ms_now() - t_fix3_ms
                wait_ms(max(0, CUE_MS - load3_ms))
        else:
            wait_ms(max(0, WITHIN_BLOCK_MS - load2_ms))

        write_row([session_id, block_no, '-', 'fixcross', '-',
                   t_wb_ms, ms_now()-t_wb_ms, '-', '-', '-', '-'])

    score_pct, score_list = notemporal_rating_py(
        targets=_score_targets,
        reaction_times=_score_rts,
        key_presses=_score_keys,
        option1_targets={"high"},
        option2_targets={"low"},
    )

    msg = f"Your score is {score_pct:.2f}%."
    psychopy.event.clearEvents(eventType='keyboard')
    psychopy.visual.TextStim(win, text=msg, color="yellow", height=0.07, pos=(0,0)).draw()
    win.flip()
    psychopy.core.wait(2.0)

    t_sum_ms = ms_now()
    write_row([session_id, block_no, '-', 'score', '-', t_sum_ms, 0, '-', '-', '-', f"{score_pct:.2f}%"])

    win.close()
    xf.close()

    try:
        st.close()
    except Exception:
        pass

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
