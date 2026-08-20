# one_st_visual_NTFD.py — Visual No-Temporal

import os, csv, re, sys, datetime
from pathlib import Path

import psychopy.visual, psychopy.event, psychopy.core
from psychopy import gui
from psychopy.hardware import keyboard

from one_stim_tracker_setup import connect_stimtracker

from utilities import notemporal_rating_py, load_inputs

from stimuli_setup import (
    win, purple_cross, black_cross, gray_cross,
    startkey, option1, option2,
    stim_duration, intertrial, onsettime, baselinetime,
    hide_cursor,
    rect, triangle, circle
)

# ---------- setup ----------
HERE = Path(__file__).resolve().parent
os.chdir(HERE)
os.makedirs("data", exist_ok=True)

try:
    win._setVsync(1)
except Exception:
    pass

# ---------- ID normalizers ----------
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

def _run_idx(p: Path) -> int:
    m = re.search(r"run[-_]?(\d+)", p.stem, re.I)
    return int(m.group(1)) if m else 9999

def load_notemp_visual_strict(subject_id, session_id, run_number, session_type='behavioral'):
    # 'training' inputs ignore subject and session; 'behavioral' inputs
    # are specific to subject, session and run.
    return load_inputs('visual', 'notemporal', run_number, session_type,
                       subject_id, session_id)

# ---------- helpers ----------
def resolve_target_shape(trial) -> str:
    s = str(trial.get('target') or trial.get('target_shape') or trial.get('comparison') or '').strip().lower()
    if s.startswith('tri') or s == 'triangle':
        return 'triangle'
    if s.startswith('cir') or s == 'circle':
        return 'circle'
    return 'triangle'

def isi_list_dynamic_ms(trial):
    items = []
    for k, v in trial.items():
        m = re.match(r'^\s*isi[_\-]?(\d+)\s*$', str(k).strip().lower())
        if m and str(v).strip():
            try:
                val = float(v)
                if val < 0:
                    val = 0.0
            except:
                val = 0.0
            items.append((int(m.group(1)), val))
    items.sort(key=lambda x: x[0])
    return [val for _, val in items]

# ---------- timings ----------
STIM_MS = int(round(float(stim_duration) * 1000.0))
WAIT_MS = int(round(float(onsettime) * 1000.0))
INTRO_MS = 1250
CUE_MS  = int(round(0.50 * 1000.0))
ITI_MS  = int(round(float(intertrial) * 1000.0))
WITHIN_BLOCK_MS = ITI_MS + CUE_MS
TTL_KEY = startkey

