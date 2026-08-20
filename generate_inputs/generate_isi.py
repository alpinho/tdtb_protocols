# -*- coding: utf-8 -*-
# ======================================================================
# Generate Inter-Stimulus Intervals (ISIs) for the
# Timing-Domain Task Battery (TDTB)
#
# Author: Ana Luisa Pinho
#
# email: agrilopi@uwo.ca
#
# Created: April 2022
# Last Update: August 2026
#
# Compatibility: Python 3.7.11
# ======================================================================

import os
import sys
import csv
import random
import numpy as np

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from confparser import load_config


# %%
# ========================== CALL .INI FILE ============================
# setting = load_config('../imagingsess_config.ini')
setting = load_config('../behavsess_config.ini')
# setting = load_config('../trainsess_config.ini')


# %%
# ========================== FUNCTIONS =================================


def compute_isi1(minisi, maxisi, n_tr):
    isi = np.linspace(minisi, maxisi, maxisi - minisi, dtype=int)
    isi16 = isi[isi % 16 == 0]
    isi17 = isi[isi % 17 == 0]
    isi1 = np.unique(np.sort(np.concatenate((isi16, isi17))))
    step_size = int(round(len(isi1)/n_tr, 0))

    if step_size < 1:
        raise ValueError(
            'Length of Isi1 is smaller than number of trials per condition.')
    elif step_size > 1:
        isi1 = isi1[::step_size]
    else:
        assert step_size == 1
        pass

    print('Number of standards is: ', len(isi1))

    trial_names_beat = ['beat%02d' % tnb
                        for tnb in np.arange(1, len(isi1) + 1)]
    trial_names_interval = ['interval%02d' % tni
                            for tni in np.arange(1, len(isi1) + 1)]
    trial_names_random = ['random%02d' % tnr
                          for tnr in np.arange(1, len(isi1) + 1)]

    return isi1, trial_names_beat, trial_names_interval, trial_names_random


def middle_isis_condbeat(isi1):
    isi2 = np.multiply(3, isi1)
    mask2 = [False if i % 16 == 0 or i % 17 == 0 else True for i in isi2]
    if np.any(mask2):
        raise ValueError('Isi2 is not multiple of inverse of refresh rate!')

    print('Mean of Isi2: ', round(np.mean(isi2), 0))

    return isi2


def middle_isis_condint(isi1):
    isi2s = np.linspace(
        np.amin(np.multiply(3, isi1)),
        np.amax(np.multiply(3, isi1)),
        np.amax(np.multiply(3, isi1)) - np.amin(np.multiply(3, isi1)),
        dtype=int)
    isi2f = np.concatenate((isi2s[isi2s % 16 == 0], isi2s[isi2s % 17 == 0]))
    stop = False
    while not stop:
        isi2 = np.random.choice(isi2f, len(isi1))
        mask2 = [False if k % 16 == 0 or k % 17 == 0 else True for k in isi2]
        if np.any(mask2):
            continue
        isi4 = np.array([6*b - isi2[c] for c, b in enumerate(isi1)])
        mask4 = [False if k % 16 == 0 or k % 17 == 0 else True for k in isi4]
        if np.any(mask4):
            continue
        if np.mean(isi2) != round(np.mean(isi4), 0):
        # if abs(np.mean(isi2) - round(np.mean(isi4), 0)) > 2:
            continue
        mask24 = [False if i != j else True for i, j in zip(isi2, isi4)]
        if np.any(mask24):
            continue
        if np.mean(isi2) != np.mean(np.multiply(3, isi1)):
            continue
        else:
            stop = True

    print('Mean of Isi2: ', round(np.mean(isi2), 0))
    print('Mean of Isi4: ', round(np.mean(isi4), 0))

    return isi2, isi4


def last_isi_percep(isi1, deviations):
    isi5 = []
    for d in deviations:
        for i in isi1:
            new_isi = int(round(i * (1 + d), 0))
            isi5.append(new_isi)

    isi5 = np.reshape(isi5, (len(isi5), 1))

    return isi5


