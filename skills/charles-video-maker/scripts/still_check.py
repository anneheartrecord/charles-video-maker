#!/usr/bin/env python3
"""Find stretches where the picture stops moving, and subtitle swaps the picture doesn't follow.

  still_check.py out/<name>.mp4                                  # still stretches longer than 2 s
  still_check.py out/<name>.mp4 --subs audio/subs.srt           # also: subtitle changed, picture didn't
  still_check.py out/<name>.mp4 --allow 85.9-91.3 --max 2.0     # skip the end card (repeatable)

Why: viewers watch knowledge, they don't read it. When the subtitle keeps changing but the picture holds
still for more than 2 seconds, people swipe away (rule from the 许先森Ai teardown, 2026-10-26: his four hits
held still 0-2.2 times a minute, the longest 3.6 s; his flops about 6 times a minute, up to 5.8 s).

Only the picture above the subtitle band is measured (--band, fraction of the height, default 0.78), so a
subtitle swapping on a frozen picture still counts as still. Exit code 1 when anything is flagged.
Calibrated at 192x108 grayscale, 5 fps: a frame counts as still when the mean absolute change is under 0.4.
"""
import argparse, re, subprocess, sys
import numpy as np

W, H, FPS = 192, 108, 5


def frames(path, band):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-vf', f'fps={FPS},scale={W}:{H},format=gray',
                          '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
    return fr[:, :int(H * band), :]


def srt(path):
    ts = lambda s: sum(float(x) * m for x, m in zip(s.replace(',', '.').split(':'), (3600, 60, 1)))
    cues = re.findall(r'(\d+:\d+:[\d,.]+)\s*-->\s*(\d+:\d+:[\d,.]+)\s*\n(.+?)(?:\n\n|\Z)', open(path, encoding='utf-8').read(), re.S)
    return [(ts(a), ts(b), t.strip().replace('\n', ' ')) for a, b, t in cues]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video')
    ap.add_argument('--subs', help='subs.srt: check that the picture moves within --follow seconds of every new subtitle')
    ap.add_argument('--max', type=float, default=2.0, help='longest allowed still stretch in seconds (default 2.0)')
    ap.add_argument('--follow', type=float, default=1.0, help='seconds after a subtitle starts in which the picture must move')
    ap.add_argument('--band', type=float, default=0.78, help='measure the picture above this fraction of the height')
    ap.add_argument('--thresh', type=float, default=0.4, help='mean absolute change below which a frame is still')
    ap.add_argument('--allow', action='append', default=[], help='START-END seconds to skip, e.g. an end card')
    a = ap.parse_args()

    fr = frames(a.video, a.band)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))           # d[i] = change from frame i to i+1
    still = d < a.thresh
    allow = [tuple(map(float, s.split('-'))) for s in a.allow]
    allowed = lambda t0, t1: any(s <= t0 and t1 <= e for s, e in allow)
    dur = len(fr) / FPS

    runs, i = [], 0
    while i < len(still):
        if still[i]:
            j = i
            while j < len(still) and still[j]: j += 1
            t0, t1 = i / FPS, (j + 1) / FPS
            if t1 - t0 > a.max and not allowed(t0, t1): runs.append((t0, t1))
            i = j
        else:
            i += 1
    print(f'{a.video}: {dur:.1f}s, {len(runs)} still stretch(es) over {a.max:g}s ({len(runs) / dur * 60:.1f} per minute; '
          f'reference: hits 0-2.2, flops ~6)')
    for t0, t1 in runs:
        print(f'  STILL {t0:6.1f}-{t1:6.1f}s  ({t1 - t0:.1f}s)')

    frozen = []
    if a.subs:
        for s, e, text in srt(a.subs):
            k0, k1 = int(s * FPS), int(min(e, s + a.follow) * FPS) + 1
            if k0 >= len(d) or allowed(s, s + a.follow): continue
            if d[k0:max(k1, k0 + 1)].max() < a.thresh * 2:            # nothing in the picture changed when the line came up
                frozen.append((s, text))
        print(f'  {len(frozen)} subtitle(s) the picture did not follow within {a.follow:g}s')
        for s, text in frozen:
            print(f'  FROZEN {s:6.1f}s  {text[:30]}')
    sys.exit(1 if runs or frozen else 0)


if __name__ == '__main__':
    main()
