# -*- coding: utf-8 -*-
"""S5 41mm(q63) 的压力检测动画 -> S4 eSIM 的 pressure/measure 槽位（等长覆盖）。

硬约束：ROMFS 里文件数据长度固定（后面所有文件的偏移都是绝对值），所以 119 个槽位
必须**逐字节等长**替换；而目标槽位是 464x464 I8 且 **RLE 压缩**，源（q63）是 480x480。
于是走三步：
  1) q63 帧缩放/量化：按 (颜色数, 缩放比例) 阶梯找一档，让编码结果 <= 槽位 csize
  2) 编码：LVGL RLE 语法（lvgl_bin.rle_compress）
  3) 补齐：ctrl=0 的空指令补到 csize（lvgl_bin.pad_rle）—— 解码器读完 csize 字节
     既不会越界也不会多出像素
文件总长 = 12(头) + 12(压缩头) + csize = 原槽位长度 ✓（头里的 csize/usize/method 原样沿用）
"""
import os, sys, json, struct, shutil, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import INPUTS, WORK
from romfs import Romfs
import lvgl_bin as L
from PIL import Image, ImageDraw
import numpy as np

STOCK = os.path.join(INPUTS, 'target', 'vela_app.bin')      # S4 eSIM 原厂
SOURCE = os.path.join(INPUTS, 'source', 'vela_app.bin')     # q63（S5 41mm）
OUTDIR = os.path.join(WORK, 'anim')
PATCHED = os.path.join(OUTDIR, 'vela_app_anim.bin')
DIRP = 'pressure/measure/'

# 从「最清晰」往「最省字节」排；缩放 <1 时把画面缩小居中（四周纯黑，RLE 大幅变短）
# ------------------------------------------------------------------ 比例怎么定
# 之前用「离散阶梯」逐档试：相邻两帧的预算只差一点，却可能一档跳到 0.6、下一帧跳到 0.22 —— 真机上就是
# 「忽大忽小」。现在改成：**由槽位预算直接算出连续的比例**，球体大小随预算平滑变化。
#
#   464x464 的 I8 图，光是全黑背景就要 FLOOR ≈ 3.7 KB（RLE 单游程上限 127 -> 一行至少 4 个 token）；
#   球体本身的开销大致正比于「直径^1.57」（实测拟合），满尺寸 32 色约 BALL ≈ 41.6 KB。
#   于是  scale = ((csize - FLOOR) / BALL) ^ (1/1.57)，截到 [0.03, 1.0]。
FLOOR = 3700.0
BALL = 41600.0
POW = 1.57
TARGET_COLORS = (256, 192, 128, 96, 64, 48, 32)
MIN_COLORS = 32
KEEP_STOCK_IF_TOO_TIGHT = False      # 用户要求：一帧都不保留原厂


def plan_scale(csize):
    b = max(0.0, csize - FLOOR)
    return min(1.0, max(0.03, (b / BALL) ** (1.0 / POW)))


def num_of(path):
    return int(path.rsplit('Measuring', 1)[-1].replace('.bin', ''))


def collect(rom, prefix):
    d = {}
    for p, i in rom.entries():
        if i.type == 1 or not p.startswith(prefix) or not p.endswith('.bin'):
            continue
        d[num_of(p)] = (p, i, rom.read(i))
    return d


def usize_tail(comp, raw_len, usize):
    """补「重复 N 次」token 把解码长度凑到 usize（原厂流解出的正是 usize，少一字节设备就不画）。"""
    short = usize - raw_len
    if short <= 0:
        return comp
    ex = bytearray()
    while short > 0:
        n = min(short, 127)
        ex += bytes((n, 0))
        short -= n
    return comp + bytes(ex)


def pal4(q):
    pal = list(q.getpalette() or [])
    pal += [0] * (768 - len(pal))
    out = bytearray()
    for k in range(256):
        out += bytes((pal[k * 3 + 2], pal[k * 3 + 1], pal[k * 3], 255))
    return bytes(out)


