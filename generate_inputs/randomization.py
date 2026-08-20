# -*- coding: utf-8 -*-
# ======================================================================
# Randomize trials across runs for the
# Timing-Domain Task Battery (TDTB)
#
# Author: Ana Luísa Pinho
#
# email: agrilopi@uwo.ca
#
# Created: April 2022
# Last Update: August 2026
#
# Compatibility: Python 3.7.11
#
# How to run the script:
# python randomization.py <session_type> <subject_number> <session_number>
# Example:
# python randomization.py behavioral_session 10 2
# python randomization.py imaging_session 10 2
# For the training_session, no need to introduce the two last args
# python randomization.py training_session
# ======================================================================

import os
import sys
import glob
import re
import csv
import numpy as np

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from confparser import load_config

# %%
# ========================== FUNCTIONS =================================

def balance_deviations(arr, dev_list):
    occur = np.empty((len(dev_list))).astype('int')
    for row in arr:
        row = np.array(row[1:]).astype('int')
        ratio = round((row[4]/row[0] -1), 2)
        occur[np.argwhere(dev_list==ratio)[0][0]] += 1

    return occur


def loadinputs(category, modality, sess_type, subject_number, session_number,
               cdir, pdir, random=False):
    if category == 'notemporal':
        if random:
            folder = 'ntfd_random'
        else:
            folder = 'ntfd_no_random'
        sensemod = '_' + modality
    else:
        folder = category
        sensemod = ''
    inputs_beat = [k for k in csv.reader(
        open(os.path.join(cdir, folder,
                          category + '_beat' + sensemod + '.tsv'), 'r'),
        delimiter='\t', )][1:]
    inputs_interval = [j for j in csv.reader(
        open(os.path.join(cdir, folder,
                          category + '_interval' + sensemod + '.tsv'), 'r'),
        delimiter='\t')][1:]
    file_header = [h for h in csv.reader(
        open(os.path.join(cdir, folder,
                          category + '_beat' + sensemod + '.tsv'), 'r'),
        delimiter='\t')][0]

    # Fix different behaviours of csvreader between Windows and Linux
    inputs_beat = [x for x in inputs_beat if x]
    inputs_interval = [y for y in inputs_interval if y]

    if sess_type in ['imaging_session', 'behavioral_session']:
        output_dir = os.path.join(
            pdir, sess_type.replace('_', '-') + 's_inputs',
            'sub-%02d' % int(subject_number),
            'ses-%02d' % int(session_number),
            'inputs_' + category + '_sub-%02d' % int(subject_number) + \
            '_ses-%02d' % int(session_number), modality)
    else:
        assert sess_type == 'training_session'
        output_dir = os.path.join(
            pdir, sess_type.replace('_', '-') + '_inputs',
            'inputs_' + category, modality)

    return inputs_beat, inputs_interval, file_header, output_dir


def loadrandom(modality):

    sensemod = '_' + modality
    inputs_random = [k for k in csv.reader(
        open(os.path.join(
            'ntfd_random', 'notemporal_random' + sensemod + '.tsv'), 'r'),
        delimiter='\t')][1:]

    # Fix different behaviours of csvreader between Windows and Linux
    inputs_random = [z for z in inputs_random if z]

    return inputs_random


