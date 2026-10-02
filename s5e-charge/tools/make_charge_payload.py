# -*- coding: utf-8 -*-
"""把 S5 41mm(q63) 的充电动画搬进 S5 eSIM 46mm(p62lte) 的 /dev/system（逐帧等长覆盖）。

目标：inputs/target/vela_system.bin  charging/charge0..60.bin（**480x480** I8+RLE，61 帧）
源  ：inputs/source/vela_system.bin charging/charge0..60.bin（**464x464** I8+RLE，61 帧）
映射：**帧号 1:1（n -> n）**。S4e 那版是 57 帧按比例重采样（n -> round(n/56*60)），
      这一版两边都是 61 帧，**不要照抄那个比例** —— 逐帧对应才不会出现错帧/跳帧。

放大与编码策略（按优先级逐级降级，选第一条塞进槽位的）：
  1. 原调色板 + Lanczos：把源帧用 Lanczos 放大到 480x480（RGB），再把每个像素**吸附回源帧
     自己的调色板**（256 项里找最近的）。颜色只可能来自源帧的调色板 —— 空间上比最近邻放大
     平滑，颜色上零新增。实测 61/61 帧都塞得进，且体积与最近邻放大几乎一样（0.996x）。
  2. 原调色板 + Lanczos + 暗区合并：把亮度 < T 的像素全归到一个最暗的索引上换 RLE 长度，
     T 从小到大试（只影响接近黑的雾面区，亮环不动）。这是兜底，本项目实际没用上。
  3. 原调色板 + 最近邻索引放大（保底、无插值）。
  4. 整帧重新量化（颜色数从 256 逐级往下试）—— 最后兜底。

等长要点（这是命根子）：
  1) 数据总长必须**恰好**等于原槽位长度（ROMFS 后面所有偏移都是绝对值）
  2) 解码长度必须**恰好**等于 usize（少一字节设备端整帧不画；多一字节越界 -> INVALID）
     —— usize_tail 用「重复最后一个字节」补齐，正是因为踩过「RLE 输出比 usize 少 1 个像素」的坑
  3) pad_rle_safe 只用「产出 0 像素」的合法空指令（00 00 / 80）补齐到 csize
"""
import os, sys, json, struct, shutil, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import INPUTS, WORK, DOCS
from romfs import Romfs
import lvgl_bin as L
from PIL import Image
import numpy as np

STOCK = os.path.join(INPUTS, 'target', 'vela_system.bin')      # S5 eSIM 46mm (p62lte)
SOURCE = os.path.join(INPUTS, 'source', 'vela_system.bin')     # S5 41mm (q63)
OUTDIR = os.path.join(WORK, 'charge')
PATCHED = os.path.join(OUTDIR, 'vela_system_charge.bin')
DIRP = 'charging/'
W = H = 480
SAMPLE = None if (len(sys.argv) > 1 and sys.argv[1] == 'all') else [0, 14, 28, 42, 56]
THRS = (4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 96, 128, 192, 255)
FALLBACK_COLORS = (256, 192, 128, 96, 64, 48, 32)
DRAW_DOCS = True


def num_of(path):
    return int(path.rsplit('charge', 1)[-1].replace('.bin', ''))


def collect(rom):
    d = {}
    for p, i in rom.entries():
        if i.type == 1 or not p.startswith(DIRP) or not p.endswith('.bin'):
            continue
        d[num_of(p)] = (p, i, rom.read(i))
    return d


def decode_fast(blob):
    """(header, palette 256x4 BGRA, index HxW) —— 用库里的 rle_decompress，索引取出用 numpy。"""
    h = L.parse_header(blob)
    method, csize, usize = struct.unpack('<III', blob[12:24])
    raw = L.rle_decompress(blob[24:24 + csize], 1, usize)
    pal = np.frombuffer(raw[:1024], dtype=np.uint8).reshape(256, 4)
    st = max(h['stride'], h['w'])
    idx = np.frombuffer(raw[1024:1024 + st * h['h']], dtype=np.uint8).reshape(h['h'], st)[:, :h['w']]
    return h, pal, idx


src_indexed = decode_fast


