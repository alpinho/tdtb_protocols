# -*- coding: utf-8 -*-

import os
import glob
import csv
import re

from expyriment import stimuli, io, misc
from confparser import load_config


CODE_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_from_code_dir(path):
    return os.path.abspath(os.path.join(CODE_DIR, path))


def same_beep(name_1, name_2):
    # Compare two beep names ignoring any decoration of the filename.
    # The input files store the beep as e.g. 'beep_220hz', whereas the .ini
    # files store the name of the file actually loaded, e.g.
    # 'beep_220hz_mono'. Both refer to the same beep, so the comparison is
    # made on the tone frequency alone.
    return _beep_key(name_1) == _beep_key(name_2)


def _beep_key(name):
    name = str(name).strip().lower()
    frequency = re.search(r'(\d+) *hz', name)
    return frequency.group(1) if frequency else name


def _launch_sess(setting, spec, exp):
    # Wait 5 seconds in order to launch input text screen
    exp.keyboard.wait(duration=5000)

    # Create text input box
    ti = io.TextInput(
        message='Number of the Session:', message_text_size=24,
        message_colour=(150, 0, 255),
        user_text_colour=tuple(list(map(int, setting["dark_yellow"]))),
        ascii_filter=misc.constants.K_ALL_DIGITS,
        background_colour=tuple(list(map(int, setting["black"]))),
        frame_colour=tuple(list(map(int, setting["dark_gray"]))))

    # Load user's input
    while True:
        sb = ti.get('1')
        # If string is empty
        if not sb:
            warning_message1 = stimuli.TextLine(
                setting["wm1"], text_size=spec["txtsize"],
                text_colour=tuple(list(map(int, setting["black"]))))
            warning_message1.present()
            exp.keyboard.wait(misc.constants.K_RETURN, duration=5000)
            continue
        else:
            session_number = int(sb)
            break

    return session_number


def _load_inputs(setting, main_dir, subject_number, session_number,
                 modality_dir):
    # Define the pathway of the inputs directory
    inputs_root = _resolve_from_code_dir(setting["inputs_root"])
    if setting['sesstype'] in ['imaging session', 'behavioral session']:
        sess_path = os.path.join(
            inputs_root,
            'sub-%02d' % int(subject_number),
            'ses-%02d' % int(session_number))
        inputs_path = os.path.join(
            sess_path,
            setting[main_dir] + '_sub-%02d' % int(subject_number) + \
            '_ses-%02d' % int(session_number),
            modality_dir)
        sessplan = glob.glob(os.path.join(sess_path, "*.tsv"))[0]
        sesslist = [s for s in csv.reader(open(sessplan), delimiter='\t')]

        # Fix different behaviours of csvreader between Windows and Linux
        sesslist = [x for x in sesslist if x]

        last_run = sesslist[-1][0]
    else:
        assert setting['sesstype'] == 'training session'
        inputs_path = os.path.join(inputs_root, setting[main_dir],
                                   modality_dir)
        last_run = None
    # List input csv files
    inputs_filenames = glob.glob(os.path.join(inputs_path, "*.tsv"))
    inputs_filenames.sort()

    # Define number of runs
    n_block = len(inputs_filenames)

    return inputs_filenames, n_block, last_run


def _launch_run(setting, spec, n_block, exp):
    # Wait 5 seconds in order to launch input text screen
    exp.keyboard.wait(duration=5000)

    # Create text input box
    ti = io.TextInput(
        message='Number of the Run:', message_text_size=24,
        message_colour=(150, 0, 255),
        user_text_colour=tuple(list(map(int, setting["dark_yellow"]))),
        ascii_filter=misc.constants.K_ALL_DIGITS,
        background_colour=tuple(list(map(int, setting["black"]))),
        frame_colour=tuple(list(map(int, setting["dark_gray"]))))

    # Load user's input
    while True:
        sb = ti.get('1')
        # If string is empty
        if not sb:
            warning_message1 = stimuli.TextLine(
                setting["wm1"], text_size=spec["txtsize"],
                text_colour=tuple(list(map(int, setting["black"]))))
            warning_message1.present()
            exp.keyboard.wait(misc.constants.K_RETURN, duration=5000)
            continue
        # If run (aka block) number introduced is higher than the number
        # of runs
        elif int(sb) > n_block:
            warning_message2 = stimuli.TextLine(
                setting["wm2"], text_size=spec["txtsize"],
                text_colour=tuple(list(map(int, setting["black"]))))
            warning_message2.present()
            exp.keyboard.wait(misc.constants.K_RETURN, duration=5000)
            continue
        else:
            start_block = int(sb)
            break

    return start_block


