# -*- coding: utf-8 -*-
"""Xiaomi Watch S5 eSIM 46mm（480x480）页面规格 + 本机渲染器。

设计语言与 466x466 的 S4e 版一致，整体按 480/466 放大并重新居中；坐标就是
main.lua 里实际用的坐标（tools/render_ui.py 严格按本文件渲染，tools/check_clip.py
拿**真实渲染像素**判圆屏是否切边），所以预览图是诚实的。

CSS -> 实际能力 的映射（真机验证过）:
    left/top/width/height  -> x / y / w / h（480 画布绝对坐标）
    background             -> bg_color
    border-radius          -> radius
    color (alpha 1)        -> text_color '#rrggbb'
    color (alpha 0.6)      -> 白 60% 叠在纯黑底上 = #999999
    font-weight 600        -> MiSans-Semibold ; 500 -> MiSans-Medium
    多色文本               -> **不能**用 LVGL recolor（会被原样显示），拆成多个标签 + 手工算 x
"""
import os

from paths import PROJ, DOCS
ROOT = PROJ
ASSETS = os.path.join(ROOT, 'assets')
W = H = 480
BG = (0, 0, 0)                 # 页面底色纯黑
GRAY = '999999'                # rgba(255,255,255,0.6) 叠黑
WHITE = 'ffffff'
PLATE = '002927'               # rgba(0,41,39,1)
CIRCLE = '4f4f4f'              # rgba(79,79,79,1)
OK = '43cf7c'                  # rgba(67,207,124,1)
ERR = 'd43030'                 # rgba(212,48,48,1)
S600, S500 = 'semibold', 'medium'

# 列表项几何（480 档；= 466 档 × 480/466 后取整）
ITEM_X, ITEM_W, ITEM_H, ITEM_R = 50, 379, 91, 35
ICONC_DX, ICONC_DY, ICONC_SZ = 21, 20, 52
ICON_DX, ICON_DY, ICON_SZ = 31, 30, 31
TITLE_DX, TITLE_DY, TITLE_W, TITLE_H = 82, 26, 214, 40
# 说明文字的公共框（比 466 档宽一点：中文 25px 一行放得下，且右边界仍在圆内）
DESC_X, DESC_W = 60, 372
ICON_PNG = {'ic_help': 'MdiLightbulbOutline.png', 'ic_replace': 'MdiBandage.png',
            'ic_about': 'MdiInformationOutline.png', 'ic_check': 'MdiClipboardTextSearchOutline.png',
            'ic_rollback': 'MdiReplyAllOutline.png', 'ic_qq': 'qq.png'}


def item(y, iconkey, title):
    """一个列表项：底板(整块可点) + 圆形遮罩 + 图标 + 标题。"""
    return [
        dict(kind='rect', x=ITEM_X, y=y, w=ITEM_W, h=ITEM_H, bg=PLATE, radius=ITEM_R),
        dict(kind='circle', x=ITEM_X + ICONC_DX, y=y + ICONC_DY, w=ICONC_SZ, h=ICONC_SZ, bg=CIRCLE),
        dict(kind='image', x=ITEM_X + ICON_DX, y=y + ICON_DY, w=ICON_SZ, h=ICON_SZ,
             src=os.path.join(ASSETS, ICON_PNG[iconkey])),
        # 标题行高 40（29px 字体），框高 40 -> 垂直居中 y = 26 + (40-40)/2 = 26
        dict(kind='label', x=ITEM_X + TITLE_DX, y=y + TITLE_DY, w=TITLE_W, h=TITLE_H,
             text=title, size=29, weight=S500, color=WHITE, align='left', vtop=True),
    ]


def clock(t='10:24'):
    return dict(kind='label', x=201, y=4, w=78, h=46, text=t, size=29,
                weight=S600, color=GRAY, align='left', vtop=True)


def title(text, x, w):
    return dict(kind='label', x=x, y=36, w=w, h=46, text=text, size=31,
                weight=S500, color=WHITE, align='left', vtop=True)


def back_arrow(x=167):
    return dict(kind='image', x=x, y=44, w=18, h=29, src=os.path.join(ASSETS, 'backarrow.png'))


