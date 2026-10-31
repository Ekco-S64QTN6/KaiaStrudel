#!/usr/bin/env python3
"""KaiaStrudel — Kaia live-coding music in Strudel, without the Discord bot.

STANDALONE-ONLY FILE: the entry point. Everything it drives is Kaiacord's own code
(utils/audio/strudel_*.py, tracks.py, dj.py; shared byte-for-byte, see sync.py).
Each genre is an arranged track she performs in a real Strudel REPL — intro, groove,
build, drop, break, outro — and takes requests while it plays. No model, no GPU.

    python3 kaiastrudel.py play                  she picks a genre for her mood and the hour
    python3 kaiastrudel.py play techno           a genre (see `genres`)
    python3 kaiastrudel.py play --mood heavy --minutes 20
    python3 kaiastrudel.py play trance --out set.wav --minutes 5   record instead of playing
    python3 kaiastrudel.py genres                the genres
    python3 kaiastrudel.py audition [--calibrate] [GENRE]   tools/maintenance/audition_tracks.py

While a set plays, type a request and press Enter: darker, brighter, faster, slower,
drop, more bass, less drums … (what `!music <request>` does in Kaiacord). `stop` ends it.
The Strudel window shows the code as it plays (music.show_window); `--hide-window`
parks it off-screen.
"""
from __future__ import annotations

import standalone.bootstrap  # noqa: F401  (working directory, log file, discord stand-in)

import argparse
import asyncio
import inspect
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path


def _say(text: str) -> None:
    print(text, flush=True)


async def _requests(session, stop: asyncio.Event) -> None:
    """Lines typed on stdin become DJ requests."""
    loop = asyncio.get_running_loop()
    while not stop.is_set():
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:                      # stdin closed (not a terminal): just play
            return
        text = line.strip()
        if not text:
            continue
        if text.lower() in ("stop", "quit", "exit", "off"):
            stop.set()
            return
        result = await session.request(text, who="you")
        _say(f"  kaia: {result.reply}" if result.understood else f"  kaia: {result.reply or 'not sure what you want there.'}")


async def cmd_play(a) -> int:
    from utils.audio import dj, strudel_session
    from utils.audio.strudel_patterns import genre_names
    from utils.core.kaia_art_intent import feeling_word, mood
    from utils.infrastructure.system.yaml_config import config
    from standalone.speaker import SpeakerChannel
    if a.mood:
        os.environ["KAIA_MOOD"] = a.mood
    if a.hide_window:
        config.set("music.show_window", False)
    genres = genre_names()
    if a.genre:
        if a.genre not in genres:
            _say(f"no genre {a.genre!r}; one of: {', '.join(genres)}")
            return 1
        genre, why = a.genre, "you asked for it"
    else:
        genre, why = dj.pick_genre(mood(), datetime.now().hour, genres)
    _say(f"starting {genre} — {why} (mood: {feeling_word(mood())}). Chromium and the audio capture take a few seconds…")
    channel = SpeakerChannel(out=Path(a.out) if a.out else None)
    session = await strudel_session.start_session(channel, genre=genre, requested_by="you")
    _say("playing" + (f" → writing {a.out}" if a.out else " on the speakers")
         + ". type a request (darker, faster, drop, more bass…) and Enter; `stop` or Ctrl+C to end.")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    asker = asyncio.create_task(_requests(session, stop)) if sys.stdin and sys.stdin.isatty() else None
    end = time.time() + a.minutes * 60 if a.minutes else None
    while not stop.is_set() and session in strudel_session.active_sessions() and (end is None or time.time() < end):
        try:
            await asyncio.wait_for(stop.wait(), 1.0)
        except asyncio.TimeoutError:
            pass
    if asker:
        asker.cancel()
    await session.stop()
    st = session.stats()
    _say(f"set over: {genre}, {st.get('uptime_min', 0):.1f} min" + (f", {session.requests} requests" if session.requests else ""))
    return 0


def cmd_genres(a) -> int:
    from utils.audio.strudel_patterns import GENRES, genre_names
    for g in genre_names():
        _say(f"{g:14} {GENRES[g].get('cpm', '')}")
    return 0


def cmd_audition(a) -> int:
    import runpy
    sys.argv = ["audition_tracks.py"] + a.rest
    runpy.run_path("tools/maintenance/audition_tracks.py", run_name="__main__")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="kaiastrudel", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("play", help="perform a set")
    p.add_argument("genre", nargs="?", help="a genre; none: she picks for her mood and the hour")
    p.add_argument("--mood", help="wired, restless, tired, hollow, bright, heavy, calm or curious")
    p.add_argument("--minutes", type=float, help="stop after this long")
    p.add_argument("--out", help="write the set to this WAV instead of the speakers")
    p.add_argument("--hide-window", action="store_true", help="park the Strudel window off-screen")
    sub.add_parser("genres", help="list the genres")
    au = sub.add_parser("audition", help="solo and measure every part (tools/maintenance/audition_tracks.py)")
    au.add_argument("rest", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    fn = {"play": cmd_play, "genres": cmd_genres, "audition": cmd_audition}[a.cmd]
    return asyncio.run(fn(a)) if inspect.iscoroutinefunction(fn) else fn(a)


if __name__ == "__main__":
    sys.exit(main())
