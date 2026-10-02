"""为官方 LuaDevTemplate 生成可编译的 overlay。两份盘：S4Chg（替换）/ S4ChgRestore（还原）。"""
import os, sys, json, shutil
from PIL import Image, ImageFont
from paths import PROJ, WORK

ROLE = (sys.argv[1] if len(sys.argv) > 1 else 'replace').lower()
NAME = 'S4Chg' if ROLE == 'replace' else 'S4ChgRestore'
# 手表上显示的表盘名：replace / restore 两张盘共用同一个名字（写进 .fprj 的 <Screen Title>，
# 同时就是 watchface.config.json 的 projectName）。只是「显示名」—— NAME、.fprj 文件名、
# dist/<NAME>.face、.work/build/<NAME>、表盘 id 这些路径/标识全部不变。
DISPLAY_NAME = 'S4e Pt.3'
OUT = os.path.join(WORK, 'overlay')
ASSETS = os.path.join(PROJ, 'assets')

DEVICE_TYPE = "362"                 # 与官方模板一致（362 = S4 家族）
ENTRY_WIDGET = "app_lua%2Fmain.lua"
PREVIEW_SIZE = 326                  # Compiler.exe 对 362 设备强制 326x326
SCREEN_SIZE = 466
WF_ID = "362150103"                 # 两份盘共用同一个 id：装一份就顶掉另一份
FONTS = [r'C:\Windows\Fonts\msyhbd.ttc', r'C:\Windows\Fonts\msyh.ttc',
         r'C:\Windows\Fonts\arialbd.ttf', r'C:\Windows\Fonts\arial.ttf']


def font(size):
    for p in FONTS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_preview(path):
    Image.open(os.path.join(ASSETS, 'cover.png')).convert('RGBA') \
         .resize((PREVIEW_SIZE, PREVIEW_SIZE), Image.LANCZOS).save(path)


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

    cfg = {"projectName": DISPLAY_NAME, "watchfaceId": WF_ID, "power_consumption": "3",
           "resourceBin": {"lvglVersion": 9, "colorFormat": "I8", "compress": "NONE",
                           "input": "watchface/fprj/images/preview.png", "name": "preview"}}
    json.dump(cfg, open(os.path.join(base, 'watchface.config.json'), 'w', encoding='utf-8'),
              indent=4, ensure_ascii=False)
    write_fprj(os.path.join(fprj, f'{name}.fprj'), DISPLAY_NAME)
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