def big_button(y, text):
    """大按钮：258x82 圆角 41 —— 圆角把四角收进圆内（本机像素判据实测 0 越界）。"""
    return [
        dict(kind='rect', x=111, y=y, w=258, h=82, bg=PLATE, radius=41),
        dict(kind='label', x=182, y=y + 22, w=126, h=40, text=text, size=29,
             weight=S500, color=WHITE, align='left', vtop=True),
    ]


# ---------------------------------------------------------------- 1. 首页
# 标题按真字体宽度居中：'S5e Pt.3' 31px 量得 126 -> x = (480-126)/2 = 177
PAGE_HOME = [clock(), title('S5e Pt.3', 177, 128),
             *item(88, 'ic_help', '快速帮助'),
             *item(186, 'ic_replace', '开始替换'),
             *item(285, 'ic_about', '关于')]

# ---------------------------------------------------------------- 2. 快速帮助
_HELP_HEAD = [clock(), back_arrow(167), title('快速帮助', 188, 124)]
# 说明文字固定 2 行（显式换行），框高 76 = 2 × 行高 35 + 余量
HELP_DESC_DEF = dict(kind='label', x=DESC_X, y=182, w=DESC_W, h=76,
                     text='检查 /dev/system 分区与\n61 帧充电动画的完整性。', size=25,
                     weight=S500, color=GRAY, align='left', vtop=True)
HELP_DESC_OK = dict(kind='label', x=DESC_X, y=182, w=DESC_W, h=76,
                    text='预检查通过 | 61 条 | 11.27MB\n您可以返回主页开始修改。',
                    size=25, weight=S500, color=OK, align='left', vtop=True)
HELP_DESC_ERR = dict(kind='label', x=DESC_X, y=182, w=DESC_W, h=76,
                     text='预检查失败：设备节点不可读\n或分区头不是 ROMFS。',
                     size=25, weight=S500, color=ERR, align='left', vtop=True)
HELP_DESC_TIP = dict(kind='label', x=DESC_X, y=182, w=DESC_W, h=76,
                     text='本盘只负责替换，请装\nS5e Pt.3 · 还原。',
                     size=25, weight=S500, color=GRAY, align='left', vtop=True)
HELP_D1 = dict(kind='label', x=DESC_X, y=355, w=DESC_W, h=36,
               text='还原请装 S5e Pt.3 · 还原。', size=25, weight=S500, color=GRAY,
               align='left', vtop=True)
HELP_DESC_TIP_RB = dict(kind='label', x=DESC_X, y=182, w=DESC_W, h=76,
                        text='本盘负责还原，换回动画\n请装 S5e Pt.3。',
                        size=25, weight=S500, color=GRAY, align='left', vtop=True)
HELP_D1_RB = dict(kind='label', x=DESC_X, y=355, w=DESC_W, h=36,
                  text='换回动画请装 S5e Pt.3。', size=25, weight=S500, color=GRAY,
                  align='left', vtop=True)


def _help_page(desc, d1=None):
    return (_HELP_HEAD + item(88, 'ic_check', '环境预检查') + [desc]
            + item(264, 'ic_rollback', '回滚修改') + [d1 or HELP_D1])


PAGE_HELP = _help_page(HELP_DESC_DEF)
PAGE_HELP_OK = _help_page(HELP_DESC_OK)
PAGE_HELP_ERR = _help_page(HELP_DESC_ERR)
PAGE_HELP_TIP = _help_page(HELP_DESC_TIP)

# ---------------------------------------------------------------- 3. 开始替换（警告确认页）
# 每个片段都用真 MiSans 25px 量过宽度，框宽 ≥ 文本宽 -> 保证**不折行**（折行会让
# 手工算 x 的多色片段错位），并且整框都在圆内（check_clip 用渲染像素实测）。
WARN_LABELS = [
    dict(kind='label', x=52, y=93, w=340, h=36,
         text='替换充电动画之前，请先确认', size=25, weight=S500, color=GRAY,
         align='left', vtop=True),
    dict(kind='label', x=52, y=126, w=380, h=36,
         text='自己的系统版本号为 3.112.035！', size=25, weight=S500, color=GRAY,
         align='left', vtop=True),
    dict(kind='label', x=52, y=208, w=280, h=36, text='请确认自己的手表型号为',
         size=25, weight=S500, color=GRAY, align='left', vtop=True),
    dict(kind='label', x=52, y=241, w=405, h=36, text='Xiaomi Watch S5 eSIM 46mm ！',
         size=25, weight=S500, color=WHITE, align='left', vtop=True),
    dict(kind='label', x=52, y=331, w=330, h=36, text='搞机有风险，变砖后果自负。',
         size=25, weight=S500, color=GRAY, align='left', vtop=True),
]
PAGE_CONFIRM = ([clock(), back_arrow(167), title('开始替换', 188, 124)] +
                WARN_LABELS + big_button(376, '确认替换'))

