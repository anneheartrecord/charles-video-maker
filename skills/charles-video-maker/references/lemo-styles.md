# 风格库：接入 Lemo-Opuscar

[Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar)（MIT）是一套用代码拍短片的风格库：53 种画风，每种有一份 `STYLE.md`（画面、配色、字体、运动、镜头语法、声音、这种媒介独有的动作、常见坑）和一条示范片。它的渲染原理和本 skill 一样（页面暴露 `render(t)`，逐帧截图），所以能直接接进来。

本 skill 只把它当**风格层和工具箱**用：画面怎么画按它的 `STYLE.md`，配音、对齐、字幕、封面、事实核查、发布文案仍走本 skill 的流程。它不解决「整片都是代码画面」的问题（它明确不用实拍素材），那是素材层的事，见 footage-layer.md。

## 开工四选

视频流程第 1 步开头，用 AskUserQuestion 一次问完下面四项，每项第一个选项是默认值，标「（推荐）」。用户在请求里已经说清楚的项不问。

| 选项 | 默认 | 可选 | 选了之后改什么 |
|---|---|---|---|
| **画面** | 代码画面（讲解模板 / 自由设计 / Anatomy 机器） | 素材打底：实录、原片引用、空镜、生成补位，代码只做信息层（见 footage-layer.md）；或 Lemo 风格库里的一种：按题材推荐两三种，并附全部风格列表 | 素材打底按 footage-layer.md 备素材和合成；Lemo 风格在方案的「风格」一栏写 `Lemo · <风格名>`，制作按它的 `STYLE.md` |
| **规格** | 竖版短视频：1080×1920，30fps，30–60 秒，第一帧是封面、前 5 秒一句暴论、硬字幕 | 横版短片：1920×1080，24fps，30–60 秒，电影节奏（Lemo 的默认值，3 秒内有钩子，节奏有快有慢、留一次呼吸） | 渲染的 `--size` 和 `--fps`；横版的开场规则见下文「横版短片」 |
| **配音** | Gemini（`gemini-3.8-flash-tts`，音色 Charon，1.25 倍速） | edge-tts（免费，要联网）／Kokoro（离线，英文好，中文偏平）／不配音 | `tts.py --backend gemini｜edge｜kokoro`；不配音就跳过配音流水线 |
| **流程** | 三个方案加预览，用户确认后再做 | 只问一次就开拍（Lemo 式）：写一份 `TREATMENT.md` 就直接做，中途不停 | 选后者就跳过第 2–3 步，见下文「只问一次」 |

配乐不单独问。默认用代码合成的 lo-fi；选了 Lemo 画风，或者题材明显需要别的乐器时，改用真乐器配乐（见下文），并在方案的「声音」一栏写明。

## 准备

```bash
sh scripts/lemo/setup.sh            # 找到或下载风格库（默认 ~/lemo-opuscar，约 30MB），最后一行打印 LIB=<路径>
sh scripts/lemo/setup.sh deps       # 核心工具：readcheck、采样器（约 350MB，首次几分钟，可以放后台）
sh scripts/lemo/setup.sh deps voice # 只有选 Kokoro 时才装
sh $LIB/tools/fetch.sh instruments all     # 五套采样库约 1.3GB；只下 vcsl、vsco2ce 也能用，缺的乐器会自动换成替代乐器
```

缺 Node 20+、ffmpeg、Python 3.11+ 这类系统工具时，告诉用户自己装，不要替他装。

## 用一种风格

1. 在 `$LIB/styles/README.md` 按中文名、英文名或文件夹名查到风格，读 `$LIB/styles/<slug>/STYLE.md`。它写的是这种风格**不能变**的东西，全部保留。故事、结构、镜头、时长都由本 skill 的流程按用户的题材来定，不要往示范片上靠。
2. 方案里写一个**对标作品**：一部为这个题材挑的参考作品（电影、片头、游戏、广告），写清楚学什么（构图、节奏、镜头、配色、配乐结构）、不学什么（角色、设计、旋律、具体镜头、标志、字体）。不要拿示范片当对标。
3. **方案定了以后才看示范片。** `sh $LIB/plugin/skills/lemo-opuscar/scripts/setup.sh demo <slug>` 取到源码，只学技术（笔刷引擎、骨骼、着色器、混音），不学故事。交付前把成片和示范片对比六项：结构、开场、招牌镜头、镜头路径、配乐走向、结尾，至少四项不同。
4. 竖版讲解里比较好用的风格：白板讲解 `whiteboard`、数据叙事 `dataviz`、等距信息图 `iso-infographic`、综艺节奏扁平 `game-show`、瑞士动态排版 `swiss-motion`、档案灯台 `archive-lighttable`、16-bit 像素 RPG `pixel-rpg`。讲东方文化的可以用水墨 `ink-wash`、皮影 `shadow-puppet`、浮世绘 `ukiyoe`。

### 页面怎么写，用哪套工具渲染

- **自包含（默认）**：需要 `$LIB/core/lib.js` 这类小文件就拷进工程，用相对路径引用。本 skill 的 `render.py`、`render_parallel.py`、`qa_stills.py` 都能直接用。
- **依赖库里的大件**（three.js、`core/three/post.js`、`core/post/crt.js`，3D 和着色器类风格常用）：页面用绝对路径 `/core/…`、`/node_modules/…`，改用库自带的工具渲染：

