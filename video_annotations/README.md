# Video annotations

Screen recordings of the sequence of events displayed at every run of the TDTB, one per
task and sensory modality. They document what a participant actually sees and hears, so that
the protocol can be inspected without installing and launching the code.

| File | Task | Modality | Launcher entry | Duration |
| --- | --- | --- | --- | --- |
| `audio_production.mp4` | Production | Auditory | 11) Audio Production - training | 80 s |
| `audio_perception.mp4` | Perception | Auditory | 13) Audio Perception - training | 84 s |
| `audio_ntfd.mp4` | Non-temporal feature discrimination | Auditory | 15) Audio No-Temporal FD - training | 85 s |
| `visual_production.mp4` | Production | Visual | 17) Visual Production - training | 82 s |
| `visual_perception.mp4` | Perception | Visual | 19) Visual Perception - training | 84 s |
| `visual_ntfd.mp4` | Non-temporal feature discrimination | Visual | 21) Visual No-Temporal FD - training | 84 s |

## What each recording shows

Every video is a capture of the experimenter's screen, from launch to the end of
the run:

1. selection of the task in the `music-sdtb_menu.py` menu of the Expyriment implementation
   (`../unified_protocols`);
2. the Expyriment prompts for participant, session and run number;
3. the initialization of the run;
4. the run itself — fixation, the sequence of pacing events, the response window and the
   feedback of each trial.

The recordings use the **training** version of each task, which runs only five trials. 
The trial timing, the trial types and the composition of a full run are specified in 
[`../generate_inputs/README.md`](../generate_inputs/README.md).

## Technical characteristics

The recordings are a qualitative demonstration of the sequence of events. They are not a
timing measurement: capture, encoding and playback all resample the display, so intervals
should not be estimated from the videos. Measurements of the physical onsets actually
delivered by the protocols are in [`../physical_onsets`](../physical_onsets).
