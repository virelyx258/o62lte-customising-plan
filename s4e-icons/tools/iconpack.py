"""Build / apply a system-app launcher-icon replacement for a Vela `vela_app.bin`.

Why "same length" is the whole ball game
----------------------------------------
ROMFS packs superblock -> inode -> name -> file data strictly back to back, and
every `next` / `spec` pointer is an ABSOLUTE offset.  If a replacement file
changes length by even one byte, every later offset shifts and the image is
corrupt.  So a replacement must encode to EXACTLY the original byte length:

  * source PNG == original dimensions  -> encode, lengths match, done.
  * source PNG != original dimensions  -> two options:
      (default) resize to the original dimensions  (icon renders identically)
      --pad     keep the source dimensions, zero-pad the container to the
                original length (renders smaller unless the launcher scales)

Usage:
  iconpack.py list    <vela_app.bin>
  iconpack.py make    <vela_app.bin> <pngdir> <outdir> [--pad] [--patched]
  iconpack.py apply   <vela_app.bin> <patch.bin> <out.bin>
"""
import os, sys, json, struct, hashlib, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romfs import Romfs, img_header
from lvgl_bin import rle_compress, pad_rle
from PIL import Image

CF_ARGB8888, CF_I8, MAGIC = 0x10, 0x0a, 0x19
FMT = {CF_ARGB8888: 'ARGB8888', CF_I8: 'I8'}
RESAMPLE = Image.LANCZOS


# ----------------------------------------------------------------- encoders
def encode_argb8888(img):
    rgba = img.convert('RGBA')
    w, h = rgba.size
    px = rgba.load()
    out = bytearray()
    for y in range(h):
        row = bytearray()
        for x in range(w):
            r, g, b, a = px[x, y]
            row += bytes((b, g, r, a))
        out += row
    return bytes(out)


