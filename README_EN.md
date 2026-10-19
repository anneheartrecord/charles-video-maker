# charles-video-maker

English | [中文](README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/Node-20.10%2B-339933.svg)](https://nodejs.org/)
[![JavaScript](https://img.shields.io/badge/JavaScript-Canvas%20%7C%20SVG%20%7C%20WebGL-f7df1e.svg)](skills/charles-video-maker/bridge)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-required-007808.svg)](https://ffmpeg.org/)
[![Agent Skill](https://img.shields.io/badge/Agent-Skill-d97757.svg)](skills/charles-video-maker/SKILL.md)

> A written script goes in; a narrated vertical video with subtitles, a cover and publish copy comes out. The picture can be code animation or real footage underneath.

An agent skill. The model writes a page that draws frame t, captured frame by frame into a video; voice, alignment, subtitles, score, fact-checking, rendering, cover and publish copy are one pipeline. On top of that:

- **Footage layer**: screen recordings of a product or game, quotes from a source video, royalty-free b-roll and generated stills, graded and cut on narration cues, with the code picture reduced to a transparent information layer on top.
- **Machines that explain ideas**: a technical idea built as a working isometric machine ([Anatomy](https://github.com/wheresryan22/anatomy)) that does each step as the narration reaches it.
- **Style library (optional)**: the 53 styles of [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar), plus sampled-instrument scores, an offline voice and a reading-time check.

## Four choices at the start

When a video starts, the skill asks four things at once; each has a default:

| Choice | Default | Alternatives |
|---|---|---|
| Picture | code picture | footage underneath (recordings, source quotes, b-roll, generated), or one Lemo-Opuscar style |
| Format | vertical short: 1080×1920, 30 fps, cover as frame 0, a bold claim in the first 5 s | horizontal film: 1920×1080, 24 fps, cinematic pacing |
| Voice | Gemini TTS at 1.25x | edge-tts, Kokoro (offline), none |
| Workflow | three plans with previews, build after approval | ask once and go: write a TREATMENT.md and build |

## How a video is made

```
script ──► fact-check table ──► voice (one take, sped up) ──► word timestamps ──► scene cuts, cues, subtitles
                                                                                     │
          ┌──────────────────────────────────────────────────────────────────────────┘
          ▼
   code picture render(t) ──► frame capture (parallel) ──┐
   footage layer footage.json ──► cut, grade, fade ──────┼──► composite ──► out/<topic>.mp4 + cover + publish.txt
   score + effects + voice ──► -14 LUFS ─────────────────┘
```

- **Voiceover pipeline**: the narration is synthesized in one take and Whisper word timestamps are aligned back to the script text, so scene changes, on-screen actions, sound effects and subtitles land on the spoken words, and recognition mistakes never reach the subtitles.
- **Footage layer**: `record.py` records a web page through Chrome's screencast, re-timed to a constant frame rate; `source.py` downloads and transcribes a source video and finds where a sentence is said; `stock.py` searches Pexels / Pixabay and builds a numbered contact sheet; `compose.py` composites footage, the transparent code layer and the voice, splices in quotes with their own sound, and reports the material mix and missing credits.
- **Quality gates**: a fact-check gate (numbers in the script and on screen must be in the table), a sheet of every scene at its fullest, a reading-time check, frame-count checks, loudness and true-peak checks.
- **Delivery**: the video and cover are named after the title; `publish.txt` holds only the title, the description and 5 tags.

## Results

**The dial indicator (Anatomy's smallest example), narrated**: the carriage slides when the narration says so, and the probe drops onto each gauge block as it is named.

![Dial indicator video](examples/dial-indicator-video.png)

**The Raptor engine (with a WebGL plume)**: hover takes it apart into 11 assemblies, leaving puts it back, and on ignition the WebGL plume fires in the same isometric camera.

![Raptor engine video](examples/raptor-engine-video.png)

## Install

```bash
npx skills add anneheartrecord/charles-video-maker
```

Or copy it manually:

```bash
git clone https://github.com/anneheartrecord/charles-video-maker.git
cp -r charles-video-maker/skills/charles-video-maker ~/.claude/skills/
```

### Requirements

- Python 3.9+ with `numpy`, `scipy` and `playwright` (`python3 -m pip install numpy scipy playwright`), then `python3 -m playwright install chromium`
- FFmpeg
- Node.js 20.10+ (Anatomy's builds and checks use only built-in modules)
- Voice: the `GEMINI_API_KEY` environment variable (Gemini TTS), or `edge-tts` (free, `uv tool install edge-tts`)
- Whisper for alignment: `mlx-whisper` on Apple Silicon, `faster-whisper` elsewhere; or run `uv run --with mlx-whisper ...`
- Footage layer, optional: `yt-dlp` (source videos), `PEXELS_API_KEY` or `PIXABAY_API_KEY` (b-roll, free), `GEMINI_API_KEY` with image quota (generated stills)
- Style library, optional: `sh skills/charles-video-maker/scripts/lemo/setup.sh deps` downloads Lemo-Opuscar to `~/lemo-opuscar` and installs its packages (about 350 MB; needs Node 20+ and Python 3.11+ or uv); the sample libraries are about 1.3 GB more

Keys are read from environment variables only and never written to any file.

## Usage

Just say what you want:

```text
Turn this article into a 60-second vertical video with voiceover and subtitles (text attached)
```

```text
Make an intro video for this web game from real gameplay: https://...
```

```text
Here is the source video and my script; use clips from it and b-roll, not just illustrations
```

```text
Make a vertical video about CDN cache hits and misses, explained by a working machine
```

```text
A 45-second watercolor film about tea, from picking to brewing
```

## Layout

```
skills/charles-video-maker/
  SKILL.md                 routing (video / figure / machine explainer) + four choices + the video workflow
  references/              plans, brief, craft rules, cover and opening, voiceover, fact-check,
                           machine explainer, footage layer, style library
  scripts/                 rendering (parallel, transparent output), fact-check, QA sheet, naming, audio tools
  scripts/voice/           voice, alignment, timeline and subtitles, mix, sampled scores
  scripts/footage/         recording, source quotes, b-roll, generated stills, compositing
  scripts/lemo/            style library setup
  templates/               vertical explainer template
  bridge/                  virtual clock, video overlay, page wrapper, example
  anatomy/                 Anatomy vendored as-is
examples/                  images for this README
```

## Credits and license

- The video workflow, references and rendering scripts started from [xilo-opus-video](https://github.com/Kianzzz/xilo-opus-video) by [周行 (Kianzzz)](https://github.com/Kianzzz).
- `anatomy/` is [Anatomy](https://github.com/wheresryan22/anatomy) by [Ryan (@wheresryan22)](https://github.com/wheresryan22), vendored unmodified.
- The style library, sampled-instrument scoring, Kokoro voice and reading-time check come from [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) by LemoLab, downloaded on demand and not copied into this repository.
- Sources, versions and changes are in [NOTICE.md](NOTICE.md); plans in [ROADMAP.md](ROADMAP.md).

MIT, keeping every original copyright notice. See [LICENSE](LICENSE).