def runmap(inputs_beat, inputs_interval, category, modality, dev_list,
           inputs_random=None):

    run1 = []
    run2 = []

    idx = np.arange(len(inputs_beat))

    stop = False
    while not stop:
        np.random.shuffle(idx)
        # Match id's for beat and interval (and random)
        idx1 = idx[:len(idx)//2]
        idx2 = idx[len(idx)//2:]
        ibeat1 = [inputs_beat[bo] for bo in idx1]
        ibeat2 = [inputs_beat[bt] for bt in idx2]
        isi2b1 = np.array(ibeat1)[:, 2].astype('int')
        isi2b2 = np.array(ibeat2)[:, 2].astype('int')
        # Means of isi2 for beat in the two runs are the same
        if isi2b1.mean(0) != isi2b2.mean(0):
            continue
        iint1 = [inputs_interval[io] for io in idx1]
        iint2 = [inputs_interval[it] for it in idx2]
        isi2i1 = np.array(iint1)[:, 2].astype('int')
        isi2i2 = np.array(iint2)[:, 2].astype('int')
        # Means of isi2 for interval in the two runs are the same
        if isi2i1.mean(0) != isi2i2.mean(0):
            continue
        if inputs_random is not None:
            irand1 = [inputs_random[ro] for ro in idx1]
            irand2 = [inputs_random[rt] for rt in idx2]
            isi2r1 = np.array(irand1)[:, 2].astype('int')
            isi2r2 = np.array(irand2)[:, 2].astype('int')
        # All means for isi2 between beat and interval are the same
        if isi2b1.mean(0) != isi2i1.mean(0):
            continue
        # Number of trials with the same deviations are balanced across runs
        if category == 'perception':
            occur_b1 = balance_deviations(ibeat1, dev_list)
            if ~np.all(occur_b1 >= len(ibeat1) // len(dev_list)):
                continue
            occur_b2 = balance_deviations(ibeat2, dev_list)
            if ~np.all(occur_b2 >= len(ibeat2) // len(dev_list)):
                continue
            occur_i1 = balance_deviations(iint1, dev_list)
            if ~np.all(occur_i1 >= len(iint1) // len(dev_list)):
                continue
            occur_i2 = balance_deviations(iint2, dev_list)
            if ~np.all(occur_i2 >= len(iint2) // len(dev_list)):
                continue
            else:
                print(category, ' - ', modality)
                print(occur_b1)
                print(occur_i1)
                print(category, ' - ', modality)
                print(occur_b2)
                print(occur_i2)
                stop = True
        # Number of features to be discriminated are balanced across runs
        elif category == 'notemporal':
            fdb1 = np.array(ibeat1)[:, 6]
            if modality == 'audio':
                if np.count_nonzero(np.char.count(fdb1, 'beep_880hz')) != \
                   len(fdb1) // 2:
                    continue
                else:
                    fdb2 = np.array(ibeat2)[:, 6]
                    fdi1 = np.array(iint1)[:, 6]
                    fdi2 = np.array(iint2)[:, 6]
                    print(category, ' - ', modality)
                    print('beat high: ',
                          np.count_nonzero(np.char.count(fdb1, 'beep_880hz')))
                    print('interval high: ',
                          np.count_nonzero(np.char.count(fdi1, 'beep_880hz')))
                    print(category, ' - ', modality)
                    print('beat high: ',
                          np.count_nonzero(np.char.count(fdb2, 'beep_880hz')))
                    print('interval high: ',
                          np.count_nonzero(np.char.count(fdi2, 'beep_880hz')))
                    stop = True
            else:
                assert modality == 'visual'
                if np.count_nonzero(np.char.count(fdb1, 'circle')) != \
                   len(fdb1) // 2:
                    continue
                else:
                    fdb2 = np.array(ibeat2)[:, 6]
                    fdi1 = np.array(iint1)[:, 6]
                    fdi2 = np.array(iint2)[:, 6]
                    print(category, ' - ', modality)
                    print('beat circle: ',
                          np.count_nonzero(np.char.count(fdb1, 'circle')))
                    print('interval circle: ',
                          np.count_nonzero(np.char.count(fdi1, 'circle')))
                    print(category, ' - ', modality)
                    print('beat circle: ',
                          np.count_nonzero(np.char.count(fdb2, 'circle')))
                    print('interval circle: ',
                          np.count_nonzero(np.char.count(fdi2, 'circle')))
                    stop = True
        else:
            assert category == 'production'
            stop = True
    run1.extend(ibeat1)
    run1.extend(iint1)
    run2.extend(ibeat2)
    run2.extend(iint2)
    if inputs_random is not None:
        run1.extend(irand1)
        run2.extend(irand2)

    return run1, run2


def create_onsets(inputs_table, category, modality, setting):
    onsets = []
    for tl, line in enumerate(inputs_table):
        if tl == 0 and modality == 'audio':
            onset = setting["WAIT"]
            onsets.append(onset)
        elif tl == 0 and modality == 'visual':
            onset = setting["between_tasks_duration"]
            onsets.append(onset)
        else:
            onsets.append(onset)

        if line[1] == 'baseline':
            onset += setting["baseline_duration"]
        else:
            if category == 'notemporal':
                onset += np.sum(np.int64(line[2:-1])) + \
                    setting["stim_duration"] + setting["feedback_duration"] + \
                    setting["within_block_duration"]
            else:
                assert category in ['production', 'perception']
                onset += np.sum(np.int64(line[2:])) + \
                    setting["stim_duration"] + setting["feedback_duration"] + \
                    setting["within_block_duration"]

    onsets = np.array(onsets).reshape(1, len(onsets))
    new_inputs_table = np.hstack((onsets.T, inputs_table))

    return new_inputs_table


def randomize_trials(block, header, sess_type, n_ttr, category, modality, setting, randmod):
    if sess_type in ['imaging_session', 'behavioral_session']:
        n_baseline = len(block) // 6
        baseline_row = np.repeat('-', len(block[0]) - 1).tolist()
        baseline_row.insert(0, 'baseline')
        baseline = np.array([baseline_row for x in np.arange(n_baseline)])
        inputs = np.vstack((block, baseline))

        stop = False
        while not stop:
            np.random.shuffle(inputs)
            # Prevent baseline to be in the first trial
            # Prevent two baselines be next to each other or at every...
            # ... other trial
            # Prevent baseline be in the second last trial
            mask = [False
                    if np.any(inputs[i] != inputs[i+1]) and
                    np.any(inputs[i] != inputs[i+2]) and \
                    inputs[0][0] != 'baseline' and \
                    inputs[1][0] != 'baseline' and \
                    inputs[-2][0] != 'baseline'
                    else True
                    for i in np.arange(len(inputs) - 2)]
            if np.any(mask):
                continue
            # Prevent baseline to be in the last trial
            if inputs[-1][0] == 'baseline':
                continue
            else:
                stop = True
    else:
        assert sess_type == 'training_session'
        while True:
            np.random.shuffle(block)
            inputs = np.array(block[:n_ttr])
            conditions = inputs[:, 0]
            count_rand = [c for c in np.array(block)[:, 0] if c[:4] == 'rand']
            if count_rand:
                count = [c for c in conditions if c[:4] == 'rand']
                if len(count) == len(inputs) // 2 + 1:
                    break
            else:
                count = [c for c in conditions if c[:4] == 'beat']
                if len(count) == len(inputs) // 2:
                    break

    trial_numbers = np.arange(1, len(inputs) + 1)
    count_trial = 0
    new_inputs = np.empty((0, len(inputs[0]) + 1))
    for row in inputs:
        row = row.tolist()
        if row[0] == 'baseline':
            row.insert(0, '-')
        else:
            row.insert(0, trial_numbers[count_trial])
            count_trial += 1
        new_inputs = np.append(new_inputs, [row], axis=0)

    on_inputs = create_onsets(new_inputs, category, modality, setting)

    header = np.concatenate([['onsets', 'trial_number'], header])
    header = header.reshape(1, len(header))
    final_list = np.vstack((header, on_inputs))

    return final_list


def store_file(outdir, fname, inputs, sess_type, category, modality, nr):
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    else:
        if nr == 1:
            for f in glob.glob(outdir + '/*.tsv'):
                os.remove(f)
        else:
            pass
    outfname = os.path.join(outdir, fname)
    with open(outfname, "w", newline='') as fp:
        a = csv.writer(fp, delimiter="\t")
        a.writerows(inputs)

    return outfname


def build_behavsess(files_liste, odir, nrun, subject_number, session_number,
                    perception=None):
    files_liste = [line for line in files_liste
                   if int(re.match('.*/*_run-(.*).tsv',
                                   line).groups()[0]) <= nrun]
    flist_final = []
    for nr in np.arange(0, nrun, 2):
        files_list0 = files_liste[nr::nrun]
        files_list1 = files_liste[nr+1::nrun]
        files_list = []
        while True:
            np.random.shuffle(files_list0)
            np.random.shuffle(files_list1)
            last_task0 = re.match(
                '.*/*_(.*)_run(.*).tsv', files_list0[-1]).groups()[0]
            first_task1 = re.match(
                '.*/*_(.*)_run(.*).tsv', files_list1[0]).groups()[0]
            if last_task0 != first_task1:
                break
        files_list.append(files_list0)
        files_list.append(files_list1)

        files_list = np.ravel(files_list)
        for flist in files_list:
            k = 0
            while k <= len(flist[-4-k:-4]):
                if flist[-4-k] == '/' or flist[-4-k] == '\\':
                    flist_final.append([flist[-4-k+1:-4]])
                    break
                k += 1

    if perception:
        assert perception in ['avva', 'vaav']
        if perception == 'avva':
            flist_final.extend([['audio_perception_run-%02d' % (nrun+1)],
                                ['visual_perception_run-%02d' % (nrun+1)],
                                ['visual_perception_run-%02d' % (nrun+2)],
                                ['audio_perception_run-%02d' % (nrun+2)]])
        elif perception == 'vaav':
            flist_final.extend([['visual_perception_run-%02d' % (nrun+1)],
                                ['audio_perception_run-%02d' % (nrun+1)],
                                ['audio_perception_run-%02d' % (nrun+2)],
                                ['visual_perception_run-%02d' % (nrun+2)]])

    print('\nSession plan is: \n', np.array(flist_final))

    sessplan = os.path.join(
        odir, 'sub-%02d' % subject_number, 'ses-%02d' % session_number,
        'plan_sub-%02d' % subject_number + '_ses-%02d' % session_number + \
        '.tsv')

    if os.path.exists(sessplan):
        os.remove(sessplan)

    with open(sessplan, "w", newline='') as f:
        a = csv.writer(f, delimiter="\t")
        a.writerows(flist_final)


def build_imgsess(files_liste, odir, nrun, subject_number, session_number):
    tasks = [f[-28:-11] for f in files_liste]
    tasks = [t[1:] if t[0] == '/' else t for t in tasks]
    tasks = [task if not (task.startswith('/') or task.startswith('\\'))
             else task[1:] for task in tasks]
    tasks = np.unique(tasks)
    tasks1 = np.flip(tasks[:len(tasks)//2])
    tasks2 = np.flip(tasks[len(tasks)//2:])

    modunit = ['AV', 'VA']
    modunit_rev = modunit[::-1]
    modunit.append(modunit[0])
    modunit_rev.append(modunit_rev[0])
    modseq = []
    for nr in np.arange(1, nrun + 1):
        if nr % 2 != 0:
            modseq.append(modunit)
        else:
            modseq.append(modunit_rev)

    if (subject_number % 2 != 0 and session_number % 2 == 0) or \
       (subject_number % 2 == 0 and session_number % 2 != 0):
        modseq = modseq[::-1]

    idxs = np.arange(len(tasks1))
    tasks_seq = []
    for r in np.arange(nrun):
        for m, idx in zip(modseq[r], idxs):
            if m == 'AV':
                tasks_seq.append([tasks1[idx] + '_run-%02d' % (r + 1)])
                tasks_seq.append([tasks2[idx] + '_run-%02d' % (r + 1)])
            else:
                tasks_seq.append([tasks2[idx] + '_run-%02d' % (r + 1)])
                tasks_seq.append([tasks1[idx] + '_run-%02d' % (r + 1)])

    tasks_seq1 = tasks_seq[:len(tasks_seq)//2]
    tasks_seq2 = tasks_seq[len(tasks_seq)//2:]
    tasks_seq1 = np.reshape(tasks_seq1, (len(tasks_seq1)//2, 2))
    tasks_seq2 = np.reshape(tasks_seq2, (len(tasks_seq2)//2, 2))
    np.random.shuffle(tasks_seq1)
    np.random.shuffle(tasks_seq2)
    final_task_seq = np.concatenate((np.ravel(tasks_seq1),
                                     np.ravel(tasks_seq2)))
    final_task_seq = np.reshape(final_task_seq,
                                (len(final_task_seq), 1)).tolist()

    if session_number == 2:
        if subject_number % 2 != 0:
            final_task_seq.append(['visual_notemporal_random_run-%02d' % (nrun + 1)])
            final_task_seq.append(['audio_notemporal_random_run-%02d' % (nrun + 1)])
            final_task_seq.append(['audio_notemporal_random_run-%02d' % (nrun + 2)])
            final_task_seq.append(['visual_notemporal_random_run-%02d' % (nrun + 2)])
        else:
            final_task_seq.append(['audio_notemporal_random_run-%02d' % (nrun + 1)])
            final_task_seq.append(['visual_notemporal_random_run-%02d' % (nrun + 1)])
            final_task_seq.append(['visual_notemporal_random_run-%02d' % (nrun + 2)])
            final_task_seq.append(['audio_notemporal_random_run-%02d' % (nrun + 2)])

    print('\nSession plan is: \n', np.array(final_task_seq ))

    sessplan = os.path.join(
        odir, 'sub-%02d' % subject_number, 'ses-%02d' % session_number,
        'plan_sub-%02d' % subject_number + '_ses-%02d' % session_number + \
        '.tsv')

    if os.path.exists(sessplan):
        os.remove(sessplan)

    with open(sessplan, "w", newline='') as f:
        a = csv.writer(f, delimiter="\t")
        a.writerows(final_task_seq)


# %%
# ========================== INPUTS ====================================

current_dir = os.path.abspath(os.path.dirname(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

n_train_trials = 5 # no. of trials in training session

n_runs = 4 # behavioral and training
# n_runs = 2 # imaging

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
    session_type = sys.argv[1]
    assert(session_type in ['imaging_session', 'behavioral_session',
                            'training_session']), \
        "Not valid arg for type of stimulus. Please select " + \
        "'imaging_session', 'behavioral_session' or " + \
        "'training_session' to generate randomization for these " + \
        "sessions, respectively."

    if session_type in ['imaging_session', 'behavioral_session']:
        subject_no = int(sys.argv[2])
        session_no = int(sys.argv[3])
        if session_type == 'imaging_session':
            setting = load_config("../imagingsess_config.ini")
        else:
            assert session_type == 'behavioral_session'
            setting = load_config("../behavsess_config.ini")
    else:
        assert session_type == 'training_session'
        subject_no = None
        session_no = None
        setting = load_config("../trainsess_config.ini")

    session = []
    for c in ['production', 'perception', 'notemporal']:
        if (c == 'perception' and session_type == 'behavioral_session' and \
           session_no > 1) or (c == 'notemporal' and \
                               session_type == 'imaging_session' and \
                               session_no == 2):
            nruns = n_runs + 2
        else:
            nruns = n_runs
        if c == 'notemporal' and \
           ((session_type == 'imaging_session' and session_no == 2) or
            session_type == 'training_session'):
            randmods = ['norand', 'rand']
        elif c == 'notemporal' and session_type == 'behavioral_session':
            randmods = ['rand']
        else:
            randmods = ['norand']
        for randmod in randmods:
            for m in ['audio', 'visual']:
                if randmod == 'norand':
                    # Load beat and interval inputs when there's no
                    # NTFD random condition
                    ibeat, iint, fheader, odir = loadinputs(
                        c, m, session_type, subject_no, session_no, current_dir,
                        parent_dir)
                else:
                    # Load beat and interval inputs when there's a
                    # NTFD random condition
                    assert randmod == 'rand'
                    ibeat, iint, fheader, odir = loadinputs(
                        c, m, session_type, subject_no, session_no, current_dir,
                        parent_dir, random=True)

                if randmod == 'rand':
                    # Load NTFD random condition
                    irand = loadrandom(m)
                    r1, r2 = runmap(ibeat, iint, c, m, deviations_list,
                                    inputs_random=irand)
                else:
                    r1, r2 = runmap(ibeat, iint, c, m, deviations_list)

                for rn in np.arange(1, nruns + 1):
                    # Filter
                    if c == 'notemporal':
                        if randmod == 'norand' and rn > nruns/2 + 1:
                            if session_type == 'imaging_session' and \
                               session_no == 2:
                                continue
                            elif session_type == 'training_session':
                                continue
                            else:
                                pass
                        if randmod == 'rand' and rn < nruns/2 + 1:
                            if session_type == 'imaging_session' and \
                               session_no == 2:
                                continue
                            elif session_type == 'training_session':
                                continue
                            else:
                                pass
                    # Randomize filtered runs
                    if rn % 2 == 0:
                        randstim = randomize_trials(
                            r2, fheader, session_type, n_train_trials, c, m,
                            setting, randmod)
                    else:
                        randstim = randomize_trials(
                            r1, fheader, session_type, n_train_trials, c, m,
                            setting, randmod)
                    inputs = store_file(
                        odir, m + '_' + c + '_run-' + '%02d' % rn + '.tsv',
                        randstim, session_type, c, m, rn)
                    session.append(inputs)

    if session_type in ['imaging_session', 'behavioral_session']:
        session_dir = os.path.join(parent_dir,
                                   session_type.replace('_', '-') + 's_inputs')

        if session_type == 'behavioral_session':
            if int(session_no) == 1:
                build_behavsess(session, session_dir, n_runs, subject_no,
                                session_no)
            else:
                if int(subject_no) % 2 == 0:
                    build_behavsess(session, session_dir, n_runs, subject_no,
                                    session_no, perception='vaav')
                else:
                    build_behavsess(session, session_dir, n_runs, subject_no,
                                    session_no, perception='avva')
        else:
            assert session_type == 'imaging_session'
            build_imgsess(session, session_dir, n_runs, subject_no, session_no)
