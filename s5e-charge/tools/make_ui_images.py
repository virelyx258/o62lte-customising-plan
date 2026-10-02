"""把 assets/ 里的 UI 素材转成 LVGL v9 二进制图片（.bin），供表盘运行时加载。

尺寸取自 tools/pages.py 的 480 档规格：列表图标 31x31、返回箭头 18x29、关于页 logo 80x80。
格式（已在真机验证）:
    header 12B: magic=0x19 | cf | flags | w | h | stride | reserved
    cf=0x10 ARGB8888 -> 数据为 BGRA，长度 = w*h*4
编码器用 iconpack.encode（与图标包同一套，字节级验证过）。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iconpack as ip
from PIL import Image, ImageDraw

from paths import PROJ, DOCS
ASSETS = os.path.join(PROJ, 'assets')
OUT = os.path.join(PROJ, 'ui_images')

SPEC = [
    ('back',        'backarrow.png',                     18, 29),
    ('ic_help',     'MdiLightbulbOutline.png',            31, 31),
    ('ic_replace',  'MdiBandage.png',                     31, 31),
    ('ic_about',    'MdiInformationOutline.png',          31, 31),
    ('ic_check',    'MdiClipboardTextSearchOutline.png',  31, 31),
    ('ic_rollback', 'MdiReplyAllOutline.png',             31, 31),
    ('ic_qq',       'qq.png',                             31, 31),
]

os.makedirs(OUT, exist_ok=True)
for name, png, w, h in SPEC:
    p = os.path.join(ASSETS, png)
    if not os.path.exists(p):
        print(f'  缺少 {png}'); continue
    img = Image.open(p).convert('RGBA')
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    blob = ip.encode(img, ip.CF_ARGB8888, w, h, 0)
    dst = os.path.join(OUT, name + '.bin')
    open(dst, 'wb').write(blob)
    print(f'  {name:<12} <- {png:<34} {w}x{h}  {len(blob)} bytes')

# 关于页的 logo：封面图缩到 80x80，并加圆形遮罩
# （封面是圆形图案 + 黑色方角，不裁成圆的话会在墨绿卡片上露出黑方块）
logo_src = os.path.join(ASSETS, 'cover.png')
if os.path.exists(logo_src):
    L = 80
    img = Image.open(logo_src).convert('RGBA').resize((L, L), Image.LANCZOS)
    mask = Image.new('L', (L, L), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, L - 1, L - 1], fill=255)
    img.putalpha(mask)
    blob = ip.encode(img, ip.CF_ARGB8888, L, L, 0)
    open(os.path.join(OUT, 'logo.bin'), 'wb').write(blob)
    # 顺便存一份 PNG 给本机预览用（注意别放进打包目录，会一起被打进去）
    prev = os.path.join(DOCS, 'logo_preview_480.png')
    os.makedirs(os.path.dirname(prev), exist_ok=True)
    img.save(prev)
    print(f'  {"logo":<12} <- cover.png(圆形裁切)              {L}x{L}  {len(blob)} bytes')

print('written to', OUT)
