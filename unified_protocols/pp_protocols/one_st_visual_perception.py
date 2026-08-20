# one_st_visual_perception.py — Visual Perception 

import os, csv, re, sys, datetime
from pathlib import Path
from typing import List

import psychopy.visual, psychopy.event, psychopy.core
from psychopy import gui
from psychopy.hardware import keyboard

from one_stim_tracker_setup import connect_stimtracker  # ST adapter

from utilities import perception_rating_py, load_inputs

# ===== stimuli + constants from your setup =====
from stimuli_setup import (
    win, purple_cross, black_cross, gray_cross,
    startkey, option1, option2,
    stim_duration, intertrial, onsettime, baselinetime,
    hide_cursor,
    rect
)

# Optional prompts (question screen elements) from your setup
try:
    from stimuli_setup import text2, longer, shorter
    _HAS_LS = True
except Exception:
    _HAS_LS = False
    try:
        from stimuli_setup import text2 as _maybe_text2
    except Exception:
        _maybe_text2 = None

# ---------- setup ----------
HERE = Path(__file__).resolve().parent
os.chdir(HERE)
OS_DATA = HERE / 'data'
OS_DATA.mkdir(exist_ok=True)

# Force vsync = 1 (Expyriment-like blocking on vertical retrace)
try:
    win._setVsync(1)
except Exception:
    pass

# ---------- inputs base resolver ----------
BASE_IN = HERE.parent / "inputs" / "behavioral-sessions_inputs"

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

