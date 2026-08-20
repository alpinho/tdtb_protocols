# one_st_audio_production.py — Audio production 

import os, csv, re, sys, datetime
from pathlib import Path
from typing import List

from psychopy import prefs
prefs.hardware['audioLib'] = ['ptb']  # PTB only; no fallback

import psychopy.visual, psychopy.event, psychopy.core
from psychopy import gui
from psychopy.hardware import keyboard

from one_stim_tracker_setup import connect_stimtracker

from utilities import production_rating_py, load_inputs

try:
    import psychtoolbox as ptb
    _HAS_PTB = True
except Exception:
    _HAS_PTB = False

# ===== stimuli + constants from your setup =====
from stimuli_setup import (
    win, purple_cross, black_cross, gray_cross,
    audiowav_medium,
    startkey, option1, option2,
    stim_duration, intertrial, onsettime, baselinetime,
    hide_cursor
)

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
os.makedirs('data', exist_ok=True)

# ---------- inputs base ----------
INPUTS_DIR = HERE.parent / "inputs" / "behavioral-sessions_inputs"

# ---------- ID helpers ----------
def norm_sub(s):
    s = str(s).strip()
    return s if s.lower().startswith('sub-') else f"sub-{int(s):02d}"

def norm_ses(s):
    s = str(s).strip()
    return s if s.lower().startswith(('ses-','pilotses-')) else f"ses-{int(s):02d}"

# ---------- TSV loader ----------
def _run_idx(p: Path):
    m = re.search(r"run[-_]?(\d+)", p.stem, re.I)
    return int(m.group(1)) if m else 9999

def load_production(subject_id, session_id, run_number, session_type='behavioral'):
    # 'training' inputs ignore subject and session; 'behavioral' inputs
    # are specific to subject, session and run.
    return load_inputs('audio', 'production', run_number, session_type,
                       subject_id, session_id)

# ---------- ISI parsing ----------
def parse_isis(tr: dict) -> List[int]:
    cands = []
    for k, v in tr.items():
        kk = str(k).strip().lower()
        m = re.fullmatch(r"isi[_-]?(\d+)", kk)
        if m:
            val = str(v).strip()
            if val != '' and val != '-':
                try:
                    cands.append((int(m.group(1)), int(round(float(val)))))
                except Exception:
                    pass
    cands.sort(key=lambda x: x[0])
    return [ms for _, ms in cands]  # IOIs (onset->onset), ms

# ---------- timings (ms) ----------
STIM_MS = int(round(float(stim_duration) * 1000.0))
WAIT_MS = int(round(float(onsettime) * 1000.0))
INTRO_MS = 1250
CUE_MS  = 500
ITI_MS  = int(round(float(intertrial) * 1000.0))
WITHIN_BLOCK_MS = ITI_MS + CUE_MS
TTL_KEY = startkey

# ---------- logging schema (Expyriment parity; NO jitter column) ----------
LLOG = [
    'subject_id','session_number','run_number','trial_number','trial_id','condition',
    'onset','duration','theoretical_isi/feedback','real_isi/feedback','rt','key'
]

# ---------- time utils ----------
ms_now = lambda: float(psychopy.core.getTime() * 1000.0)
_KEYBOARD = keyboard.Keyboard()

if _HAS_PTB:
    _PTB0 = ptb.GetSecs()
    _CORE0 = ms_now()
    def _ptb_secs_to_ms(sec):  # noqa: F811
        return _CORE0 + (sec - _PTB0) * 1000.0
else:
    def _ptb_secs_to_ms(sec):  # noqa: F811
        return None

def _play_start(snd):
    try:
        t0 = snd.play(when=0)
    except TypeError:
        snd.play(); t0 = None
    except Exception:
        snd.play(); t0 = None
    return t0

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

def wait_ms(ms_total: float):
    end = ms_now() + float(ms_total)
    while True:
        now = ms_now(); rem = end - now
        if rem <= 4.0:
            break
        kill_check()
        psychopy.core.wait(0.002)
    while True:
        now = ms_now(); rem = end - now
        if rem <= 0.4:
            break
        kill_check()
        psychopy.core.wait(0.001)
    while ms_now() < end:
        kill_check()

# ---------- row writer (match siblings: ints for ms fields) ----------
def w(xw, row):
    out = [subject_id] + list(row)

    while len(out) < 12:
        out.append('-')

    def to_int_or_dash(x):
        try:
            return int(round(float(x)))
        except Exception:
            return '-'

    # shifted by +1 because subject_id is now first
    out[6] = to_int_or_dash(out[6])  # onset
    out[7] = to_int_or_dash(out[7])  # duration
    out[8] = to_int_or_dash(out[8])  # theoretical
    out[9] = to_int_or_dash(out[9])  # realized
    out[10] = to_int_or_dash(out[10]) if out[10] != '-' else '-'  # rt

    xw.writerow(out)

