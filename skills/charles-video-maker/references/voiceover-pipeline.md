# 有配音的片子：流水线

有旁白的视频（知识讲解、口播稿转视频）按这条线做。核心思路：**旁白整段合成，用逐字时间戳让画面去对旁白**，场景切换、画面动作、字幕全部用稿子里的原话定位。

模板有两套，把整个目录拷到项目目录再改：

- `templates/vertical-explainer/`：竖版 1080×1920，第 0 帧是封面、场景淡入淡出、底部一行硬字幕。

- `templates/horizontal-explainer/`：横版 1920×1080，抖音知识号的版式，标题条从第 0 帧挂到片尾、高潮收暗定格砸字、`?cover=1` 出 3:4 封面、`?cover=43` 出 4:3 横封面。用法见目录里的 `index.html` 注释。

## 命令顺序

下面 `$S` 是本 skill 的目录，命令都在项目目录里跑。

```bash
# 1. 旁白：由 Gemini 写（gemini_copy.py gen / check，见 gemini-copy.md），把 copy.json 的 lines 一段一行写进 audio/narration.txt；有事实就先建核对表（见 fact-check.md）
python3 $S/scripts/factcheck.py extract audio/narration.txt source/factcheck.md
# 2. 合成并加速（默认 1.25 倍）；后端按开工四选：默认 Gemini，--backend edge（免费、联网）或 --backend kokoro（离线，见 lemo-styles.md）
python3 $S/scripts/voice/tts.py audio/narration.txt audio/voice.wav
# 3. 逐词时间戳（Apple Silicon 用 mlx-whisper，其他机器换成 faster-whisper）
uv run --with mlx-whisper python $S/scripts/voice/align.py audio/voice.wav audio/voice_segments.json
# 3.5 核对念稿：数字有没有被吞、念岔（见下面「念稿核对」），有 NUM 就改稿重合成，过了再往下
python3 $S/scripts/voice/say_check.py
# 4. 写 audio/scenes.json，生成时间轴和字幕（同时导出 audio/subs.srt，可单独上传成字幕轨）
python3 $S/scripts/voice/timeline.py
# 5. 改 index.html 的 HEAD / BODY，出每个场景最满状态的拼图检查
python3 $S/scripts/qa_stills.py index.html audio/timeline.json qa/scenes.png
# 6. 配乐 + 音效 + 旁白混音（-14 LUFS，峰值留够 AAC 编码的余量）；要真乐器配乐，先跑 score.py 再加 --score audio/score.wav（见 lemo-styles.md）
python3 $S/scripts/voice/mix.py
# 抖音片子开头要做响：python3 $S/scripts/voice/mix.py --score audio/score.wav --open-boost 10 --open-lift 5（见 douyin-remake.md 开头 3 秒那节）
# 7. 先写好 out/publish.txt（标题 / 简介 / 5 个 tag），用标题生成文件名，再过事实闸门、并行渲染、导出封面图
NAME=$(python3 $S/scripts/topic_name.py out/publish.txt)
python3 $S/scripts/factcheck.py gate source/factcheck.md --narration audio/narration.txt --page index.html
python3 $S/scripts/render_parallel.py index.html "out/$NAME.mp4" --size 1080x1920 --fps 30 --duration <timeline.json 的 total> --audio audio/mix.wav
python3 $S/scripts/render.py "index.html?cover=1" "out/$NAME-封面.png" --still <开头印章落下之后的秒数> --size 1080x1920
```

## Gemini 额度用完时：自动切到 edge-tts

Gemini TTS 免费档一天大约 10 次整段合成，按美国太平洋时间零点重置，对应北京时间 15:00 或 16:00。多集并行很容易用完。用完时 Gemini 返回 429，`tts.py` 会自动改用 edge-tts 合成同一段旁白，免费、不要 key，默认声音是 `zh-CN-YunxiNeural`。

- 想换后备声音就设环境变量 `TTS_FALLBACK_VOICE`，填任一 edge-tts 声音名；不想切就加 `--no-fallback`，额度用完直接报错。
- 同一集只用一个声音。用后备声音合成的那集，在 report 里注明；一批片子并行时，大批量最好跨过额度重置时间分两批派。

