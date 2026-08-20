# -*- coding: utf-8 -*-
#
# Explicit-instruction variants of the visual protocols.
#
# Implemented: Visual Production, Visual Perception, Visual No-Temporal
# Feature Discrimination (NTFD). Training sessions only.
#
# Difference from the standard tasks (visual_protocols.py):
#   For trials labelled "beat*" each long interval (an isi equal to an
#   integer multiple n >= 2 of the on-beat unit isi_1) is split into n
#   sub-intervals of length isi_1. Every internal subdivision is made
#   visible with a SMALLER rectangle, centred on the screen like the main
#   flash (the visual analogue of the softer beep in the auditory tasks).
#   All inserted flashes and sub-intervals are written to the .xpd log.
#
#   Base unit is isi_1 (= isi_3 = T), NOT min(isi): in Perception the probe
#   isi_5 can be shorter than T. The split is applied only when the interval
#   is an exact integer multiple of isi_1, so the varying probe is left
#   intact, and the NTFD target shape (outside the interval loop) is
#   untouched.
#
#   Refresh rate: like the main flash, the small rectangle is shown with
#   .present(), which flips the buffer on the next vertical retrace, so each
#   inserted flash starts on a refresh tick. The isi values and stim_duration
#   are multiples of the frame period (16/17 ms at ~60 Hz), so the waits end
#   on a refresh boundary and the following flash is not delayed by a frame.
#
# Author: Ana Luisa Pinho  (explicit variant)

import numpy as np

from expyriment import design, control, misc, stimuli

from confparser import load_config
from utils import (_load_inputs, _launch_sess, _launch_run, fixcrosses,
                   visual_stim, panel_stim, production_rating,
                   perception_rating, notemporal_rating, _display_score_run,
                   _txt_message, _next_run, wait, baseline_bt)
from visual_protocols import _visual_design


# %%
# ===================== EXPLICIT-VARIANT CONSTANTS =====================
# Key (in the PC spec .ini, e.g. pc1.ini/pc2.ini) holding the (w, h) size
# of the smaller rectangle used for the inserted subdivision flashes.
SMALL_RECT_SIZE_KEY = "small_rectangle_size"
# Label written in the .xpd "condition" column for the small-rectangle flash.
SMALL_RECT_CONDITION = "small_rectangle"
# Suffix used in the .xpd "condition" column for inserted sub-intervals.
SUBINTERVAL_TAG = "_sub"
# Label prefix identifying the trials acted upon.
TARGET_TRIAL_PREFIX = "beat"


def _isi_visual_explicit(setting, exp, t0, fixcross3, small_rect,
                         session_id, block_no, trial, trial_number,
                         var_names_key, i, interval, base_unit, is_beat,
                         t_flash, flash_duration):
    """Display and log one inter-stimulus interval (visual).

    For a beat trial, an interval that is an exact integer multiple
    n >= 2 of base_unit (the on-beat unit isi_1) is split into n
    sub-intervals of length base_unit, each internal subdivision marked by
    a smaller centred rectangle. Otherwise the interval is shown/logged
    unchanged. All events (small flashes and sub-intervals) are written to
    the log, and the time from the main flash onset to the next flash onset
    is preserved exactly (= interval).
    """
    tid = trial.get_factor(setting[var_names_key][1])
    label = setting[var_names_key][i + 1]
    if base_unit and is_beat and interval % base_unit == 0 \
            and interval // base_unit >= 2:
        n_sub = interval // base_unit
        for s in np.arange(1, n_sub + 1):
            if s == 1:
                # First sub-interval follows the main (big) flash.
                ref_onset = t_flash
                ref_flash_duration = flash_duration
            else:
                # ###### EXPLICIT SMALL RECTANGLE (refresh-aligned) ######
                t_small = t0.time
                # present() flips on the next vertical retrace: the small
                # flash starts on a refresh tick, like the main flash.
                small_rect.present()
                exp.clock.wait(setting["stim_duration"],
                               process_control_events=True)
                small_flash_duration = t0.time - t_small
                exp.data.add([session_id, block_no + 1, trial_number, tid,
                              SMALL_RECT_CONDITION, t_small,
                              small_flash_duration, '-', '-', '-', '-'])
                ref_onset = t_small
                ref_flash_duration = small_flash_duration
            # ############## SUB-INTERVAL (= base_unit) ##############
            t_sub = t0.time
            # Replace the rectangle by the fixation cross for the remainder.
            fixcross3.present()
            load_fixcross = t0.time - t_sub
            exp.clock.wait(base_unit - ref_flash_duration - load_fixcross,
                           process_control_events=True)
            sub_clock_duration = t0.time - t_sub
            exp.data.add([session_id, block_no + 1, trial_number, tid,
                          label + SUBINTERVAL_TAG + str(int(s)),
                          t_sub, sub_clock_duration, base_unit,
                          t0.time - ref_onset, '-', '-'])
    else:
        t_interval = t0.time
        fixcross3.present()
        load_fixcross = t0.time - t_interval
        exp.clock.wait(interval - flash_duration - load_fixcross,
                       process_control_events=True)
        interval_clock_duration = t0.time - t_interval
        exp.data.add([session_id, block_no + 1, trial_number, tid, label,
                      t_interval, interval_clock_duration, interval,
                      t0.time - t_flash, '-', '-'])


