# -*- coding: utf-8 -*-
"""Two-pass build for the S5 eSIM icon face.

    watchface_s5e/main.lua      源码（含 __UIIMG__ / __PAY__ / __RB__ 占位符）
    build_overlay_s5e/S5eIcons  中间产物（回填后的 Lua 落在这里）
    _build_s5e/S5eIcons         编译工作区（Compiler.exe 的输入）
    _out/faces/S5eIcons.face    交付物

为什么两遍：.face 里各资源的偏移取决于打包顺序，我们靠在 .face 里搜字节来定位。
Lua 源码排在所有资源之后，所以回填（Lua 变长）不会移动前面的资源；脚本最后逐条校验 0 漂移。
"""
import os, sys, json, shutil, subprocess, hashlib, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
import render_ui as R
from s5e_pages import PAGES

from paths import PROJ, WORK, DIST, TEMPLATE
WF = PROJ                                     # 源码就在项目根
TPL = TEMPLATE
OVER = os.path.join(WORK, 'overlay', 'S5eIcons')
BUILD = os.path.join(WORK, 'build', 'S5eIcons')
OUTFACE = DIST
NAME = 'S5eIcons'            # 路径/标识（文件名、目录名、dist 名都用它，**不要改**）
DISPLAY_NAME = 'S5e Pt.1'    # 手表上显示的表盘名 = fprj 的 <Screen Title> = config 的 projectName
WF_ID = '462150101'          # 462 = S5 家族（固件自带 AOD 表盘是 462150001..8）
DEVICE_TYPE = '462'
SCREEN = 480
PREVIEW = 326
MAGIC_PAY = b'\x00S5E-PAYv1\x00\xa5\x5a\xc3\x3c'
MAGIC_RB = b'\x00S5E-RBKv1\x00\x5a\xa5\x3c\xc3'
MAGIC_LEN = len(MAGIC_PAY)      # 15 —— 别再手写常量，之前写 16 让偏移整体差 1
LOG = []


def log(s):
    print(s)
    LOG.append(s)


def make_preview(path):
    """480 首页 -> 圆形 alpha -> 326x326（Compiler.exe 只收这个尺寸）"""
    R.W = R.H = SCREEN
    items = PAGES['home']
    img = Image.new('RGBA', (SCREEN, SCREEN), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for it in items:
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
    base = Image.new('RGBA', (SCREEN, SCREEN), (0, 0, 0, 255))
    base.alpha_composite(img)
    mask = Image.new('L', (SCREEN, SCREEN), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, SCREEN - 1, SCREEN - 1], fill=255)
    base.putalpha(mask)
    base.resize((PREVIEW, PREVIEW), Image.LANCZOS).save(path)


def prepare(lua_text):
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    shutil.copytree(TPL, BUILD)
    old = os.path.join(BUILD, 'watchface', 'fprj', 'LuaDevTemplate.fprj')
    if os.path.exists(old):
        os.remove(old)

    cfg = {"projectName": DISPLAY_NAME, "watchfaceId": WF_ID, "power_consumption": "3",
           "resourceBin": {"lvglVersion": 9, "colorFormat": "I8", "compress": "NONE",
                           "input": "watchface/fprj/images/preview.png", "name": "preview"}}
    json.dump(cfg, open(os.path.join(BUILD, 'watchface.config.json'), 'w', encoding='utf-8'),
              indent=4, ensure_ascii=False)

    fprj = ('<?xml version="1.0" encoding="utf-16" ?>\r\n'
            '<FaceProject DeviceType="%s">\r\n'
            '    <Screen Title="%s" Bitmap="preview.png">\r\n'
            '        <Widget Shape="34" Name="app_lua%%2Fmain.lua" X="0" Y="0" '
            'Width="%d" Height="%d" Alpha="0" />\r\n'
            '    </Screen>\r\n</FaceProject>\r\n') % (DEVICE_TYPE, DISPLAY_NAME, SCREEN, SCREEN)
    fprjdir = os.path.join(BUILD, 'watchface', 'fprj')
    open(os.path.join(fprjdir, NAME + '.fprj'), 'w',
         encoding='utf-16', newline='').write(fprj)

    make_preview(os.path.join(fprjdir, 'images', 'preview.png'))
    open(os.path.join(fprjdir, 'app', 'lua', 'main.lua'), 'w',
         encoding='utf-8', newline='\n').write(lua_text)

    imgdir = os.path.join(fprjdir, 'app', 'images')
    for sub, src in (('pay', os.path.join(WF, 'payload')),
                     ('ui', os.path.join(WF, 'ui_images'))):
        dst = os.path.join(imgdir, sub)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        os.makedirs(dst)
        for fn in sorted(os.listdir(src)):
            shutil.copyfile(os.path.join(src, fn), os.path.join(dst, fn))
    shutil.copyfile(os.path.join(WF, 'payload_rollback', 'rollback.bin'),
                    os.path.join(imgdir, 'pay', 'rollback.bin'))


