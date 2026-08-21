# TDTB Protocols

Behavioral Protocols of the *Timing Domain Task Battery* (TDTB). The analysis of the data
collected with these protocols is in
[alpinho/tdtb_analysis](https://github.com/alpinho/tdtb_analysis).

The battery crosses three tasks (production, perception, and non-temporal feature
discrimination) with two temporal conditions (beat and interval) and two sensory modalities
(auditory and visual), over a training session, three behavioral sessions and two imaging
sessions. This repository holds everything needed to generate the stimuli, run the sessions,
and check what was actually delivered.

## Organization

Each directory has its own README with the details.

| Directory | Contents |
| --- | --- |
| [`generate_inputs`](generate_inputs) | Generation of the trial tables: interval timing, trial types, assignment of trials to runs and of runs to sessions |
| [`unified_protocols`](unified_protocols) | The task scripts themselves, in Expyriment (`expy_protocols`) and PsychoPy (`pp_protocols`), with their configuration files, instructions, audio stimuli and the generated input tables (`inputs`) |
| [`video_annotations`](video_annotations) | Screen recordings of one run of each task and modality |
| [`physical_onsets`](physical_onsets) | Validation of the timing actually delivered, measured externally and compared with the nominal timing |
| [`logfiles_validation`](logfiles_validation) | Diagnostic checks on the log files released by the protocols |

## Launching a session

Sessions are launched from the runner of the corresponding implementation:
`unified_protocols/script_runner.py` for the mixed PsychoPy and Expyriment sessions, and
`expy_protocols/music-sdtb_menu.py` for the Expyriment battery. Both read the session plan
and the run files under `unified_protocols/inputs`, and write their log files alongside.
`video_annotations` shows what each launch looks like.

Requirements: Python 3.10 with PsychoPy for `pp_protocols`, and Python 3.7.11 with Expyriment
0.10.0 for `expy_protocols` (see `expy_protocols/requirements.txt`). The stimulus timing
assumes a 60 Hz display.

## Authors

- Ana Luísa Pinho, 2022 - present
- Anmar Alsibaie, 2025 - present
