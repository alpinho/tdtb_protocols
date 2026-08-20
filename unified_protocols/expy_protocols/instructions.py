# -*- coding: utf-8 -*-

import os
import re
import csv
import numpy as np

from confparser import load_config
from expyriment import stimuli, misc

from utils import audio_stim, visual_stim, fixcrosses, panel_stim


def flatten(li):
    return sum(([x] if not isinstance(x, list) else flatten(x)
                for x in li), [])


# Mapping between a slide's "action" and the interactive demo/trial it runs.
# Two tsv layouts are supported, auto-detected from the header:
#   * legacy single-column ("slide"): a slide's action is derived from its
#     absolute index via _index_action(), reproducing the original behaviour
#     (demos at 4/6/9/11, interactive trials at 14/15).
#   * tagged two-column ("tag" + "text"): the action is read straight from
#     the tag column, so slides can be inserted, removed or reordered without
#     shifting anything. An empty tag is just a plain text slide.
_COMMON_ACTIONS = {4: 'beep_iso', 6: 'flash_iso', 9: 'beep_beat',
                   11: 'flash_beat'}
_TRIAL_ACTIONS = {
    'production': {14: 'trial_prod_audio', 15: 'trial_prod_visual'},
    'perception': {14: 'trial_percep_audio', 15: 'trial_percep_visual'},
    'notemporal': {14: 'trial_ntfd_audio', 15: 'trial_ntfd_visual'},
    'notemporal_withrandom': {14: 'trial_ntfd_audio',
                              15: 'trial_ntfd_visual'},
}


def _index_action(category, ldx):
    """Legacy layout: derive a slide's action from its absolute index."""
    trials = _TRIAL_ACTIONS.get(category, {})
    if ldx in trials:
        return trials[ldx]
    return _COMMON_ACTIONS.get(ldx, '')


# ---------------------------------------------------------------------------
# Explicit-marking helpers for the interactive Beat-trial demos.
# In a Beat trial the interval BETWEEN pairs is a true 3X of the within-pair
# unit (base_unit). Following audio_protocols_explicit._isi_explicit and
# visual_protocols_explicit._isi_visual_explicit, that interval is split into
# n = interval // base_unit sub-intervals of length base_unit; every internal
# boundary (there are n - 1 of them) is marked by a soft beep (audio) or a
# small centred rectangle (visual). Onset-to-onset timing is preserved.
# ---------------------------------------------------------------------------
def _audio_beat_gap(exp, soft_beep, base_unit, n_sub):
    # The main (pair-ending) beep has already been presented by the caller.
    # First sub-interval follows that beep with no marker.
    exp.clock.wait(base_unit, process_control_events=True)
    for _ in range(int(n_sub) - 1):
        if soft_beep is not None:
            soft_beep.present()
        exp.clock.wait(base_unit, process_control_events=True)


def _visual_beat_gap(exp, fixcross3, small_rect, base_unit, flash_dur, n_sub):
    # The main (pair-ending) flash has already been shown by the caller.
    # First sub-interval: fixation cross for the remainder of base_unit.
    fixcross3.present()
    exp.clock.wait(base_unit - flash_dur, process_control_events=True)
    for _ in range(int(n_sub) - 1):
        if small_rect is not None:
            small_rect.present()
            exp.clock.wait(flash_dur, process_control_events=True)
            fixcross3.present()
            exp.clock.wait(base_unit - flash_dur, process_control_events=True)
        else:
            exp.clock.wait(base_unit, process_control_events=True)


def _fit_textbox(line, bsize, text_size):
    # Build a TextBox for `line`, shrinking the font only if the word-wrapped
    # text would be too tall for `bsize` (Expyriment raises rather than clips).
    # Slides that already fit at the configured size are left unchanged.
    ts = int(text_size)
    while ts >= 20:
        text_display = stimuli.TextBox(line, bsize, text_size=ts)
        try:
            text_display.preload()
        except Exception:
            ts -= 2
            continue
        return text_display
    return stimuli.TextBox(line, bsize, text_size=ts)


