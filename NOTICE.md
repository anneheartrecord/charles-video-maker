# Notice / 来源说明

This repository started from two MIT-licensed projects joined by a bridge, then added a footage layer and an optional style library.
本仓库起步于两个 MIT 协议开源项目的合并和一层桥接，之后加了素材层和可选的风格库。它是独立的新仓库，不是任何上游的 fork。

| Path / 路径 | Source / 来源 | Version / 版本 | Changes / 改动 |
|---|---|---|---|
| `skills/charles-video-maker/anatomy/` | [wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) by Ryan, MIT | commit `e948829` | none, vendored as-is (`git archive`); its own LICENSE is kept in the folder / 原样收录，未修改 |
| `skills/charles-video-maker/` (except `anatomy/` and `bridge/`) | [Kianzzz/xilo-opus-video](https://github.com/Kianzzz/xilo-opus-video) by 周行, MIT, through the fork [anneheartrecord/xilo-opus-video](https://github.com/anneheartrecord/xilo-opus-video) | fork commit `1676d97` | the fork's additions (voiceover pipeline, templates, fact-check, parallel render, naming); here the skill is named `charles-video-maker` and its SKILL.md gains the routing section / 加了分流说明 |
| `skills/charles-video-maker/bridge/`, `examples/` | new in this repository / 本仓库新增 | | virtual clock, video overlay, page wrapper, example |
| `scripts/footage/`, `references/footage-layer.md`, transparent `.mov` output in `render.py` / `render_parallel.py` | new in this repository / 本仓库新增 | | screen recording, source quotes, stock b-roll, generated stills, compositing and material report |
| `references/lemo-styles.md`, `scripts/lemo/setup.sh`, `scripts/voice/score.py`, the Kokoro backend in `tts.py`, `window.TEXTS` in the template | built on [lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) by LemoLab, MIT (code and docs) | main `508848a` | the library is not copied: it is downloaded on demand into `~/lemo-opuscar` and called from there; the integration doc adapts its directing rules / 不收录库本身，按需下载后调用；接入文档改写了它的导演规则 |

Lemo-Opuscar's demo films and stills are CC BY 4.0 and are never copied into this repository or into users' films.
Lemo-Opuscar 的示范片和静帧是 CC BY 4.0，不收进本仓库，也不剪进用户的成片。

To update Anatomy, replace `skills/charles-video-maker/anatomy/` with a newer `git archive` of the upstream repository and update the commit above.
更新 Anatomy：用上游新版本的 `git archive` 替换 `skills/charles-video-maker/anatomy/`，并更新上表的 commit。