def fixcrosses(setting, spec):
    # TTL cross
    fixcross1 = stimuli.FixCross(
        size=tuple(list(map(int, spec["fixcross_size"]))),
        line_width=spec["fixcross_thickness"],
        colour=tuple(list(map(int, setting["dark_purple"]))))

    # Baseline cross
    fixcross2 = stimuli.FixCross(
        size=tuple(list(map(int, spec["fixcross_size"]))),
        line_width=spec["fixcross_thickness"],
        colour=tuple(list(map(int, setting["black"]))))

    # Trial cross
    fixcross3 = stimuli.FixCross(
        size=tuple(list(map(int, spec["fixcross_size"]))),
        line_width=spec["fixcross_thickness"],
        colour=tuple(list(map(int, setting["dark_gray"]))))

    return fixcross1, fixcross2, fixcross3


def audio_stim(setting):
    audistim_low = stimuli.Audio(
        setting["audiowav_path"] + "/" +
        setting["audiowav_low"] + "." +
        setting["ext"])
    audistim_medium = stimuli.Audio(
        setting["audiowav_path"] + "/" +
        setting["audiowav_medium"] + "." +
        setting["ext"])
    audistim_high = stimuli.Audio(
        setting["audiowav_path"] + "/" +
        setting["audiowav_high"] + "." +
        setting["ext"])

    return audistim_low, audistim_medium, audistim_high


def visual_stim(setting, spec):
    vstim_trialrect = stimuli.Rectangle(
        tuple(list(map(int, spec["rectangle_size"]))),
        colour=tuple(list(map(int, setting["dark_gray"]))),
        position=(0, 0))

    vstim_targetcirc = stimuli.Circle(
        spec["circle_radius"],
        colour=tuple(list(map(int, setting["dark_gray"]))),
        position=(0, 0))

    vstim_targettri = stimuli.Shape(
        vertex_list=misc.geometry.vertices_triangle(
            setting["triangle_angle"],
            spec["triangle_length1"],
            spec["triangle_length2"]),
        colour=tuple(list(map(int, setting["dark_gray"]))),
        position=tuple(list(map(int, spec["triangle_pos"]))))

    return vstim_trialrect, vstim_targetcirc, vstim_targettri


def panel_stim(setting, spec):
    panel_feedback_percep = stimuli.TextBox(
        str(''.join((
            'Longer or Shorter?',
            '\n\n\n\n\n\n\n',
            'Longer (Index Finger)',
            '                            ',
            'Shorter (Middle Finger)'))),
        tuple(list(map(int, spec["box_size"]))),
        position=tuple(list(map(int, spec["box_pos"]))),
        text_size=spec["box_txtsize"],
        text_colour=tuple(list(map(int, setting["black"]))))

    return panel_feedback_percep


def production_rating(setting, reaction_time, standard_time, score=None):
    score_list = []
    for rtt, stt in zip(reaction_time, standard_time):
        if rtt is None:
            score_val = None
        else:
            score_val = rtt / stt
        if score_val is None:
            score_list.append(0)
        elif setting["min_prod"] < score_val < setting["max_prod"]:
            score_list.append(1)
        else:
            score_list.append(0)

    if score is not None:
        score_list.extend(score)

    final_score = '{0:.2f}'.format(
        (score_list.count(1) / len(score_list)) * 100)

    return final_score, score_list


def perception_rating(setting, key_press, standard_time, perception_time,
                      score=None):
    score_list = []
    for kpr, stt, pct in zip(key_press, standard_time, perception_time):
        if kpr == setting["INDEX_BUTTON"]:
            if pct > stt:
                score_list.append(1)
            else:
                score_list.append(0)
        elif kpr == setting["MIDDLE_BUTTON"]:
            if pct < stt:
                score_list.append(1)
            else:
                score_list.append(0)
        else:
            score_list.append(0)

    if score is not None:
        score_list.extend(score)

    final_score = '{0:.2f}'.format(
        (score_list.count(1) / len(score_list)) * 100)

    return final_score, score_list


