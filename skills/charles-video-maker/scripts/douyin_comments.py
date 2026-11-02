#!/usr/bin/env python3
"""用登录态逐条打开 www.douyin.com/video/<id>，页面自己会请求评论和详情，原样截获存盘。
用法：douyin_comments.py <输出目录> <aweme_id> [...]
"""
import json, os, sys, time
from playwright.sync_api import sync_playwright

PROFILE = os.path.expanduser('~/.config/douyin/douyin-pw-profile')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36')
out, ids = sys.argv[1], sys.argv[2:]
os.makedirs(out, exist_ok=True)
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(PROFILE, headless=True, viewport={'width': 1400, 'height': 900},
                                               locale='zh-CN', user_agent=UA)
    for aid in ids:
        got = {'comments': [], 'detail': None}
        def on(r):
            try:
                u = r.url
                if 'comment/list' in u and 'reply' not in u:
                    got['comments'] += [{'text': c.get('text'), 'digg': c.get('digg_count'),
                                         'reply': c.get('reply_comment_total'), 'ip': c.get('ip_label')}
                                        for c in (r.json().get('comments') or [])]
                elif 'aweme/detail' in u:
                    got['detail'] = r.json().get('aweme_detail')
            except Exception:
                pass
        pg = ctx.new_page(); pg.on('response', on)
        pg.goto(f'https://www.douyin.com/video/{aid}', timeout=60000); time.sleep(10)
        for _ in range(4):
            pg.mouse.move(1150, 500); pg.mouse.wheel(0, 2500); time.sleep(2)
        pg.screenshot(path=f'{out}/{aid}.png')
        json.dump(got, open(f'{out}/{aid}.json', 'w'), ensure_ascii=False, indent=1)
        d = got['detail'] or {}
        print(aid, len(got['comments']), (d.get('desc') or '')[:30], (d.get('mix_info') or {}).get('mix_name'))
        pg.close()
    ctx.close()
