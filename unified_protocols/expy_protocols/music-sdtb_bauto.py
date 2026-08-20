# -*- coding: utf-8 -*-
# ======================================================================
# Protocol for the Music Single-Domain-Task-Battery (Music-SDTB)
# ******** Session-plan version for behavioral sessions ********
#
# Author: Ana Luísa Pinho
#
# email: agrilopi@uwo.ca
#
# Created: July 2022
# Last Update: May 2026
#
# Compatibility: Expyriment 0.10.0 (Python 3.7.11)
# How to run the script:
# python music-sdtb_bauto.py <pc_type> <subject_number> <session_number> <line_number_from_session_plan>
# Example:
# python music-sdtb_bauto.py win 48 1 7
# ======================================================================

import os
import sys
import csv
import re

from expyriment import design, control, stimuli, io, misc
from confparser import load_config

from audio_protocols import (audio_production, audio_perception,
                             audio_notemporal)
from visual_protocols import(visual_production, visual_perception,
                             visual_notemporal)
from instructions import launch_instructions


CODE_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_from_code_dir(path):
    return os.path.abspath(os.path.join(CODE_DIR, path))


# %%
# ========== SET COMMAND-LINE ARGUMENTS TO BE PASSED TO THE SCRIPT =====

pc1 = 'lin'
pc2 = 'win'

assert(len(sys.argv) > 1), "No arg was introduced. " + \
                           "You must pass a valid arg to the script."
pc = sys.argv[1]
assert(pc in [pc1, pc2]), "Not valid first arg for PC id. " + \
                          "Please use either " + pc1 + " or " + pc2 + "."

subject_no = int(sys.argv[2])
session_no = int(sys.argv[3])
line = int(sys.argv[4])
assert(isinstance(subject_no, int) and isinstance(session_no, int) and
       isinstance(line, int)), \
       "Not valid second, third and fourth args for subject, session " + \
       "and task numbers, respectively. They must be integers."

# %%
# ========================== CALL .INI FILES ===========================
setting = load_config("menu_config.ini")

if pc == pc1:
    spec = load_config("pc1.ini")
else:
    assert pc == pc2
    spec = load_config("pc2.ini")

# %%
# ======================== SET DEVELOPMENT MODE ========================
control.set_develop_mode(False)

# Size of window in dev mode
control.defaults.window_size = tuple(list(map(int, spec["devwin_size"]))) 

# %%
# ========================== AUDIO SETTINGS ============================
control.defaults.audiosystem_bit_depth = -16  # Default: -16
control.defaults.audiosystem_buffer_size = 2048  # Default: 2048
control.defaults.audiosystem_sample_rate = 44100  # Default: 44100

# %%
# ========================= VISUAL SETTINGS ============================
control.defaults.open_gl=2

# %%
# ========================== SET DEFAULT KEYS ==========================
# control.defaults.pause_key = misc.constants.K_s
control.defaults.quit_key = misc.constants.K_ESCAPE

# %%
# ============================== RUN ===================================

sessplan_path = os.path.join(
    resolve_from_code_dir(load_config("behavsess_config.ini")["inputs_root"]),
    'sub-%02d' % subject_no,
    'ses-%02d' % session_no,
    'plan_sub-%02d' % subject_no + '_ses-%02d' % session_no + '.tsv')
sessparam = re.match('.*plan_sub-(.*)_ses-(.*).tsv',
                     sessplan_path).groups()

