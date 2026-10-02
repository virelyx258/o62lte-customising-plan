# -*- coding: utf-8 -*-
"""S4 图标表盘交付物的独立校验（不信任构建脚本的账本）。

从 dist/S5Icons.face 里把 Lua 源码抠出来 -> 解析 UIIMG / PAYTBL 两张表 ->
每一条都拿去和 **固件镜像**（inputs/target 原厂 + .work/s4_from_s5 改后）以及
ui_images/ 目录逐字节比对；另外单独验证 voice_aivs 那条的字节就是
assets/override/voice_aivs.png 按槽位格式重编码的结果。

用法：  python tools/s4e_verify.py
"""
import os, re, sys, json, hashlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romfs import Romfs
from lvgl_bin import decode_lvgl_bin
import iconpack as ip
from PIL import Image, ImageFilter

from paths import PROJ, INPUTS, WORK, DIST

FACE = os.path.join(DIST, 'S5Icons.face')
STOCK = os.path.join(INPUTS, 'target', 'vela_app.bin')
PATCHED = os.path.join(WORK, 's4_from_s5', 'vela_app_s5icons.bin')
MANIFEST = os.path.join(WORK, 's4_from_s5', 'manifest.json')
WID = '362150101'

fails = []


def ck(cond, msg):
    print(('  OK   ' if cond else '  FAIL ') + msg)
    if not cond:
        fails.append(msg)


face = open(FACE, 'rb').read()
_end = face.find(b'return ui\n')
if _end < 0:
    raise SystemExit('face 里找不到 Lua 结尾')
_start = face.rfind(b'--[[', 0, _end)
lua = face[_start:_end + len(b'return ui\n')]
if not lua.startswith(b'--[[--') or b'local UIIMG = {' not in lua:
    raise SystemExit('Lua 提取失败：%r ... %r' % (lua[:24], lua[-24:]))
txt = lua.decode('utf-8')

print('== 头部 ==')
ck(face[0:4] == b'\x5a\xa5\x34\x12', 'magic 5a a5 34 12')
ck(face[40:50] == (WID + '\x00').encode(), 'id = %r' % face[40:50])
ck(face[5] == 0, 'b5 = %d（固件自带表盘也是 0）' % face[5])
ck(face.count(lua) == 1, 'Lua 源码原样出现 %d 次（%d B）' % (face.count(lua), len(lua)))
print('  文件 %d B' % len(face))

print('== UI 图片 ==')
ui = re.findall(r'\{(\d+),(\d+),"([a-z_]+)"\}', txt)
files = {f[:-4]: open(os.path.join(PROJ, 'ui_images', f), 'rb').read()
         for f in os.listdir(os.path.join(PROJ, 'ui_images')) if f.endswith('.bin')}
ck(len(ui) == len(files), 'UIIMG %d 条（ui_images 里 %d 个）' % (len(ui), len(files)))
for o, l, n in ui:
    o, l = int(o), int(l)
    ck(n in files and face[o:o + l] == files[n],
       '%-12s @0x%06x len=%-6d 与 ui_images/%s.bin 一致' % (n, o, l, n))

print('== 负载表结构 ==')
_pay_at = txt.index('pay = {')
_rb_at = txt.index('rb = {', _pay_at)
pay = [(int(a), int(b), int(c)) for a, b, c in re.findall(r'\{(\d+),(\d+),(\d+)\}', txt[_pay_at:_rb_at])]
rb = [(int(a), int(b), int(c)) for a, b, c in re.findall(r'\{(\d+),(\d+),(\d+)\}', txt[_rb_at:])]
exp = json.load(open(MANIFEST, encoding='utf-8'))['records']          # 计划替换的 81 条
pj = json.load(open(os.path.join(PROJ, 'payload.json'), encoding='utf-8'))
emit = pj['records']                                                 # 实际下发的（含 canary）
dropped = pj['dropped_identical']
ck(len(emit) - 1 == len(exp) - len(dropped),
   '下发 %d 条 = 计划 %d 条 - 与源逐字节相同的 %d 条 %s + canary'
   % (len(emit), len(exp), len(dropped), dropped))
ck(len(pay) == len(rb) == len(emit), 'pay %d 条 / rb %d 条（payload.json %d 条）'
   % (len(pay), len(rb), len(emit)))
ck(len(pay) > 0 and len(pay) == len(rb), '两张表条数相同')

print('== 逐条字节比对（负载 vs 改后镜像、回滚 vs 原厂镜像）==')
stock = open(STOCK, 'rb').read()
patched = open(PATCHED, 'rb').read()
ck(len(stock) == len(patched) and stock[:8] == b'-rom1fs-', '两个整分区镜像等长且是 ROMFS')
bad, misalign, manifest_bad = 0, 0, 0
for i, ((po, pt, pl), (ro, rt, rl)) in enumerate(zip(pay, rb)):
    if not (po and ro) or (pt, pl) != (rt, rl):
        manifest_bad += 1
        continue
    if pt % 4 or pt + pl > len(stock):      # RLE 素材的长度可以是任意值，只有偏移必须对齐
        misalign += 1
    if (face[po:po + pl] != patched[pt:pt + pl] or len(face[po:po + pl]) != pl
            or face[ro:ro + pl] != stock[pt:pt + pl] or len(face[ro:ro + pl]) != pl):
        bad += 1
        print('  FAIL #%d %s off=0x%x len=%d'
              % (i, emit[i]['name'] if i < len(emit) else '?', pt, pl))
