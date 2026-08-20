# -*- coding: utf-8 -*-

import csv
import numpy as np

from expyriment import design, control, misc
from confparser import load_config
from utils import (_load_inputs, _launch_sess, _launch_run, fixcrosses,
                   audio_stim, panel_stim, production_rating,
                   perception_rating, notemporal_rating, _display_score_run,
                   _txt_message, _next_run, wait, baseline_bt, same_beep)


def _audio_design(setting, n_block, exp, inputs_filenames, varnames):
    # Stimuli sequence of the protocol
    session_list = [[i for i in csv.reader(open(inputs_filename),
                                           delimiter='\t')]
                    for inputs_filename in inputs_filenames]

    # Fix different behaviours of csvreader between Windows and Linux
    session_list = [[sess for sess in session if sess]
                    for session in session_list if session]

    # Define the runs (aka blocks) using expyriment module
    block_list = [design.Block(name="block%02d" % bs)
                  for bs in np.arange(1, n_block + 1)]

    # For all runs (aka blocks) in the run list...
    for bl in np.arange(n_block):
        # ...add stimuli to every trial and add trial to the block
        for line in session_list[bl][1:]:
            # Remove theoretical onsets
            line = line[1:]
            # Create a trial
            trial = design.Trial()
            # Retrieve variables, i.e. isi's, from input files at every
            # trial and label them according to what is defined by
            # var_names in the corresponding .ini file
            for tsf in np.arange(len(setting[varnames])):
                trial.set_factor(setting[varnames][tsf], line[tsf])
            # Add trial to run (aka block)
            block_list[bl].add_trial(trial)
    # Add run (aka block) to the experiment
    for ad in np.arange(n_block):
        exp.add_block(block_list[ad])

    # Print which task of the battery in the log files (.xpd and .xpe)
    if varnames == "var_names_production":
        exp.add_experiment_info(
            'Task: Auditory Production - ' + setting["sesstype"])
        task_tag = 'audio_production'
    elif varnames == "var_names_perception":
        exp.add_experiment_info(
            'Task: Auditory Perception - ' + setting["sesstype"])
        task_tag = 'audio_perception'
    else:
        assert varnames == "var_names_notemporal"
        exp.add_experiment_info(
            'Task: Auditory No-Temporal Feature Discrimination - ' + \
            setting["sesstype"])
        task_tag = 'audio_notemporal'

    # Print exp. variable names in the log files (.xpd and .xpe)
    exp.data_variable_names = setting["llog_var_names"]

    return task_tag


