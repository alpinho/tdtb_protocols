# Music Single-Domain Task Battery (Music-SDTB): stimulus timing and randomization

This document specifies how the trial tables of the Music-SDTB are constructed: the
inter-stimulus intervals (ISIs) that define every trial, and the assignment of trials to
runs and of runs to sessions.

Two scripts implement the specification:

| Script | Output |
| --- | --- |
| `generate_isi.py` | Condition-level stimulus tables (one TSV per task x condition x modality) |
| `randomization.py` | Per-participant, per-session run files and the session plan |

The tables produced here are format-neutral: the same TSV files drive both the Expyriment
and the PsychoPy implementations of the battery. Requirements: Python 3.7.11 with NumPy;
session parameters are read from `behavsess_config.ini`, `imagingsess_config.ini` or
`trainsess_config.ini` through `confparser.load_config`.

---

## 1. Terminology: the interval columns are onset-to-onset

The columns named `isi_1` ... `isi_5` in every table hold **onset-to-onset intervals**, that
is, the time from the onset of one pacing event to the onset of the next. The formal name for
this quantity is the **stimulus onset asynchrony (SOA)**: the interval between the beginning
of one stimulus and the beginning of the following one. It is not the interstimulus interval
in the strict sense, which is defined from the *offset* of one stimulus to the *onset* of the
next; ISI and SOA differ by exactly one stimulus duration and coincide only when stimulus
duration is held constant (Colman, *A Dictionary of Psychology*, OUP). In the rhythm, beat
perception and sensorimotor-synchronization literature the same onset-to-onset quantity is
conventionally called the **inter-onset interval (IOI)** (e.g. Repp, 2005; Repp & Su, 2013),
and that is the term used for the pacing intervals of isochronous and non-isochronous
sequences.

Throughout this document the intervals are therefore referred to as SOAs, with IOI as the
equivalent term in the rhythm literature. The column labels retain the historical `isi_`
prefix for backward compatibility with the existing input files and analysis pipeline; they
should be read as SOAs, and any downstream description of the stimuli should use SOA or IOI
rather than ISI.

The onset-to-onset reading is what the code implements: a trial advances the run clock by
`sum(isi) + stim_duration + ...`, adding the stimulus duration once — for the final event —
rather than once per event, as an offset-to-onset definition would require.

---

## 2. Trial structure

A trial is a sequence of discrete pacing events — a tone in the auditory modality, a flash
in the visual modality — separated by the SOAs `isi_1`, `isi_2`, ... Each row of a stimulus
table is one trial.

| Task | SOAs per trial | Participant's response |
| --- | --- | --- |
| Production | `isi_1`–`isi_4` (5 events) | Continues the sequence by tapping |
| Perception | `isi_1`–`isi_5` (6 events) | Judges the final SOA `isi_5` against the standard |
| Non-temporal feature discrimination (NTFD) | `isi_1`–`isi_5` (6 events) | Identifies a non-temporal feature of the final event |

Every task is run in two temporal conditions, **beat** and **interval**, and in two sensory
modalities, **auditory** and **visual**. The NTFD task has an additional **random**
condition (Section 7.2).

---

## 3. Display-timing constraint

All SOAs of the pacing sequence are integer numbers of milliseconds divisible by 16 or by 17.
These are the two integer approximations of the 16.67 ms frame period of a 60 Hz display, so
every pacing event in the visual tasks falls on, or immediately adjacent to, a vertical
retrace and no SOA accumulates a systematic one-frame delay. The same constraint is applied
to the auditory tables so that the two modalities are timing-matched.

The only SOAs exempt from this constraint are the perception comparison intervals `isi_5`,
which are obtained by scaling a standard and rounding to the nearest millisecond (Section 6).

---

## 4. Standards (`isi_1`, `isi_3`)

Candidate standards are all values in 450–700 ms divisible by 16 or 17, which yields 29
values. Every sixth candidate is retained, giving **five standard SOAs**:

| Standard | 459 | 510 | 561 | 612 | 663 |
| --- | --- | --- | --- | --- | --- |
| ms | 459 | 510 | 561 | 612 | 663 |

