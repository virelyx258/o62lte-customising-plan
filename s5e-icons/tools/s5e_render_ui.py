# -*- coding: utf-8 -*-
"""Render the 480x480 page spec with the real MiSans fonts (previews + overview)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_ui as R
from PIL import Image
from paths import DOCS
R.W = R.H = 480
from s5e_pages import PAGES

outs = []
for name, items in PAGES.items():
    p = os.path.join(DOCS, 's5e_ui_%s.png' % name)
    R.render(items, p)
    outs.append((name, p))
    print('wrote', p)
if R.OVERFLOW:
    print('!! label overflow (text, lh, lines, total, box, natural):')
    for o in R.OVERFLOW:
        print('   ', o)
else:
    print('no label overflow')
cols = 3
rows = (len(outs) + cols - 1) // cols
sheet = Image.new('RGB', (cols * (480 + 12) + 12, rows * (480 + 12) + 12), (28, 28, 32))
for i, (name, p) in enumerate(outs):
    sheet.paste(Image.open(p), (12 + (i % cols) * 492, 12 + (i // cols) * 492))
sp = os.path.join(DOCS, 's5e_ui_all.png')
sheet.save(sp)
print('wrote', sp, sheet.size)
