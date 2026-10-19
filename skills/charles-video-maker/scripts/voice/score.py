#!/usr/bin/env python3
"""A score played on real sampled instruments, laid on the narration timeline -> audio/score.wav for mix.py --score.

  $LIB/.venv/bin/python score.py --dir <project> --palette play      # LIB = the Lemo-Opuscar library (scripts/lemo/setup.sh)
  python3 mix.py --dir <project> --score audio/score.wav              # then mix it under the voice instead of the lo-fi bed

Palettes (each instrument falls back to one from VSCO 2 CE / VCSL when its sample library is not downloaded;
fetch all five with: sh $LIB/tools/fetch.sh instruments all):
  keys    grand piano + jazz bass + shaker                 calm explainer
  play    marimba + cello pizzicato + glockenspiel         games, products, light topics
  cine    cello and viola pads + harp + timpani on cuts    serious, story, money
  east    dan tranh zither + erhu + frame drum             Chinese culture, history
  guitar  nylon guitar + jazz bass + shaker                vlog, personal story
Writes audio/score.wav (mono, 48 kHz, 16-bit) and audio/score-credits.txt (licence lines for the sample libraries).
"""
import argparse, json, os, sys
import numpy as np

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--dir', default='.')
ap.add_argument('--palette', choices=['keys', 'play', 'cine', 'east', 'guitar'], default='keys')
ap.add_argument('--bpm', type=float)
a = ap.parse_args()
LIB = os.environ.get('LEMO_OPUSCAR_HOME', os.path.expanduser('~/lemo-opuscar'))
sys.path.insert(0, LIB)
try:
    from core.audio import sampler as S
    import soundfile as sf
except ImportError:
    sys.exit(f'run this with the library Python: {LIB}/.venv/bin/python (install with sh scripts/lemo/setup.sh deps)')
os.chdir(a.dir)
TL = json.load(open('audio/timeline.json'))
DUR = TL['total']
BPM = a.bpm or {'keys': 88, 'play': 108, 'cine': 76, 'east': 84, 'guitar': 92}[a.palette]


def pick(*names):
    """the first instrument whose sample library is downloaded"""
    for n in names:
        try: S.load(n); return n
        except Exception: pass
    sys.exit(f'none of {names} is available: sh {LIB}/tools/fetch.sh instruments all')


PIANO, BASS, ERHU, GUITAR = pick('piano', 'upright'), pick('jazz_bass', 'contrabass_pizz'), pick('erhu', 'flute'), pick('guitar_nylon', 'harp')
BG = 2.2 if BASS == 'jazz_bass' else 1.0   # the jazz bass samples are recorded much quieter than the orchestral ones
BEAT = 60 / BPM; BAR = 4 * BEAT; bars = int(DUR / BAR) + 1
CHORDS = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]   # Fmaj7 Em7 Dm7 Cmaj7
ROOTS = [41, 40, 38, 36]
PENTA = [60, 62, 64, 67, 69]
ev = []   # (t, inst, pitch, dur, vel, pan) or dicts with attack / release
E = lambda t, inst, p, d, v, pan=0, **kw: ev.append(dict(t=t, inst=inst, pitch=p, dur=d, vel=v, pan=pan, **kw)) if t < DUR else None

