"""用真实渲染结果判"会不会被圆屏切掉"。

做法：渲染一张**不套圆形遮罩**的 RGBA，然后量所有非透明像素到圆心的距离。
这样自动考虑字体实际字宽、折行、圆角、图片缩放 —— 比按元素外框估算准得多。
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from render_ui import draw_label, W, H
from pages import PAGES

CX = CY = 233.0
R = 233.0


def render_raw(items):
    img = Image.new('RGBA', (W, None) if False else (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    from render_ui import _rgb, font
    for it in items:
        k = it.get('kind')
        if k == 'rect':
            box = [it['x'], it['y'], it['x'] + it['w'] - 1, it['y'] + it['h'] - 1]
            r = it.get('radius', 0)
            if r:
                d.rounded_rectangle(box, radius=r, fill=_rgb(it['bg']) + (255,))
            else:
                d.rectangle(box, fill=_rgb(it['bg']) + (255,))
        elif k == 'circle':
            d.ellipse([it['x'], it['y'], it['x'] + it['w'] - 1, it['y'] + it['h'] - 1],
                      fill=_rgb(it['bg']) + (255,))
        elif k == 'image':
            if os.path.exists(it['src']):
                im = Image.open(it['src']).convert('RGBA').resize((it['w'], it['h']), Image.LANCZOS)
                img.alpha_composite(im, (it['x'], it['y']))
        elif k == 'label':
            draw_label(img, d, it)
    return img


print(f'{"page":<10} {"max r":>7} {"outside px":>11}  worst point / note')
print('-' * 78)
for name, items in PAGES.items():
    im = render_raw(items)
    px = im.load()
    worst, wpt, outside = 0.0, None, 0
    for y in range(H):
        for x in range(W):
            if px[x, y][3] > 8:
                d = math.hypot(x - CX, y - CY)
                if d > worst:
                    worst, wpt = d, (x, y)
                if d > R:
                    outside += 1
    note = '全部在圆内' if worst <= R else f'会被切 {outside} px'
    print(f'{name:<10} {worst:>7.1f} {outside:>11}  {wpt} {note}')
print('-' * 78)
print(f'圆心 ({CX:.0f},{CY:.0f})  半径 {R:.0f}   画布 {W}x{H}')
