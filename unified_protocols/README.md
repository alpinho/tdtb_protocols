# Unified Protocols

The TDTB used the Exypriment and PsychoPy libraries to minimize jitter with the equipement at hand, for the visual and auditory tasks respectively. Tasks may be run using `script_runner.py`, or one at a time as explained in their respective folders.
## Organization

| Script or Directory | Contents |
| --- | --- |
| [`script_runner.py`](script_runner.py) | Launching the protocols using a command line interface (CLI) in the order of the session plan found in `inputs/` |
| [`inputs/`](inputs) | Stimuli onsets per-trial for each task-type and modality in a given behavioural, imaging, or training session. Also contains the order of tasks for a given session |
| [`expy_protocols/`](expy_protocols) | Expyriment-coded scripts, to be launched individually via a GUI (`music-sdtb_menu.py`) or continuously via a CLI (`music-sdtb_bauto.py`) in the order of the session plan|
| [`pp_protocols/`](pp_protocols) | Psychopy-coded scripts, with tasks run individually via GUI or CLI |
## Running the experiment using `script_runner.py`
Environment filepaths for the Expyriment and PsychoPy scripts must be set-up in the `script_runner.py` before launch.
### Launch command
```bash
python script_runner.py <system> <subject_number> <session_number> <line_number>
```
With the arguments being: 

- `<system>` - Operating system, accepts `win` or `lin`
- `<subject_number>` - With or without leading zeros (`09` and `9` both work)
- `<session_number>` - With or without leading zeros (`02` and `2` both work)
- `<line_number>` - The task order according to the session plan in `inputs`, starting at `1` for the first task

An example of an input:

```bash
python script_runner.py win 09 2 1
```
### Navigation while running
In between trials, the runner will display the previous and next task. Press `Enter` to launch the next task, `B` to move back one line in the session plan, `N` to skip forward to the next line, and `Q` to quit `script_runner.py` entirely. 

The following is an example of what is displayed in-terminal:

```bash
--------------------------------------------------
Previous: audio perception run 2 | line 6
Next:     visual production run 1 | line 7
Press ENTER to continue, B to go back, N to go next, or Q to quit:
--------------------------------------------------
```

## Notes
- The environment paths must be configured inside of the `script_runner.py` code itself.
- Line numbers for the task order start at 1. 
- `script_runner.py` uses Expyriment scripts for the visual tasks, and PsychoPy scripts for the auditory tasks.
