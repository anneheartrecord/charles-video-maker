#!/usr/bin/env python3
"""用本地 Antigravity CLI（agy，走你自己的 Google 账号）生成一张剧照。

  agy_image.py "Cinematic film still, ..." source/plate_hook.png [--aspect 16:9] [--retries 3]

agy 原生出图约 1376x768（16:9），脚本按 --aspect 放大到 1920x1080 / 1080x1440 等，保留原图为 *.raw.png。
全机最多同时 5 个 agy 出图（文件锁），多个子任务并行也不会互相挤爆。agy 不读系统代理，需要时用环境变量 GEMINI_PROXY
指定（和 gemini_copy.py 同一个变量，默认 http://127.0.0.1:7890）。画质与 gpt-image-2 相当。
Google 账号的出图额度按时间窗重置（实测一个窗口约二三十张）：碰到 QUOTA_EXHAUSTED 不算重试次数，
按 agy 报的重置时间睡到点再出（最多等 6 小时），全机共用一个 ~/.cache/agy_image/quota_until 标记，别的进程看到也一起等。
"""
import argparse, datetime, fcntl, glob, os, re, shutil, subprocess, sys, tempfile, time

AGY = os.path.expanduser('~/.local/bin/agy')
LOCKDIR = os.path.expanduser('~/.cache/agy_image'); os.makedirs(LOCKDIR, exist_ok=True)
SIZES = {'16:9': (1920, 1080), '3:4': (1080, 1440), '9:16': (1080, 1920), '1:1': (1440, 1440), '4:3': (1440, 1080)}
RULES = ' No text, letters, numbers, captions or watermarks anywhere in the image. No brand logos. Hands and fingers anatomically correct.'


QUOTA = f'{LOCKDIR}/quota_until'


def wait_quota():
    try:
        until = float(open(QUOTA).read())
    except Exception:
        return
    if until > time.time():
        print(f'quota exhausted, sleeping until {time.strftime("%H:%M", time.localtime(until))}', file=sys.stderr)
        time.sleep(until - time.time() + 30)


def mark_quota(text):
    m = re.search(r'(\d{1,2}):(\d{2})\s*(?:Beijing|北京|CST|\))', text) or re.search(r'around (\d{1,2}):(\d{2})', text)
    now = datetime.datetime.now()
    if m:
        t = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0)
        if t < now: t += datetime.timedelta(days=1)
    else:
        t = now + datetime.timedelta(minutes=30)
    t = min(t, now + datetime.timedelta(hours=6))
    open(QUOTA, 'w').write(str(t.timestamp()))


def slot():
    while True:
        for i in range(5):
            f = open(f'{LOCKDIR}/slot{i}', 'w')
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB); return f
            except BlockingIOError:
                f.close()
        time.sleep(3)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('prompt'); ap.add_argument('out')
    ap.add_argument('--aspect', default='16:9', choices=list(SIZES)); ap.add_argument('--retries', type=int, default=3)
    a = ap.parse_args()
    out = os.path.abspath(a.out); os.makedirs(os.path.dirname(out), exist_ok=True)
    px = os.environ.get('GEMINI_PROXY', 'http://127.0.0.1:7890')
    env = dict(os.environ, https_proxy=px, http_proxy=px)
    k = 0
    while k < a.retries:
        wait_quota()
        lock = slot()
        tmp = tempfile.mkdtemp(prefix='agyimg-')
        try:
            ask = (f'Use your image generation tool to create exactly one image, aspect ratio {a.aspect}: {a.prompt}{RULES} '
                   f'Save it into the current directory as img.png. Do not write code. Then print the absolute path.')
            r = subprocess.run([AGY, '-p', ask, '--dangerously-skip-permissions', '--print-timeout', '300s'],
                               cwd=tmp, env=env, capture_output=True, text=True, timeout=360)
            got = [p for p in glob.glob(f'{tmp}/**/*.png', recursive=True) + glob.glob(f'{tmp}/**/*.jp*g', recursive=True)]
            if got:
                raw = out[:-4] + '.raw.png'
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', got[0], raw], check=True)
                w, h = SIZES[a.aspect]
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-vf',
                                f'scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}', out], check=True)
                print(f'{out}: {w}x{h} (try {k + 1})'); return
            if re.search(r'QUOTA_EXHAUSTED|RESOURCE_EXHAUSTED|429', r.stdout + r.stderr):
                mark_quota(r.stdout + r.stderr); print('quota exhausted', file=sys.stderr); continue
            k += 1
            print(f'try {k}: no image | ' + ' '.join((r.stdout + r.stderr).split())[-300:], file=sys.stderr)
        except subprocess.TimeoutExpired:
            k += 1
            print(f'try {k}: timeout', file=sys.stderr)
        finally:
            lock.close(); shutil.rmtree(tmp, ignore_errors=True)
        time.sleep(5)
    sys.exit('agy_image: failed')


if __name__ == '__main__':
    main()