def audio_production(protocol_ini, spec, exp, kind='training', t0=None,
                     tlast=None, auto=None, score=None):
    """
    kind accepts 'imaging', 'training' and 'behavioral'
    default is 'imaging'
    """
    # %%
    # ======================== LOAD CONFIG.INI FILE ====================
    setting = load_config(protocol_ini)

    # %%
    # ==================== DEFINE AND PRELOAD SOME STIMULI =============
    fixcross1, fixcross2, fixcross3 = fixcrosses(setting, spec)
    _, medium_beep, _ = audio_stim(setting)
    text_end_run, text_end_session = _txt_message(setting, spec)

    fixcross1.preload()
    fixcross2.preload()
    fixcross3.preload()

    medium_beep.preload()

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

    # Start audio system
    control.start_audiosystem()

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
        _load_inputs(setting, 'prod_dir', subject_id, session_id, 'audio')

    # %%
    # ====================== EXPERIMENTAL DESIGN =======================
    task_id = _audio_design(setting, n_block, exp, inputs_filenames,
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
            # Start at any run number
            block_no = b + start_block
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
                    for i, interval in enumerate(intervals, 1):
                        # ################# AUDIO BEEP #################
                        t_beep = t0.time
                        # Display audio stim
                        medium_beep.present()
                        # Display trial fixation cross
                        t_fix3 = t0.time
                        fixcross3.present()
                        load_fixcross3 = t0.time - t_fix3
                        exp.clock.wait(setting["stim_duration"] -
                                       load_fixcross3,
                                       process_control_events=True)
                        # Calculate duration of the audio condition
                        audio_duration = t0.time - t_beep

                        # Log file registry for the current trial
                        exp.data.add([
                            session_id,
                            block_no+1,
                            trial_number,
                            trial.get_factor(
                                setting["var_names_production"][1]),
                            setting["audiowav_medium"],
                            t_beep,
                            audio_duration,
                            '-',
                            '-',
                            '-',
                            '-'])
                        # ################# INTERVAL ###################
                        t_interval = t0.time
                        exp.clock.wait(interval - audio_duration,
                                       process_control_events=True)

                        # Calculate the real duration of the interval
                        interval_clock_duration = t0.time - t_interval

                        # *****************************************
                        # print(trial.get_factor(
                        #     setting["var_names_production"][1]))
                        # print('Isi', i, 'is: ', interval)
                        # print('Real Isi is: ', t0.time - t_beep)
                        # *****************************************

                        # Log file registry for the current trial
                        exp.data.add([
                            session_id,
                            block_no+1,
                            trial_number,
                            trial.get_factor(
                                setting["var_names_production"][1]),
                            setting["var_names_production"][i+1],
                            t_interval,
                            interval_clock_duration,
                            interval,
                            t0.time - t_beep,
                            '-',
                            '-'])

                        if i == 1:
                            isi1.append(interval)
                    # ################# TARGET AUDIO BEEP ##############
                    t_tbeep = t0.time
                    # Display audio stim
                    medium_beep.present()
                    exp.clock.wait(setting["stim_duration"],
                                   process_control_events=True)
                    # Calculate duration of the target audio condition
                    target_audio_duration = t0.time - t_tbeep
                    # Log file registry for the current trial
                    exp.data.add([
                        session_id,
                        block_no+1,
                        trial_number,
                        trial.get_factor(setting["var_names_production"][1]),
                        setting["audiowav_medium"],
                        t_tbeep,
                        target_audio_duration,
                        '-',
                        '-',
                        '-',
                        '-'])
                    # ##################### FEEDBACK ###################
                    t_feedback = t0.time
                    # Wait for the feedback
                    remaining_duration_feedback = \
                        setting["feedback_duration"] + \
                        setting["stim_duration"] - target_audio_duration
                    key, rt = exp.keyboard.wait_char(
                        setting["INDEX_BUTTON"],
                        # [setting["INDEX_BUTTON"], setting["MIDDLE_BUTTON"]],
                        duration=remaining_duration_feedback)
                    if rt is None:
                        RT = -1
                    else:
                        RT = rt
                    if 0 <= RT <= remaining_duration_feedback:
                        tsfix = t0.time
                        medium_beep.present()
                        fixcross2.present()
                        soundfix_duration = t0.time - tsfix
                        if kind != 'behavioral':
                            exp.clock.wait(remaining_duration_feedback - rt -
                                           soundfix_duration,
                                           process_control_events=True)
                        else:
                            exp.clock.wait(0, process_control_events=True)
                    # Calculate duration of the feedback period
                    feedback_duration = t0.time - t_feedback

                    # *****************************************
                    # print('Real Target Beep + Feedback Period is: ',
                    #       t0.time - t_tbeep)
                    # print('rt is: ', rt)
                    # print('feedback_rt is: ', rt)
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
                        t0.time - t_tbeep,
                        rt,
                        key])

                    if rt is None:
                        rts.append(None)
                        # print('Real rt is: ', None)
                    else:
                        rts.append(target_audio_duration + rt)
                        # print('Real rt is: ', target_audio_duration + rt)
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
            # ################# Compute final score ####################
            rate_run, score_list = production_rating(setting, rts, isi1,
                                                     score=score)
            if kind == 'imaging' and auto is None:
                # End of first task for img run --> Go to next run
                break
            else:
                # Final baseline before stopping the scan
                if kind == 'imaging':
                    # Display baseline fixation cross
                    wait(t0, fixcross2, exp, setting, session_id)
                # ############### Display final run score ##############
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


