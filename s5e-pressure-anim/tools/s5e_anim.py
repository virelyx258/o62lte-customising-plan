# -*- coding: utf-8 -*-
"""把 S5 41mm(q63) 的 `pressure/measure/Measuring1..100.bin`（480x480）逐帧等长写进
S5 eSIM(p62lte) `vela_health.bin` 的 `pressure/measure/Measuring1..119.bin`（464x464 I8+RLE）。

硬约束（为什么必须"逐字节等长"）
--------------------------------
ROMFS 里 `next` / `spec` 全是**绝对偏移**，文件数据又紧随 inode 之后；任何一条负载
长度变化 1 字节，后面所有文件的偏移就整体平移 → 分区报废。所以：

    12 B 头 + 12 B 压缩头 + csize  必须 == 原槽位长度
    csize 原样沿用（解码器按 csize 读），usize 原样沿用（= 1024 + 464*464 = 216321）

四步流水线
----------
  1) 解码 q63 帧 → 缩放到 464x464（**缩小**，LANCZOS）
  2) 暗部归零：q63 帧的"黑"其实是一条均匀的 #1a1a1a(26,26,26) 底噪 + 抖动噪声，
     实测占 68% 的像素、熵极高（256 色几乎全糊在暗部，不处理时 RLE 压不动：172 KB）。
     阈值以下的像素一律置 0，背景塌成整行单游程，体积掉到 1/4（~45 KB）。
  3) 量化：按一条**单调质量阶梯**（缩放比例 + 颜色数一起动）挑能塞进 csize 的最高档。
  4) LVGL RLE 压缩 → 先补「重复 N 次」把解码长度做到**正好 usize**，
     再用 `pad_rle_safe` 的合法空指令（00 00 / 80）补齐到 csize。

为什么用"质量单参数"而不是逐槽各自最优
--------------------------------------
槽位预算从 4.5 KB 到 196 KB 差 40 倍。逐帧各自最优会让相邻帧出现
「2 色 x0.32」跳到「4 色 x0.80」这种忽大忽小（S4e 那版踩过）。这里把
(颜色数, 缩放) 绑成一个连续量，先算每槽能撑住的最大档，再从峰值向两侧取
「运行最小值」—— 曲线单峰且平滑，画面尺寸/色阶随预算连续变化。

产出
----
  .work/anim/vela_health_anim.bin   改后镜像（长度 == 原镜像）
  .work/anim/manifest.json          逐条清单（偏移/长度/映射/降级/保留）
"""
import os, sys, json, struct, shutil, hashlib, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import (PROJ, INPUTS, WORK, TARGET_IMAGE, SOURCE_IMAGE, TARGET_VOLUME,
                   DIRP, FACE_W, FACE_H)
from romfs import Romfs
import lvgl_bin as L
from PIL import Image
import numpy as np

OUTDIR = os.path.join(WORK, 'anim')
PATCHED = os.path.join(OUTDIR, 'vela_health_anim.bin')
# 设备端解码器要求流解出的字节数**正好** == 头里的 usize。原厂 119 条全是 216321，
# 比"调色板 + 像素"多 1 字节（解码器只用到前 1024 + 464*464 字节，多出来的 1 字节
# 落在行外、被 `y < h` 挡掉，所以既安全又是原厂行为）。实测值由 build() 从镜像里读出来，
# 不在这儿写常量 —— 写错过一次（写成 216320）就被下面的断言当场抓住。
USIZE = 1024 + FACE_W * FACE_H          # 216320：调色板 + 像素；真实值以镜像为准
TAIL_EXTRA = 1                          # 期望的原厂尾部额外字节数
USIZE_EXTRA = TAIL_EXTRA                # 实际值由 build() 从镜像读出来后覆盖

# ------------------------------------------------------------------ 暗部归零
# q63 帧的底噪是 #1a1a1a(26)，球体最暗的实体像素也 >100。取 40 吃掉整片底噪与抖动，
# 又不动球体本体；56 作为第二档兜底（更狠，留给塞不下的槽位）。
DARK_LEVELS = (40, 56)