def notemporal_rating(setting, target, reaction_time, key_press, score=None):
    score_list = []
    for trg, rtt, kpr in zip(target, reaction_time, key_press):
        if kpr == setting["INDEX_BUTTON"]:
            if (same_beep(trg, setting["audiowav_high"]) or
                trg == 'circle') and \
               setting["min_ntfd"] < int(rtt) < setting["max_ntfd"]:
                score_list.append(1)
            else:
                score_list.append(0)
        elif kpr == setting["MIDDLE_BUTTON"]:
            if (same_beep(trg, setting["audiowav_low"]) or
                trg == 'triangle') and \
               setting["min_ntfd"] < int(rtt) < setting["max_ntfd"]:
                score_list.append(1)
            else:
                score_list.append(0)
        else:
            score_list.append(0)

    if score is not None:
        score_list.extend(score)

    final_score = '{0:.2f}'.format(
        (score_list.count(1) / len(score_list)) * 100)

    return final_score, score_list


def _display_score_run(setting, spec, score):
    score_txt = 'Your score is ' + score + '%.'
    score_obj = stimuli.TextLine(
        score_txt, text_size=spec["txtsize"],
        text_colour=tuple(list(map(int, setting["dark_yellow"]))))

    return score_obj


def _txt_message(setting, spec):
    # Text for end of session
    txt_end_run = stimuli.TextLine(
        setting["text_end_run"], text_size=spec["txtsize"],
        text_colour=tuple(list(map(int, setting["dark_yellow"]))))

    # Text for end of experiment
    txt_end_session = stimuli.TextBox(
        str(''.join((setting["text_end_exp_one"], '\n\n',
                     setting["text_end_exp_two"]))),
        (1000, 1000), position=(0, -400), text_size=spec["txtsize"],
        text_colour=tuple(list(map(int, setting["dark_yellow"]))))

    return txt_end_run, txt_end_session


def _next_run(lrun, task_id, nblock, sblock, txt_end_session,
              txt_end_run, exp):
    if lrun is not None:
        # For imaging and behavioral sessions
        task_name = re.match('(.*)_run-(.*)', lrun).groups()[0]
        run_batch = int(
            re.match('(.*)_run-(.*)', lrun).groups()[1])
        if task_name.endswith('_random'):
            task_name = task_name[:-7]
        if task_id == task_name and run_batch == nblock and \
           run_batch == sblock+1:
            # Present "End of Session" message
            txt_end_session.present()
        else:
            # For training session
            # Present "End of Run" message
            txt_end_run.present()
    else:
        # Present "End of Run" message
        txt_end_run.present()
    # Go back to the main menu when pressing "ENTER"
    key, _ = exp.keyboard.wait(keys=[misc.constants.K_RETURN,
                                     misc.constants.K_KP_ENTER])

    return key


def wait(t0, fixcross2, exp, setting, session_id):
    tb_fix = t0.time
    fixcross2.present()
    load_fixcross2 = t0.time - tb_fix
    # Wait WAIT seconds before the beginning of the trial
    exp.clock.wait(setting["WAIT"] - load_fixcross2,
                   process_control_events=True)
    # Calculate the real duration of the interval
    wait_real_duration = t0.time - tb_fix
    # Log file registry for the current trial
    exp.data.add([session_id,
                  '-',
                  '-',
                  'final_baseline',
                  '-',
                  tb_fix,
                  wait_real_duration,
                  '-',
                  '-',
                  '-',
                  '-'])


def baseline_bt(t0, exp, setting, tlast, session_id):
    t_bt = t0.time
    exp.clock.wait(
        setting["between_tasks_duration"] - t_bt + tlast,
        process_control_events=True)
    # Calculate the real duration of the interval
    bt_real_duration = t0.time - tlast
    # Log file registry for the current trial
    exp.data.add([session_id,
                  '-',
                  '-',
                  'baseline',
                  '-',
                  tlast,
                  bt_real_duration,
                  '-',
                  '-',
                  '-',
                  '-'])