def audio_perception(protocol_ini, spec, exp, kind='training', t0=None,
                     tlast=None, auto=None, score=None):
    # %%
    # ======================== LOAD CONFIG.INI FILE ====================
    setting = load_config(protocol_ini)

    # %%
    # ==================== DEFINE AND PRELOAD SOME STIMULI =============
    fixcross1, fixcross2, fixcross3 = fixcrosses(setting, spec)
    _, medium_beep, _ = audio_stim(setting)
    screen_feedback_percep = panel_stim(setting, spec)
    text_end_run, text_end_session = _txt_message(setting, spec)

    fixcross1.preload()
    fixcross2.preload()
    fixcross3.preload()

    medium_beep.preload()

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

    # Start audio system
    control.start_audiosystem()

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
        _load_inputs(setting, 'percep_dir', subject_id, session_id, 'audio')

    # %%
    # ====================== EXPERIMENTAL DESIGN =======================
    task_id = _audio_design(setting, n_block, exp, inputs_filenames,
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
            # Start at any run number
            block_no = b + start_block
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
                    for i, interval in enumerate(intervals, 1):
                        # ################# AUDIO BEEP #################
                        t_beep = t0.time
                        # Display audio stim
                        medium_beep.present()
                        # Display trial fixation cross
                        t_fix3 = t0.time
                        fixcross3.present()
                        load_fixcross3 = t0.time - t_fix3
                        exp.clock.wait(setting["stim_duration"] -
                                       load_fixcross3,
                                       process_control_events=True)
                        # Calculate duration of the audio condition
                        audio_duration = t0.time - t_beep
                        # Log file registry for the current trial
                        exp.data.add([
                            session_id,
                            block_no+1,
                            trial_number,
                            trial.get_factor(
                                setting["var_names_perception"][1]),
                            setting["audiowav_medium"],
                            t_beep,
                            audio_duration,
                            '-',
                            '-',
                            '-',
                            '-'])
                        # ################# INTERVAL ###################
                        t_interval = t0.time
                        exp.clock.wait(interval - audio_duration,
                                       process_control_events=True)

                        # Calculate the real duration of the interval
                        interval_clock_duration = t0.time - t_interval

                        # *****************************************
                        # print(trial.get_factor(
                        #     setting["var_names_perception"][1]))
                        # print('Isi', i, 'is: ', interval)
                        # print('Real Isi is: ', t0.time - t_beep)
                        # *****************************************

                        # Log file registry for the current trial
                        exp.data.add([
                            session_id,
                            block_no+1,
                            trial_number,
                            trial.get_factor(
                                setting["var_names_perception"][1]),
                            setting["var_names_perception"][i+1],
                            t_interval,
                            interval_clock_duration,
                            interval,
                            t0.time - t_beep,
                            '-',
                            '-'])

                        if i == 1:
                            isi1.append(interval)
                        elif i == 5:
                            isi5.append(interval)
                    # ################# FINAL AUDIO BEEP ###############
                    t_fbeep = t0.time
                    # Getter for the time in milliseconds since clock init.
                    # Display audio stim
                    medium_beep.present()
                    exp.clock.wait(setting["stim_duration"],
                                   process_control_events=True)
                    # Calculate duration of the audio condition
                    final_audio_duration = t0.time - t_fbeep
                    # Log file registry for the current trial
                    exp.data.add([
                        session_id,
                        block_no+1,
                        trial_number,
                        trial.get_factor(setting["var_names_perception"][1]),
                        setting["audiowav_medium"],
                        t_fbeep,
                        final_audio_duration,
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
                        final_audio_duration - load_screen
                    key, rt = exp.keyboard.wait_char(
                        [setting["INDEX_BUTTON"], setting["MIDDLE_BUTTON"]],
                        duration=remaining_duration_feedback)
                    if rt is None:
                        RT = -1
                        feedback_rt = None
                    else:
                        RT = rt
                        feedback_rt = load_screen + rt
                    if 0 <= RT <= remaining_duration_feedback:
                        # Remove Questionnaire screen and display
                        # baseline fixation cross
                        tfix = t0.time
                        fixcross2.present()
                        load_fixcross = t0.time - tfix
                        if kind != 'behavioral':
                            exp.clock.wait(
                                remaining_duration_feedback - rt -
                                load_fixcross,
                                process_control_events=True)
                        else:
                            exp.clock.wait(0, process_control_events=True)
                    # Calculate duration of the feedback period
                    feedback_duration = t0.time - t_feedback

                    # *****************************************
                    # print('Real Final Beep + Feedback Period is: ',
                    #       t0.time - t_fbeep)
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
                        t0.time - t_fbeep,
                        feedback_rt,
                        key])

                    if rt is None:
                        answers.append(None)
                        # print('Real rt is: ', None)
                    else:
                        answers.append(key)
                        # print('Real rt is: ',
                        #       final_audio_duration + feedback_rt)
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


def audio_notemporal(protocol_ini, spec, exp, kind='training', t0=None,
                     tlast=None, auto=None, score=None):
    # %%
    # ======================== LOAD CONFIG.INI FILE ====================
    setting = load_config(protocol_ini)

    # %%
    # ==================== DEFINE AND PRELOAD SOME STIMULI =============
    fixcross1, fixcross2, fixcross3 = fixcrosses(setting, spec)
    low_beep, medium_beep, high_beep = audio_stim(setting)
    text_end_run, text_end_session = _txt_message(setting, spec)

    fixcross1.preload()
    fixcross2.preload()
    fixcross3.preload()

    low_beep.preload()
    medium_beep.preload()
    high_beep.preload()

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

    # Start audio system
    control.start_audiosystem()

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
        _load_inputs(setting, 'notemp_dir', subject_id, session_id, 'audio')

    # %%
    # ====================== EXPERIMENTAL DESIGN =======================
    task_id = _audio_design(setting, n_block, exp, inputs_filenames,
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
            # Start at any run number
            block_no = b + start_block
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
                    for i, interval in enumerate(intervals, 1):
                        # ################# AUDIO BEEP #################
                        t_beep = t0.time
                        # Display audio stim
                        medium_beep.present()
                        # Display trial fixation cross
                        t_fix3 = t0.time
                        fixcross3.present()
                        load_fixcross3 = t0.time - t_fix3
                        exp.clock.wait(setting["stim_duration"] -
                                       load_fixcross3,
                                       process_control_events=True)
                        # Calculate duration of the audio condition
                        audio_duration = t0.time - t_beep
                        # Log file registry for the current trial
                        exp.data.add([
                            session_id,
                            block_no+1,
                            trial_number,
                            trial.get_factor(
                                setting["var_names_notemporal"][1]),
                            setting["audiowav_medium"],
                            t_beep,
                            audio_duration,
                            '-',
                            '-',
                            '-',
                            '-'])
                        # ################# INTERVAL ###################
                        t_interval = t0.time
                        # Display only fixation cross
                        exp.clock.wait(interval - audio_duration,
                                       process_control_events=True)

                        # Calculate the real duration of the interval
                        interval_clock_duration = t0.time - t_interval

                        # *****************************************
                        # print(trial.get_factor(
                        #     setting["var_names_notemporal"][1]))
                        # print('Isi', i, 'is: ', interval)
                        # print('Real Isi is: ', t0.time - t_beep)
                        # *****************************************

                        # Log file registry for the current trial
                        exp.data.add([
                            session_id,
                            block_no+1,
                            trial_number,
                            trial.get_factor(
                                setting["var_names_notemporal"][1]),
                            setting["var_names_notemporal"][i+1],
                            t_interval,
                            interval_clock_duration,
                            interval,
                            t0.time - t_beep,
                            '-',
                            '-'])
                    # ################# TARGET AUDIO BEEP ##############
                    t_tbeep = t0.time
                    # Display target beep
                    if same_beep(trial.get_factor(
                            setting["var_names_notemporal"][7]),
                            setting["audiowav_high"]):
                        high_beep.present()
                    else:
                        assert same_beep(trial.get_factor(
                            setting["var_names_notemporal"][7]),
                            setting["audiowav_low"])
                        low_beep.present()
                    exp.clock.wait(setting["stim_duration"],
                                   process_control_events=True)
                    # Calculate duration of the target audio condition
                    target_audio_duration = t0.time - t_tbeep
                    # Log file registry for the current trial
                    exp.data.add([
                        session_id,
                        block_no+1,
                        trial_number,
                        trial.get_factor(setting["var_names_notemporal"][1]),
                        trial.get_factor(setting["var_names_notemporal"][7]),
                        t_tbeep,
                        target_audio_duration,
                        '-',
                        '-',
                        '-',
                        '-'])

                    targetstim.append(
                        trial.get_factor(setting["var_names_notemporal"][7]))
                    # ##################### FEEDBACK ###################
                    t_feedback = t0.time
                    # Wait for the feedback
                    remaining_duration_feedback = \
                        setting["feedback_duration"] + \
                        setting["stim_duration"] - \
                        target_audio_duration
                    key, rt = exp.keyboard.wait_char(
                        [setting["INDEX_BUTTON"], setting["MIDDLE_BUTTON"]],
                        duration=remaining_duration_feedback)
                    # Add extra-time to the feedback period if < 1s
                    # in order to assure constant trial duration
                    if rt is None:
                        RT = -1
                    else:
                        RT = rt
                    if 0 <= RT <= remaining_duration_feedback:
                        tsfix = t0.time
                        if key == setting["INDEX_BUTTON"]:
                            high_beep.present()
                        else:
                            assert key == setting["MIDDLE_BUTTON"]
                            low_beep.present()
                        fixcross2.present()
                        soundfix_duration = t0.time - tsfix
                        if kind != 'behavioral':
                            exp.clock.wait(
                                remaining_duration_feedback - rt -
                                soundfix_duration,
                                process_control_events=True)
                        else:
                            exp.clock.wait(0, process_control_events=True)
                    # Calculate duration of the feedback period
                    feedback_duration = t0.time - t_feedback

                    # *****************************************
                    # print('Real Target Beep + Feedback Period is: ',
                    #       t0.time - t_tbeep)
                    # print('rt is: ', rt)
                    # print('feedback_rt is: ', rt)
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
                        t0.time - t_tbeep,
                        rt,
                        key])

                    if rt is None:
                        rts.append(None)
                        answers.append(None)
                        # print('Real rt is: ', None)
                    else:
                        rts.append(target_audio_duration + rt)
                        answers.append(key)
                        # print('Real rt is: ', target_audio_duration + rt)
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
