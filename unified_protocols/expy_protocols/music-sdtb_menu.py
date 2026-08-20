# -*- coding: utf-8 -*-
# ======================================================================
# Protocol for the Timing-Domain-Task-Battery (TDTB)
# Session-plan version for both behavioral and imaging sessions
#
# Author: Ana Luisa Pinho
# email: agrilopi@uwo.ca
#
# Created: February 2022
# Last Update: July 2026
#
# Compatibility: Expyriment 0.10.0 (Python 3.7.11)
# ======================================================================

import sys
import os

# Run from this script's own directory so that all relative paths
# (config .ini, instruction .tsv, audio_stim/*.wav) resolve regardless of
# the working directory the menu is launched from.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from expyriment import design, control, stimuli, io, misc
from confparser import load_config

from audio_protocols import (audio_production, audio_perception,
                             audio_notemporal)
from audio_protocols_explicit import (audio_production_explicit,
                                      audio_perception_explicit,
                                      audio_notemporal_explicit)
from visual_protocols import (visual_production, visual_perception,
                              visual_notemporal)
from visual_protocols_explicit import (visual_production_explicit,
                                       visual_perception_explicit,
                                       visual_notemporal_explicit)
from instructions import launch_instructions


class ScrollTextMenu(io.TextMenu):
    """io.TextMenu (Expyriment 0.10.0) with a top-anchored scroll window.

    The stock scrollable TextMenu keeps the selected item in the vertical
    centre of the window, so when the first item is selected the slots
    above it map to negative indices: they stay empty but still take
    vertical space, leaving a large blank gap below the heading. This
    override instead draws a contiguous window of items clamped to the
    list bounds (anchored at the top at the start, at the bottom at the
    end), so there is never a blank slot. Only the scroll branch differs
    from the base _redraw; the no-scroll branch is identical.
    """

    def _redraw(self, selected_item):
        if self._scroll_menu > 0:
            n = self._scroll_menu
        else:
            n = len(self._menu_items)
        self._canvas.clear_surface()
        if self._background_stimulus is not None:
            self._background_stimulus.plot(self._canvas)
        y_pos = int(((1.5 + n) * self._line_size[1]) +
                    (n * self._gap)) // 2
        self._heading.position = (self._position[0],
                                  y_pos + self._position[1])
        self._heading.plot(self._canvas)
        y_pos = y_pos - int(0.5 * self._line_size[1])

        if self._scroll_menu == 0:
            for cnt, item in enumerate(self._menu_items):
                y_pos -= (self._line_size[1] + self._gap)
                self._append_item(item, cnt == selected_item, y_pos)
                if cnt == selected_item:
                    self._frame.position = (0, y_pos)
        else:  # top-anchored, clamped scroll window (no blank slots)
            total = len(self._menu_items)
            window = self._scroll_menu + 1
            top = selected_item - self._scroll_menu // 2
            if top < 0:
                top = 0
            elif top > total - window:
                top = max(0, total - window)
            for cnt in range(top, top + window):
                y_pos -= (self._line_size[1] + self._gap)
                if 0 <= cnt < total:
                    self._append_item(self._menu_items[cnt],
                                      cnt == selected_item, y_pos)
                    if cnt == selected_item:
                        self._frame.position = (0, y_pos)

        if self._frame.line_width > 0:
            self._frame.plot(self._canvas)
        self._canvas.present()


# %%
# ========== SET COMMAND-LINE ARGUMENTS TO BE PASSED TO THE SCRIPT =====

pc1 = 'lin'
pc2 = 'win'

assert(len(sys.argv) > 1), "No arg was introduced. " + \
                           "You must pass a valid arg to the script."
pc = sys.argv[1]
assert(pc in [pc1, pc2]), \
    "Not valid arg for PC id. Please use either " + pc1 + " or " + pc2 + "."

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
# ========================== INITIALIZATION ============================
#
# (1) Present the startup screen with the countdown;
# (2) Start an experimental clock, create the screen;
# (3) Create an event file;
# (4) Present "Preparing experiment"
#
# ======================================================================
exp = design.Experiment(
    name='TDTB',
    foreground_colour=tuple(list(map(int, setting["black"]))),
    background_colour=tuple(list(map(int, setting["gray"]))))

