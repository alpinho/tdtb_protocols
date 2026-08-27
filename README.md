# TDTB Protocols

Behavioral Protocols of the *Timing Domain Task Battery* (TDTB). The analysis of the data
collected with these protocols is in
[alpinho/tdtb_analysis](https://github.com/alpinho/tdtb_analysis).

The battery crosses three **task types** (production, perception, and non-temporal feature
discrimination) with two **temporal structures** (beat and interval), and two **sensory modalities**
(auditory and visual), run over a training session, three behavioral sessions and two imaging
sessions. This repository holds everything needed to generate the stimuli, run the sessions,
and validate what was actually delivered.

## Organization

Each directory has its own README with the details.

| Directory | Contents |
| --- | --- |
| [`generate_inputs/`](generate_inputs) | Generation of the trial tables: interval timing, trial types, assignment of trials to runs and of runs to sessions |
| [`unified_protocols/`](unified_protocols) | The task scripts themselves, using Expyriment (`expy_protocols/`) and PsychoPy (`pp_protocols/`) libraries, with their configuration files, instructions, audio stimuli and the generated input tables (`inputs/`) |
| [`video_annotations/`](video_annotations) | Screen recordings of one run of each task and modality |
| [`physical_onsets/`](physical_onsets) | Validation of the timing actually delivered, measured externally and compared with the nominal timing |
| [`logfiles_validation/`](logfiles_validation) | Diagnostic checks on the log files released by the protocols |

## Task Paradigms
- Stimuli modality:
	- **Audio** - Beeps at 440Hz, 200Hz, or 800Hz
	- **Visual** - Rectangles, traingles, or circles
- Task type:
	- **Production**: Reproduce the temporal invterval of a pair of stimuli
	- **Perception**: Detect whether a pair's temporal interval is longer or shorter than previous pairs
	- **Non-Temporal Feature Discrimination (NTFD)**: Respond as quickly as possible to the correct stimuli change (higher or lower beep, circle or triangle)
- Temporal Structure:
	- **Beat** - For an in-pair interval of x seconds, the next pair will begin after 3x seconds. The structure is akin to 4/4 time in music.
	- **Interval** - For an in-pair interval of x seconds, the next pair begins after an arbitrary amount of time.
- Instruction type:
	- **Explicit** - The task's response requires direct interaction with the task's temporal structure. For example, reproducing an interval in the production task, or judging an interval's longer or shorter length in the perception task.
	- **Implicit** - The task's expected response is not directly related to the temporal structure, though temporal structure facilitates the response. The NTFD task demands a quick response of the stimuli's change, and anticipation for change may be facilitated in a regular, beat temporal structure. 

## Launching a session

Sessions are launched from the runner of the corresponding implementation:
`unified_protocols/script_runner.py` for the mixed PsychoPy and Expyriment sessions, and
`expy_protocols/music-sdtb_menu.py` for the Expyriment battery. Both read the session plan
and the run files under `unified_protocols/inputs`, and write their log files alongside.
`video_annotations` shows what each launch looks like.

Requirements: Python 3.10 with PsychoPy for `pp_protocols`, and Python 3.7.11 with Expyriment
0.10.0 for `expy_protocols` (see `expy_protocols/requirements.txt`). The stimulus timing
assumes a 60 Hz display.

## Notes
Hardware differences may effect the way in which the tasks are delivered, specifically as it pertains to latency and jitter of the stimuli and response detection. It is important to measure CPU times and validate the physical onsets of the stimuli to ensure that the hardware is not compromising the desired temporal structure of the experiment. 

## Authors

- Ana Luísa Pinho, 2022 - present
- Anmar Alsibaie, 2025 - present