def featdis(isi1, sensory_modality):
    feat_sequence = []
    while len(feat_sequence) != len(isi1):
        if sensory_modality == 'audio':
            stim_type = [setting['audiowav_low'], setting['audiowav_high']]
        else:
            assert sensory_modality == 'visual'
            stim_type = ['circle', 'triangle']
        feat_sequence.extend(stim_type)

    return feat_sequence


def save_output(ofname, isi_s):
    with open(ofname, "w", newline='') as fp:
        a = csv.writer(fp, delimiter="\t")
        a.writerows(isi_s)


def production_beat(header_production, isi_one, cdir, trial_names_beat,
                    n_repeat):

    # Generate fixed isi2's and isi4's multiples of isi1's
    isi_two = middle_isis_condbeat(isi_one)

    # Create final list
    isis = np.vstack((trial_names_beat, isi_one, isi_two, isi_one, isi_two)).T
    isis = np.repeat([isis], n_repeat, axis=0)
    isis = isis.reshape(isis.shape[0] * isis.shape[1], 5)
    isis = np.vstack((header_production, isis))

    # Create the output path
    output = os.path.join(cdir, "production_beat.tsv")

    # Save final file
    save_output(output, isis)


def production_interval(header_production, isi_one, cdir,
                        trial_names_interval, n_repeat):

    # Generate randomized isi2's and isi4's
    isi_two, isi_four = middle_isis_condint(isi_one)

    # Create final list
    isis = np.vstack((trial_names_interval, isi_one, isi_two, isi_one,
                      isi_four)).T
    isis = np.repeat([isis], n_repeat, axis=0)
    isis = isis.reshape(isis.shape[0] * isis.shape[1], 5)
    isis = np.vstack((header_production, isis))

    # Create the output path
    output = os.path.join(cdir, "production_interval.tsv")

    # Save final file
    save_output(output, isis)


def perception_beat(header_perception, isi_one, minisi, maxisi, cdir,
                    trial_names_beat, deviations, n_repeat):

    # Generate fixed isi2's and isi4's multiples of isi1's
    isi_two = middle_isis_condbeat(isi_one)

    # Generate randomized isi5's
    isi_five = last_isi_percep(isi_one, deviations)

    # Create a final list
    isis = np.vstack((trial_names_beat, isi_one, isi_two, isi_one,
                      isi_two)).T
    isis = np.repeat([isis], n_repeat, axis=0)
    isis = isis.reshape(isis.shape[0]*isis.shape[1], 5)
    isis = np.hstack((isis, isi_five))
    isis = np.vstack((header_perception, isis))

    # Create the output path
    output = os.path.join(cdir, "perception_beat.tsv")

    # Save final file
    save_output(output, isis)


def perception_interval(header_perception, isi_one, minisi, maxisi, cdir,
                        trial_names_interval, deviations, n_repeat):

    # Generate randomized isi2's and isi4's
    isi_two, isi_four = middle_isis_condint(isi_one)

    # Generate randomized isi5's
    isi_five = last_isi_percep(isi_one, deviations)

    # Create a final list
    isis = np.vstack((trial_names_interval, isi_one, isi_two, isi_one,
                      isi_four)).T
    isis = np.repeat([isis], n_repeat, axis=0)
    isis = isis.reshape(isis.shape[0]*isis.shape[1], 5)
    isis = np.hstack((isis, isi_five))
    isis = np.vstack((header_perception, isis))

    # Create the output path
    output = os.path.join(cdir, "perception_interval.tsv")

    # Save final file
    save_output(output, isis)


def notemporal_beat(header_notemporal, isi_one, cdir, modality,
                    trial_names_beat, n_repeat, random=False):

    # Generate fixed isi2's and isi4's multiples of isi1's
    isi_two = middle_isis_condbeat(isi_one)

    # Stacking
    isis = np.vstack((trial_names_beat, isi_one, isi_two, isi_one,
                      isi_two, isi_one)).T
    isis = np.repeat([isis], n_repeat, axis=0)
    isis = isis.reshape(isis.shape[0]*isis.shape[1], 6)

    # Generate sequence of different features to be discriminated
    fseq = featdis(isis, modality)

    # Create final list
    fseq = np.reshape(fseq, (len(fseq), 1))
    isis = np.hstack((isis, fseq))
    isis = np.vstack((header_notemporal, isis))

    # Create the output path
    if random:
        output = os.path.join(cdir, "ntfd_random",
                              "notemporal_beat_" + modality + ".tsv")
    else:
        output = os.path.join(cdir, "ntfd_no_random",
                              "notemporal_beat_" + modality + ".tsv")

    # Save final file
    save_output(output, isis)


