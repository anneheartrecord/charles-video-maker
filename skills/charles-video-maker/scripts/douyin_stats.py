#!/usr/bin/env python3
"""分页拉作品列表（含 metrics：完播率、2 秒跳出、5 秒完播、平均观看时长等）。用法：douyin_stats.py <输出 json>"""
import json, os, sys, time
from playwright.sync_api import sync_playwright

PROFILE = os.path.expanduser('~/.config/douyin/douyin-pw-profile')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36')
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(PROFILE, headless=True, locale='zh-CN', user_agent=UA)
    pg = ctx.new_page(); pg.goto('https://creator.douyin.com/creator-micro/content/manage', timeout=60000); time.sleep(5)
    rows, cur = [], 0
    for _ in range(10):
        j = ctx.request.get('https://creator.douyin.com/janus/douyin/creator/pc/work_list',
                            params={'status': 0, 'count': 12, 'max_cursor': cur, 'scene': 'star_atlas',
                                    'device_platform': 'android', 'aid': 1128}).json()
        for it in j.get('items') or []:
            rows.append(it)
        if not j.get('has_more'):
            break
        cur = j['max_cursor']
    json.dump(rows, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
    print('items', len(rows))
    ctx.close()
