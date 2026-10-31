"""The local speakers as a "voice channel" (STANDALONE-ONLY FILE).

Kaiacord plays music by handing a discord.AudioSource to a VoiceClient, whose voice
thread calls source.read() for 20 ms of 48 kHz stereo s16le (3,840 bytes) at a time.
The shared session code does exactly that — `channel.connect()`, `vc.play(source)`,
`vc.is_playing()`, `channel.members` — so this module offers the same names, and the
player thread writes each frame to a local audio player instead of Discord:
pw-cat (PipeWire), else paplay (PulseAudio), else aplay (ALSA), else ffplay. With
`out=` it writes a WAV file instead (headless runs, tests).

The audio player's buffer paces the reads: a write blocks once it is full, so the
source is read at real time, as Discord's 20 ms clock would.
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
import threading
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

FRAME_BYTES = 3840          # 20 ms of 48 kHz stereo s16le
RATE, CHANNELS = 48000, 2


def player_command() -> Optional[list[str]]:
    if shutil.which("pw-cat"):
        return ["pw-cat", "--playback", "--rate", str(RATE), "--channels", str(CHANNELS), "--format", "s16",
                "--latency", "100ms", "-"]
    if shutil.which("paplay"):
        return ["paplay", "--raw", f"--rate={RATE}", f"--channels={CHANNELS}", "--format=s16le"]
    if shutil.which("aplay"):
        return ["aplay", "-q", "-f", "S16_LE", "-r", str(RATE), "-c", str(CHANNELS)]
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-loglevel", "error", "-f", "s16le", "-ar", str(RATE), "-ac", str(CHANNELS), "-"]
    return None


@dataclass
class Listener:
    display_name: str
    bot: bool = False


@dataclass
class SpeakerGuild:
    id: int = 1
    name: str = "local"
    voice_client: Optional["SpeakerVoice"] = None


@dataclass
class SpeakerChannel:
    """A voice channel with one listener in it: you. Sessions stop when a channel
    empties, so there is always someone here until the program stops."""
    name: str = "speakers"
    listener: str = "you"
    out: Optional[Path] = None              # write a WAV here instead of playing
    guild: SpeakerGuild = field(default_factory=SpeakerGuild)

    @property
    def members(self) -> list[Listener]:
        return [Listener(self.listener)]

    async def connect(self, timeout: float = 30.0, reconnect: bool = True) -> "SpeakerVoice":
        vc = SpeakerVoice(self)
        self.guild.voice_client = vc
        return vc


class SpeakerVoice:
    """discord.VoiceClient, for the speakers."""

    def __init__(self, channel: SpeakerChannel) -> None:
        self.channel = channel
        self.guild = channel.guild
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._connected = True
        self.frames = 0                      # frames played, for status lines and tests

    # ── what the sessions call ──
    def is_connected(self) -> bool:
        return self._connected

    def is_playing(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def is_paused(self) -> bool:
        return False

    def play(self, source, *, after: Optional[Callable] = None, signal_type: str = "music", **_) -> None:
        if self.is_playing():
            raise RuntimeError("Already playing audio.")
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, args=(source, after), daemon=True, name="speaker")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=5)

    async def disconnect(self, force: bool = False) -> None:
        await asyncio.to_thread(self.stop)
        self._connected = False
        if self.guild.voice_client is self:
            self.guild.voice_client = None

    async def move_to(self, channel) -> None:
        self.channel = channel

    # ── the player thread ──
    def _run(self, source, after) -> None:
        error = None
        sink = None
        try:
            sink = _WavSink(self.channel.out) if self.channel.out else _ProcessSink()
            while not self._stop.is_set():
                frame = source.read()
                if not frame:
                    break
                if not sink.write(frame):
                    # No audio player could take it: keep time so the source is paced.
                    time.sleep(0.02)
                self.frames += 1
        except Exception as e:                  # what discord.py hands to after()
            error = e
        finally:
            if sink:
                sink.close()
            if after:
                try:
                    after(error)
                except Exception:
                    pass


class _ProcessSink:
    def __init__(self) -> None:
        cmd = player_command()
        if cmd is None:
            raise RuntimeError("no audio player found: install PipeWire (pw-cat), PulseAudio (paplay), "
                               "ALSA (aplay) or ffmpeg (ffplay)")
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def write(self, frame: bytes) -> bool:
        try:
            self.proc.stdin.write(frame)
            return True
        except (BrokenPipeError, ValueError):
            return False

    def close(self) -> None:
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()


class _WavSink:
    """A WAV file, written at real time (20 ms per frame) like the speakers."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.w = wave.open(str(path), "wb")
        self.w.setnchannels(CHANNELS)
        self.w.setsampwidth(2)
        self.w.setframerate(RATE)
        self.t = time.monotonic()

    def write(self, frame: bytes) -> bool:
        self.w.writeframes(frame)
        self.t += 0.02
        delay = self.t - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        return True

    def close(self) -> None:
        self.w.close()
