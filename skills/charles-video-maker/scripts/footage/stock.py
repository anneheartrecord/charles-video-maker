#!/usr/bin/env python3
"""Royalty-free b-roll from Pexels or Pixabay (both allow commercial use without attribution; we credit anyway).

  stock.py search "city night rain" --n 8                 # candidates + numbered contact sheet in source/stock/
  stock.py get pexels:123456                              # download the chosen clip -> source/footage/pexels-123456.mp4
  stock.py search "茶叶 采摘" --provider pixabay --orientation landscape

Keys (free): PEXELS_API_KEY from https://www.pexels.com/api/ , PIXABAY_API_KEY from https://pixabay.com/api/docs/ .
With both set, search asks both. Search in English for better results. Every download is logged in source/credits.md.
"""
import argparse, glob, json, os, re, subprocess, sys, urllib.parse, urllib.request

UA = {'User-Agent': 'charles-video-maker/1.0'}


def get_json(url, headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **(headers or {})}), timeout=60))


def download(url, path):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(path, 'wb') as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def pexels(q, n, orient):
    key = os.environ['PEXELS_API_KEY']
    d = get_json(f'https://api.pexels.com/videos/search?query={urllib.parse.quote(q)}&per_page={n}&orientation={orient}&size=medium',
                 {'Authorization': key})
    return [{'id': f"pexels:{v['id']}", 'page': v['url'], 'thumb': v['image'], 'duration': v['duration'],
             'author': v['user']['name'], 'license': 'Pexels License',
             'files': [{'w': f['width'], 'h': f['height'], 'url': f['link']} for f in v['video_files'] if f.get('width') and f['file_type'] == 'video/mp4']}
            for v in d.get('videos', [])]


def pixabay(q, n, orient):
    key = os.environ['PIXABAY_API_KEY']
    d = get_json(f'https://pixabay.com/api/videos/?key={key}&q={urllib.parse.quote(q)}&per_page={max(3, n)}&safesearch=true')
    out = []
    for v in d.get('hits', []):
        files = [{'w': f['width'], 'h': f['height'], 'url': f['url']} for f in v['videos'].values() if f.get('url')]
        if orient == 'portrait' and not any(f['h'] > f['w'] for f in files):
            continue                                   # Pixabay has no orientation filter for videos
        out.append({'id': f"pixabay:{v['id']}", 'page': v['pageURL'], 'thumb': v['videos'].get('medium', {}).get('thumbnail', ''),
                    'duration': v['duration'], 'author': v['user'], 'license': 'Pixabay Content License', 'files': files})
    return out[:n]


def search(a):
    provs = [p for p in (['pexels', 'pixabay'] if a.provider == 'all' else [a.provider]) if os.environ.get(f'{p.upper()}_API_KEY')]
    if not provs:
        sys.exit('no stock key: set PEXELS_API_KEY or PIXABAY_API_KEY (free, see the header of this script)')
    cands = []
    for p in provs:
        cands += {'pexels': pexels, 'pixabay': pixabay}[p](a.query, a.n, a.orientation)
    if not cands:
        sys.exit('nothing found; try other (English) words')
    slug = re.sub(r'\W+', '-', a.query.lower()).strip('-')[:40] or 'q'
    os.makedirs('source/stock', exist_ok=True)
    json.dump(cands, open(f'source/stock/{slug}.json', 'w'), ensure_ascii=False, indent=1)
    for i, c in enumerate(cands):
        print(f"{i + 1:2d}. {c['id']:<18} {c['duration']:>3}s  {max((f['w'], f['h']) for f in c['files'])}  {c['author']}  {c['page']}")
    # numbered contact sheet, drawn by the browser (no ffmpeg drawtext needed)
    cols = min(4, len(cands)); rows = -(-len(cands) // cols)
    cells = ''.join(f'<div><img src="{c["thumb"]}"><b>{i + 1}</b></div>' for i, c in enumerate(cands))
    page = f'source/stock/{slug}.html'
    open(page, 'w').write('<!doctype html><meta charset="utf-8"><style>body{margin:0;background:#111;display:grid;'
                          f'grid-template-columns:repeat({cols},360px)}}div{{position:relative;width:360px;height:640px;display:flex;align-items:center}}'
                          'img{width:100%;max-height:100%;object-fit:contain}b{position:absolute;left:10px;top:8px;font:700 44px sans-serif;color:#fff;'
                          f'background:#000a;padding:0 12px;border-radius:8px}}</style>{cells}<script>window.render=()=>{{}}</script>')
    render = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'render.py')
    subprocess.run(['python3', render, page, f'source/stock/{slug}.png', '--still', '0', '--size', f'{cols * 360}x{rows * 640}'], check=True, capture_output=True)
    print(f'contact sheet: source/stock/{slug}.png')


def get(a):
    c = None
    for f in sorted(glob.glob('source/stock/*.json')):
        c = next((c for c in json.load(open(f)) if c['id'] == a.id), None)
        if c: break
    if not c:
        sys.exit(f'{a.id} is not in any search result; run stock.py search first')
    W, H = map(int, a.size.split('x'))
    long_side = max(W, H)
    files = sorted(c['files'], key=lambda f: (max(f['w'], f['h']) < long_side, abs(max(f['w'], f['h']) - long_side)))   # smallest file that is big enough
    out = f"source/footage/{a.id.replace(':', '-')}.mp4"
    os.makedirs('source/footage', exist_ok=True)
    download(files[0]['url'], out)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from source import credit
    credit(f"- `{os.path.basename(out)}` · {c['page']} · {c['author']} · {c['license']} · 空镜")
    print(f"{out}: {files[0]['w']}x{files[0]['h']}, {c['duration']}s, {c['author']} ({c['license']})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('search'); p.add_argument('query'); p.add_argument('--n', type=int, default=8)
    p.add_argument('--provider', choices=['all', 'pexels', 'pixabay'], default='all')
    p.add_argument('--orientation', choices=['portrait', 'landscape', 'square'], default='portrait')
    p = sub.add_parser('get'); p.add_argument('id'); p.add_argument('--size', default='1080x1920', help='the film size, to pick a big-enough file')
    a = ap.parse_args()
    {'search': search, 'get': get}[a.cmd](a)


if __name__ == '__main__':
    main()
