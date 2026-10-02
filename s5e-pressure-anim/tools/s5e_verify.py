# -*- coding: utf-8 -*-
"""独立校验交付的两张 .face —— 只读交付物 + 固件镜像，不信任任何中间产物。

  role=replace -> dist/S5ePAnim.face        pay 应等于**改后镜像**的字节，rb 应等于**原厂**前 64 B
  role=restore -> dist/S5ePAnimRestore.face pay 应等于**原厂**字节，    rb 应等于**改后**前 64 B

查的东西（缺一不可）：
  ① .face 头：magic / b4 / b5 / id / 预览块尺寸 326x326
  ② 从 .face 里**反解**加载的 Lua 源码：ROLE 正确、占位符已回填、
     分区键是 'health'（不是 '/dev/health'，那样运行时会拼成 if=nil）
  ③ pay / rb 表逐条：目标偏移 == 原厂槽位 data_off、长度 == 原槽位长度（等长覆盖的底线）
  ④ 每条 pay 长度 == 原槽位长度，且能按 LVGL RLE 解出**正好 usize 字节**、解成 464x464
  ⑤ 每条 pay 字节 == 另一侧镜像对应位置；每条 rb 指纹 == 另一侧前 64 B
  ⑥ 改后镜像的 inode 表 / superblock / 分区长度与原厂**逐位一致**
  ⑦ 负载在 .face 里原样连续存放（偏移 == 文件基址 + 魔数长度 + 相对偏移 的前提）
"""
import os, re, sys, json, struct, hashlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import (PROJ, INPUTS, WORK, DIST, TARGET_IMAGE, DIRP, FACE_W, FACE_H,
                   WF_ID, PREVIEW, SCREEN)
from romfs import Romfs
import lvgl_bin as L

ROLE = (sys.argv[1] if len(sys.argv) > 1 else 'replace').lower()
assert ROLE in ('replace', 'restore'), ROLE
NAME = 'S5ePAnim' if ROLE == 'replace' else 'S5ePAnimRestore'
FACE = os.path.join(DIST, NAME + '.face')
PATCHED = os.path.join(WORK, 'anim', 'vela_health_anim.bin')
FP_LEN = 64
ok = fail = 0


def ck(cond, msg):
    global ok, fail
    if cond:
        ok += 1
        print('  OK   ' + msg)
    else:
        fail += 1
        print('  FAIL ' + msg)


print('=' * 78)
print('%s（role=%s）  %s' % (NAME, ROLE, FACE))
print('=' * 78)
if not os.path.exists(FACE):
    raise SystemExit('交付物不存在：%s' % FACE)
face = open(FACE, 'rb').read()
stock_b = open(TARGET_IMAGE, 'rb').read()
patch_b = open(PATCHED, 'rb').read()
stock = Romfs(TARGET_IMAGE)
patched = Romfs(PATCHED)

# ---------------------------------------------------------------- ① 头
print('\n[1] .face 头')
ck(face[0:4] == b'\x5a\xa5\x34\x12', 'magic 5a a5 34 12')
ck(face[4] in (0, 1, 2), 'b4 = %d' % face[4])
ck(face[5] == 0, 'b5 = %d（固件自带表盘 b5 也是 0）' % face[5])
ck(face[40:50] == WF_ID.encode() + b'\x00', 'id = %r（期望 %r）' % (face[40:50], WF_ID))
a32, = struct.unpack('<I', face[32:36])
pal, pw, ph, psz = struct.unpack('<IHHI', face[a32:a32 + 12])
ck((pw, ph) == (PREVIEW, PREVIEW), 'preview %dx%d（Compiler.exe 对 462 设备强制 %dx%d）'
   % (pw, ph, PREVIEW, PREVIEW))
ck(a32 + 12 + psz <= len(face) + 1, 'preview 数据 %d B @0x%x（文件尾 0x%x）' % (psz, a32 + 12, len(face)))
print('      文件 %d B  sha256 %s' % (len(face), hashlib.sha256(face).hexdigest()))

# ---------------------------------------------------------------- ② Lua 源码
print('\n[2] 从 .face 里反解加载的 Lua')
_end = face.find(b'return ui\n')
ck(_end > 0, '找到 Lua 结尾 "return ui\\n"')
_start = face.rfind(b'--[[', 0, _end)
lua = face[_start:_end + len(b'return ui\n')]
ck(lua.startswith(b'--[[--') and b'local UIIMG = {' in lua, 'Lua 提取成功（%d B）' % len(lua))
txt = lua.decode('utf-8')
ck(face.count(lua) == 1, 'Lua 原样出现 1 次（偏移 0x%x）' % face.find(lua))
c = re.search(r"local ROLE = '(\w+)'", txt)
ck(c is not None and c.group(1) == ROLE, "Lua 里的 ROLE == '%s'" % ROLE)
ck('__UIIMG__' not in txt and '__PAY__' not in txt and '__RB__' not in txt
   and '__ROLE__' not in txt, '占位符已全部回填')
