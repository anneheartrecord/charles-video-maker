#!/usr/bin/env python3
"""抖音话题雷达：抓 #话题 下的视频数据 → 排名 → 按需下载无水印原片。

  python3 douyin_radar.py crawl  [--tag Vibe知识大赏] [--out DIR]   # 弹出 Chrome，出滑块就拖一下
  python3 douyin_radar.py rank   --out DIR                          # 总点赞榜 + 72 小时内每小时点赞榜
  python3 douyin_radar.py get    --out DIR <aweme_id> [name] ...    # 下载原片到 DIR/refs/（签名地址几小时内有效）

cookie：优先用环境变量 DOUYIN_COOKIES 指的文件（默认 ~/.config/douyin/cookies.txt，600 权限，只含抖音域名）；校验登录失效时自动从本机 Chrome 重新导出
并覆盖保存（必须带 sessionid 才算导出成功）。也可单独跑 `douyin_radar.py login` 只刷新并校验。
"""
import argparse, json, os, re, subprocess, sys, time, urllib.parse
from playwright.sync_api import sync_playwright
TAG = 'Vibe知识大赏'
import json, sys, time, re, urllib.parse
from playwright.sync_api import sync_playwright

def load(path):
    out = []
    for l in open(path):
        if l.startswith('#HttpOnly_'): l = l[len('#HttpOnly_'):]
        elif l.startswith('#') or not l.strip(): continue
        p = l.rstrip('\n').split('\t')
        if len(p) < 7: continue
        out.append({'name': p[5], 'value': p[6], 'domain': p[0], 'path': p[2], 'secure': p[3] == 'TRUE',
                    'expires': int(float(p[4])) if p[4] not in ('0', '') and 0 < float(p[4]) < 4e9 else -1})
    return out

aw, src, hid = {}, {}, {}
def grab(obj, tag):
    if isinstance(obj, dict):
        if 'aweme_id' in obj and 'statistics' in obj and 'desc' in obj:
            aw[obj['aweme_id']] = obj; src.setdefault(obj['aweme_id'], set()).add(tag)
            for t in obj.get('text_extra') or []:
                if t.get('hashtag_name') == TAG and t.get('hashtag_id'): hid['id'] = t['hashtag_id']
            for c in obj.get('cha_list') or []:
                if c.get('cha_name') == TAG: hid['id'] = c.get('cid')
        for v in obj.values(): grab(v, tag)
    elif isinstance(obj, list):
        for v in obj: grab(v, tag)

stage = {'name': 'search'}
def on(r):
    if '/aweme/v1/web/' not in r.url or 'favorite' in r.url or 'collect' in r.url: return
    try: j = r.json()
    except Exception: return
    path = r.url.split('?')[0].split('/aweme/v1/web/')[1]
    grab(j, f"{stage['name']}:{path}")

def scroll(page, n, label):
    last = -1
    for i in range(n):
        page.mouse.wheel(0, 4000); time.sleep(2.5)
        if i % 5 == 4:
            print(f'{label} scroll {i+1}: {len(aw)} videos', flush=True)
            if len(aw) == last: break
            last = len(aw)


COOKIE = os.path.expanduser(os.environ.get('DOUYIN_COOKIES', '~/.config/douyin/cookies.txt'))

