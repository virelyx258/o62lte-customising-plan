"""overlay + 官方模板 -> Compiler.exe -> .face（两份盘共用同一个 watchface id）

要点（都是踩过的坑）：
  * preview.png 必须是 326x326，Compiler.exe 会直接拒绝别的尺寸
  * watchfaceId 要带机型家族前缀：S4 家族 = 362150xxx
  * 用 Python 的 copytree 拷目录，别用 PowerShell 的 Copy-Item -Recurse（会拍平）
  * replace 盘与 restore 盘用**同一个 id**：装一份就顶掉另一份，设备上只占一份空间
"""
import os, json, shutil, subprocess, sys
from paths import WORK, TEMPLATE

TPL = TEMPLATE
OVER = os.path.join(WORK, 'overlay')
BUILD = os.path.join(WORK, 'build')

TARGETS = {'S4PAnim': ('362150102', 'S5 41mm 压力检测动画 -> S4 eSIM（只写负载）'),
           'S4PAnimRestore': ('362150102', 'S4 eSIM 压力检测动画还原盘（只写原厂字节）')}


def prepare(name):
    oid, _ = TARGETS[name]
    ov = os.path.join(OVER, name)
    dst = os.path.join(BUILD, name)
    if not os.path.exists(TPL):
        raise SystemExit('找不到官方模板：%s\n请把 FangAiden/LuaDevTemplate 放到 vendor/ 下（见 README）' % TPL)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(TPL, dst)

    old = os.path.join(dst, 'watchface', 'fprj', 'LuaDevTemplate.fprj')
    if os.path.exists(old):
        os.remove(old)

    cfg = json.load(open(os.path.join(ov, 'watchface.config.json'), encoding='utf-8'))
    cfg['watchfaceId'] = oid
    json.dump(cfg, open(os.path.join(dst, 'watchface.config.json'), 'w', encoding='utf-8'),
              indent=4, ensure_ascii=False)

    shutil.copyfile(os.path.join(ov, 'watchface', 'fprj', name + '.fprj'),
                    os.path.join(dst, 'watchface', 'fprj', name + '.fprj'))
    # projectName 现在就是「手表上显示的表盘名」（见 make_overlays.py 的 DISPLAY_NAME）。
    # 官方 scripts/build_face.ps1 先跑 sync_watchface_config.ps1：它按 projectName 找
    # watchface/fprj/<projectName>.fprj，找不到就把目录里**唯一**那份 .fprj 改名成它，
    # 并把该 fprj 的 <Screen Title> 覆盖成 projectName —— 所以这条流水线里真正进 .face 的
    # 显示名就是这个 projectName。注意 fprj 目录里必须**只有一份** .fprj：Compiler.exe 会
    # 按目录里每份 .fprj 把资源各打包一遍，多放一份副本会让 .face 直接翻倍。
    disp = cfg['projectName']
    shutil.copyfile(os.path.join(ov, 'watchface', 'fprj', 'images', 'preview.png'),
                    os.path.join(dst, 'watchface', 'fprj', 'images', 'preview.png'))
    shutil.copyfile(os.path.join(ov, 'watchface', 'fprj', 'app', 'lua', 'main.lua'),
                    os.path.join(dst, 'watchface', 'fprj', 'app', 'lua', 'main.lua'))

    img = os.path.join(dst, 'watchface', 'fprj', 'app', 'images')
    os.makedirs(img, exist_ok=True)
    ovimg = os.path.join(ov, 'watchface', 'fprj', 'app', 'images')
    for d in sorted(x for x in os.listdir(ovimg) if os.path.isdir(os.path.join(ovimg, x))):
        tgt = os.path.join(img, d)
        if os.path.exists(tgt):
            shutil.rmtree(tgt)
        shutil.copytree(os.path.join(ovimg, d), tgt)
        print('   %s: app/images/%s/ -> %d files' % (name, d, len(os.listdir(tgt))))
    return dst, cfg['projectName']


def workspace_fprj(dst):
    """把工作区里的 .fprj 归一成 <name>.fprj，并返回它的路径。

    我们拷进去时是 <name>.fprj，但 vendor 的 build_face.ps1 会先跑
    sync_watchface_config.ps1：它按 config 的 projectName（现在是**显示名** S4e Pt.2）找
    <projectName>.fprj，找不到就把目录里**唯一**那份改名过去（<Screen Title> 也被改写成
    projectName）。编完这里再改回 <name>.fprj —— 工作区里始终只有一份 .fprj（放两份会被
    Compiler.exe 并成双倍资源），文件名保持项目标识不变，下游 finalize_faces.compile_raw /
    gen_ui_lua 仍能按 fprj/<name>.fprj 找到它。
    多于一份 / 一份都没有都直接报错，不静默放过。
    """
    name = os.path.basename(dst)
    d = os.path.join(dst, 'watchface', 'fprj')
    fs = sorted(f for f in os.listdir(d) if f.endswith('.fprj'))
    if len(fs) != 1:
        raise SystemExit('%s: watchface/fprj 下的 .fprj 应恰好 1 份，实际：%s' % (name, fs))
    want = os.path.join(d, name + '.fprj')
    if fs[0] != name + '.fprj':
        os.replace(os.path.join(d, fs[0]), want)
    return want


def build(dst, name, disp):
    ps = os.path.join(dst, 'scripts', 'build_face.ps1')
    # 显式指定产物名：build_face.ps1 默认按 projectName（现在 = 显示名，可能带空格/点）命名产物，
    # 这里仍然用 NAME，保证 bin/<NAME>.face、dist/<NAME>.face 这些标识路径不变。
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps,
                        '-FaceName', name + '.face'],
                       capture_output=True, text=True, errors='replace')
    # sync 已经把 .fprj 改名成 <显示名>.fprj（里面的 <Screen Title> 也写成了显示名）；
    # 这里改回 NAME，好让下游 finalize_faces.compile_raw 仍按 fprj/<NAME>.fprj 找它。
    fprj = workspace_fprj(dst)
    print('   fprj 归一：%s' % os.path.relpath(fprj, dst))
    for l in [x for x in (r.stdout or '').splitlines() if x.strip()][-6:]:
        print('   |', l)
    if r.returncode != 0:
        print('   !! build failed, rc=', r.returncode)
        return False
    # 官方脚本按 projectName 命名产物（bin/<显示名>.face）；-FaceName 已经把它压成 NAME，
    # 万一没生效，这里再兜一次（内容一样，只差文件名）。
    face = os.path.join(dst, 'bin', name + '.face')
    alt = os.path.join(dst, 'bin', disp + '.face')
    if disp != name and os.path.exists(alt) and not os.path.exists(face):
        os.replace(alt, face)
    return True


if __name__ == '__main__':
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name in TARGETS:
        if only and name != only:
            continue
        print('== %s (id=%s) ==' % (name, TARGETS[name][0]))
        dst, disp = prepare(name)
        build(dst, name, disp)
        face = os.path.join(dst, 'bin', name + '.face')
        if os.path.exists(face):
            print('   OK  %s  %d bytes' % (face, os.path.getsize(face)))
        else:
            print('   missing output')
