# CLAUDE.md — KaiaStrudel

KaiaStrudel is Kaia's live-coded music from the Kaiacord Discord bot, runnable on its
own: each genre is an arranged track she performs in a real Strudel REPL (in a headed
Chromium, captured from a PipeWire null sink), following its form and taking requests
(darker, faster, drop…) as edits to the running program. No model, no GPU. **Kaiacord is
the mother project.** This repo exists so the music can be worked on, tested and used
without the bot, and every improvement goes back to Kaiacord.

## The one rule: shared files stay byte-identical with Kaiacord

`sync.json` lists the **shared files** (`utils/audio/strudel_*`, `tracks.py`, `dj.py`,
`assets/strudel/`, some tools and tests). They are copies of Kaiacord's files at the same relative path, and the same file
runs in both places. Everything else is **standalone-only** and says so in its header.

| Shared (edit carefully, it runs in Kaiacord too) | Standalone-only (this repo's own) |
|:--|:--|
| `utils/audio/strudel_engine.py`, `strudel_session.py`, `strudel_patterns.py`, `tracks.py`, `dj.py`, … (see `sync.json`) | `kaiastrudel.py` (entry point), `standalone/` (bootstrap, discord stand-in, `speaker.py`), `utils/core/kaia_art_intent.py` (mood), `utils/infrastructure/system/yaml_config.py`, `config/`, `conftest.py`, `sync.py`, docs |

So, for a shared file:

- **Don't add standalone hacks to it.** If the standalone needs different behaviour, put it
  in a standalone-only file (the entry point, `standalone/`, the config loader) — or make
  the shared code configurable through `config.get(...)` with Kaiacord's default unchanged.
- **Don't rename or move it** without doing the same in Kaiacord (and `sync.json`).
- **It must still work inside Kaiacord**, where `discord` is the real library and the bot,
  Ollama and the voice thread are running. Kaiacord's rules for this code apply here
  unchanged: read `docs/kaiacord/CLAUDE.md` (a read-only copy, refreshed by `sync.py pull`):
  §7 "Music Engine" up to "`!music records`" (the browser runs headed, patterns are
  applied by clicking a real button, PULSE_SINK only in Chromium's environment, a track is
  arranged not accumulated, levels are measured — each rule learned from silence), §9 (logging,
  telemetry that lies, check the payload), §11 (working practice).
- **Kaia's mood** is `utils/core/kaia_art_intent.py` here, a standalone stand-in for the
  two functions the music reads (`mood`, `feeling_word`). In Kaiacord the same path is her
  live mood engine and her art; don't add it to `sync.json`.
- New shared files: add them in Kaiacord first (or here, then list them in `sync.json`
  and push), so both sides have them.

## Workflow

```bash
python3 sync.py pull                 # before starting: take Kaiacord's latest
# … work, then test here:
venv/bin/python -m pytest -q
python3 sync.py status               # what you changed (local), what Kaiacord changed (upstream)
python3 sync.py push                 # send your shared-file changes to ../Kaiacord
# then in Kaiacord: run its suite and commit there (its CLAUDE.md §2, §13)
```

`sync.lock.json` records each shared file's hash at the last sync (commit it; never edit
it by hand). A file changed on both sides is a **conflict**: merge by hand, then
`sync.py pull --force PATH` or `push --force PATH`. A push never deletes a file in
Kaiacord unless named with `--force`.

## Tests

`venv/bin/python -m pytest -q` runs Kaiacord's Strudel tests unchanged (`tools/tests/`,
shared) plus this repo's own (`tests/`). A shared test that needs a Kaiacord-only module
(the bot's background tasks, the RAG index) is reported as *skipped: Kaiacord-only*, by
`conftest.py`; any other failure is real. Add tests for shared code to the shared test
files (or a new shared test file) so Kaiacord runs them too.

## Running

`python3 kaiastrudel.py --help`. Settings in `config/local.yaml` override
`config/default_config.yaml` (same keys as Kaiacord's `music:` section). Logs go to
`logs/kaiastrudel.log`. The set plays through `standalone/speaker.py` (pw-cat / paplay /
aplay / ffplay), or into a WAV with `--out`. Kaiacord's bot uses the same null sink
(`kaia_music`): don't run a KaiaStrudel set while the bot plays a live set.

## Verify behaviour, not just syntax

As in Kaiacord: a change is done when you have heard it work — a real set
(`kaiastrudel.py play GENRE`), or one written with `--out` and measured — not when the
tests pass. A part changed in a track is re-measured with `kaiastrudel.py audition
--calibrate GENRE`; a part it reports SILENT is broken. A Strudel eval error keeps the old
program playing, so "it still plays" proves nothing about the new code.