def encode_i8(img, alpha_levels=16, sharpen_up=0.0):
    """I8 encoder with an ALPHA-AWARE palette.

    The naive version quantised RGB only and then stored one *averaged* alpha
    per palette entry.  Any colour shared by an opaque body pixel and a
    semi-transparent edge pixel collapsed to a mid alpha, and fully transparent
    pixels inherited that same entry -- so the transparent margin became faintly
    visible (measured: perpetual_calendar haze 0.000 -> 1.000, i.e. a grey veil
    around the whole icon).

    Here the palette is built over (quantised RGB, quantised alpha) PAIRS, so a
    colour can own several entries at different alphas and alpha 0 stays alpha 0.
    """
    rgba = img.convert('RGBA')
    w, h = rgba.size
    src = rgba.load()

    # average colour of the visible pixels: transparent pixels must not invent
    # their own colour clusters
    rs = gs = bs = n = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = src[x, y]
            if a > 0:
                rs += r; gs += g; bs += b; n += 1
    avg = (rs // n, gs // n, bs // n) if n else (0, 0, 0)

    step = max(1, 256 // max(1, alpha_levels))
    flat = Image.new('RGB', (w, h))
    fp = flat.load()
    qa = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b, a = src[x, y]
            fp[x, y] = (r, g, b) if a > 0 else avg
            q = int(round(a / float(step))) * step
            qa[y][x] = 255 if q > 255 else q

    p = flat.quantize(colors=256, method=Image.MEDIANCUT)
    pal_rgb = p.getpalette()[:768]
    idx = p.tobytes()

    cnt = {}
    for y in range(h):
        row = y * w
        for x in range(w):
            k = (idx[row + x], qa[y][x])
            cnt[k] = cnt.get(k, 0) + 1
    keep = sorted(cnt.items(), key=lambda kv: -kv[1])[:256]

    pal = bytearray()
    remap = {}
    by_rgb = {}
    for slot, ((pi, al), _c) in enumerate(keep):
        r = pal_rgb[pi * 3] if pi * 3 + 2 < len(pal_rgb) else 0
        g = pal_rgb[pi * 3 + 1] if pi * 3 + 2 < len(pal_rgb) else 0
        b = pal_rgb[pi * 3 + 2] if pi * 3 + 2 < len(pal_rgb) else 0
        pal += bytes((b, g, r, al))
        remap[(pi, al)] = slot
        by_rgb.setdefault(pi, []).append((al, slot))
    removed = 256 - len(keep)
    if removed > 0:
        pal += b'\x00\x00\x00\x00' * removed
    for pi in by_rgb:
        by_rgb[pi].sort()

    out = bytearray(w * h)
    for y in range(h):
        row = y * w
        for x in range(w):
            pi = idx[row + x]
            al = qa[y][x]
            s = remap.get((pi, al))
            if s is None:
                cand = by_rgb.get(pi)
                if cand:
                    s = min(cand, key=lambda t: abs(t[0] - al))[1]
                else:
                    s = 0
            out[row + x] = s
    return bytes(pal) + bytes(out)


def encode_i8_palette(img, pal_bgra, alpha_tol=12):
    """Quantise to an EXISTING 256-entry BGRA palette (as stored in an I8 blob).

    Reusing the source icon's own palette preserves the artwork's gradient shades
    and its anti-aliased edge levels.  A freshly clustered palette cannot: the
    plate gradient eats the 256 entries, the edge collapses to a few alpha steps
    and dropped pixels land on wrong entries -- measured on remote_camera as a
    jagged plate rim plus stray coloured speckles.

    The search is constrained by alpha so that
      * fully transparent source pixels can only pick transparent entries
        (no veil, no speckles), and
      * fully opaque source pixels can only pick opaque entries
        (the body never goes translucent).
    """
    rgba = img.convert('RGBA')
    w, h = rgba.size
    px = rgba.load()

    ent = [(pal_bgra[i * 4 + 2], pal_bgra[i * 4 + 1],
            pal_bgra[i * 4], pal_bgra[i * 4 + 3]) for i in range(256)]
    clear = [i for i, e in enumerate(ent) if e[3] == 0]
    if not clear:                       # guarantee a transparent entry exists
        worst = min(range(256), key=lambda i: ent[i][3])
        ent[worst] = (0, 0, 0, 0)
        clear = [worst]
    solid = [i for i, e in enumerate(ent) if e[3] >= 248]
    by_alpha = {}
    for i, e in enumerate(ent):
        by_alpha.setdefault(e[3], []).append(i)

    def premul(e):
        r, g, b, a = e
        return (r * a // 255, g * a // 255, b * a // 255, a)

    P = [premul(e) for e in ent]
    cache = {}
    out = bytearray(w * h)
    for y in range(h):
        row = y * w
        for x in range(w):
            r, g, b, a = px[x, y]
            key = (r >> 2, g >> 2, b >> 2, a >> 3)
            s = cache.get(key)
            if s is None:
                if a == 0:
                    cand = clear
                elif a >= 248 and solid:
                    cand = solid
                else:
                    cand = []
                    for da in range(0, alpha_tol + 1):
                        cand += by_alpha.get(a + da, ()) if a + da <= 255 else ()
                        if da:
                            cand += by_alpha.get(a - da, ()) if a - da >= 0 else ()
                    if not cand:
                        cand = range(256)
                pr, pg, pb, pa = premul((r, g, b, a))
                best, bd = cand[0], None
                for i in cand:
                    q = P[i]
                    d = ((pr - q[0]) ** 2 + (pg - q[1]) ** 2 + (pb - q[2]) ** 2
                         + 2 * (pa - q[3]) ** 2)
                    if bd is None or d < bd:
                        bd, best = d, i
                s = best
                cache[key] = s
            out[row + x] = s

    pal = bytearray()
    for (r, g, b, a) in ent:
        pal += bytes((b, g, r, a))
    return bytes(pal) + bytes(out)


def encode(img, cf, w, h, flags=0, pad_to=None, palette=None):
    if cf == CF_ARGB8888:
        body = encode_argb8888(img)
    elif palette is not None:
        body = encode_i8_palette(img, palette)
    else:
        body = encode_i8(img)
    stride = w * (4 if cf == CF_ARGB8888 else 1)
    blob = struct.pack('<BBHHHHH', MAGIC, cf, flags, w, h, stride, 0) + body
    if pad_to is not None:
        if len(blob) > pad_to:
            raise ValueError(f'encoded {len(blob)} > slot {pad_to}')
        blob += b'\x00' * (pad_to - len(blob))
    return blob


# ----------------------------------------------------------------- helpers
def raw_i8_strided(img, stride, colors=256):
    """I8 像素流：1024 B 调色板（BGRA）+ stride*h 个索引（行尾按 header 的 stride 补 0）。

    RLE 槽位专用：用 FASTOCTREE 自适应减色 + 关闭抖动 —— 颜色越少、相邻像素越容易出现
    长游程，RLE 流就越短（这是能不能塞进原 csize 的关键）。
    """
    q = img.convert('RGBA').quantize(colors=max(2, min(256, colors)),
                                     method=Image.FASTOCTREE, dither=Image.NONE)
    if q.palette.mode == 'RGBA':
        pal = list(q.getpalette('RGBA'))
    else:
        rgb = q.getpalette('RGB')
        pal = [v for i in range(256) for v in (rgb[i * 3], rgb[i * 3 + 1], rgb[i * 3 + 2], 255)]
    pal = (pal + [0] * 1024)[:1024]
    pal_b = bytearray()
    for i in range(256):                                  # 存储序：B, G, R, A
        r, g, b, a = pal[i * 4:i * 4 + 4]
        pal_b += bytes((b, g, r, a))
    idx = q.tobytes()
    w, h = img.size
    rows = bytearray()
    for y in range(h):
        rows += idx[y * w:(y + 1) * w]
        if stride > w:
            rows += b'\x00' * (stride - w)
    return bytes(pal_b) + bytes(rows)


# 从大到小试：优先保真，装不下再减色
RLE_COLOR_STEPS = (256, 192, 160, 128, 96, 80, 64, 48, 40, 32, 24, 16, 12, 8, 6, 4)


def encode_into_slot(img, stock_blob, slot_len=None, colors=None):
    """把 img 编成与 stock_blob **逐字节等长** 的 LVGL v9 blob（沿用原 header）。

    真实固件里这些 UI 素材有两种槽位形态，都必须支持，否则 ROMFS 后面所有偏移全平移：
      * ARGB8888 未压缩（144x144 图标那种）：像素流 + 零填充到原长度
      * I8 + RLE 压缩（walkie_talkie 里几乎全是）：量化 -> RLE -> 用 ctrl=0 空指令补齐到原 csize
        （颜色数从 256 逐级往下试，取第一个能塞进原 csize 的）
    返回 (blob, how)；不支持 / 压缩后仍超长时返回 (None, 原因)。
    """
    h = img_header(stock_blob)
    if h is None:
        return None, '不是 LVGL bin'
    w, ht, cf, flags = h['w'], h['h'], h['cf'], h['flags']
    if slot_len is None:
        slot_len = len(stock_blob)
    out_img = img.convert('RGBA')
    if out_img.size != (w, ht):
        # 约定：**长宽比不一致的素材直接不替换**（保持原厂图），而不是拉伸或裁切 ——
        # 拉伸会把方块变长方形；裁切会切掉按钮两端。宁可保持原厂，也不给设备塞变形图。
        pw, ph = out_img.size
        if abs(pw / ph - w / ht) / (w / ht) > 0.005:
            return None, ('长宽比不一致（源 %dx%d = %.3f，槽位 %dx%d = %.3f）-> 按约定跳过，保持原厂'
                          % (pw, ph, pw / ph, w, ht, w / ht))
        out_img = out_img.resize((w, ht), RESAMPLE)
    if cf == CF_ARGB8888 and not (flags & 0x08):
        blob = stock_blob[:12] + encode_argb8888(out_img)
        if len(blob) > slot_len:
            return None, 'ARGB 编码 %d > 槽位 %d' % (len(blob), slot_len)
        return blob + b'\x00' * (slot_len - len(blob)), 'ARGB(补 %d)' % (slot_len - len(blob))
    if cf == CF_I8 and (flags & 0x08):
        method, csize, usize = struct.unpack('<III', stock_blob[12:24])
        stride = h['stride'] or w
        best = None
        for n in (colors,) if colors else RLE_COLOR_STEPS:
            raw = raw_i8_strided(out_img, stride, n)
            comp = rle_compress(raw)
            # 末尾还要补一条「重复 1 次」指令(2 B)：原厂流解出来正好是 usize 字节
            # （= 1024 + stride*h + 1），少这 1 字节设备端解码器可能直接判失败。
            if len(comp) + 2 <= csize:
                best = (n, raw, comp)
                break
        if best is None:
            n_last = RLE_COLOR_STEPS[-1]
            comp = rle_compress(raw_i8_strided(out_img, stride, n_last))
            return None, 'RLE 压缩后 %d > csize %d（已减到 %d 色）' % (len(comp), csize, n_last)
        n, raw, comp = best
        comp = comp + bytes((1, raw[-1]))          # 把流做到正好 usize 字节，和原厂一致
        padded = pad_rle(comp, csize)
        if padded is None:
            return None, '补齐失败'
        blob = stock_blob[:12] + struct.pack('<III', 1, csize, usize) + padded
        if len(blob) != slot_len:
            return None, '组装后 %d != 槽位 %d' % (len(blob), slot_len)
        return blob, 'RLE %d色 %d/%d' % (n, len(comp), csize)
    return None, 'cf=0x%02x flags=%d 不支持' % (cf, flags)


def targets(r):
    """Map a flat, file-name-safe key -> inode for every launcher icon.

    alarm/launcher.bin            -> alarm
    sports/training/launcher.bin  -> sports_training
    phone/contacts_launcher.bin   -> phone_contacts
    """
    out = {}
    for p, i in r.entries():
        if not p.rsplit('/', 1)[-1].endswith('launcher.bin'):
            continue
        stem = p[:-4]                                   # drop '.bin'
        if stem.endswith('_launcher'):
            stem = stem[:-len('_launcher')]
        elif stem.endswith('/launcher'):
            stem = stem[:-len('/launcher')]
        out[stem.replace('/', '_')] = i
    return out


def describe(r, i):
    h = img_header(r.read(i))
    if not h:
        return '?', '?', '?'
    return f'{h["w"]}x{h["h"]}', FMT.get(h['cf'], f'0x{h["cf"]:02x}'), h


def cmd_list(image):
    r = Romfs(image)
    print(f'{os.path.basename(image)}  volume={r.volume}  romfs_size={r.sb_size}')
    for app, i in sorted(targets(r).items()):
        dim, fmt, _ = describe(r, i)
        print(f'  {app:<26} data@0x{i.data_off:08x} len={i.size:<7} {dim} {fmt}')


def cmd_make(image, pngdir, outdir, pad=False, write_patched=False):
    r = Romfs(image)
    tg = targets(r)
    os.makedirs(outdir, exist_ok=True)
    payload_dir = os.path.join(outdir, 'payload')
    os.makedirs(payload_dir, exist_ok=True)
    patch = bytearray()
    rollback = bytearray()
    records, skipped = [], []
    for fn in sorted(os.listdir(pngdir)):
        if not fn.lower().endswith('.png'):
            continue
        app = fn[:-4]
        if app not in tg:
            skipped.append((app, 'no such app'))
            continue
        ino = tg[app]
        orig = r.read(ino)
        _, fmt, h = describe(r, ino)
        if h is None:
            skipped.append((app, f'not LVGL image (len={ino.size})'))
            continue
        src = Image.open(os.path.join(pngdir, fn)).convert('RGBA')
        src_dim = f'{src.size[0]}x{src.size[1]}'
        resized = False
        if src.size != (h['w'], h['h']):
            if pad:
                tw, th = src.size
                blob = encode(src, h['cf'], tw, th, h['flags'], pad_to=len(orig))
            else:
                src = src.resize((h['w'], h['h']), RESAMPLE)
                tw, th = src.size
                resized = True
                blob = encode(src, h['cf'], tw, th, h['flags'])
        else:
            tw, th = src.size
            blob = encode(src, h['cf'], tw, th, h['flags'])
        if len(blob) != len(orig):
            skipped.append((app, f'length {len(blob)} != {len(orig)}'))
            continue
        patch += struct.pack('<II', ino.data_off, len(blob)) + blob
        rollback += struct.pack('<II', ino.data_off, len(orig)) + orig
        open(os.path.join(payload_dir, app.replace('/', '_') + '.bin'), 'wb').write(blob)
        records.append(dict(app=app, offset=ino.data_off, length=len(blob),
                            format=fmt, stock_dim=f'{h["w"]}x{h["h"]}',
                            source=fn, source_dim=src_dim,
                            resized=resized, padded=bool(pad and src.size != (h['w'], h['h'])),
                            sha256=hashlib.sha256(blob).hexdigest()))

    open(os.path.join(outdir, 'icons.patch'), 'wb').write(patch)
    open(os.path.join(outdir, 'icons.rollback'), 'wb').write(rollback)
    manifest = dict(image=os.path.basename(image), volume=r.volume,
                    image_sha256=hashlib.sha256(r.data).hexdigest(),
                    replace_count=len(records), records=records,
                    skipped=[{'app': a, 'reason': b} for a, b in skipped])
    json.dump(manifest, open(os.path.join(outdir, 'manifest.json'), 'w'),
              indent=1, ensure_ascii=False)

    print(f'{"app":<26}{"offset":>12}{"bytes":>8}  {"fmt":<10}{"stock":>9}{"source":>9}  note')
    for m in records:
        note = 'resized' if m['resized'] else ('padded' if m['padded'] else '')
        print(f'{m["app"]:<26}0x{m["offset"]:08x}{m["length"]:>8}  {m["format"]:<10}'
              f'{m["stock_dim"]:>9}{m["source_dim"]:>9}  {note}')
    for a, why in skipped:
        print(f'  SKIP {a}: {why}')
    print(f'\n{len(records)} replacement(s)')
    print(f'  payload  -> {payload_dir}')
    print(f'  patch    -> {os.path.join(outdir, "icons.patch")}  ({len(patch)} bytes)')
    print(f'  rollback -> {os.path.join(outdir, "icons.rollback")}  ({len(rollback)} bytes)')
    print(f'  manifest -> {os.path.join(outdir, "manifest.json")}')
    if write_patched:
        out = os.path.join(outdir, 'vela_app_patched.bin')
        cmd_apply(image, os.path.join(outdir, 'icons.patch'), out)


def cmd_apply(image, patch, out):
    data = bytearray(open(image, 'rb').read())
    blob = open(patch, 'rb').read()
    off = n = 0
    while off < len(blob):
        addr, ln = struct.unpack('<II', blob[off:off+8])
        chunk = blob[off+8:off+8+ln]
        assert len(chunk) == ln and addr + ln <= len(data), 'corrupt patch'
        data[addr:addr+ln] = chunk
        off += 8 + ln
        n += 1
    open(out, 'wb').write(data)
    print(f'applied {n} record(s) -> {out}')


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        print(__doc__)
    elif a[0] == 'list':
        cmd_list(a[1])
    elif a[0] == 'make':
        cmd_make(a[1], a[2], a[3], '--pad' in a, '--patched' in a)
    elif a[0] == 'apply':
        cmd_apply(a[1], a[2], a[3])
    else:
        print(__doc__)
