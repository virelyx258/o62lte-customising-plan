"""项目里所有脚本的路径入口 —— 换机器 / 换目录只看这一个文件。

默认布局（都相对项目根）：
    inputs/target/   目标固件的分区镜像（要自己放，见 README）
    inputs/source/   图标来源的分区镜像（要自己放）
    inputs/fonts/    可选：MiSans-Medium.ttf / MiSans-Semibold.ttf（渲染预览用）
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

for _d in (WORK, DIST, DOCS, INPUT_TARGET, INPUT_SOURCE):
    os.makedirs(_d, exist_ok=True)
