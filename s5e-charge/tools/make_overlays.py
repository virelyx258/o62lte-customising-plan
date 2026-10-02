# -*- coding: utf-8 -*-
"""为官方 LuaDevTemplate 生成可编译的 overlay。两份盘：S5Chg（替换）/ S5ChgRestore（还原）。

要点（都是踩过的坑）：
  * Compiler.exe 的设备表里没有 480 档 -> 用 DeviceType=462（S5 家族，圆表）+ 480x480 的
    Screen；preview.png 必须是 326x326，别的尺寸直接拒绝
  * 预览图按 tools/pages.py 的首页规格真渲染（真 MiSans 字体）再套圆形 alpha 缩到 326
  * 两份盘共用同一个 watchface id 462150103：装一份就顶掉另一份
"""
import os, sys, json, shutil
from PIL import Image, ImageDraw
from paths import PROJ, WORK
import render_ui as R
from pages import PAGES

ROLE = (sys.argv[1] if len(sys.argv) > 1 else 'replace').lower()
NAME = 'S5Chg' if ROLE == 'replace' else 'S5ChgRestore'   # 路径/标识（不要改）
OUT = os.path.join(WORK, 'overlay')
ASSETS = os.path.join(PROJ, 'assets')

DEVICE_TYPE = "462"                 # S5 家族（Compiler.exe 只认 362 / 462 这两个圆表档）
ENTRY_WIDGET = "app_lua%2Fmain.lua"
PREVIEW_SIZE = 326                  # Compiler.exe 对圆表设备强制 326x326
SCREEN_SIZE = 480
WF_ID = "462150103"                 # 两份盘共用同一个 id：装一份就顶掉另一份
TITLE = 'S5e Pt.3'                  # 手表上显示的表盘名（两份盘同一个名字）= fprj 的 <Screen Title>


def make_preview(path):
    """480 首页 -> 圆形 alpha -> 326x326（Compiler.exe 只收这个尺寸）。"""
    R.W = R.H = SCREEN_SIZE
    img = Image.new('RGBA', (SCREEN_SIZE, SCREEN_SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for it in PAGES['home']:
        k = it.get('kind')
        if k == 'rect':
            box = [it['x'], it['y'], it['x'] + it['w'] - 1, it['y'] + it['h'] - 1]
            r = it.get('radius', 0)
            (d.rounded_rectangle(box, radius=r, fill=R._rgb(it['bg']) + (255,)) if r
             else d.rectangle(box, fill=R._rgb(it['bg']) + (255,)))
        elif k == 'circle':
            d.ellipse([it['x'], it['y'], it['x'] + it['w'] - 1, it['y'] + it['h'] - 1],
                      fill=R._rgb(it['bg']) + (255,))
        elif k == 'image':
            if os.path.exists(it['src']):
                im = Image.open(it['src']).convert('RGBA').resize((it['w'], it['h']), Image.LANCZOS)
                img.alpha_composite(im, (it['x'], it['y']))
        elif k == 'label':
            R.draw_label(img, d, it)
    base = Image.new('RGBA', (SCREEN_SIZE, SCREEN_SIZE), (0, 0, 0, 255))
    base.alpha_composite(img)
    mask = Image.new('L', (SCREEN_SIZE, SCREEN_SIZE), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, SCREEN_SIZE - 1, SCREEN_SIZE - 1], fill=255)
    base.putalpha(mask)
    base.resize((PREVIEW_SIZE, PREVIEW_SIZE), Image.LANCZOS).save(path)


def write_fprj(path, title):
    xml = ('<?xml version="1.0" encoding="utf-16" ?>\r\n'
           f'<FaceProject DeviceType="{DEVICE_TYPE}">\r\n'
           f'    <Screen Title="{title}" Bitmap="preview.png">\r\n'
           f'        <Widget Shape="34" Name="{ENTRY_WIDGET}" '
           f'X="0" Y="0" Width="{SCREEN_SIZE}" Height="{SCREEN_SIZE}" Alpha="0" />\r\n'
           '    </Screen>\r\n</FaceProject>\r\n')
    open(path, 'w', encoding='utf-16', newline='').write(xml)


def build(name, role):
    base = os.path.join(OUT, name)
    if os.path.exists(base):
        shutil.rmtree(base)
    fprj = os.path.join(base, 'watchface', 'fprj')
    os.makedirs(os.path.join(fprj, 'images'), exist_ok=True)
    os.makedirs(os.path.join(fprj, 'app', 'lua'), exist_ok=True)

    cfg = {"projectName": TITLE, "watchfaceId": WF_ID, "power_consumption": "3",
           "resourceBin": {"lvglVersion": 9, "colorFormat": "I8", "compress": "NONE",
                           "input": "watchface/fprj/images/preview.png", "name": "preview"}}
    json.dump(cfg, open(os.path.join(base, 'watchface.config.json'), 'w', encoding='utf-8'),
              indent=4, ensure_ascii=False)
    write_fprj(os.path.join(fprj, f'{name}.fprj'), TITLE)
    make_preview(os.path.join(fprj, 'images', 'preview.png'))
    shutil.copyfile(os.path.join(PROJ, 'main.lua'),
                    os.path.join(fprj, 'app', 'lua', 'main.lua'))
    # 只放「合并后的单条目」(blob_<role>/) —— .face 里每个文件 = 一个资源条目
    blob = os.path.join(PROJ, 'blob_' + role)
    if not os.path.isdir(blob):
        raise SystemExit('缺少 blob_%s/ —— 先跑 tools/make_dd_payload.py %s' % (role, role))
    for src, rel in ((blob, 'pay'), (os.path.join(PROJ, 'ui_images'), 'ui')):
        dst = os.path.join(fprj, 'app', 'images', rel)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    return base


if __name__ == '__main__':
    build(NAME, ROLE)
    print('overlay written to', os.path.join(OUT, NAME))