def export_cookies(tries=3):
    """Chrome -> COOKIE (douyin domains only). The Chrome export is flaky (sometimes returns ~20 cookies, no sessionid): retry."""
    os.makedirs(os.path.dirname(COOKIE), mode=0o700, exist_ok=True)
    tmp = COOKIE + '.all'
    for k in range(tries):
        subprocess.run(['yt-dlp', '--cookies-from-browser', 'chrome', '--cookies', tmp, '--skip-download', 'https://www.douyin.com/'],
                       capture_output=True)
        lines = open(tmp).read().splitlines() if os.path.exists(tmp) else []
        if os.path.exists(tmp): os.remove(tmp)
        keep = [l for l in lines if re.search(r'douyin\.com|amemv|bytedance|snssdk|zijieapi', l)]
        if any(l.split('\t')[5:6] == ['sessionid'] for l in keep if l.count('\t') >= 6):
            fd = os.open(COOKIE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w') as f: f.write('# Netscape HTTP Cookie File\n' + '\n'.join(keep) + '\n')
            print(f'cookies exported from Chrome: {len(keep)}', flush=True); return True
        print(f'Chrome export #{k + 1} had no sessionid ({len(keep)} douyin cookies), retrying', flush=True); time.sleep(3)
    return False

def whoami(ctx):
    """logged-in nickname via creator center, or None"""
    try:
        j = ctx.request.get('https://creator.douyin.com/web/api/media/user/info/', timeout=20000).json()
        u = j.get('user') or {}
        return u.get('nickname')
    except Exception: return None

PROFILE = os.path.expanduser(os.environ.get('DOUYIN_PROFILE', '~/.config/douyin/pw-profile'))   # dedicated browser profile: logs in once, stays logged in

def save_cookies(ctx):
    rows = ['# Netscape HTTP Cookie File']
    for c in ctx.cookies():
        if not re.search(r'douyin\.com|amemv|bytedance|snssdk|zijieapi', c['domain']): continue
        rows.append('\t'.join([c['domain'], 'TRUE' if c['domain'].startswith('.') else 'FALSE', c['path'], 'TRUE' if c['secure'] else 'FALSE',
                               str(int(c['expires'])) if c['expires'] > 0 else '0', c['name'], c['value']]))
    os.makedirs(os.path.dirname(COOKIE), mode=0o700, exist_ok=True)
    fd = os.open(COOKIE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f: f.write('\n'.join(rows) + '\n')

def login(ctx, page=None, wait_scan=300):
    """already logged in (profile) -> saved cookie file -> fresh Chrome export -> QR scan in this window. Saves cookies on success."""
    steps = [('profile', None), ('saved cookies', lambda: os.path.exists(COOKIE)), ('Chrome export', export_cookies)]
    for label, prep in steps:
        if prep is not None:
            if not prep(): continue
            ctx.add_cookies(load(COOKIE))
        name = whoami(ctx)
        if name:
            print(f'logged in as {name} (via {label})', flush=True); save_cookies(ctx); return name
        print(f'{label}: not logged in', flush=True)
    if page is not None and wait_scan:
        ctx.clear_cookies()
        page.goto('https://creator.douyin.com/', timeout=60000)
        print(f'>>> 请在弹出的浏览器窗口里用抖音 App 扫码登录（{wait_scan // 60} 分钟内），登录一次之后会一直保存', flush=True)
        t0 = time.time()
        while time.time() - t0 < wait_scan:
            time.sleep(4); name = whoami(ctx)
            if name: print(f'logged in as {name} (via QR scan)', flush=True); save_cookies(ctx); return name
    if ANON: print('continuing without login (--anon)', flush=True); return None
    sys.exit('not logged in')

def crawl(D):
    if True:
        with sync_playwright() as p:
            os.makedirs(PROFILE, mode=0o700, exist_ok=True)
            ctx = p.chromium.launch_persistent_context(PROFILE,
                headless=HEADLESS, viewport={'width': 1400, 'height': 900}, locale='zh-CN',
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36')
            page = ctx.new_page(); login(ctx, page, 0 if HEADLESS else 300); page.on('response', on)
            page.goto('https://www.douyin.com/search/' + urllib.parse.quote(TAG) + f'?type=video&sort_type={SORT}&publish_time={DAYS}', timeout=60000)
            # wait for captcha if any (user drags slider), up to 8 min
            t0 = time.time()
            while not aw and time.time() - t0 < 300: time.sleep(3)
            print('search first batch:', len(aw), 'hashtag id:', hid.get('id'), flush=True)
            scroll(page, 30, 'search')
            if hid.get('id') and HASHTAG:
                for name in ['hashtag']:
                    stage['name'] = name
                    page.goto(f"https://www.douyin.com/hashtag/{hid['id']}", timeout=60000); time.sleep(6)
                    scroll(page, 40, name)
                    # try switching to 最新 tab if exists
                    for label in ['最新', '最新发布']:
                        try:
                            page.get_by_text(label, exact=True).first.click(timeout=3000); stage['name'] = 'hashtag-latest'
                            time.sleep(5); scroll(page, 40, 'latest'); break
                        except Exception: pass

            json.dump({'hashtag_id': hid.get('id'), 'awemes': list(aw.values()), 'src': {k: sorted(v) for k, v in src.items()}},
                      open(f'{D}/{NAMES[0]}.json', 'w'), ensure_ascii=False)
            print('done', len(aw), flush=True); ctx.close()

def rank(D):
    d = {'awemes': [a for n in NAMES for a in json.load(open(f'{D}/{n}.json'))['awemes']]}; now = time.time(); T = []; seen = set()
    for a in d['awemes']:
        if a['aweme_id'] in seen: continue
        seen.add(a['aweme_id'])
        tags = [t.get('hashtag_name') for t in a.get('text_extra') or []]
        if TAG not in a.get('desc', '') and TAG not in tags: continue
        s = a['statistics']
        T.append(dict(id=a['aweme_id'], h=(now - a.get('create_time', now)) / 3600, like=s.get('digg_count', 0),
                      sh=s.get('share_count', 0), col=s.get('collect_count', 0), cm=s.get('comment_count', 0),
                      fans=a.get('author', {}).get('follower_count', 0), au=a.get('author', {}).get('nickname', ''),
                      dur=(a.get('video') or {}).get('duration', 0) / 1000, desc=a.get('desc', '').replace('\n', ' ')))
    def show(L):
        for r in L[:25]:
            print(f"{r['like']:>7}赞 {r['sh']:>6}转 {r['col']:>6}藏 {r['cm']:>5}评 | {r['h']:6.1f}h | 粉{r['fans']:>7} | {int(r['dur'])}s | {r['id']} | {r['au'][:8]} | {r['desc'][:50]}")
    print(f'带 #{TAG} 的 {len(T)} 条\n== 总点赞 =='); show(sorted(T, key=lambda r: -r['like']))
    print('\n== 72 小时内每小时点赞 =='); show(sorted([r for r in T if r['h'] <= 72], key=lambda r: -r['like'] / max(r['h'], 1)))

def get(D, args):
    d = {a['aweme_id']: a for n in NAMES for a in json.load(open(f'{D}/{n}.json'))['awemes']}; os.makedirs(f'{D}/refs', exist_ok=True)
    pairs = [(args[i], args[i + 1] if i + 1 < len(args) and not args[i + 1].isdigit() else '') for i in range(len(args)) if args[i].isdigit()]
    for aid, name in pairs:
        if aid not in d: print('NOT IN DATA', aid, flush=True); continue
        v = d[aid]['video']; urls = []
        for br in sorted(v.get('bit_rate') or [], key=lambda b: -b.get('bit_rate', 0)): urls += (br.get('play_addr') or {}).get('url_list', [])
        urls += (v.get('play_addr') or {}).get('url_list', [])
        out = f"{D}/refs/{name + '-' if name else ''}{aid}.mp4"
        for u in urls:
            subprocess.run(['curl', '-sL', '--max-time', '180', '-o', out, '-H', 'Referer: https://www.douyin.com/', '-A', 'Mozilla/5.0', u])
            if subprocess.run(['ffprobe', '-v', 'error', out], capture_output=True).returncode == 0: print('OK', out); break
        else: print('FAIL', aid)

def fetch(D, args):
    """open each video page in the logged-in profile, grab its fresh play URL from the page's own API responses, download"""
    pairs = [(args[i], args[i + 1] if i + 1 < len(args) and not args[i + 1].isdigit() else '') for i in range(len(args)) if args[i].isdigit()]
    os.makedirs(f'{D}/refs', exist_ok=True); os.makedirs(PROFILE, mode=0o700, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, headless=HEADLESS, viewport={'width': 1400, 'height': 900}, locale='zh-CN',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36')
        page = ctx.new_page(); login(ctx, page, 0 if HEADLESS else 300); page.on('response', on)
        for aid, name in pairs:
            page.goto(f'https://www.douyin.com/video/{aid}', timeout=60000)
            for _ in range(20):
                if aid in aw: break
                time.sleep(1)
            urls = []
            if aid in aw:
                v = aw[aid]['video']
                for br in sorted(v.get('bit_rate') or [], key=lambda b: -b.get('bit_rate', 0)): urls += (br.get('play_addr') or {}).get('url_list', [])
                urls += (v.get('play_addr') or {}).get('url_list', [])
            else:   # web now server-renders the detail into <script id="RENDER_DATA"> (url-encoded JSON, camelCase keys)
                m = re.search(r'<script id="RENDER_DATA"[^>]*>(.*?)</script>', page.content(), re.S)
                if m:
                    data = json.loads(urllib.parse.unquote(m.group(1)))
                    def walk(o):
                        if isinstance(o, dict):
                            if o.get('awemeId') == aid and isinstance(o.get('video'), dict): return o
                            for x in o.values():
                                r = walk(x)
                                if r: return r
                        elif isinstance(o, list):
                            for x in o:
                                r = walk(x)
                                if r: return r
                    det = walk(data)
                    if det:
                        v = det['video']
                        for br in sorted(v.get('bitRateList') or [], key=lambda b: -(b.get('bitRate') or 0)):
                            urls += [('https:' + a['src']) if a.get('src', '').startswith('//') else a.get('src', '') for a in br.get('playAddr') or []]
                        urls += [('https:' + a['src']) if a.get('src', '').startswith('//') else a.get('src', '') for a in v.get('playAddr') or []]
                        aw[aid] = det
            if not urls: print('NO DETAIL', aid, flush=True); continue
            out = f"{D}/refs/{name + '-' if name else ''}{aid}.mp4"
            for u in urls:
                subprocess.run(['curl', '-sL', '--max-time', '180', '-o', out, '-H', 'Referer: https://www.douyin.com/', '-A', 'Mozilla/5.0', u])
                if subprocess.run(['ffprobe', '-v', 'error', out], capture_output=True).returncode == 0: print('OK', out, flush=True); break
            else: print('FAIL', aid, flush=True)
            json.dump(aw[aid], open(out[:-4] + '.json', 'w'), ensure_ascii=False)
        ctx.close()

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['crawl', 'rank', 'get', 'login', 'fetch']); ap.add_argument('ids', nargs='*')
    ap.add_argument('--tag', default=TAG); ap.add_argument('--sort', default='0', help='0 综合 / 1 最多点赞 / 2 最新发布'); ap.add_argument('--days', default='0', help='0 不限 / 1 一天内 / 7 一周内 / 180 半年内'); ap.add_argument('--hashtag', action='store_true', help='also scroll the hashtag page'); ap.add_argument('--name', default='raw', help='output json name'); ap.add_argument('--anon', action='store_true', help='continue even if not logged in'); ap.add_argument('--headless', action='store_true'); ap.add_argument('--out', default=time.strftime(os.path.expanduser('~/Desktop/video/vibe-video/_refs/%Y-%m-%d')))
    a = ap.parse_args(); TAG, SORT, DAYS, HASHTAG, NAME = a.tag, a.sort, a.days, a.hashtag, a.name; NAMES = [n for n in a.name.split(',')]; ANON, HEADLESS = a.anon, a.headless; os.makedirs(a.out, exist_ok=True)
    def do_login():
        os.makedirs(PROFILE, mode=0o700, exist_ok=True)
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(PROFILE, headless=HEADLESS, locale='zh-CN')
            login(ctx, ctx.new_page(), 0 if HEADLESS else 300); ctx.close()
    {'crawl': lambda: crawl(a.out), 'rank': lambda: rank(a.out), 'get': lambda: get(a.out, a.ids), 'login': do_login, 'fetch': lambda: fetch(a.out, a.ids)}[a.cmd]()