# ---------------------------------------------------------------- 4. 替换中
LOG_MID = ('> 开始替换\n'
           '> 读取 resource.bin\n'
           '> 写入 40/61  失败 0\n'
           '> 替换完毕，请重启手表。\n'
           '> 若发现问题，请回滚修改。')
LOG_END = ('> 开始替换\n'
           '> 读取 resource.bin\n'
           '> 写入 61/61  失败 0\n'
           '> 共 61 条，失败 0 条\n'
           '> 版本不符跳过 0 条')
PAGE_RUNNING = [clock(), title('正在替换', 178, 124),
                dict(kind='label', x=67, y=93, w=348, h=277, text=LOG_MID, size=25,
                     weight=S500, color=WHITE, align='left', vtop=True),
                *big_button(376, '重启手表')]
PAGE_RUNNING_END = [clock(), title('正在替换', 178, 124),
                    dict(kind='label', x=67, y=93, w=348, h=277, text=LOG_END, size=25,
                         weight=S500, color=WHITE, align='left', vtop=True),
                    *big_button(376, '重启手表')]

# ---------------------------------------------------------------- 5. 关于
# 卡片 373 宽：'S5e Pt.3' 29px 量得 119 -> x = 54 + (373-119)/2 = 181（整）
# '1.0.0' 21px 量得 49 -> x = 54 + (373-49)/2 = 216
PAGE_ABOUT = [
    clock(), back_arrow(198), title('关于', 220, 62),
    dict(kind='rect', x=54, y=81, w=373, h=210, bg=PLATE, radius=31),
    dict(kind='image', x=200, y=111, w=80, h=80, src=os.path.join(DOCS, 'logo_preview_480.png')),
    dict(kind='label', x=181, y=198, w=121, h=40, text='S5e Pt.3',
         size=29, weight=S500, color=WHITE, align='left', vtop=True),
    dict(kind='label', x=216, y=234, w=49, h=28, text='1.0.0',
         size=21, weight=S500, color=GRAY, align='left', vtop=True),
    *item(300, 'ic_qq', '732681995'),
]

PAGES = {'home': PAGE_HOME, 'help': PAGE_HELP, 'help_ok': PAGE_HELP_OK, 'help_err': PAGE_HELP_ERR,
         'help_tip': PAGE_HELP_TIP, 'confirm': PAGE_CONFIRM, 'running': PAGE_RUNNING,
         'running_end': PAGE_RUNNING_END, 'about': PAGE_ABOUT}


# ---------------------------------------------------------------- 还原盘（ROLE=restore）的文案
# 同一套坐标，只换文字。文字比替换盘长的（首页标题 / 关于卡片大标题：加了 " · 还原"）
# 必须把 x / w 一起重新按真字体宽度居中 —— check_clip.py 会把 PAGES_ALT 一起渲染并测量。
def _swap(items, old, new, x=None, w=None):
    out = []
    for it in items:
        if it.get('kind') == 'label' and it['text'] == old:
            it = dict(it, text=new)
            if x is not None:
                it['x'] = x
            if w is not None:
                it['w'] = w
        out.append(it)
    return out


PAGES_ALT = {
    'home': _swap(PAGE_HOME, 'S5e Pt.3', 'S5e Pt.3 · 还原', x=127, w=228),
    'home_item2': _swap(PAGE_HOME, '开始替换', '开始还原'),
    'help_d1': _help_page(HELP_DESC_DEF, HELP_D1_RB),
    'help_tip': _help_page(HELP_DESC_TIP_RB, HELP_D1_RB),
    'confirm': _swap(PAGE_CONFIRM, '开始替换', '开始还原'),
    'confirm_btn': _swap(PAGE_CONFIRM, '确认替换', '确认还原'),
    'running': _swap(PAGE_RUNNING, '正在替换', '正在回滚'),
    'about': _swap(PAGE_ABOUT, 'S5e Pt.3', 'S5e Pt.3 · 还原', x=134, w=214),
}
