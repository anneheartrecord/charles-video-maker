<div align="center">

![charles-video-maker](examples/banner.jpg)

# charles-video-maker

**A script goes in; a finished video with voice, subtitles, cover and publish copy comes out. The picture is drawn by code, frame by frame.**

English | [中文](README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/Node-20.10%2B-339933.svg)](https://nodejs.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-required-007808.svg)](https://ffmpeg.org/)
[![Agent Skill](https://img.shields.io/badge/Agent-Skill-d97757.svg)](skills/charles-video-maker/SKILL.md)

</div>

## A zero-follower account, 13 days, 370K views

On 2026-10-20 a new Douyin account was started with this skill's Douyin mode. No paid promotion. A person picks the topic and does the final review; everything from script to publishing is done by the pipeline.

| Total views | Best single video | Most shares on one video | Ad spend |
|:---:|:---:|:---:|:---:|
| **370K+** | **231K** | **7,053** | **0** |

### Showcase

| [![The least happy year](examples/douyin-happiness-u.jpg)](https://www.douyin.com/video/7700211164583873834) | [![Six wins](examples/douyin-winner-effect.jpg)](https://www.douyin.com/video/7699389178563300651) | [![Franklin effect](examples/douyin-franklin-effect.jpg)](https://www.douyin.com/video/7700210236262567168) |
|:---:|:---:|:---:|
| **At what age is your life least happy?** | **Feel you're worse than everyone? Maybe you just haven't won 6 times** | **Want someone to like you? How the Franklin effect works** |
| 78 s · 231K views | 66 s · 99K views | 71 s · 13K views |
| 7,053 shares · 2,537 comments | 1,441 saves · 102 new followers | 373 likes · 178 saves |
| [▶ Watch on Douyin](https://www.douyin.com/video/7700211164583873834) | [▶ Watch on Douyin](https://www.douyin.com/video/7699389178563300651) | [▶ Watch on Douyin](https://www.douyin.com/video/7700210236262567168) |

Numbers as of 2026-11-02. The same pipeline has also produced videos with a few dozen views: reach is mostly decided by the topic and the first 3 seconds; the tool keeps the finished quality at a steady level.

## Start in 30 seconds

```bash
npx skills add anneheartrecord/charles-video-maker
```

Then tell your agent what you want:

```text
Turn this article into a 60-second vertical video with voiceover and subtitles
```

## What it does

| Capability | In one line | Good for |
|---|---|---|
| **Code animation** | The model writes a page that draws frame t; frames are captured and composited into a video | explainers, data stories, product intros |
| **Footage underneath** | Recordings, source-video quotes, royalty-free b-roll and generated stills sit under a transparent code layer | product demos, game intros, commentary |
| **Machines that explain** | A technical idea built as a working isometric machine that does each step as the narration reaches it | deep technical explainers |
| **Douyin knowledge-video mode** | Start from a video that is taking off, then topic, style, script, score, render, publish and stats run end to end | growing an account, batches of short explainers |
| **Style library** (optional) | The 53 styles of [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) plus sampled-instrument scores | films that need a specific look |

Every video passes quality gates: every number must be in the fact-check table, every scene is checked on a contact sheet, and reading time, frame count, loudness and true peak are verified.

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

- **Voiceover pipeline**: the narration is synthesized in one take and Whisper word timestamps are aligned back to the script, so scene changes, actions, sound effects and subtitles land on the spoken words, and recognition mistakes never reach the subtitles.
- **Footage layer**: `record.py` records a web page, `source.py` downloads and transcribes a source video and finds where a sentence is said, `stock.py` searches royalty-free b-roll, and `compose.py` composites footage, the transparent code layer and the voice.
- **Delivery**: the video and cover are named after the title; `publish.txt` holds only the title, the description and 5 tags.

## Douyin knowledge-video mode

All three showcase videos came from this mode. It does not start from an idea; it starts from a video that is taking off. The style is matched one to one, the content is never copied, and picture, texture and timing are pushed past the original. One request authorizes the whole run; it stops to ask only when no primary source can be found or the same tool fails twice in a row.

```
D-1 topic radar ──► D1 distill style ──► D2 sources & script ──► D3 score first, then picture ──► D4 build & self-check ──► D5 deliver
 douyin_radar        style library        gemini_copy             voiceover-pipeline                still_check               cover, publish.txt
                                                                                                                                │
                          findings written back to the ops handbook ◄── douyin_stats / douyin_comments ◄── douyin_publish ◄───┘
```

| Step | What it does |
|---|---|
| **Topic radar** | `douyin_radar.py` ranks the videos rising under a hashtag and produces 10 to 20 topics |
| **The first 3 seconds** | `douyin-opening.md` takes apart the openings of top videos, with checklists for picture, first line and sound |
| **Script** | `gemini_copy.py` hands narration and title to a local Gemini; the skill checks facts and structure |
| **Still check** | `still_check.py` finds stretches where the picture stops for more than 2 seconds, and subtitle changes the picture doesn't follow |
| **Publishing and stats** | `douyin_publish.py` schedules the video, `douyin_stats.py` pulls 2-second bounce, 5-second completion, likes, saves and shares, `douyin_comments.py` saves comments |
| **Series** | `douyin-series.md` turns one-offs into a series with one world and one recurring character |

You set up two things yourself: a working directory (default `~/Desktop/video/vibe-video/`) for source videos, the style library and projects, and an ops handbook you maintain for topic rules and findings. Without the handbook, videos still come out; the read-the-handbook and write-back steps are skipped.

## More results

| **Dial indicator** (Anatomy's smallest example) | **Raptor engine** (with a WebGL plume) |
|:---:|:---:|
| ![Dial indicator video](examples/dial-indicator-video.png) | ![Raptor engine video](examples/raptor-engine-video.png) |
| The carriage slides when the narration says so; the probe drops onto each gauge block as it is named | Hover takes it apart into 11 assemblies; on ignition the WebGL plume fires in the same isometric camera |

## Four choices at the start

In the default mode the skill asks four things at once, each with a default; the Douyin mode skips this step.

| Choice | Default | Alternatives |
|---|---|---|
| Picture | code picture | footage underneath, or one style from the library |
| Format | vertical 1080×1920, 30 fps, cover as frame 0 | horizontal 1920×1080, 24 fps, cinematic pacing |
| Voice | Gemini TTS at 1.25x | edge-tts, Kokoro (offline), none |
| Workflow | three plans with previews, build after approval | ask once, write a TREATMENT.md and build |

## More prompts

```text
Make an intro video for this web game from real gameplay; the link is https://...
Here is the source video and my script; use the source and b-roll, not just illustrations
Make a vertical video on CDN cache hits and misses, explained by a working machine
A 45-second watercolor film about tea, from picking to brewing
Find 10 Douyin topics rising under #Vibe知识大赏 and make one from the best
```

## Install and requirements

```bash
npx skills add anneheartrecord/charles-video-maker
# or copy it manually
git clone https://github.com/anneheartrecord/charles-video-maker.git
cp -r charles-video-maker/skills/charles-video-maker ~/.claude/skills/
```

| Dependency | Required / optional | Notes |
|---|---|---|
| Python 3.9+ | required | `pip install numpy scipy playwright`, then `playwright install chromium` |
| FFmpeg | required | compositing and audio |
| Node.js 20.10+ | required | Anatomy builds and checks, built-in modules only |
| Voice | one required | `GEMINI_API_KEY` (Gemini TTS), or the free `edge-tts` |
| Whisper | required | `mlx-whisper` on Apple Silicon, `faster-whisper` elsewhere |
| Footage layer | optional | `yt-dlp`, `PEXELS_API_KEY` or `PIXABAY_API_KEY` |
| Douyin mode | optional | a Playwright browser profile logged in to the Douyin creator center (QR login on first run), Antigravity CLI `agy` |
| Style library | optional | `sh skills/charles-video-maker/scripts/lemo/setup.sh deps`, about 350 MB, samples about 1.3 GB more |

Keys are read from environment variables only and never written to any file.

## Layout

```
skills/charles-video-maker/
  SKILL.md        routing (video / figure / machine explainer / Douyin) + four choices + the video workflow
  references/     plans, brief, craft rules, cover and opening, voiceover, fact-check, machines, footage, styles, Douyin mode
  scripts/        rendering, fact-check, QA sheet, audio tools, Douyin radar / publish / stats / comments, Gemini script, still check
  scripts/voice/  voice, alignment, timeline and subtitles, mix, sampled scores
  scripts/footage/recording, source quotes, b-roll, generated stills, compositing
  templates/      vertical explainer template
  bridge/         virtual clock, video overlay, page wrapper
  anatomy/        Anatomy, vendored unmodified
examples/         images for this README
```

## Credits and license

- The video workflow, references and render scripts started from [xilo-opus-video](https://github.com/Kianzzz/xilo-opus-video) by [Kianzzz](https://github.com/Kianzzz).
- `anatomy/` is [Anatomy](https://github.com/wheresryan22/anatomy) by [Ryan (@wheresryan22)](https://github.com/wheresryan22), vendored unmodified.
- The Douyin mode's account-building and remake playbook is adapted from chapters 5 and 6 of WEILANX's Opus 5.5 Douyin account-building tutorial.
- The style library, sampled-instrument scoring, Kokoro voice and reading-time check come from [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) by LemoLab, downloaded on demand and not copied into this repository.
- Sources, versions and changes are listed in [NOTICE.md](NOTICE.md); plans are in [ROADMAP.md](ROADMAP.md).

MIT, with all original copyright notices kept. See [LICENSE](LICENSE).