def run_build(script=True):
    ps = os.path.join(BUILD, 'scripts', 'build_face.ps1')
    # 显式给 -FaceName：vendor 脚本默认拿 config 的 projectName 当输出名，而 projectName
    # 现在是**显示名**（S5e Pt.1），交付文件名必须还是 NAME.face。
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps,
                        '-FaceName', NAME + '.face'],
                       capture_output=True, text=True, errors='replace')
    workspace_fprj()      # vendor 可能把 .fprj 改名成显示名，编完改回 NAME.fprj
    tail = [l for l in ((r.stdout or '') + (r.stderr or '')).splitlines() if l.strip()][-6:]
    for l in tail:
        log('   | ' + l)
    face = os.path.join(BUILD, 'bin', NAME + '.face')
    if not os.path.exists(face):
        raise SystemExit('build failed: no ' + face)
    return open(face, 'rb').read()


def workspace_fprj():
    """把工作区里的 .fprj 归一成 NAME.fprj，并返回它的路径。

    我们写下去时就是 NAME.fprj，但 vendor 的 build_face.ps1 会先跑
    sync_watchface_config.ps1：它按 config 的 projectName（现在是**显示名**）找
    <projectName>.fprj，找不到就把唯一那份改名过去（Title 也被改写成 projectName）。
    编完这里再改回 NAME.fprj —— 这样工作区里始终只有一份 .fprj（放两份会被
    Compiler.exe 并成双倍资源，实测资源整体翻倍），文件名也保持项目标识不变。
    """
    d = os.path.join(BUILD, 'watchface', 'fprj')
    fs = sorted(f for f in os.listdir(d) if f.endswith('.fprj'))
    if len(fs) != 1:
        raise SystemExit('watchface/fprj 下的 .fprj 应恰好 1 份，实际：%s' % fs)
    want = os.path.join(d, NAME + '.fprj')
    if fs[0] != NAME + '.fprj':
        os.replace(os.path.join(d, fs[0]), want)
    return want


def compile_raw():
    exe = os.path.join(BUILD, 'watchface', 'tools', 'Compiler.exe')
    fprj = workspace_fprj()
    out = os.path.join(BUILD, 'raw')
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    subprocess.run([exe, '-b', fprj, out, NAME + '.face', WF_ID],
                   capture_output=True, text=True, errors='replace')
    p = os.path.join(out, NAME + '.face')
    if not os.path.exists(p):
        raise SystemExit('raw compile failed')
    return open(p, 'rb').read()


def hits(face, blob):
    out, s = [], 0
    while True:
        i = face.find(blob, s)
        if i < 0:
            return out
        out.append(i)
        s = i + 1


def locate(face, rels):
    """量出 UI 图片 / 负载 在 .face 里的偏移，并逐条字节校验"""
    ui = []
    for fn in sorted(os.listdir(os.path.join(WF, 'ui_images'))):
        if not fn.endswith('.bin'):
            continue
        blob = open(os.path.join(WF, 'ui_images', fn), 'rb').read()
        h = hits(face, blob)
        if len(h) != 1:
            raise SystemExit('UI %s 命中 %d 次' % (fn, len(h)))
        ui.append((h[0], len(blob), fn[:-4]))
    pay_base = hits(face, MAGIC_PAY)
    rb_base = hits(face, MAGIC_RB)
    if len(pay_base) != 1 or len(rb_base) != 1:
        raise SystemExit('payload magic 命中 %d/%d 次（应为 1）' % (len(pay_base), len(rb_base)))
    pay_base, rb_base = pay_base[0], rb_base[0]

    hashes = {'pay': {i: r['sha256'] for i, r in enumerate(recs)},
              'rb': {i: r['rb_sha256'] for i, r in enumerate(recs)}}
    for tag, base, path in (('pay', pay_base, os.path.join(WF, 'payload', 'payload.bin')),
                            ('rb', rb_base, os.path.join(WF, 'payload_rollback', 'rollback.bin'))):
        data = open(path, 'rb').read()
        # 整个负载文件必须**原样连续**放在 base 处 —— 这是"偏移=base+magic+rel"成立的前提
        if face.find(data) != base:
            raise SystemExit('%s 文件不是原样连续存放（找不到或位置不符）' % tag)
        for i, (off, ln) in enumerate(rels[tag]):
            res = base + MAGIC_LEN + off
            if i == 0:
                log('  %s 资源偏移 0x%x（%%4=%d，运行时走 /tmp 中转，不依赖对齐）'
                    % (tag, res, res % 4))
            # 用独立的 sha256（来自生成负载时的 manifest）校验，避免"自己比自己"这种恒真检查
            seg = face[res:res + ln]
            if len(seg) != ln or hashlib.sha256(seg).hexdigest() != hashes[tag][i]:
                raise SystemExit('%s[%d] 在 0x%x 处字节不吻合' % (tag, i, res))
    return ui, pay_base, rb_base


