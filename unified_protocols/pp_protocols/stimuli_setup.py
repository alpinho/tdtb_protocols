# stimuli_setup.py
import os
from pathlib import Path

# ================== DETECT EXTERNAL (Steinberg/Yamaha UR) FIRST ==================
STEINBERG_HINTS = [
    "Steinberg", "Yamaha Steinberg USB",
    "UR22", "UR12", "UR24", "UR44", "UR28M", "UR824",
]

def _steinberg_present_via_sounddevice():
    """Detect Steinberg/Yamaha output devices using the 'sounddevice' package (no psychopy.sound import)."""
    try:
        import sounddevice as sd
        devs = sd.query_devices()
        # Prefer default output first
        try:
            def_out = sd.default.device[1]
        except Exception:
            def_out = None
        order = list(range(len(devs)))
        if def_out is not None and 0 <= def_out < len(devs):
            order = [def_out] + [i for i in order if i != def_out]

        def _is_steinberg(name: str) -> bool:
            name = name or ""
            return any(h.lower() in name.lower() for h in STEINBERG_HINTS)

        # Check default, then others
        for i in order:
            d = devs[i]
            if int(d.get("max_output_channels", 0)) > 0 and _is_steinberg(str(d.get("name", ""))):
                return True, str(d.get("name", ""))
        for d in devs:
            if int(d.get("max_output_channels", 0)) > 0 and _is_steinberg(str(d.get("name", ""))):
                return True, str(d.get("name", ""))
    except Exception:
        pass
    return False, None

_HAS_STEINBERG, _STEINBERG_NAME = _steinberg_present_via_sounddevice()

# ================== IMPORTS (ORDER DIFFERS BASED ON DETECTION) ===================
from psychopy import logging
logging.console.setLevel(logging.INFO)

set_sample_rate = 48000 #44100 or 48000
set_buffer = 0.01 #from 0.05 to 0.01
set_latency_mode =1 # 1, 2 or 3 (strictest)

# ==================== AUDIO FILE NAMES (single source of truth) ====================
# Change a beep file here ONCE; every protocol (standard + explicit) uses it via
# stimuli_setup. Handy for testing beeps of other amplitudes (esp. the soft beep).
BEEP_LOW_FILE    = "beep_220hz_stereo.wav"
BEEP_MEDIUM_FILE = "beep_440hz_stereo.wav"
BEEP_HIGH_FILE   = "beep_880hz_stereo.wav"
BEEP_SOFT_FILE   = "beep_440hz_amp0p05_stereo.wav"   # softer beep for explicit subdivisions
# Log "condition" labels are derived from the file names, so the log tracks the
# file actually used (change a name above and the label follows).
BEEP_MEDIUM_CONDITION = os.path.splitext(BEEP_MEDIUM_FILE)[0]
BEEP_SOFT_CONDITION   = os.path.splitext(BEEP_SOFT_FILE)[0]

if _HAS_STEINBERG:
    # --- Steinberg present: set prefs BEFORE importing psychopy.sound ---
    from psychopy import prefs
    prefs.hardware['audioLib']       = ['ptb']
    prefs.hardware['audioLatencyMode'] = set_latency_mode
    prefs.hardware['audioSampleRate']  = set_sample_rate
    prefs.hardware['audioChannels']    = 2
    prefs.hardware['audioDevice']      = _STEINBERG_NAME
    logging.info(f"Steinberg detected → PTB. Device: {_STEINBERG_NAME}")

    # Now import sound after prefs so PTB opens cleanly at 48k
    from psychopy import event, core
    import psychopy.visual
    from psychopy import sound
    try:
        try:
            sound.init(rate=set_sample_rate, stereo=True, buffer=set_buffer)
        except TypeError:
            sound.init(sampleRate=set_sample_rate, stereo=True, buffer=set_buffer)
        _SR = set_sample_rate
        logging.info(f"PTB init OK at {set_sample_rate}, buffer = {set_buffer} and Latency Mode {set_latency_mode}")
    except Exception as e:
        raise RuntimeError(f"PTB init failed: {e}")

    from psychopy import prefs
    print("AUDIO CHECK:",
      "audioLib=", prefs.hardware.get("audioLib"),
      "latencyMode=", prefs.hardware.get("audioLatencyMode"),
      "device=", prefs.hardware.get("audioDevice"),
      "sr_var=", _SR,
      "sound.audioLib=", getattr(sound, "audioLib", None))
