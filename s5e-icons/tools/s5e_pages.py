# -*- coding: utf-8 -*-
"""Xiaomi Watch S5 eSIM (480x480) page spec.

Same design language as the 466x466 S5->S4 face, uniformly scaled by 480/466 and
re-centred; every coordinate here is what watchface_s5e/main.lua uses, and
_tools/s5e_render_ui.py draws exactly this spec so the previews are honest.
"""
import os

from paths import PROJ, DOCS
ROOT = PROJ
ASSETS = os.path.join(ROOT, 'assets')
W = H = 480
BG = (0, 0, 0)
GRAY = '999999'
WHITE = 'ffffff'
PLATE = '002927'
CIRCLE = '4f4f4f'
OK = '43cf7c'
ERR = 'd43030'
S600, S500 = 'semibold', 'medium'

# list item geometry
ITEM_X, ITEM_W, ITEM_H, ITEM_R = 50, 379, 91, 35
ICONC_DX, ICONC_DY, ICONC_SZ = 21, 20, 52
ICON_DX, ICON_DY, ICON_SZ = 31, 30, 31
TITLE_DX, TITLE_DY, TITLE_W, TITLE_H = 82, 26, 214, 40
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
    return dict(kind='label', x=201, y=4, w=78, h=46, text=t, size=29,
                weight=S600, color=GRAY, align='left', vtop=True)


def title(text, x, w=260):
    return dict(kind='label', x=x, y=36, w=w, h=46, text=text, size=31,
                weight=S500, color=WHITE, align='left', vtop=True)


def back_arrow(x=167):
    return dict(kind='image', x=x, y=44, w=18, h=29, src=os.path.join(ASSETS, 'backarrow.png'))


def big_button(y, text):
    return [
        dict(kind='rect', x=111, y=y, w=258, h=82, bg=PLATE, radius=41),
        dict(kind='label', x=182, y=y + 22, w=126, h=40, text=text, size=29,
             weight=S500, color=WHITE, align='left', vtop=True),
    ]


PAGE_HOME = [clock(), title('OS4 Icons', 164, 152),
             *item(88, 'ic_help', '快速帮助'),
             *item(186, 'ic_replace', '开始替换'),
             *item(285, 'ic_about', '关于')]

_HELP_HEAD = [clock(), back_arrow(167), title('快速帮助', 188, 124)]
_HELP_D1 = dict(kind='label', x=67, y=182, w=348, h=76,
                text='检查 app / health 两个分区\n与 47 条负载的完整性。', size=25,
                weight=S500, color=GRAY, align='left', vtop=True)
_HELP_I2 = item(264, 'ic_rollback', '回滚修改')
_HELP_D2 = dict(kind='label', x=67, y=355, w=348, h=36,
                text='恢复 47 个图标的原始样式。', size=25,
                weight=S500, color=GRAY, align='left', vtop=True)
PAGE_HELP = _HELP_HEAD + item(88, 'ic_check', '环境预检查') + [_HELP_D1] + _HELP_I2 + [_HELP_D2]

HELP_DESC_OK = dict(kind='label', x=67, y=182, w=348, h=76,
                    text='预检查通过 | 47 条 | 3.72MB\n两个分区都可读。',
                    size=25, weight=S500, color=OK, align='left', vtop=True)
HELP_DESC_ERR = dict(kind='label', x=67, y=182, w=348, h=76,
                     text='预检查失败：设备节点不可读\n或分区头不是 ROMFS。',
                     size=25, weight=S500, color=ERR, align='left', vtop=True)
PAGE_HELP_OK = _HELP_HEAD + item(88, 'ic_check', '环境预检查') + [HELP_DESC_OK] + _HELP_I2 + [_HELP_D2]
PAGE_HELP_ERR = _HELP_HEAD + item(88, 'ic_check', '环境预检查') + [HELP_DESC_ERR] + _HELP_I2 + [_HELP_D2]

WARN_LABELS = [
    dict(kind='label', x=60, y=93, w=360, h=36,
         text='替换图标包之前，请先确认自己', size=25, weight=S500, color=GRAY,
         align='left', vtop=True),
    dict(kind='label', x=60, y=126, w=360, h=36,
         text='的系统版本号为 ', size=25, weight=S500, color=GRAY, align='left', vtop=True),
    dict(kind='label', x=244, y=126, w=120, h=36, text='3.112.035',
         size=25, weight=S500, color=WHITE, align='left', vtop=True),
    dict(kind='label', x=356, y=126, w=40, h=36, text='！',
         size=25, weight=S500, color=GRAY, align='left', vtop=True),
    dict(kind='label', x=60, y=196, w=360, h=36, text='请确认自己的手表型号为',
         size=25, weight=S500, color=GRAY, align='left', vtop=True),
    dict(kind='label', x=60, y=229, w=372, h=36, text='Xiaomi Watch S5 eSIM 46mm',
         size=25, weight=S500, color=WHITE, align='left', vtop=True),
    dict(kind='label', x=427, y=229, w=40, h=36, text='！',
         size=25, weight=S500, color=GRAY, align='left', vtop=True),
    dict(kind='label', x=60, y=331, w=360, h=36, text='搞机有风险，变砖后果自负。',
         size=25, weight=S500, color=GRAY, align='left', vtop=True),
]
PAGE_CONFIRM = [clock(), back_arrow(167), title('开始替换', 188, 124)] + WARN_LABELS + big_button(376, '确认替换')

LOG_MID = ('> 开始替换\n'
           '> app 33 条 / health 14 条\n'
           '> 写入 20/47\n'
           '> 替换完毕，请重启手表。\n'
           '> 若发现问题，请回滚修改。')
PAGE_RUNNING = [clock(), title('正在替换', 178, 124),
                dict(kind='label', x=67, y=93, w=348, h=277, text=LOG_MID, size=25,
                     weight=S500, color=WHITE, align='left', vtop=True),
                *big_button(376, '重启手表')]

PAGE_ABOUT = [
    clock(), back_arrow(198), title('关于', 220, 62),
    dict(kind='rect', x=54, y=81, w=373, h=210, bg=PLATE, radius=31),
    dict(kind='image', x=200, y=111, w=80, h=80, src=os.path.join(DOCS, 'logo_preview_480.png')),
    dict(kind='label', x=170, y=198, w=141, h=40, text='OS4 Icons',
         size=29, weight=S500, color=WHITE, align='left', vtop=True),
    dict(kind='label', x=216, y=234, w=49, h=28, text='1.0.0',
         size=21, weight=S500, color=GRAY, align='left', vtop=True),
    *item(300, 'ic_qq', '732681995'),
]

PAGES = {'home': PAGE_HOME, 'help': PAGE_HELP, 'help_ok': PAGE_HELP_OK, 'help_err': PAGE_HELP_ERR,
         'confirm': PAGE_CONFIRM, 'running': PAGE_RUNNING, 'about': PAGE_ABOUT}