FACE = None
rels = {'pay': [], 'rb': []}
recs = json.load(open(os.path.join(WORK, 's5e_from_os4', 'manifest.json'), encoding='utf-8'))['records']
off = 0
for r in recs:
    rels['pay'].append((off, r['length']))
    off += r['length']
off = 0
for r in recs:
    rels['rb'].append((off, r['length']))
    off += r['length']

src = open(os.path.join(WF, 'main.lua'), encoding='utf-8').read()
for ph in ('__UIIMG__', '__PAY__', '__RB__'):
    if ph not in src:
        raise SystemExit('watchface_s5e/main.lua 缺少占位符 ' + ph)

# ---------------------------------------------------------------- pass 1
log('第 1 遍：占位符版编一次，量出资源偏移')
prepare(src)
face1 = run_build()
log('  face %d bytes' % len(face1))
ui, pay_base, rb_base = locate(face1, rels)
for o, l, n in ui:
    log('  %-12s off=0x%06x len=%d' % (n, o, l))
log('  payload base=0x%06x  rollback base=0x%06x' % (pay_base, rb_base))

ui_txt = '\n'.join('  { %d, %d, "%s" },' % (o, l, n) for o, l, n in ui)
pay_txt = '  pay = {\n' + '\n'.join(
    '    { "%s", 0x%08x, %d, %d },' % (r['dev'], r['offset'], r['length'], pay_base + MAGIC_LEN + rels['pay'][i][0])
    for i, r in enumerate(recs)) + '\n  },'
rb_txt = '  rb = {\n' + '\n'.join(
    '    { "%s", 0x%08x, %d, %d },' % (r['dev'], r['offset'], r['length'], rb_base + MAGIC_LEN + rels['rb'][i][0])
    for i, r in enumerate(recs)) + '\n  },'
resolved = src.replace('__UIIMG__', ui_txt).replace('__PAY__', pay_txt).replace('__RB__', rb_txt)
assert '__UIIMG__' not in resolved and '__PAY__' not in resolved and '__RB__' not in resolved
overlay_lua = os.path.join(OVER, 'watchface', 'fprj', 'app', 'lua')
os.makedirs(overlay_lua, exist_ok=True)
open(os.path.join(overlay_lua, 'main.lua'), 'w', encoding='utf-8', newline='\n').write(resolved)
log('第 2 遍：回填后的 Lua（%d bytes）重新编译' % len(resolved))

# ---------------------------------------------------------------- pass 2
prepare(resolved)
face2 = run_build()
ui2, pay_base2, rb_base2 = locate(face2, rels)
drift = 0
if (pay_base2, rb_base2) != (pay_base, rb_base) or ui2 != ui:
    drift = 1
log('偏移校验：%s' % ('0 漂移' if not drift else '!! 有漂移'))
if drift:
    raise SystemExit('resource offsets drifted between pass 1 and pass 2')

# ---------------------------------------------------------------- finalize
raw = compile_raw()
d = bytearray(raw)
assert d[0:4] == b'\x5a\xa5\x34\x12', 'bad face magic'
d[40:50] = WF_ID.encode() + b'\x00' * (10 - len(WF_ID))
os.makedirs(OUTFACE, exist_ok=True)
faithful = os.path.join(OUTFACE, NAME + '.face')
open(faithful, 'wb').write(bytes(d))
toolchain = os.path.join(OUTFACE, NAME + '_toolchain.face')
shutil.copyfile(os.path.join(BUILD, 'bin', NAME + '.face'), toolchain)

# 交付产物独立自查：直接从最终 .face 里抠出来比对
fin = open(faithful, 'rb').read()
ui3, pb3, rb3 = locate(fin, rels)
assert ui3 == ui and pb3 == pay_base and rb3 == rb_base
for i, r in enumerate(recs):
    res = pb3 + MAGIC_LEN + rels['pay'][i][0]
    assert fin[res:res + r['length']] == open(os.path.join(WF, 'payload', 'payload.bin'), 'rb').read()[MAGIC_LEN + rels['pay'][i][0]:MAGIC_LEN + rels['pay'][i][0] + r['length']]
log('')
log('%-34s %10s b4 b5 id          sha256[:16]' % ('file', 'bytes'))
for p in (faithful, toolchain):
    b = open(p, 'rb').read()
    log('%-34s %10d %2d %2d %-10r  %s' % (os.path.basename(p), len(b), b[4], b[5], b[40:50],
                                          hashlib.sha256(b).hexdigest()[:16]))
_p32, = struct.unpack('<I', fin[32:36])
_pal, _pw, _ph, _psz = struct.unpack('<IHHI', fin[_p32:_p32 + 12])
log('preview @0x%x: %dx%d, palette %d B, data %d B' % (_p32, _pw, _ph, _pal, _psz))
log('交付物：' + faithful)
open(os.path.join(WORK, 's5e_build_log.txt'), 'w', encoding='utf-8').write('\n'.join(LOG))
