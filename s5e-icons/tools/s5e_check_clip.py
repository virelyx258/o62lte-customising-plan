# -*- coding: utf-8 -*-
"""Round-screen clipping check for the 480 spec (measures real rendered pixels)."""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_ui as R
from PIL import Image, ImageDraw
W = H = 480
CX = CY = 240.0
RAD = 240.0
from s5e_pages import PAGES

def render_raw(items):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for it in items:
        k = it.get('kind')
        if k == 'rect':
            box = [it['x'], it['y'], it['x'] + it['w'] - 1, it['y'] + it['h'] - 1]
            r = it.get('radius', 0)
            (d.rounded_rectangle(box, radius=r, fill=R._rgb(it['bg']) + (255,)) if r
             else d.rectangle(box, fill=R._rgb(it['bg']) + (255,)))
        elif k == 'circle':
            d.ellipse([it['x'], it['y'], it['x'] + it['w'] - 1, it['y'] + it['h'] - 1],
                      fill=R._rgb(it['bg']) + (255,))
        elif k == 'image':
            if os.path.exists(it['src']):
                im = Image.open(it['src']).convert('RGBA').resize((it['w'], it['h']), Image.LANCZOS)
                img.alpha_composite(im, (it['x'], it['y']))
        elif k == 'label':
            R.draw_label(img, d, it)
    return img

print('%-10s %8s %11s  worst point' % ('page', 'max r', 'outside px'))
print('-' * 60)
bad = 0
for name, items in PAGES.items():
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
    print('%-10s %8.1f %11d  %s%s' % (name, worst, outside, wpt,
                                      '' if worst <= RAD else '  <-- CLIPPED'))
    if outside: bad += 1
print('-' * 60)
print('centre (240,240) radius 240 canvas 480x480   pages clipped:', bad)
