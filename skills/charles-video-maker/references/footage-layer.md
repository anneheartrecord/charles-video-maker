# 素材层：真实画面打底，代码退到信息层

整条视频都是代码画的插图，看久了会累。素材层把画面换成真实的东西：产品或游戏的实录、原视频里的原话、免版税空镜、补位的生成图。代码画面变成透明的一层，只放标题、关键词、数字、字幕，叠在素材上面。

开工四选里「画面」选了「素材打底」就走这一篇。三层结构：

```
素材层  footage.json 的 bed：一段段素材按场景或动作点切换，统一调色，交叉淡化
代码层  index.html?alpha=1 渲成透明的 overlay.mov，背景留空，只画信息
插入    原片引用：在某个场景前插一小段原片，保留原声，加字幕和来源角标
```

## 目标比例

| 素材 | 占比 | 来源 |
|---|---|---|
| 原片引用 | 30–50%（有原片时） | 用户给的、有出处的视频 |
| 实录 / 空镜 | 30–40% | 产品或游戏实录、Pexels / Pixabay |
| 纯信息画面 | 不超过 20% | 代码层自己画背景的场景（讲数字、讲结构时） |

讲产品、游戏、网站的片子，实录可以占到八九成。`compose.py --check` 会打出实际比例，纯信息画面超过 20%、连续三段都是纯信息、相邻两段用了同一素材的同一部分、素材没登记来源，都会报警告。

## 四种素材

### 实录（自己的产品、游戏、网站）

```bash
python3 scripts/footage/record.py <网址> source/footage/demo.mp4 --actions source/actions.json --size 1600x900 --scale 1.2
```

`actions.json` 是一串动作：等待、点击文字、点击坐标、鼠标滑过、滚动、按键，以及 `{"mark": "名字"}`。mark 会记下当时是第几秒，写进 `demo.marks.json`，直接拿来当 `footage.json` 的入点。画面来自 Chrome 的 screencast，按实际时间重采样成恒定帧率，所以清晰、时长准确。要登录的网站，先问过用户再录。

### 原片引用

```bash
python3 scripts/footage/source.py fetch <链接> --name talk          # 先征得用户同意再下载
python3 scripts/footage/source.py transcribe source/footage/talk.mp4
python3 scripts/footage/source.py find source/footage/talk.mp4 "原话里的一句"
```

`find` 按字符对齐，识别有错字、稿子里换了说法也能定位，输出 `in / out / match`，match 低于 0.6 就回去看转写稿。引用规矩：

- 只截短片段（单段一般不超过 10 秒），前后要有自己的解读，不整段搬运。
- 画面角标写出处（`credit`），简介里也写。
- 以各平台的规则为准，用户说不用就不用。

### 空镜（Pexels / Pixabay）

```bash
python3 scripts/footage/stock.py search "porcelain kiln fire" --n 8     # 候选 + 编号拼图 source/stock/<词>.png
python3 scripts/footage/stock.py get pexels:1234567
```

两家都允许商用、不强制署名，我们仍然在 `source/credits.md` 记下作者和链接。需要免费的 key：`PEXELS_API_KEY`、`PIXABAY_API_KEY`（放进环境变量，不写进任何文件）。用英文关键词搜，结果更多。看编号拼图挑，挑的时候注意和全片的光线、色调接近。

### 生成补位

```bash
python3 scripts/footage/genimage.py "a quiet porcelain kiln at dawn, warm light" source/footage/kiln.png --aspect 9:16
```

只在实录、原片、空镜都找不到的时候用（抽象概念、古代场景）。脚本会自动加上不出现文字、不出现可辨认的真人、不出现品牌标志这几条要求。生成的是静帧，`compose.py` 会给它加推拉摇移。Gemini 的生图额度用完会返回 429，这时开通计费或者换成空镜。

## footage.json

