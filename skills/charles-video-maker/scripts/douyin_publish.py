#!/usr/bin/env python3
"""抖音创作者中心：上传一条成片，填标题/简介/tags/封面，定时或立即发布。

用法：
  douyin_publish.py <slug> "2026-10-25 08:00"   # 定时（须在 2 小时后、14 天内）
  douyin_publish.py <slug> now                  # 立即发布
  加 --dry 只填表核对，不点发布。

登录态：专用持久化浏览器配置，路径取环境变量 DOUYIN_PROFILE（默认 ~/.config/douyin/pw-profile，扫码登录过一次）。
工程目录取环境变量 DOUYIN_WORKDIR（默认 ~/Desktop/video/vibe-video），<slug> 是其中的子目录。
环境变量 DOUYIN_NICKNAME 设了就核对登录的是不是这个账号，不对就退出。
不要再从 Chrome 搬 cookie——10-22 搬过几次后服务端把会话踢下线了。
发布前逐项核对（标题、时间、公开、tags、封面检测），任一不对就退出，不点发布。
"""
import glob, os, sys, time
from playwright.sync_api import sync_playwright

ROOT = os.path.expanduser(os.environ.get('DOUYIN_WORKDIR', '~/Desktop/video/vibe-video'))
PROFILE = os.path.expanduser(os.environ.get('DOUYIN_PROFILE', '~/.config/douyin/pw-profile'))
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36')


def shot(pg, path, **k):
    try:
        pg.screenshot(path=path, timeout=10000, **k)
    except Exception:
        pass


def upload_cover(pg, path):
    # 封面弹窗里有好几个隐藏的上传框，位置随页面状态变（2026-10-24 按位置找会传错，抖音退回视频截帧、判成截屏封面）；
    # 点当前可见的上传封面按钮，用文件选择器传
    with pg.expect_file_chooser(timeout=20000) as fc:
        pg.get_by_text('上传封面', exact=True).last.click(force=True)
    fc.value.set_files(path)
    time.sleep(6)


def stop(pg, out, msg):
    shot(pg, f'{out}/发布失败.png', full_page=True)
    print('STOP', msg)
    sys.exit(2)


def main():
    args = [a for a in sys.argv[1:] if a != '--dry']
    dry = '--dry' in sys.argv
    slug, when = args[0], args[1]
    out = f'{ROOT}/{slug}/out'
    video = [v for v in glob.glob(f'{out}/*.mp4') if '预览版' not in os.path.basename(v)][0]
    c34 = glob.glob(f'{out}/*-封面.png')[0]
    c43 = f'{out}/横封面-4x3.png'
    title, desc, tags = open(f'{out}/publish.txt').read().strip().split('\n\n')[:3]
    tags = tags.split()
    print(slug, when, os.path.basename(video), tags)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=False, viewport={'width': 1400, 'height': 900},
            locale='zh-CN', user_agent=UA)
        pg = ctx.new_page()
        nick = ctx.request.get('https://creator.douyin.com/web/api/media/user/info/').json() \
            .get('user', {}).get('nickname')
        want = os.environ.get('DOUYIN_NICKNAME')  # 设了就核对是不是这个号，防止发错号
        if not nick or (want and nick != want):
            stop(pg, out, f'未登录或不是目标账号（{nick}）')

        pg.goto('https://creator.douyin.com/creator-micro/content/upload', timeout=180000, wait_until='domcontentloaded')
        pg.locator('input[type=file]').first.set_input_files(video)
        pg.get_by_placeholder('填写作品标题，为作品获得更多流量').wait_for(timeout=120000)
        time.sleep(2)
        for _ in range(2):
            b = pg.get_by_text('我知道了')
            if b.count():
                b.first.click(); time.sleep(0.5)

        pg.get_by_placeholder('填写作品标题，为作品获得更多流量').fill(title)
        ed = pg.locator('[contenteditable=true]').first
        ed.click(); pg.keyboard.type(desc, delay=5)
        for tg in tags:
            pg.keyboard.type(' ' + tg, delay=30); time.sleep(1.6); pg.keyboard.press('Enter')
        time.sleep(1)

        pg.get_by_text('选择封面').nth(1).wait_for(timeout=300000)  # 视频还在处理时封面入口要过一会儿才出现
        pg.get_by_text('选择封面').nth(1).click(); time.sleep(3)
        upload_cover(pg, c34)
        pg.get_by_role('button', name='设置横封面').click(); time.sleep(3)
        upload_cover(pg, c43)
        done = pg.get_by_role('button', name='完成')
        for _ in range(60):
            if done.is_enabled():
                break
            time.sleep(1)
        done.click(); time.sleep(4)

        if when != 'now':
            pg.locator('label:has-text("定时发布")').first.click(); time.sleep(1)
            box = pg.get_by_placeholder('日期和时间')
            box.click(); pg.keyboard.press('Meta+a'); pg.keyboard.type(when, delay=40)
            pg.keyboard.press('Enter'); time.sleep(0.5)
            pg.get_by_text('发布时间').first.click(); time.sleep(1)

        # ---- 发布前核对 ----
        got = pg.get_by_placeholder('填写作品标题，为作品获得更多流量').input_value()
        if got != title:
            stop(pg, out, f'标题不符：{got}')
        if when != 'now':
            got = pg.get_by_placeholder('日期和时间').input_value()
            if got != when:
                stop(pg, out, f'时间不符：{got}')
        if pg.locator('label:has-text("公开")').first.get_attribute('data-checked') != 'true':
            stop(pg, out, '不是公开')
        body = ed.inner_text()
        miss = [t for t in tags if t.lstrip('#') not in body]
        if miss:
            stop(pg, out, f'tags 缺失：{miss}')
        # 网速慢时视频没传完，封面检测要等上传结束才出结果；扁平图形封面会被判成截屏（封面不佳），出现就停
        for _ in range(600):
            ok = pg.get_by_text('封面效果检测通过').count() or pg.get_by_text('封面检测通过').count()
            if not pg.get_by_text('检测中').count() and (ok or pg.get_by_text('封面不佳').count()):
                break
            time.sleep(1)
        if pg.get_by_text('封面不佳').count() or not ok:
            stop(pg, out, '封面检测未通过')
        shot(pg, f'{out}/发布前核对.png', full_page=True)
        if dry:
            print('DRY OK'); ctx.close(); return

        pg.get_by_role('button', name='发布', exact=True).click()
        for _ in range(300):  # 视频没传完时点发布会一直等上传
            if pg.get_by_text('作品合集', exact=True).count() and not pg.get_by_placeholder('填写作品标题，为作品获得更多流量').count():  # 发布成功会跳到内容管理，网址不一定带 manage
                break
            time.sleep(1)
        else:
            stop(pg, out, '点发布后没跳到作品管理')
        time.sleep(4)
        shot(pg, f'{out}/发布后.png')
        print('PUBLISHED', slug, when)
        ctx.close()


if __name__ == '__main__':
    main()
