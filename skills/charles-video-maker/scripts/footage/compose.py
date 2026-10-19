#!/usr/bin/env python3
"""Footage film: a bed of real footage under the code layer, plus short quotes from a source video with their own sound.

  compose.py footage.json out/<topic>.mp4 --overlay audio/overlay.mov --audio audio/mix.wav
  compose.py footage.json --check                    # only the material report

Run it in the project folder (it reads audio/timeline.json). Three layers:
  1. bed: footage.json "bed", one entry per shot, cut on scene starts or cues, graded with one look, cross-faded;
  2. code layer: the page rendered transparent (render_parallel.py "index.html?alpha=1" audio/overlay.mov ...) on top,
     with the narration mix (mix.py) as the sound;
  3. inserts: quotes from the source video spliced in before a scene, with their original sound, a caption and a source label.

footage.json:
  {"size": "1080x1920", "fps": 30, "grade": "warm", "band_y": 1000,
   "bed": [
     {"at": "cover", "src": "source/footage/gameplay.mp4", "in": 0, "fit": "band", "kind": "screen"},
     {"at": "map.dg", "src": "source/footage/pexels-123.mp4", "in": 2.0, "kind": "stock"},
     {"at": 12.5, "src": "source/footage/kiln.png", "move": "push", "kind": "gen"},
     {"at": "tier", "src": null}
   ],
   "inserts": [{"before": "battle", "src": "source/footage/talk.mp4", "in": 63.8, "out": 67.1,
                "caption": "芒格一辈子都在推崇一个古老的品格：可靠", "credit": "来源：某某访谈", "kind": "quote"}]}

  at      scene name (its start), "scene.cue", or seconds; the first entry is at 0. A shot lasts until the next one.
  fit     fill (crop to fill the frame, default for portrait sources) or band (a 16:9 source as a band at band_y over a
          blurred copy of itself, default for landscape sources)
  crop    [x0, y0, x1, y1] fractions of the source to keep before fitting, to zoom into part of a screen
  move    none | push | pull | left | right (default push for stills, none for video)
  speed   playback speed of a video shot (0.5 = slow motion)
  src     null = no footage: the code layer paints this part itself (counts as a pure information shot)
  grade   none | warm | cool | film, the one look for every shot (inserts keep their own look)
  kind    quote | stock | gen | screen, for the material report (guessed from the path when missing)
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GRADES = {
    'none': 'null',
    'warm': 'eq=contrast=1.05:saturation=1.1:gamma=0.98,colorbalance=rs=.05:gs=.01:bs=-.05:rm=.03:bm=-.03,vignette=PI/5',
    'cool': 'eq=contrast=1.05:saturation=1.0,colorbalance=rs=-.04:bs=.05:rm=-.02:bm=.03,vignette=PI/5',
    'film': 'eq=contrast=1.1:saturation=.85,colorbalance=rs=.03:bs=-.02:rh=.02:bh=-.04,vignette=PI/4,noise=alls=6:allf=t',
}
IMG = re.compile(r'\.(png|jpe?g|webp)$', re.I)


def ff(*args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *map(str, args)], check=True)


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration',
                          '-of', 'json', path], capture_output=True, text=True, check=True).stdout
    d = json.loads(out); s = d['streams'][0]
    return s['width'], s['height'], float(d.get('format', {}).get('duration') or 0)


def when(at, TL):
    if isinstance(at, (int, float)): return float(at)
    sc = {s['name']: s for s in TL['scenes']}
    name, _, cue = at.partition('.')
    if name not in sc: sys.exit(f'unknown scene in "at": {at}')
    return sc[name]['cues'][cue] if cue else sc[name]['start']


def kind_of(e):
    if e.get('kind'): return e['kind']
    if not e.get('src'): return 'info'
    p = e['src'].lower()
    return 'stock' if ('pexels' in p or 'pixabay' in p) else 'gen' if IMG.search(p) else 'footage'


def report(cfg, TL, shots, total):
    secs, warn = {}, []
    for (t0, t1, e) in shots:
        secs[kind_of(e)] = secs.get(kind_of(e), 0) + t1 - t0
    for q in cfg.get('inserts', []):
        secs[q.get('kind', 'quote')] = secs.get(q.get('kind', 'quote'), 0) + q['out'] - q['in']
    print(f'material ({total:.1f}s):  ' + '  '.join(f'{k} {v:.1f}s {v / total:.0%}' for k, v in sorted(secs.items(), key=lambda x: -x[1])))
    if secs.get('info', 0) / total > .2:
        warn.append(f"pure information shots are {secs['info'] / total:.0%} of the film (aim for 20% or less)")
    run = 0
    for (_, _, e) in shots:
        run = run + 1 if not e.get('src') else 0
        if run == 3: warn.append('three information-only shots in a row: put footage between them')
    for (a0, a1, a), (b0, b1, b) in zip(shots, shots[1:]):
        if a.get('src') and a.get('src') == b.get('src') and not IMG.search(a['src']):
            ia, ib = a.get('in', 0), b.get('in', 0)
            if ib < ia + (a1 - a0) * a.get('speed', 1) and ia < ib + (b1 - b0) * b.get('speed', 1):
                warn.append(f'shots at {a0:.1f}s and {b0:.1f}s show the same part of {a["src"]}')
    credits = open('source/credits.md', encoding='utf-8').read() if os.path.exists('source/credits.md') else ''
    for src in sorted({e['src'] for _, _, e in shots if e.get('src')} | {q['src'] for q in cfg.get('inserts', [])}):
        if os.path.basename(src) not in credits and not src.startswith(('img/', 'assets/')):
            warn.append(f'{src} is not in source/credits.md (where it came from, its licence)')
    for w in warn: print('  WARN', w)
    return warn


def shot(e, L, W, H, fps, grade, band_y, out):
    n = round(L * fps)
    if not e.get('src'):
        ff('-f', 'lavfi', '-i', f"color=c={e.get('color', '#101014')}:s={W}x{H}:r={fps}", '-frames:v', n, '-c:v', 'libx264', '-crf', 18, '-pix_fmt', 'yuv420p', out)
        return
    src, still = e['src'], bool(IMG.search(e['src']))
    sw, sh, sdur = probe(src)
    speed = e.get('speed', 1.0)
    if still:
        inp = ['-loop', 1, '-framerate', fps, '-t', L + .5, '-i', src]
    else:
        need = e.get('in', 0) + L * speed
        inp = (['-stream_loop', -1] if sdur and need > sdur else []) + ['-ss', e.get('in', 0), '-t', L * speed + .5, '-i', src]
    f = [f'setpts=(PTS-STARTPTS)/{speed}', f'fps={fps}']
    if e.get('crop'):
        x0, y0, x1, y1 = e['crop']; f.append(f'crop=iw*{x1 - x0}:ih*{y1 - y0}:iw*{x0}:ih*{y0}')
        sw, sh = sw * (x1 - x0), sh * (y1 - y0)
    fit = e.get('fit') or ('band' if sw / sh > W / H * 1.2 else 'fill')
    move = e.get('move') or ('push' if still else 'none')
    z0, z1 = {'push': (1, 1.12), 'pull': (1.12, 1)}.get(move, (1.1, 1.1) if move in ('left', 'right') else (1, 1))
    xs = {'left': "(iw-iw/zoom)*(1-on/{N})", 'right': "(iw-iw/zoom)*on/{N}"}.get(move, "iw/2-iw/zoom/2")
    def moved(w, h):               # zoompan at 2x for smooth sub-pixel motion, then back to w x h
        if move == 'none': return f'scale={w}:{h}'
        N = max(1, round(L * fps) - 1)
        return (f"scale={2 * w}:{2 * h},zoompan=z='{z0}+({z1}-{z0})*on/{N}':d=1:x='{xs.format(N=N)}':y='ih/2-ih/zoom/2':s={2 * w}x{2 * h}:fps={fps},"
                f'scale={w}:{h}')
    g = GRADES[grade]
    if fit == 'fill':
        cw, ch = (W, round(W * sh / sw)) if sw / sh < W / H else (round(H * sw / sh), H)
        cw, ch = cw + cw % 2, ch + ch % 2
        fc = f"[0:v]{','.join(f)},scale={cw}:{ch},crop={W}:{H},{moved(W, H)},{g},format=yuv420p,setsar=1[v]"
    else:
        bh = round(W * sh / sw); bh += bh % 2
        fc = (f"[0:v]{','.join(f)},split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:2,"
              f"eq=brightness=-0.12:saturation=0.8[bg];[b]{moved(W, bh)}[fg];[bg][fg]overlay=0:{band_y}-h/2,{g},format=yuv420p,setsar=1[v]")
    ff(*inp, '-filter_complex', fc, '-map', '[v]', '-frames:v', n, '-an', '-c:v', 'libx264', '-crf', 18, '-preset', 'veryfast', out)


def text_png(text, out, W, H, size, y, align='center', tmp='.'):
    """caption / label as a transparent PNG, drawn by the browser (this ffmpeg may lack drawtext)"""
    page = os.path.join(tmp, 'text.html')
    pos = 'left:36px;' if align == 'left' else 'left:0;right:0;text-align:center;'
    open(page, 'w', encoding='utf-8').write(
        '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:transparent}'
        f'div{{position:absolute;{pos}top:{y}px;font:800 {size}px "Noto Sans CJK SC","PingFang SC",sans-serif;color:#fff;'
        'text-shadow:0 2px 6px #000,0 0 2px #000;padding:0 40px;line-height:1.35}</style>'
        f'<div>{text}</div><script>window.render=()=>{{}}</script>')
    subprocess.run(['python3', os.path.join(HERE, '..', 'render.py'), page + '?alpha=1', out, '--still', '0', '--size', f'{W}x{H}'],
                   check=True, capture_output=True)


def insert(q, W, H, fps, band_y, tmp, k):
    L = q['out'] - q['in']
    base = os.path.join(tmp, f'ins{k}')
    shot({'src': q['src'], 'in': q['in'], 'fit': q.get('fit'), 'crop': q.get('crop')}, L, W, H, fps, 'none', band_y, base + '.v.mp4')
    text_png(q.get('caption', ''), base + '.cap.png', W, H, 52, int(H * .8), tmp=tmp)   # empty caption: the source has its own subtitles
    text_png(q.get('credit', ''), base + '.cred.png', W, H, 36, 120, 'left', tmp=tmp)
    n = round(L * fps)
    ff('-i', base + '.v.mp4', '-i', base + '.cap.png', '-i', base + '.cred.png', '-ss', q['in'], '-t', L, '-i', q['src'],
       '-filter_complex', f'[0][1]overlay[a];[a][2]overlay,format=yuv420p,setsar=1[v];'
       f'[3:a]loudnorm=I=-14:TP=-1.5,afade=t=in:d=0.05,afade=t=out:st={L - .12:.3f}:d=0.12,aformat=sample_rates=48000:channel_layouts=stereo[s]',
       '-map', '[v]', '-map', '[s]', '-frames:v', n, '-c:v', 'libx264', '-crf', 18, '-c:a', 'aac', '-b:a', '192k', '-shortest', base + '.mp4')
    return base + '.mp4', L


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('config'); ap.add_argument('out', nargs='?')
    ap.add_argument('--overlay', help='transparent code layer (.mov from render_parallel.py "index.html?alpha=1")')
    ap.add_argument('--audio', help='narration mix (audio/mix.wav)')
    ap.add_argument('--xfade', type=float, default=.25, help='cross-fade between shots, seconds')
    ap.add_argument('--check', action='store_true', help='only print the material report')
    a = ap.parse_args()
    cfg, TL = json.load(open(a.config)), json.load(open('audio/timeline.json'))
    W, H = map(int, cfg.get('size', '1080x1920').split('x')); fps = cfg.get('fps', 30); total = TL['total']
    band_y, grade = cfg.get('band_y', H // 2), cfg.get('grade', 'none')
    bed = sorted(cfg['bed'], key=lambda e: when(e['at'], TL))
    if when(bed[0]['at'], TL) > 0: sys.exit('the first bed entry must be at 0 (the cover)')
    starts = [when(e['at'], TL) for e in bed] + [total]
    shots = [(starts[i], starts[i + 1], e) for i, e in enumerate(bed)]
    warn = report(cfg, TL, shots, total + sum(q['out'] - q['in'] for q in cfg.get('inserts', [])))
    if a.check: return
    if not a.out: sys.exit('give the output path')

    tmp = tempfile.mkdtemp(prefix='compose_')
    X = a.xfade
    segs = []
    for i, (t0, t1, e) in enumerate(shots):
        L = t1 - t0 + (X if i < len(shots) - 1 else 0)
        seg = os.path.join(tmp, f'bed{i:02d}.mp4'); shot(e, L, W, H, fps, grade, band_y, seg); segs.append(seg)
        print(f'  shot {i + 1}/{len(shots)} {t0:6.2f}s {e.get("src") or "(code layer)"}', flush=True)
    bedv = os.path.join(tmp, 'bed.mp4')
    if len(segs) == 1:
        shutil.copy(segs[0], bedv)
    else:
        fc, last = [], '[0:v]'
        for i in range(1, len(segs)):
            fc.append(f'{last}[{i}:v]xfade=transition=fade:duration={X}:offset={starts[i]:.4f}[x{i}]'); last = f'[x{i}]'
        ff(*sum((['-i', s] for s in segs), []), '-filter_complex', ';'.join(fc), '-map', last, '-frames:v', round(total * fps),
           '-c:v', 'libx264', '-crf', 17, '-preset', 'veryfast', '-pix_fmt', 'yuv420p', bedv)

    film = os.path.join(tmp, 'film.mp4')
    args, fc, vmap = ['-i', bedv], '', '0:v'
    if a.overlay:
        args += ['-i', a.overlay]; fc = '[0:v][1:v]overlay=format=auto,format=yuv420p[v]'; vmap = '[v]'
    if a.audio:
        args += ['-i', a.audio]
    amap = ['-map', f'{len(args) // 2 - 1}:a', '-af', 'apad', '-c:a', 'aac', '-b:a', '192k', '-ar', 48000, '-ac', 2] if a.audio else []
    ff(*args, *(['-filter_complex', fc] if fc else []), '-map', vmap, *amap, '-frames:v', round(total * fps),
       '-c:v', 'libx264', '-crf', 17, '-pix_fmt', 'yuv420p', film)

    ins = sorted(cfg.get('inserts', []), key=lambda q: when(q['before'], TL))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if not ins:
        shutil.move(film, a.out)
    else:
        cuts = [when(q['before'], TL) for q in ins]
        if cuts[0] <= 0: sys.exit('an insert cannot come before the cover')
        parts, inputs = [], ['-i', film]
        for k, q in enumerate(ins):
            path, _ = insert(q, W, H, fps, band_y, tmp, k); inputs += ['-i', path]
        bounds = [0] + cuts + [total]
        fc = [f'[0:v]split={len(bounds) - 1}' + ''.join(f'[v{j}]' for j in range(len(bounds) - 1)),
              f'[0:a]asplit={len(bounds) - 1}' + ''.join(f'[a{j}]' for j in range(len(bounds) - 1))]
        for j in range(len(bounds) - 1):
            fc.append(f'[v{j}]trim={bounds[j]:.4f}:{bounds[j + 1]:.4f},setpts=PTS-STARTPTS,setsar=1[fv{j}]')
            fc.append(f'[a{j}]atrim={bounds[j]:.4f}:{bounds[j + 1]:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,afade=t=out:st={bounds[j + 1] - bounds[j] - .06:.4f}:d=0.06[fa{j}]')
            parts += [f'[fv{j}][fa{j}]']
            if j < len(ins): parts += [f'[{j + 1}:v][{j + 1}:a]']
        fc.append(''.join(parts) + f'concat=n={len(parts)}:v=1:a=1[v][a]')
        ff(*inputs, '-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', 17, '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', a.out)
    shutil.rmtree(tmp)
    w, h, d = probe(a.out)
    print(f'{a.out}: {w}x{h}, {d:.2f}s' + (f', {len(warn)} warnings above' if warn else ''))


if __name__ == '__main__':
    main()
