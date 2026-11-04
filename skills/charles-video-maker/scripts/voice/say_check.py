#!/usr/bin/env python3
"""Check what the TTS actually said against the script: swallowed numbers, dropped or misread words.

  say_check.py --dir <project>          # reads audio/narration.txt and audio/voice_segments.json (align.py)

Both texts are reduced to Chinese characters, with every number spelled out the way it is read (20,186 → 二万零一百八十六,
2004 年 → 二零零四年, 67% → 百分之六十七, 两 → 二), then aligned character by character. Every place where the
transcript differs from the script is listed with its time in the voice track:

  NUM   the difference touches a number: listen, and if the TTS swallowed or misread it, write the number out in
        Chinese characters in narration.txt (3628800 → 三百六十二万八千八百) and synthesize again
  WORD  only words differ: often Whisper mishearing a homophone (老幺 → 老妖), sometimes the TTS misreading;
        listen to that second before deciding (re-synthesizing usually fixes a real misreading)

Exit code 1 when any NUM difference is found, so batch scripts can stop on it.
"""
import argparse, difflib, json, os, re, sys

D = '零一二三四五六七八九'


def under_10k(n):
    out, zero = '', False
    for v, u in ((1000, '千'), (100, '百'), (10, '十'), (1, '')):
        d = n // v % 10
        if d:
            if zero and out: out += '零'
            out += D[d] + u; zero = False
        elif out: zero = True
    return out


def spell(n):
    if n == 0: return '零'
    parts, i, out = [], 0, ''
    while n:
        parts.append(n % 10000); n //= 10000
    for i in range(len(parts) - 1, -1, -1):
        p = parts[i]
        if p:
            if out and p < 1000: out += '零'
            out += under_10k(p) + ('', '万', '亿', '万亿')[i]
        elif out and not out.endswith('零'): pass
    out = re.sub('零+', '零', out).rstrip('零')
    return out[1:] if out.startswith('一十') else out   # 十五, not 一十五


NUM = re.compile(r'(\d{4})(?=\s*年)|(\d+(?:,\d{3})*(?:\.\d+)?)(\s*%)?|两')


def spoken(s, times=None):
    """s with numbers spelled out, as a list of (character, time); only Chinese characters and letters are kept."""
    times = times or [0.0] * len(s)
    out, i = [], 0
    for m in NUM.finditer(s):
        out += zip(s[i:m.start()], times[i:m.start()]); t = times[m.start()]
        if m.group(1): rep = ''.join(D[int(c)] for c in m.group(1))                     # years read digit by digit
        elif m.group(2):
            a_, _, b_ = m.group(2).replace(',', '').partition('.')
            rep = spell(int(a_)) + ('点' + ''.join(D[int(c)] for c in b_) if b_ else '')
            if m.group(3): rep = '百分之' + rep
        else: rep = '二'
        out += [(c, t) for c in rep]; i = m.end()
    out += zip(s[i:], times[i:])
    return [(c, t) for c, t in out if '\u4e00' <= c <= '\u9fff' or c.isalpha()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dir', default='.')
    ap.add_argument('--context', type=int, default=6, help='script characters shown on each side of a difference')
    a = ap.parse_args()
    script = open(os.path.join(a.dir, 'audio/narration.txt')).read()
    segs = json.load(open(os.path.join(a.dir, 'audio/voice_segments.json')))
    text, ts = '', []   # the transcript joined back into one string, with the start time of each character's word
    for seg in segs:
        for w in seg.get('words') or [{'word': seg['text'], 'start': seg['start']}]:
            text += w['word']; ts += [w['start']] * len(w['word'])
    got = spoken(text, ts)
    heard, times = [c for c, _ in got], [t for _, t in got]
    want = [c for c, _ in spoken(script)]
    nums = set(D + '十百千万亿点')
    found = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, want, heard, autojunk=False).get_opcodes():
        if op == 'equal': continue
        a_txt, b_txt = ''.join(want[i1:i2]), ''.join(heard[j1:j2])
        kind = 'NUM ' if set(a_txt + b_txt) & nums else 'WORD'
        t = times[min(j1, len(times) - 1)] if times else 0
        ctx = ''.join(want[max(0, i1 - a.context):i1]) + '【' + a_txt + '】' + ''.join(want[i2:i2 + a.context])
        print(f'{kind}  {t:6.2f}s  script {ctx}   heard 【{b_txt or "（没念）"}】')
        found += kind == 'NUM '
    print(f'{found} number difference(s)' if found else 'numbers: all read as written')
    sys.exit(1 if found else 0)


if __name__ == '__main__':
    main()
