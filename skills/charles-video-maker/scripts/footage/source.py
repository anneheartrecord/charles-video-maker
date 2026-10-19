#!/usr/bin/env python3
"""Source video for quoting: download it, transcribe it, find where a sentence is said.

  source.py fetch <url> --name talk                    # yt-dlp -> source/footage/talk.mp4, logged in source/credits.md
  source.py transcribe source/footage/talk.mp4         # -> talk.words.json + talk.transcript.txt (timestamped lines)
  source.py find source/footage/talk.mp4 "原话里的一句"   # -> in / out seconds of that sentence, for footage.json

Ask the user before downloading anything, and only quote short pieces with commentary around them
(references/footage-layer.md). Transcription uses voice/align.py (mlx-whisper or faster-whisper; through uv if
not installed). `find` matches by characters, so recognition mistakes or small wording differences still land.
"""
import argparse, json, os, re, subprocess, sys
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
norm = lambda c: c.lower() if (c.isalnum() or '一' <= c <= '鿿') else ''


def credit(line):
    os.makedirs('source', exist_ok=True)
    new = not os.path.exists('source/credits.md')
    with open('source/credits.md', 'a', encoding='utf-8') as f:
        if new:
            f.write('# 素材来源\n\n每段外部素材一行：文件 · 标题 · 作者 · 链接 · 许可 / 用途\n\n')
        f.write(line + '\n')


def fetch(a):
    out = f'source/footage/{a.name}.mp4'
    os.makedirs('source/footage', exist_ok=True)
    subprocess.run(['yt-dlp', '-f', 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/b', '--merge-output-format', 'mp4',
                    '-o', out, '--no-playlist', a.url], check=True)
    info = json.loads(subprocess.run(['yt-dlp', '-J', '--no-playlist', a.url], capture_output=True, text=True).stdout or '{}')
    credit(f"- `{a.name}.mp4` · {info.get('title', '?')} · {info.get('uploader', '?')} · {a.url} · 引用（原片，只截短片段）")
    print(f'{out}: {info.get("duration", "?")}s · {info.get("title", "")}')


def transcribe(a):
    base = os.path.splitext(a.video)[0]
    wav = base + '.16k.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.video, '-ac', '1', '-ar', '16000', wav], check=True)
    align = os.path.join(HERE, '..', 'voice', 'align.py')
    try:
        import mlx_whisper  # noqa: F401
        cmd = ['python3', align]
    except ImportError:
        cmd = ['uv', 'run', '--with', 'mlx-whisper' if sys.platform == 'darwin' else 'faster-whisper', 'python', align]
    subprocess.run(cmd + [wav, base + '.words.json', '--lang', a.lang], check=True)
    os.remove(wav)
    segs = json.load(open(base + '.words.json'))
    mmss = lambda t: f'{int(t // 60):02d}:{t % 60:05.2f}'
    open(base + '.transcript.txt', 'w', encoding='utf-8').write('\n'.join(f"[{mmss(s['start'])} - {mmss(s['end'])}] {s['text'].strip()}" for s in segs) + '\n')
    print(f'{base}.transcript.txt: {len(segs)} lines')


def locate(words_json, query):
    """best (in, out, score) for query in the transcript; score = share of query characters matched"""
    chars, times = [], []
    for s in json.load(open(words_json)):
        for w in s.get('words', []):
            cs = [c for c in w['word'] if norm(c)]
            for k, c in enumerate(cs):
                chars.append(norm(c)); times.append((w['start'] + (w['end'] - w['start']) * k / len(cs), w['end']))
    q = ''.join(norm(c) for c in query)
    if not q or not chars:
        return None
    blocks = [b for b in SequenceMatcher(None, ''.join(chars), q, autojunk=False).get_matching_blocks() if b.size]
    best = None
    for i in range(len(blocks)):                 # densest run of matches spanning at most twice the query length
        got, j = 0, i
        while j < len(blocks) and blocks[j].a + blocks[j].size - blocks[i].a <= 2 * len(q):
            got += blocks[j].size; j += 1
        if not best or got > best[0]:
            best = (got, blocks[i].a, blocks[j - 1].a + blocks[j - 1].size - 1)
    got, i0, i1 = best
    return max(0, times[i0][0] - .15), times[i1][1] + .25, got / len(q)


def find(a):
    words = os.path.splitext(a.video)[0] + '.words.json'
    if not os.path.exists(words):
        sys.exit(f'no transcript yet: source.py transcribe {a.video}')
    r = locate(words, a.text)
    if not r:
        sys.exit('nothing to match')
    t0, t1, score = r
    print(json.dumps({'src': a.video, 'in': round(t0, 2), 'out': round(t1, 2), 'match': round(score, 2)}, ensure_ascii=False))
    if score < .6:
        print('  weak match: check the transcript, the sentence may be paraphrased or not in this video', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('fetch'); p.add_argument('url'); p.add_argument('--name', required=True)
    p = sub.add_parser('transcribe'); p.add_argument('video'); p.add_argument('--lang', default='zh')
    p = sub.add_parser('find'); p.add_argument('video'); p.add_argument('text')
    a = ap.parse_args()
    {'fetch': fetch, 'transcribe': transcribe, 'find': find}[a.cmd](a)


if __name__ == '__main__':
    main()