def visual_production_explicit(protocol_ini, spec, exp, kind='training', t0=None,
                      tlast=None, auto=None, score=None):
    # %%
    # ======================== LOAD CONFIG.INI FILE ====================
    setting = load_config(protocol_ini)

    # %%
    # ==================== DEFINE AND PRELOAD SOME STIMULI =============
    fixcross1, fixcross2, fixcross3 = fixcrosses(setting, spec)
    trial_rect, _, _ = visual_stim(setting, spec)
    small_rect = stimuli.Rectangle(
        tuple(list(map(int, spec[SMALL_RECT_SIZE_KEY]))),
        colour=tuple(list(map(int, setting["dark_gray"]))),
        position=(0, 0))
    text_end_run, text_end_session = _txt_message(setting, spec)

    fixcross1.preload()
    fixcross2.preload()
    fixcross3.preload()

    trial_rect.preload()
    small_rect.preload()

    text_end_run.preload()
    text_end_session.preload()

    # %%
    # ================================ RUN =============================
    # ==================================================================
    # Starts running the experiment:
    # (1) Present a screen asking for the subject no. (exp.subject) and
    #     wait for the RETURN key
    # (2) Create a data file (exp.data)
    # (3) Present the "Ready" screen
    # ==================================================================

    if auto is None:
        control.start(skip_ready_screen=True)
        session_id = _launch_sess(setting, spec, exp)
    else:
        if kind == 'behavioral':
            control.start(skip_ready_screen=True, subject_id=auto['subject'])
        elif kind == 'imaging':
            offset = len(exp.blocks)
        else:
            pass
        session_id = auto['session']

    subject_id = exp.subject

    # %%
    # ========================== LOAD INPUT FILES ======================
    inputs_filenames, n_block, last_run = \
        _load_inputs(setting, 'prod_dir', subject_id, session_id, 'visual')

    # %%
    # ====================== EXPERIMENTAL DESIGN =======================
    task_id = _visual_design(setting, n_block, exp, inputs_filenames,
                             "var_names_production")

    # %%
    # ============= WAITS FOR USER TO ENTER RUN NUMBER TO START ========
    if auto is None:
        start_block = _launch_run(setting, spec, n_block, exp)
    else:
        start_block = auto['nrun']
        # 2nd task of the same run, n_blocks in design are incremented
        if kind == 'imaging':
            start_block += offset
    start_block -= 1

    # ==================================================================
    # Run the protocol
    # ==================================================================
    stop = False
    # While "ESC" key is not pressed, ...
    while not stop:
        # Prepare arrays of score estimation for the entire session
        isi1_session = []
        rts_session = []
        # ... and for each run
        for b, block in enumerate(exp.blocks[start_block:]):
            # Prepare arrays of score estimation for each run
            isi1 = []
            rts = []
            # TTL or not?
            if kind == 'imaging' and auto is not None:
                block_no = b + start_block - offset
                # ############ Baseline between tasks ##################
                baseline_bt(t0, exp, setting, tlast, session_id)
            else:
                # Start at any run number
                block_no = b + start_block
                if kind != 'imaging':
                    # Creates the clock
                    t0 = misc.Clock()
                # Display TTL fixation cross that sets the beginning of
                # the experiment
                fixcross1.present()
                # Wait for TTL
                exp.keyboard.wait_char(setting["TTL"])
                t_ttl = t0.time
                # Display baseline fixation cross
                fixcross2.present()
                load_fixcross2 = t0.time - t_ttl
                # Wait WAIT seconds before the beginning of the trial
                exp.clock.wait(setting["WAIT"] - load_fixcross2 -
                               setting["cue"],
                               process_control_events=True)
                # Display trial fixation cross beforehand for preparation to
                # the beginning of the trial
                t_fix3 = t0.time
                fixcross3.present()
                load_fixcross3 = t0.time - t_fix3
                exp.clock.wait(setting["cue"] - load_fixcross3,
                               process_control_events=True)
                # Log file registry of TTL
                exp.data.add([session_id,
                              block_no+1,
                              '-',
                              'ttl',
                              '-',
                              t_ttl,
                              t0.time-t_ttl,
                              '-',
                              '-',
                              '-',
                              '-'])
            # Loop over all trials within a run (aka block)
            for t, trial in enumerate(block.trials):
                # Start the beep sequence
                trial_number = [*trial.factor_dict.values()][0]
                trial_name = [*trial.factor_dict.values()][1]
                intervals = [*trial.factor_dict.values()][2:]
                if trial_name != 'baseline':
                    intervals = list(map(int, intervals))
                    # Explicit variant: beat trials + base unit (isi_1 = T)
                    is_beat = trial_name.startswith(TARGET_TRIAL_PREFIX)
                    base_unit = intervals[0] if intervals else 0
                    for i, interval in enumerate(intervals, 1):
                        # ############### FLASH RECTANGLE ##############
                        t_flash = t0.time
                        # Display trial rectangle
                        trial_rect.present()
                        exp.clock.wait(setting["stim_duration"],
                                       process_control_events=True)
                        # Calculate duration of the audio condition
                        flash_duration = t0.time - t_flash
                        # Log file registry for the current trial
                        exp.data.add([
                            session_id,
                            block_no+1,
                            trial_number,
                            trial.get_factor(
                                setting["var_names_production"][1]),
                            'rectangle',
                            t_flash,
                            flash_duration,
                            '-',
                            '-',
                            '-',
                            '-'])
                        # ############### INTERVAL(S) (explicit) #######
                        _isi_visual_explicit(
                            setting, exp, t0, fixcross3, small_rect,
                            session_id, block_no, trial, trial_number,
                            "var_names_production", i, interval, base_unit, is_beat,
                            t_flash, flash_duration)

                        if i == 1:
                            isi1.append(interval)
                    # ############### TARGET FLASH RECTANGLE ###########
                    t_tflash = t0.time
                    # Display perception rectangle
                    trial_rect.present()
                    exp.clock.wait(setting["stim_duration"],
                                   process_control_events=True)
                    # Calculate duration of the target audio condition
                    target_flash_duration = t0.time - t_tflash
                    # Log file registry for the current trial
                    exp.data.add([
                        session_id,
                        block_no+1,
                        trial_number,
                        trial.get_factor(setting["var_names_production"][1]),
                        'rectangle',
                        t_tflash,
                        target_flash_duration,
                        '-',
                        '-',
                        '-',
                        '-'])
                    # ##################### FEEDBACK ###################
                    t_feedback = t0.time
                    # Display only fixation cross
                    fixcross3.present()
                    load_ffixcross = t0.time - t_feedback
                    # Wait for the feedback
                    remaining_duration_feedback = \
                        setting["feedback_duration"] + \
                        setting["stim_duration"] - \
                        target_flash_duration - load_ffixcross
                    key, rt = exp.keyboard.wait_char(
                        setting["INDEX_BUTTON"],
                        # [setting["INDEX_BUTTON"], setting["MIDDLE_BUTTON"]],
                        duration=remaining_duration_feedback)
                    # Add extra-time to the feedback period if < 1s
                    # in order to assure constant trial duration
                    if rt is None:
                        RT = -1
                        feedback_rt = None
                    else:
                        RT = rt
                        feedback_rt = load_ffixcross + rt
                    if 0 <= RT <= remaining_duration_feedback:
                        # Display the feedback-period rectangle
                        t_afterrt = t0.time
                        trial_rect.present()
                        exp.clock.wait(setting["stim_duration"],
                                       process_control_events=True)
                        fixcross2.present()
                        load_fbk = t0.time - t_afterrt
                        if kind != 'behavioral':
                            exp.clock.wait(remaining_duration_feedback - rt -
                                           load_fbk,
                                           process_control_events=True)
                        else:
                            exp.clock.wait(0, process_control_events=True)
                    # Calculate duration of the feedback period
                    feedback_duration = t0.time - t_feedback

                    # *****************************************
                    # print('Real Target Flash + Feedback Period is: ',
                    #       t0.time - t_tflash)
                    # print('rt is: ', rt)
                    # print('feedback_rt is: ', feedback_rt)
                    # *****************************************

                    # Log file registry of feedback for each event
                    exp.data.add([
                        session_id,
                        block_no+1,
                        trial_number,
                        trial.get_factor(setting["var_names_production"][1]),
                        'feedback',
                        t_feedback,
                        feedback_duration,
                        setting[
                            "feedback_duration"] + setting["stim_duration"],
                        t0.time - t_tflash,
                        feedback_rt,
                        key])

                    if rt is None:
                        rts.append(None)
                        # print('Real rt is: ', None)
                    else:
                        rts.append(target_flash_duration + feedback_rt)
                        # print('Real rt is: ',
                        #       target_flash_duration + feedback_rt)
                    # ########### FIXATION CROSS BETWEEN TRIALS ########
                    t_wb = t0.time
                    fixcross2.present()
                    load_fixcross2 = t0.time - t_wb
                    if t < len(list(enumerate(block.trials))) - 1:
                        if [*block.trials[t+1].factor_dict.values()][1] == \
                           'baseline':
                            exp.clock.wait(setting["within_block_duration"] -
                                           load_fixcross2,
                                           process_control_events=True)
                        else:
                            exp.clock.wait(
                                setting["within_block_duration"] -
                                load_fixcross2 - setting["cue"],
                                process_control_events=True)
                            t_fix3 = t0.time
                            fixcross3.present()
                            load_fixcross3 = t0.time - t_fix3
                            exp.clock.wait(setting["cue"] - load_fixcross3,
                                           process_control_events=True)
                    else:
                        assert t == len(list(enumerate(block.trials))) - 1
                        exp.clock.wait(
                            setting["within_block_duration"] - load_fixcross2,
                            process_control_events=True)
                    # Calculate the real duration of the interval
                    wb_real_duration = t0.time - t_wb
                    # Log file registry for the current trial
                    exp.data.add([session_id,
                                  block_no+1,
                                  '-',
                                  'fixcross',
                                  '-',
                                  t_wb,
                                  wb_real_duration,
                                  '-',
                                  '-',
                                  '-',
                                  '-'])
                # ##################### BASELINE #######################
                else:
                    t_baseline = t0.time
                    # Display fixation cross
                    fixcross2.present()
                    load_fixcross2 = t0.time - t_baseline
                    # Add a resting state period
                    if t < len(block.trials) - 1:
                        exp.clock.wait(
                            setting["baseline_duration"] - load_fixcross2 -
                            setting["cue"],
                            process_control_events=True)
                        t_fix3 = t0.time
                        fixcross3.present()
                        load_fixcross3 = t0.time - t_fix3
                        exp.clock.wait(setting["cue"] - load_fixcross3,
                                       process_control_events=True)
                    else:
                        assert t == len(block.trials) - 1
                        exp.clock.wait(
                            setting["baseline_duration"] - load_fixcross2,
                            process_control_events=True)
                    # Calculate the real duration of the interval
                    baseline_real_duration = t0.time - t_baseline
                    # Log file registry for the current trial
                    exp.data.add([session_id,
                                  block_no+1,
                                  '-',
                                  trial_name,
                                  '-',
                                  t_baseline,
                                  baseline_real_duration,
                                  '-',
                                  '-',
                                  '-',
                                  '-'])

            rts_session.extend(rts)
            isi1_session.extend(isi1)

            # ######################### END OF RUN #####################
            stop = True
            # ################### Compute final score ##################
            rate_run, score_list = production_rating(setting, rts, isi1,
                                                     score=score)
            if kind == 'imaging' and auto is None:
                break
            else:
                # Final baseline before stopping the scan
                if kind == 'imaging':
                    # Display baseline fixation cross
                    wait(t0, fixcross2, exp, setting, session_id)
                # ############### Compute final run score ##############
                score_run = _display_score_run(setting, spec, rate_run)
                score_run.present()
                exp.clock.wait(setting["score_display_duration"])

                # ################ Display final message ###############
                if kind == 'imaging' and auto is not None:
                    found_key = _next_run(last_run, task_id, n_block,
                                          start_block - offset,
                                          text_end_session, text_end_run, exp)
                else:
                    found_key = _next_run(last_run, task_id, n_block,
                                          start_block,
                                          text_end_session, text_end_run, exp)

                # ################## Return to main menu ###############
                if found_key in [misc.constants.K_RETURN,
                                 misc.constants.K_KP_ENTER]:
                    break

    end = t0.time

    return session_id, start_block + 1, score_list, end


