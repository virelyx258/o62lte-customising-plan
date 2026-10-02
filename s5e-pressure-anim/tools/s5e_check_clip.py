# -*- coding: utf-8 -*-
"""圆屏切边检查：用**真实渲染出来的像素**判 480x480 圆屏有没有被切到。

圆心 (240,240)、半径 240。任何 alpha>8 且离圆心 >240 的像素都算越界。
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s5e_render_ui as R
from s5e_pages import PAGES

W = H = 480
CX = CY = 240.0
RAD = 240.0

print('%-10s %8s %11s  worst point' % ('page', 'max r', 'outside px'))
print('-' * 62)
bad = 0
for name, items in PAGES.items():
    im = R.render_raw(items)
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
    if outside:
        bad += 1
print('-' * 62)
print('圆心 (240,240) 半径 240 画布 480x480   越界页数：%d' % bad)
if R.OVERFLOW:
    print('!! 文本溢出框 %d 处：' % len(R.OVERFLOW))
    for o in R.OVERFLOW:
        print('   ', o)
sys.exit(1 if (bad or R.OVERFLOW) else 0)