```json
{"size": "1080x1920", "fps": 30, "grade": "warm", "band_y": 1000,
 "bed": [
  {"at": "cover", "src": "source/footage/demo.mp4", "in": 0, "kind": "screen"},
  {"at": "map.dg", "src": "source/footage/demo.mp4", "in": 6.2, "speed": 1.3, "kind": "screen"},
  {"at": "why", "src": "source/footage/pexels-1234567.mp4", "in": 2, "kind": "stock"},
  {"at": 21.5, "src": "source/footage/kiln.png", "move": "push", "kind": "gen"},
  {"at": "numbers", "src": null}
 ],
 "inserts": [{"before": "point2", "src": "source/footage/talk.mp4", "in": 63.8, "out": 67.1,
              "caption": "芒格一辈子都在推崇一个古老的品格：可靠", "credit": "来源：某某访谈", "kind": "quote"}]}
```

- `at`：场景名（场景开始）、`场景.动作点`（念到那个词）或秒数。第一条必须在 0，一段素材持续到下一条开始。切在动作点上，画面就和旁白卡上了。
- `fit`：`fill` 裁满画面（竖版素材默认）；`band` 把横版素材放成一条横带，背景是它自己的模糊放大版（横版素材默认）。`band_y` 是横带中心的纵坐标，代码层的标题放在横带上方，标签和字幕放在下方。
- `crop`：先裁出素材的一部分再放大，比如只要界面的左上角。
- `move`：`push`、`pull`、`left`、`right`、`none`。静帧默认 `push`。
- `speed`：倍速，用来让实录里的动作对上旁白的节奏。
- `src: null`：这一段没有素材，由代码层自己画背景（算纯信息画面）。
- `grade`：全片统一调色，可选 `none`、`warm`、`cool`、`film`。混用不同来源的空镜时一定要开，否则一段冷一段暖会很跳。游戏、产品界面用 `none`，保持原色。
- `inserts`：插在某个场景开始之前，用原片自己的声音（响度统一到 -14 LUFS），`caption` 是烧在下方的字幕（原片自带字幕时留空），`credit` 是左上角的来源角标。插入会让全片变长，旁白和画面的同步不受影响。

## 代码层怎么改

页面加一个透明模式：URL 带 `?alpha=1` 时不画背景、不画原本代表素材的截图框，只画标题、标签、数字、字幕；需要自己背景的场景（纯信息画面）照常画背景。写法参考：

```js
const FOOT = location.search.includes('alpha'), OWN_BG = new Set(['numbers']);
if (FOOT) document.documentElement.style.background = document.body.style.background = 'transparent';
// render(t) 里：FOOT 时 g.clearRect(0, 0, W, H)，否则画背景；画 OWN_BG 里的场景之前先画它自己的背景
```

布局按横带来：标题在横带上方，标签、角标、字幕在横带下方，不压住素材的主体。要把元素放到素材里的某个位置（比如往界面的槽位里放东西），按横带的缩放算坐标：横带宽 1080，缩放比例 = 1080 ÷ 素材宽度，纵向从 `band_y - 横带高 / 2` 开始。

## 命令顺序

```bash
# 1. 配音流水线照常：narration → tts → align → scenes.json → timeline → mix（见 voiceover-pipeline.md）
# 2. 备素材：record.py / source.py / stock.py / genimage.py，全部登记在 source/credits.md
# 3. 写 footage.json，先看比例和警告
python3 scripts/footage/compose.py footage.json --check
# 4. 代码层渲成透明 .mov（帧数会自动核对）
python3 scripts/render_parallel.py "index.html?alpha=1" audio/overlay.mov --size 1080x1920 --fps 30 --duration <total>
# 5. 合成
python3 scripts/footage/compose.py footage.json "out/$NAME.mp4" --overlay audio/overlay.mov --audio audio/mix.wav
# 6. 抽帧自检：analyze_video.py out/$NAME.mp4 --out qa/final
```

封面图从成片第 0 帧导出：`ffmpeg -i out/$NAME.mp4 -frames:v 1 out/$NAME-封面.png`。

## 自检多看几样

- 第 0 帧：素材和代码层叠在一起之后，还是一张完整的封面。
- 每次切素材都落在场景开始或动作点上，没有在一句话中间乱切。
- 文字压在亮色素材上看不清时，给文字加底或描边，不要靠运气。
- 原片插入的前后，旁白有没有接住（插入前一句引出它，插入后一句评论它）。
- `source/credits.md` 每一行都对得上，简介里写好出处。