def notemporal_interval(header_notemporal, isi_one, cdir, modality,
                        trial_names_interval, n_repeat, random=False):

    # Generate randomized isi2's and isi4's
    isi_two, isi_four = middle_isis_condint(isi_one)

    # Stacking
    isis = np.vstack((trial_names_interval, isi_one, isi_two, isi_one,
                      isi_four, isi_one)).T
    isis = np.repeat([isis], n_repeat, axis=0)
    isis = isis.reshape(isis.shape[0]*isis.shape[1], 6)

    # Generate sequence of different features to be discriminated
    fseq = featdis(isis, modality)

    # Create final list
    fseq = np.reshape(fseq, (len(fseq), 1))
    isis = np.hstack((isis, fseq))
    isis = np.vstack((header_notemporal, isis))

    # Create the output path
    if random:
        output = os.path.join(cdir, "ntfd_random",
                              "notemporal_interval_" + modality + ".tsv")
    else:
        output = os.path.join(cdir, "ntfd_no_random",
                              "notemporal_interval_" + modality + ".tsv")

    # Save final file
    save_output(output, isis)


def notemporal_random(isi_one, n_repeat, header_notemporal, cdir, modality):

    random_arr = np.zeros((len(isi_one) * n_repeat, len(isi_one)),
                          dtype=int)

    for i, isi in enumerate(isi_one):
        isi_list = np.linspace(isi, 5*isi, 4*isi, dtype=int)
        isi16 = isi_list[isi_list % 16 == 0]
        isi17 = isi_list[isi_list % 17 == 0]
        isis = np.unique(np.concatenate((isi16, isi17)))
        random_trials = []
        j=0
        while j < n_repeat:
            trial = np.random.choice(isis, len(isi_one) - 1).tolist()
            trial.append(isi)
            if np.sum(trial) != isi*9:
                del trial
                continue
            else:
                random_trials.append(trial)
                j += 1
        for rtr, random_trial in enumerate(random_trials):
            random_arr[rtr*len(isi_one) + i] = random_trial

    # Create names for trials
    trial_names_random = ['random%02d' % s
                          for s in np.arange(1, len(random_arr) + 1)]
    trial_names_random = np.reshape(trial_names_random,
                                    (len(trial_names_random), 1))

    # Generate sequence of different features to be discriminated
    fseq = featdis(random_arr, modality)
    fseq = np.reshape(fseq, (len(fseq), 1))

    # Stacking
    random_isis = np.hstack((trial_names_random, random_arr, fseq))
    random_isis = np.vstack((header_notemporal, random_isis))

    # Create the output path
    output = os.path.join(cdir, "ntfd_random",
                          "notemporal_random_" + modality + ".tsv")

    # Save final file
    save_output(output, random_isis)


# %%
# ========================== INPUTS ====================================

current_dir = os.path.dirname(os.path.abspath(__file__))

# NOTE ON THE COLUMN NAMES:
# The isi_* columns hold ONSET-TO-ONSET intervals, i.e. the time from the
# onset of one pacing event to the onset of the next. The formal name for
# this quantity is stimulus onset asynchrony (SOA); the rhythm and
# sensorimotor-synchronization literature calls it the inter-onset interval
# (IOI). They are NOT interstimulus intervals in the strict sense
# (offset-to-onset), which would be shorter by one stimulus duration.
# The 'isi_' prefix is kept only for backward compatibility with the input
# TSVs already generated and with the analysis pipeline that reads them;
# do not rename it without regenerating every input file. The same applies
# to MIN_ISI/MAX_ISI below and to the isi_* variables throughout this module.
HEADER_PRODUCTION = ['trial_id', 'isi_1', 'isi_2', 'isi_3', 'isi_4']
HEADER_PERCEPTION = ['trial_id', 'isi_1', 'isi_2', 'isi_3', 'isi_4', 'isi_5']
HEADER_NOTEMPORAL = [
    'trial_id', 'isi_1', 'isi_2', 'isi_3', 'isi_4', 'isi_5', 'target_shape']