The five values are equally spaced (51 ms) and have a mean of 561 ms. The 450–700 ms window
was chosen so that the standards fall in, or just above, the 450–600 ms range over which
beat perception is most accurate.

`isi_3` is set equal to `isi_1` in every task and condition. Each standard defines one trial
type; trial identifiers are `beat01`–`beat05`, `interval01`–`interval05` and
`random01`–`random20`.

---

## 5. Temporal conditions

### 5.1 Beat

```
isi_2 = isi_4 = 3 * isi_1
```

Every SOA of the trial is an integer multiple of a single underlying period, so the sequence
is metrically regular.

| `isi_1` = `isi_3` (ms) | 459 | 510 | 561 | 612 | 663 |
| --- | --- | --- | --- | --- | --- |
| `isi_2` = `isi_4` (ms) | 1377 | 1530 | 1683 | 1836 | 1989 |
| First-to-last onset (ms) | 3672 | 4080 | 4488 | 4896 | 5304 |

### 5.2 Interval

`isi_2` is drawn at random from the values divisible by 16 or 17 lying between three times
the smallest and three times the largest standard, i.e. 1377–1989 ms. `isi_4` is then fixed
by

```
isi_4 = 6 * isi_1 - isi_2
```

Draws are repeated until all of the following hold across the five trial types:

1. `isi_4` is also divisible by 16 or 17;
2. `isi_2` != `isi_4` within every trial;
3. mean(`isi_2`) = mean(`isi_4`) = 3 x mean(`isi_1`) = 1683 ms.

No SOA of an interval-condition trial is a common multiple of a single period, so the
sequence carries no periodic beat.

### 5.3 What the two conditions share

Because `isi_2 + isi_4 = 6 * isi_1` in both conditions, a beat trial and the interval trial
built on the same standard span the **same total time from first to last onset**, `8 * isi_1`,
and have the same mean SOA. Averaged over the five standards, that span is 4488 ms and the
mean of `isi_2` (and of `isi_4`) is 1683 ms. Condition therefore contrasts temporal structure
with total duration, number of events, and mean SOA held constant.

A separate draw of `isi_2` is made for each task, so the interval-condition values in the
production and perception tables are not identical; the constraints above hold within each
table.

---

## 6. Perception: comparison SOA (`isi_5`)

The comparison SOA is a proportional deviation from the standard:

```
isi_5 = round(isi_1 * (1 + d)),  d in {-0.20, -0.12, -0.02, +0.02, +0.12, +0.20}
```

| `isi_1` | -20 % | -12 % | -2 % | +2 % | +12 % | +20 % |
| --- | --- | --- | --- | --- | --- | --- |
| 459 | 367 | 404 | 450 | 468 | 514 | 551 |
| 510 | 408 | 449 | 500 | 520 | 571 | 612 |
| 561 | 449 | 494 | 550 | 572 | 628 | 673 |
| 612 | 490 | 539 | 600 | 624 | 685 | 734 |
| 663 | 530 | 583 | 650 | 676 | 743 | 796 |

The six deviations are symmetric about zero, so the mean of `isi_5` is 561 ms — equal to the
mean of `isi_1` — in both conditions and both modalities. Crossing 5 standards with 6
deviations gives **30 trials per condition**, and fixes the number of repetitions of each
trial type at six for every task (Section 8).

---

## 7. Non-temporal feature discrimination (NTFD)

### 7.1 Beat and interval conditions

`isi_5` is set equal to `isi_1`, so the trial spans `9 * isi_1` from first to last onset and
the temporal structure matches the corresponding production trial. Each trial carries a
target feature, given in the `target_shape` column:

| Modality | Features |
| --- | --- |
| Auditory | low and high pure tone (`audiowav_low` / `audiowav_high` in the session config; the high tone is 880 Hz) |
| Visual | circle and triangle |

Features alternate row by row, so the two levels are exactly balanced within every table.

### 7.2 Random condition

The random condition preserves the total duration of an NTFD beat trial while removing any
temporal regularity. For each standard, the first four SOAs are drawn from the values
divisible by 16 or 17 lying between `isi_1` and `5 * isi_1`, and the fifth is set to `isi_1`;
sequences are redrawn until

```
isi_1 + isi_2 + isi_3 + isi_4 + isi_5 = 9 * isi_1
```