control.initialize(exp)

# %%
# ============================== MENU ==================================
# Preset the menu

menu_options = [setting["instruct_prod"],
                setting["instruct_prod_explicit"],
                setting["instruct_percep"],
                setting["instruct_percep_explicit"],
                setting["instruct_notemp"],
                setting["instruct_notemp_explicit"],
                setting["instruct_notemp_rand"],
                setting["instruct_notemp_rand_explicit"],
                setting["prodAV_img"],
                setting["prodVA_img"],
                setting["percepAV_img"],
                setting["percepVA_img"],
                setting["notempAV_img"],
                setting["notempVA_img"],
                setting["audiprod_train"],
                setting["audiprod_train_explicit"],
                setting["audiprod_behav"],
                setting["audipercep_train"],
                setting["audipercep_train_explicit"],
                setting["audipercep_behav"],
                setting["audinotemp_train"],
                setting["audinotemp_train_explicit"],
                setting["audinotemp_behav"],
                setting["viprod_train"],
                setting["viprod_train_explicit"],
                setting["viprod_behav"],
                setting["vipercep_train"],
                setting["vipercep_train_explicit"],
                setting["vipercep_behav"],
                setting["vinotemp_train"],
                setting["vinotemp_train_explicit"],
                setting["vinotemp_behav"],
                setting["exit"]]

task_title = setting["protocol_title"]

# Use the next command line if you're running Expyriment vs. O.7.0 on
# Windows:
# menu_options = [s.decode('utf-8').encode('cp1252')
#                 for s in menu_options]
# task_title = task_title.decode('utf-8').encode('cp1252')

display_note = stimuli.TextLine(
    setting["note"], text_size=spec["mmtxtsize"],
    text_colour=tuple(list(map(int, setting["dark_purple"]))),
    position=tuple(list(map(int, spec["display_note_pos"]))))

menu = ScrollTextMenu(task_title, menu_options, width=1000,
                   text_size=spec["mmtxtsize"], gap=10, justification=0,
                   scroll_menu=spec["menu_scroll"],
                   background_colour=tuple(list(map(int, setting["gray"]))),
                   background_stimulus=display_note)

# Launch the menu (default_preselected_item = 'Auditory Production - is')
selected_option = menu.get(0)