def load_perception_visual(subject_id, session_id, run_number, session_type='behavioral'):
    # 'training' inputs ignore subject and session; 'behavioral' inputs
    # are specific to subject, session and run.
    return load_inputs('visual', 'perception', run_number, session_type,
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
    return [ms for _, ms in cands]  # IOIs onset->onset (ms)

# ---------- timings (ms) ----------
WAIT_MS = int(round(float(onsettime) * 1000.0))
INTRO_MS = 1250
CUE_MS  = 500
ITI_MS  = int(round(float(intertrial) * 1000.0))
WITHIN_BLOCK_MS = ITI_MS + CUE_MS
TTL_KEY = startkey

STIM_MS = int(round(float(stim_duration) * 1000.0))

# ---------- logging schema ----------
LLOG = [
    'subject_id','session_number','run_number','trial_number','trial_id','condition',
    'onset','duration','theoretical_isi/feedback','real_isi/feedback','rt','key'
]

# ---------- time + quit + waits ----------
ms_now = lambda: float(psychopy.core.getTime()*1000.0)
_KEYBOARD = keyboard.Keyboard()

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

def wait_ms(ms_total: float):
    end = ms_now() + float(ms_total)
    while True:
        now = ms_now(); rem = end - now
        if rem <= 4.0: break
        kill_check(); psychopy.core.wait(0.002)
    while True:
        now = ms_now(); rem = end - now
        if rem <= 0.4: break
        kill_check(); psychopy.core.wait(0.001)
    while ms_now() < end:
        kill_check()

def show_run_intro(task_name, run_number):
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

# ---------- row writer (ints for ms fields) ----------
def w(xw, row):
    out = [subject_id] + list(row)
    while len(out) < 12:
        out.append('-')

    def to_int_or_dash(x):
        try:
            return int(round(float(x)))
        except Exception:
            return '-'

    out[6] = to_int_or_dash(out[6])  # onset
    out[7] = to_int_or_dash(out[7])  # duration
    out[8] = to_int_or_dash(out[8])  # theoretical
    out[9] = to_int_or_dash(out[9])  # realized
    out[10] = to_int_or_dash(out[10]) if out[10] != '-' else '-'  # rt

    xw.writerow(out)

# ---------- scoring helpers ----------
def _extract_std_cmp_ms(tr: dict):
    def _get_first(tr_, keys):
        for k in keys:
            if k in tr_ and str(tr_[k]).strip() != "":
                try:
                    return float(tr_[k])
                except Exception:
                    pass
        return None
    std = _get_first(tr, ["standard_time","std_time","std_ms","isi_std","std","standard"])
    cmp_ = _get_first(tr, ["perception_time","cmp_time","cmp_ms","isi_cmp","cmp","comparison"])
    if std is None:
        std = _get_first(tr, ["isi1","isi_1"])
    if cmp_ is None:
        cmp_ = _get_first(tr, ["isi5","isi_5","comparison_isi"])
    return std, cmp_

# ---------- prompt drawing helper (NEW) ----------
def draw_prompt():
    if _HAS_LS:
        try:
            text2.draw(); longer.draw(); shorter.draw()
            return
        except Exception:
            pass
    if _maybe_text2 is not None:
        _maybe_text2.draw()
    else:
        gray_cross.draw()

# ---------- UI ----------
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
            "Usage: python one_st_visual_perception.py [pc_type] "
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
    expInfo = {'StimTracker? (y/n)': 'n', 'subject_id':'05','session_number':'01','run_number':'1','session_type':'behavioral'}
    dlg = gui.DlgFromDict(expInfo, title='Visual Perception — strict TSV')
    if not dlg.OK:
        psychopy.core.quit()
hide_cursor()

# StimTracker connect (dummy-safe)
use_hw = _stimtracker_enabled(expInfo['StimTracker? (y/n)'])
st = connect_stimtracker(enabled=use_hw, dummy=not use_hw, verbose=True)

cond_file, conditions = load_perception_visual(expInfo['subject_id'], expInfo['session_number'], expInfo['run_number'], expInfo['session_type'])

# ---------- logger ----------
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
MODALITY = "visual"
TASK = "perception"
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
    xf.write(f"#e Task: st visual PERCEPTION\n")
    xf.write(f"#e conditions: {cond_file.name}\n")
    xf.write('#--SUBJECT INFO\n')
    xf.write(f"#s id: {int(expInfo['subject_id'])}\n")
    xw.writerow(LLOG)

# ---------- RUN ----------
subject_id = int(expInfo['subject_id'])
session_id = int(expInfo['session_number'])
block_no = int(expInfo['run_number'])

_p_keys, _p_stds, _p_cmps = [], [], []

try:
    show_run_intro("Visual Perception", block_no)

    # ===== TTL -> wait(onsettime − cue) -> CUE =====
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
    wait_ms(max(0.0, WAIT_MS - load2_ms - CUE_MS))

    t_fix3 = ms_now()
    gray_cross.draw(); win.flip()
    load3_ms = ms_now() - t_fix3
    wait_ms(max(0.0, CUE_MS - load3_ms))

    w(xw, [session_id, block_no, '-', 'ttl', '-', t_ttl_ms, ms_now()-t_ttl_ms, '-', '-', '-', '-'])

    N = len(conditions)
    for i, tr in enumerate(conditions, start=1):
        kill_check()
        psychopy.event.clearEvents(eventType='keyboard')

        trial_label = str(tr.get('trial_id', f't{i}'))
        is_baseline = trial_label.strip().lower() == 'baseline'
        tnum_field = str(tr.get('trial_number','')).strip()
        tnum = ('-' if is_baseline else (int(tnum_field) if tnum_field not in ('','-') else i))
        last = (i == N)

        if is_baseline:
            t_b = ms_now()
            black_cross.draw(); win.flip()
            base_ms = int(round(float(baselinetime)*1000.0))
            wait_ms(max(0.0, base_ms - (ms_now() - t_b)))
            w(xw, [session_id, block_no, '-', 'baseline', '-', t_b, ms_now()-t_b, '-', '-', '-', '-'])
            continue

        # ===== FLASH TRAIN (flip-stamped; parity semantics) =====
        isis = parse_isis(tr)  # IOIs onset->onset (ms)

        prev_on_ms = None
        last_off_ms = None
        last_flash_dur = None
        last_on_ms = None

        # First rect ON
        _on = [None]
        win.callOnFlip(_on.__setitem__, 0, ms_now())
        try:
            win.callOnFlip(st.pulse_visual)
        except Exception:
            pass
        rect.draw(); win.flip()
        t_on_ms = float(_on[0])

        # First rect OFF (black cross)
        wait_ms(max(0.0, float(STIM_MS)))
        _off = [None]
        win.callOnFlip(_off.__setitem__, 0, ms_now())
        black_cross.draw(); win.flip()
        t_off_ms = float(_off[0])

        flash_dur = float(t_off_ms - t_on_ms)
        w(xw, [session_id, block_no, tnum, trial_label, 'rectangle', t_on_ms, flash_dur, '-', '-', '-', '-'])

        prev_on_ms = t_on_ms
        last_on_ms = t_on_ms
        last_off_ms = t_off_ms
        last_flash_dur = flash_dur

        # Feedback anchors (will be set on the FINAL rect OFF flip)
        t_fb_ms = None

        for k, ioims in enumerate(isis, start=1):
            gap_wait = max(0.0, float(ioims) - float(last_flash_dur))
            isi_onset = float(last_off_ms)

            wait_ms(gap_wait)

            # Next rect ON
            _nxt = [None]
            win.callOnFlip(_nxt.__setitem__, 0, ms_now())
            try:
                win.callOnFlip(st.pulse_visual)
            except Exception:
                pass
            rect.draw(); win.flip()
            t_next_on = float(_nxt[0])

            realized_on2on = float(t_next_on - prev_on_ms)
            gap_dur = float(t_next_on - isi_onset)

            w(xw, [session_id, block_no, tnum, trial_label, f'interval_{k}',
                   isi_onset, gap_dur, float(ioims), realized_on2on, '-', '-'])

            # rect OFF: if this is the FINAL rect in the train, combine OFF with prompt flip + RT reset
            wait_ms(max(0.0, float(STIM_MS)))

            is_last_rect = (k == len(isis))  # last rect corresponds to the last IOI-triggered onset

            if is_last_rect:
                _fbStart = [None]
                win.callOnFlip(_fbStart.__setitem__, 0, ms_now())
                _KEYBOARD.clearEvents()
                rt0_ms = ms_now()
                _KEYBOARD.clock.reset()
                draw_prompt()
                win.flip()

                t_next_off = float(_fbStart[0])
                t_fb_ms = float(_fbStart[0])   # feedback onset == final rect OFF flip (same flip)
            else:
                _off2 = [None]
                win.callOnFlip(_off2.__setitem__, 0, ms_now())
                black_cross.draw(); win.flip()
                t_next_off = float(_off2[0])

            flash_dur2 = float(t_next_off - t_next_on)
            w(xw, [session_id, block_no, tnum, trial_label, 'rectangle',
                   t_next_on, flash_dur2, '-', '-', '-', '-'])

            prev_on_ms = t_next_on
            last_on_ms = t_next_on
            last_off_ms = t_next_off
            last_flash_dur = flash_dur2

        # ===== FEEDBACK WINDOW (terminate at response like PTB) =====
        FB_MS = 2000.0
        FIXED_FB_THEO_MS = float(int(round(FB_MS + float(STIM_MS))))  # 2080 when STIM_MS=80

        # If there were no isis (edge case), we didn't set t_fb_ms in the loop; fall back to current behavior
        if t_fb_ms is None:
            t_fb_ms = float(last_off_ms)
            _KEYBOARD.clearEvents()
            rt0_ms = ms_now()
            _KEYBOARD.clock.reset()
            draw_prompt()
            _fbStart2 = [None]
            win.callOnFlip(_fbStart2.__setitem__, 0, ms_now())
            win.flip()
            t_fb_ms = float(_fbStart2[0])

        t_dead = float(t_fb_ms + FB_MS)

        key = None
        rt = None  # ms, from PP-audio-style pre-presentation clock reset
        response_onset_ms = None

        while ms_now() < t_dead and key is None:
            kill_check()
            evs = _KEYBOARD.getKeys([option1, option2], waitRelease=False, clear=False)
            if evs:
                e = min(evs, key=lambda x: x.rt if x.rt is not None else float('inf'))
                if e.rt is not None:
                    key = e.name
                    rt = int(round(e.rt * 1000.0))

                    # Optional: pulse when RT is defined
                    try:
                        st.pulse_visual()
                    except Exception:
                        pass
                    break
            psychopy.core.wait(0.002)

        # End-time rule:
        # - timeout: end at t_dead
        # - response: end after showing feedback for STIM_MS
        if rt is None:
            response_onset_ms = float(t_dead)
            end_ms = float(t_dead)
            now_ms = ms_now()
            if now_ms < end_ms:
                wait_ms(end_ms - now_ms)
        else:
            response_onset_ms = float(rt0_ms + rt)
            end_ms = float(response_onset_ms + float(STIM_MS))
            now_ms = ms_now()
            if now_ms < end_ms:
                wait_ms(end_ms - now_ms)

        fb_duration = float(response_onset_ms - t_fb_ms)
        fb_realized = float(response_onset_ms - float(last_on_ms))

        w(xw, [session_id, block_no, tnum, trial_label, 'feedback',
               t_fb_ms, fb_duration, FIXED_FB_THEO_MS, fb_realized,
               (rt if rt is not None else '-'), key or '-'])

        # ----- scoring collect -----
        std_ms, cmp_ms = _extract_std_cmp_ms(tr)
        _p_keys.append(key if key is not None else None)
        _p_stds.append(std_ms)
        _p_cmps.append(cmp_ms)

        # ===== ITI + pre-cue =====
        t_wb = ms_now()
        black_cross.draw(); win.flip()
        lwb = ms_now() - t_wb

        if not last:
            wait_ms(max(0.0, WITHIN_BLOCK_MS - lwb - CUE_MS))
            t_c = ms_now()
            gray_cross.draw(); win.flip()
            lc = ms_now() - t_c
            wait_ms(max(0.0, CUE_MS - lc))
        else:
            wait_ms(max(0.0, WITHIN_BLOCK_MS - lwb))

        w(xw, [session_id, block_no, '-', 'fixcross', '-', t_wb, ms_now()-t_wb, '-', '-', '-', '-'])

    # ===== run score (perception) =====
    score_pct, score_list = perception_rating_py(_p_keys, _p_stds, _p_cmps)
    
    msg = f"Your score is {score_pct:.2f}%."
    psychopy.event.clearEvents(eventType='keyboard')
    psychopy.visual.TextStim(win, text=msg, color="yellow", height=0.07, pos=(0,0)).draw()
    win.flip()
    wait_ms(2000.0)

    t_sum = ms_now()
    w(xw, [session_id, block_no, '-', 'score', '-', t_sum, 0.0, '-', '-', '-', f"{score_pct:.2f}%"])

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
