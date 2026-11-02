"""Master a mix to -14 LUFS without flattening its dynamics: static gain + a peak-only limiter.

  cd <project>/audio && ~/lemo-opuscar/.venv/bin/python <skill>/scripts/master_static.py     # reads mix_raw.wav -> mix.wav

Why not `ffmpeg loudnorm` single-pass: it is dynamic and evens out loudness, so a deliberately louder opening
(Douyin rule: the first 3 s are the strongest part) comes out as loud as the body. Two-pass `linear=true` falls back
to dynamic whenever the needed gain would clip. This keeps the level difference and only shaves transient peaks.
"""
import os, sys, subprocess, re
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.expanduser('~/lemo-opuscar')); from core.audio import sfx as X
x, sr = sf.read('mix_raw.wav')
def lufs(path):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', out)[-1]), float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', out)[-1])
y = x
for _ in range(4):
    sf.write('mix.wav', y, sr, subtype='PCM_24'); I, tp = lufs('mix.wav')
    if abs(I + 14) < .3 and tp <= -1.5: break
    y = y * 10 ** ((-14 - I) / 20)
    y = X.limit(y, ceil=.7) if y.ndim == 1 else np.stack([X.limit(y[:, 0], ceil=.7), X.limit(y[:, 1], ceil=.7)], 1)
sf.write('mix.wav', y, sr, subtype='PCM_24'); print('LUFS %.1f  true peak %.1f' % lufs('mix.wav'))
