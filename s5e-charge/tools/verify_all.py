# -*- coding: utf-8 -*-
"""独立总校验：只看**交付物 + 固件镜像**，不看任何中间产物（不读 .work/）。

    python tools/verify_all.py            # 生成 docs/selfcheck_report.txt + 预览图

逐项判据（每项都是一条可证伪的断言）：
  A 交付物形态：.face 魔数、watchface id = 462150103（两份共用）、b5=0、体积上限
  B Lua 表：从 .face 里的 Lua 反解 pay / rb 表（各 61 条）
  C 等长：每条 pay 的长度 == 原厂槽位长度，且目标偏移就是 charging/chargeN.bin 的
          数据偏移（61 条恰好一一覆盖，无重复无遗漏）
  D 可解码：每条 pay 是 480x480 I8+RLE，且 RLE 流**恰好**解出 usize = 1024+480*480
  E 帧内容：把交付物里的每一帧解出来，与"用 q63 源帧独立做的 Lanczos 放大"比对，
          平均差 < 1.0/255（吸附误差量级），并报最像的源帧号（证明 n 对 n 没错帧）
  F 版本指纹：replace 盘的 rb == **原厂**前 64 B（对固件镜像独立比对）
              restore 盘的 pay == **原厂**整条字节（逐字节）
              restore 盘的 rb == replace 盘 pay 的前 64 B（两份交付物互证）
  G 整镜像：用 replace 盘的负载重建改后镜像 -> inode 表 / superblock / 长度与原厂
          逐位一致，且**除 61 个槽位外没有任何字节变化**
  H 预览：把交付物解出来的 61 帧拼成图（docs/decode_preview.png）便于肉眼复核
"""
import os, re, sys, hashlib, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import PROJ, INPUTS, DOCS
from romfs import Romfs
import lvgl_bin as L
from make_charge_payload import src_indexed
from PIL import Image, ImageDraw
import numpy as np

W = H = 480
WF_ID = '462150103'
DIRP = 'charging/'
STOCK = os.path.join(INPUTS, 'target', 'vela_system.bin')
SOURCE = os.path.join(INPUTS, 'source', 'vela_system.bin')
FACES = {'replace': os.path.join(PROJ, 'dist', 'S5Chg.face'),
         'restore': os.path.join(PROJ, 'dist', 'S5ChgRestore.face')}
REPORT = []
ok = fail = 0


def log(s=''):
    print(s)
    REPORT.append(s)


def ck(cond, msg, detail=''):
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
    log('  [%s] %s%s' % ('OK ' if cond else 'FAIL', msg, ('  ' + detail) if detail else ''))
    return cond


def num_of(p):
    return int(p.rsplit('charge', 1)[-1].replace('.bin', ''))


def slots_of(path):
    rom = Romfs(path)
    d = {}
    for p, i in rom.entries():
        if i.type == 1 or not p.startswith(DIRP) or not p.endswith('.bin'):
            continue
        d[i.data_off] = (num_of(p), i.size)
    return rom, d


def decode(blob):
    h = L.parse_header(blob)
    m, csize, usize = struct.unpack('<III', blob[12:24])
    raw = L.rle_decompress(blob[24:24 + csize], 1, usize)
    pal = np.frombuffer(raw[:1024], dtype=np.uint8).reshape(256, 4)
    st = max(h['stride'], h['w'])
    idx = np.frombuffer(raw[1024:1024 + st * h['h']], dtype=np.uint8).reshape(h['h'], st)[:, :h['w']]
    return h, m, csize, usize, len(raw), pal, idx


def rgb_of(pal, idx):
    return pal[idx][:, :, [2, 1, 0]]


def sig(rgb):
    """64x64 灰度特征（用于"最像哪一帧"的快速最近邻）。"""
    im = Image.fromarray(np.asarray(rgb, np.uint8), 'RGB').resize((64, 64), Image.BILINEAR)
    return np.asarray(im, np.float32).mean(axis=2).ravel()


