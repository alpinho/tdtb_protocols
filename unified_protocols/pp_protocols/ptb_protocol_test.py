# ptb_protocol_test.py

#dummy protocol for testing initialization, connectivity, and
#runs one trial from ntfd with a log output


#quickly run all visual and audio elements

#run trial

#exports

#imports

import os, csv, re, sys, datetime
from pathlib import Path
from typing import List

from psychopy import core, visual, gui, event
from psychopy.hardware import keyboard

from one_stim_tracker_setup import connect_stimtracker

try:
    import psychtoolbox as ptb
except Exception as e:
    raise RuntimeError(
        "PTB scheduling requested but psychtoolbox (ptb) is not available. "
        "Install psychtoolbox + use PTB audio backend."
    ) from e

from stimuli_setup import (
    win, purple_cross, black_cross, gray_cross,
    text, higher, lower,
    text2, longer, shorter,
    text3, triangletext, circletext,
    rect, triangle, circle,
    get_medium_beep, audiowav_medium_pool,
    beep_220hz, beep_880hz,
    startkey, option1, option2,
    stim_duration, intertrial, onsettime, baselinetime, kill_check, hide_cursor
)

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
os.makedirs("data", exist_ok=True)


ms_now = lambda: float(core.getTime() * 1000.0)
_KEYBOARD = keyboard.Keyboard()

def stim_test():
    stim_sec = 0.15
    
    "start display"
    visual.TextStim(
        win, text="Testing Stimuli", color="blue",
        height=0.08, pos=(0, 0)
    ).draw()
    win.flip()
    core.wait(0.8)

    purple_cross.draw(); win.flip(); core.wait(stim_sec)
    black_cross.draw();  win.flip(); core.wait(stim_sec)
    gray_cross.draw();   win.flip(); core.wait(stim_sec)

    try:
        for s in audiowav_medium_pool:
            s.stop()
        beep_220hz.stop()
        beep_880hz.stop()
    except Exception:
        pass

    gray_cross.draw(); win.flip()
    get_medium_beep().play()
    core.wait(stim_sec)

    gray_cross.draw(); win.flip()
    beep_220hz.play()
    core.wait(stim_sec)

    gray_cross.draw(); win.flip()
    beep_880hz.play()
    core.wait(stim_sec)

    text.draw();  higher.draw(); lower.draw(); win.flip();   core.wait(stim_sec)
    text2.draw(); longer.draw(); shorter.draw(); win.flip(); core.wait(stim_sec)
    text3.draw(); triangletext.draw(); circletext.draw(); win.flip(); core.wait(stim_sec)

    rect.draw();     win.flip(); core.wait(stim_sec)
    triangle.draw(); win.flip(); core.wait(stim_sec)
    circle.draw();   win.flip(); core.wait(stim_sec)

def fb_test(window_length_ms = 2000):

    visual.TextStim(
        win, text="Now, test the feedback keys (o - p)", color="blue",
        height=0.08, pos=(0, 0)
    ).draw()


    win.callOnFlip(_KEYBOARD.clearEvents)
    win.callOnFlip(_KEYBOARD.clock.reset)
    t0_s = win.flip()
    deadline_ms = (t0_s * 1000.0) + window_length_ms

    while ms_now() < deadline_ms:
        kill_check()
        evs = _KEYBOARD.getKeys([option1, option2], waitRelease=False, clear=True)
        for ev in evs:
            if ev.name == option1:
                try: beep_220hz.stop()
                except: pass
                beep_880hz.play()
                st.pulse_audio()
            elif ev.name == option2:
                try: beep_880hz.stop()
                except: pass
                beep_220hz.play()
                st.pulse_audio()
        
        core.wait(0.002)
    
    #COMPLETION MESSAGE
    visual.TextStim(
        win, text="Beginning Experiment", color="blue",
        height=0.08, pos=(0, 0)
    ).draw(); win.flip()
    core.wait(0.8)


#start menu
expInfo = {"StimTracker? (y/n)":"n", "subject_id":"05","session_number":"01","run_number":"1"}
dlg = gui.DlgFromDict(expInfo, title='Dummy Protocol (NTFD)')
if not dlg.OK: core.quit()



use_hw = expInfo["StimTracker? (y/n)"].strip().lower() == "y"
st = connect_stimtracker(enabled=use_hw, dummy=not use_hw, verbose=True)


try:
    hide_cursor()
    
    #test stimuli and feedback
    stim_test()
    fb_test(window_length_ms = 1000000)

    # START EXPERIMENT
    _KEYBOARD.clearEvents()
    purple_cross.draw(); win.flip()

    #start loop
    while True:
        kill_check()
        if _KEYBOARD.getKeys([startkey], waitRelease=False, clear=True): break
        core.wait(0.01)


    try:
        st.close()
    except Exception:
        pass
    win.close()
    core.quit()

except SystemExit:
    try: win.close()
    except: pass
    try:
        st.close()
    except Exception:
        pass
    core.quit()
