"""按页面规格渲染 480x480 预览图（真 MiSans 字体 + 真素材 + 圆形遮罩）。

支持 kind: rect / circle / image / label
label 支持 recolor 标记 "#RRGGBB 文字#"（LVGL 的写法），以及 align/vcenter/vtop/lh
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont

from paths import PROJ, INPUTS, FONTS, WORK, DOCS
ROOT = PROJ
FONT_FILES = {'semibold': 'MiSans-Semibold.ttf', 'medium': 'MiSans-Medium.ttf',
              'regular': 'MiSans-Regular.ttf'}
W = H = 480
_fc = {}


def _font_from_firmware(name):
    """从 inputs/target/vela_font.bin 里现取 MiSans（固件里就有这几个 ttf）。"""
    p = os.path.join(INPUTS, 'target', 'vela_font.bin')
    if not os.path.exists(p):
        return None
    try:
        from romfs import Romfs
        r = Romfs(p)
    except Exception:
        return None
    for path, ino in r.entries():
        if path == name:
            d = os.path.join(WORK, 'fonts')
            os.makedirs(d, exist_ok=True)
            out = os.path.join(d, name)
            open(out, 'wb').write(r.read(ino))
            return out
    return None


def font(weight, size):
    k = (weight, size)
    if k in _fc:
        return _fc[k]
    name = FONT_FILES.get(weight, FONT_FILES['medium'])
    p = os.path.join(FONTS, name)
    if not os.path.exists(p):
        p = _font_from_firmware(name) or p
    if not os.path.exists(p):
        for alt in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\msyhbd.ttc',
                    r'C:\Windows\Fonts\arial.ttf'):
            if os.path.exists(alt):
                p = alt
                print('   [warn] %s 缺失，预览改用 %s（只影响预览缩略图）' % (name, os.path.basename(alt)))
                break
    _fc[k] = ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()
    return _fc[k]


def _rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def split_recolor(text, base):
    """LVGL 写法: '灰#ffffff 白#灰'
    - # + 6 位十六进制   -> 切到该颜色（该字符不显示）
    - 再次遇到单独的 #    -> 结束着色，回到基础色（该字符不显示）
    """
    runs, buf, cur, incol = [], '', base, False
    i = 0
    while i < len(text):
        if text[i] == '#':
            if re.match(r'[0-9a-fA-F]{6}', text[i + 1:i + 7]):
                runs.append((cur, buf)); buf = ''
                cur = text[i + 1:i + 7].lower(); incol = True
                i += 7
                continue
            if incol:
                runs.append((cur, buf)); buf = ''
                cur = base; incol = False
                i += 1
                continue
        buf += text[i]; i += 1
    runs.append((cur, buf))
    return runs


def wrap_runs(d, runs, f, maxw):
    """按像素宽度折行，返回 [[(color, text), ...], ...]（尽量保持原换行）"""
    lines = [[]]
    for color, chunk in runs:
        for k, seg in enumerate(chunk.split('\n')):
            if k:
                lines.append([])
            if not seg:
                continue
            cur = ''
            for ch in seg:
                if d.textlength(cur + ch, font=f) > maxw and cur:
                    lines[-1].append((color, cur))
                    lines.append([])
                    cur = ch
                else:
                    cur += ch
            if cur:
                lines[-1].append((color, cur))
    return lines


OVERFLOW = []          # (标签文本前 12 字, css_lh, 行数, 块高, 框高)


def draw_label(img, d, it):
    f = font(it.get('weight', 'medium'), it['size'])
    runs = split_recolor(it['text'], it.get('color', 'ffffff')) \
        if it.get('recolor') else [(it.get('color', 'ffffff'), it['text'])]
    asc, desc = f.getmetrics()
    natural = asc + desc
    lh = max(it.get('lh', 0), natural)      # LVGL 用字体自身行高，取较大者预测
    lines = wrap_runs(d, runs, f, it['w'])
    total = lh * len(lines)
    if total > it['h'] + 0.5:
        OVERFLOW.append((it['text'][:14].replace('\n', '/'),
                         round(it.get('lh', 0), 2), len(lines),
                         round(total, 1), it['h'], round(natural, 2)))
    if it.get('vcenter'):
        y = it['y'] + (it['h'] - total) / 2
    elif it.get('vtop'):
        y = it['y']
    else:
        y = it['y'] + (it['h'] - total) / 2
    for ln in lines:
        wsum = sum(d.textlength(t, font=f) for _, t in ln)
        if it.get('align') == 'center':
            x = it['x'] + (it['w'] - wsum) / 2
        elif it.get('align') == 'right':
            x = it['x'] + it['w'] - wsum
        else:
            x = it['x']
        for color, t in ln:
            d.text((x, y), t, font=f, fill=_rgb(color) + (255,))
            x += d.textlength(t, font=f)
        y += lh


def render(items, out, mask=True, ring=False):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for it in items:
        k = it.get('kind')
        if k == 'rect':
            box = [it['x'], it['y'], it['x'] + it['w'] - 1, it['y'] + it['h'] - 1]
            r = it.get('radius', 0)
            (d.rounded_rectangle if r else d.rectangle)(
                box, radius=r, fill=_rgb(it['bg']) + (255,)) if r else d.rectangle(
                box, fill=_rgb(it['bg']) + (255,))
        elif k == 'circle':
            box = [it['x'], it['y'], it['x'] + it['w'] - 1, it['y'] + it['h'] - 1]
            d.ellipse(box, fill=_rgb(it['bg']) + (255,))
        elif k == 'image':
            p = it['src']
            if os.path.exists(p):
                im = Image.open(p).convert('RGBA').resize((it['w'], it['h']), Image.LANCZOS)
                img.alpha_composite(im, (it['x'], it['y']))
        elif k == 'label':
            draw_label(img, d, it)
    if mask:
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).ellipse([0, 0, W - 1, H - 1], fill=255)
        img.putalpha(m)
    base = Image.new('RGB', (W, H), (0, 0, 0))
    base.paste(img, (0, 0), img)
    if ring:
        ImageDraw.Draw(base).ellipse([0, 0, W - 1, H - 1], outline=(80, 80, 90))
    base.save(out)
    return out


if __name__ == '__main__':
    from pages import PAGES, PAGES_ALT
    os.makedirs(DOCS, exist_ok=True)
    outs = []
    for name, items in list(PAGES.items()) + [('alt_' + k, v) for k, v in PAGES_ALT.items()]:
        p = os.path.join(DOCS, 'ui_%s.png' % name)
        render(items, p)
        outs.append((name, p))
        print('wrote', p)
    if OVERFLOW:
        print('!! 标签超出框高（会被裁/折行，需要调框或调文案）：')
        for o in OVERFLOW:
            print('   ', o)
    else:
        print('no label overflow（所有标签都在框内，不多行、不裁切）')
    cols = 4
    rows = (len(outs) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (W + 12) + 12, rows * (H + 26) + 12), (28, 28, 32))
    d = ImageDraw.Draw(sheet)
    for i, (name, p) in enumerate(outs):
        x = 12 + (i % cols) * (W + 12)
        y = 12 + (i // cols) * (H + 26)
        sheet.paste(Image.open(p), (x, y + 18))
        d.text((x + 4, y + 2), name, fill=(200, 200, 200))
    sp = os.path.join(DOCS, 'ui_all.png')
    sheet.save(sp)
    print('wrote', sp, sheet.size)
