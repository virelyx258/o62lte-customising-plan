# -*- coding: utf-8 -*-
"""Xiaomi Watch S5 eSIM (p62lte) 480x480 页面规格。

坐标系就是 `main.lua` 用的那一套；`s5e_render_ui.py` / `s5e_check_clip.py` 画的是同一份规格，
所以预览图是"诚实"的（不是另画一套）。与 S5 图标包那份 480 设计稿同一套语言，
只是页面文案改成压力动画替换器。
"""
import os

from paths import PROJ, DOCS, ASSETS
W = H = 480
BG = (0, 0, 0)
GRAY = '999999'
WHITE = 'ffffff'
PLATE = '002927'
CIRCLE = '4f4f4f'
OK = '43cf7c'
ERR = 'd43030'
S600, S500, S400 = 'semibold', 'medium', 'regular'

# 列表项几何
# radius=40 不是审美选择：y=88 那一行离圆心 152px，圆屏在那里的弦半宽只有 √(240²-152²)=185.8，
# 也就是该行 x 只能在 54.2..425.8 之内。底板是 x=50 w=379，圆角不够大时四个角会越过圆边
# （r=35 时角点半径 240.7 → check_clip 记为越界）。r=40 正好把角收进去。
ITEM_X, ITEM_W, ITEM_H, ITEM_R = 50, 379, 91, 40
ICONC_DX, ICONC_DY, ICONC_SZ = 21, 20, 52
ICON_DX, ICON_DY, ICON_SZ = 31, 30, 31
TITLE_DX, TITLE_DY, TITLE_W, TITLE_H = 82, 26, 214, 42
ICON_PNG = {'ic_help': 'MdiLightbulbOutline.png', 'ic_replace': 'MdiBandage.png',
            'ic_about': 'MdiInformationOutline.png', 'ic_check': 'MdiClipboardTextSearchOutline.png',
            'ic_rollback': 'MdiReplyAllOutline.png', 'ic_qq': 'qq.png'}


def item(y, iconkey, title):
    return [
        dict(kind='rect', x=ITEM_X, y=y, w=ITEM_W, h=ITEM_H, bg=PLATE, radius=ITEM_R),
        dict(kind='circle', x=ITEM_X + ICONC_DX, y=y + ICONC_DY, w=ICONC_SZ, h=ICONC_SZ, bg=CIRCLE),
        dict(kind='image', x=ITEM_X + ICON_DX, y=y + ICON_DY, w=ICON_SZ, h=ICON_SZ,
             src=os.path.join(ASSETS, ICON_PNG[iconkey])),
        dict(kind='label', x=ITEM_X + TITLE_DX, y=y + TITLE_DY, w=TITLE_W, h=TITLE_H,
             text=title, size=29, weight=S500, color=WHITE, align='left', vtop=True),
    ]


def clock(t='10:24'):
    return dict(kind='label', x=201, y=4, w=78, h=40, text=t, size=29,
                weight=S600, color=GRAY, align='left', vtop=True)


def title(text, x, w=260):
    return dict(kind='label', x=x, y=36, w=w, h=42, text=text, size=31,
                weight=S500, color=WHITE, align='left', vtop=True)


def back_arrow(x=167):
    return dict(kind='image', x=x, y=44, w=18, h=29, src=os.path.join(ASSETS, 'backarrow.png'))


def big_button(y, text):
    return [
        dict(kind='rect', x=111, y=y, w=258, h=82, bg=PLATE, radius=41),
        dict(kind='label', x=182, y=y + 22, w=126, h=40, text=text, size=29,
             weight=S500, color=WHITE, align='left', vtop=True),
    ]


# ------------------------------------------------------------------ 页面
# 所有文字的像素宽度都用真 MiSans 量过（tools/s5e_render_ui.py 同一套字体）：
#   31px: 'S5e Pt.2'=125  '快速帮助'/'开始替换'/'正在替换'=124  '关于'=62
#   29px: '确认替换'/'重启手表'=116  '环境预检查'=145  '732681995'=155
#   25px: '检查 health 分区与负载完整性。'=369  '恢复 119 帧动画的原厂样式。'=331
#         '预检查通过 | 119 条 | 15.49MB'=349  'Xiaomi Watch S5 eSIM 46mm'=367
# 圆屏在高度 y 处的弦半宽 = √(240² - (y-240)²)，所以**越靠下的行越窄** ——
# 型号那行原来放在 y=229（弦半宽只有 171），'Xiaomi Watch S5 eSIM 46mm' 宽 367 直接被切掉。
# 现在把该行拆成两行、整体上移到 y=195 / 228，两行都短于那里的弦。
PAGE_HOME = [clock(), title('S5e Pt.2', 177, 127),
             *item(88, 'ic_help', '快速帮助'),
             *item(186, 'ic_replace', '开始替换'),
             *item(285, 'ic_about', '关于')]