def launch_instructions(instructions_file, instructions_ini, spec, exp):
    # %%
    # ======================== LOAD CONFIG.INI FILE ====================
    setting = load_config(instructions_ini)

    # %%
    # ==================== DEFINE AND PRELOAD SOME STIMULI =============
    low_beep, medium_beep, high_beep = audio_stim(setting)
    low_beep.preload()
    medium_beep.preload()
    high_beep.preload()

    # Explicit-marking stimuli for the Beat-trial demos. Loaded defensively so
    # that the standard instructions still run if the .ini lacks the soft-beep
    # key or the spec lacks the small-rectangle size.
    soft_beep = None
    if "audiowav_soft" in setting:
        soft_beep = stimuli.Audio(setting["audiowav_path"] + "/" +
                                  setting["audiowav_soft"] + "." +
                                  setting["ext"])
        soft_beep.preload()
    small_rect = None
    if "small_rectangle_size" in spec:
        small_rect = stimuli.Rectangle(
            tuple(list(map(int, spec["small_rectangle_size"]))),
            colour=tuple(list(map(int, setting["dark_gray"]))),
            position=(0, 0))
        small_rect.preload()

    trial_rect, target_circ, target_tri = visual_stim(setting, spec)
    target_circ.preload()
    target_tri.preload()

    _, _, fixcross3 = fixcrosses(setting, spec)
    fixcross3.preload()

    screen_feedback_percep = panel_stim(setting, spec)
    screen_feedback_percep.preload()

    positive_feedback_prodntfd = stimuli.TextBox(
        str(''.join((setting["line1"], '\n\n',
                     setting["line2"]))),
        tuple(list(map(int, spec["bsize"]))),
        position=tuple(list(map(int, spec["fbox_pos"]))),
        text_size=spec["itxtsize"],
        text_colour=tuple(list(map(int, setting["blue"]))))
    positive_feedback_prodntfd.preload()

    negative_feedback_production = stimuli.TextBox(
        str(''.join((setting["line4"], '\n\n',
                     setting["line11"]))),
        tuple(list(map(int, spec["bsize"]))),
        position=tuple(list(map(int, spec["fbox_pos"]))),
        text_size=spec["itxtsize"],
        text_colour=tuple(list(map(int, setting["dark_red"]))))
    negative_feedback_production.preload()

    positive_feedback_perception = stimuli.TextBox(
        str(''.join((setting["line1"], '\n\n',
                     setting["line3"]))),
        tuple(list(map(int, spec["bsize"]))),
        position=tuple(list(map(int, spec["fbox_pos"]))),
        text_size=spec["itxtsize"],
        text_colour=tuple(list(map(int, setting["blue"]))))
    positive_feedback_perception.preload()

    negative_feedback_percepntfd = stimuli.TextBox(
        str(''.join((setting["line5"], '\n\n',
                     setting["line11"]))),
        tuple(list(map(int, spec["bsize"]))),
        position=tuple(list(map(int, spec["fbox_pos"]))),
        text_size=spec["itxtsize"],
        text_colour=tuple(list(map(int, setting["dark_red"]))))
    negative_feedback_percepntfd.preload()

    negative_feedback_ntfd1 = stimuli.TextBox(
        str(''.join((setting["line6"], '\n\n',
                     setting["line8"]))),
        tuple(list(map(int, spec["bsize"]))),
        position=tuple(list(map(int, spec["fbox_pos"]))),
        text_size=spec["itxtsize"],
        text_colour=tuple(list(map(int, setting["dark_red"]))))
    negative_feedback_ntfd1.preload()

    negative_feedback_ntfd2 = stimuli.TextBox(
        str(''.join((setting["line7"], '\n\n',
                     setting["line8"]))),
        tuple(list(map(int, spec["bsize"]))),
        position=tuple(list(map(int, spec["fbox_pos"]))),
        text_size=spec["itxtsize"],
        text_colour=tuple(list(map(int, setting["dark_red"]))))
    negative_feedback_ntfd2.preload()

    negative_feedback_ntfd3 = stimuli.TextBox(
        str(''.join((setting["line9"], '\n\n',
                     setting["line11"]))),
        tuple(list(map(int, spec["bsize"]))),
        position=tuple(list(map(int, spec["fbox_pos"]))),
        text_size=spec["itxtsize"],
        text_colour=tuple(list(map(int, setting["dark_red"]))))
    negative_feedback_ntfd3.preload()

    negative_feedback_ntfd4 = stimuli.TextBox(
        str(''.join((setting["line10"], '\n\n',
                     setting["line11"]))),
        tuple(list(map(int, spec["bsize"]))),
        position=tuple(list(map(int, spec["fbox_pos"]))),
        text_size=spec["itxtsize"],
        text_colour=tuple(list(map(int, setting["dark_red"]))))
    negative_feedback_ntfd4.preload()

    # %%
    # ================================ RUN =============================
    _m = re.match('instructions_(.*).tsv', instructions_file)
    category = _m.groups()[0] if _m else ''
    with open(instructions_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        rows = [row for row in reader]
    header = rows[0] if rows else []
    rows = rows[1:]
    # Auto-detect layout: a leading 'tag'/'action' column selects per-slide
    # (tag-driven) dispatch; otherwise the legacy index-driven behaviour.
    tagged = len(header) >= 2 and header[0].strip().lower() in ('tag', 'action')
    if tagged:
        actions = [row[0].strip() if len(row) > 0 else '' for row in rows]
        instructions = [row[1] if len(row) > 1 else '' for row in rows]
    else:
        actions = None
        instructions = flatten(rows)
    # Initialization of variable containing the value of the key pressed
    found_key = 0
    # While "h" key to return to main menu is not pressed...
    while not found_key == misc.constants.K_h:
        # Read the instructions file, line by line
        ldx = 0
        while ldx < len(instructions):
            line = instructions[ldx]
            line = line.replace('\\n', '\n')
            text_display = _fit_textbox(
                line,
                tuple(list(map(int, spec["bsize"]))),
                spec["itxtsize"])
            text_display.present()

            if tagged:
                action = actions[ldx]
            else:
                action = _index_action(category, ldx)

            if action == 'beep_iso':
                medium_beep.present()
                exp.clock.wait(539, process_control_events=True)
                medium_beep.present()
            elif action == 'flash_iso':
                text_display.present()
                trial_rect.position = (0, spec["rect_yrepos"])
                trial_rect.preload()
                for i, interval in enumerate([80, 459, 80]):
                    if i % 2 == 0:
                        trial_rect.present(clear=False, update=True)
                        exp.clock.wait(80, process_control_events=True)
                    else:
                        text_display.present()
                        exp.clock.wait(interval, process_control_events=True)
                text_display.present()
            elif action == 'beep_beat':
                for interval in [539, 1457, 539]:
                    medium_beep.present()
                    exp.clock.wait(interval, process_control_events=True)
                medium_beep.present()
            elif action == 'flash_beat':
                text_display.present()
                trial_rect.position = (0, spec["rect_yrepos"])
                trial_rect.preload()
                for i, interval in enumerate([80, 459, 80, 1377, 80, 459, 80]):
                    if i % 2 == 0:
                        trial_rect.present(clear=False, update=True)
                        exp.clock.wait(80, process_control_events=True)
                    else:
                        text_display.present()
                        exp.clock.wait(interval, process_control_events=True)
                text_display.present()
            elif action == 'trial_prod_audio':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                for interval in [539, 1457, 539, 1457]:
                    medium_beep.present()
                    exp.clock.wait(interval, process_control_events=True)
                medium_beep.present()
                _, rt = exp.keyboard.wait_char(setting["INDEX_BUTTON"])
                medium_beep.present()
                if setting["min_prod"] < rt/539 < setting["max_prod"]:
                    positive_feedback_prodntfd.present()
                else:
                    negative_feedback_production.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            elif action == 'trial_prod_visual':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                trial_rect.position = (0, 0)
                trial_rect.preload()
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                for i, interval in enumerate([80, 459, 80, 1377,
                                              80, 459, 80, 1377,
                                              80]):
                    if i % 2 == 0:
                        trial_rect.present()
                        exp.clock.wait(interval, process_control_events=True)
                    else:
                        fixcross3.present()
                        exp.clock.wait(interval, process_control_events=True)
                fixcross3.present()
                _, rt = exp.keyboard.wait_char(setting["INDEX_BUTTON"])
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                if setting["min_prod"] < rt/539 < setting["max_prod"]:
                    positive_feedback_prodntfd.present()
                else:
                    negative_feedback_production.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            elif action == 'trial_percep_audio':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                for interval in [539, 1457, 539, 1457, 367]:
                    medium_beep.present()
                    exp.clock.wait(interval, process_control_events=True)
                medium_beep.present()
                exp.clock.wait(80, process_control_events=True)
                screen_feedback_percep.present()
                key, _ = exp.keyboard.wait_char([setting["INDEX_BUTTON"],
                                                 setting["MIDDLE_BUTTON"]])
                if key == setting["INDEX_BUTTON"]:
                    negative_feedback_percepntfd.present()
                else:
                    assert key == setting["MIDDLE_BUTTON"]
                    positive_feedback_perception.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            elif action == 'trial_percep_visual':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                trial_rect.position = (0, 0)
                trial_rect.preload()
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                for i, interval in enumerate([80, 459, 80, 1377,
                                              80, 459, 80, 1377,
                                              80, 551]):
                    if i % 2 == 0:
                        trial_rect.present()
                        exp.clock.wait(interval, process_control_events=True)
                    else:
                        fixcross3.present()
                        exp.clock.wait(interval, process_control_events=True)
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                screen_feedback_percep.present()
                key, _ = exp.keyboard.wait_char([setting["INDEX_BUTTON"],
                                                 setting["MIDDLE_BUTTON"]])
                if key == setting["INDEX_BUTTON"]:
                    positive_feedback_perception.present()
                else:
                    assert key == setting["MIDDLE_BUTTON"]
                    negative_feedback_percepntfd.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            elif action == 'trial_ntfd_audio':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                for interval in [539, 1457, 539, 1457, 539]:
                    medium_beep.present()
                    exp.clock.wait(interval, process_control_events=True)
                high_beep.present()
                key, rt = exp.keyboard.wait_char([setting["INDEX_BUTTON"],
                                                  setting["MIDDLE_BUTTON"]])
                if key == setting["INDEX_BUTTON"]:
                    high_beep.present()
                elif key == setting["MIDDLE_BUTTON"]:
                    low_beep.present()
                exp.clock.wait(240, process_control_events=True)
                if rt < setting["min_ntfd"] and key == setting["INDEX_BUTTON"]:
                    negative_feedback_ntfd1.present()
                elif rt < setting["min_ntfd"] and \
                     key == setting["MIDDLE_BUTTON"]:
                    negative_feedback_ntfd2.present()
                elif setting["min_ntfd"] < rt < setting["max_ntfd"] and \
                     key == setting["INDEX_BUTTON"]:
                    positive_feedback_prodntfd.present()
                elif setting["min_ntfd"] < rt < setting["max_ntfd"] and \
                     key == setting["MIDDLE_BUTTON"]:
                    negative_feedback_percepntfd.present()
                elif rt > setting["max_ntfd"] and \
                     key == setting["INDEX_BUTTON"]:
                    negative_feedback_ntfd3.present()
                else:
                    assert rt > setting["max_ntfd"] and \
                        key == setting["MIDDLE_BUTTON"]
                    negative_feedback_ntfd4.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            elif action == 'trial_ntfd_visual':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                trial_rect.position = (0, 0)
                trial_rect.preload()
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                for i, interval in enumerate([80, 459, 80, 1377,
                                              80, 459, 80, 1377,
                                              80, 459]):
                    if i % 2 == 0:
                        trial_rect.present()
                        exp.clock.wait(interval, process_control_events=True)
                    else:
                        fixcross3.present()
                        exp.clock.wait(interval, process_control_events=True)
                target_tri.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                key, rt = exp.keyboard.wait_char([setting["INDEX_BUTTON"],
                                                  setting["MIDDLE_BUTTON"]])
                if key == setting["INDEX_BUTTON"]:
                    target_circ.present()
                elif key == setting["MIDDLE_BUTTON"]:
                    target_tri.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                if rt < setting["min_ntfd"] and \
                   key == setting["MIDDLE_BUTTON"]:
                    negative_feedback_ntfd1.present()
                elif rt < setting["min_ntfd"] and \
                     key == setting["INDEX_BUTTON"]:
                    negative_feedback_ntfd2.present()
                elif setting["min_ntfd"] < rt < setting["max_ntfd"] and \
                     key == setting["MIDDLE_BUTTON"]:
                    positive_feedback_prodntfd.present()
                elif setting["min_ntfd"] < rt < setting["max_ntfd"] and \
                     key == setting["INDEX_BUTTON"]:
                    negative_feedback_percepntfd.present()
                elif rt > setting["max_ntfd"] and \
                     key == setting["MIDDLE_BUTTON"]:
                    negative_feedback_ntfd3.present()
                else:
                    assert rt > setting["max_ntfd"] and \
                        key == setting["INDEX_BUTTON"]
                    negative_feedback_ntfd4.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            elif action == 'trial_prod_audio_beat':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                # Two pairs; each interval BETWEEN pairs is a true 3X beat (3 * 539)
                # with a soft beep on the two internal subdivisions.
                medium_beep.present()
                exp.clock.wait(539, process_control_events=True)
                medium_beep.present()
                _audio_beat_gap(exp, soft_beep, 539, 3)
                medium_beep.present()
                exp.clock.wait(539, process_control_events=True)
                medium_beep.present()
                _audio_beat_gap(exp, soft_beep, 539, 3)
                medium_beep.present()
                _, rt = exp.keyboard.wait_char(setting["INDEX_BUTTON"])
                medium_beep.present()
                if setting["min_prod"] < rt/539 < setting["max_prod"]:
                    positive_feedback_prodntfd.present()
                else:
                    negative_feedback_production.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            elif action == 'trial_prod_visual_beat':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                trial_rect.position = (0, 0)
                trial_rect.preload()
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                # pair 1
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(459, process_control_events=True)
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                _visual_beat_gap(exp, fixcross3, small_rect, 539, 80, 3)
                # pair 2
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(459, process_control_events=True)
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                _visual_beat_gap(exp, fixcross3, small_rect, 539, 80, 3)
                # target
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                _, rt = exp.keyboard.wait_char(setting["INDEX_BUTTON"])
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                if setting["min_prod"] < rt/539 < setting["max_prod"]:
                    positive_feedback_prodntfd.present()
                else:
                    negative_feedback_production.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            elif action == 'trial_percep_audio_beat':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                medium_beep.present()
                exp.clock.wait(539, process_control_events=True)
                medium_beep.present()
                _audio_beat_gap(exp, soft_beep, 539, 3)
                medium_beep.present()
                exp.clock.wait(539, process_control_events=True)
                medium_beep.present()
                _audio_beat_gap(exp, soft_beep, 539, 3)
                medium_beep.present()
                exp.clock.wait(367, process_control_events=True)
                medium_beep.present()
                exp.clock.wait(80, process_control_events=True)
                screen_feedback_percep.present()
                key, _ = exp.keyboard.wait_char([setting["INDEX_BUTTON"],
                                                 setting["MIDDLE_BUTTON"]])
                if key == setting["INDEX_BUTTON"]:
                    negative_feedback_percepntfd.present()
                else:
                    assert key == setting["MIDDLE_BUTTON"]
                    positive_feedback_perception.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            elif action == 'trial_percep_visual_beat':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                trial_rect.position = (0, 0)
                trial_rect.preload()
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                # pair 1
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(459, process_control_events=True)
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                _visual_beat_gap(exp, fixcross3, small_rect, 539, 80, 3)
                # pair 2
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(459, process_control_events=True)
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                _visual_beat_gap(exp, fixcross3, small_rect, 539, 80, 3)
                # probe pair
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(551, process_control_events=True)
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                screen_feedback_percep.present()
                key, _ = exp.keyboard.wait_char([setting["INDEX_BUTTON"],
                                                 setting["MIDDLE_BUTTON"]])
                if key == setting["INDEX_BUTTON"]:
                    positive_feedback_perception.present()
                else:
                    assert key == setting["MIDDLE_BUTTON"]
                    negative_feedback_percepntfd.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            elif action == 'trial_ntfd_audio_beat':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                medium_beep.present()
                exp.clock.wait(539, process_control_events=True)
                medium_beep.present()
                _audio_beat_gap(exp, soft_beep, 539, 3)
                medium_beep.present()
                exp.clock.wait(539, process_control_events=True)
                medium_beep.present()
                _audio_beat_gap(exp, soft_beep, 539, 3)
                medium_beep.present()
                exp.clock.wait(539, process_control_events=True)
                high_beep.present()
                key, rt = exp.keyboard.wait_char([setting["INDEX_BUTTON"],
                                                  setting["MIDDLE_BUTTON"]])
                if key == setting["INDEX_BUTTON"]:
                    high_beep.present()
                elif key == setting["MIDDLE_BUTTON"]:
                    low_beep.present()
                exp.clock.wait(240, process_control_events=True)
                if rt < setting["min_ntfd"] and key == setting["INDEX_BUTTON"]:
                    negative_feedback_ntfd1.present()
                elif rt < setting["min_ntfd"] and \
                     key == setting["MIDDLE_BUTTON"]:
                    negative_feedback_ntfd2.present()
                elif setting["min_ntfd"] < rt < setting["max_ntfd"] and \
                     key == setting["INDEX_BUTTON"]:
                    positive_feedback_prodntfd.present()
                elif setting["min_ntfd"] < rt < setting["max_ntfd"] and \
                     key == setting["MIDDLE_BUTTON"]:
                    negative_feedback_percepntfd.present()
                elif rt > setting["max_ntfd"] and \
                     key == setting["INDEX_BUTTON"]:
                    negative_feedback_ntfd3.present()
                else:
                    assert rt > setting["max_ntfd"] and \
                        key == setting["MIDDLE_BUTTON"]
                    negative_feedback_ntfd4.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            elif action == 'trial_ntfd_visual_beat':
                found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                                  misc.constants.K_KP_ENTER,
                                                  misc.constants.K_RIGHT,
                                                  misc.constants.K_LEFT])
                if found_key == misc.constants.K_LEFT:
                    ldx -= 1
                    continue
                trial_rect.position = (0, 0)
                trial_rect.preload()
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                # pair 1
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(459, process_control_events=True)
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                _visual_beat_gap(exp, fixcross3, small_rect, 539, 80, 3)
                # pair 2
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(459, process_control_events=True)
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                _visual_beat_gap(exp, fixcross3, small_rect, 539, 80, 3)
                # probe pair
                trial_rect.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(459, process_control_events=True)
                target_tri.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                key, rt = exp.keyboard.wait_char([setting["INDEX_BUTTON"],
                                                  setting["MIDDLE_BUTTON"]])
                if key == setting["INDEX_BUTTON"]:
                    target_circ.present()
                elif key == setting["MIDDLE_BUTTON"]:
                    target_tri.present()
                exp.clock.wait(80, process_control_events=True)
                fixcross3.present()
                exp.clock.wait(160, process_control_events=True)
                if rt < setting["min_ntfd"] and \
                   key == setting["MIDDLE_BUTTON"]:
                    negative_feedback_ntfd1.present()
                elif rt < setting["min_ntfd"] and \
                     key == setting["INDEX_BUTTON"]:
                    negative_feedback_ntfd2.present()
                elif setting["min_ntfd"] < rt < setting["max_ntfd"] and \
                     key == setting["MIDDLE_BUTTON"]:
                    positive_feedback_prodntfd.present()
                elif setting["min_ntfd"] < rt < setting["max_ntfd"] and \
                     key == setting["INDEX_BUTTON"]:
                    negative_feedback_percepntfd.present()
                elif rt > setting["max_ntfd"] and \
                     key == setting["MIDDLE_BUTTON"]:
                    negative_feedback_ntfd3.present()
                else:
                    assert rt > setting["max_ntfd"] and \
                        key == setting["INDEX_BUTTON"]
                    negative_feedback_ntfd4.present()
                exp.clock.wait(3008, process_control_events=True)
                ldx += 1
                continue
            # Checks whether "ENTER", "LEFT" or m" key were pressed.
            # If "ENTER", goes to the next line;
            # if "LEFT", goes to the previous slide;
            # if "h", returns to main menu.
            found_key, _ = exp.keyboard.wait([misc.constants.K_RETURN,
                                              misc.constants.K_KP_ENTER,
                                              misc.constants.K_RIGHT,
                                              misc.constants.K_LEFT,
                                              misc.constants.K_BACKSPACE,
                                              misc.constants.K_h])
            if found_key == misc.constants.K_h:
                break
            if ldx < len(instructions) - 1:
                if found_key == misc.constants.K_BACKSPACE:
                    continue
                elif found_key == misc.constants.K_LEFT:
                    ldx = ldx - 2
                    if ldx < 0:
                        ldx = -1
                else:
                    pass
                ldx += 1
            else:
                assert ldx == len(instructions) - 1
                if found_key == misc.constants.K_BACKSPACE:
                    break
                elif found_key == misc.constants.K_LEFT:
                    ldx = ldx - 1
                else:
                    pass