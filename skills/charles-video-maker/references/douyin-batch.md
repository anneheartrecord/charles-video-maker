# 抖音知识号：多条并行做

用户一次要好几条（选题表里挑 N 个、一个系列 10 集、一批 remake）时走这里。做法是**一条一个子 agent，主 agent 只管分活、验收和排发布**。2026-10-24 到 10-28 实际跑过三批：bug 系列 10 集、10 集 remake、几岁系列 5 条。下面的规矩都来自这三批踩过的坑。

## 分工

| 谁 | 做什么 | 不做什么 |
|---|---|---|
| 主 agent | 定选题表和 slug；每条写一份子任务单；同时派出；收齐后逐条验收；统一排定时发布；在手册「发布记录」追加 | 不替子 agent 写文案或改画面；子 agent 没交差就不排它的定时 |
| 子 agent | 只做分给它的那一条：查一手资料 → Gemini 写文案 → 配音、对齐、念稿核对 → 画面 → 混音 → 渲染 → `out/report.md`，做到可以直接发布 | 不发布、不碰抖音、不改 skill、手册和记忆、不 git commit、不碰别的工程目录 |

派活用 Agent 工具，在**同一条消息里**并发派出；用户开了 workflow 时也可以用 workflow 编排，按会话的规模上限分批。

## 子任务单模板

每条一份，把尖括号换掉。照抄这个结构，别写成一句「照着上一期做」：子 agent 只知道任务单里写了的东西。

```markdown
# 子任务：做一条抖音知识视频「<暂定标题>」（slug：<slug>，有配音、横屏）

只做这一条，做到 out/ 下可以直接发布。不发布、不碰抖音、不改 skill / 手册 / 记忆、不 git commit、不碰别的目录。

## 先读
- skill：SKILL.md、references/douyin-remake.md、gemini-copy.md、voiceover-pipeline.md、douyin-opening.md（开头 5 秒四拍）
- 起步模板：<styles/<风格名>/template.html 或 templates/horizontal-explainer/>；参考工程：<一条已发布、做得好的工程目录>
- 选题依据：<选题表里这一条：一手资料线索、三问各过没过、能画的东西>

## 流程（S=<skill 目录>，命令在 <工程目录> 里跑）
1. 查一手资料，核不到的数字不用；能算的写进 source/calc.py。
2. 写 copy/brief.json → gemini_copy.py gen → check，最多两轮反馈，不许亲手改 Gemini 的字。
3. tts.py → align.py → say_check.py（有 NUM 就改稿重合成）→ scenes.json → timeline.py。
4. 写 index.html；qa_stills.py 自检至少两轮，单独看 0～6 秒逐帧。
5. mix.py --score audio/score.wav --open-boost 10 --open-lift 5，最后一行两个数都要过。
6. 渲成片、3:4 封面、4:3 横封面、字幕 srt；audio_tools.py check 真峰值 ≤ -1 dBTP；still_check.py；analyze_video.py 看联系表。
7. 写 out/report.md：事实与来源、替用户做的决定、已知不足、提醒戴耳机重点听哪几秒。

## 规矩
- 写 index.html 分段写，每段不超过约 150 行，一次输出太长容易断线。
- 删文件用 /bin/rm -f（shell 里的 rm 可能被设成交互确认，会卡住）。
- out/ 顶层只留一条 mp4，样片挪进 out/样片/。
- 卡住（Gemini 两轮不过、TTS 一直 429）就写进 report.md 并说明卡在哪，不要无限重试。

## 交差（≤ 15 行）
成片、封面、publish.txt 的绝对路径；publish.txt 全文；时长；Gemini 用了几轮；配音用的哪个声音；事实来源；已知不足。
```

## 资源会互相抢

并行时下面几样是共享的，慢和报错大多出在这里：

- **Gemini TTS 额度**：免费档一天大约 10 次整段合成，多条并行很快用完，返回 429。`tts.py` 会自动切到 edge-tts 合成，加 `--no-fallback` 则直接失败（见 voiceover-pipeline.md）。**同一集只用一个声音**；用了后备声音的那集要在 report 里注明。额度按美国太平洋时间零点重置，对应北京时间 15:00 或 16:00，大批量最好跨过这个点分两批派。

- **Gemini 写文案**：`gemini_copy.py gen` 偶尔很慢，单次超过 8 分钟没结束就杀掉重跑一次。

- **whisper 对齐**：几条同时跑会抢 GPU，慢是正常的，不用重启。

- **出图**：`agy_image.py` 自带全机 5 路并发锁，排队是正常的；AI 剧照路线的批次不要一次派超过 5 条出图。

- **渲染**：`render_parallel.py` 每条会开多个浏览器进程，五条同时渲会把 CPU 打满。渲染慢了就让后面几条排队，不影响结果。

- **抖音登录态**：`douyin_publish.py`、`douyin_stats.py`、`douyin_comments.py` 共用一个专用浏览器配置，同一时间只能跑一个，所以发布只由主 agent 串行做，子 agent 不碰。

## 主 agent 验收和排发布

1. **等交差，再等文件不动**：子 agent 回复交差之后，再确认 `out/*.mp4` 的修改时间不再变化。2026-10-26 有一集的 agent 还在重配音，旧配音版就先排了出去，只好删掉重排。

2. **逐条验收**：读 report.md，看联系表和封面，核对 out/ 下面这几样齐不齐：一条 mp4、`*-封面.png`、`横封面-4x3.png`、`*-字幕.srt`、`publish.txt`。缺什么就退回给那个子 agent（用 SendMessage 接着它的上下文），不要自己补。

3. **同一条视频只上传一次**：抖音会记住上传过的视频指纹，删掉也还在。所以 remake 必须在第一次上传之前做完；已经传过的，要重发就当成新视频，剧照、标题、简介、封面全换。2026-10-27 bug 系列 01、02 原版和 remake 各传了一次，发出后只有 34 和 23 次播放。

4. **串行排定时**：按用户定的档位，用 `douyin_publish.py <slug> "YYYY-MM-DD HH:MM"` 一条一条排，每条看它的核对截图；一条失败就停下来查，不要接着排下一条。

5. **回写**：每条在手册「七、发布记录」追加一行；批次里踩到的新坑写进这篇或对应的 reference。

## remake 一批

要改一批已经做好、**还没上传**的片子时，同样一条一个子 agent，任务单里多写这几条：

- 先 `cp -R <slug> <slug>-remake`，之后只在 `-remake` 里干活，原目录一个字节都不动；改之前把 brief、copy、narration、scenes、timeline、voice 备份成 `*.orig.*`。

- 任务单里写清这次只改什么、哪些不动，比如标题、封面、publish.txt 沿用原版。画面只改和新旁白对不上的地方，剧照和整体画面不重做。

- 旁白变了，`scenes.json` 的锚点要换成新旁白里的原文片段；原报告里写过的手动卡点要重新核对，比如砸数字那一拍要落在数字被念到的时刻。

- 交差时多交一份逐句新旧对照，只列改过的句子。
