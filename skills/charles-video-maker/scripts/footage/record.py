#!/usr/bin/env python3
"""Record a real web page (a product, a game, a site) as footage, driven by a list of actions.

  record.py https://example.com source/footage/demo.mp4 --actions actions.json --size 1600x900

actions.json is a list, run in order:
  {"wait": 1.5}                          seconds of plain recording
  {"click": "开 始 游 戏"}                click the element with this exact text, else the first one containing it
  {"click_xy": [476, 163]}               click at viewport coordinates
  {"move": [800, 300], "steps": 30}      glide the mouse there (hover effects show up)
  {"scroll": 600}                        wheel scroll by this many pixels
  {"key": "Enter"}                       press a key
  {"mark": "battle"}                     note the current second into <out>.marks.json, for in-points in footage.json

Frames come from Chrome's screencast at full quality and are re-timed to a constant frame rate, so the result is
sharp (Playwright's built-in recorder is low-bitrate VP8). Sites that need a login are recorded only with the user's consent.
"""
import argparse, base64, json, os, subprocess, sys, tempfile, time

from playwright.sync_api import sync_playwright


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('url'); ap.add_argument('out')
    ap.add_argument('--actions', help='JSON file with the action list (default: just wait --wait seconds)')
    ap.add_argument('--wait', type=float, default=5, help='seconds to record when there is no action list')
    ap.add_argument('--size', default='1600x900')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--scale', type=float, default=1, help='device scale factor (2 = retina-sharp, bigger frames)')
    a = ap.parse_args()
    W, H = map(int, a.size.split('x'))
    acts = json.load(open(a.actions)) if a.actions else [{'wait': a.wait}]
    tmp = tempfile.mkdtemp(prefix='record_')
    frames, marks = [], {}

    with sync_playwright() as p:
        br = p.chromium.launch(headless=True, args=['--enable-gpu', '--ignore-gpu-blocklist'])
        pg = br.new_page(viewport={'width': W, 'height': H}, device_scale_factor=a.scale)
        pg.goto(a.url, wait_until='networkidle', timeout=120000)
        cdp = pg.context.new_cdp_session(pg)

        def on_frame(e):
            path = os.path.join(tmp, f'{len(frames):06d}.jpg')
            open(path, 'wb').write(base64.b64decode(e['data']))
            frames.append((e['metadata']['timestamp'], path))
            cdp.send('Page.screencastFrameAck', {'sessionId': e['sessionId']})

        cdp.on('Page.screencastFrame', on_frame)
        cdp.send('Page.startScreencast', {'format': 'jpeg', 'quality': 92, 'maxWidth': int(W * a.scale), 'maxHeight': int(H * a.scale)})
        for act in acts:
            if 'wait' in act: pg.wait_for_timeout(act['wait'] * 1000)
            elif 'click' in act:                     # exact text first, else the first element containing it
                loc = pg.get_by_text(act['click'], exact=True)
                (loc if loc.count() else pg.get_by_text(act['click'])).first.click(timeout=10000)
            elif 'click_xy' in act: pg.mouse.click(*act['click_xy'])
            elif 'move' in act: pg.mouse.move(*act['move'], steps=act.get('steps', 25))
            elif 'scroll' in act: pg.mouse.wheel(0, act['scroll'])
            elif 'key' in act: pg.keyboard.press(act['key'])
            elif 'mark' in act: marks[act['mark']] = time.time()   # wall clock, same base as the screencast timestamps
            else: sys.exit(f'unknown action: {act}')
        pg.wait_for_timeout(300)
        t_end = time.time()
        cdp.send('Page.stopScreencast')
        br.close()

    if len(frames) < 2:
        sys.exit('no frames captured (is the page static and headless-rendered?)')
    marks = {k: round(v - frames[0][0], 2) for k, v in marks.items()}
    # screencast only sends a frame when something changes: for every output frame, pipe the latest screencast frame
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    start, end = frames[0][0], max(t_end, frames[-1][0] + .1)
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', str(a.fps), '-i', '-',
                           '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p', '-c:v', 'libx264', '-crf', '16', a.out], stdin=subprocess.PIPE)
    k = 0
    for n in range(round((end - start) * a.fps)):
        while k + 1 < len(frames) and frames[k + 1][0] - start <= n / a.fps: k += 1
        ff.stdin.write(open(frames[k][1], 'rb').read())
    ff.stdin.close()
    if ff.wait(): sys.exit('ffmpeg failed')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from source import credit
    credit(f'- `{os.path.basename(a.out)}` · 实录 {a.url} · 自录 · 实机画面')
    if marks:
        json.dump(marks, open(os.path.splitext(a.out)[0] + '.marks.json', 'w'), indent=1)
    dur = end - start
    print(f'{a.out}: {dur:.1f}s, {len(frames)} screencast frames -> {a.fps}fps' + (f', marks {marks}' if marks else ''))
    for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


if __name__ == '__main__':
    main()