# Call the functions according to the options selected in the menu
while True:
    # Launch option: "Instructions for Production Tasks"
    if selected_option == 0:
        launch_instructions("instructions_production.tsv",
                            "instructions_config.ini", spec, exp)

    # Launch option: "Instructions for Production Tasks with explicit instruction"
    elif selected_option == 1:
        launch_instructions("instructions_production_explicit.tsv",
                            "instructions_config.ini", spec, exp)

    # Launch option: "Instructions for Perception Tasks"
    elif selected_option == 2:
        launch_instructions("instructions_perception.tsv",
                            "instructions_config.ini", spec, exp)

    # Launch option: "Instructions for Perception Tasks with explicit instruction"
    elif selected_option == 3:
        launch_instructions("instructions_perception_explicit.tsv",
                            "instructions_config.ini", spec, exp)

    # Launch option: "Instructions for No-Temporal FD Tasks"
    elif selected_option == 4:
        launch_instructions("instructions_notemporal.tsv",
                            "instructions_config.ini", spec, exp)

    # Launch option: "Instructions for No-Temporal FD Tasks with explicit instruction"
    elif selected_option == 5:
        launch_instructions("instructions_notemporal_explicit.tsv",
                            "instructions_config.ini", spec, exp)

    # Launch option: "Instructions for No-Temporal FD Tasks with Random Condition"
    elif selected_option == 6:
        launch_instructions("instructions_notemporal_withrandom.tsv",
                            "instructions_config.ini", spec, exp)

    # Launch option: "Instructions for No-Temporal FD Tasks with Random Condition with explicit instruction"
    elif selected_option == 7:
        launch_instructions("instructions_notemporal_withrandom_explicit.tsv",
                            "instructions_config.ini", spec, exp)

    # Launch option: "Production Audio/Visual - imaging"
    elif selected_option == 8:
        t0 = misc.Clock()
        print('Production')
        sess_aprod, run_aprod, scores, t_end = audio_production(
            "imagingsess_config.ini", spec, exp, kind='imaging', t0=t0)
        vprod_sessrun = {'session': sess_aprod, 'nrun': run_aprod}
        visual_production("imagingsess_config.ini", spec, exp, kind='imaging',
                          t0=t0, tlast=t_end, auto=vprod_sessrun, score=scores)
        break

    # Launch option: "Production Visual/Audio - imaging"
    elif selected_option == 9:
        t0 = misc.Clock()
        print('Production')
        sess_vprod, run_vprod, scores, t_end = visual_production(
            "imagingsess_config.ini", spec, exp, kind='imaging', t0=t0)
        aprod_sessrun = {'session': sess_vprod, 'nrun': run_vprod}
        audio_production("imagingsess_config.ini", spec, exp, kind='imaging',
                         t0=t0, tlast=t_end, auto=aprod_sessrun, score=scores)
        break

    # Launch option: "Perception Audio/Visual - imaging"
    elif selected_option == 10:
        t0 = misc.Clock()
        print('Perception')
        sess_apercep, run_apercep, scores, t_end = audio_perception(
            "imagingsess_config.ini", spec, exp, kind='imaging', t0=t0)
        vpercep_sessrun = {'session': sess_apercep, 'nrun': run_apercep}
        visual_perception("imagingsess_config.ini", spec, exp, kind='imaging',
                          t0=t0, tlast=t_end, auto=vpercep_sessrun,
                          score=scores)
        break

    # Launch option: "Perception Visual/Audio - imaging"
    elif selected_option == 11:
        t0 = misc.Clock()
        print('Perception')
        sess_vpercep, run_vpercep, scores, t_end = visual_perception(
            "imagingsess_config.ini", spec, exp, kind='imaging', t0=t0)
        apercep_sessrun = {'session': sess_vpercep, 'nrun': run_vpercep}
        audio_perception("imagingsess_config.ini", spec, exp, kind='imaging',
                          t0=t0, tlast=t_end, auto=apercep_sessrun,
                          score=scores)
        break

    # Launch option: "No-Temporal Feature Discrimination Audio/Visual - imaging"
    elif selected_option == 12:
        t0 = misc.Clock()
        print('NTFD')
        sess_antfd, run_antfd, scores, t_end = audio_notemporal(
            "imagingsess_config.ini", spec, exp, kind='imaging', t0=t0)
        vntfd_sessrun = {'session': sess_antfd, 'nrun': run_antfd}
        visual_notemporal("imagingsess_config.ini", spec, exp, kind='imaging',
                          t0=t0, tlast=t_end, auto=vntfd_sessrun, score=scores)
        break

    # Launch option: "No-Temporal Feature Discrimination Visual/Audio - imaging"
    elif selected_option == 13:
        t0 = misc.Clock()
        print('NTFD')
        sess_vntfd, run_vntfd, scores, t_end = visual_notemporal(
            "imagingsess_config.ini", spec, exp, kind='imaging', t0=t0)
        antfd_sessrun = {'session': sess_vntfd, 'nrun': run_vntfd}
        audio_notemporal("imagingsess_config.ini", spec, exp, kind='imaging',
                          t0=t0, tlast=t_end, auto=antfd_sessrun, score=scores)
        break

    # Launch option: "Auditory Production - training"
    elif selected_option == 14:
        audio_production("trainsess_config.ini", spec, exp)

    # Launch option: "Auditory Production - explicit training"
    elif selected_option == 15:
        audio_production_explicit("trainsess_config.ini", spec, exp)

    # Launch option: "Auditory Production - behavioral"
    elif selected_option == 16:
        audio_production("behavsess_config.ini", spec, exp, kind='behavioral')

    # Launch option: "Auditory Perception - training"
    elif selected_option == 17:
        audio_perception("trainsess_config.ini", spec, exp)

    # Launch option: "Auditory Perception - explicit training"
    elif selected_option == 18:
        audio_perception_explicit("trainsess_config.ini", spec, exp)

    # Launch option: "Auditory Perception - behavioral"
    elif selected_option == 19:
        audio_perception("behavsess_config.ini", spec, exp, kind='behavioral')

    # Launch option: "Auditory No-Temporal Feature Discrimination - training"
    elif selected_option == 20:
        audio_notemporal("trainsess_config.ini", spec, exp)

    # Launch option: "Auditory No-Temporal FD - explicit training"
    elif selected_option == 21:
        audio_notemporal_explicit("trainsess_config.ini", spec, exp)

    # Launch option: "Auditory No-Temporal Feature Discrimination - behavioral"
    elif selected_option == 22:
        audio_notemporal("behavsess_config.ini", spec, exp, kind='behavioral')

    # Launch option: "Visual Production - training"
    elif selected_option == 23:
        visual_production("trainsess_config.ini", spec, exp)

    # Launch option: "Visual Production - explicit training"
    elif selected_option == 24:
        visual_production_explicit("trainsess_config.ini", spec, exp)

    # Launch option: "Visual Production - behavioral"
    elif selected_option == 25:
        visual_production("behavsess_config.ini", spec, exp, kind='behavioral')

    # Launch option: "Visual Perception - training"
    elif selected_option == 26:
        visual_perception("trainsess_config.ini", spec, exp)

    # Launch option: "Visual Perception - explicit training"
    elif selected_option == 27:
        visual_perception_explicit("trainsess_config.ini", spec, exp)

    # Launch option: "Visual Perception - behavioral"
    elif selected_option == 28:
        visual_perception("behavsess_config.ini", spec, exp, kind='behavioral')

    # Launch option: "Visual No-Temporal Feature Discrimination - training"
    elif selected_option == 29:
        visual_notemporal("trainsess_config.ini", spec, exp)

    # Launch option: "Visual No-Temporal FD - explicit training"
    elif selected_option == 30:
        visual_notemporal_explicit("trainsess_config.ini", spec, exp)

    # Launch option: "Visual No-Temporal Feature Discrimination - behavioral"
    elif selected_option == 31:
        visual_notemporal("behavsess_config.ini", spec, exp, kind='behavioral')

    # Launch option: "Exit"
    else:
        break

    # Goes back to the main menu after quitting any option
    # (except for the last one)
    if selected_option < (len(menu_options) - 1):
        exp = design.Experiment(
            "TDTB",
            foreground_colour=tuple(list(map(int, setting["black"]))),
            background_colour=tuple(list(map(int, setting["gray"]))))
        control.initialize(exp)
        menu_options = [setting["instruct_prod"],
                        setting["instruct_prod_explicit"],
                        setting["instruct_percep"],
                        setting["instruct_percep_explicit"],
                        setting["instruct_notemp"],
                        setting["instruct_notemp_explicit"],
                        setting["instruct_notemp_rand"],
                        setting["instruct_notemp_rand_explicit"],
                        setting["prodAV_img"],
                        setting["prodVA_img"],
                        setting["percepAV_img"],
                        setting["percepVA_img"],
                        setting["notempAV_img"],
                        setting["notempVA_img"],
                        setting["audiprod_train"],
                        setting["audiprod_train_explicit"],
                        setting["audiprod_behav"],
                        setting["audipercep_train"],
                        setting["audipercep_train_explicit"],
                        setting["audipercep_behav"],
                        setting["audinotemp_train"],
                        setting["audinotemp_train_explicit"],
                        setting["audinotemp_behav"],
                        setting["viprod_train"],
                        setting["viprod_train_explicit"],
                        setting["viprod_behav"],
                        setting["vipercep_train"],
                        setting["vipercep_train_explicit"],
                        setting["vipercep_behav"],
                        setting["vinotemp_train"],
                        setting["vinotemp_train_explicit"],
                        setting["vinotemp_behav"],
                        setting["exit"]]

        task_title = setting["protocol_title"]

        menu_options = [s for s in menu_options]

        menu = ScrollTextMenu(
            task_title, menu_options, width=1000, text_size=spec["mmtxtsize"],
            gap=10, justification=0,
            scroll_menu=spec["menu_scroll"],
            background_colour=tuple(list(map(int, setting["gray"]))),
            background_stimulus=display_note)
        selected_option = menu.get(0)

control.end(fast_quit=1)