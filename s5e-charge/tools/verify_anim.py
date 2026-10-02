# -*- coding: utf-8 -*-
"""独立校验交付的 .face（只看交付物 + 固件镜像，不看中间产物）。

  role: replace -> dist/S5Chg.face        pay 应等于**改后镜像**的字节，fp 应等于**原厂**前 64 B
        restore -> dist/S5ChgRestore.face pay 应等于**原厂**字节，   fp 应等于**改后镜像**前 64 B
  ① 从 .face 里抠出 Lua 表（pay / rb），按表里的偏移取字节
  ② 每条 pay 长度必须 == 原厂槽位长度（等长覆盖的底线），且能按 LVGL RLE 解出 480x480
  ③ rb 每条必须是 64 B 指纹，且等于另一侧字节的前 64 B（版本校验数据正确）
  ④ 目标镜像的 inode 表 / superblock / 分区长度与原厂逐位一致
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import PROJ, INPUTS, WORK
from romfs import Romfs
import lvgl_bin as L

ROLE = (sys.argv[1] if len(sys.argv) > 1 else 'replace').lower()
NAME = 'S5Chg' if ROLE == 'replace' else 'S5ChgRestore'
FACE = os.path.join(PROJ, 'dist', NAME + '.face')
STOCK = os.path.join(INPUTS, 'target', 'vela_system.bin')
PATCHED = os.path.join(WORK, 'charge', 'vela_system_charge.bin')
DIRP = 'charging/'
FP_LEN = 64
ok = fail = 0


def ck(cond, msg):
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        print('   !! ' + msg)


face = open(FACE, 'rb').read()
src = face.decode('latin1')
m = re.search(r'pay = \{(.*?)\n  \},', src, re.S)
m2 = re.search(r'rb = \{(.*?)\n  \},', src, re.S)
ck(m is not None and m2 is not None, '在 .face 里找不到 pay / rb 表')
pay = [tuple(int(x) for x in r) for r in re.findall(r'\{(\d+),(\d+),(\d+)\}', m.group(1))]
rb = [tuple(int(x) for x in r) for r in re.findall(r'\{(\d+),(\d+),(\d+)\}', m2.group(1))]
print('%s：pay %d 条，rb %d 条' % (NAME, len(pay), len(rb)))

stock_b = open(STOCK, 'rb').read()
patch_b = open(PATCHED, 'rb').read()
c = re.search(r"local ROLE = '(\w+)'", src)
ck(c is not None and c.group(1) == ROLE, 'Lua 里的 ROLE 不是 %s' % ROLE)
EXPECT_PAY = patch_b if ROLE == 'replace' else stock_b
EXPECT_FP = stock_b if ROLE == 'replace' else patch_b
stock = Romfs(STOCK)
slots = {}
for p, i in stock.entries():
    if i.type == 1 or not p.startswith(DIRP) or not p.endswith('.bin') or i.size == 0:
        continue
    slots[i.data_off] = (p, i.size)

canary = [r for r in pay if r[1] == 0 and r[2] == 32]
ck(len(canary) <= 1, 'canary 记录不止一条')
if canary:
    ck(face[canary[0][0]:canary[0][0] + 32] == stock_b[:32], 'canary 不对')
data = [r for r in pay if not (r[1] == 0 and r[2] == 32)]
bad_len = bad_dec = bad_bytes = 0
for o, t, ln in data:
    blob = face[o:o + ln]
    if t not in slots or slots[t][1] != ln:
        bad_len += 1; continue
    if EXPECT_PAY[t:t + ln] != blob:
        bad_bytes += 1
    h = L.parse_header(blob)
    if h is None or not (h['flags'] & L.FLAG_COMPRESSED) or h['w'] != 480 or h['h'] != 480:
        bad_dec += 1; continue
    # ★ 设备端解码器要求流解出**正好 usize 字节**（1024 + w*h + 1），少一字节就整帧不画
    import struct as _s
    _m, _cs, _us = _s.unpack('<III', blob[12:24])
    if len(L.rle_decompress(blob[24:24 + _cs], 1, None)) != _us:
        bad_dec += 1; continue
    try:
        if L.decode_lvgl_bin(blob)[1] is None:
            bad_dec += 1
    except Exception:
        bad_dec += 1
ck(bad_len == 0, '有 %d 条长度 != 原厂槽位长度' % bad_len)
ck(bad_dec == 0, '有 %d 条解不出 480x480' % bad_dec)
ck(bad_bytes == 0, '有 %d 条 != %s 的字节' % (bad_bytes, '改后镜像' if ROLE == 'replace' else '原厂镜像'))
print('  pay 检查 %d 条：长度全对 %s，可解码 %s，字节与%s一致 %s'
      % (len(data), bad_len == 0, bad_dec == 0, '改后镜像' if ROLE == 'replace' else '原厂镜像', bad_bytes == 0))

bad_fp = 0
for o, t, ln in rb:
    if ln == 0 or (t == 0 and ln == 32):      # canary 那条的指纹是空表
        continue
    if ln != FP_LEN or t not in slots or face[o:o + ln] != EXPECT_FP[t:t + ln]:
        bad_fp += 1
ck(bad_fp == 0, '有 %d 条指纹不对（应为另一侧前 64 B）' % bad_fp)
print('  rb 指纹 %d 条：全部 64 B 且与另一侧一致 %s' % (len(rb), bad_fp == 0))

p2 = Romfs(PATCHED)
a = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in stock.entries()]
b = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in p2.entries()]
ck(a == b, 'inode 表变了')
ck(stock.sb_size == p2.sb_size and stock.sb_cksum == p2.sb_cksum, 'superblock 变了')
ck(len(stock_b) == len(patch_b), '分区长度变了')
ck(len(face) < 20 * 1048576, '交付物体积异常：%d B' % len(face))
print('\n%s —— %d 项通过，%d 项失败' % ('全部通过' if fail == 0 else '有失败', ok, fail))
sys.exit(1 if fail else 0)