def rgb_tab(pal):
    """(256,3) int32 RGB 表（调色板存的是 BGRA）。"""
    return pal[:, [2, 1, 0]].astype(np.int32)


def src_rgb(pal, idx):
    return rgb_tab(pal)[idx]


def lanczos_ref(pal, idx, w, h):
    """源帧 -> Lanczos 放大到 (w,h) 的 RGB（质量基准，也用于吸附）。"""
    im = Image.fromarray(src_rgb(pal, idx).astype(np.uint8), 'RGB').resize((w, h), Image.LANCZOS)
    return np.asarray(im, np.int32)


def snap(rgb, pal, chunk=8192):
    """每个像素在 256 项调色板里的最近色索引（欧氏距离，分块 brute force）。"""
    p = rgb_tab(pal)
    flat = rgb.reshape(-1, 3).astype(np.int32)
    out = np.empty(len(flat), np.uint8)
    for i in range(0, len(flat), chunk):
        d = flat[i:i + chunk, None, :] - p[None, :, :]
        out[i:i + chunk] = np.argmin((d * d).sum(axis=2), axis=1)
    return out.reshape(rgb.shape[:2])


def nn_idx(idx, w, h):
    """最近邻索引放大（不做任何插值）。"""
    sh, sw = idx.shape
    ys = np.clip(np.floor((np.arange(h) + 0.5) * sh / h).astype(np.int64), 0, sh - 1)
    xs = np.clip(np.floor((np.arange(w) + 0.5) * sw / w).astype(np.int64), 0, sw - 1)
    return idx[ys[:, None], xs[None, :]]


def dark_index(pal, idx, thr):
    """暗区里选一个代表索引：取其中颜色最暗的那个。"""
    vals = np.unique(idx[np.asarray(rgb_tab(pal)[idx].max(axis=2) < thr)])
    if len(vals) == 0:
        return None
    return int(vals[rgb_tab(pal)[vals].max(axis=1).argmin()])


def pal4(q):
    pal = list(q.getpalette() or []) + [0] * (768 - len(q.getpalette() or []))
    out = bytearray()
    for k in range(256):
        out += bytes((pal[k * 3 + 2], pal[k * 3 + 1], pal[k * 3], 255))
    return bytes(out)


def usize_tail(comp, raw_len, usize):
    """把「解码出来的裸字节数」补到恰好 usize。

    踩过的坑：RLE 输出比 usize **少一个像素**时设备端整帧不画。这里的补法是
    「再重复最后一个字节 N 次」（ctrl=N, unit=last）—— 视觉上只是把最后一个像素的
    游程延长，不会像补 0 那样在末尾画一条黑边；也不会多解（正好补齐 usize）。
    """
    short = usize - raw_len
    if short <= 0:
        return comp
    unit = comp[-1] if comp else 0
    ex = bytearray()
    while short > 0:
        n = min(short, 127)
        ex += bytes((n, unit))
        short -= n
    return comp + bytes(ex)


