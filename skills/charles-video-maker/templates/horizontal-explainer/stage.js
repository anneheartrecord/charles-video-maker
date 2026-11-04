// Horizontal explainer stage (1920×1080, 30 fps): the Douyin #Vibe知识大赏 layout. A dark stage with soft light, a title
// bar from frame 0 to the end, one-line subtitles, climaxes that dim, freeze 3 frames and slam a word in.
// Distilled from the episodes that did best on the account (birthday, winner-effect, happiness-u).
//
// index.html loads timeline.js (written by voice/timeline.py) and this file, defines EP and calls startEpisode(EP):
//   EP.title     title bar text; [red] and {gold} mark highlighted words
//   EP.scenes    { name: (t, c) => draw }   c = that scene's cue times: c.start, c.end, c.<cue> (from audio/scenes.json)
//   EP.hard      scene names that cut in hard instead of cross-fading (the hook, every climax)
//   EP.climax    cue times to slam on: 'scene' (its start) or 'scene.cue'; 0.75 s dim + 3 frozen frames before each
//   EP.sections  [[fromScene, toScene, label], ...] small grey label under the title bar (optional)
//   EP.cover     (w, h) => draw the cover; ?cover=1 renders it at 1080×1440 (3:4), ?cover=43 at 1440×1080 (4:3)
//   EP.colors    overrides for C (bg, red, gold, white, grey, fig, figS)
// All drawing goes through g (2D context) in a W×H coordinate space; render(t) depends on t only.
const Q = new URLSearchParams(location.search), COVER = Q.get('cover');
const cv = document.getElementById('c'), g = cv.getContext('2d');
const VW = innerWidth, VH = innerHeight; cv.width = VW; cv.height = VH;
const W = COVER === '1' ? 1080 : COVER === '43' ? 1440 : 1920, H = COVER === '1' ? 1440 : 1080;
const FONT = '"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif';
const EMOJI = '"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji"';
const C = { bg: '#111113', red: '#ff4a3d', gold: '#ffc94a', white: '#f2f2f5', grey: '#8d8d98', fig: '#e8e8ee', figS: '#a9a9b4' };
const TL = window.TL || { total: 1, offset: 0, scenes: [{ name: 'main', start: 0, cues: {} }], subs: [] };
const SC = {}; TL.scenes.forEach((s, i) => { SC[s.name] = Object.assign({ start: s.start, end: (TL.scenes[i + 1] || { start: TL.total }).start }, s.cues); });