def encode(img, w, h, ncol, scale):
    im = img
    if scale != 1.0:
        s = max(8, int(round(w * scale)))
        small = img.convert('RGBA').resize((s, s), Image.LANCZOS)
        cv = Image.new('RGBA', (w, h), (0, 0, 0, 255))
        cv.paste(small, ((w - s) // 2, (h - s) // 2))
        im = cv
    q = im.convert('RGB').quantize(colors=max(1, ncol), method=Image.MEDIANCUT, dither=Image.NONE)
    return L.rle_compress(pal4(q) + q.tobytes()), q


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    stock, src = Romfs(STOCK), Romfs(SOURCE)
    slots, srcs = collect(stock, DIRP), collect(src, DIRP)
    tl, sl = sorted(slots), sorted(srcs)
    print('目标槽位 %d 个（编号 %d..%d，合计 %.1f MB）' % (
        len(tl), tl[0], tl[-1], sum(len(slots[n][2]) for n in tl) / 1048576))
    print('源帧     %d 个（编号 %d..%d，合计 %.1f MB）' % (
        len(sl), sl[0], sl[-1], sum(len(srcs[n][2]) for n in sl) / 1048576))
    h0 = L.parse_header(slots[tl[0]][2])
    print('槽位格式 %dx%d cf=0x%02x flags=0x%02x method=%d' % (
        h0['w'], h0['h'], h0['cf'], h0['flags'],
        struct.unpack('<I', slots[tl[0]][2][12:16])[0]))

    # ---- 两遍法：① 先量出每帧「≥32 色能撑住的最大比例」cap ② 从峰值向外取「运行最小」得到单峰平滑曲线 ----
    # 这样球体尺寸连续（不会忽大忽小），同时每个槽位都还保得住 32 色以上（不会色阶断层）。
    caps = []
    src_cache = {}
    for k, n in enumerate(tl):
        path, ino, blob = slots[n]
        h = L.parse_header(blob)
        w, ht = h['w'], h['h']
        method, csize, usize = struct.unpack('<III', blob[12:24])
        qn = sl[round(k / max(1, len(tl) - 1) * (len(sl) - 1))]
        if qn not in src_cache:
            _, im = L.decode_lvgl_bin(srcs[qn][2])
            big = im.convert('RGBA').resize((w, ht), Image.LANCZOS)
            a = np.asarray(big).copy()
            dark = a[:, :, :3].max(axis=2) < 40
            a[dark, 0] = a[dark, 1] = a[dark, 2] = 0
            src_cache[qn] = Image.fromarray(a, 'RGBA')
        simg = src_cache[qn]
        # 二分找「≥32 色还能塞下的最大比例」—— 比离散档细得多，曲线因此近乎连续
        lo, hi = 0.02, 1.0
        for _ in range(8):
            mid = (lo + hi) / 2.0
            comp, _q = encode(simg, w, ht, 32, mid)
            comp = usize_tail(comp, 1024 + w * ht, usize)
            if len(comp) <= csize:
                lo = mid
            else:
                hi = mid
        caps.append(lo)
    peak = caps.index(max(caps))
    sm = list(caps)
    for i in range(peak - 1, -1, -1):
        sm[i] = min(sm[i], sm[i + 1])
    for i in range(peak + 1, len(sm)):
        sm[i] = min(sm[i], sm[i - 1])
    adj = [abs(sm[i + 1] - sm[i]) for i in range(len(sm) - 1)]
    print('比例曲线（每 6 帧采样）：%s' % ' '.join('%.3f' % sm[i] for i in range(0, len(sm), 6)))
    print('相邻帧比例最大跳变：%.3f' % max(adj))

    records, decode_ck, used, kept = [], 0, {}, []
    placeholder = 0
    for k, n in enumerate(tl):
        path, ino, blob = slots[n]
        h = L.parse_header(blob)
        w, ht = h['w'], h['h']
        method, csize, usize = struct.unpack('<III', blob[12:24])
        qn = sl[round(k / max(1, len(tl) - 1) * (len(sl) - 1))]
        simg = src_cache[qn]
        base = sm[k]
        chosen = None
        for ncol in (256, 192, 128, 96, 64, 48, 32):
            comp, q = encode(simg, w, ht, ncol, base)
            comp = usize_tail(comp, 1024 + w * ht, usize)
            if len(comp) <= csize:
                chosen = (ncol, base, comp, q)
                break
        if chosen is None:
            for s_try in (base * 0.9, base * 0.8, base * 0.7, base * 0.6, base * 0.5):
                for ncol in (24, 16, 12, 8, 6, 4, 3, 2):
                    comp, q = encode(simg, w, ht, ncol, s_try)
                    comp = usize_tail(comp, 1024 + w * ht, usize)
                    if len(comp) <= csize:
                        chosen = (ncol, s_try, comp, q)
                        break
                if chosen:
                    break
        if chosen is None:
            comp2 = usize_tail(L.rle_compress(bytes(bytearray(1024)) + bytes(w * ht)), 1024 + w * ht, usize)
            if len(comp2) <= csize:
                chosen = (0, 0.0, comp2, None)
                placeholder += 1
        if chosen is None:
            kept.append((n, csize))
            new, tag = blob, 'keep'
        else:
            ncol, sc, comp, q = chosen
            new = blob[:12] + struct.pack('<III', method, csize, usize) + L.pad_rle_safe(comp, csize)
            assert len(new) == len(blob)
            used[(ncol, round(sc, 2))] = used.get((ncol, round(sc, 2)), 0) + 1
            tag = '%d色%s' % (ncol, '' if sc >= 0.995 else ' 缩放%.2f' % sc)
            _, back = L.decode_lvgl_bin(new)
            raw_len = len(L.rle_decompress(new[24:24 + csize], 1, None))
            if q is not None:
                same = list(back.convert('RGB').getdata()) == list(q.convert('RGB').getdata())
            else:
                same = all(pp[:3] == (0, 0, 0) for pp in back.convert('RGB').getdata())
            if same and raw_len == usize:
                decode_ck += 1
            else:
                print('  !! 槽 %d：解码长度 %d（应 %d）或像素不一致' % (n, raw_len, usize))
        records.append(dict(name='%03d_%s_%d' % (len(records), path.rsplit('/', 1)[-1][:-4], n),
                            src='measure%d' % qn, offset=ino.data_off, length=len(blob),
                            data=new, csize=csize, how=tag))
    print('\n阶梯使用情况（颜色数, 缩放 -> 帧数）：')
    for kk, v in sorted(used.items(), key=lambda kv: -kv[1]):
        print('   %3d 色 %s -> %3d 帧' % (kk[0], 'x1.00' if kk[1] == 1.0 else 'x%.2f' % kk[1], v))
    if placeholder:
        print('   全透明兜底（也绝不留原厂）：%d 帧' % placeholder)
    if kept:
        print('   !! 仍保留原厂：%d 帧 %s' % (len(kept), kept[:8]))
    print('   回解逐像素一致：%d / %d' % (decode_ck, len(records) - len(kept)))

    shutil.copyfile(STOCK, PATCHED)
    with open(PATCHED, 'r+b') as f:
        for r in records:
            f.seek(r['offset'])
            f.write(r['data'])
    manifest = dict(
        device='Xiaomi Watch S4 eSIM (o62lte) vela_app.bin',
        source='Xiaomi Watch S5 41mm (q63) v4.101.020 pressure/measure frames',
        target_dir=DIRP,
        mapping='第 i 个槽位(1..%d) <- q63 第 round((i-1)/(n-1)*(m-1))+1 帧(1..%d)' % (len(tl), len(sl)),
        image_sha256=hashlib.sha256(stock.data).hexdigest(),
        records=[dict(name=r['name'], offset=r['offset'], length=r['length'],
                      src=r['src'], how=r['how']) for r in records])
    json.dump(manifest, open(os.path.join(OUTDIR, 'manifest.json'), 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False)

    # 自证：inode 表逐位不变 + 回放一致
    r2 = Romfs(PATCHED)
    a = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in stock.entries()]
    b = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in r2.entries()]
    print('\ninode 表逐位不变：%s（%d 条）' % (a == b, len(a)))
    print('superblock 一致：%s' % (stock.sb_size == r2.sb_size and stock.sb_cksum == r2.sb_cksum))
    sh = open(PATCHED, 'rb').read()
    replay = all(sh[r['offset']:r['offset'] + r['length']] == r['data'] for r in records)
    print('回放（改后镜像 == 计划字节）：%s' % replay)
    print('负载合计 %.2f MB；写出 %s' % (
        sum(r['length'] for r in records) / 1048576, os.path.join(OUTDIR, 'manifest.json')))


if __name__ == '__main__':
    main()