else:
    # --- No Steinberg: keep your original behavior (this path worked for you) ---
    from psychopy import event, core
    import psychopy.visual
    import psychopy.sound as sound  # import early, as in your original file
    from psychopy import prefs
    prefs.hardware['audioLib'] = ['ptb']
    prefs.hardware['audioChannels'] = 2
    try:
        sound.init(stereo=True, buffer=set_buffer)
    except TypeError:
        sound.init(stereo=True, buffer=set_buffer)
    _SR = None
    logging.info("No Steinberg device. Using system default backend (original path).")


# --- paths ---
HERE = Path(__file__).resolve().parent
audio_dir = HERE / "audio_stim"
if not audio_dir.exists():
    raise FileNotFoundError(f"Missing folder: {audio_dir}")

def wav(name: str) -> str:
    p = audio_dir / name
    if not p.exists():
        raise FileNotFoundError(f"Missing audio: {p}")
    return str(p)

# --- helper for creating Sound with/without forced SR ---
def _snd(path):
    """Create a Sound; use 48k only on Steinberg/PTB path, else let file/driver decide."""
    return sound.Sound(path, sampleRate=(_SR or None), stereo=True, hamming=True)


# ================================ WINDOW =======================================
HZ = 60.0                # fixed refresh rate
FRAME = 1.0 / HZ

win = psychopy.visual.Window(
    fullscr=True,
    screen=0,
    allowGUI=False,
    color=[127,127,127], colorSpace="rgb255",
    units="height",
    waitBlanking= True,
    checkTiming=False,
    autoLog=False,
)

def hide_cursor():
    try: win.setMouseVisible(False)
    except: pass
    try: event.Mouse(win=win).setVisible(False)
    except: pass
    try: win.winHandle.set_mouse_visible(False)
    except: pass
    try: win.winHandle.set_exclusive_mouse(True)
    except: pass

# --- force backend init before creating any stimuli (as in your file) ---
for _ in range(2):
    win.flip()
core.wait(0.01)

# --- colors ---
purple = [51, 34, 136]
black  = [0, 0, 0]
gray   = [70, 70, 70]

# --- keys ---
startkey = "t"
ttl      = "t"
option1  = "o"
option2  = "p"

# --- kill key ---

# --- kill key (canonical) ---
def kill_check():
    """Immediate abort on Ctrl/Cmd+Q (raise SystemExit)."""
    for k, mods in event.getKeys(keyList=['q'], modifiers=True):
        if k == 'q' and (mods.get('ctrl') or mods.get('command')):
            raise SystemExit

CLOCK = core.Clock()
LAST_CHECK = 0.0
def kill_pressed(interval=5.0):
    """Return True if Ctrl/Cmd+Q pressed, checked only every `interval` seconds."""
    global LAST_CHECK
    now = CLOCK.getTime()
    if now - LAST_CHECK < interval:
        return False
    LAST_CHECK = now
    for k, mods in event.getKeys(modifiers=True):
        if k == "q" and (mods.get("ctrl") or mods.get("command")):
            return True
    return False

# --- fixation crosses (smaller) ---
purple_cross = psychopy.visual.TextStim(win, text="+", color=purple, colorSpace="rgb255", height=0.10)
black_cross  = psychopy.visual.TextStim(win, text="+", color=black,  colorSpace="rgb255", height=0.10)
gray_cross   = psychopy.visual.TextStim(win, text="+", color=gray,   colorSpace="rgb255", height=0.10)

# --- prompts (smaller) ---
text    = psychopy.visual.TextStim(win, text="Higher or Lower?",   color=black, colorSpace="rgb255", pos=(0, 0.35),  height=0.08)
higher  = psychopy.visual.TextStim(win, text="Higher (index)",     color=black, colorSpace="rgb255", pos=(-0.35, -0.35), height=0.05)
lower   = psychopy.visual.TextStim(win, text="Lower (middle)",     color=black, colorSpace="rgb255", pos=(0.35, -0.35),  height=0.05)

text3        = psychopy.visual.TextStim(win, text="Triangle or Circle?", color=black, colorSpace="rgb255", pos=(0, 0.35),  height=0.08)
triangletext = psychopy.visual.TextStim(win, text="Triangle (index)",     color=black, colorSpace="rgb255", pos=(-0.35, -0.35), height=0.05)
circletext   = psychopy.visual.TextStim(win, text="Circle (middle)",      color=black, colorSpace="rgb255", pos=(0.35, -0.35),  height=0.05)

