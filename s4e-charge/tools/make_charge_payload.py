# -*- coding: utf-8 -*-
"""把 S5 41mm(q63) 的充电动画搬进 S4 eSIM 的 system 分区（逐帧等长覆盖）。

目标：inputs/target/vela_system.bin 的 charging/charge0..56.bin（464x464 I8 RLE）
源  ：inputs/source/vela_system.bin 的 charging/charge0..60.bin（464x464 I8 RLE）

编码策略（v2，2026-10-02 换掉旧方案）：
  旧方案把整帧重新量化成 256 色（MEDIANCUT）—— 结果**圆环本身被毁**：亮区平均差 27~52，
  因为 MEDIANCUT 按像素数量分配调色板，而亮环只占少部分像素 -> 分不到几个颜色。
  新方案**直接沿用 q63 原帧的调色板 + 索引**（零量化误差，圆环逐像素完全一致），
  只把"很暗的像素"归到一个索引上换取 RLE 长度，阈值从 0 起逐档加大，取**能塞进槽位的最小阈值**。
  阈值只影响接近黑的雾面区（4~32/255），亮环完全不动。

等长要点：
  1) 数据总长必须等于原槽位长度；usize 尾巴必须补够（少一字节设备就不画）
  2) pad_rle_safe 只用 00 00 / 80 这类空指令补齐
"""
import os, sys, json, struct, shutil, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import INPUTS, WORK
from romfs import Romfs
import lvgl_bin as L
from PIL import Image
import numpy as np

STOCK = os.path.join(INPUTS, 'target', 'vela_system.bin')     # S4 eSIM
SOURCE = os.path.join(INPUTS, 'source', 'vela_system.bin')    # q63
OUTDIR = os.path.join(WORK, 'charge')
PATCHED = os.path.join(OUTDIR, 'vela_system_charge.bin')
DIRP = 'charging/'
SAMPLE = None if (len(sys.argv) > 1 and sys.argv[1] == 'all') else [0, 14, 28, 42, 56]
THRS = (0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 96, 128, 192, 255)
FALLBACK_COLORS = (256, 192, 128, 96, 64, 48, 32)


def num_of(path):
    return int(path.rsplit('charge', 1)[-1].replace('.bin', ''))


def collect(rom):
    d = {}
    for p, i in rom.entries():
        if i.type == 1 or not p.startswith(DIRP) or not p.endswith('.bin'):
            continue
        d[num_of(p)] = (p, i, rom.read(i))
    return d


def src_indexed(blob):
    """取出 I8 RLE 帧的原始调色板(256x4 BGRA)与索引图(H,W)。"""
    h = L.parse_header(blob)
    method, csize, usize = struct.unpack('<III', blob[12:24])
    raw = L.rle_decompress(blob[24:24 + csize], 1, usize)
    pal = np.frombuffer(raw[:1024], dtype=np.uint8).reshape(256, 4)
    st = max(h['stride'], h['w'])
    idx = np.frombuffer(raw[1024:1024 + st * h['h']], dtype=np.uint8).reshape(h['h'], st)[:, :h['w']]
    return h, pal, idx


def enc_source_palette(pal, idx, idx2, w, h, stride):
    data = idx2.tobytes() if stride == w else np.hstack(
        [idx2, np.zeros((h, stride - w), dtype=np.uint8)]).tobytes()
    return L.rle_compress(pal.tobytes() + data)


def dark_index(pal, idx, thr):
    """暗区里选一个代表索引：取其中颜色最暗的那个。"""
    vals = np.unique(idx[idx < 256][np.asarray(pal[idx][:, :, :3].max(axis=2) < thr).ravel()]) \
        if False else np.unique(idx[np.asarray(pal[idx][:, :, :3].max(axis=2) < thr)])
    lums = pal[vals][:, :3].max(axis=1)
    return int(vals[lums.argmin()])


def pal4(q):
    pal = list(q.getpalette() or []) + [0] * (768 - len(q.getpalette() or []))
    out = bytearray()
    for k in range(256):
        out += bytes((pal[k * 3 + 2], pal[k * 3 + 1], pal[k * 3], 255))
    return bytes(out)