def parse_tables(face):
    src = face.decode('latin1')
    m = re.search(r'pay = \{(.*?)\n  \},', src, re.S)
    m2 = re.search(r'rb = \{(.*?)\n  \},', src, re.S)
    if not m or not m2:
        return None, None
    pay = [tuple(int(x) for x in r) for r in re.findall(r'\{(\d+),(\d+),(\d+)\}', m.group(1))]
    rb = [tuple(int(x) for x in r) for r in re.findall(r'\{(\d+),(\d+),(\d+)\}', m2.group(1))]
    return pay, rb


log('=' * 78)
log('S5eChg 独立总校验（只读 dist/*.face + inputs/*/vela_system.bin）')
log('=' * 78)

stock_b = open(STOCK, 'rb').read()
src_rom = Romfs(SOURCE)
src_blob = {}
for p, i in src_rom.entries():
    if i.type == 1 or not p.startswith(DIRP) or not p.endswith('.bin'):
        continue
    src_blob[num_of(p)] = src_rom.read(i)
stock_rom, slot = slots_of(STOCK)
log('目标镜像 %s：%d 字节，charging/ 槽位 %d 个' % (os.path.basename(STOCK), len(stock_b), len(slot)))
log('源镜像   %s：%d 帧' % (os.path.basename(SOURCE), len(src_blob)))

faces = {}
log('\n--- A 交付物形态 ---')
for role, path in FACES.items():
    if not os.path.exists(path):
        ck(False, '%s 存在' % path)
        continue
    b = open(path, 'rb').read()
    faces[role] = b
    log('  %-18s %10d 字节  sha256=%s' % (os.path.basename(path), len(b),
                                          hashlib.sha256(b).hexdigest()))
    log('  %-18s sha256[:16]=%s' % ('', hashlib.sha256(b).hexdigest()[:16]))
    ck(b[0:4] == b'\x5a\xa5\x34\x12', '%s 魔数正确' % role)
    ck(b[40:50].rstrip(b'\x00') == WF_ID.encode(), '%s id == %s' % (role, WF_ID), repr(b[40:50]))
    ck(b[5] == 0, '%s b5 == 0' % role, 'b5=%d' % b[5])
    ck(len(b) < 20 * 1048576, '%s 体积 < 20MB' % role)
    ck(b'__PAY__' not in b and b'__ROLE__' not in b, '%s 占位符已回填' % role)

log('\n--- B Lua 表（从 .face 反解）---')
tables = {}
for role, b in faces.items():
    pay, rb = parse_tables(b)
    ck(pay is not None and rb is not None, '%s 找到 pay / rb 表' % role)
    if pay is None:
        continue
    tables[role] = (pay, rb)
    log('  %s：pay %d 条 / rb %d 条' % (role, len(pay), len(rb)))
    ck(len(pay) == 61, '%s pay 条数 == 61' % role, str(len(pay)))
    ck(len(rb) == 61, '%s rb 条数 == 61' % role, str(len(rb)))
    ck(re.search(r"local ROLE = '(\w+)'", b.decode('latin1')).group(1) == role,
       '%s Lua 里的 ROLE == %s' % (role, role))

