# 风格库：抖音知识号蒸馏过的五套画风

抖音模式 D1 蒸馏出的风格放在这里，每期开工从其中一套的 `template.html` 起步，不从空白页写。每套有三样东西：

- `style.md`：风格配方卡，写清配色、字体、版式、招牌画面、动效，以及没有搬原片的哪些东西。

- `template.html`：把每个组件都演一遍的 `render(t)` 页面，直接用 `scripts/render.py` 能渲；要读 `timeline.js` 的两套附了首期工程的时间轴当样例，跑完配音流程后会被新的覆盖。

- `preview.jpg`：预览图。

| 风格 | 画幅 | 适合的选题 | 配音 | 一句话特征 |
|---|---|---|---|---|
| 暗金粒子 | 横屏 | 科普、原理、年龄曲线类 | 有 | 黑底金色发光粒子剪影，白色细线框搭空间，一个粒子集合在场景间变形、全片不切镜头 |
| 深色小人数据风 | 横屏 | 研究数据、实验对比 | 有 | 深灰聚光舞台，红白 3D 小人对比，双色折线、印章砸字；幸福感那条和赢家效应都是这一系 |
| 灰底金属风 | 横屏 | 物理现象隐喻人生 | 无 | 浅灰底、宋体大标题、金属线条和晶粒剖面 |
| 霓虹血条风 | 横屏 | 心理、关系、伤害和回复 | 无 | 黑底霓虹爱心、像素血条、游戏 HUD 道具卡 |
| 暗蓝点阵竖屏风 | **竖屏** | 统计、筛选 | 有 | 海军蓝网格，金色点阵和大数字，逐项筛到 0 |

## 怎么挑

- **默认先看暗金粒子和深色小人数据风**：两套都是纯代码，不受出图额度影响，横屏配音，账号上用得最多。暗金粒子画面质感更高，但它的开头靠粒子聚形，单张图的代入感不如人物剧照；人物、场景类钩子仍按 `references/douyin-opening.md` 走 AI 剧照加代码运动。

- **新原片和库里五套都不像**：走 D1 蒸馏一套新的，按同样三件套放进这里。

- **没有原片、只有选题**：直接用 `templates/horizontal-explainer/`，它是深色小人数据风的通用骨架，带标题条、字幕、高潮收暗砸字和 3:4、4:3 两种封面。

## 暗金粒子的 three.iife.js

`template.html` 走 `file://` 打开，不能加载 ES 模块，所以 Three.js 要打成一个 IIFE 文件挂到 `window.THREE`。本目录的 `three.iife.js` 是 three@0.160.0（MIT 许可）用下面的方法打出来的，要换版本就重打：

```bash
mkdir three-build && cd three-build && npm init -y >/dev/null && npm i three@0.160.0 esbuild@0.19.12
echo "import * as THREE from 'three'; window.THREE = THREE;" > entry.js
npx esbuild entry.js --bundle --minify --format=iife --outfile=three.iife.js
```

每期工程把它和 `template.html` 一起拷进工程目录。