# ---------- logging schema ----------
LLOG = [
    "subject_id","session_number","run_number","trial_number","trial_id","condition",
    "onset","duration","theoretical_isi/feedback","real_isi/feedback","rt","key"
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

# ---------- row writing ----------
def write_row(base_list):
    b = [subject_id] + list(base_list)
    while len(b) < 12:
        b.append('-')

    def to_int_or_dash(x):
        try:
            return int(round(float(x)))
        except Exception:
            return '-'

    b[6] = to_int_or_dash(b[6])
    b[7] = to_int_or_dash(b[7])
    b[8] = to_int_or_dash(b[8])
    b[9] = to_int_or_dash(b[9])
    if b[10] != '-':
        b[10] = to_int_or_dash(b[10])

    xw.writerow(b)


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
            "Usage: python one_st_visual_NTFD.py [pc_type] "
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
    dlg = gui.DlgFromDict(expInfo, title='Visual Notemporal')
    if not dlg.OK:
        psychopy.core.quit()

hide_cursor()

use_hw = _stimtracker_enabled(expInfo['StimTracker? (y/n)'])
st = connect_stimtracker(enabled=use_hw, dummy=not use_hw, verbose=True)

# Make sure nothing is stuck on autoDraw (common cause of "stopped flipping properly")
for stim in (rect, triangle, circle, purple_cross, black_cross, gray_cross):
    try:
        stim.autoDraw = False
    except Exception:
        pass

cond_file, conditions = load_notemp_visual_strict(expInfo["subject_id"], expInfo["session_number"], expInfo["run_number"], expInfo['session_type'])

# ---------- logger ----------
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
MODALITY = "visual"
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
    xf.write(f"#e Task: st visual NTFD\n")
    xf.write(f"#e conditions: {cond_file.name}\n")
    xf.write("#--SUBJECT INFO\n")
    xf.write(f"#s id: {int(expInfo['subject_id'])}\n")
    xw.writerow(LLOG)

# ---------- run ----------
subject_id = int(expInfo["subject_id"])
session_id = int(expInfo["session_number"])
block_no = int(expInfo["run_number"])

_score_targets, _score_rts, _score_keys = [], [], []

try:
    show_run_intro("Visual NTFD", block_no)

    # START: TTL -> WAIT -> CUE
    psychopy.event.clearEvents(eventType='keyboard')
    purple_cross.draw()
    win.flip()
    while True:
        kill_check()
        if psychopy.event.getKeys(keyList=[TTL_KEY]):
            break
        psychopy.core.wait(0.01)
    t_ttl_ms = ms_now()

    black_cross.draw()
    win.flip()
    load2_ms = ms_now() - t_ttl_ms
    wait_ms(max(0, WAIT_MS - load2_ms - CUE_MS))

    t_fix3_ms = ms_now()
    gray_cross.draw()
    win.flip()
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
            black_cross.draw()
            win.flip()
            base_ms = int(round(float(baselinetime) * 1000.0))
            wait_ms(base_ms)
            write_row([session_id, block_no, '-', 'baseline', '-', t_base_ms, base_ms, '-', '-', '-', '-'])

            if not last:
                t_cue_ms = ms_now()
                gray_cross.draw()
                win.flip()
                load3_ms = ms_now() - t_cue_ms
                wait_ms(max(0, CUE_MS - load3_ms))
            continue

        isi_ms_list = isi_list_dynamic_ms(trial)

        # ---------- ENTRAINERS ----------
        for j, isi_ms in enumerate(isi_ms_list, 1):
            # ONSET flip (rect)
            _on = [None]
            win.callOnFlip(lambda: _on.__setitem__(0, ms_now()))
            try:
                win.callOnFlip(st.pulse_visual)
            except Exception:
                pass
            rect.draw()
            win.flip()
            t_on_ms = _on[0]

            write_row([session_id, block_no, tnum, trial_label, 'rectangle',
                       t_on_ms, STIM_MS, '-', '-', '-', '-'])

            # OFFSET flip (black)
            wait_ms(STIM_MS)
            _off = [None]
            win.callOnFlip(lambda: _off.__setitem__(0, ms_now()))
            black_cross.draw()
            win.flip()
            t_gap_ms = _off[0]

            # ISI meaning: onset-to-onset (IOI). duration here is the gap (IOI - STIM_MS)
            th_ms = int(round(float(isi_ms)))
            gap_ms = max(0, th_ms - STIM_MS)

            # realized IOI = next onset - this onset (we can only know after waiting)
            wait_ms(max(0, float(isi_ms) - STIM_MS))
            realized_o2o = ms_now() - t_on_ms

            write_row([session_id, block_no, tnum, trial_label, f"interval_{j}",
                       t_gap_ms, gap_ms, th_ms, realized_o2o, '-', '-'])

        # ---------- TARGET ----------
        label = resolve_target_shape(trial)
        target_stim = triangle if label == 'triangle' else circle

        _tar = [None]
        win.callOnFlip(lambda: _tar.__setitem__(0, ms_now()))
        try:
            win.callOnFlip(st.pulse_visual)
        except Exception:
            pass
        target_stim.draw()
        win.flip()
        t_tar_ms = _tar[0]

        write_row([session_id, block_no, tnum, trial_label, label,
                   t_tar_ms, STIM_MS, '-', '-', '-', '-'])

        # target OFFSET flip (black)
        wait_ms(STIM_MS)
        _toff = [None]
        win.callOnFlip(lambda: _toff.__setitem__(0, ms_now()))
        black_cross.draw()
        win.flip()
        t_tar_off_ms = _toff[0]

        # ---------- FEEDBACK WINDOW ----------
        FB_MS = 2000

        # Feedback is anchored to target offset. Reset the RT clock before
        # presenting the response screen, matching PP audio.
        t_fb_ms = float(t_tar_off_ms)
        _KEYBOARD.clearEvents()
        rt0_ms = ms_now()
        _KEYBOARD.clock.reset()

        _fb = [None]
        win.callOnFlip(lambda: _fb.__setitem__(0, ms_now()))
        gray_cross.draw()
        win.flip()
        deadline_ms = t_fb_ms + FB_MS

        key = None
        rt_ms = None
        response_onset_ms = None

        while ms_now() < deadline_ms and key is None:
            kill_check()
            evs = _KEYBOARD.getKeys([option1, option2], waitRelease=False, clear=False)
            if evs:
                e = min(evs, key=lambda x: x.rt if x.rt is not None else float('inf'))
                if e.rt is not None:
                    key = e.name

                    try:
                        st.pulse_visual()  # pulse at RT-defining key
                    except Exception:
                        pass

                    which = 'circle' if key == option1 else ('triangle' if key == option2 else None)
                    fb_shape = circle if which == 'circle' else (triangle if which == 'triangle' else None)

                    _resp = [None]
                    win.callOnFlip(lambda: _resp.__setitem__(0, ms_now()))
                    try:
                        win.callOnFlip(st.pulse_visual)  # pulse on feedback-shape onset
                    except Exception:
                        pass

                    if fb_shape is not None:
                        fb_shape.draw()
                    else:
                        black_cross.draw()
                    win.flip()
                    fb_shape_on = _resp[0]

                    rt_ms = float(e.rt) * 1000.0
                    response_onset_ms = rt0_ms + rt_ms
                    
                    wait_ms(STIM_MS)
                    black_cross.draw()
                    win.flip()
                    break

            psychopy.core.wait(0.002)

        if key is None:
            response_onset_ms = deadline_ms
            end_ms = deadline_ms
            now_ms = ms_now()
            if now_ms < end_ms:
                wait_ms(end_ms - now_ms)
        else:
            end_ms = response_onset_ms + STIM_MS
            now_ms = ms_now()
            if now_ms < end_ms:
                wait_ms(end_ms - now_ms)

        fb_dur_ms = response_onset_ms - t_fb_ms
        fb_realized_ms = response_onset_ms - t_tar_ms

        write_row([session_id, block_no, tnum, trial_label, 'feedback',
                   t_fb_ms, fb_dur_ms, STIM_MS + FB_MS, fb_realized_ms,
                   (rt_ms if rt_ms is not None else '-'), (key if key is not None else '-')])

        _score_targets.append(label)
        _score_rts.append(fb_dur_ms if rt_ms is not None else None)
        _score_keys.append(key if key is not None else None)

        # ---------- ITI + optional pre-cue ----------
        t_wb_ms = ms_now()
        black_cross.draw()
        win.flip()
        load2_ms = ms_now() - t_wb_ms

        if not last:
            if next_is_baseline:
                wait_ms(max(0, WITHIN_BLOCK_MS - load2_ms))
            else:
                wait_ms(max(0, WITHIN_BLOCK_MS - load2_ms - CUE_MS))
                t_cue_ms = ms_now()
                gray_cross.draw()
                win.flip()
                load3_ms = ms_now() - t_cue_ms
                wait_ms(max(0, CUE_MS - load3_ms))
        else:
            wait_ms(max(0, WITHIN_BLOCK_MS - load2_ms))

        write_row([session_id, block_no, '-', 'fixcross', '-',
                   t_wb_ms, ms_now()-t_wb_ms, '-', '-', '-', '-'])

    score_pct, _ = notemporal_rating_py(
        _score_targets,
        _score_rts,
        _score_keys,
        option1_targets={"circle"},
        option2_targets={"triangle"}
    )

    msg = f"Your score is {score_pct:.2f}%."
    psychopy.event.clearEvents(eventType='keyboard')
    psychopy.visual.TextStim(win, text=msg, color="yellow", height=0.07, pos=(0,0)).draw()
    win.flip()
    wait_ms(2000.0)

    t_sum_ms = ms_now()
    write_row([session_id, block_no, '-', 'score', '-', t_sum_ms, 0, '-', '-', '-', f"{score_pct:.2f}%"])

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
    except:
        pass
    try:
        win.close()
    except:
        pass
    try:
        st.close()
    except:
        pass
    print("Run aborted by user.")
    sys.exit(0)
