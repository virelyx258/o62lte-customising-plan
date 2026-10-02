# -*- coding: utf-8 -*-
"""为官方 LuaDevTemplate 生成可编译的 overlay。

两份盘（role）：
    replace -> S5ePAnim         负载 = q63 的帧
    restore -> S5ePAnimRestore  负载 = 原厂字节
两份盘**共用同一个 watchface id**（462150102）：装一份就顶掉另一份，设备上只占一份空间。

要点（都是踩过的坑）：
  * preview.png 必须是 326x326 —— Compiler.exe 对 DeviceType 462 只收这个尺寸
  * fprj 必须是 UTF-16（带 BOM）且用 CRLF，否则 Compiler.exe 直接拒绝
  * 表盘界面是 480x480（Screen Width/Height），预览图只是表盘列表里的缩略图
  * 负载只放 blob_<role>/ 那一份「合并后的单条目」
"""
import os, sys, json, shutil
from PIL import Image
from paths import PROJ, WORK, SCREEN, PREVIEW, WF_ID, DEVICE_TYPE
from s5e_pages import PAGES
import s5e_render_ui as R

ROLE = (sys.argv[1] if len(sys.argv) > 1 else 'replace').lower()
assert ROLE in ('replace', 'restore'), ROLE
NAME = 'S5ePAnim' if ROLE == 'replace' else 'S5ePAnimRestore'   # 路径/标识（不要改）
TITLE = 'S5e Pt.2'          # 手表上显示的表盘名（两份盘同一个名字）= fprj 的 <Screen Title>
OUT = os.path.join(WORK, 'overlay')
ENTRY_WIDGET = 'app_lua%2Fmain.lua'


def make_preview(path):
    """480 首页 -> 圆形 alpha -> 326x326（Compiler.exe 只收这个尺寸）。"""
    R.W = R.H = SCREEN
    img = R.render_raw(PAGES['home'])
    base = Image.new('RGBA', (SCREEN, SCREEN), (0, 0, 0, 255))
    base.alpha_composite(img)
    mask = Image.new('L', (SCREEN, SCREEN), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(mask).ellipse([0, 0, SCREEN - 1, SCREEN - 1], fill=255)
    base.putalpha(mask)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    base.resize((PREVIEW, PREVIEW), Image.LANCZOS).save(path)


def write_fprj(path, title):
    xml = ('<?xml version="1.0" encoding="utf-16" ?>\r\n'
           '<FaceProject DeviceType="%s">\r\n'
           '    <Screen Title="%s" Bitmap="preview.png">\r\n'
           '        <Widget Shape="34" Name="%s" X="0" Y="0" '
           'Width="%d" Height="%d" Alpha="0" />\r\n'
           '    </Screen>\r\n</FaceProject>\r\n'
           % (DEVICE_TYPE, title, ENTRY_WIDGET, SCREEN, SCREEN))
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
    write_fprj(os.path.join(fprj, name + '.fprj'), TITLE)
    make_preview(os.path.join(fprj, 'images', 'preview.png'))
    shutil.copyfile(os.path.join(PROJ, 'main.lua'),
                    os.path.join(fprj, 'app', 'lua', 'main.lua'))
    blob = os.path.join(PROJ, 'blob_' + role)
    if not os.path.isdir(blob):
        raise SystemExit('缺少 blob_%s/ —— 先跑 tools/s5e_payload.py %s' % (role, role))
    for src, rel in ((blob, 'pay'), (os.path.join(PROJ, 'ui_images'), 'ui')):
        dst = os.path.join(fprj, 'app', 'images', rel)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    return base


if __name__ == '__main__':
    build(NAME, ROLE)
    print('overlay written to', os.path.join(OUT, NAME))