for b in range(bars):
    t0, ch, root = b * BAR, CHORDS[b % 4], ROOTS[b % 4]
    last = b == bars - 1
    if a.palette == 'keys':
        for k, m in enumerate(ch): E(t0 + k * .015, PIANO, m, BAR * (1.5 if last else .9), .42, -.2 + k * .13)
        if not last:
            for k, m in enumerate(ch[1:]): E(t0 + 2.5 * BEAT, PIANO, m + 12, BEAT * 1.2, .28, .2)
            E(t0, BASS, root, BEAT, .45, gain=BG); E(t0 + 2 * BEAT, BASS, root + 7, BEAT, .35, gain=BG)
            if b: [E(t0 + e * BEAT / 2, 'shaker', None, None, .22 if e % 2 else .14, .3) for e in range(8)]
    elif a.palette == 'play':
        tones = [m + 12 for m in ch]
        for e in range(4 if last else 8): E(t0 + e * BEAT / 2, 'marimba', tones[[0, 1, 2, 3, 2, 1, 2, 3][e]], BEAT, .5 if e % 2 == 0 else .38, -.15)
        if not last:
            E(t0, 'cellos_pizz', root, BEAT, .7); E(t0 + 2 * BEAT, 'cellos_pizz', root + 7, BEAT, .55)
            if b % 2 == 0: E(t0, 'glockenspiel', ch[-1] + 24, BEAT * 2, .3, .3)
            if b: [E(t0 + e * BEAT / 2, 'shaker', None, None, .2 if e % 2 else .12, .3) for e in range(8)]
    elif a.palette == 'cine':
        d = BAR * (2 if last else 1) + .4
        for m in ch[:2]: E(t0, 'cellos', m - 12, d, .45, -.3, attack=.5)
        for m in ch[2:]: E(t0, 'violas', m, d, .4, .3, attack=.5)
        E(t0, 'contrabass', root - 12, d, .5, 0, attack=.3)
        if b >= 2 and not last: [E(t0 + e * BEAT / 2, 'harp', ch[e % 4] + 12 * (1 + e // 4), BEAT, .35, .2) for e in range(8)]
    elif a.palette == 'guitar':
        pat = [0, 2, 1, 3, 2, 1, 3, 2]
        for e in range(4 if last else 8): E(t0 + e * BEAT / 2, GUITAR, ch[pat[e]] + (12 if pat[e] > 1 else 0), BEAT * 1.6, .5 if e % 2 == 0 else .38, -.1)
        if not last:
            E(t0, BASS, root, BEAT * 1.5, .45, gain=BG); E(t0 + 2.5 * BEAT, BASS, root + 7, BEAT, .35, gain=BG)
            if b: [E(t0 + e * BEAT / 2, 'shaker', None, None, .18 if e % 2 else .1, .3) for e in range(8)]
    else:   # east
        for e in range(4 if last else 8): E(t0 + e * BEAT / 2, 'dan_tranh', PENTA[(e * 2 + b) % 5] + (12 if e % 4 == 3 else 0), BEAT * 1.5, .48 if e % 2 == 0 else .36, -.2)
        E(t0, 'cellos', root, BAR + .4, .32, .2, attack=.6)
        if b % 2 == 1 and not last: E(t0, ERHU, PENTA[b % 5] + 12, BEAT * 2.5, .34, .25, attack=.15); E(t0 + 3 * BEAT, ERHU, PENTA[(b + 2) % 5] + 12, BEAT, .3, .25)
        if b and not last: E(t0, 'frame_drum', None, None, .45); E(t0 + 2.5 * BEAT, 'frame_drum', None, None, .3)
if a.palette == 'cine':   # timpani under every scene change
    for sc in TL['scenes'][1:]: E(sc['start'], 'timpani', 41, 1.5, .5)

S.seed(7)
st = S.room(S.render(ev, DUR + 1, master=False), size=.45, mix=.18)
mono = st.mean(axis=1)[:int(DUR * S.SR)]
from scipy.signal import butter, sosfilt   # keep 20-120 Hz a few dB under the rest, so it does not boom on phones
mono = sosfilt(butter(2, 90, 'highpass', fs=S.SR, output='sos'), mono)
fade = int(1.5 * S.SR); mono[-fade:] *= np.linspace(1, 0, fade)
mono = mono / (np.abs(mono).max() + 1e-9) * .9
sf.write('audio/score.wav', mono, S.SR, subtype='PCM_16')
names = sorted({e['inst'] for e in ev})
open('audio/score-credits.txt', 'w').write('\n'.join(S.credits(names)) + '\n')
print(f'audio/score.wav: {DUR:.1f}s, {a.palette}, {BPM:.0f} bpm, {len(ev)} notes, instruments {", ".join(names)}')
