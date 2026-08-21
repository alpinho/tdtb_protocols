# Physical onsets

Validation of the timing that the protocols actually deliver. The scripts in this directory
compare the **physical onsets** of the stimuli — recorded outside the presentation computer
with a photodiode and a microphone connected to a Cedrus StimTracker, sampled at 2048 Hz —
with the **nominal onsets** specified by the input tables in
[`../generate_inputs`](../generate_inputs). They were used to compare the Expyriment and
PsychoPy implementations, the standard and pre-scheduled (PTB) PsychoPy back-ends, and
several audio buffer sizes.

Each script documents its own purpose and outputs in its header; this README gives the shape
of the pipeline, how to launch the scripts and what the input tables look like.

## The pipeline

The work proceeds in three stages. Every stage writes TSV files that the next stage reads.

**1. Nominal timing.** `build_theoretical_durations.py` reads one run input TSV produced by
the randomization (`<modality>_<task>_run-XX.tsv`) and expands it into one row per interval,
labelled by its role in the trial.

**2. Curation.** `xlsx2tsv.py` splits a multi-sheet Excel export from the recording software
into one TSV per sheet. The `curation_*.py` scripts then parse the recordings, discard TTL
and artefact rows, segment the event stream into trials, align each recording with the
nominal table, and compute the rendered durations and their errors. There is one curation
script per measurement campaign, because each used a different implementation and a different
event-coding scheme:

| Script | Measurement campaign |
| --- | --- |
| `curation_expy2.py` | July 2025 — Expyriment with TTL pulse |
| `curation_st.py` | February 2026 — PsychoPy, standard back-end |
| `curation_ptb.py` | February 2026 — PsychoPy, pre-scheduled (PTB) back-end |
| `curation_ptb-st_audio.py` | April 2026 — PsychoPy, auditory protocols, both back-ends, several audio buffer sizes |

**3. Analysis.** All the analysis scripts consume the curated long tables:

| Script | Question |
| --- | --- |
| `jittering_analysis.py` | How large is the timing error, in ms, and how often does it exceed a fixed threshold? |
| `rhythm_fidelity.py` | How far does each rendered interval depart from its own nominal, as a proportion of that nominal? |
| `beat_regularity_analysis.py` | How often does the auditory Beat depart from its nominal structure by more than a perceptually relevant fraction? |
| `timing_randomness.py` | Does the error reproduce across repeated replays of the same sequence, i.e. could it be corrected post hoc? |
| `comparison_flip_analysis.py` | In the perception task, does the rendered comparison ever fall on the wrong side of its standard? |
| `lags.py` | What is the lag between the physical onset of an event and the CPU-time pulse that marks it? |

Outputs are TSV summaries, RTF and Excel reports, and PDF figures, written next to the
scripts. `rhythm_metrics_overview.tex` documents the candidate rhythm-fidelity metrics that
were considered and the reasoning behind the one that was kept.

## Running the scripts

Every script is standalone and takes no command-line arguments. Configure it by editing the
configuration block at the top of the file, then run it from this directory:

```
python build_theoretical_durations.py
python curation_st.py
python jittering_analysis.py
```

What to edit in each case:

| Script | Set |
| --- | --- |
| `build_theoretical_durations.py` | `subject`, `session_type`, `session`, `run_number`, `task`, `modality` in the `INPUTS` section. One run per invocation. |
| `xlsx2tsv.py` | `input_dir`, `xlsx_file`, `out_dir` |
| `curation_*.py` | `input_dir`, `theoretical_dir`, `output_dir`, and the campaign constants (subject, modalities, expected measurements, output filenames) in the `Inputs` section |
| `jittering_analysis.py`, `rhythm_fidelity.py`, `beat_regularity_analysis.py`, `comparison_flip_analysis.py` | `TAG` — one key of `INPUT_FILES`, or a list of keys plus an `OUT_TAG` to pool them. `beat_regularity_analysis.py` also takes `MODALITY` and `CONDITION`. |
| `timing_randomness.py` | `INPUT_FILES` — the curated tables of the sessions to be compared |
| `lags.py` | `session_name` — one key of `session_configs` |

Requirements: Python 3.10.16 with pandas, numpy, matplotlib and seaborn.

The recordings themselves are not distributed in this repository. The scripts expect the raw
measurement directories (`data_*`) and the curated outputs (`curated_data_*`,
`theoretical_durations`) alongside them; the paths are set in the configuration blocks.

## Shape of the inputs

**Raw measurement file** — one TSV per recording, exported from the StimTracker software.
Rows are events in acquisition order; the relevant columns are the event label
(`markerLabel` or `type`, e.g. a sensor detection, a tone onset or a TTL), the event code
(`eventCode` / `EventCode`), and the latency, given either in samples at 2048 Hz (`latency`)
or already in milliseconds (`onsetLatency_ms`, `onset2onset_durations_ms`). Filenames encode
the task, participant, session, run and repetition, e.g.
`AuditoryProduction_P03_S1R1_1.tsv`.

**Nominal durations table** — the output of `build_theoretical_durations.py`, one row per
interval:

| Column | Content |
| --- | --- |
| `task` | `production`, `perception` or `ntfd` |
| `subject`, `modality` | Participant and `audio` / `visual` |
| `condition` | `beat` or `interval`, from `trial_id` with the trial-type index dropped |
| `trial` | Trial number within the run; baseline rows are dropped |
| `theoretical_durations` | Nominal interval, in ms, taken from the `isi_*` columns of the run file |
| `duration_type` | Role of the interval: `standard`, `soa1`, `soa2`, or `comparison` |

Rows follow the fixed order `standard, soa1, standard, soa2` for production, with a fifth row
that is `comparison` for perception and `standard` for NTFD.

**Curated long table** — the output of the `curation_*.py` scripts and the input to every
analysis script. It repeats the six nominal columns above and adds:

| Column | Content |
| --- | --- |
| `measurement` | Index of the repeated recording of the same sequence |
| `onsets` | Physical onset of the event, in ms from the start of the recording |
| `durations` | Rendered interval, onset to onset, in ms |
| `error` | `durations - theoretical_durations`, in ms |

One row is therefore one interval, of one trial, in one recording. The analysis scripts stack
these tables across campaigns, which is why the interval role (`duration_type`) and the
recording identity (`measurement`) both have to be columns rather than filename conventions.