Consequently the standard is both the shortest SOA a random trial can contain (459 ms for the
shortest standard) and the SOA that terminates it, and the first-to-last onset span equals
that of its beat and interval counterparts. Four sequences are generated per standard,
giving 20 random trials per modality; target features alternate as in Section 7.1.

---

## 8. Size of the stimulus tables

| Table | Repetitions per standard | Trials |
| --- | --- | --- |
| `production_beat`, `production_interval` | 6 | 30 |
| `perception_beat`, `perception_interval` | 6 (one per deviation) | 30 |
| `notemporal_{beat,interval}_{audio,visual}` (`ntfd_no_random/`) | 6 | 30 |
| `notemporal_{beat,interval}_{audio,visual}` (`ntfd_random/`) | 4 | 20 |
| `notemporal_random_{audio,visual}` | 4 | 20 |

In the production and NTFD tables the repetitions of a trial type are identical rows; in the
perception tables they differ by the comparison SOA.

---

## 9. Construction of runs

`randomization.py` turns the stimulus tables into run files. It is run once per participant
and session:

```
python randomization.py behavioral_session <subject_number> <session_number>
python randomization.py imaging_session   <subject_number> <session_number>
python randomization.py training_session
```

### 9.1 Splitting into two run maps

For each task and modality, the row indices of the condition tables are shuffled and split
into two halves, **A** and **B**. The *same* index set selects rows from the beat, the
interval and, where present, the random table, so the three conditions are matched trial type
by trial type within a run. A split is accepted only if all of the following hold:

1. mean `isi_2` is equal in A and B within the beat condition;
2. mean `isi_2` is equal in A and B within the interval condition;
3. mean `isi_2` is equal between the beat and interval conditions;
4. **perception only** — each of the six deviations occurs at least `n/6` times (rounded
   down) in each half;
5. **NTFD only** — each of the two target features occurs in exactly half the trials of each
   half.

Each map therefore holds 30 trials: 15 beat + 15 interval, or, when the random condition is
present, 10 beat + 10 interval + 10 random.

Odd-numbered runs are built from map A and even-numbered runs from map B. Runs drawn from the
same map contain the same trials in a different order.

### 9.2 Baseline trials

Rest (baseline) trials are added at a rate of one per six task trials, i.e. five per run.
They are marked `baseline` in `trial_id`, carry `-` in all SOA columns and are not numbered.

### 9.3 Trial order

The 35 rows are shuffled until:

1. no baseline occupies the first, second, second-to-last or last position;
2. no two identical rows are adjacent or separated by a single row. Because baseline rows are
   identical to one another, this prevents baselines at lag 1 and lag 2; it also separates
   repeated identical trials in the production and NTFD tables.

### 9.4 Onsets

Onsets are cumulative from the start of the run. The first onset is `WAIT` for auditory runs
and `between_tasks_duration` for visual runs. Each trial then advances the clock by

```
sum(isi) + stim_duration + feedback_duration + within_block_duration
```

where `sum(isi)` is the first-to-last onset span of the trial and `stim_duration` covers the
final event, and each baseline advances it by `baseline_duration`. All four durations are
read from the session configuration file, so onsets follow the timing of the session for
which the run was generated.

---

## 10. Session composition

The protocol comprises one training session, three behavioural sessions and two imaging
sessions. Every task is administered in both modalities in every session.

| Session | Production | Perception | NTFD |
| --- | --- | --- | --- |
| Training | 4 runs | 4 runs | 2 runs beat/interval + 2 runs random |
| Behavioural 1 | 4 runs | 4 runs | 4 runs (beat/interval/random) |
| Behavioural 2, 3 | 4 runs | 6 runs | 4 runs (beat/interval/random) |
| Imaging 1 | 2 runs | 2 runs | 2 runs beat/interval |
| Imaging 2 | 2 runs | 2 runs | 2 runs beat/interval + 2 runs random |

Run counts are per modality. Training runs contain five trials each, drawn from the maps of
Section 9.1 with the two conditions balanced; all other runs contain 30 task trials and five
baselines.

### 10.1 Coverage of the perception design