// ---------- math ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const ss = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };   // smoothstep a→b
const eo = k => 1 - Math.pow(1 - clamp(k), 3);                                                   // ease-out cubic
function spring(x, w = 15, z = .72) { if (x <= 0) return 0; const wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * x) * (Math.cos(wd * x) + (z * w / wd) * Math.sin(wd * x)); }
function rnd(s) { s = Math.sin(s * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }      // deterministic noise
const win = (t, a, b, f = .25) => clamp(Math.min((t - a) / f, (b - t) / f));                      // fade in at a, out at b
const pop = (t, t0, w = 18, z = .55) => t < t0 ? 0 : spring(t - t0, w, z);
const counter = (t, t0, from, to, dur = .8) => t < t0 ? from : lerp(from, to, eo((t - t0) / dur));

// ---------- text: [red] {gold} ----------
let REC = null;   // collects on-screen text for window.TEXTS (lemo-styles readcheck); subtitles are not recorded
function segs(s) { const out = []; let cur = '', col = null; const map = { '[': C.red, '{': C.gold };
  for (const ch of s) { if (map[ch]) { if (cur) out.push([cur, col]); cur = ''; col = map[ch]; }
    else if (']}'.includes(ch)) { if (cur) out.push([cur, col]); cur = ''; col = null; } else cur += ch; }
  if (cur) out.push([cur, col]); return out; }
function txt(s, x, y, size, col = C.white, align = 'center', weight = 800, a = 1, glow = 0) {
  if (a <= 0) return 0; g.save(); g.globalAlpha *= a; g.font = `${weight} ${size}px ${FONT},${EMOJI}`; g.textBaseline = 'middle';
  const sg = segs(s); const w = sg.reduce((p, [t]) => p + g.measureText(t).width, 0);
  let x0 = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
  if (REC && g.globalAlpha > .3) { const m = g.getTransform(), k = W / VW;
    REC.push({ id: s, text: sg.map(p => p[0]).join(''), x0: (m.a * x0 + m.e) * k, x1: (m.a * (x0 + w) + m.e) * k, y0: (m.d * (y - size / 2) + m.f) * k, y1: (m.d * (y + size / 2) + m.f) * k }); }
  for (const [t, c] of sg) { const cc = c || col; g.fillStyle = cc;
    if (glow || c) { g.shadowColor = cc; g.shadowBlur = glow || 16; }
    g.fillText(t, x0, y); x0 += g.measureText(t).width; g.shadowBlur = 0; }
  g.restore(); return w;
}
// slam: a word drops in from 1.8× scale with a shock ring (the climax hit)
function slam(t, t0, s, x, y, size, col = C.gold, glow = 40) {
  if (t < t0) return; const d = t - t0, k = 1 + .8 * (1 - spring(d, 10, .9));
  g.save(); g.translate(x, y); g.scale(k, k); txt(s, 0, 0, size, col, 'center', 900, clamp(d / .08), glow); g.restore();
  if (d < .7) { g.save(); g.strokeStyle = col; g.globalAlpha = .8 * (1 - d / .7); g.lineWidth = 6; g.beginPath(); g.arc(x, y, 100 + 800 * eo(d / .7), 0, 7); g.stroke(); g.restore(); }
}
// stamp: a framed label punched in at an angle (verdicts: 测不出, 又是 253)
function stamp(t, t0, s, x, y, col = C.red, rot = -.12, size = 54) {
  if (t < t0) return; const d = t - t0, k = 1 + 1.4 * (1 - spring(d, 20, .8));
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(k, k); g.globalAlpha = clamp(d / .06);
  g.strokeStyle = col; g.lineWidth = 6; g.font = `900 ${size}px ${FONT}`; const w = g.measureText(s).width + 50;
  g.beginPath(); g.roundRect(-w / 2, -size * .8, w, size * 1.6, 12); g.stroke(); txt(s, 0, 2, size, col, 'center', 900, 1, 0); g.restore();
}

// ---------- shapes ----------
function stage(cx = W / 2, glow = 1) {   // top light + floor pool
  const rg = g.createRadialGradient(cx, -200, 50, cx, 300, 1100); rg.addColorStop(0, `rgba(255,255,255,${.13 * glow})`); rg.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = rg; g.fillRect(0, 0, W, H);
  const fl = g.createRadialGradient(cx, 820, 20, cx, 820, 700); fl.addColorStop(0, `rgba(255,255,255,${.07 * glow})`); fl.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = fl; g.beginPath(); g.ellipse(cx, 820, 760, 120, 0, 0, 7); g.fill();
}
function dot(x, y, r, col, a = 1, glow = 0) { if (a <= 0 || r <= 0) return; g.save(); g.globalAlpha *= a; g.fillStyle = col; if (glow) { g.shadowColor = col; g.shadowBlur = glow; } g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); g.restore(); }
function line(x1, y1, x2, y2, col, w = 2, a = 1) { if (a <= 0) return; g.save(); g.globalAlpha *= a; g.strokeStyle = col; g.lineWidth = w; g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke(); g.restore(); }
function card(x, y, w, h, a = 1, border = 'rgba(255,255,255,.18)') { if (a <= 0) return; g.save(); g.globalAlpha *= a; g.fillStyle = 'rgba(28,28,32,.92)'; g.strokeStyle = border; g.lineWidth = 2;
  g.beginPath(); g.roundRect(x - w / 2, y - h / 2, w, h, 16); g.fill(); g.stroke(); g.restore(); }
// mannequin figure, feet at (x, y), about 330·s tall. pose: stand / read / cheer / slump / think / pull
function figure(x, y, s, col = C.fig, pose = 'stand', t = 0, a = 1) {
  if (a <= 0) return; g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(s, s);
  const shade = col === C.red ? '#b8261c' : col === C.gold ? '#c99a2a' : C.figS;
  g.lineCap = 'round'; g.lineJoin = 'round';
  g.fillStyle = 'rgba(0,0,0,.45)'; g.beginPath(); g.ellipse(0, 4, 70, 12, 0, 0, 7); g.fill();
  const limb = (p, w, c) => { g.strokeStyle = c; g.lineWidth = w; g.beginPath(); g.moveTo(p[0], p[1]); for (let i = 2; i < p.length; i += 2) g.lineTo(p[i], p[i + 1]); g.stroke(); };
  const sl = pose === 'slump', hy = sl ? -258 : -290, hx = sl ? 18 : 0, dy = sl ? 18 : 0, sh = -228 + dy;
  limb([-18, -140, -24, -70, -26, 0], 26, shade); limb([18, -140, 24, -70, 28, 0], 26, col);
  g.fillStyle = col; g.beginPath(); g.roundRect(-38 + hx * .3, -248 + dy, 76, 120, 30); g.fill();
  const A = { read: [[-50, -170, -10, -175], [50, -170, 10, -175]], think: [[-50, -150, -40, -110], [60, -200, 30, -270]], pull: [[-50, -150, -40, -110], [90, -300, 60, -340]],
    slump: [[-46, -150, -40, -90], [46, -150, 40, -90]], stand: [[-46, -160, -44, -110], [46, -160, 44, -110]] };
  if (pose === 'cheer') { const w = Math.sin(t * 8) * 8; limb([-34, sh, -70, -300 + w, -80, -360 + w], 22, shade); limb([34, sh, 70, -300 - w, 80, -360 - w], 22, col); }
  else { const [l, r] = A[pose] || A.stand; limb([-34, sh, ...l], 22, shade); limb([34, sh, ...r], 22, col); }
  const hg = g.createRadialGradient(hx - 12, hy - 14, 4, hx, hy, 46); hg.addColorStop(0, '#fff'); hg.addColorStop(.35, col); hg.addColorStop(1, shade);
  g.fillStyle = hg; g.beginPath(); g.arc(hx, hy, 40, 0, 7); g.fill(); g.restore();
}

