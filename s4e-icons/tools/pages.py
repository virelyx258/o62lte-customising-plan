"""页面规格 + 本机渲染器：按 CSS 逐条落地，用真 MiSans 字体和真素材渲染预览。

CSS -> 实际能力 的映射（已在真机验证过）:
    left/top/width/height  -> x / y / w / h（466 画布绝对坐标）
    background             -> bg_color
    border-radius          -> radius（50x50 圆的 radius=25）
    color (alpha 1)        -> text_color '#rrggbb'
    color (alpha 0.6)      -> 白 60% 叠在纯黑底上 = #999999（页面底色是黑，见下）
    font-weight 600        -> MiSans-Semibold
    font-weight 500        -> MiSans-Medium
    vertical-align middle  -> vcenter=True
    多色文本               -> LVGL recolor: "灰#ffffff 白#灰"
"""
import os

from paths import PROJ, DOCS
ROOT = PROJ
ASSETS = os.path.join(ROOT, 'assets')
W = H = 466
BG = (0, 0, 0)                 # 封面四角纯黑 -> 页面底色
GRAY = '999999'                # rgba(255,255,255,0.6) 叠黑
WHITE = 'ffffff'
PLATE = '002927'               # rgba(0,41,39,1)
CIRCLE = '4f4f4f'              # rgba(79,79,79,1)
OK = '43cf7c'                  # rgba(67,207,124,1)
ERR = 'd43030'                 # rgba(212,48,48,1)

S600, S500 = 'semibold', 'medium'

# 列表项几何（来自第一个表项的 CSS，其余按同一相对关系排布）
ITEM_X, ITEM_W, ITEM_H, ITEM_R = 49, 368, 88, 34
PITCH = 96                     # 88 + 8px 间距
ICONC_DX, ICONC_DY, ICONC_SZ = 20, 19, 50     # 圆形遮罩 69-49 / 104-85
ICON_DX, ICON_DY, ICON_SZ = 30, 29, 30         # 图标图片 79-49 / 114-85
TITLE_DX, TITLE_DY, TITLE_W, TITLE_H = 80, 17, 208, 54   # 129-49 / 102-85


def item(y, icon, title):
    """一个列表项：底板 + 圆形遮罩 + 图标 + 标题"""
    return [
        dict(kind='rect', x=ITEM_X, y=y, w=ITEM_W, h=ITEM_H, bg=PLATE, radius=ITEM_R),
        dict(kind='circle', x=ITEM_X + ICONC_DX, y=y + ICONC_DY,
             w=ICONC_SZ, h=ICONC_SZ, bg=CIRCLE),
        dict(kind='image', x=ITEM_X + ICON_DX, y=y + ICON_DY,
             w=ICON_SZ, h=ICON_SZ, src=os.path.join(ASSETS, icon)),
        dict(kind='label', x=ITEM_X + TITLE_DX, y=y + TITLE_DY,
             w=TITLE_W, h=TITLE_H, text=title, size=28, weight=S500,
             color=WHITE, align='left', vcenter=True, lh=37.13),
    ]


def clock(t='10:24'):
    return dict(kind='label', x=168, y=0, w=130, h=45, text=t, size=28,
                weight=S600, color=GRAY, align='center', vcenter=True, lh=33.6)


def title(text, x=106, w=255):
    return dict(kind='label', x=x, y=34, w=w, h=45, text=text, size=30,
                weight=S500, color=WHITE, align='center', vcenter=True, lh=44.8)


def back_arrow():
    return dict(kind='image', x=160, y=43, w=17, h=28,
                src=os.path.join(ASSETS, 'backarrow.png'))


def big_button(y=365, text='确认替换'):
    return [
        dict(kind='rect', x=108, y=y, w=250, h=80, bg=PLATE, radius=40),
        dict(kind='label', x=173, y=y + 13, w=120, h=54, text=text, size=28,
             weight=S500, color=WHITE, align='center', vcenter=True, lh=37.13),
    ]


# ---------------------------------------------------------------- 1. 首页
PAGE_HOME = [
    clock(),
    title('OS4 Icons'),
    *item(85,  'MdiLightbulbOutline.png',       '快速帮助'),
    *item(181, 'MdiBandage.png',                '开始替换'),
    *item(277, 'MdiInformationOutline.png',     '关于'),
]

# ---------------------------------------------------------------- 2. 快速帮助
_HELP_HEAD = [clock(), back_arrow(), title('快速帮助', x=179, w=128)]
_HELP_I1 = item(85, 'MdiClipboardTextSearchOutline.png', '环境预检查')
_HELP_D1 = dict(kind='label', x=65, y=176, w=338, h=72,
                text='检查原始资源状态、分区可写情况等。', size=24, weight=S500,
                color=GRAY, align='left', vtop=True, lh=31.82)
_HELP_I2 = item(256, 'MdiReplyAllOutline.png', '回滚修改')
_HELP_D2 = dict(kind='label', x=65, y=344, w=334, h=72,
                text='将图标恢复到系统原始样式。', size=24, weight=S500,
                color=GRAY, align='left', vtop=True, lh=31.82)