def encode_frame(pal, idx, w, h, csize, usize):
    """返回 (comp, idx_out, how)。comp 已补到「恰好解码出 usize 字节」。"""
    ref = lanczos_ref(pal, idx, w, h)
    # --- 1) 原调色板 + Lanczos 吸附（本项目 61/61 都走这条）
    cand_idx = snap(ref, pal)
    for thr in (0,) + THRS:
        if thr <= 0:
            i2 = cand_idx
        else:
            m = ref.max(axis=2) < thr
            if not m.any():
                i2 = cand_idx
            else:
                di = dark_index(pal, cand_idx, thr)
                i2 = cand_idx if di is None else np.where(m, di, cand_idx).astype(np.uint8)
        c = L.rle_compress(pal.tobytes() + i2.tobytes())
        c = usize_tail(c, 1024 + w * h, usize)
        if len(c) <= csize:
            how = '原调色板+Lanczos' if thr <= 0 else '原调色板+Lanczos+暗区<%d' % thr
            return c, i2, how
    # --- 2) 最近邻索引放大（无插值）
    i2 = nn_idx(idx, w, h)
    c = usize_tail(L.rle_compress(pal.tobytes() + i2.tobytes()), 1024 + w * h, usize)
    if len(c) <= csize:
        return c, i2, '原调色板+最近邻放大'
    # --- 3) 整帧重新量化，颜色数逐级往下
    for ncol in FALLBACK_COLORS:
        q = Image.fromarray(ref.astype(np.uint8), 'RGB').quantize(
            colors=ncol, method=Image.MEDIANCUT, dither=Image.NONE)
        i2 = np.asarray(q, np.uint8)
        c = usize_tail(L.rle_compress(pal4(q) + i2.tobytes()), 1024 + w * h, usize)
        if len(c) <= csize:
            return c, i2, '重新量化 %d 色' % ncol
    raise AssertionError('帧塞不进槽位（连 %d 色都不行）' % FALLBACK_COLORS[-1])


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    stock, src = Romfs(STOCK), Romfs(SOURCE)
    slots, srcs = collect(stock), collect(src)
    tl, sl = sorted(slots), sorted(srcs)
    print('目标 S5 eSIM(p62lte) %d 帧（%d..%d，槽位合计 %.2f MB）' % (
        len(tl), tl[0], tl[-1], sum(len(slots[n][2]) for n in tl) / 1048576))
    print('源   S5 41mm(q63)    %d 帧（%d..%d，%.2f MB）' % (
        len(sl), sl[0], sl[-1], sum(len(srcs[n][2]) for n in sl) / 1048576))
    assert tl == sl, '两边帧号不一致，不能做 1:1 覆盖'
    todo = tl if SAMPLE is None else [n for n in SAMPLE if n in slots]
    print('映射：n -> n（1:1）   本次要改的帧：%s' % todo)
    print('输出分辨率：%dx%d（源 464x464 -> Lanczos 放大后吸附回源调色板）\n' % (W, H))

    records, decode_ck, used, samples = [], 0, {}, []
    for n in todo:
        path, ino, blob = slots[n]
        h = L.parse_header(blob)
        w, ht, stride = h['w'], h['h'], max(h['stride'], h['w'])
        method, csize, usize = struct.unpack('<III', blob[12:24])
        assert len(blob) == 24 + csize, '槽位长度 != 24+csize'
        assert (w, ht) == (W, H), '目标槽位不是 %dx%d' % (W, H)
        assert usize == 1024 + w * ht, 'usize 不是 1024+w*h'
        sh, spal, sidx = src_indexed(srcs[n][2])
        assert (sh['w'], sh['h']) == (464, 464), '源帧不是 464x464'

        comp, idx_out, how = encode_frame(spal, sidx, w, ht, csize, usize)
        new = blob[:24] + L.pad_rle_safe(comp, csize)
        assert len(new) == len(blob), '替换负载长度 != 原槽位长度'
        assert len(comp) <= csize

        # 回解自检：① 解码长度恰好 usize ② 解出来的图与"计划写进去的图"逐像素一致
        hh, pal2, idx2 = decode_fast(new)
        raw_len = len(L.rle_decompress(new[24:24 + csize], 1, None))
        same = (idx2.shape == idx_out.shape) and bool((idx2 == idx_out).all())
        decode_ck += 1 if (same and raw_len == usize and (pal2 == spal).all()) else 0
        # 质量：与 Lanczos 放大基准比（吸附误差）+ 暗区误差
        ref = lanczos_ref(spal, sidx, w, ht)
        got = rgb_tab(spal)[idx_out]
        err = float(np.abs(got - ref).mean())
        dark = ref.max(axis=2) < 64
        e_dk = float(np.abs(got[dark] - ref[dark]).mean()) if dark.any() else 0.0
        used[how] = used.get(how, 0) + 1
        print('   帧 %-3d <- q63 第 %-3d 帧  槽位 %6d B  编码 %6d B（留白 %5d）  '
              'Lanczos 均差 %.3f（暗区 %.3f）  色数 %3d  %s'
              % (n, n, len(blob), len(comp), csize - len(comp), err, e_dk,
                 len(np.unique(idx_out)), how))
        records.append(dict(name='charge%d' % n, src='charge%d' % n, offset=ino.data_off,
                            length=len(blob), data=new, how=how, csize=len(comp),
                            slack=csize - len(comp), err=round(err, 4)))
        if n in (0, 20, 40, 60):
            samples.append((n, spal, sidx, idx_out))
    print('\n回解自检通过 %d / %d（解码长度恰好 usize 且逐像素等于计划图）' % (decode_ck, len(records)))
    print('编码方式分布：%s' % used)

    shutil.copyfile(STOCK, PATCHED)
    with open(PATCHED, 'r+b') as f:
        for r in records:
            f.seek(r['offset'])
            f.write(r['data'])
    json.dump(dict(device='Xiaomi Watch S5 eSIM 46mm (p62lte) vela_system.bin', target_dir=DIRP,
                   source='Xiaomi Watch S5 41mm (q63) charging frames (464x464)',
                   frames=len(records), size=[W, H], mapping='n -> n',
                   sample='all' if SAMPLE is None else SAMPLE,
                   image_sha256=hashlib.sha256(stock.data).hexdigest(),
                   records=[dict(name=r['name'], offset=r['offset'], length=r['length'],
                                 src=r['src'], how=r['how'], csize=r['csize']) for r in records]),
              open(os.path.join(OUTDIR, 'manifest.json'), 'w', encoding='utf-8'), indent=1,
              ensure_ascii=False)

    # ---------------- 整镜像级自证 ----------------
    r2 = Romfs(PATCHED)
    a = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in stock.entries()]
    b = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in r2.entries()]
    print('\ninode 表逐位不变：%s（%d 条）' % (a == b, len(a)))
    print('superblock 一致：%s（sb_size=%d / %d，sb_cksum=%d / %d）'
          % (stock.sb_size == r2.sb_size and stock.sb_cksum == r2.sb_cksum,
             stock.sb_size, r2.sb_size, stock.sb_cksum, r2.sb_cksum))
    sh = open(PATCHED, 'rb').read()
    print('回放（改后镜像 == 计划字节）：%s' % all(
        sh[r['offset']:r['offset'] + r['length']] == r['data'] for r in records))
    sa = np.frombuffer(stock.data, np.uint8)
    sb = np.frombuffer(sh, np.uint8)
    diff = np.nonzero(sa != sb)[0]
    inside = np.zeros(len(sa), dtype=bool)
    for r in records:
        inside[r['offset']:r['offset'] + r['length']] = True
    outside = int((~inside[diff]).sum()) if len(diff) else 0
    print('逐字节差异：共 %d 字节，全部落在 %d 个槽位内：%s（槽位外 %d 字节）'
          % (len(diff), len(records), outside == 0, outside))
    print('负载合计 %.2f MB；写出 %s' % (sum(r['length'] for r in records) / 1048576,
                                        os.path.join(OUTDIR, 'manifest.json')))
    if samples and DRAW_DOCS:
        draw_docs(samples)