text2   = psychopy.visual.TextStim(win, text="Longer or Shorter?", color=black, colorSpace="rgb255", pos=(0, 0.35),  height=0.08)
longer  = psychopy.visual.TextStim(win, text="Longer (index)",     color=black, colorSpace="rgb255", pos=(-0.35, -0.35), height=0.05)
shorter = psychopy.visual.TextStim(win, text="Shorter (middle)",   color=black, colorSpace="rgb255", pos=(0.35, -0.35),  height=0.05)

# --- timing (s) ---
baselinetime  = 0.0
stim_duration = 0.080
intertrial    = 1.500
onsettime     = 3.000

# --- shapes ---
rect     = psychopy.visual.Rect(win, width=0.30, height=0.60, fillColor=gray, lineColor=gray, colorSpace="rgb255", pos=(0, 0))
SMALL_RECT_CONDITION = "small_rectangle"
small_rect = psychopy.visual.Rect(win, width=0.09, height=0.18, fillColor=gray, lineColor=gray, colorSpace="rgb255", pos=(0, 0))
triangle = psychopy.visual.Polygon(win, edges=3, radius=0.25,       fillColor=gray, lineColor=gray, colorSpace="rgb255", pos=(0, 0))
circle   = psychopy.visual.Circle(win,  radius=0.25, edges=128,     fillColor=gray, lineColor=gray, colorSpace="rgb255", pos=(0, 0))

# --- audio ---
audiowav_medium = _snd(wav(BEEP_MEDIUM_FILE))
beep_220hz      = _snd(wav(BEEP_LOW_FILE))
beep_880hz      = _snd(wav(BEEP_HIGH_FILE))

# ===== MEDIUM BEEP POOL (for avoiding scheduling conflicts) =====
#since ptb cannot schedule the same sound more than once at the same time
MEDIUM_POOL_SIZE = 6

audiowav_medium_pool = [
    _snd(wav(BEEP_MEDIUM_FILE))
    for _ in range(MEDIUM_POOL_SIZE)
]

# index
_medium_idx = 0

def get_medium_beep():
    """
    Return the next available medium beep Sound object.
    Cycles through the pool.
    """
    global _medium_idx
    snd = audiowav_medium_pool[_medium_idx]
    _medium_idx = (_medium_idx + 1) % MEDIUM_POOL_SIZE
    return snd

# ===== SOFTER BEEP (explicit-instruction subdivisions) =====
# Lower-amplitude 440 Hz beep marking the inserted subdivisions in the
# explicit variants (the analogue of the soft/lower beep).
#
# Loaded DEFENSIVELY on purpose: this is an explicit-variant-only asset, so a
# missing file must not break this shared module or the standard protocols.
# If absent we keep going (warning only); the explicit scripts check
# soft_beep_available and fail fast with a clear message.
SOFT_POOL_SIZE = 6
soft_beep_error = None
try:
    audiowav_soft = _snd(wav(BEEP_SOFT_FILE))
    audiowav_soft_pool = [_snd(wav(BEEP_SOFT_FILE)) for _ in range(SOFT_POOL_SIZE)]
    soft_beep_available = True
    logging.info("Soft beep loaded OK: %s" % BEEP_SOFT_FILE)
except Exception as _soft_err:
    audiowav_soft = None
    audiowav_soft_pool = []
    soft_beep_available = False
    soft_beep_error = "%s: %s" % (type(_soft_err).__name__, _soft_err)
    logging.warning(
        "Soft beep NOT loaded -> %s. Standard protocols are unaffected; "
        "explicit variants need BEEP_SOFT_FILE=%r in audio_stim/."
        % (soft_beep_error, BEEP_SOFT_FILE)
    )

_soft_idx = 0

def get_soft_beep():
    """Return the next soft beep from the pool (avoids PTB same-sound scheduling).

    Raises a clear error if the soft beep file was not found at import time.
    """
    if not audiowav_soft_pool:
        raise FileNotFoundError(
            "Missing audio_stim/%s, required for the explicit variant." % BEEP_SOFT_FILE
        )
    global _soft_idx
    snd = audiowav_soft_pool[_soft_idx]
    _soft_idx = (_soft_idx + 1) % SOFT_POOL_SIZE
    return snd