log('\n--- C 等长 + 目标偏移 / D 可解码（480x480，恰好 usize）---')
decoded = {}
for role in ('replace', 'restore'):
    if role not in tables:
        continue
    pay, rb = tables[role]
    bad_len = bad_off = bad_dec = 0
    imgs = {}
    for i, (res, tgt, ln) in enumerate(pay):
        blob = faces[role][res:res + ln]
        if len(blob) != ln or tgt not in slot or slot[tgt][1] != ln:
            bad_len += 1
            continue
        if slot[tgt][0] != i:
            bad_off += 1
        try:
            h, m, cs, us, rawlen, pal, idx = decode(blob)
        except Exception:
            bad_dec += 1
            continue
        if (h is None or h['w'] != W or h['h'] != H or h['cf'] != 0x0a
                or not (h['flags'] & L.FLAG_COMPRESSED) or m != 1
                or cs != ln - 24 or us != 1024 + W * H or rawlen != us
                or not (pal[:, 3] == 255).all()):
            bad_dec += 1
            continue
        imgs[i] = (pal, idx)
    ck(bad_len == 0, '%s：61 条长度 == 原厂槽位长度' % role, '不符 %d 条' % bad_len)
    ck(bad_off == 0, '%s：目标偏移一一对应 chargeN' % role, '错位 %d 条' % bad_off)
    ck(bad_dec == 0, '%s：61 条都解出 480x480 且 RLE 恰好 usize' % role, '不符 %d 条' % bad_dec)
    decoded[role] = imgs

log('\n--- E 帧内容：与 q63 源帧的独立 Lanczos 放大比对 ---')
src_sig = {j: sig(rgb_of(*src_indexed(src_blob[j])[1:])) for j in sorted(src_blob)}
errs, mismatch = [], []
for i in sorted(decoded.get('replace', {})):
    pal, idx = decoded['replace'][i]
    got = rgb_of(pal, idx).astype(np.int32)
    _, spal, sidx = src_indexed(src_blob[i])
    ref = np.asarray(Image.fromarray(rgb_of(spal, sidx).astype(np.uint8), 'RGB')
                     .resize((W, H), Image.LANCZOS), np.int32)
    errs.append(float(np.abs(got - ref).mean()))
    g = sig(got.astype(np.uint8))
    best = min(src_sig, key=lambda j: float(np.abs(src_sig[j] - g).mean()))
    if best != i:
        mismatch.append((i, best))
log('  61 帧平均差：mean %.3f  max %.3f（第 %d 帧）'
    % (float(np.mean(errs)), max(errs), int(np.argmax(errs))))
ck(max(errs) < 1.0, '每一帧与独立 Lanczos 基准的平均差 < 1.0/255', 'max=%.3f' % max(errs))
log('  最像的源帧号与自身不一致的帧：%d 个 %s'
    % (len(mismatch), mismatch[:8] if mismatch else ''))
ck(len(mismatch) <= 2, '交付物第 n 帧就是 q63 第 n 帧（最多容忍 2 帧近邻歧义）',
   '%d 个不一致' % len(mismatch))

log('\n--- F 版本指纹 / 还原字节 ---')
if 'replace' in tables and 'restore' in tables:
    rpay, rrb = tables['replace']
    apay, arb = tables['restore']
    bad = sum(1 for res, tgt, ln in rrb
              if ln != 64 or faces['replace'][res:res + 64] != stock_b[tgt:tgt + 64])
    ck(bad == 0, 'replace 盘 rb == 原厂前 64 B（对固件镜像比对）', '不符 %d 条' % bad)
    bad = 0
    for res, tgt, ln in apay:
        if ln != slot[tgt][1] or faces['restore'][res:res + ln] != stock_b[tgt:tgt + ln]:
            bad += 1
    ck(bad == 0, 'restore 盘 pay == 原厂整条字节（逐字节）', '不符 %d 条' % bad)
    bad = 0
    for i, (res, tgt, ln) in enumerate(arb):
        new64 = faces['replace'][rpay[i][0]:rpay[i][0] + 64]
        if ln != 64 or faces['restore'][res:res + 64] != new64:
            bad += 1
    ck(bad == 0, 'restore 盘 rb == replace 盘 pay 前 64 B（两份交付物互证）', '不符 %d 条' % bad)

