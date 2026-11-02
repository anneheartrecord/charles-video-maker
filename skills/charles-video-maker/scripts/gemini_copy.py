#!/usr/bin/env python3
"""Video copy (narration lines, title, description, tags) written by the local Gemini (Antigravity CLI `agy`), checked here.

  gemini_copy.py gen   copy/brief.json copy/copy.json [--feedback copy/feedback.txt] [--model gemini-3.8-flash-high]
  gemini_copy.py check copy/brief.json copy/copy.json        # exit 1 when a hard rule fails; prints every problem

Brief format and the writing rules: references/gemini-copy.md (the prompt is read from that file).
agy needs the proxy in env (it ignores the macOS system proxy); set GEMINI_PROXY to override http://127.0.0.1:7890.
"""
import argparse, json, os, re, signal, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, '..', 'references', 'gemini-copy.md')
AGY = os.environ.get('AGY_BIN', os.path.expanduser('~/.local/bin/agy'))
CPS = 4.5   # default chars/sec: edge-tts at +0% reads ~4.7–5.2; the 1.25x voiceover pipeline reads ~6.7 -> set "cps": 6.5 in the brief


def prompt_template():
    s = open(REF, encoding='utf-8').read()
    m = re.search(r'## 给 Gemini 的提示词.*?```\n(.*?)```', s, re.S)
    if not m: sys.exit(f'prompt block not found in {REF}')
    return m.group(1).strip()