PAGE_HELP = _HELP_HEAD + _HELP_I1 + [_HELP_D1] + _HELP_I2 + [_HELP_D2]

# 帮助页的两种结果状态（同一标签换色换字）
HELP_DESC_OK = dict(kind='label', x=65, y=176, w=338, h=72,
                    text='预检查通过 | 38 条 | 2.58MB\n您可以返回主页开始修改。',
                    size=24, weight=S500, color=OK, align='left', vtop=True, lh=31.82)
HELP_DESC_ERR = dict(kind='label', x=65, y=176, w=338, h=72,
                     text='预检查失败：分区头不是 ROMFS，位置 0x00。',
                     size=24, weight=S500, color=ERR, align='left', vtop=True, lh=31.82)

PAGE_HELP_OK = _HELP_HEAD + _HELP_I1 + [HELP_DESC_OK] + _HELP_I2 + [_HELP_D2]
PAGE_HELP_ERR = _HELP_HEAD + _HELP_I1 + [HELP_DESC_ERR] + _HELP_I2 + [_HELP_D2]

# ---------------------------------------------------------------- 3. 开始替换
# 多色文本**不能**用 recolor（AP 里那几处是图片重着色，不是文本属性），
# 所以拆成多个标签 + 手工算 x。折行也写死，否则多色片段位置不确定。
# 宽度用真 MiSans 24px 量得：
#   "的系统版本号为 " = 177   "3.202.79" = 99
#   "Xiaomi Watch S4 eSIM（非" = 313   "15 周年纪念版）" = 178
WARN_LABELS = [
    dict(kind='label', x=64, y=90, w=338, h=70,
         text='替换图标包之前，请先确认自己\n的系统版本号为 ',
         size=24, weight=S500, color=GRAY, align='left', vtop=True, lh=33),
    dict(kind='label', x=241, y=123, w=104, h=33, text='3.202.79',
         size=24, weight=S500, color=WHITE, align='left', vtop=True, lh=33),
    dict(kind='label', x=340, y=123, w=30, h=33, text='！',
         size=24, weight=S500, color=GRAY, align='left', vtop=True, lh=33),
    dict(kind='label', x=64, y=189, w=338, h=33, text='请确认自己的手表型号为',
         size=24, weight=S500, color=GRAY, align='left', vtop=True, lh=33),
    dict(kind='label', x=64, y=222, w=338, h=70,
         text='Xiaomi Watch S4 eSIM（非\n15 周年纪念版）',
         size=24, weight=S500, color=WHITE, align='left', vtop=True, lh=33),
    dict(kind='label', x=242, y=255, w=30, h=33, text='！',
         size=24, weight=S500, color=GRAY, align='left', vtop=True, lh=33),
    dict(kind='label', x=64, y=321, w=338, h=33, text='搞机有风险，变砖后果自负。',
         size=24, weight=S500, color=GRAY, align='left', vtop=True, lh=33),
]

PAGE_CONFIRM = [
    clock(),
    back_arrow(),
    title('开始替换', x=179, w=128),
    *WARN_LABELS,
    *big_button(365, '确认替换'),
]

# ---------------------------------------------------------------- 4. 替换中
LOG_MID = ('> 开始替换\n'
           '> 读取 resource.bin\n'
           '> 写入 12/38\n'
           '> 写入 38/38 完成，0 失败\n'
           '> 替换完毕，请重启手表。若发现问题，请回滚修改。')

PAGE_RUNNING = [
    clock(),
    title('正在替换', x=179, w=128),
    dict(kind='label', x=64, y=90, w=338, h=269, text=LOG_MID, size=24,
         weight=S500, color=WHITE, align='left', vtop=True, lh=31.82),
    *big_button(365, '重启手表'),
]

# ---------------------------------------------------------------- 5. 关于
PAGE_ABOUT = [
    clock(),
    dict(kind='image', x=191, y=43, w=17, h=28,
         src=os.path.join(ASSETS, 'backarrow.png')),
    title('关于', x=212, w=64),
    dict(kind='rect', x=52, y=79, w=362, h=204, bg=PLATE, radius=30),
    dict(kind='image', x=194, y=108, w=78, h=78,
         src=os.path.join(DOCS, 'logo_preview.png')),
    dict(kind='label', x=164, y=192, w=138, h=38, text='OS4 Icons',
         size=28, weight=S500, color=WHITE, align='left', vtop=True, lh=38),
    dict(kind='label', x=210, y=227, w=45, h=27, text='1.0.0',
         size=20, weight=S500, color=GRAY, align='left', vtop=True, lh=27),
    *item(291, 'qq.png', '732681995'),
]

PAGES = {
    'home': PAGE_HOME,
    'help': PAGE_HELP,
    'help_ok': PAGE_HELP_OK,
    'help_err': PAGE_HELP_ERR,
    'confirm': PAGE_CONFIRM,
    'about': PAGE_ABOUT,
    'running': PAGE_RUNNING,
}