```bash
cd "$LIB" && node core/render/still.mjs "<工程绝对路径>" 1.5 3 --size 1080x1920
cd "$LIB" && node core/render/video.mjs "<工程绝对路径>" --fps 30 --size 1080x1920 --out "<工程>/out/video.mp4"
sh "$LIB/core/render/mux.sh" "<工程>/out/video.mp4" "<工程>/audio/mix.wav" "<工程>/out/<主题名>.mp4" 30 0
```

两种页面都要同时满足两边的契约：`window.render(t)`，加载完设 `window.ready = window.READY = true`，`window.DUR` 是总时长。`render.py` 认这两种写法。

## 配音

`scripts/voice/tts.py` 有三个后端，后面的对齐、时间轴、字幕、混音都一样：

| 后端 | 命令 | 说明 |
|---|---|---|
| Gemini（默认） | `tts.py audio/narration.txt audio/voice.wav` | 需要 `GEMINI_API_KEY`，中文最自然 |
| edge-tts | `… --backend edge [--voice zh-CN-YunxiNeural]` | 免费，要联网 |
| Kokoro | `… --backend kokoro [--voice zm_yunxi]` | 离线，走风格库的 Kokoro；英文很好，中文偏平 |

三个后端默认都加速到 1.25 倍，`--speed 1.0` 保持原速。横版短片可以考虑用 1.0。

## 配乐：真乐器

`scripts/voice/score.py` 用风格库的采样器，按旁白时间轴用真乐器写一段配乐，`mix.py --score` 把它垫在旁白下面（人声出来时自动压低）。

```bash
$LIB/.venv/bin/python scripts/voice/score.py --dir . --palette play    # 写 audio/score.wav 和 audio/score-credits.txt
python3 scripts/voice/mix.py --score audio/score.wav
```

| 预设 | 乐器 | 适合 |
|---|---|---|
| `keys` | 三角钢琴、爵士贝斯、沙锤 | 平静的讲解 |
| `play` | 马林巴、拨弦大提琴、钟琴 | 游戏、产品、轻松的题材 |
| `cine` | 大提琴和中提琴铺底、竖琴、每次切场景一声定音鼓 | 严肃的题材、故事、钱 |
| `east` | 越南筝、二胡、手鼓 | 中国文化、历史 |
| `guitar` | 尼龙弦吉他、爵士贝斯、沙锤 | vlog、个人故事 |

采样库没下全时，三角钢琴换成立式钢琴、爵士贝斯换成拨弦低音提琴、二胡换成长笛、吉他换成竖琴，脚本会自动处理。

`score-credits.txt` 里是采样库的授权说明。CC BY 的必须写进简介或片尾（三角钢琴 Salamander 是 CC BY 3.0），CC0 的写不写都可以。五个预设都压过低频（20–120Hz 比其余频段低 2 dB 以上），在手机上不会发闷。

## 阅读时长检查（readcheck）

风格库的 `readcheck.mjs` 会检查屏幕上每段文字有没有停留够时间（中文每秒 4.5 个字再加 1.5 秒），专门抓「字还没读完就切走」。

```bash
cd "$LIB" && node core/render/readcheck.mjs "<工程绝对路径>" --size 1080x1920 --step 0.1
```

页面需要导出 `window.TEXTS(t)`，返回 t 秒时画面上的每段文字和它的位置。`templates/vertical-explainer/stage.js` 已经自动导出（字幕不算，字幕看 `.srt`），自己写的页面照着它补。结果是 BAD 的条目，要么延长停留，要么删字。片尾最后一两句来不及读完的，可以接受，但要在交付说明里写出来。

## 横版短片

选了横版就按 1920×1080、24fps 做，节奏用风格库 `DIRECTOR.md` 的规则：

- 3 秒内要有钩子，片头不放慢吞吞的 logo。
- 节奏有快有慢，至少一次明显的加速或减速，留一个长镜头让观众喘口气。
- 声音分环境声、动作音效、音乐三层；在转折前留两次静默，至少两次用声音做转场。
- 镜头至少有四种运动，有一个让人记住的招牌镜头。

第一帧是封面这条在横版里不强制，但封面图照样要导出。`audio/subs.srt` 是配音流水线自动导出的字幕文件，横版发布时可以作为单独的字幕轨上传。

## 只问一次

选了「只问一次就开拍」，开工四选加原材料确认只问这一轮，之后不再停。把第 2–3 步换成一份 `TREATMENT.md`，写完直接做：

1. 三种候选结构，每种几句话，然后写选了哪一种、为什么。
2. 一句话 logline，以及开头、转折、结尾。
3. 对标作品：学什么、不学什么。
4. 分镜表：每个镜头的景别、角度、运动、时长和理由。
5. 封面帧和开头前 5 秒（竖版时）。
6. 声音设计：每段的环境声、动作音效、音乐状态。

`brief.md` 照样要写，后面的制作、自检、交付和默认流程完全一样。

## 版权红线

- 成片里不出现 LemoLab 署名、水印。交付前用 `grep -rniE "lemo ?lab" <工程>` 检查，片尾最后几秒要亲眼看一遍。
- 示范片和它的静帧是 CC BY 4.0，不剪进用户的成片；只学技术。
- 参考作品只学语法，不照搬角色、设计、旋律、镜头、标志和字体。
- 用到的第三方素材（采样库、字体、图片）都记进 `CREDITS`，`score-credits.txt` 里的内容一并写入。