// ---------- chrome ----------
function titleBar(s) { g.fillStyle = 'rgba(255,255,255,.045)'; g.fillRect(0, 0, W, 108); g.fillStyle = C.red; g.fillRect(70, 32, 8, 44); txt(s, 100, 55, 44, C.white, 'left', 800); }
function subtitle(t) { const s = (TL.subs || []).find(([a, b]) => t >= a && t < b); if (!s) return; const keep = REC; REC = null;
  g.save(); g.font = `700 40px ${FONT}`; const w = g.measureText(s[2]).width; g.fillStyle = 'rgba(0,0,0,.55)'; g.beginPath(); g.roundRect(W / 2 - w / 2 - 24, 990, w + 48, 60, 10); g.fill(); g.restore();
  txt(s[2], W / 2, 1021, 40, C.white, 'center', 700); REC = keep; }
function finish(t) {   // vignette + film grain, drawn last
  const vg = g.createRadialGradient(W / 2, H / 2, H * .35, W / 2, H / 2, H * .95); vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.55)');
  g.fillStyle = vg; g.fillRect(0, 0, W, H);
  g.fillStyle = 'rgba(255,255,255,.022)'; const fs = Math.floor(t * 24); for (let i = 0; i < 240; i++) g.fillRect(rnd(fs * 1000 + i) * W, rnd(fs * 2000 + i) * H, 2, 2);
}

function startEpisode(EP) {
  Object.assign(C, EP.colors || {});
  const HARD = new Set(EP.hard || []), order = TL.scenes.map(s => s.name);
  const CLIMAX = (EP.climax || []).map(k => { const [s, cue] = k.split('.'); return cue ? SC[s][cue] : SC[s].start; });
  function frame(t) {
    g.fillStyle = C.bg; g.fillRect(0, 0, W, H);
    order.forEach((name, i) => { const a = SC[name].start, b = SC[name].end, fn = EP.scenes[name];
      if (!fn || t < a - .01 || t >= b + .3) return;
      if (t >= b && HARD.has(order[i + 1])) return;                       // the next scene cuts in hard: no overlap
      const fi = HARD.has(name) ? 1 : clamp((t - a) / .3), fo = t < b ? 1 : clamp((b + .3 - t) / .3);
      g.save(); g.globalAlpha = Math.min(fi, fo); fn(t, SC[name]); g.restore(); });
    for (const [a, b, s] of EP.sections || []) { const v = win(t, SC[a].start, SC[b].end, .3); if (v > 0) txt(s, 72, 150, 26, C.grey, 'left', 600, v); }
    if (EP.title) titleBar(EP.title);
    subtitle(t);
    for (const c of CLIMAX) if (t > c - .75 && t < c) { g.fillStyle = `rgba(0,0,0,${.75 * ss(c - .75, c - .1, t)})`; g.fillRect(0, 0, W, H); }
    finish(t);
  }
  window.ready = false;
  window.render = function (t) {
    for (const c of CLIMAX) if (t >= c - .1 && t < c) t = c - .1;         // freeze the last 3 frames before each slam
    g.setTransform(VW / W, 0, 0, VH / H, 0, 0);
    if (COVER) { g.fillStyle = C.bg; g.fillRect(0, 0, W, H); EP.cover && EP.cover(W, H); finish(0); } else frame(t);
  };
  window.TEXTS = t => { REC = []; window.render(t); const r = REC; REC = null; return r.map(b => ({ ...b, x0: b.x0 * VW / W, x1: b.x1 * VW / W, y0: b.y0 * VH / H, y1: b.y1 * VH / H })); };
  document.fonts.ready.then(() => { window.render(0); window.ready = window.READY = true; });
}