ck(re.search(r'local W, H = %d, %d' % (SCREEN, SCREEN), txt) is not None,
   '界面尺寸 W,H = %d,%d（480x480 圆屏）' % (SCREEN, SCREEN))
# ★ S4e 那版踩过的坑：Lua 表里存 '/dev/app'，运行时又拼一次 -> if=nil
mdev = re.search(r'local DEVS = \{([^}]*)\}', txt)
ck(mdev is not None and '/dev/health' in mdev.group(1),
   'DEVS 里有 health -> /dev/health：%s' % (mdev.group(1).strip() if mdev else None))

# ---------------------------------------------------------------- 偏移（自己找，不信 Lua）
print('\n[3] 资源偏移（独立在 .face 里搜字节，不信 Lua 表）')
ML_PAY = b'\x00S5P-PAYv1\x00\xa5\x5a\xc3\x3c'
ML_FP = b'\x00S5P-FPv1\x00\x5a\xa5\x3c\xc3'
offs = json.load(open(os.path.join(PROJ, 'blob_' + ROLE, 'offsets.json'), encoding='utf-8'))
pay_blob = open(os.path.join(PROJ, 'blob_' + ROLE, 'payload.bin'), 'rb').read()
fp_blob = open(os.path.join(PROJ, 'blob_' + ROLE, 'fp.bin'), 'rb').read()
ck(face.count(ML_PAY) == 1, 'payload 魔数（%d B）在 .face 里唯一' % len(ML_PAY))
ck(face.count(ML_FP) == 1, 'fp 魔数（%d B）在 .face 里唯一' % len(ML_FP))
pay_base = face.find(ML_PAY)
fp_base = face.find(ML_FP)
ck(face.find(pay_blob) == pay_base, 'payload.bin 原样连续存放在 0x%x' % pay_base)
ck(face.find(fp_blob) == fp_base, 'fp.bin 原样连续存放在 0x%x' % fp_base)
recs = offs['records']
ck(len(recs) == 119, '负载记录 %d 条（期望 119）' % len(recs))
# 整个负载文件必须**原样连续**放在 base 处 —— 这是"偏移 == base + 魔数 + rel"成立的前提
ck(face[pay_base:pay_base + len(pay_blob)] == pay_blob,
   'payload.bin %d B 在 .face 里逐字节连续' % len(pay_blob))
ck(face[fp_base:fp_base + len(fp_blob)] == fp_blob,
   'fp.bin %d B 在 .face 里逐字节连续' % len(fp_blob))

# Lua 表里的偏移必须和独立量出来的一致
pay = [tuple(int(x) for x in r) for r in
       re.findall(r'\{(\d+),(\d+),(\d+)\}', re.search(r'pay = \{(.*?)\n  \},', txt, re.S).group(1))]
rb = [tuple(int(x) for x in r) for r in
      re.findall(r'\{(\d+),(\d+),(\d+)\}', re.search(r'rb = \{(.*?)\n  \},', txt, re.S).group(1))]
ck(len(pay) == len(recs) and len(rb) == len(recs),
   'Lua 表 pay %d 条 / rb %d 条' % (len(pay), len(rb)))
bad_off = 0
for i, r in enumerate(recs):
    if pay[i] != (pay_base + len(ML_PAY) + r['rel'], r['target'], r['length']):
        bad_off += 1
    if rb[i] != (fp_base + len(ML_FP) + r['fprel'], r['target'], r['fplen']):
        bad_off += 1
ck(bad_off == 0, 'Lua 表里的 %d 条偏移 == 文件基址 + 魔数长度 + 相对偏移' % len(recs))

# ---------------------------------------------------------------- 原厂槽位
slots = {}
for p, i in stock.entries():
    if i.type == 1 or not p.startswith(DIRP) or not p.endswith('.bin') or i.size == 0:
        continue
    slots[i.data_off] = (p, i.size, i)
ck(len(slots) == 119, '原厂 %s 下 %d 个槽位' % (DIRP, len(slots)))
usizes = {struct.unpack('<III', stock.read(slots[o][2])[12:24])[2] for o in slots}
ck(usizes == {1024 + FACE_W * FACE_H + 1},
   '原厂 usize 唯一且 == 1024 + %d*%d + 1 = %d' % (FACE_W, FACE_H, 1024 + FACE_W * FACE_H + 1))