Two runs of a given task and modality together contain each (standard, comparison) pair
exactly once. The number of observations per pair therefore follows the number of runs:

| Session | Perception runs per modality | Trials per (standard, comparison) |
| --- | --- | --- |
| Behavioural 1 | 4 | 2 |
| Behavioural 2 | 6 | 3 |
| Behavioural 3 | 6 | 3 |
| Imaging 1 | 2 | 1 |
| Imaging 2 | 2 | 1 |
| **Total** | | **10** (8 behavioural, 2 imaging) |

### 10.2 Order of runs within a session

The order of runs is written to `plan_sub-XX_ses-XX.tsv` and is counterbalanced as follows.

**Behavioural sessions.** Runs are grouped in blocks of two consecutive run numbers and
shuffled within each group, subject to the constraint that the task ending one group differs
from the task starting the next. In sessions 2 and 3 the two additional perception runs per
modality are appended at the end, in the order audio–visual–visual–audio for odd-numbered
participants and visual–audio–audio–visual for even-numbered participants.

**Imaging sessions.** Within each run, the two modalities alternate in an AV/VA pattern; the
pattern is reversed for odd participants in even sessions and for even participants in odd
sessions, so modality order is counterbalanced across participants and sessions. Task order is
shuffled within the first and second halves of the session. In imaging session 2 the four
NTFD-random runs are appended, with modality order set by participant parity.

---

## 11. Output files

### 11.1 Stimulus tables (`generate_isi.py`)

```
production/          production_beat.tsv, production_interval.tsv
perception/          perception_beat.tsv, perception_interval.tsv
ntfd_no_random/      notemporal_{beat,interval}_{audio,visual}.tsv
ntfd_random/         notemporal_{beat,interval}_{audio,visual}.tsv
                     notemporal_random_{audio,visual}.tsv
```

Columns: `trial_id`, `isi_1`–`isi_4` (production) or `isi_1`–`isi_5` (perception), and
`isi_1`–`isi_5` plus `target_shape` (NTFD). All interval columns are SOAs in milliseconds
(Section 1).

### 11.2 Run files (`randomization.py`)

```
behavioral-sessions_inputs/sub-XX/ses-XX/inputs_<task>_sub-XX_ses-XX/<modality>/<modality>_<task>_run-XX.tsv
imaging-sessions_inputs/  sub-XX/ses-XX/inputs_<task>_sub-XX_ses-XX/<modality>/<modality>_<task>_run-XX.tsv
training-session_inputs/  inputs_<task>/<modality>/<modality>_<task>_run-XX.tsv
```

with the session plan at `<sessions>_inputs/sub-XX/ses-XX/plan_sub-XX_ses-XX.tsv`.

Run files add two columns in front of the stimulus-table columns:

| Column | Content |
| --- | --- |
| `onsets` | Onset of the trial from the start of the run, in ms |
| `trial_number` | Sequential index over task trials; `-` for baselines |

All files are tab-separated with a header row. Existing files in a target directory are
deleted when run 1 is written, so a re-run replaces a session cleanly.

### 11.3 Column dictionary

Definitions for every column that appears in a stimulus table or a run file. Columns are
listed in the order in which they occur; `onsets` and `trial_number` are present in run files
only.

| Column | Type | Unit | Present in | Definition |
| --- | --- | --- | --- | --- |
| `onsets` | integer | ms | run files | Onset of the trial relative to the start of the run, measured to the onset of the trial's first pacing event. Cumulative; see Section 9.4. |
| `trial_number` | integer or `-` | — | run files | Sequential index over task trials within the run, starting at 1. `-` on baseline rows, which are not counted. |
| `trial_id` | string | — | all | Trial type. `beatNN` and `intervalNN` index the five standards (`NN` = 01–05); `randomNN` indexes the 20 NTFD random sequences (`NN` = 01–20); `baseline` marks a rest row. |
| `isi_1` | integer | ms | all | **Onset-to-onset interval (SOA/IOI)** from the first to the second pacing event. This is the *standard* of the trial: one of 459, 510, 561, 612, 663 ms. `-` on baseline rows. |
| `isi_2` | integer | ms | all | SOA from the second to the third pacing event. `3 * isi_1` in the beat condition; a constrained random draw in the interval condition (Section 5.2); a random draw in the NTFD random condition (Section 7.2). |
| `isi_3` | integer | ms | all | SOA from the third to the fourth pacing event. Equal to `isi_1` in the beat and interval conditions. |
| `isi_4` | integer | ms | all | SOA from the fourth to the fifth pacing event. Equal to `isi_2` in the beat condition; `6 * isi_1 - isi_2` in the interval condition. |
| `isi_5` | integer | ms | perception, NTFD | SOA from the fifth to the sixth pacing event. In perception it is the *comparison*, `round(isi_1 * (1 + d))` for a deviation `d` (Section 6). In NTFD it equals `isi_1`. |
| `target_shape` | string | — | NTFD | Non-temporal feature of the final event to be discriminated: `circle` or `triangle` in the visual modality, the value of `audiowav_low` or `audiowav_high` from the session config in the auditory modality. |

