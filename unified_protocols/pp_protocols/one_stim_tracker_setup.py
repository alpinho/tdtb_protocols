#one_stim_tracker_setup.py
"""

- USB → StimTracker using pyxid2
- Pulse width default 80 ms
- Reset base + RT timers on start
- Functions to emit TTL pulses on stimulus onsets (audio vs visual masks)
- NO INPUT INTO COMPUTER! (no iuA1/iuL1, etc.)
- Dummy mode

Usage in a task (audio example):
    from stim_tracker_setup import connect_stimtracker
    st = connect_stimtracker(enabled=True, pulse_ms=80)

    # ... on each beep onset
    st.pulse_audio()
    snd_medium.play()

Visual example:
    win.callOnFlip(st.pulse_visual)
    win.flip()

Close at end:
    st.close()
"""

try:
    import pyxid2  # supervisor used this
except Exception:
    pyxid2 = None  # allow import to fail on different computers


# =========================== defaults ============================
DEFAULT_PULSE_MS = 80
DEFAULT_AUDIO_MASK = 11  # AL used 11 for audio
DEFAULT_VISUAL_MASK = 11  # AL used 12 for visual


# ========================= no-op adapter =========================
class _NoOpStimTracker: #dummy
    """Safe drop-in when hardware is disabled, missing, or dummy.
    Methods do nothing but keep the task code simple.
    """
    def __init__(self, enabled=False, pulse_ms=DEFAULT_PULSE_MS,
                 audio_mask=DEFAULT_AUDIO_MASK, visual_mask=DEFAULT_VISUAL_MASK):
        self.enabled = bool(enabled)
        self.pulse_ms = int(pulse_ms)
        self.audio_mask = int(audio_mask)
        self.visual_mask = int(visual_mask)

    def pulse_audio(self):
        return None

    def pulse_visual(self):
        return None

    def close(self):
        return None


# ========================== real adapter =========================
class _StimTrackerEEGOnly:
    """
    - set_pulse_duration(ms)
    - reset_base_timer(), reset_rt_timer()
    - activate_line(bitmask=...)
    """

    def __init__(self, dev, pulse_ms=DEFAULT_PULSE_MS,
                 audio_mask=DEFAULT_AUDIO_MASK, visual_mask=DEFAULT_VISUAL_MASK,
                 verbose=False):
        self._dev = dev
        self.pulse_ms = int(pulse_ms)
        self.audio_mask = int(audio_mask)
        self.visual_mask = int(visual_mask)
        self.verbose = bool(verbose)

        # Configure once at start (parity with supervisor)
        try:
            self._dev.set_pulse_duration(self.pulse_ms)
        except Exception as e:
            if self.verbose:
                print("[StimTracker] set_pulse_duration failed: %s" % e)

        for fn in ("reset_base_timer", "reset_rt_timer"):
            try:
                getattr(self._dev, fn)()
            except Exception as e:
                if self.verbose:
                    print("[StimTracker] %s failed: %s" % (fn, e))

        if self.verbose:
            print("[StimTracker] ready — pulse=%dms, audio_mask=%d, visual_mask=%d" % (
                self.pulse_ms, self.audio_mask, self.visual_mask))

    # --------------- pulses on demand ---------------
    def pulse_audio(self):
        """Fire a TTL pulse for audio events (bitmask=audio_mask)."""
        try:
            self._dev.activate_line(bitmask=self.audio_mask)
        except Exception as e:
            if self.verbose:
                print("[StimTracker] pulse_audio failed: %s" % e)

    def pulse_visual(self):
        """Fire a TTL pulse for visual events (bitmask=visual_mask)."""
        try:
            self._dev.activate_line(bitmask=self.visual_mask)
        except Exception as e:
            if self.verbose:
                print("[StimTracker] pulse_visual failed: %s" % e)

    def close(self):
        # Nothing required for parity; keep method for symmetry
        if self.verbose:
            print("[StimTracker] closed")
        return None


# ======================== connection helper ======================
def connect_stimtracker(enabled=True, dummy=False, pulse_ms=DEFAULT_PULSE_MS,
                        audio_mask=DEFAULT_AUDIO_MASK, visual_mask=DEFAULT_VISUAL_MASK,
                        verbose=False):
    """Create the EEG-style adapter or a dummy (no-op).

    Parameters
    ----------
    enabled : bool
        If False, returns a no-op adapter.
    dummy : bool
        If True, returns a no-op adapter regardless of hardware.
    pulse_ms : int
        TTL pulse width in milliseconds. Default 80 ms.
    audio_mask : int
        Bitmask used when pulsing audio events. Default 11.
    visual_mask : int
        Bitmask used when pulsing visual events. Default 12.
    verbose : bool
        Print diagnostics on errors.
    """
    if not enabled or dummy:
        return _NoOpStimTracker(enabled=False, pulse_ms=pulse_ms,
                                audio_mask=audio_mask, visual_mask=visual_mask)

    if pyxid2 is None:
        if verbose:
            print("[StimTracker] pyxid2 not available; using no-op")
        return _NoOpStimTracker(enabled=False, pulse_ms=pulse_ms,
                                audio_mask=audio_mask, visual_mask=visual_mask)

    try:
        devices = [d for d in pyxid2.get_xid_devices() if d is not None]
    except Exception as e:
        if verbose:
            print("[StimTracker] device discovery failed: %s" % e)
        return _NoOpStimTracker(enabled=False, pulse_ms=pulse_ms,
                                audio_mask=audio_mask, visual_mask=visual_mask)

    if not devices:
        if verbose:
            print("[StimTracker] no XID devices found; using no-op")
        return _NoOpStimTracker(enabled=False, pulse_ms=pulse_ms,
                                audio_mask=audio_mask, visual_mask=visual_mask)

    # Prefer a device whose string mentions StimTracker; otherwise take first
    dev = None
    for d in devices:
        if "StimTracker" in str(d):
            dev = d
            break
    if dev is None:
        dev = devices[0]

    try:
        return _StimTrackerEEGOnly(dev, pulse_ms=pulse_ms,
                                   audio_mask=audio_mask,
                                   visual_mask=visual_mask,
                                   verbose=verbose)
    except Exception as e:
        if verbose:
            print("[StimTracker] init failed (%s); falling back to no-op" % e)
        return _NoOpStimTracker(enabled=False, pulse_ms=pulse_ms,
                                audio_mask=audio_mask, visual_mask=visual_mask)
