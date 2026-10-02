"""用真实渲染结果判"会不会被圆屏切掉"（480x480 档）。

做法：渲染一张**不套圆形遮罩**的 RGBA，然后量所有非透明像素到圆心的距离。
这样自动考虑字体实际字宽、折行、圆角、图片缩放 —— 比按元素外框估算准得多。
replace 盘与 restore 盘的文案都过一遍（PAGES_ALT），只换字不改坐标，所以文案变长
就必须重新量 —— 这里就是那道闸。
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from render_ui import draw_label, W, H, _rgb
import render_ui as R
from pages import PAGES, PAGES_ALT

CX = CY = 240.0
RAD = 240.0


def render_raw(items):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
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


R.OVERFLOW.clear()
cases = list(PAGES.items()) + [('alt:' + k, v) for k, v in PAGES_ALT.items()]
print('%-16s %8s %11s  %s' % ('page', 'max r', 'outside px', 'worst point / note'))
print('-' * 78)
bad = 0
for name, items in cases:
    im = render_raw(items)
    px = im.load()
    worst, wpt, outside = 0.0, None, 0
    for y in range(H):
        for x in range(W):
            if px[x, y][3] > 8:
                dd = math.hypot(x - CX, y - CY)
                if dd > worst:
                    worst, wpt = dd, (x, y)
                if dd > RAD:
                    outside += 1
    note = '全部在圆内' if worst <= RAD else '会被切 %d px' % outside
    print('%-16s %8.1f %11d  %s %s%s' % (name, worst, outside, wpt, note,
                                         '' if outside == 0 else '  <-- CLIPPED'))
    if outside:
        bad += 1
print('-' * 78)
print('圆心 (%.0f,%.0f) 半径 %.0f 画布 %dx%d 圆屏' % (CX, CY, RAD, W, H))
if R.OVERFLOW:
    print('!! 有标签超出框高（会折行/被裁，先修文案或框）：')
    for o in R.OVERFLOW:
        print('   ', o)
    bad += len(R.OVERFLOW)
print('检查了 %d 个页面（含 replace/restore 两套文案）：越界页面 %d' % (len(cases), bad))
print('RESULT: %s' % ('PASS（0 越界、0 折行）' if bad == 0 else 'FAIL'))
sys.exit(1 if bad else 0)