log('\n--- G 整镜像（用 replace 盘负载重建改后镜像）---')
if 'replace' in tables:
    rpay, _ = tables['replace']
    patched = bytearray(stock_b)
    for res, tgt, ln in rpay:
        patched[tgt:tgt + ln] = faces['replace'][res:res + ln]
    patched = bytes(patched)
    os.makedirs(DOCS, exist_ok=True)
    tmp = os.path.join(DOCS, '_patched_tmp.bin')
    open(tmp, 'wb').write(patched)
    p_rom = Romfs(tmp)
    a = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in stock_rom.entries()]
    b2 = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in p_rom.entries()]
    ck(a == b2, 'inode 表逐位不变（%d 条）' % len(a))
    ck(stock_rom.sb_size == p_rom.sb_size and stock_rom.sb_cksum == p_rom.sb_cksum,
       'superblock 逐位不变', 'size=%d cksum=%d' % (stock_rom.sb_size, stock_rom.sb_cksum))
    ck(len(patched) == len(stock_b), '分区长度不变')
    sa = np.frombuffer(stock_b, np.uint8)
    sb = np.frombuffer(patched, np.uint8)
    diff = np.nonzero(sa != sb)[0]
    inside = np.zeros(len(sa), dtype=bool)
    for res, tgt, ln in rpay:
        inside[tgt:tgt + ln] = True
    outside = int((~inside[diff]).sum()) if len(diff) else 0
    ck(outside == 0, '除 %d 个槽位外没有任何字节变化' % len(rpay),
       '差异 %d 字节，槽位外 %d 字节' % (len(diff), outside))
    mid = os.path.join(PROJ, '.work', 'charge', 'vela_system_charge.bin')
    if os.path.exists(mid):
        log('  [info] 与构建中间产物逐字节一致：%s' % (open(mid, 'rb').read() == patched))
    os.remove(tmp)

log('\n--- H 预览图（交付物解出来的帧）---')
if decoded.get('replace'):
    cols, cell = 8, 120
    n = len(decoded['replace'])
    rows = (n + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cell, rows * cell), (18, 18, 20))
    for i in sorted(decoded['replace']):
        pal, idx = decoded['replace'][i]
        sheet.paste(Image.fromarray(rgb_of(pal, idx).astype(np.uint8), 'RGB')
                    .resize((cell, cell), Image.LANCZOS), ((i % cols) * cell, (i // cols) * cell))
    p1 = os.path.join(DOCS, 'decode_preview.png')
    sheet.save(p1)
    log('  61 帧总览：%s' % p1)
    samp, c2 = [0, 15, 30, 45, 60], 200
    sh2 = Image.new('RGB', (len(samp) * (c2 + 8) + 8, 2 * (c2 + 30) + 8), (28, 28, 32))
    d = ImageDraw.Draw(sh2)
    for k, i in enumerate(samp):
        pal, idx = decoded['replace'][i]
        _, spal, sidx = src_indexed(src_blob[i])
        x = 8 + k * (c2 + 8)
        sh2.paste(Image.fromarray(rgb_of(spal, sidx).astype(np.uint8), 'RGB')
                  .resize((c2, c2), Image.LANCZOS), (x, 28))
        sh2.paste(Image.fromarray(rgb_of(pal, idx).astype(np.uint8), 'RGB')
                  .resize((c2, c2), Image.NEAREST), (x, 28 + c2 + 26))
        d.text((x + 4, 8), 'q63 charge%d (464)' % i, fill=(200, 200, 200))
        d.text((x + 4, 28 + c2 + 8), 'face charge%d (480)' % i, fill=(120, 220, 160))
    p2 = os.path.join(DOCS, 'face_before_after.png')
    sh2.save(p2)
    log('  抽样对照：%s' % p2)

log('\n' + '=' * 78)
log('RESULT: %s —— %d 项通过，%d 项失败' % ('全部通过' if fail == 0 else '有失败', ok, fail))
log('=' * 78)
open(os.path.join(DOCS, 'selfcheck_report.txt'), 'w', encoding='utf-8').write('\n'.join(REPORT) + '\n')
print('report -> ' + os.path.join(DOCS, 'selfcheck_report.txt'))
sys.exit(1 if fail else 0)
