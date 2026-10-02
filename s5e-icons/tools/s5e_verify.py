# -*- coding: utf-8 -*-
"""Independent end-to-end check of the delivered .face.

Nothing here trusts the build script's bookkeeping: the Lua table is parsed out of
the face and every offset is validated against the *firmware images* (stock and
patched) and the ui_images directory.
"""
import os, re, sys, json, hashlib, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romfs import Romfs

from paths import PROJ, INPUTS, WORK, DIST
WF = PROJ
NEW = os.path.join(INPUTS, 'target')
PAT = os.path.join(WORK, 's5e_from_os4')
FACE = os.path.join(DIST, 'S5eIcons.face')
IMAGES = {'app': ('vela_app.bin', 'vela_app_os4.bin'), 'health': ('vela_health.bin', 'vela_health_os4.bin')}
MANIFEST = os.path.join(PAT, 'manifest.json')

face = open(FACE, 'rb').read()
# 直接从 .face 里把 Lua 抠出来校验（不依赖构建目录）
_end = face.find(b'return ui\n')
if _end < 0:
    raise SystemExit('face 里找不到 Lua 结尾')
_start = face.rfind(b'--[[', 0, _end)
lua = face[_start:_end + len(b'return ui\n')]
if not lua.startswith(b'--[[--') or b'local UIIMG = {' not in lua:
    raise SystemExit('Lua 提取失败：%r ... %r' % (lua[:24], lua[-24:]))
fails = []


def ck(cond, msg):
    print(('  OK   ' if cond else '  FAIL ') + msg)
    if not cond:
        fails.append(msg)


print('== 头部 ==')
ck(face[0:4] == b'\x5a\xa5\x34\x12', 'magic 5a a5 34 12')
ck(face[40:50] == b'462150101\x00', 'id = %r' % face[40:50])
ck(face[5] == 0, 'b5 = %d（固件自带表盘 b5 也是 0）' % face[5])
a16, = struct.unpack('<I', face[16:20])
a32, = struct.unpack('<I', face[32:36])
print('  info @16=%d @32=0x%x  文件 %d B' % (a16, a32, len(face)))

print('== 预览块 ==')
pal, pw, ph, psz = struct.unpack('<IHHI', face[a32:a32 + 12])
ck(pw == 326 and ph == 326, 'preview %dx%d（Compiler.exe 对 462 设备强制 326x326）' % (pw, ph))
ck(a32 + 12 + psz <= len(face) + 1,
   'preview 数据 %d B @0x%x（文件尾 0x%x）' % (psz, a32 + 12, len(face)))

print('== Lua 源码 ==')
ck(face.count(lua) == 1, 'Lua 源码原样出现 %d 次（%d B）' % (face.count(lua), len(lua)))
off_lua = face.find(lua)
ck(off_lua > 0, 'Lua 偏移 0x%x' % off_lua)
txt = lua.decode('utf-8')

print('== UI 图片（从 .face 里的 Lua 表读出来校验）==')
ui = re.findall(r'\{ (\d+), (\d+), "([a-z_]+)" \}', txt)
ck(len(ui) == 8, 'UIIMG 条目 %d 条' % len(ui))
files = {f[:-4]: open(os.path.join(WF, 'ui_images', f), 'rb').read()
         for f in os.listdir(os.path.join(WF, 'ui_images')) if f.endswith('.bin')}
for o, l, n in ui:
    o, l = int(o), int(l)
    ck(n in files and face[o:o + l] == files[n], '%(n)-12s @0x%(o)06x len=%(l)d 与 ui_images/%(n)s.bin 一致' % dict(n=n, o=o, l=l))

print('== 负载表 ==')
pay = re.findall(r'\{ "(app|health)", 0x([0-9a-f]+), (\d+), (\d+) \}', txt)
blocks = re.findall(r'^  (pay|rb) = \{', txt, re.M)
ck(blocks == ['pay', 'rb'], 'pay / rb 两个表都在')
half = len(pay) // 2
exp = json.load(open(MANIFEST, encoding='utf-8'))['records']
ck(half == len(exp) and len(pay) == 2 * len(exp),
   'pay %d 条 + rb %d 条（manifest 里 %d 条）' % (half, len(pay) - half, len(exp)))
pay_recs = [dict(dev=d, off=int(o, 16), ln=int(l), res=int(r)) for d, o, l, r in pay[:half]]
rb_recs = [dict(dev=d, off=int(o, 16), ln=int(l), res=int(r)) for d, o, l, r in pay[half:]]

stock, patched, sizes = {}, {}, {}
for dev, (sf, pf) in IMAGES.items():
    rs, rp = Romfs(os.path.join(NEW, sf)), Romfs(os.path.join(PAT, pf))
    stock[dev] = rs.data
    patched[dev] = rp.data
    sizes[dev] = rs.sb_size

bad = 0
for i, (p, r) in enumerate(zip(pay_recs, rb_recs)):
    assert p['dev'] == r['dev'] and p['off'] == r['off'] and p['ln'] == r['ln'], 'record %d 表错位' % i
    d, o, l = p['dev'], p['off'], p['ln']
    ok = (face[p['res']:p['res'] + l] == patched[d][o:o + l] and
          face[r['res']:r['res'] + l] == stock[d][o:o + l] and
          o % 4 == 0 and o + l <= sizes[d] and      # RLE 素材的长度可以是任意值，只要偏移对齐
          len(face[p['res']:p['res'] + l]) == l and len(face[r['res']:r['res'] + l]) == l)
    if not ok:
        bad += 1
        print('  FAIL %-22s %s off=0x%x len=%d' % (d, p['dev'], o, l))
ck(bad == 0, '%d 条：负载字节 == 改后镜像，回滚字节 == 原厂镜像，且都 4 对齐、不越界' % half)
devs = {}
for p in pay_recs:
    devs[p['dev']] = devs.get(p['dev'], 0) + 1
exp_devs = {}
for r in exp:
    exp_devs[r['dev']] = exp_devs.get(r['dev'], 0) + 1
ck(devs == exp_devs, '分区分布 %s（manifest %s）' % (devs, exp_devs))

print('== 负载文件在 .face 里连续存放 ==')
pbin = open(os.path.join(WF, 'payload', 'payload.bin'), 'rb').read()
rbin = open(os.path.join(WF, 'payload_rollback', 'rollback.bin'), 'rb').read()
ck(face.count(pbin) == 1 and face.count(rbin) == 1,
   'payload %d B / rollback %d B 各出现 1 次' % (len(pbin), len(rbin)))
rel = sorted(x['res'] - (face.find(pbin) + 15) for x in pay_recs)
ck(rel[0] == 0, '第一条负载相对偏移为 0')
ck(face[pay_recs[0]['res'] - 15:pay_recs[0]['res']] == pbin[:15], 'magic 紧贴第一条负载')

print()
if fails:
    print('!! %d 项未通过' % len(fails))
    sys.exit(1)
print('全部通过 —— %s (%d B, sha256 %s)' % (os.path.basename(FACE), len(face),
                                        hashlib.sha256(face).hexdigest()[:16]))
