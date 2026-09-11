
# Expyriment Protocols

## Organization

| Script or Directory | Contents |
| --- | --- |
| [`audio_stim/`](audio_stim) | Audio wav files used as stimuli |
| [`requirements.txt`](requirements.txt) | Python package requirements |
| [`music-sdtb_menu.py`](music-sdtb_menu.py) | Main menu for launching scripts including instructions, training, and behavioral tasks, via GUI |
| [`music-sdtb_bauto.py`](music-sdtb_bauto.py) | Continously launch scripts via CLI |
| [`music-sdtb_bauto_single.py`](music-sdtb_bauto_single.py) | Launch a single script via CLI|
| [`audio_protocols.py`](audio_protocols.py),<br> [`visual_protocols.py`](visual_protocols.py),<br> [`audio_protocols_explicit.py`](audio_protocols_explicit.py),<br> [`visual_protocols_explicit.py`](visual_protocols_explicit.py)| Functions for running tasks |
| [`instructions_production.tsv`](instructions_production.tsv),<br> [`instructions_perception.tsv`](instructions_perception.tsv),<br> [`instructions_notemporal.tsv`](instructions_notemporal.tsv),<br> [`instructions_notemporal_withrandom.tsv`](instructions_notemporal_withrandom.tsv),<br>[`instructions_production_explicit.tsv`](instructions_production_explicit.tsv),<br>[`instructions_perception_explicit.tsv`](instructions_perception_explicit.tsv),<br> [`instructions_notemporal_explicit.tsv`](instructions_notemporal_explicit.tsv),<br> [`instructions_notemporal_withrandom_explicit.tsv`](instructions_notemporal_withrandom_explicit.tsv) | Instruction texts|
| [`menu_config.ini`](menu_config.ini),<br> [`instructions_config.ini`](instructions_config.ini),<br> [`trainsess_config.ini`](trainsess_config.ini),<br> [`behavsess_config.ini`](behavsess_config.ini),<br> [`imagingsess_config.ini`](imagingsess_config.ini),<br> [`pc1.ini`](pc1.ini),<br> [`pc2.ini`](pc2.ini) | Configuration files |
| [`confparser.py`](confparser.py),<br> [`instructions.py`](instructions.py),<br> [`utils.py`](utils.py),<br> [`sessrun_numbers.py`](sessrun_numbers.py) | Helper files |

## Using `music-sdtb_menu.py`
### Launch

The proper Expyriment environment must be activated in-terminal before launching the script.

```bash
python music-sdtb_menu.py <system>
```

With the arguments being:

- `<system>` - operating system, accepts `win` or `lin`

Example:

```bash
python music-sdtb_menu.py win
```

### Navigation

Use the `Up Arrow` and `Down Arrow` to go through the menu, `Enter` to launch a script, and `Control` + `Q` to quit the menu entirely. 

Once a script is launched, further arguments are prompted via GUI dialogue, including `subject_number`, `session_number`, and `run_number` 

## Using `music-sdtb_bauto.py`

`music-sdtb_bauto.py` launches tasks via CLI, and automatically carries on to the next task, in accordance with the task's placement on the session plan in `inputs/`

```bash
python music-sdtb_bauto.py <system> <subject_number> <session_number> <line_number>
```

With the arguments being:

- `<system>` - Operating system, accepts `win` or `lin`
- `<subject_number>` - With or without leading zeros (`09` and `9` both work)
- `<session_number>` - With or without leading zeros (`02` and `2` both work)
- `<line_number>` - The task order according to the session plan in `inputs`, starting at `1` for the first task

Example:

```bash
python music-sdtb_bauto.py win 09 2 1
```
Quit the program via `Control` + `Q`

## Using `music-sdtb_bauto_single.py`

`music-sdtb_bauto_single.py` uses the same arguments as `music-sdtb_bauto.py`, but only launches a single task, quitting automatically afterwards. 
Example:

```bash
python music-sdtb_bauto_single.py win 09 2 1
```
Internally, `music-sdtb_bauto_single.py` is used by `script_runner.py` to launch Expyriment scripts one at a time.

## Notes
- If a window is not centered correctly at launch, try quitting the program and relaunching.