def call_agy(prompt, model, timeout=300):
    px = os.environ.get('GEMINI_PROXY', 'http://127.0.0.1:7890')
    env = {**os.environ, 'http_proxy': px, 'https_proxy': px, 'HTTP_PROXY': px, 'HTTPS_PROXY': px,
           'all_proxy': '', 'ALL_PROXY': '', 'no_proxy': 'localhost,127.0.0.1,::1', 'NO_PROXY': 'localhost,127.0.0.1,::1'}
    # agy sometimes prints the whole answer and then never exits (2026-10-25: hung 17 min past subprocess.run's timeout,
    # whose pipes a grandchild kept open). Stream to a file, stop as soon as a complete JSON object is there,
    # and kill the whole process group.
    with tempfile.TemporaryDirectory() as cwd:   # empty workspace: the agent has nothing to read or edit
        raw = os.path.join(cwd, '.agy-out.txt')
        with open(raw, 'w') as f:
            pr = subprocess.Popen([AGY, '-p', prompt, '--model', model, '--disable-slash-commands', '--print-timeout', f'{timeout}s'],
                                  cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        t0, res, out = time.time(), None, ''
        while time.time() - t0 < timeout + 60:
            time.sleep(3)
            out = open(raw, encoding='utf-8', errors='replace').read()
            i, j = out.find('{'), out.rfind('}')
            if i >= 0 and j > i:
                try:
                    res = json.loads(out[i:j + 1])
                except ValueError:
                    res = None
                if isinstance(res, dict) and 'lines' in res and 'tags' in res:
                    break
                res = None
            if pr.poll() is not None:
                break
        if pr.poll() is None:
            try:
                os.killpg(pr.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            pr.wait()
    if res is not None:
        return res
    if pr.returncode not in (0, None, -signal.SIGKILL): sys.exit(f'agy failed ({pr.returncode}): {out.strip()[-800:]}')
    i, j = out.find('{'), out.rfind('}')
    if i < 0 or j < i: raise ValueError('no JSON object in Gemini output:\n' + out[-1500:])
    return json.loads(out[i:j + 1])


def cmd_gen(a):
    brief = json.load(open(a.brief, encoding='utf-8'))
    cps = brief.get('cps', CPS)
    p = prompt_template().replace('每秒 4.5 个字', f'每秒 {cps:g} 个字') + '\n\n任务单：\n' + json.dumps(brief, ensure_ascii=False, indent=1)
    if a.feedback:
        p += '\n\n上一版的问题（逐条改掉，其余保持你的说法）：\n' + open(a.feedback, encoding='utf-8').read()
        if os.path.exists(a.out): p += '\n\n上一版：\n' + open(a.out, encoding='utf-8').read()
    for attempt in range(2):
        try:
            res = call_agy(p, a.model); break
        except (ValueError, subprocess.TimeoutExpired) as e:   # JSONDecodeError is a ValueError
            print(f'retrying: {str(e)[:300]}', file=sys.stderr)
            if attempt: sys.exit(f'Gemini output unusable twice: {e}')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for l in res.get('lines', []): print(l.get('id'), l.get('text'))
    print('\n' + res.get('title', '')); print(res.get('description', '')); print(' '.join(res.get('tags', [])))


# ---------- checks ----------
CN = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
UNIT = {'十': 10, '百': 100, '千': 1000, '万': 10000}


def cn2int(s):
    total, sec, num = 0, 0, 0
    for ch in s:
        if ch in CN: num = CN[ch]
        elif ch == '万': total += (sec + num) * 10000; sec = num = 0
        else: sec += (num or 1) * UNIT[ch]; num = 0
    return total + sec + num


def numbers(text):
    """arabic numbers, plus Chinese numerals that contain a unit (七十二, 一千三百) — bare 一/两 are words, not numbers"""
    out = {float(x) for x in re.findall(r'\d+(?:\.\d+)?', text.replace(',', ''))}
    for run in re.findall(r'[零〇一二两三四五六七八九十百千万]+', text):
        if any(u in run for u in UNIT): out.add(float(cn2int(run)))
    return out


def speak_len(s):
    return len(re.sub(r'[\s，。：；！？、「」『』（）《》“”‘’—…·,.:;!?()\-"\']', '', s))


def cmd_check(a):
    brief = json.load(open(a.brief, encoding='utf-8')); cp = json.load(open(a.copy, encoding='utf-8'))
    probs = []
    facts = set().union(*[numbers(f['text']) for f in brief.get('facts', [])]) if brief.get('facts') else set()
    keep = brief.get('keep_terms', [])
    got = {l['id']: l['text'] for l in cp.get('lines', [])}
    for sl in brief.get('slots', []):
        t = got.get(sl['id'])
        if t is None: probs.append(f"{sl['id']}：缺这一句"); continue
        n, cap = speak_len(t), int(sl['max_sec'] * brief.get('cps', CPS))
        if n > cap: probs.append(f"{sl['id']}：{n} 字，超过 {sl['max_sec']} 秒能念完的 {cap} 字 —— {t}")
        for x in numbers(t) - facts: probs.append(f"{sl['id']}：数字 {x:g} 不在事实清单里 —— {t}")
    for x in [k for k in got if k not in {s['id'] for s in brief.get('slots', [])}]: probs.append(f'{x}：任务单里没有这个 slot')
    for k in keep:
        if not any(k in t for t in got.values()): probs.append(f'必须出现的词没出现：{k}')
    every = list(got.items()) + [('标题', cp.get('title', '')), ('简介', cp.get('description', ''))]
    for i, t in every:
        if re.search(r'[一-鿿][,.:;!?()]|[,.:;!?()][一-鿿]', t): probs.append(f'{i}：有半角标点 —— {t}')
        for q in re.findall(r'[「“"]([^」”"]+)[」”"]', t):
            if q not in keep and not any(q in f['text'] for f in brief.get('facts', [])): probs.append(f'{i}：用引号强调普通词语「{q}」')
    title = cp.get('title', '')
    if len(title.replace(' ', '')) > 20: probs.append(f'标题 {len(title)} 字，超过 20 字 —— {title}')
    tags = cp.get('tags', [])
    if len(tags) != 5 or not all(x.startswith('#') for x in tags): probs.append(f'tags 要正好 5 个且都以 # 开头 —— {tags}')
    if brief.get('platform') == 'douyin' and (not tags or tags[0] != '#Vibe知识大赏'): probs.append('抖音 tags 第一个要是 #Vibe知识大赏')
    for p in probs: print('✗', p)
    print('通过' if not probs else f'{len(probs)} 个问题；把它们写进 feedback.txt 再 gen --feedback')
    sys.exit(1 if probs else 0)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'selftest':
        assert cn2int('七十二') == 72 and cn2int('一千三百') == 1300 and cn2int('十') == 10 and cn2int('一万二千') == 12000
        assert numbers('一只杯子，要经过七十二双手') == {72.0} and numbers('烧到 1300 度') == {1300.0}
        assert speak_len('把泥土，烧成玉。') == 6
        print('ok'); sys.exit()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('gen'); g.add_argument('brief'); g.add_argument('out'); g.add_argument('--feedback'); g.add_argument('--model', default='gemini-3.8-flash-high')
    c = sp.add_parser('check'); c.add_argument('brief'); c.add_argument('copy')
    a = ap.parse_args()
    {'gen': cmd_gen, 'check': cmd_check}[a.cmd](a)