# ------------------------------------------------------------------ 固定调色板（低预算兜底）
# 到 8 色以下时"重新聚类"会把仅剩的颜色浪费在底噪残渣上、球体反而变花；
# 改用这几套手工调色板（索引 0 一定是黑），画面干净、也更好压。
FIXED_PALETTES = {
    2: [(0, 0, 0), (92, 132, 255)],
    3: [(0, 0, 0), (40, 60, 190), (120, 190, 255)],
    4: [(0, 0, 0), (28, 40, 150), (70, 120, 245), (140, 220, 210)],
    6: [(0, 0, 0), (18, 26, 110), (44, 66, 200), (80, 130, 250),
        (140, 200, 245), (150, 220, 160)],
    8: [(0, 0, 0), (12, 18, 80), (26, 38, 140), (46, 70, 195), (72, 110, 240),
        (110, 165, 252), (165, 215, 250), (150, 222, 168)],
}

# ------------------------------------------------------------------ 质量阶梯
# 从「最好」到「最省」单调排列：(缩放, 颜色数, 固定调色板色数|None)
LADDER = [
    (1.00, 256, None), (1.00, 192, None), (1.00, 128, None), (1.00, 96, None),
    (0.95, 96, None), (0.95, 64, None), (0.90, 64, None),
    (0.85, 64, None), (0.85, 48, None), (0.80, 48, None),
    (0.75, 48, None), (0.75, 32, None), (0.70, 32, None),
    (0.65, 32, None), (0.65, 24, None), (0.60, 24, None),
    (0.55, 24, None), (0.55, 16, None), (0.50, 16, None),
    (0.45, 16, None), (0.45, 12, None), (0.40, 12, None),
    (0.35, 12, None), (0.35, 8, 8), (0.30, 8, 8),
    (0.26, 6, 6), (0.22, 6, 6), (0.19, 4, 4), (0.16, 4, 4),
    (0.13, 3, 3), (0.11, 3, 3), (0.09, 2, 2), (0.07, 2, 2), (0.05, 2, 2),
]
CI_KEEP = len(LADDER)                    # 哨兵：连最省档都塞不下
# 平滑之后允许比目标档**大**多少缩放：0 表示只许更小。留一点余量是为了让球体尽量顶到
# 预算上限，同时不给相邻帧制造肉眼可见的尺寸跳变（每档缩放差约 0.05）。
SCALE_SLACK = 0.02


def num_of(path):
    return int(path.rsplit('Measuring', 1)[-1].replace('.bin', ''))


def collect(rom):
    d = {}
    for p, i in rom.entries():
        if i.type == 1 or not p.startswith(DIRP) or not p.endswith('.bin') or i.size == 0:
            continue
        d[num_of(p)] = (p, i, rom.read(i))
    return d


# ------------------------------------------------------------------ 编码原语
def palette_bytes(cols):
    """1024 B BGRA；索引 0 一定是黑，没用的条目留 0 —— 调色板本身也好压。"""
    out = bytearray(1024)
    for k, (r, g, b) in enumerate(cols[:256]):
        out[k * 4:k * 4 + 4] = bytes((b, g, r, 255))
    return bytes(out)


def kill_dark(img, dark):
    a = np.asarray(img.convert('RGB')).copy()
    a[a.max(axis=2) < dark] = 0
    return Image.fromarray(a, 'RGB')