def visual_perception_explicit(protocol_ini, spec, exp, kind='training', t0=None,
                      tlast=None, auto=None, score=None):
    # %%
    # ======================== LOAD CONFIG.INI FILE ====================
    setting = load_config(protocol_ini)

    # %%
    # ==================== DEFINE AND PRELOAD SOME STIMULI =============
    fixcross1, fixcross2, fixcross3 = fixcrosses(setting, spec)
    trial_rect, _, _ = visual_stim(setting, spec)
    small_rect = stimuli.Rectangle(
        tuple(list(map(int, spec[SMALL_RECT_SIZE_KEY]))),
        colour=tuple(list(map(int, setting["dark_gray"]))),
        position=(0, 0))
    screen_feedback_percep = panel_stim(setting, spec)
    text_end_run, text_end_session = _txt_message(setting, spec)

    fixcross1.preload()
    fixcross2.preload()
    fixcross3.preload()

    trial_rect.preload()
    small_rect.preload()

    screen_feedback_percep.preload()

    text_end_run.preload()
    text_end_session.preload()

    # %%
    # ================================ RUN =============================
    # ==================================================================
    # Starts running the experiment:
    # (1) Present a screen asking for the subject no. (exp.subject) and
    #     wait for the RETURN key
    # (2) Create a data file (exp.data)
    # (3) Present the "Ready" screen
    # ==================================================================

    if auto is None:
        control.start(skip_ready_screen=True)
        session_id = _launch_sess(setting, spec, exp)
    else:
        if kind == 'behavioral':
            control.start(skip_ready_screen=True, subject_id=auto['subject'])
        elif kind == 'imaging':
            offset = len(exp.blocks)
        else:
            pass
        session_id = auto['session']

    subject_id = exp.subject

    # %%
    # ========================== LOAD INPUT FILES ======================
    inputs_filenames, n_block, last_run = \
        _load_inputs(setting, 'percep_dir', subject_id, session_id, 'visual')

    # %%
    # ====================== EXPERIMENTAL DESIGN =======================
    task_id = _visual_design(setting, n_block, exp, inputs_filenames,
                             "var_names_perception")

    # %%
    # ============= WAITS FOR USER TO ENTER RUN NUMBER TO START ========
    if auto is None:
        start_block = _launch_run(setting, spec, n_block, exp)
    else:
        start_block = auto['nrun']
        # 2nd task of the same run, n_blocks in design are incremented
        if kind == 'imaging':
            start_block += offset
    start_block -= 1

    # ==================================================================
    # Run the protocol
    # ==================================================================
    stop = False
    # While "ESC" key is not pressed, ...
    while not stop:
        # Prepare arrays of score estimation for the entire session
        isi1_session = []
        isi5_session = []
        answers_session = []
        # ... and for each run
        for b, block in enumerate(exp.blocks[start_block:]):
            # Prepare arrays of score estimation for each run
            isi1 = []
            isi5 = []
            answers = []
            # TTL or not?
            if kind == 'imaging' and auto is not None:
                block_no = b + start_block - offset
                # ############ Baseline between tasks ##################
                baseline_bt(t0, exp, setting, tlast, session_id)
            else:
                # Start at any run number
                block_no = b + start_block
                if kind != 'imaging':
                    # Creates the clock
                    t0 = misc.Clock()
                # Display TTL fixation cross that sets the beginning of
                # the experiment
                fixcross1.present()
                # Wait for TTL
                exp.keyboard.wait_char(setting["TTL"])
                t_ttl = t0.time
                # Display baseline fixation cross
                fixcross2.present()
                load_fixcross2 = t0.time - t_ttl
                # Wait WAIT seconds before the beginning of the trial
                exp.clock.wait(setting["WAIT"] - load_fixcross2 -
                               setting["cue"],
                               process_control_events=True)
                # Display trial fixation cross beforehand for preparation to
                # the beginning of the trial
                t_fix3 = t0.time
                fixcross3.present()
                load_fixcross3 = t0.time - t_fix3
                exp.clock.wait(setting["cue"] - load_fixcross3,
                               process_control_events=True)
                # Log file registry of TTL
                exp.data.add([session_id,
                              block_no+1,
                              '-',
                              'ttl',
                              '-',
                              t_ttl,
                              t0.time-t_ttl,
                              '-',
                              '-',
                              '-',
                              '-'])
            # Loop over all trials within a run (aka block)
            for t, trial in enumerate(block.trials):
                # Start the beep sequence
                trial_number = [*trial.factor_dict.values()][0]
                trial_name = [*trial.factor_dict.values()][1]
                intervals = [*trial.factor_dict.values()][2:]
                if trial_name != 'baseline':
                    intervals = list(map(int, intervals))
                    # Explicit variant: beat trials + base unit (isi_1 = T)
                    is_beat = trial_name.startswith(TARGET_TRIAL_PREFIX)
                    base_unit = intervals[0] if intervals else 0
                    for i, interval in enumerate(intervals, 1):
                        # ############### FLASH RECTANGLE ##############
                        t_flash = t0.time
                        # Display trial rectangle
                        trial_rect.present()
                        exp.clock.wait(setting["stim_duration"],
                                       process_control_events=True)
                        # Calculate duration of the audio condition
                        flash_duration = t0.time - t_flash
                        # Log file registry for the current trial
                        exp.data.add([
                            session_id,
                            block_no+1,
                            trial_number,
                            trial.get_factor(
                                setting["var_names_perception"][1]),
                            'rectangle',
                            t_flash,
                            flash_duration,
                            '-',
                            '-',
                            '-',
                            '-'])
                        # ############### INTERVAL(S) (explicit) #######
                        _isi_visual_explicit(
                            setting, exp, t0, fixcross3, small_rect,
                            session_id, block_no, trial, trial_number,
                            "var_names_perception", i, interval, base_unit, is_beat,
                            t_flash, flash_duration)

                        if i == 1:
                            isi1.append(interval)
                        elif i == 5:
                            isi5.append(interval)
                    # ############### FINAL FLASH RECTANGLE ############
                    t_fflash = t0.time
                    # Display perception rectangle
                    trial_rect.present()
                    exp.clock.wait(setting["stim_duration"],
                                   process_control_events=True)
                    # Calculate duration of the audio condition
                    final_flash_duration = t0.time - t_fflash
                    # Log file registry for the current trial
                    exp.data.add([
                        session_id,
                        block_no+1,
                        trial_number,
                        trial.get_factor(setting["var_names_perception"][1]),
                        'rectangle',
                        t_fflash,
                        final_flash_duration,
                        '-',
                        '-',
                        '-',
                        '-'])
                    # ################### FEEDBACK #####################
                    t_feedback = t0.time
                    # Display Screen with question
                    fixcross3.present()
                    exp.clock.wait(80, process_control_events=True)
                    screen_feedback_percep.present()
                    load_screen = t0.time - t_feedback
                    # Wait for the feedback
                    remaining_duration_feedback = \
                        setting["feedback_duration"] + \
                        setting["stim_duration"] - \
                        final_flash_duration - load_screen
                    key, rt = exp.keyboard.wait_char(
                        [setting["INDEX_BUTTON"], setting["MIDDLE_BUTTON"]],
                        duration=remaining_duration_feedback)
                    # Add extra-time to the feedback period if < 10s
                    # in order to assure constant trial duration
                    if rt is None:
                        RT = -1
                        feedback_rt = None
                    else:
                        RT = rt
                        feedback_rt = load_screen + rt
                    if 0 <= RT <= remaining_duration_feedback:
                        # Remove Questionnaire screen and display baseline
                        # fixation cross
                        tfix = t0.time
                        fixcross2.present()
                        load_fixcross2 = t0.time - tfix
                        if kind != 'behavioral':
                            exp.clock.wait(remaining_duration_feedback - rt -
                                           load_fixcross2,
                                           process_control_events=True)
                        else:
                            exp.clock.wait(0, process_control_events=True)
                    # Calculate duration of the feedback period
                    feedback_duration = t0.time - t_feedback

                    # *****************************************
                    # print('Real Final Flash + Feedback Period is: ',
                    #       t0.time - t_fflash)
                    # print('rt is: ', rt)
                    # print('feedback_rt is: ', feedback_rt)
                    # *****************************************

                    # Log file registry of feedback for each event
                    exp.data.add([
                        session_id,
                        block_no+1,
                        trial_number,
                        trial.get_factor(setting["var_names_perception"][1]),
                        'feedback',
                        t_feedback,
                        feedback_duration,
                        setting[
                            "feedback_duration"] + setting["stim_duration"],
                        t0.time - t_fflash,
                        feedback_rt,
                        key])

                    if rt is None:
                        answers.append(None)
                        # print('Real rt is: ', None)
                    else:
                        answers.append(key)
                        # print('Real rt is: ',
                        #       final_flash_duration + feedback_rt)
                    # ########### FIXATION CROSS BETWEEN TRIALS ########
                    t_wb = t0.time
                    fixcross2.present()
                    load_fixcross2 = t0.time - t_wb
                    if t < len(list(enumerate(block.trials))) - 1:
                        if [*block.trials[t+1].factor_dict.values()][1] == \
                           'baseline':
                            exp.clock.wait(setting["within_block_duration"] -
                                           load_fixcross2,
                                           process_control_events=True)
                        else:
                            exp.clock.wait(
                                setting["within_block_duration"] -
                                load_fixcross2 - setting["cue"],
                                process_control_events=True)
                            t_fix3 = t0.time
                            fixcross3.present()
                            load_fixcross3 = t0.time - t_fix3
                            exp.clock.wait(setting["cue"] - load_fixcross3,
                                           process_control_events=True)
                    else:
                        assert t == len(list(enumerate(block.trials))) - 1
                        exp.clock.wait(
                            setting["within_block_duration"] - load_fixcross2,
                            process_control_events=True)
                    # Calculate the real duration of the interval
                    wb_real_duration = t0.time - t_wb
                    # Log file registry for the current trial
                    exp.data.add([session_id,
                                  block_no+1,
                                  '-',
                                  'fixcross',
                                  '-',
                                  t_wb,
                                  wb_real_duration,
                                  '-',
                                  '-',
                                  '-',
                                  '-'])
                # ##################### BASELINE #######################
                else:
                    t_baseline = t0.time
                    # Display fixation cross
                    fixcross2.present()
                    load_fixcross2 = t0.time - t_baseline
                    # Add a resting state period
                    if t < len(block.trials) - 1:
                        exp.clock.wait(
                            setting["baseline_duration"] - load_fixcross2 -
                            setting["cue"],
                            process_control_events=True)
                        t_fix3 = t0.time
                        fixcross3.present()
                        load_fixcross3 = t0.time - t_fix3
                        exp.clock.wait(setting["cue"] - load_fixcross3,
                                       process_control_events=True)
                    else:
                        assert t == len(block.trials) - 1
                        exp.clock.wait(
                            setting["baseline_duration"] - load_fixcross2,
                            process_control_events=True)
                    # Calculate the real duration of the interval
                    baseline_real_duration = t0.time - t_baseline
                    # Log file registry for the current trial
                    exp.data.add([session_id,
                                  block_no+1,
                                  '-',
                                  trial_name,
                                  '-',
                                  t_baseline,
                                  baseline_real_duration,
                                  '-',
                                  '-',
                                  '-',
                                  '-'])

            answers_session.extend(answers)
            isi1_session.extend(isi1)
            isi5_session.extend(isi5)

            # ######################### END OF RUN #####################
            stop = True
            # ##################### Compute final score ################
            rate_run, score_list = perception_rating(setting, answers,
                                                     isi1, isi5,
                                                     score=score)
            if kind == 'imaging' and auto is None:
                break
            else:
                # Final baseline before stopping the scan
                if kind == 'imaging':
                    # Display baseline fixation cross
                    wait(t0, fixcross2, exp, setting, session_id)
                # ############### Compute final run score ##############
                score_run = _display_score_run(setting, spec, rate_run)
                score_run.present()
                exp.clock.wait(setting["score_display_duration"])

                # ################ Display final message ###############
                if kind == 'imaging' and auto is not None:
                    found_key = _next_run(last_run, task_id, n_block,
                                          start_block - offset,
                                          text_end_session, text_end_run, exp)
                else:
                    found_key = _next_run(last_run, task_id, n_block,
                                          start_block,
                                          text_end_session, text_end_run, exp)

                # ################## Return to main menu ###############
                if found_key in [misc.constants.K_RETURN,
                                 misc.constants.K_KP_ENTER]:
                    break

    end = t0.time

    return session_id, start_block + 1, score_list, end