Notes that apply to every interval column:

- All values are **onset-to-onset**, not offset-to-onset; see Section 1. The duration of the
  pacing event itself is `stim_duration` in the session configuration and is not included in
  any `isi_*` value.
- All values are integer milliseconds divisible by 16 or by 17, with the single exception of
  the perception comparison `isi_5` (Section 3).
- Baseline rows carry `-` in every interval column and in `target_shape`.
- Column names use the `isi_` prefix for backward compatibility with previously generated
  input files and with the analysis pipeline. The prefix is historical and does not describe
  the quantity; read the columns as SOAs.

---

## 12. Reproducing the tables

1. Select the session type in `generate_isi.py` by uncommenting the corresponding
   `load_config` line; this determines the auditory stimulus names used for the NTFD target
   feature.
2. Generate each table, e.g. `python generate_isi.py production_beat`. Valid arguments are
   `production_{beat,interval}`, `perception_{beat,interval}`,
   `notemporal_{beat,interval}_{audio,visual}` and `notemporal_random_{audio,visual}`.
3. The production and perception tables are written to the working directory; move them into
   `production/` and `perception/` before running the randomization.
4. The beat and interval tables in `ntfd_random/` use four repetitions rather than six, to
   match the 20 trials of the random table. They are produced by the `random=True` calls in
   the `__main__` block of `generate_isi.py`, which must be enabled for this step.
5. Set `n_runs` in `randomization.py` to 4 for behavioural and training sessions and to 2 for
   imaging sessions, then run the commands in Section 9.

Neither script sets a random seed. The interval-condition SOAs, the random NTFD sequences,
the run maps and the trial orders therefore differ between invocations, and the delivered TSV
files — not the scripts — are the definitive record of what a given participant received.

---

## 13. Summary of fixed parameters

| Parameter | Value |
| --- | --- |
| Interval definition | Onset-to-onset (SOA; IOI in the rhythm literature) |
| Display refresh rate assumed | 60 Hz (SOAs divisible by 16 or 17 ms) |
| Standard range | 450–700 ms |
| Standards | 459, 510, 561, 612, 663 ms (mean 561) |
| `isi_2` in beat condition | 3 x `isi_1` (mean 1683 ms) |
| `isi_2` range in interval condition | 1377–1989 ms (mean 1683) |
| `isi_2 + isi_4` | 6 x `isi_1`, both conditions |
| First-to-last onset (production, perception) | 8 x `isi_1` (mean 4488 ms) |
| First-to-last onset (NTFD, all three conditions) | 9 x `isi_1` |
| Perception deviations | -20, -12, -2, +2, +12, +20 % |
| Task trials per run | 30 |
| Baseline trials per run | 5 |

---

## References

Colman, A. M. *A Dictionary of Psychology*. Oxford University Press (entries *stimulus onset
asynchrony*, *interstimulus interval*).

Repp, B. H. (2005). Sensorimotor synchronization: A review of the tapping literature.
*Psychonomic Bulletin & Review*, 12, 969–992.

Repp, B. H., & Su, Y.-H. (2013). Sensorimotor synchronization: A review of recent research
(2006–2012). *Psychonomic Bulletin & Review*, 20, 403–452.

---

*Scripts by Ana Luísa Pinho (agrilopi@uwo.ca). Created April 2022; last updated August 2026.*