def draw_docs(samples):
    """对照图：上排 q63 原帧（放大到 480 只为本机预览），下排改后镜像里解出来的 480x480。"""
    os.makedirs(DOCS, exist_ok=True)
    from PIL import ImageDraw
    cell = 240
    rows, cols = 2, len(samples)
    sheet = Image.new('RGB', (cols * (cell + 8) + 8, rows * (cell + 34) + 8), (28, 28, 32))
    d = ImageDraw.Draw(sheet)
    for i, (n, spal, sidx, idx_out) in enumerate(samples):
        top = Image.fromarray(src_rgb(spal, sidx).astype(np.uint8), 'RGB').resize(
            (cell, cell), Image.LANCZOS)
        bot = Image.fromarray(rgb_tab(spal)[idx_out].astype(np.uint8), 'RGB').resize(
            (cell, cell), Image.NEAREST)
        x = 8 + i * (cell + 8)
        sheet.paste(top, (x, 28))
        sheet.paste(bot, (x, 28 + cell + 26))
        d.text((x + 4, 8), 'q63 charge%d (464)' % n, fill=(200, 200, 200))
        d.text((x + 4, 28 + cell + 8), 'S5e charge%d (480)' % n, fill=(120, 220, 160))
    p = os.path.join(DOCS, 'before_after.png')
    sheet.save(p)
    print('对照图（上=源帧 下=改后解出）：%s' % p)


if __name__ == '__main__':
    main()