def visual_notemporal_explicit(protocol_ini, spec, exp, kind='training', t0=None,
                      tlast=None, auto=None, score=None):
    # %%
    # ======================== LOAD CONFIG.INI FILE ====================
    setting = load_config(protocol_ini)

    # %%
    # ==================== DEFINE AND PRELOAD SOME STIMULI =============
    fixcross1, fixcross2, fixcross3 = fixcrosses(setting, spec)
    trial_rect, target_circ, target_tri = visual_stim(setting, spec)
    small_rect = stimuli.Rectangle(
        tuple(list(map(int, spec[SMALL_RECT_SIZE_KEY]))),
        colour=tuple(list(map(int, setting["dark_gray"]))),
        position=(0, 0))
    text_end_run, text_end_session = _txt_message(setting, spec)

    fixcross1.preload()
    fixcross2.preload()
    fixcross3.preload()

    trial_rect.preload()
    small_rect.preload()
    target_circ.preload()
    target_tri.preload()

    text_end_run.preload()
    text_end_session.preload()

    # %%
    # ================================ RUN =============================
    # ==================================================================
    # Starts running the experiment:
    # (1) Present a screen asking for the subject no. (exp.subject) and
    #     wait for the RETURN key
    # (2) Create a data file (exp.data)
    # (3) Present the "Ready" screen
    # ==================================================================

    if auto is None:
        control.start(skip_ready_screen=True)
        session_id = _launch_sess(setting, spec, exp)
    else:
        if kind == 'behavioral':
            control.start(skip_ready_screen=True, subject_id=auto['subject'])
        elif kind == 'imaging':
            offset = len(exp.blocks)
        else:
            pass
        session_id = auto['session']

    subject_id = exp.subject

    # %%
    # ========================== LOAD INPUT FILES ======================
    inputs_filenames, n_block, last_run = \
        _load_inputs(setting, 'notemp_dir', subject_id, session_id, 'visual')

    # %%
    # ====================== EXPERIMENTAL DESIGN =======================
    task_id = _visual_design(setting, n_block, exp, inputs_filenames,
                             "var_names_notemporal")

    # %%
    # ============= WAITS FOR USER TO ENTER RUN NUMBER TO START ========
    if auto is None:
        start_block = _launch_run(setting, spec, n_block, exp)
    else:
        start_block = auto['nrun']
        # 2nd task of the same run, n_blocks in design are incremented
        if kind == 'imaging':
            start_block += offset
    start_block -= 1

    # ==================================================================
    # Run the protocol
    # ==================================================================
    stop = False
    # While "ESC" key is not pressed, ...
    while not stop:
        # Prepare arrays of score estimation for the entire session
        targetstim_session = []
        rts_session = []
        answers_session = []
        # ... and for each run
        for b, block in enumerate(exp.blocks[start_block:]):
            # Prepare arrays of score estimation for each run
            targetstim = []
            rts = []
            answers = []
            # TTL or not?
            if kind == 'imaging' and auto is not None:
                block_no = b + start_block - offset
                # ############ Baseline between tasks ##################
                baseline_bt(t0, exp, setting, tlast, session_id)
            else:
                # Start at any run number
                block_no = b + start_block
                if kind != 'imaging':
                    # Creates the clock
                    t0 = misc.Clock()
                # Display TTL fixation cross that sets the beginning of
                # the experiment
                fixcross1.present()
                # Wait for TTL
                exp.keyboard.wait_char(setting["TTL"])
                t_ttl = t0.time
                # Display baseline fixation cross
                fixcross2.present()
                load_fixcross2 = t0.time - t_ttl
                # Wait WAIT seconds before the beginning of the trial
                exp.clock.wait(setting["WAIT"] - load_fixcross2 -
                               setting["cue"],
                               process_control_events=True)
                # Display trial fixation cross beforehand for preparation to
                # the beginning of the trial
                t_fix3 = t0.time
                fixcross3.present()
                load_fixcross3 = t0.time - t_fix3
                exp.clock.wait(setting["cue"] - load_fixcross3,
                               process_control_events=True)
                # Log file registry of TTL
                exp.data.add([session_id,
                              block_no+1,
                              '-',
                              'ttl',
                              '-',
                              t_ttl,
                              t0.time-t_ttl,
                              '-',
                              '-',
                              '-',
                              '-'])
            # Loop over all trials within a run (aka block)
            for t, trial in enumerate(block.trials):
                # Start the beep sequence
                trial_number = [*trial.factor_dict.values()][0]
                trial_name = [*trial.factor_dict.values()][1]
                intervals = [*trial.factor_dict.values()][2:-1]
                if trial_name != 'baseline':
                    intervals = list(map(int, intervals))
                    # Explicit variant: beat trials + base unit (isi_1 = T)
                    is_beat = trial_name.startswith(TARGET_TRIAL_PREFIX)
                    base_unit = intervals[0] if intervals else 0
                    for i, interval in enumerate(intervals, 1):
                        # ############### FLASH RECTANGLE ##############
                        t_flash = t0.time
                        # Display trial rectangle
                        trial_rect.present()
                        exp.clock.wait(setting["stim_duration"],
                                       process_control_events=True)
                        # Calculate duration of the audio condition
                        flash_duration = t0.time - t_flash
                        # Log file registry for the current trial
                        exp.data.add([
                            session_id,
                            block_no+1,
                            trial_number,
                            trial.get_factor(
                                setting["var_names_notemporal"][1]),
                            'rectangle',
                            t_flash,
                            flash_duration,
                            '-',
                            '-',
                            '-',
                            '-'])
                        # ############### INTERVAL(S) (explicit) #######
                        _isi_visual_explicit(
                            setting, exp, t0, fixcross3, small_rect,
                            session_id, block_no, trial, trial_number,
                            "var_names_notemporal", i, interval, base_unit, is_beat,
                            t_flash, flash_duration)
                    # ############ TARGET FLASH CIRCLE/TRIANGLE ########
                    t_tflash = t0.time
                    # Display target shape
                    if trial.get_factor(
                            setting["var_names_notemporal"][7]) == 'circle':
                        target_circ.present()
                    else:
                        assert trial.get_factor(
                            setting["var_names_notemporal"][7]) == 'triangle'
                        target_tri.present()
                    exp.clock.wait(setting["stim_duration"],
                                   process_control_events=True)
                    # Calculate duration of the target audio condition
                    target_flash_duration = t0.time - t_tflash
                    # Log file registry for the current trial
                    exp.data.add([
                        session_id,
                        block_no+1,
                        trial_number,
                        trial.get_factor(setting["var_names_notemporal"][1]),
                        trial.get_factor(setting["var_names_notemporal"][7]),
                        t_tflash,
                        target_flash_duration,
                        '-',
                        '-',
                        '-',
                        '-'])

                    targetstim.append(
                        trial.get_factor(setting["var_names_notemporal"][7]))
                    # ##################### FEEDBACK ###################
                    t_feedback = t0.time
                    # Wait for the feedback
                    fixcross3.present()
                    load_fixcross = t0.time - t_feedback
                    remaining_duration_feedback = \
                        setting["feedback_duration"] + \
                        setting["stim_duration"] - \
                        target_flash_duration - load_fixcross
                    key, rt = exp.keyboard.wait_char(
                        [setting["INDEX_BUTTON"], setting["MIDDLE_BUTTON"]],
                        duration=remaining_duration_feedback)
                    # Add extra-time to the feedback period if < 1s
                    # in order to assure constant trial duration
                    if rt is None:
                        RT = -1
                        feedback_rt = None
                    else:
                        RT = rt
                        feedback_rt = load_fixcross + rt
                    if 0 <= RT <= remaining_duration_feedback:
                        tffix = t0.time
                        if key == setting["INDEX_BUTTON"]:
                            target_circ.present()
                        else:
                            assert key == setting["MIDDLE_BUTTON"]
                            target_tri.present()
                        fixcross2.present()
                        flashfix_duration = t0.time - tffix
                        if kind != 'behavioral':
                            exp.clock.wait(
                                remaining_duration_feedback - rt -
                                flashfix_duration,
                                process_control_events=True)
                        else:
                            exp.clock.wait(0, process_control_events=True)

                    # Calculate duration of the feedback period
                    feedback_duration = t0.time - t_feedback

                    # *****************************************
                    # print('Real Target Flash + Feedback Period is: ',
                    #       t0.time - t_tflash)
                    # print('rt is: ', rt)
                    # print('feedback_rt is: ', feedback_rt)
                    # *****************************************

                    # Log file registry of feedback for each event
                    exp.data.add([
                        session_id,
                        block_no+1,
                        trial_number,
                        trial.get_factor(setting["var_names_notemporal"][1]),
                        'feedback',
                        t_feedback,
                        feedback_duration,
                        setting[
                            "feedback_duration"] + setting["stim_duration"],
                        t0.time - t_tflash,
                        rt,
                        key])

                    if rt is None:
                        rts.append(None)
                        answers.append(None)
                        # print('Real rt is: ', None)
                    else:
                        rts.append(target_flash_duration + feedback_rt)
                        answers.append(key)
                        # print('Real rt is: ',
                        #       target_flash_duration + feedback_rt)
                    # ########### FIXATION CROSS BETWEEN TRIALS ########
                    t_wb = t0.time
                    fixcross2.present()
                    load_fixcross2 = t0.time - t_wb
                    if t < len(list(enumerate(block.trials))) - 1:
                        if [*block.trials[t+1].factor_dict.values()][1] == \
                           'baseline':
                            exp.clock.wait(setting["within_block_duration"] -
                                           load_fixcross2,
                                           process_control_events=True)
                        else:
                            exp.clock.wait(
                                setting["within_block_duration"] -
                                load_fixcross2 - setting["cue"])
                            t_fix3 = t0.time
                            fixcross3.present()
                            load_fixcross3 = t0.time - t_fix3
                            exp.clock.wait(setting["cue"] - load_fixcross3,
                                           process_control_events=True)
                    else:
                        assert t == len(list(enumerate(block.trials))) - 1
                        exp.clock.wait(
                            setting["within_block_duration"] - load_fixcross2,
                            process_control_events=True)
                    # Calculate the real duration of the interval
                    wb_real_duration = t0.time - t_wb
                    # Log file registry for the current trial
                    exp.data.add([session_id,
                                  block_no+1,
                                  '-',
                                  'fixcross',
                                  '-',
                                  t_wb,
                                  wb_real_duration,
                                  '-',
                                  '-',
                                  '-',
                                  '-'])
                # ##################### BASELINE #######################
                else:
                    t_baseline = t0.time
                    # Display fixation cross
                    fixcross2.present()
                    load_fixcross2 = t0.time - t_baseline
                    # Add a resting state period
                    if t < len(block.trials) - 1:
                        exp.clock.wait(
                            setting["baseline_duration"] - load_fixcross2 -
                            setting["cue"],
                            process_control_events=True)
                        t_fix3 = t0.time
                        fixcross3.present()
                        load_fixcross3 = t0.time - t_fix3
                        exp.clock.wait(setting["cue"] - load_fixcross3,
                                       process_control_events=True)
                    else:
                        assert t == len(block.trials) - 1
                        exp.clock.wait(
                            setting["baseline_duration"] - load_fixcross2,
                            process_control_events=True)
                    # Calculate the real duration of the interval
                    baseline_real_duration = t0.time - t_baseline
                    # Log file registry for the current trial
                    exp.data.add([session_id,
                                  block_no+1,
                                  '-',
                                  trial_name,
                                  '-',
                                  t_baseline,
                                  baseline_real_duration,
                                  '-',
                                  '-',
                                  '-',
                                  '-'])

            targetstim_session.extend(targetstim)
            rts_session.extend(rts)
            answers_session.extend(answers)

            # ######################### END OF RUN #####################
            stop = True
            # ##################### Compute final score ################
            rate_run, score_list = notemporal_rating(setting, targetstim,
                                                     rts, answers,
                                                     score=score)
            if kind == 'imaging' and auto is None:
                break
            else:
                # Final baseline before stopping the scan
                if kind == 'imaging':
                    # Display baseline fixation cross
                    wait(t0, fixcross2, exp, setting, session_id)
                # ############### Compute final run score ##############
                score_run = _display_score_run(setting, spec, rate_run)
                score_run.present()
                exp.clock.wait(setting["score_display_duration"])

                # ################ Display final message ###############
                if kind == 'imaging' and auto is not None:
                    found_key = _next_run(last_run, task_id, n_block,
                                          start_block - offset,
                                          text_end_session, text_end_run, exp)
                else:
                    found_key = _next_run(last_run, task_id, n_block,
                                          start_block,
                                          text_end_session, text_end_run, exp)

                # ################## Return to main menu ###############
                if found_key in [misc.constants.K_RETURN,
                                 misc.constants.K_KP_ENTER]:
                    break

    end = t0.time

    return session_id, start_block + 1, score_list, end