_HELP_HEAD = [clock(), back_arrow(167), title('快速帮助', 188, 124)]
# 说明文字必须**单行**放下（折行后第 2 行会越出圆屏，check_clip 抓过）：
# y=182 处圆屏弦半宽 = √(240²-58²) = 232.9，x 从 64 起时最多能到 64+232.9 = 296.9...
# 实际用 380 的框宽是安全的（文字宽 354px < 380，且落在 64..444 内）。
_HELP_D1 = dict(kind='label', x=64, y=182, w=380, h=35,
                text='检查 health 分区与负载完整性。', size=24,
                weight=S500, color=GRAY, align='left', vtop=True)
_HELP_I2 = item(264, 'ic_rollback', '回滚修改')
_HELP_D2 = dict(kind='label', x=67, y=360, w=348, h=35,
                text='恢复 119 帧动画的原厂样式。', size=25,
                weight=S500, color=GRAY, align='left', vtop=True)
PAGE_HELP = _HELP_HEAD + item(88, 'ic_check', '环境预检查') + [_HELP_D1] + _HELP_I2 + [_HELP_D2]

# 预检查结果：最多 2 行（24px 行高 33，框高 76 >= 2*33）
HELP_DESC_OK = dict(kind='label', x=67, y=182, w=348, h=76,
                    text='预检查通过 | 119 条 | 15.49MB\nhealth 分区可读。',
                    size=24, weight=S500, color=OK, align='left', vtop=True)
HELP_DESC_ERR = dict(kind='label', x=67, y=182, w=348, h=76,
                     text='预检查失败：设备节点读不到，\n或分区头不是 ROMFS。',
                     size=24, weight=S500, color=ERR, align='left', vtop=True)
PAGE_HELP_OK = _HELP_HEAD + item(88, 'ic_check', '环境预检查') + [HELP_DESC_OK] + _HELP_I2 + [_HELP_D2]
PAGE_HELP_ERR = _HELP_HEAD + item(88, 'ic_check', '环境预检查') + [HELP_DESC_ERR] + _HELP_I2 + [_HELP_D2]

# 警告页：每行单独一个框（h=34 ≈ 25px 真行高 35），行距 34。
# 最下面那行放在 y=341：圆屏在 y=375 处正好收成一点，所以底边必须留在 375 以上。
WARN_LABELS = [
    dict(kind='label', x=60, y=95, w=360, h=35,
         text='替换压力检测动画之前，', size=25, weight=S500, color=GRAY,
         align='left', vtop=True),
    dict(kind='label', x=60, y=129, w=360, h=35,
         text='请先确认自己的系统版本号为 ', size=25, weight=S500, color=GRAY, align='left', vtop=True),
    dict(kind='label', x=304, y=129, w=120, h=35, text='3.112.035',
         size=25, weight=S500, color=WHITE, align='left', vtop=True),
    dict(kind='label', x=422, y=129, w=40, h=35, text='！',
         size=25, weight=S500, color=GRAY, align='left', vtop=True),
    # 型号拆成两行：y=195 处弦半宽 195，y=228 处 173 —— 367px 的长行只能拆
    dict(kind='label', x=64, y=195, w=360, h=35, text='请确认自己的手表型号为',
         size=25, weight=S500, color=GRAY, align='left', vtop=True),
    dict(kind='label', x=64, y=229, w=360, h=35, text='Xiaomi Watch S5',
         size=25, weight=S500, color=WHITE, align='left', vtop=True),
    dict(kind='label', x=64, y=263, w=360, h=35, text='eSIM 46mm（p62lte）',
         size=25, weight=S500, color=WHITE, align='left', vtop=True),
    dict(kind='label', x=60, y=341, w=360, h=35, text='搞机有风险，变砖后果自负。',
         size=25, weight=S500, color=GRAY, align='left', vtop=True),
]
PAGE_CONFIRM = [clock(), back_arrow(167), title('开始替换', 188, 124)] + WARN_LABELS + big_button(376, '确认替换')

LOG_MID = ('> 开始替换\n'
           '> health 119 条\n'
           '> 写入 60/119 成 60 失 0\n'
           '> 替换完毕，请重启手表。\n'
           '> 若发现问题，请回滚修改。')
PAGE_RUNNING = [clock(), title('正在替换', 178, 124),
                dict(kind='label', x=67, y=95, w=348, h=280, text=LOG_MID, size=24,
                     weight=S500, color=WHITE, align='left', vtop=True),
                *big_button(376, '重启手表')]

PAGE_ABOUT = [
    clock(), back_arrow(198), title('关于', 220, 62),
    dict(kind='rect', x=54, y=81, w=373, h=210, bg=PLATE, radius=31),
    dict(kind='image', x=200, y=111, w=80, h=80, src=os.path.join(DOCS, 'logo_preview_480.png')),
    dict(kind='label', x=181, y=200, w=120, h=40, text='S5e Pt.2',
         size=29, weight=S500, color=WHITE, align='left', vtop=True),
    dict(kind='label', x=222, y=237, w=49, h=28, text='1.0.0',
         size=21, weight=S500, color=GRAY, align='left', vtop=True),
    *item(300, 'ic_qq', '732681995'),
]

PAGES = {'home': PAGE_HOME, 'help': PAGE_HELP, 'help_ok': PAGE_HELP_OK, 'help_err': PAGE_HELP_ERR,
         'confirm': PAGE_CONFIRM, 'running': PAGE_RUNNING, 'about': PAGE_ABOUT}