sessplan = [i[0] for i in csv.reader(open(sessplan_path), delimiter='\t')]
sessplan = sessplan[line-1:]
for sess in sessplan:
    runparam = re.match('(.*)_run-(.*)', sess).groups()
    dic_sessplan = {'subject': int(sessparam[0]), 'session': int(sessparam[1]),
                    'nrun': int(runparam[1])}

    # %%
    # ========================== INITIALIZATION ============================
    #
    # (1) Present the startup screen with the countdown;
    # (2) Start an experimental clock, create the screen;
    # (3) Create an event file;
    # (4) Present "Preparing experiment"
    #
    # ======================================================================
    exp = design.Experiment(
        name='music-sdtb',
        foreground_colour=tuple(list(map(int, setting["black"]))),
        background_colour=tuple(list(map(int, setting["gray"]))))

    control.initialize(exp)

    # %%
    #============= PRELOAD TEXT SCREEN WITH UPCOMING PROTOCOL ==============

    audioprod_stxt = stimuli.TextLine(
        'Audio Production',
        text_size=spec["task_name_size"],
        text_colour=tuple(list(map(int, setting["dark_purple"]))),
        background_colour=tuple(list(map(int, setting["gray"]))))

    audiopercep_stxt = stimuli.TextLine(
        'Audio Perception',
        text_size=spec["task_name_size"],
        text_colour=tuple(list(map(int, setting["dark_purple"]))),
        background_colour=tuple(list(map(int, setting["gray"]))))

    audiontfd_stxt = stimuli.TextLine(
        'Audio NTFD',
        text_size=spec["task_name_size"],
        text_colour=tuple(list(map(int, setting["dark_purple"]))),
        background_colour=tuple(list(map(int, setting["gray"]))))

    visualprod_stxt = stimuli.TextLine(
        'Visual Production',
        text_size=spec["task_name_size"],
        text_colour=tuple(list(map(int, setting["dark_purple"]))),
        background_colour=tuple(list(map(int, setting["gray"]))))

    visualpercep_stxt = stimuli.TextLine(
        'Visual Perception',
        text_size=spec["task_name_size"],
        text_colour=tuple(list(map(int, setting["dark_purple"]))),
        background_colour=tuple(list(map(int, setting["gray"]))))

    visualntfd_stxt = stimuli.TextLine(
        'Visual NTFD',
        text_size=spec["task_name_size"],
        text_colour=tuple(list(map(int, setting["dark_purple"]))),
        background_colour=tuple(list(map(int, setting["gray"]))))

    audioprod_stxt.preload()
    audiopercep_stxt.preload()
    audiontfd_stxt.preload()
    visualprod_stxt.preload()
    visualpercep_stxt.preload()
    visualntfd_stxt.preload()

    nrun_stxt = stimuli.TextLine(
        'Run %d' % int(runparam[1]),
        text_size=spec["task_name_size"],
        text_colour=tuple(list(map(int, setting["dark_purple"]))),
        background_colour=tuple(list(map(int, setting["gray"]))))
    nrun_stxt.preload()

    # %%
    #======================= SELECT TASK ===============================

    if runparam[0] == 'audio_production':
        audioprod_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        nrun_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        audio_production("behavsess_config.ini", spec, exp, kind='behavioral',
                         auto=dic_sessplan)
    elif runparam[0] == 'audio_perception':
        audiopercep_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        nrun_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        audio_perception("behavsess_config.ini", spec, exp, kind='behavioral',
                         auto=dic_sessplan)
    elif runparam[0] == 'audio_notemporal':
        audiontfd_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        nrun_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        audio_notemporal("behavsess_config.ini", spec, exp, kind='behavioral',
                         auto=dic_sessplan)
    elif runparam[0] == 'visual_production':
        visualprod_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        nrun_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        visual_production("behavsess_config.ini", spec, exp, kind='behavioral',
                          auto=dic_sessplan)
    elif runparam[0] == 'visual_perception':
        visualpercep_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        nrun_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        visual_perception("behavsess_config.ini", spec, exp, kind='behavioral',
                          auto=dic_sessplan)
    else:
        assert runparam[0] == 'visual_notemporal'
        visualntfd_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        nrun_stxt.present()
        exp.clock.wait(setting["autotxt_duration"],
                       process_control_events=True)
        visual_notemporal("behavsess_config.ini", spec, exp, kind='behavioral',
                          auto=dic_sessplan)

control.end(fast_quit=1)