# ---------------------------------------------------------------- ④⑤ 逐条
print('\n[4] 逐条负载')
EXPECT_PAY = patch_b if ROLE == 'replace' else stock_b
EXPECT_FP = stock_b if ROLE == 'replace' else patch_b
bad_len = bad_dec = bad_bytes = bad_shape = 0
for i, r in enumerate(recs):
    o, t, ln = pay[i]
    blob = face[o:o + ln]
    if t not in slots or slots[t][1] != ln or ln != r['length']:
        bad_len += 1
        continue
    if EXPECT_PAY[t:t + ln] != blob:
        bad_bytes += 1
    h = L.parse_header(blob)
    if h is None or not (h['flags'] & L.FLAG_COMPRESSED) or (h['w'], h['h']) != (FACE_W, FACE_H):
        bad_dec += 1
        continue
    _m, _cs, _us = struct.unpack('<III', blob[12:24])
    if len(L.rle_decompress(blob[24:24 + _cs], 1, None)) != _us or _us not in usizes:
        bad_dec += 1
        continue
    try:
        img = L.decode_lvgl_bin(blob)[1]
        if img is None or img.size != (FACE_W, FACE_H):
            bad_dec += 1
    except Exception:
        bad_dec += 1
ck(bad_len == 0, '每条负载长度 == 原槽位长度（%d 条）' % len(recs))
ck(bad_bytes == 0, '每条负载字节 == %s镜像对应位置'
   % ('改后' if ROLE == 'replace' else '原厂'))
ck(bad_dec == 0, '每条负载都能按 LVGL RLE 解出正好 usize 字节、解成 %dx%d' % (FACE_W, FACE_H))

print('\n[5] 版本校验指纹')
bad_fp = 0
for i, r in enumerate(recs):
    o, t, ln = rb[i]
    if ln != FP_LEN or t not in slots or face[o:o + ln] != EXPECT_FP[t:t + ln]:
        bad_fp += 1
ck(bad_fp == 0, '%d 条指纹都是 64 B 且 == %s镜像前 64 B'
   % (len(recs), '原厂' if ROLE == 'replace' else '改后'))
# 指纹必须不是"恒真"：至少要有记录真的不同
diff_fp = sum(1 for i, r in enumerate(recs) if stock_b[pay[i][1]:pay[i][1] + FP_LEN] !=
              patch_b[pay[i][1]:pay[i][1] + FP_LEN])
ck(diff_fp > 100, '%d/%d 条的"原厂前 64 B"与"改后前 64 B"确实不同（指纹有区分度）'
   % (diff_fp, len(recs)))

# ---------------------------------------------------------------- ⑥ 镜像完整性
print('\n[6] 改后镜像的完整性')
a = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in stock.entries()]
b = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in patched.entries()]
ck(a == b, 'inode 表（路径/偏移/next/spec/size/cksum）%d 条逐位不变' % len(a))
ck(stock.sb_size == patched.sb_size and stock.sb_cksum == patched.sb_cksum,
   'superblock 一致（size %d / cksum %08x）' % (patched.sb_size, patched.sb_cksum))
ck(stock.volume == patched.volume == 'health', '卷名 health 不变')
ck(len(stock_b) == len(patch_b), '分区长度不变（%d B）' % len(patch_b))
chg = [i for i in range(len(stock_b)) if stock_b[i] != patch_b[i]]
last_slot_end = max(o + slots[o][1] for o in slots)
ck(chg and chg[0] >= min(slots) and chg[-1] < last_slot_end,
   '改动只落在负载槽位区间内（首差 0x%x，末差 0x%x，槽位区间 0x%x..0x%x）'
   % (chg[0], chg[-1], min(slots), last_slot_end))
# 每个槽位都必须真的被改过（不是"看起来写了、其实字节没变"）
unchanged = [slots[o][0] for o in slots
             if stock_b[o:o + slots[o][1]] == patch_b[o:o + slots[o][1]]]
ck(not unchanged, '119 个槽位全部都真的写入了新字节（未变的槽位：%s）' % (unchanged or '无'))

# ---------------------------------------------------------------- ⑦ UI 图
print('\n[7] UI 图片')
uipairs = re.findall(r'\{(\d+),(\d+),"([a-z_]+)"\}', txt)
ck(len(uipairs) == 8, 'UIIMG 条目 %d 条（期望 8）' % len(uipairs))
badui = 0
for o, l, n in uipairs:
    blob = open(os.path.join(PROJ, 'ui_images', n + '.bin'), 'rb').read()
    if int(l) != len(blob) or face[int(o):int(o) + int(l)] != blob:
        badui += 1
ck(badui == 0, '8 张界面素材都与 ui_images/*.bin 逐字节一致')

# ---------------------------------------------------------------- 体积
print('\n[8] 体积')
ck(len(face) < 20 * 1048576, '交付物 %.2f MB < 20 MB' % (len(face) / 1048576))
print('      两张盘同 id：装一份就顶掉另一份，设备上只占一份空间')

print('\n' + '=' * 78)
print('%s：%d 项通过，%d 项失败' % (NAME, ok, fail))
if fail:
    sys.exit(1)
print('全部通过 —— %s（%d B，sha256 %s）'
      % (os.path.basename(FACE), len(face), hashlib.sha256(face).hexdigest()[:16]))
