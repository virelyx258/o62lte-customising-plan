"""项目里所有脚本的路径入口 —— 换机器 / 换目录只看这一个文件。

默认布局（都相对项目根）：
    inputs/target/   目标固件的分区镜像（要自己放，见 README）
    inputs/source/   素材来源的分区镜像（要自己放）
    inputs/fonts/    可选：MiSans-*.ttf（渲染预览用；不给就从 vela_font.bin 里取）
    vendor/          第三方 LuaDevTemplate-main（里面有 Compiler.exe，要自己放）
    .work/           构建工作区（产物，可删）
    dist/            交付的 .face
    docs/            说明与预览图

环境变量可覆盖：ICON_EDIT_INPUTS / ICON_EDIT_VENDOR / ICON_EDIT_WORK /
                ICON_EDIT_DIST / ICON_EDIT_DOCS / ICON_EDIT_FONTS
"""
import os

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _p(env, default):
    return os.environ.get(env) or os.path.join(PROJ, default)


INPUTS = _p('ICON_EDIT_INPUTS', 'inputs')
VENDOR = _p('ICON_EDIT_VENDOR', 'vendor')
WORK = _p('ICON_EDIT_WORK', '.work')
DIST = _p('ICON_EDIT_DIST', 'dist')
DOCS = _p('ICON_EDIT_DOCS', 'docs')
FONTS = os.environ.get('ICON_EDIT_FONTS') or os.path.join(INPUTS, 'fonts')
TEMPLATE = os.path.join(VENDOR, 'LuaDevTemplate-main')
INPUT_TARGET = os.path.join(INPUTS, 'target')
INPUT_SOURCE = os.path.join(INPUTS, 'source')
ASSETS = os.path.join(PROJ, 'assets')

for _d in (WORK, DIST, DOCS, INPUT_TARGET, INPUT_SOURCE):
    os.makedirs(_d, exist_ok=True)

# ------------------------------------------------------------------ 本项目的事实
# 目标：Xiaomi Watch S5 eSIM 46mm（p62lte, 480x480, Lua 5.4 宿主）
# 素材来源：Xiaomi Watch S5 41mm（q63, v4.101.020）
TARGET_IMAGE = os.path.join(INPUT_TARGET, 'vela_health.bin')   # 要改的分区（卷名就是 health）
SOURCE_IMAGE = os.path.join(INPUT_SOURCE, 'vela_app.bin')      # q63 的 100 帧在这里
TARGET_VOLUME = 'health'
DIRP = 'pressure/measure/'
FACE_W = FACE_H = 464          # 槽位是 464x464 I8 + RLE
SRC_W = SRC_H = 480            # q63 的帧是 480x480
SCREEN = 480                   # 表盘界面 480x480
WF_ID = '462150102'            # 两份盘共用（462 = S5 家族）
DEVICE_TYPE = '462'
PREVIEW = 326                  # Compiler.exe 对 462 设备强制 326x326
