# Unified Protocols

All protocols produce the stimuli timings based off a given subject's folder found in the input directory.
## Organization

| Directory | Contents |
| --- | --- |
| [`behavioral-sessions_inputs/`](behavioral-sessions_inputs) | Timings for behavioural sessions nested by subject, session, task, modality, then run number.  |
| [`imaging-sessions_inputs/`](imaging-sessions_inputs) | Timings for imaging sessions nested by subject, session, task, modality, then run number.|
| [`training-session_inputs/`](training-session_inputs) | Timings for training sessions nested by task and modality. The study was designed so that all particiapnts receive the same timings in their training.|
## Inputs pipeline
Inputs are generated in the [`generate_inputs/`](../../generate_inputs) directory. This inputs folder is used by both the Exypriment and PsychoPy scripts under [`unified_protocols/`](../). 

The behavioral and imaging session directories contain a similar heirarchy of folders: subject number, then session number, then task type (NTFD, perception, production), modality (audio, visual), which finally contains the `.tsv` file for each run.

```text
subject_number/
└── session_number/
    └── task_type/
        └── modality/
            ├── _run-01.tsv
            ├── _run-02.tsv
            └── ...
```

Note that each session directory contains a session plan `.tsv` which contains the order of tasks in their modalities for a given session. The session plan is generated alongside the other inputs, and is utilized by `script_runner.py` and some Expyriment scripts. 