ck(bad == 0, '%d 条：负载 == 改后镜像，回滚 == 原厂镜像' % len(pay))
ck(misalign == 0, '全部 4 对齐且不越界')
ck(manifest_bad == 0, 'pay/rb 的目标偏移与长度一一对应')
names_in_lua = [e['name'] for e in emit]
plan_only = [r['name'] for r in exp if r['name'] not in dropped]
ck(names_in_lua[1:] == plan_only, '下发名单（去掉 canary）== 计划名单（去掉 %s）' % dropped)

print('== 负载名单 ==')
names = [r['name'] for r in exp]
ck('voice_aivs' in names, 'voice_aivs 在负载里')
ck(sorted(names) == sorted(set(names)), '没有重名记录')

print('== voice_aivs 的字节 == 用户 PNG 重编码 ==')
rec = next(r for r in exp if r['name'] == 'voice_aivs')
r = Romfs(STOCK)
sheet = {p: i for p, i in r.entries() if p == 'voice/aivs/launcher.bin'}
ino = sheet['voice/aivs/launcher.bin']
ck(ino.data_off == rec['offset'] and ino.size == rec['length'],
   'manifest 偏移/长度 == ROMFS inode（0x%08x / %d）' % (ino.data_off, ino.size))
h, stock_img = decode_lvgl_bin(r.read(ino))


def ink_bbox(img, thr=16):
    a = img.convert('RGBA').getchannel('A'); w, hh = a.size; px = a.load()
    x0, y0, x1, y1 = w, hh, -1, -1
    for y in range(hh):
        for x in range(w):
            if px[x, y] > thr:
                x0 = min(x0, x); y0 = min(y0, y); x1 = max(x1, x); y1 = max(y1, y)
    return None if x1 < 0 else (x0, y0, x1, y1)


sp = os.path.join(PROJ, 'assets', 'override', 'voice_aivs.png')
src = Image.open(sp).convert('RGBA')
sb = ink_bbox(stock_img)
target = max(sb[2] - sb[0] + 1, sb[3] - sb[1] + 1)
nb = ink_bbox(src)
art = src.crop((nb[0], nb[1], nb[2] + 1, nb[3] + 1)).resize((target, target), Image.LANCZOS)
cv = Image.new('RGBA', (h['w'], h['h']), (0, 0, 0, 0))
cv.paste(art, ((h['w'] - target) // 2, (h['h'] - target) // 2))
want = ip.encode(cv, h['cf'], h['w'], h['h'], h['flags'])
ck(len(want) == ino.size, '按槽位格式重编码 %d B == 槽位 %d B' % (len(want), ino.size))
got = [(o, t, l) for (o, t, l) in pay if t == rec['offset']]
ck(bool(got) and face[got[0][0]:got[0][0] + rec['length']] == want,
   '交付物里 voice_aivs 的负载字节 == 用户 PNG 重编码结果')
ck(patched[ino.data_off:ino.data_off + ino.size] == want, '改后整分区镜像里也是同一份字节')
ck(stock[ino.data_off:ino.data_off + ino.size] != want, '与 S4 原厂字节确实不同')
ck(os.path.basename(sp) == 'voice_aivs.png' and
   hashlib.sha256(open(sp, 'rb').read()).hexdigest()[:16] == '362166b54ac03f2b',
   'override 源图 sha256 362166b54ac03f2b（= 用户给的 smallai.png）')

print('== ROMFS 结构未被破坏 ==')
a = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in Romfs(STOCK).entries()]
b = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in Romfs(PATCHED).entries()]
ck(a == b, 'inode 表逐位不变（%d 条）' % len(a))
ck(Romfs(STOCK).sb_size == Romfs(PATCHED).sb_size and
   Romfs(STOCK).sb_cksum == Romfs(PATCHED).sb_cksum, 'superblock 不变')
r2 = Romfs(PATCHED)
i1 = {p: i for p, i in Romfs(STOCK).entries()}
i2 = {p: i for p, i in r2.entries()}
changed = sorted(p for p in i1 if Romfs(STOCK).read(i1[p]) != r2.read(i2[p]))
ck(len(changed) == len(pay) - 1, '真正变化的文件 %d 个（负载 %d 条，其中 canary 是分区头）'
   % (len(changed), len(pay)))

print('== 负载/回滚文件在 .face 里连续存放 ==')
pfiles = [(f, open(os.path.join(PROJ, 'payload', f), 'rb').read())
          for f in sorted(os.listdir(os.path.join(PROJ, 'payload'))) if f.endswith('.bin')]
rbfiles = [(f, open(os.path.join(PROJ, 'payload_rollback', f), 'rb').read())
           for f in sorted(os.listdir(os.path.join(PROJ, 'payload_rollback'))) if f.endswith('.bin')]
ck(len(pfiles) == len(pay), 'payload/ 里 %d 个文件 == %d 条' % (len(pfiles), len(pay)))
hit_pay = sum(1 for (o, t, l) in pay if any(face[o:o + l] == d for _, d in pfiles))
hit_rb = sum(1 for (o, t, l) in rb if any(face[o:o + l] == d for _, d in rbfiles))
ck(hit_pay == len(pay), '每条负载都能在 payload/ 里找到同名同字节的文件（%d/%d）' % (hit_pay, len(pay)))
ck(hit_rb == len(rb), '每条回滚都能在 payload_rollback/ 里找到（%d/%d）' % (hit_rb, len(rb)))

print()
if fails:
    print('!! %d 项未通过' % len(fails))
    sys.exit(1)
print('全部通过 —— %s (%d B, sha256 %s)' % (os.path.basename(FACE), len(face),
                                        hashlib.sha256(face).hexdigest()[:16]))