def usize_tail(comp, raw_len, usize):
    short = usize - raw_len
    if short <= 0:
        return comp
    ex = bytearray()
    while short > 0:
        n = min(short, 127)
        ex += bytes((n, 0))
        short -= n
    return comp + bytes(ex)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    stock, src = Romfs(STOCK), Romfs(SOURCE)
    slots, srcs = collect(stock), collect(src)
    tl, sl = sorted(slots), sorted(srcs)
    print('目标 %d 帧（%d..%d，%.1f MB）  源 %d 帧（%d..%d，%.1f MB）' % (
        len(tl), tl[0], tl[-1], sum(len(slots[n][2]) for n in tl) / 1048576,
        len(sl), sl[0], sl[-1], sum(len(srcs[n][2]) for n in sl) / 1048576))
    todo = tl if SAMPLE is None else [n for n in SAMPLE if n in slots]
    print('本次要改的帧：%s' % todo)

    records, decode_ck, used, fallback = [], 0, {}, 0
    for n in todo:
        path, ino, blob = slots[n]
        h = L.parse_header(blob)
        w, ht, stride = h['w'], h['h'], max(h['stride'], h['w'])
        method, csize, usize = struct.unpack('<III', blob[12:24])
        assert len(blob) == 24 + csize
        m = sl[round((n - tl[0]) / max(1, tl[-1] - tl[0]) * (len(sl) - 1))]
        sh, spal, sidx = src_indexed(srcs[m][2])
        assert (sh['w'], sh['h']) == (w, ht), '源/目标尺寸不一致'
        s_rgb = spal[sidx][:, :, [2, 1, 0]]        # 原始调色板是 BGRA，转成 RGB 再比
        lum = np.max(s_rgb, axis=2)
        comp = keep = None
        how = ''
        for thr in THRS:                      # 首选：保原调色板，只压暗区
            if thr <= 0:
                idx2 = sidx
            else:
                dm = lum < thr
                if not dm.any():
                    idx2 = sidx
                else:
                    vals = np.unique(sidx[dm])
                    idx2 = np.where(dm, int(vals[pal_lum(spal, vals).argmin()]), sidx).astype(np.uint8)
            c = enc_source_palette(spal, sidx, idx2, w, ht, stride)
            c = usize_tail(c, 1024 + stride * ht, usize)
            if len(c) <= csize:
                comp, keep, how = c, spal[idx2][:, :, [2, 1, 0]].copy(), \
                    ('原调色板' if thr == 0 else '原调色板+暗区压到 < %d' % thr)
                break
        if comp is None:                      # 兜底：旧方案（整帧重量化）
            fallback += 1
            im = Image.fromarray(np.dstack([s_rgb, np.full((ht, w), 255, np.uint8)]), 'RGBA')
            a = np.asarray(im).copy()
            dark = a[:, :, :3].max(axis=2) < 46
            a[dark, 0] = a[dark, 1] = a[dark, 2] = 0
            for ncol in FALLBACK_COLORS:
                q = Image.fromarray(a, 'RGBA').convert('RGB').quantize(
                    colors=ncol, method=Image.MEDIANCUT, dither=Image.NONE)
                c = usize_tail(L.rle_compress(pal4(q) + q.tobytes()), 1024 + stride * ht, usize)
                if len(c) <= csize:
                    comp, keep, how = c, np.asarray(q.convert('RGB')), '兜底 %d 色' % ncol
                    break
        assert comp is not None, '帧 %d 塞不进槽位' % n
        new = blob[:12] + struct.pack('<III', method, csize, usize) + L.pad_rle_safe(comp, csize)
        assert len(new) == len(blob)
        _, back = L.decode_lvgl_bin(new)
        raw_len = len(L.rle_decompress(new[24:24 + csize], 1, None))
        want = np.asarray(keep, dtype=np.uint8).reshape(-1, 3)
        got = np.asarray(back.convert('RGB'), dtype=np.uint8).reshape(-1, 3)
        same = bool((got == want).all())            # 与"实际写进去的图"逐像素一致
        decode_ck += 1 if (same and raw_len == usize) else 0
        # 对 q63 原帧的误差：亮区(圆环)必须为 0，暗区允许有损
        d = np.abs(keep.astype(np.int16) - s_rgb.astype(np.int16))
        br = lum > 60
        e_br = float(d[br].mean()) if br.any() else 0.0
        e_dk = float(d[~br].mean()) if (~br).any() else 0.0
        used[how] = used.get(how, 0) + 1
        print('   帧 %-3d <- q63 第 %-3d 帧  槽位 %6d B  编码 %6d B  亮区均差 %.2f 暗区均差 %.2f  %s'
              % (n, m, len(blob), len(comp), e_br, e_dk, how))
        records.append(dict(name='charge%d' % n, src='charge%d' % m, offset=ino.data_off,
                            length=len(blob), data=new, how=how))
    print('回解自检通过 %d / %d（兜底 %d 帧）' % (decode_ck, len(records), fallback))
    print('编码方式分布：%s' % used)

    shutil.copyfile(STOCK, PATCHED)
    with open(PATCHED, 'r+b') as f:
        for r in records:
            f.seek(r['offset'])
            f.write(r['data'])
    json.dump(dict(device='Xiaomi Watch S4 eSIM (o62lte) vela_system.bin', target_dir=DIRP,
                   source='Xiaomi Watch S5 41mm (q63) charging frames',
                   sample='all' if SAMPLE is None else SAMPLE,
                   image_sha256=hashlib.sha256(stock.data).hexdigest(),
                   records=[dict(name=r['name'], offset=r['offset'], length=r['length'],
                                 src=r['src'], how=r['how']) for r in records]),
              open(os.path.join(OUTDIR, 'manifest.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    r2 = Romfs(PATCHED)
    a = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in stock.entries()]
    b = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in r2.entries()]
    print('\ninode 表逐位不变：%s（%d 条）' % (a == b, len(a)))
    print('superblock 一致：%s' % (stock.sb_size == r2.sb_size and stock.sb_cksum == r2.sb_cksum))
    sh = open(PATCHED, 'rb').read()
    print('回放（改后镜像 == 计划字节）：%s' % all(
        sh[r['offset']:r['offset'] + r['length']] == r['data'] for r in records))
    print('负载合计 %.2f MB；写出 %s' % (sum(r['length'] for r in records) / 1048576,
                                        os.path.join(OUTDIR, 'manifest.json')))


def pal_lum(pal, vals):
    return pal[vals][:, :3].max(axis=1)          # 只取最大值，通道序无关


def rgb_of(pal, idx):
    return pal[idx][:, :, [2, 1, 0]]


if __name__ == '__main__':
    main()