# ---------- scoring helpers ----------

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
            "Usage: python one_st_audio_production.py [pc_type] "
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
    expInfo = {'StimTracker? (y/n)': 'n', 'subject_id': '05', 'session_number': '01', 'run_number': '1','session_type':'behavioral'}
    dlg = gui.DlgFromDict(expInfo, title='Audio Production - strict TSV')
    if not dlg.OK:
        psychopy.core.quit()

hide_cursor()

use_hw = _stimtracker_enabled(expInfo['StimTracker? (y/n)'])
st = connect_stimtracker(enabled=use_hw, dummy=not use_hw, verbose=True)

cond_file, conditions = load_production(expInfo['subject_id'], expInfo['session_number'], expInfo['run_number'], expInfo['session_type'])

# ---------- logger ----------
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
MODALITY = "audio"
TASK = "production"
CODED = "st"
csv_path = HERE / "data" / (
    f"{MODALITY}_{TASK}_{CODED}-{int(expInfo['subject_id']):02d}"
    f"_ses-{int(expInfo['session_number']):02d}"
    f"_run-{int(expInfo['run_number']):02d}"
    f"_{stamp}.csv"
)
xf = open(csv_path, 'a', encoding='utf-8', newline='')
xw = csv.writer(xf)

if xf.tell() == 0:
    now_str = datetime.datetime.now().strftime('%a %b %d %Y %H:%M:%S')
    pyver = sys.version.split()[0]
    mainfile = Path(__file__).name
    xf.write(f"#Python {pyver}, coding: UTF-8\n")
    xf.write(f"#date: {now_str}\n")
    xf.write('#--EXPERIMENT INFO\n')
    xf.write(f"#st_enabled: {str(use_hw).lower()}\n")
    xf.write(f"#e mainfile: {mainfile}\n")
    xf.write(f"#e Task: st audio PRODUCTION\n")
    xf.write(f"#e conditions: {cond_file.name}\n")
    xf.write('#--SUBJECT INFO\n')
    xf.write(f"#s id: {int(expInfo['subject_id'])}\n")
    xw.writerow(LLOG)

# ---------- RUN ----------
subject_id = int(expInfo['subject_id'])
session_id = int(expInfo['session_number'])
block_no = int(expInfo['run_number'])

_prod_rts, _prod_stds = [], []