def scale_image(img, sc):
    if sc >= 0.999:
        return img
    s = max(4, int(round(FACE_W * sc)))
    small = img.convert('RGBA').resize((s, s), Image.LANCZOS)
    cv = Image.new('RGBA', (FACE_W, FACE_H), (0, 0, 0, 255))
    cv.paste(small, ((FACE_W - s) // 2, (FACE_H - s) // 2))
    return cv


def quantize_raw(rgb, ncol, fixed):
    """-> 1024 B 调色板 + w*h 个索引（LVGL I8 的裸像素流）。

    自己实现量化，不再借 PIL 的调色板 API —— 这里踩过两个坑，留作警钟：
      ① 为了"保证索引 0 是黑"，先把图贴到 (W+8)x(H+8) 黑画布上再 quantize，
         然后 `q.tobytes()[:W*H]` 取像素。但 q 是 472 宽的，按 464 宽读就"每行错 8 列"，
         整幅图被剪成斜条纹 —— RLE 流完全正确、解出来也和"量化结果"逐点一致，
         只有拿"量化结果的形状"去比**源图**才抓得住（见 silhouette()）。
      ② 改成"循环移位调色板 + convert()/paste()"更糟：`quantize(palette=...)` 会把图重新
         合并成它自己算出来的调色板，`paste()` 又只搬调色板，于是 64 色时整幅图变纯黑。
      与其猜 PIL 的语义，不如把量化写成几行明确的 numpy。

    现在：黑单独占索引 0（背景因此塌成单游程），其余 ncol-1 个颜色在**非黑像素**上做
    加权 k-means（按出现次数加权，梯度才不会被子像素级的近似黑拖偏）。固定迭代次数 => 确定。
    """
    src = np.asarray(rgb if rgb.mode == 'RGB' else rgb.convert('RGB'))
    return quantize_arr(src, ncol, fixed)


def quantize_arr(src, ncol, fixed, cache=None, ckey=None):
    """量化主体。src 是 (H,W,3) uint8；ckey 用来复用同一帧的颜色表。

    性能关键（第一版在这里把机器跑爆过内存 1.7 GB / CPU 卡死）：
      * 源图有 1.5~2 万个不同颜色、21.5 万个像素。**质心只在"不同颜色"上算**，
        绝不在 21.5 万像素上做 (N, K, 3) 的距离广播
        （那一步就是 N=215296 x K=255 的模式，一个临时数组 1.6 GB）。
      * 像素 -> 索引 走一张**粗查色立方** LUT：先把 RGB 量化到 step 网格
        （step=4 时 64³ = 262144 个格子），只对这 26 万个格子算一次最近邻，
        再让 21.5 万像素直接查表。代价是"近似最近邻"（最大偏 step/2 = 2 个色阶），
        对 8 位调色板完全够用。
    """
    H, W = src.shape[:2]
    if cache is None:
        cache = {}
    ent = cache.get(ckey)
    if ent is None:
        flat = src.reshape(-1, 3)
        bg = flat.max(axis=1) == 0
        upix, inv = np.unique(flat, axis=0, return_inverse=True)
        upix = np.ascontiguousarray(upix, dtype=np.int32)
        inv = inv.reshape(-1).astype(np.int32)
        fg = np.nonzero(upix.max(axis=1) > 0)[0]
        ent = (upix, inv, fg, bg, flat.shape[0])
        cache[ckey] = ent
    upix, inv, fg, bg, npix = ent
    if len(fg) == 0:
        return palette_bytes([(0, 0, 0)]) + bytes(npix)
    if fixed is not None:
        cols = FIXED_PALETTES[fixed]
        out = _lut_index(upix, cols)[inv]
        out[bg] = 0
        # 背景必须落在索引 0（黑），这样 RLE 才是一条单游程
        if cols[0] != (0, 0, 0):
            raise ValueError('固定调色板的索引 0 必须是黑')
        return palette_bytes(cols) + out.tobytes()
    k = max(1, min(255, int(ncol) - 1))
    ufg = upix[fg]
    uq, cnt = np.unique(ufg, axis=0, return_counts=True)
    if len(uq) <= k:
        centers = uq.astype(np.float64)
    else:
        centers = uq[cnt.argsort()[::-1][:k]].astype(np.float64)   # 出现最多的 k 色做种子
        w = cnt.astype(np.float64)
        K = len(centers)
        for _ in range(8):
            lab = _nearest_argmin(uq, centers)
            new = centers.copy()
            for j in range(K):
                sel = lab == j
                if sel.any():
                    ww = w[sel][:, None]
                    new[j] = (uq[sel] * ww).sum(axis=0) / ww.sum()
            done = np.allclose(new, centers, atol=0.25)
            centers = new
            if done:
                break
    cols = [(0, 0, 0)] + [tuple(int(round(v)) for v in c) for c in centers]
    out = _lut_index(upix, cols)[inv]
    out[bg] = 0
    return palette_bytes(cols) + out.tobytes()


def _nearest_argmin(px, cent):
    """返回每个 px 最近的 cent 下标；只用 float32（int32 的立方广播会反复申请上百 MB）。"""
    a = np.asarray(px, dtype=np.float32)
    c = np.asarray(cent, dtype=np.float32)
    out = np.empty(len(a), dtype=np.int32)
    chunk = 8192
    for s in range(0, len(a), chunk):
        d = ((a[s:s + chunk, None, :] - c[None, :, :]) ** 2).sum(axis=2)
        out[s:s + chunk] = d.argmin(axis=1)
    return out


_GRID_CACHE = {}


def _cube_grid(step):
    """粗查色立方的网格代表色（只算一次，全局缓存）。

    展平顺序是 idx = r*(bins*bins) + g*bins + b —— 与 `meshgrid(indexing='ij')`
    + `reshape(-1,3)` 完全一致，所以立方体可以直接按这个公式索引。
    ★ 轴序写错会静默换色：查表必须用 (R,G,B) 顺序，写成 (B,G,R) 颜色就全串了。
    """
    g = _GRID_CACHE.get(step)
    if g is None:
        bins = 256 // step + 1
        ax = np.arange(bins, dtype=np.int32) * step
        grid = np.stack(np.meshgrid(ax, ax, ax, indexing='ij'), axis=-1).reshape(-1, 3)
        _GRID_CACHE[step] = (grid, bins)
        return _GRID_CACHE[step]
    return g


def _lut_index(px, cols):
    """像素 -> 最近调色板项，走粗查色立方 LUT。

    step=8 → 33³ = 35937 个格子，单通道最大偏差 step/2 = 4 个色阶；
    对这些低对比度、本来就带抖动的画面完全够用（step=4 的 26 万格子慢 8 倍）。
    用 float32 算距离：int32 的 (35937, 256, 3) 中间数组会反复申请 ~100 MB，
    是之前把内存跑到 2.6 GB、整体跑十几分钟的元凶。
    """
    grid, bins = _cube_grid(8)
    pal = np.asarray(cols, dtype=np.float32)
    best = np.empty(len(grid), dtype=np.uint8)
    gn = grid.astype(np.float32)
    chunk = 8192
    for s in range(0, len(grid), chunk):
        a = gn[s:s + chunk]
        d = ((a[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
        best[s:s + chunk] = d.argmin(axis=1).astype(np.uint8)
    q = np.clip((px.astype(np.int32) + 4) >> 3, 0, bins - 1)
    flat = (q[:, 0] * bins + q[:, 1]) * bins + q[:, 2]
    return best[flat]


def pad_to_usize(comp, raw_len):
    """解码长度必须**正好 == usize**，否则设备端解码器直接判失败、整帧不画。

    ★ 本会话踩过的坑：库里 rle_compress 的输出曾比 usize 少 1 个字节（末尾少一条指令）。
      这里显式补「重复 N 次」token 把长度做满。补出来的余数可能是奇数（原厂 usize 就是
      1024+464*464+1 = 216321，比"调色板+像素"多 1），所以最后允许一条「重复 1 次」的
      2 字节指令；`00 00`（重复 0 次）也是合法空指令。
    """
    short = USIZE - raw_len
    if short <= 0:
        return comp
    ex = bytearray()
    while short >= 2:
        k = min(short, 127)
        ex += bytes((k, 0))
        short -= k
    if short == 1:
        ex += bytes((1, 0))
    return comp + bytes(ex)


def encode_cell(img, cell, qcache=None, qkey=None):
    """(缩放, 颜色数, 固定) -> (RLE 流 bytes, 裸像素流 bytes)。不含 24 B 头。

    qkey 要带上**缩放比例**：同一帧的不同缩放是不同的数组，
    ★ 少了这个维度会让"不同颜色的表"永远命中不了缓存，每次都在 21.5 万像素上重算
      （第一版就是这样把内存跑到 1.7 GB、CPU 卡死的）。
    """
    sc, ncol, fixed = cell
    rgb = scale_image(img, sc).convert('RGB')
    raw = quantize_arr(np.asarray(rgb), ncol, fixed, qcache,
                       (qkey, sc) if qkey is not None else None)
    return pad_to_usize(L.rle_compress(raw), len(raw)), raw


def raw_to_rgb(raw):
    """把裸像素流还原成 RGB 图（用于"解出来的像素 == 量化结果"这条自证）。"""
    pal = bytearray(768)
    for i in range(256):
        pal[i * 3 + 0] = raw[i * 4 + 2]
        pal[i * 3 + 1] = raw[i * 4 + 1]
        pal[i * 3 + 2] = raw[i * 4 + 0]
    im = Image.frombytes('P', (FACE_W, FACE_H), raw[1024:1024 + FACE_W * FACE_H])
    im.putpalette(bytes(pal))
    return im.convert('RGB')


def silhouette(raw):
    """(非黑像素数, bbox) —— 用来挡住"字节完全自洽、内容却整片错位"这类 bug。

    ★ 这里就是因为只比字节、不比形状，差点放过去一版"斜条纹"图：
      当时 quantize 是按 472 宽取的像素，读成 464 宽 → 每行错 8 列 → 整幅图被剪成斜条纹。
      RLE 流本身完全正确、解出来的像素也和"量化结果"逐点一致，所以只有把
      "量化结果"再和**源图**比形状才抓得住。下面这个函数就是干这个的。
    """
    a = np.asarray(raw_to_rgb(raw))
    m = a.max(axis=2) > 24
    n = int(m.sum())
    if not n:
        return 0, None
    ys, xs = np.nonzero(m)
    return n, (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max()))


# ------------------------------------------------------------------ 主流程
def build():
    t0 = time.time()
    global USIZE, USIZE_EXTRA
    os.makedirs(OUTDIR, exist_ok=True)
    stock, src = Romfs(TARGET_IMAGE), Romfs(SOURCE_IMAGE)
    if stock.volume != TARGET_VOLUME:
        raise SystemExit('目标镜像卷名是 %r，期望 %r —— 拿错分区了？'
                         % (stock.volume, TARGET_VOLUME))
    slots, srcs = collect(stock), collect(src)
    tl, sl = sorted(slots), sorted(srcs)
    h0 = L.parse_header(slots[tl[0]][2])
    print('目标槽位 %d 个（Measuring%d..Measuring%d，合计 %.2f MB）' % (
        len(tl), tl[0], tl[-1], sum(len(slots[n][2]) for n in tl) / 1048576))
    print('源帧     %d 个（Measuring%d..Measuring%d，合计 %.2f MB）' % (
        len(sl), sl[0], sl[-1], sum(len(srcs[n][2]) for n in sl) / 1048576))
    print('槽位格式 %dx%d cf=0x%02x flags=0x%02x stride=%d' % (
        h0['w'], h0['h'], h0['cf'], h0['flags'], h0['stride']))
    assert (h0['w'], h0['h']) == (FACE_W, FACE_H), '槽位不是 %dx%d' % (FACE_W, FACE_H)
    assert (h0['cf'], h0['flags']) == (0x0a, 0x08), '槽位不是 I8 + RLE'
    # ★ usize 从镜像里读出来，别写常量：原厂是 1024 + 464*464 + 1 = 216321
    n_usize = {struct.unpack('<III', slots[n][2][12:24])[2] for n in tl}
    print('原厂 usize 取值集合：%s' % sorted(n_usize))
    assert len(n_usize) == 1, '原厂 usize 不唯一：%s' % sorted(n_usize)
    USIZE = n_usize.pop()
    USIZE_EXTRA = USIZE - (1024 + FACE_W * FACE_H)
    print('usize = %d（= 1024 + %d*%d + %d）' % (USIZE, FACE_W, FACE_H, USIZE_EXTRA))
    assert USIZE_EXTRA == TAIL_EXTRA, \
        '尾部额外字节是 %d，与预期的 %d 不符 —— 先确认原厂流到底多几个字节' % (USIZE_EXTRA, TAIL_EXTRA)
    # 原厂 119 条都要真的能解出正好 usize
    bad_stock = [n for n in tl
                 if len(L.rle_decompress(slots[n][2][24:24 + struct.unpack('<III', slots[n][2][12:24])[1]],
                                         1, None)) != USIZE]
    print('原厂 %d 条解码长度 == usize：%s' % (len(tl), not bad_stock))
    assert not bad_stock, '原厂就有解不出 usize 的槽位：%s' % bad_stock[:8]

    # ---- 逐源帧解码 + 缩放 + 暗部归零（100 帧只做一次）----
    frames = {}
    for n in sl:
        _, im = L.decode_lvgl_bin(srcs[n][2])
        im = im.convert('RGBA').resize((FACE_W, FACE_H), Image.LANCZOS)
        frames[n] = {d: kill_dark(im, d) for d in DARK_LEVELS}
    print('解码 + 缩放 %d 帧：%.1fs' % (len(sl), time.time() - t0))

    # 映射与 S4e 版一致：第 k 个槽位(k=0..118) <- q63 第 round(k/(119-1)*(100-1))+1 帧
    def qn_for(k):
        return sl[round(k / (len(tl) - 1) * (len(sl) - 1))]

    cells = {}                                # (src_n, dark, ci) -> (comp, raw)
    src_sils = {}                             # (src_n, dark, ci) -> (非黑像素数, bbox)
    qcache = {}

    def get_cell(src_n, dark, ci):
        key = (src_n, dark, ci)
        v = cells.get(key)
        if v is None:
            v = encode_cell(frames[src_n][dark], LADDER[ci], qcache, (src_n, dark))
            cells[key] = v
            src_sils[key] = silhouette(v[1])
        return v

    def fits(src_n, dark, ci, csize):
        return len(get_cell(src_n, dark, ci)[0]) <= csize

    # ---- 第一遍：逐槽量出「能塞进 csize 的最大阶梯档」----
    caps = []
    for k, n in enumerate(tl):
        csize = struct.unpack('<III', slots[n][2][12:24])[1]
        src_n = qn_for(k)
        best = None
        for dark in DARK_LEVELS:
            for ci in range(len(LADDER)):
                if fits(src_n, dark, ci, csize):
                    best = (ci, dark)
                    break
            if best:
                break
        caps.append(best if best else (CI_KEEP, DARK_LEVELS[0]))
    n_keep = sum(1 for c, _d in caps if c == CI_KEEP)
    print('第一遍完成：%d/%d 槽位能编出 ≤ csize 的流，%d 个连最省档都不行（耗时 %.0fs）'
          % (len(tl) - n_keep, len(tl), n_keep, time.time() - t0))

    # ---- 平滑：从峰值向两侧取「运行最小值」----
    ordered = [c for c, _d in caps]
    peak = ordered.index(max(ordered))
    sm = list(ordered)
    for i in range(peak - 1, -1, -1):
        sm[i] = min(sm[i], sm[i + 1])
    for i in range(peak + 1, len(sm)):
        sm[i] = min(sm[i], sm[i - 1])
    jumps = [abs(sm[i + 1] - sm[i]) for i in range(len(sm) - 1)]
    print('阶梯曲线（每 6 帧采样）：%s' % ' '.join(str(sm[i]) for i in range(0, len(sm), 6)))
    print('相邻帧最大跳变：%d 档' % (max(jumps) if jumps else 0))

    # ---- 第二遍：以平滑档位为目标，在预算里挑**画面最大**的那一档；塞不下就往更省的档退 ----
    # 「挑画面最大」而不是「挑第一个能塞下的」：平滑只限制相邻帧的尺寸变化幅度，
    # 不该让它浪费槽位。实测按"第一个能塞下的"走，尾部几帧会把 7~12 万字节的 csize
    # 只用掉一半（全填 00 00 空指令），球体白白小一圈。
    records, degrade, kept, decode_ok, stat = [], [], [], 0, []
    for k, n in enumerate(tl):
        path, ino, blob = slots[n]
        method, csize, usize = struct.unpack('<III', blob[12:24])
        src_n = qn_for(k)
        start = sm[k]
        # 先按档位从优到劣扫一遍，记下所有塞得下的格子，再选缩放最大/颜色最多的那个
        best = None
        if start < CI_KEEP:
            for ci in range(start, len(LADDER)):
                for dark in DARK_LEVELS:
                    if fits(src_n, dark, ci, csize):
                        # 平滑约束：缩放不能比目标档大太多（否则相邻帧会忽大忽小），
                        # 但可以更小；颜色数不受约束（只影响色阶，不影响尺寸）
                        if LADDER[ci][0] <= LADDER[start][0] + SCALE_SLACK:
                            sc_i, ncol_i, fx_i = LADDER[ci]
                            key = (sc_i, ncol_i)
                            if best is None or key > best[1]:
                                best = ((ci, dark), key)
        rec_name = '%03d_%s_%d' % (len(records), path.rsplit('/', 1)[-1][:-4], n)
        if best is None:
            kept.append((n, csize))
            records.append(dict(name=rec_name, src='measure%d' % src_n, offset=ino.data_off,
                                length=len(blob), data=blob, csize=csize, how='保留原厂',
                                ci=None, dark=None, scale=1.0, colors=0, pad=0, enc=0))
            print('  !! 槽 %d（csize %d）塞不下 -> 保留原厂' % (n, csize))
            continue
        (ci, dark), _key = best
        comp, raw = get_cell(src_n, dark, ci)
        new = blob[:12] + struct.pack('<III', method, csize, usize) + L.pad_rle_safe(comp, csize)
        assert len(new) == len(blob), (len(new), len(blob))
        # ★ 就地自证三道：
        #   ① 解出来正好 usize 字节（少一字节设备端就整帧不画）
        #   ② 解出来的像素 == 量化结果（逐点）
        #   ③ 量化结果的**形状**和源图在同一量级（挡住"字节自洽但内容错位"的 bug）
        # 第③条的容差：低色阶档位下球体边缘的暗像素会被并到最暗的那一档、显得略小
        # （4 色/2 色时尤其明显），所以只要求非黑像素数在 ±6% 内、bbox 每边差 ≤12 像素；
        # 真正"斜条纹"那种错位会让 bbox 直接铺满全画幅，这条一定抓得住。
        back = L.rle_decompress(new[24:24 + csize], 1, None)
        _, dec = L.decode_lvgl_bin(new)
        same = dec is not None and dec.convert('RGB').tobytes() == raw_to_rgb(raw).tobytes()
        src_sil = src_sils[(src_n, dark, ci)]
        got_sil = silhouette(raw)
        sil_ok = (src_sil[1] is not None and got_sil[1] is not None and
                  abs(src_sil[0] - got_sil[0]) <= 0.06 * max(1, src_sil[0]) and
                  max(abs(a - b) for a, b in zip(src_sil[1], got_sil[1])) <= 12)
        if len(back) == usize and same and sil_ok:
            decode_ok += 1
        else:
            print('  !! 槽 %d：解码 %d 字节（应 %d），像素一致=%s，形状合理=%s（%s vs %s）'
                  % (n, len(back), usize, same, sil_ok, src_sil, got_sil))
        stat.append((n, csize, len(comp), csize - len(comp)))
        sc, ncol, fixed = LADDER[ci]
        how = ('固定%d色' % fixed if fixed is not None else '%d色' % ncol)
        how += '' if sc >= 0.995 else ' 缩放%.2f' % sc
        how += ' 暗部<%d' % dark
        if ci > start:
            degrade.append((n, csize, start, ci, how))
            how += ' [平滑目标第%d档放不下，退到第%d档]' % (start, ci)
        records.append(dict(name=rec_name, src='measure%d' % src_n, offset=ino.data_off,
                            length=len(blob), data=new, csize=csize, how=how, ci=ci,
                            dark=dark, scale=round(sc, 4), colors=ncol, fixed=fixed,
                            pad=csize - len(comp), enc=len(comp), target_ci=start))

    # ---- 写出镜像 + 清单 ----
    shutil.copyfile(TARGET_IMAGE, PATCHED)
    with open(PATCHED, 'r+b') as f:
        for r in records:
            f.seek(r['offset'])
            f.write(r['data'])
    manifest = dict(
        device='Xiaomi Watch S5 eSIM 46mm (p62lte)',
        partition='vela_health.bin  volume=health  device node=/dev/health',
        source='Xiaomi Watch S5 41mm (q63, v4.101.020) pressure/measure frames',
        target_dir=DIRP,
        mapping='第 k 个槽位(k=1..%d) <- q63 第 round((k-1)/(%d-1)*(%d-1))+1 帧(1..%d)'
                % (len(tl), len(tl), len(sl), len(sl)),
        face_wh=[FACE_W, FACE_H], slot_count=len(tl), source_count=len(sl), usize=USIZE,
        image_sha256=hashlib.sha256(stock.data).hexdigest(),
        ladder=[dict(ci=i, scale=c[0], colors=c[1], fixed=c[2]) for i, c in enumerate(LADDER)],
        records=[dict(name=r['name'], offset=r['offset'], length=r['length'],
                      src=r['src'], how=r['how'], ci=r['ci'], dark=r['dark'],
                      scale=r['scale'], colors=r['colors'], fixed=r['fixed'],
                      pad=r['pad'], enc=r['enc'], target_ci=r['target_ci'],
                      csize=r['csize']) for r in records],
        kept_stock=[dict(n=n, csize=c, name=slots[n][0]) for n, c in kept],
        degraded=[dict(n=n, csize=c, from_ci=a, to_ci=b, how=h) for n, c, a, b, h in degrade])
    json.dump(manifest, open(os.path.join(OUTDIR, 'manifest.json'), 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False)

    # ---- 汇总 ----
    print('\n阶梯使用情况（颜色数, 缩放, 暗部 -> 帧数）：')
    used = {}
    for r in records:
        if r['ci'] is None:
            continue
        k2 = (r['colors'], r['scale'], r['dark'])
        used[k2] = used.get(k2, 0) + 1
    for kk, v in sorted(used.items(), key=lambda kv: (-kv[0][1], -kv[0][0])):
        print('   %3d 色 缩放%.2f 暗部<%d -> %3d 帧' % (kk[0], kk[1], kk[2], v))
    print('   保留原厂：%d 帧 %s' % (len(kept), [n for n, _ in kept]))
    print('   平滑目标档放不下、被迫退档：%d 帧 %s'
          % (len(degrade), [(n, h) for n, _c, _a, _b, h in degrade][:8]))
    pads = [p[3] for p in stat]
    print('   槽位填充：实际用掉 %.1f%% 的 csize（填充 min %d / max %d / 平均 %.0f B，'
          '全是合法空指令 00 00 / 80）'
          % (100.0 * sum(p[2] for p in stat) / sum(p[1] for p in stat),
             min(pads), max(pads), sum(pads) / len(pads)))
    print('   回解自证：正好 usize 且像素一致 %d / %d' % (decode_ok, len(records) - len(kept)))

    # ---- 独立自证 ----
    r2 = Romfs(PATCHED)
    a = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in stock.entries()]
    b = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in r2.entries()]
    print('\ninode 表逐位不变：%s（%d 条）' % (a == b, len(a)))
    print('superblock 一致：%s（size %d / cksum %08x）' % (
        stock.sb_size == r2.sb_size and stock.sb_cksum == r2.sb_cksum,
        r2.sb_size, r2.sb_cksum))
    print('镜像长度一致：%s（%d B）' % (len(stock.data) == len(r2.data), len(r2.data)))
    sh = open(PATCHED, 'rb').read()
    replay = all(sh[r['offset']:r['offset'] + r['length']] == r['data'] for r in records)
    print('回放（改后镜像 == 计划字节）：%s' % replay)
    lens_ok = all(r['length'] == len(slots[int(r['name'].rsplit('_', 1)[1])][2]) for r in records)
    print('每条负载长度 == 原槽位长度：%s' % lens_ok)
    print('\n负载合计 %.2f MB；耗时 %.0fs；写出 %s'
          % (sum(r['length'] for r in records) / 1048576, time.time() - t0,
             os.path.join(OUTDIR, 'manifest.json')))
    return manifest


if __name__ == '__main__':
    only = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if only not in ('all', 'replace', 'restore'):
        raise SystemExit('用法: s5e_anim.py [all|replace|restore]')
    build()
