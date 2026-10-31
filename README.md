# KaiaStrudel

Kaia live-coding music in [Strudel](https://strudel.cc), without the Discord bot.

Each genre — ambient, Berlin school, drum & bass, dub, house, deep house, lo-fi,
synthwave, techno, trance, trip-hop, psytrance, acid, breakbeat — is an arranged track:
every part is in the program from the first bar, and per-bar masks and automation decide
what sounds in each section of the form (intro → groove → build → drop → break → build →
drop → outro). She performs it in a real Strudel REPL you can watch: the code, the pattern
that is sounding, the scope.

- **She picks the genre** for her mood and the hour when you don't, and her arousal nudges
  the tempo a few percent.
- **She takes requests while it plays:** *darker, brighter, faster, slower, drop, more
  bass, less drums…* become edits to the lanes that are playing, answered in her voice.
- **No model, no GPU:** the music is arranged code; the levels are measured, not guessed.

It is the live-set engine of [Kaiacord](../Kaiacord) (Kaia, a self-hosted Discord bot),
running the very same code. Where the bot streams into a voice channel, KaiaStrudel plays
on your speakers — or writes the set to a WAV.

## Install

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/playwright install chromium
venv/bin/python tools/maintenance/fetch_music_assets.py   # Strudel itself (AGPL: fetched, never committed)
```

System: a desktop session (Chromium has to run headed: headless Chromium plays pure
silence), PipeWire or PulseAudio with `pactl`, `ffmpeg`, and an audio player (`pw-cat`,
`paplay`, `aplay` or `ffplay`).

## Use

```bash
venv/bin/python kaiastrudel.py genres
venv/bin/python kaiastrudel.py play                 # her pick
venv/bin/python kaiastrudel.py play techno
venv/bin/python kaiastrudel.py play --mood tired --minutes 30
venv/bin/python kaiastrudel.py play trance --out set.wav --minutes 10 --hide-window
venv/bin/python kaiastrudel.py audition --calibrate techno   # solo and measure every part
```

While it plays, type a request and press Enter; `stop` ends the set.

## Working on it (and getting the work back into Kaiacord)

Most of the code is **shared with Kaiacord byte-for-byte** (listed in `sync.json`).
Improve it here, test it here, then:

```bash
python3 sync.py status   # what changed, on which side
python3 sync.py push     # copy your changes into ../Kaiacord (then test and commit there)
python3 sync.py pull     # take Kaiacord's changes
```

Rules for AI agents and people alike are in [CLAUDE.md](CLAUDE.md).

## Licence

The code is Kaiacord's (MIT, see Kaiacord). Strudel (AGPL) runs from `assets/strudel/`;
its samples and soundfonts load from their own hosts at play time.