try:
    show_run_intro("Audio Production", block_no)

    # TTL → wait(onsettime − cue) → CUE
    psychopy.event.clearEvents(eventType='keyboard')
    purple_cross.draw(); win.flip()
    while True:
        kill_check()
        if psychopy.event.getKeys(keyList=[startkey]):
            break
        psychopy.core.wait(0.01)
    t_ttl = ms_now()

    black_cross.draw(); win.flip()
    l2 = ms_now() - t_ttl
    wait_ms(max(0, WAIT_MS - l2 - CUE_MS))

    t_fix = ms_now(); gray_cross.draw(); win.flip()
    l3 = ms_now() - t_fix
    wait_ms(max(0, CUE_MS - l3))

    w(xw, [session_id, block_no, '-', 'ttl', '-', t_ttl, ms_now() - t_ttl, '-', '-', '-', '-'])

    N = len(conditions)
    for i, tr in enumerate(conditions, start=1):
        psychopy.event.clearEvents(eventType='keyboard')
        kill_check()

        trial_label = str(tr.get('trial_id', f't{i}'))
        is_baseline = trial_label.strip().lower() == 'baseline'
        tnum_field = str(tr.get('trial_number', '')).strip()
        tnum = ('-' if is_baseline else (int(tnum_field) if tnum_field not in ('', '-') else i))

        if is_baseline:
            t_b = ms_now(); black_cross.draw(); win.flip()
            lb = ms_now() - t_b
            base_ms = int(round(float(baselinetime) * 1000.0))
            wait_ms(max(0, base_ms - lb))
            w(xw, [session_id, block_no, '-', 'baseline', '-', t_b, ms_now() - t_b, '-', '-', '-', '-'])
            continue

        # ======== EXPPARITY CORE: beep -> isi -> beep -> ... -> target beep -> feedback ========
        isis = parse_isis(tr)                 # IOIs onset->onset (ms)
        std_ms = (isis[0] if len(isis) > 0 else None)

        # Entrainers: one beep per isi_k, and each isi_k is logged immediately after its wait.
        for k, ioims in enumerate(isis, start=1):
            # -------- beep --------
            t_beep = ms_now()
            st.pulse_audio()
            _play_start(audiowav_medium)

            gray_cross.draw()
            win.flip()

            wait_ms(max(0, STIM_MS - (ms_now() - t_beep)))  # compensate for flip-related latency

            audio_dur = ms_now() - t_beep

            w(xw, [session_id, block_no, tnum, trial_label, 'beep_440hz',
                t_beep, audio_dur, '-', '-', '-', '-'])

            # -------- isi_k (Expyriment: interval - audio_duration) --------
            t_interval = ms_now()
            wait_ms(max(0.0, float(ioims) - float(audio_dur)))
            interval_clock_dur = ms_now() - t_interval
            realized_ioi = ms_now() - t_beep  # onset->onset to next beep (should ~= ioims)

            w(xw, [session_id, block_no, tnum, trial_label, f'interval_{k}',
                   t_interval, interval_clock_dur, float(ioims), realized_ioi, '-', '-'])

        # -------- target beep --------
        t_tbeep = ms_now()
        st.pulse_audio()
        _play_start(audiowav_medium)

        gray_cross.draw()
        win.flip()

        wait_ms(max(0, STIM_MS - (ms_now() - t_tbeep)))  # compensate for flip-related latency

        target_audio_dur = ms_now() - t_tbeep
        t_toff = ms_now()  # target offset moment (measured)

        w(xw, [session_id, block_no, tnum, trial_label, 'beep_440hz',
            t_tbeep, target_audio_dur, '-', '-', '-', '-'])

        # ======== FEEDBACK (match PTB sister / siblings): starts at target OFFSET ========
        FB_MS = 2000

        fb_on_ms = float(t_toff)
        fb_deadline = fb_on_ms + float(FB_MS)

        _KEYBOARD.clearEvents()
        rt0_ms = ms_now()
        _KEYBOARD.clock.reset()  # RT from feedback onset

        black_cross.draw()
        win.flip()

        key = None
        rt = None  # ms
        end_ms = None
        response_onset_ms = None

        while ms_now() < fb_deadline and key is None:
            kill_check()
            evs = _KEYBOARD.getKeys([option1], waitRelease=False, clear=False)
            if evs:
                e = min(evs, key=lambda x: x.rt if x.rt is not None else float('inf'))
                if e.rt is not None:
                    key = e.name
                    rt = int(round(e.rt * 1000.0))          # ms since feedback onset

                    # ST: pulse exactly when RT is defined
                    st.pulse_audio()

                    # Play reproduction beep immediately
                    _play_start(audiowav_medium)

                    # response onset is the thing we log as the end of the produced interval
                    response_onset_ms = rt0_ms + float(rt)

                    # keep actual behaviour unchanged: let the reproduction beep finish
                    end_ms = response_onset_ms + float(STIM_MS)
                    break
            psychopy.core.wait(0.002)

        if key is None:
            # Timeout ends exactly at 2000 ms
            end_ms = fb_deadline
            response_onset_ms = fb_deadline

        now_ms = ms_now()
        if now_ms < end_ms:
            wait_ms(end_ms - now_ms)

        # supervisor's requested logging:
        # duration = target offset -> response onset
        # realized = target onset -> response onset
        feedback_duration = float(response_onset_ms - fb_on_ms)   # hit: rt, miss: 2000
        fb_realized = float(response_onset_ms - t_tbeep)          # hit: target_audio_dur + rt

        w(xw, [
            session_id, block_no, tnum, trial_label, 'feedback',
            fb_on_ms, feedback_duration,
            FB_MS + STIM_MS, fb_realized,
            (rt if rt is not None else '-'), key or '-'
        ])
        # ----- scoring collect (Expyriment parity) -----
        # expyriment: rts.append(target_audio_duration + rt)
        if rt is None or std_ms is None:
            _prod_rts.append(None)
            _prod_stds.append(std_ms)
        else:
            _prod_rts.append(float(rt))
            _prod_stds.append(std_ms)

        # ======== ITI + pre-cue ========
        t_wb = ms_now(); black_cross.draw(); win.flip()
        lwb = ms_now() - t_wb
        last = (i == N)
        if not last:
            wait_ms(max(0, WITHIN_BLOCK_MS - lwb - CUE_MS))
            t_c = ms_now(); gray_cross.draw(); win.flip()
            lc = ms_now() - t_c
            wait_ms(max(0, CUE_MS - lc))
        else:
            wait_ms(max(0, WITHIN_BLOCK_MS - lwb))

        w(xw, [session_id, block_no, '-', 'fixcross', '-', t_wb, ms_now() - t_wb, '-', '-', '-', '-'])

    # ===== run score (production) =====

    score_pct, score_list = production_rating_py(
        _prod_rts,
        _prod_stds,
        add_stim_duration=True
    )
    msg = f"Your score is {score_pct:.2f}%."
    psychopy.event.clearEvents(eventType='keyboard')
    psychopy.visual.TextStim(win, text=msg, color="yellow", height=0.07, pos=(0,0)).draw()
    win.flip()
    psychopy.core.wait(2.0)

    t_sum = ms_now()
    w(xw, [session_id, block_no, '-', 'score', '-', t_sum, 0, '-', '-', '-', f"{score_pct:.2f}%"])

    try:
        st.close()
    except Exception:
        pass

    win.close(); xf.close()
    print('Using:', cond_file)
    print('Wrote log:', csv_path)

except SystemExit:
    try: xf.close()
    except Exception: pass
    try: win.close()
    except Exception: pass
    try: st.close()
    except Exception: pass
    print('Run aborted by user.')
    sys.exit(0)