## 念稿核对：TTS 吞数字、念岔字

整段合成的 TTS 偶尔会吞掉长数字的一截，或者把字念岔。实测过的情况：3628800 只念出三百六十二万八千，测出来被念成测数来，两点被念成二点。
这些错字幕上看不出来，因为字幕用的是稿子原文，只有听才发现，而 AI 听不到声音。所以合成、对齐之后，先跑 `say_check.py` 再往下做：

- **怎么查**：它把稿子和 whisper 转写都换成中文读法，比如 20,186 换成二万零一百八十六，2004 年换成二零零四年，67% 换成百分之六十七，然后逐字对齐，每处不同都列出时间。

- **NUM 行**：数字对不上，脚本退出码为 1。到那一秒听一下；确实被吞或念岔，就在 `narration.txt` 里把这个数字直接写成中文读法，比如 3628800 写成三百六十二万八千八百，再整段重合成、重新对齐。也可以换成同一个意思的另一种念法，比如二点改成两点。字幕和屏上的数字照用阿拉伯数字，不受影响。

- **WORD 行**：只有字不同，大多是 whisper 把同音字听错，比如老幺听成老妖、到顶听成到底、记东西听成寄东西。去那一秒听一下：是识别错就不用管；是 TTS 真念岔了就重合成一次，通常就好了。拿不准就写进交付报告，提醒用户戴耳机重点听。

- 10-28 那批五条重新跑过一遍：数字全部对得上，WORD 行列出的正好是各集报告里提醒用户重点听的那几处。

## scenes.json

```json
{
 "scenes": [
  ["cover", "开头第一句的前几个字", {"stamp": "暴论里的关键词"}],
  ["point1", "第一，", {"a": "旁白里的一个短语", "b": "后面的另一个短语"}]
 ],
 "kind": {"cover.stamp": "stamp", "point1.b": "coin"},
 "offs": {"cover.stamp": 0.3}
}
```

- 每个场景：名字、起点原话、场景内动作点。原话必须是 `narration.txt` 里一字不差的片段，按顺序查找。
- 页面里 `BODY[名字](t, c)` 拿到的 `c` 就是这些动作点的时间（秒），`c._start` 是场景起点。念到哪个词，就在 `c.那个词` 的时刻让对应元素出现。
- `kind` 决定这个动作点配什么音效：`pop`（默认）、`stamp`、`coin`、`print`、`tick`、`pencil`。
- 一个场景的第一个动作点离场景起点超过 3 秒，就先放一个占位元素，不然画面会空着。

## 踩过的坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 开头多出一段「用自然的语气朗读……」 | Gemini TTS 会把风格指令当正文读 | `tts.py` 只传正文，不加任何指令 |
| 场景切换点算错、时长为负 | whisper 会把好几段旁白合成一个分段，分段边界不可靠 | `timeline.py` 用逐字对齐，不用分段边界 |
| 字幕出现错别字（字节 → 自解） | whisper 同音识别错 | 识别结果只拿时间，字幕和定位都用稿子原文 |
| 音频末尾多出空段、重复段 | whisper 在静音处幻觉 | `align.py` 丢掉空文本和短于 0.3 秒的分段 |
| 第一段切片为空 | 起点算成 -0.05 秒 | 起点不小于 0（已处理） |
| 成片峰值超过 -1 dBTP | AAC 编码会把真峰值抬高约 0.8 dB | `mix.py` 标准化后再限幅到 0.8 |
| edge-tts 返回 403 | 版本旧，微软换了鉴权 | `uv tool upgrade edge-tts` |
| 批量删除临时文件时卡住 | shell 里 `rm` 被设成了交互确认 | 脚本里一律用 `/bin/rm -f` |
| 长数字只念出一半、字念岔 | TTS 整段合成的偶发错误，字幕用原稿看不出来 | 对齐后跑 `say_check.py`，NUM 行改成中文读法重合成 |

## 自检时多看三样

- 第 0 帧是不是完整封面（没有字幕、没有半截动画）。
- 每个场景最满的状态有没有文字溢出、元素重叠，`qa_stills.py` 的拼图一眼能看出来。
- 印章、贴纸这类开头动作，从落下到切走至少要留 1 秒，否则观众看不见。
