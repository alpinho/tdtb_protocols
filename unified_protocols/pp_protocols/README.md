# PsychoPy Protocols

## Organization

| Script or Directory | Contents |
| --- | --- |
| [`audio_stim/`](audio_stim) | Audio wav files used as stimuli |
| [`one_st_audio_production.py`](one_st_audio_production.py), [`one_st_audio_perception.py`](one_st_audio_perception.py), [`one_st_audio_NTFD.py`](one_st_audio_NTFD.py), [`one_st_visual_production.py`](one_st_visual_production.py), [`one_st_visual_perception.py`](one_st_visual_perception.py), [`one_st_visual_NTFD.py`](one_st_visual_NTFD.py) | Behavioural tasks in each modality, launched individually via CLI or GUI |
| [`one_st_audio_production_explicit.py`](one_st_audio_production_explicit.py), [`one_st_audio_perception_explicit.py`](one_st_audio_perception_explicit.py), [`one_st_audio_NTFD_explicit.py`](one_st_audio_NTFD_explicit.py), [`one_st_visual_production_explicit.py`](one_st_visual_production_explicit.py), [`one_st_visual_perception_explicit.py`](one_st_visual_perception_explicit.py), [`one_st_visual_NTFD_explicit.py`](one_st_visual_NTFD_explicit.py) | Explicit-instruction training scripts, launched individually via CLI or GUI |
| [`stimuli_setup.py`](stimuli_setup.py), [`utilities.py`](utilities.py) | Helper scripts |
| [`one_stim_tracker_setup.py`](one_stim_tracker_setup.py) | Cedrus StimTracker functionality for physical stimuli validation, off by default|
## Using the scripts
The proper PsychoPy environment must be activated in-terminal before launching the script. 
### Launch via CLI
```bash
python <given_script.py> <system> <subject_number> <session_number> <run_number> <stimtracker_y_n> <session_type>
```
With the arguments being: 

- `<system>` - operating system, accepts `win` or `lin`
- `<subject_number>` - With or without leading zeros (`09` and `9` both work)
- `<session_number>` - With or without leading zeros (`02` and `2` both work)
- `<run_number>` - With or without leading zeros (`04` and `4` both work)
- `<stimtracker_y_n>` - Whether a StimTracker device is being used in the session, `y` or `n`
- `<session_type>` - Desired trial type, `behavioral` or `training`
An example of an input:

```bash
python one_st_audio_production.py win 09 2 4 n behavioral
```
### Launch via GUI
To input arguments via a GUI dialogue, launch the script without CLI arguments.

```bash
python <given_script.py>
```
The GUI dialogue has the same fields explained above. By default, `StimTracker` is set to `n`, excplicit-instruction scripts have `session_type` set to `training`, and non-excplicit scripts have `session_type` set to `behavioral`. 
## Notes
- `<run_number>` is not the session-plan line number. It refers to the a label of a task's trial in `inputs/`
