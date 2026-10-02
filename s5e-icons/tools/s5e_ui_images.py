# -*- coding: utf-8 -*-
"""UI image assets for the 480 face + the 326 preview / 80 logo for the builder."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iconpack as ip
from PIL import Image, ImageDraw
from paths import PROJ, DOCS
ASSETS = os.path.join(PROJ, 'assets')
OUT = os.path.join(PROJ, 'ui_images')
os.makedirs(OUT, exist_ok=True)

SPEC = [('back', 'backarrow.png', 18, 29),
        ('ic_help', 'MdiLightbulbOutline.png', 31, 31),
        ('ic_replace', 'MdiBandage.png', 31, 31),
        ('ic_about', 'MdiInformationOutline.png', 31, 31),
        ('ic_check', 'MdiClipboardTextSearchOutline.png', 31, 31),
        ('ic_rollback', 'MdiReplyAllOutline.png', 31, 31),
        ('ic_qq', 'qq.png', 31, 31)]
for name, png, w, h in SPEC:
    p = os.path.join(ASSETS, png)
    if not os.path.exists(p):
        print('  missing', png); continue
    img = Image.open(p).convert('RGBA')
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    blob = ip.encode(img, ip.CF_ARGB8888, w, h, 0)
    open(os.path.join(OUT, name + '.bin'), 'wb').write(blob)
    print('  %-12s <- %-34s %dx%d  %d bytes' % (name, png, w, h, len(blob)))

L = 80
img = Image.open(os.path.join(ASSETS, 'cover.png')).convert('RGBA').resize((L, L), Image.LANCZOS)
mask = Image.new('L', (L, L), 0)
ImageDraw.Draw(mask).ellipse([0, 0, L - 1, L - 1], fill=255)
img.putalpha(mask)
open(os.path.join(OUT, 'logo.bin'), 'wb').write(ip.encode(img, ip.CF_ARGB8888, L, L, 0))
img.save(os.path.join(DOCS, 'logo_preview_480.png'))
print('  %-12s <- cover.png(circular)                %dx%d' % ('logo', L, L))
print('->', OUT)
