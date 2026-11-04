<div align="center">

![charles-video-maker](examples/banner.jpg)

# charles-video-maker

**文字稿进去，带配音、字幕、封面和发布文案的成片出来。画面是代码一帧一帧画出来的。**

[English](README_EN.md) | 中文

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/Node-20.10%2B-339933.svg)](https://nodejs.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-required-007808.svg)](https://ffmpeg.org/)
[![Agent Skill](https://img.shields.io/badge/Agent-Skill-d97757.svg)](skills/charles-video-maker/SKILL.md)

</div>

## 零粉丝新号，13 天，37 万播放

2026 年 10 月 20 日，用这个 skill 的抖音模式开了一个新号。没有投过抖加，人只负责挑选题和最后过审，其余从文案到发布都由流水线完成。

| 总播放 | 单条最高 | 单条最多分享 | 投流 |
|:---:|:---:|:---:|:---:|
| **37 万+** | **23.1 万** | **7,053 次** | **0 元** |

### 代表作

| [![幸福感最低的一年](examples/douyin-happiness-u.jpg)](https://www.douyin.com/video/7700211164583873834) | [![没赢够 6 次](examples/douyin-winner-effect.jpg)](https://www.douyin.com/video/7699389178563300651) | [![富兰克林效应](examples/douyin-franklin-effect.jpg)](https://www.douyin.com/video/7700210236262567168) |
|:---:|:---:|:---:|
| **你人生中幸福感最低的一年，会是几岁？** | **总觉得自己不如别人？你可能只是没赢够 6 次** | **想让一个人喜欢你，富兰克林效应有多神？** |
| 78 秒 · 23.1 万播放 | 66 秒 · 9.9 万播放 | 71 秒 · 1.3 万播放 |
| 7,053 次分享 · 2,537 条评论 | 1,441 次收藏 · 带来 102 个关注 | 373 赞 · 178 次收藏 |
| [▶ 在抖音观看](https://www.douyin.com/video/7700211164583873834) | [▶ 在抖音观看](https://www.douyin.com/video/7699389178563300651) | [▶ 在抖音观看](https://www.douyin.com/video/7700210236262567168) |

数据截至 2026-11-02。同一套流水线也做出过几十播放的片子：流量主要由选题和开头 3 秒决定，工具负责把成品质量稳定在同一个水平。

## 30 秒上手

```bash
npx skills add anneheartrecord/charles-video-maker
```

然后直接告诉 agent 你想做什么：

```text
把这篇文章做成一条 60 秒的竖版视频，要配音和字幕
```

## 它能做什么

| 能力 | 一句话 | 适合 |
|---|---|---|
| **代码动画** | 模型写一个按时间 t 画画面的网页，逐帧截图合成视频 | 知识讲解、数据可视化、产品介绍 |
| **素材打底** | 实录、原视频片段、免版税空镜、生成图垫在下面，代码画面退成透明信息层 | 产品演示、游戏介绍、评论视频 |
| **机器讲概念** | 把技术概念造成一台会动的等距机器，旁白念到哪一步，机器做哪一步 | 硬核技术科普 |
| **抖音知识号模式** | 从一条正在爆的原片出发，选题、风格、文案、配乐、渲染、发布、拉数据一路做完 | 起号、批量做泛知识短视频 |
| **风格库**（可选） | 接入 [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) 的 53 种画风和真乐器配乐 | 需要特定画风的短片 |

每条视频都带一整套质量闸门：数字必须在事实核查表里，逐场景拼图自检，阅读时长、帧数、响度和真峰值都要过检查。

## 一条视频怎么做出来

```
文字稿 ──► 事实核查表 ──► 配音（整段合成、加速）──► 逐字时间戳 ──► 场景切点、动作点、字幕
                                                                        │
          ┌─────────────────────────────────────────────────────────────┘
          ▼
   代码画面 render(t) ──► 逐帧截图（并行）──┐
   素材层 footage.json ──► 剪切、调色、淡化 ─┼──► 合成 ──► out/<主题名>.mp4 + 封面图 + publish.txt
   配乐 + 音效 + 旁白 ──► -14 LUFS ────────┘
```

- **配音流水线**：旁白整段合成，用 Whisper 逐字时间戳把稿子原文对回去。场景切换、画面动作、音效和字幕都按念到的词定位，识别错字不会进字幕。
- **素材层**：`record.py` 录网页，`source.py` 下载并转写原视频、找到一句话的起止秒数，`stock.py` 搜免版税空镜，`compose.py` 把素材、透明代码层和配音合成在一起。
- **交付**：成片和封面按标题命名，`publish.txt` 只有标题、简介、5 个 tag 三段，直接复制到发布页。

## 抖音知识号模式

上面三条代表作都出自这个模式。它不从想法出发，从一条正在爆的原片出发：风格一比一，内容不搬，在画面冲击力、质感和卡点上做得比原片更好。授权一次就做到交付，只有查不到一手资料或同一个工具连续失败两次时才停下来问。

```
D-1 题材雷达 ──► D1 蒸馏风格 ──► D2 资料与文案 ──► D3 先测配乐再排画面 ──► D4 制作与自查 ──► D5 交付
 douyin_radar     风格库          gemini_copy        voiceover-pipeline       still_check          封面、publish.txt
                                                                                                     │
                     数据结论写回运营手册 ◄── douyin_stats / douyin_comments ◄── douyin_publish ◄───┘
```

| 环节 | 做什么 |
|---|---|
| **题材雷达** | `douyin_radar.py` 抓话题下正在涨的视频并排名，产出 10 到 20 个选题 |
| **开头 3 秒** | `douyin-opening.md` 拆了一批头部爆款的开头，画面、第一句、声音各有检查表 |
| **文案** | `gemini_copy.py` 交给本地 Gemini 写旁白和标题，skill 只校验事实和结构 |
| **静止检查** | `still_check.py` 找出画面停住超过 2 秒的段落，以及字幕换了画面没跟上的地方 |
| **发布与数据** | `douyin_publish.py` 定时发布，`douyin_stats.py` 拉 2 秒跳出、5 秒完播、点赞、收藏、分享，`douyin_comments.py` 存评论 |
| **念稿核对** | `say_check.py` 对比稿子和转写，找出 TTS 吞掉或念岔的数字和字 |
| **开头混音** | `mix.py --open-boost --open-lift` 让开头 3 秒比正文响约 3 dB，配乐给第一句让路 |
| **风格库与模板** | `styles/` 五套蒸馏过的画风，`templates/horizontal-explainer/` 横版骨架，`templates/douyin-cover/` 3:4 和 4:3 封面 |
| **多条并行** | `douyin-batch.md` 一条一个子 agent，主 agent 分活、验收、串行排发布 |
| **系列化** | `douyin-series.md` 记录系列做法和单条发的现行规矩 |

你需要自己准备两样东西：一个工作目录，放原片库、风格库和工程，用环境变量 `DOUYIN_WORKDIR` 指定，默认 `~/Desktop/video/vibe-video/`；一份自己维护的运营手册，记选题规律和数据结论，路径写进 `DOUYIN_HANDBOOK`。没有手册也能出片，只是跳过读手册和数据写回这两步。抖音登录态放在 `DOUYIN_PROFILE`、`DOUYIN_COOKIES` 指的位置，默认在 `~/.config/douyin/` 下，只存在本机。

## 更多效果

| **百分表**（Anatomy 最小的例子） | **猛禽发动机**（带 WebGL 尾焰） |
|:---:|:---:|
| ![百分表视频](examples/dial-indicator-video.png) | ![猛禽发动机视频](examples/raptor-engine-video.png) |
| 念到往右一滑，托架滑过去；念到每个量块，测头就落到那一块上 | 悬停拆成 11 个组件，点火时 WebGL 尾焰在同一个等距视角里喷出来 |

## 开工四选

普通模式开工时，skill 一次问你四件事，每项都有默认值；抖音模式跳过这一步。

| 选项 | 默认 | 可选 |
|---|---|---|
| 画面 | 代码画面 | 素材打底，或者风格库里的一种画风 |
| 规格 | 竖版 1080×1920，30fps，第一帧就是封面 | 横版 1920×1080，24fps，电影节奏 |
| 配音 | Gemini TTS，1.25 倍速 | edge-tts、Kokoro（离线）、不配音 |
| 流程 | 三个方案加预览，确认后再做 | 只问一次，写一份 TREATMENT.md 直接做 |

## 更多用法

```text
给这个网页游戏做一条介绍视频，用实机画面，链接是 https://...
这是原视频链接和我的文字稿，画面多用原片和空镜，别全是插图
做一条讲 CDN 缓存命中和未命中的竖版视频，用一台会动的机器讲清楚
用水彩风格做一条 45 秒的短片，讲茶叶从采摘到冲泡
找 10 个 Vibe 知识大赏下正在涨的抖音选题，挑最好的一条做一期
```

## 安装与环境

```bash
npx skills add anneheartrecord/charles-video-maker
# 或者手动复制
git clone https://github.com/anneheartrecord/charles-video-maker.git
cp -r charles-video-maker/skills/charles-video-maker ~/.claude/skills/
```

| 依赖 | 必需 / 可选 | 说明 |
|---|---|---|
| Python 3.9+ | 必需 | `pip install numpy scipy playwright`，再 `playwright install chromium` |
| FFmpeg | 必需 | 合成与音频处理 |
| Node.js 20.10+ | 必需 | Anatomy 的构建和检查，只用内置模块 |
| 配音 | 必需其一 | `GEMINI_API_KEY`（Gemini TTS），或免费的 `edge-tts` |
| Whisper | 必需 | Apple Silicon 用 `mlx-whisper`，其他机器用 `faster-whisper` |
| 素材层 | 可选 | `yt-dlp`，`PEXELS_API_KEY` 或 `PIXABAY_API_KEY` |
| 抖音模式 | 可选 | 登录过抖音创作者中心的 Playwright 浏览器配置（首次运行扫码），Antigravity CLI `agy` |
| 风格库 | 可选 | `sh skills/charles-video-maker/scripts/lemo/setup.sh deps`，约 350MB，采样库另约 1.3GB |

所有 key 只从环境变量读取，不写进任何文件。

## 目录

```
skills/charles-video-maker/
  SKILL.md        分流（视频 / 插图 / 机器讲概念 / 抖音）+ 开工四选 + 视频流程
  references/     方案、brief、制作规则、封面与开头、配音、事实核查、机器讲概念、素材层、风格库、抖音模式
  scripts/        渲染、事实核查、自检拼图、音频工具、抖音雷达 / 发布 / 数据 / 评论、Gemini 文案、静止检查
  scripts/voice/  配音、对齐、念稿核对、时间轴与字幕、混音、真乐器配乐
  scripts/footage/实录、原片、空镜、生成补位、合成
  templates/      竖版、横版讲解模板，抖音封面模板
  styles/         抖音知识号风格库（五套）
  bridge/         虚拟时钟、视频叠加层、页面包装脚本
  anatomy/        Anatomy 原样收录
examples/         README 用的效果图
```

## 致谢与协议

- 视频流程、参考文档和渲染脚本起步于 [周行（Kianzzz）](https://github.com/Kianzzz) 的 [xilo-opus-video](https://github.com/Kianzzz/xilo-opus-video)。
- `anatomy/` 原样收录自 [Ryan（@wheresryan22）](https://github.com/wheresryan22) 的 [Anatomy](https://github.com/wheresryan22/anatomy)，未做修改。
- 抖音模式的起号与复刻打法改写自蔚蓝 WEILANX 的《Opus 5.5 抖音起号超级保姆级万字教程》第五、六章。
- 风格库、真乐器采样器、Kokoro 配音和阅读时长检查来自 LemoLab 的 [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar)，按需下载使用，不收进本仓库。
- 各部分的来源、版本和改动见 [NOTICE.md](NOTICE.md)，后续计划见 [ROADMAP.md](ROADMAP.md)。

MIT，保留所有原作者的版权声明，见 [LICENSE](LICENSE)。