MIN_ISI = 450
MAX_ISI = 700
N_STANDARDS = 5
deviations_list = [-.2, -.12, -.02, .02, .12, .2]

# %%
# ========================= PARAMETERS =================================

N_DEVIATIONS = len(deviations_list)

# %%
# =========================== RUN ======================================

if __name__ == '__main__':

    assert(len(sys.argv) > 1), "No arg was introduced. " + \
                               "You must pass a valid arg to the script."
    taskcond = sys.argv[1]
    assert(taskcond in ['production_beat', 'production_interval',
                        'perception_beat', 'perception_interval',
                        'notemporal_beat_audio', 'notemporal_interval_audio',
                        'notemporal_beat_visual', 'notemporal_interval_visual',
                        'notemporal_random_audio',
                        'notemporal_random_visual']), \
        "Not valid arg for type of stimulus. Please select " + \
        "'production_beat', 'production_interval', 'perception_beat', " + \
        "'perception_interval', 'notemporal_beat_audio', " + \
        "'notemporal_interval_audio', 'notemporal_beat_visual', " + \
        "'notemporal_interval_visual', 'notemporal_random_audio', " + \
        "or 'notemporal_random_visual'."

    isione, tbeat, tint, trand = compute_isi1(MIN_ISI, MAX_ISI, N_STANDARDS)

    if taskcond == "production_beat":
        production_beat(HEADER_PRODUCTION, isione, current_dir, tbeat,
                        N_DEVIATIONS)

    elif taskcond == "production_interval":
        production_interval(HEADER_PRODUCTION, isione, current_dir, tint,
                            N_DEVIATIONS)

    elif taskcond == "perception_beat":
        perception_beat(HEADER_PERCEPTION, isione, MIN_ISI, MAX_ISI,
                        current_dir, tbeat, deviations_list, N_DEVIATIONS)

    elif taskcond == "perception_interval":
        perception_interval(HEADER_PERCEPTION, isione, MIN_ISI, MAX_ISI,
                            current_dir, tint, deviations_list, N_DEVIATIONS)

    elif taskcond == "notemporal_beat_audio":
        notemporal_beat(HEADER_NOTEMPORAL, isione, current_dir, 'audio',
                        tbeat, N_DEVIATIONS)
        # notemporal_beat(HEADER_NOTEMPORAL, isione, current_dir, 'audio',
        #                 tbeat, 4, random=True)

    elif taskcond == "notemporal_interval_audio":
        notemporal_interval(HEADER_NOTEMPORAL, isione, current_dir, 'audio',
                            tint, N_DEVIATIONS)
        # notemporal_interval(HEADER_NOTEMPORAL, isione, current_dir, 'audio',
        #                     tint, 4, random=True)

    elif taskcond == "notemporal_beat_visual":
        notemporal_beat(HEADER_NOTEMPORAL, isione, current_dir, 'visual',
                        tbeat, N_DEVIATIONS)
        # notemporal_beat(HEADER_NOTEMPORAL, isione, current_dir, 'visual',
        #                 tbeat, 4, random=True)

    elif taskcond == "notemporal_interval_visual":
        notemporal_interval(HEADER_NOTEMPORAL, isione, current_dir, 'visual',
                            tint, N_DEVIATIONS)
        # notemporal_interval(HEADER_NOTEMPORAL, isione, current_dir, 'visual',
        #                     tint, 4, random=True)

    elif taskcond == "notemporal_random_audio":
        notemporal_random(isione, 4, HEADER_NOTEMPORAL, current_dir,
                          'audio')

    else:
        assert taskcond == "notemporal_random_visual"
        notemporal_random(isione, 4, HEADER_NOTEMPORAL, current_dir,
                          'visual')