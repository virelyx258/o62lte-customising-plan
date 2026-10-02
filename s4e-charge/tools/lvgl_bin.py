"""LVGL v9 RLE codec (LV_IMAGE_COMPRESS_RLE).

Control byte grammar (upstream `lv_rle_decompress`):
  high bit CLEAR (0x00..0x7F) : repeat the next single `blk`-byte block `ctrl` times
  high bit SET   (0x80|count) : copy `count` blocks verbatim (literal run)
  count is 1..=127
For palette formats (I8) the stream decodes to 256*4 palette bytes followed by
w*h palette indices.
"""
import struct
from PIL import Image

MAGIC = 0x19
FLAG_COMPRESSED = 0x08
METHOD_NONE, METHOD_RLE, METHOD_LZ4 = 0, 1, 2


def rle_decompress(data, blk, out_len=None):
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        ctrl = data[i]; i += 1
        if ctrl & 0x80:
            cnt = ctrl & 0x7F
            nb = cnt * blk
            if i + nb > n:
                raise ValueError('truncated literal run')
            out += data[i:i + nb]
            i += nb
        else:
            cnt = ctrl
            if i + blk > n:
                raise ValueError('truncated repeat unit')
            unit = data[i:i + blk]
            i += blk
            out += unit * cnt
        if out_len is not None and len(out) >= out_len:
            break
    return bytes(out)


def rle_compress(raw, max_run=127):
    """LVGL RLE 编码器（rle_decompress 的逆向，blk=1）。

    贪心：先找同字节游程（>=2 用「重复」指令），否则攒「原样」指令。
    输出长度总是 <= 原图像素流，因为最坏情况每条 literal 只多 1 个控制字节。
    """
    out = bytearray()
    i, n = 0, len(raw)
    while i < n:
        v = raw[i]
        j = i + 1
        while j < n and raw[j] == v and j - i < max_run:
            j += 1
        run = j - i
        if run >= 2:
            out.append(run); out.append(v); i = j
            continue
        lit = bytearray()
        k = i
        while k < n and len(lit) < max_run:
            if k + 1 < n and raw[k] == raw[k + 1]:
                break
            lit.append(raw[k]); k += 1
        if not lit:                      # 理论上到不了这里
            lit.append(v); k = i + 1
        out.append(0x80 | len(lit)); out += lit
        i = k
    return bytes(out)


def pad_rle(comp, want):
    """把 RLE 流补到 want 字节：用 ctrl=0（重复 0 次 = 产出 0 像素）的 2 字节空指令。

    ctrl=0 是合法指令（`len = 0`，两个越界判断都不触发），所以设备端解码器读完 csize
    字节既不会越界、也不会返回 INVALID —— 这是「等长覆盖」能成立的关键。
    差值为奇数时先把一条 literal 拆成两条（payload 不变、多 1 个控制字节）。
    """
    d = want - len(comp)
    if d < 0:
        return None
    if d % 2:
        b = bytearray(comp)
        for idx in range(len(b) - 1, -1, -1):
            if b[idx] & 0x80 and (b[idx] & 0x7F) >= 2:
                cnt = b[idx] & 0x7F
                lit = bytes(b[idx + 1: idx + 1 + cnt])
                half = cnt // 2
                b[idx: idx + 1 + cnt] = (bytes([0x80 | half]) + lit[:half] +
                                         bytes([0x80 | (cnt - half)]) + lit[half:])
                break
        else:
            return None
        comp = bytes(b)
        d -= 1
    return comp + b'\x00\x00' * (d // 2)


def parse_header(blob):
    if len(blob) < 12 or blob[0] != MAGIC:
        return None
    magic, cf, flags, w, h, stride, rsv = struct.unpack('<BBHHHHH', blob[:12])
    return dict(magic=magic, cf=cf, flags=flags, w=w, h=h, stride=stride, reserved=rsv)


def decode_lvgl_bin(blob):
    """Return (header, RGBA PIL image) for uncompressed / RLE LVGL v9 .bin.

    NOTE stride: LVGL pads each row to the header's `stride`, which is NOT always
    equal to w (e.g. the S5 41mm control-center icons are 116 wide with stride 128).
    Reading them as w*h contiguous pixels yields rainbow garbage, so the row pitch
    below is taken from the header.
    """
    h = parse_header(blob)
    if h is None:
        return None, None
    cf, w, ht = h['cf'], h['w'], h['h']
    body = blob[12:]
    if h['flags'] & FLAG_COMPRESSED:
        method, csize, usize = struct.unpack('<III', body[:12])
        if method != METHOD_RLE:
            raise ValueError(f'unsupported compression method {method}')
        blk = 4 if cf == 0x10 else 1     # ARGB8888 是 4 字节一块，I8 是 1 字节
        raw = rle_decompress(body[12:12 + csize], blk, usize)
    else:
        raw = body
    img = Image.new('RGBA', (w, ht))
    px = img.load()
    if cf == 0x10:                                  # ARGB8888 (BGRA)
        pitch = max(h['stride'] or 0, w * 4)
        if len(raw) < pitch * ht:
            return h, None
        for y in range(ht):
            row = y * pitch
            for x in range(w):
                b, g, r, a = raw[row + x * 4:row + x * 4 + 4]
                px[x, y] = (r, g, b, a)
    elif cf == 0x0a:                                # I8: palette then indices
        pitch = max(h['stride'] or 0, w)
        if len(raw) < 1024 + pitch * ht:
            return h, None
        pal = raw[:1024]
        palette = [(pal[i*4+2], pal[i*4+1], pal[i*4+0], pal[i*4+3]) for i in range(256)]
        for y in range(ht):
            row = 1024 + y * pitch
            for x in range(w):
                px[x, y] = palette[raw[row + x]]
    else:
        return h, None
    return h, img


def pad_rle_safe(comp, want):
    """把 RLE 流补齐到 want 字节 —— 只用两类**产出 0 像素**的合法指令：
        ctrl=0x00 + unit  : 重复 0 次（2 字节）
        0x80              : 原样 0 个（1 字节，用来修奇偶）
    两者都能通过上游 lv_rle_decompress 的边界判断（len 为 0，不越界）。
    注意：不要像 pad_rle 那样去“拆一条 literal”修奇偶 —— 那是按裸字节扫描的，
    会命中负载里的普通字节、把流改坏（本工具就是踩了这个坑才发现）。"""
    d = want - len(comp)
    if d < 0:
        return None
    out = bytearray(comp)
    out += b'\x00\x00' * (d // 2)
    if d % 2:
        out.append(0x80)
    assert len(out) == want
    return bytes(out)
