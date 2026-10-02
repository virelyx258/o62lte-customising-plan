"""overlay + 官方模板 -> Compiler.exe -> .face

要点（都是踩过的坑）：
  * preview.png 必须是 326x326，Compiler.exe 会直接拒绝别的尺寸
  * watchfaceId 要带机型家族前缀：S4 家族 = 362150xxx（固件自带表盘是 362150004..7）
  * 用 Python 的 copytree 拷目录，别用 PowerShell 的 Copy-Item -Recurse（会拍平）
"""
import os, json, shutil, subprocess, sys
from paths import WORK, TEMPLATE

TPL = TEMPLATE
OVER = os.path.join(WORK, 'overlay')
BUILD = os.path.join(WORK, 'build')

# name -> (watchfaceId, description)
TARGETS = {'S5Icons': ('362150101', 'S5 41mm OS4 icons -> S4 eSIM')}


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

    shutil.copyfile(os.path.join(ov, 'watchface', 'fprj', f'{name}.fprj'),
                    os.path.join(dst, 'watchface', 'fprj', f'{name}.fprj'))
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
        print(f'   {name}: app/images/{d}/ -> {len(os.listdir(tgt))} files')
    return dst, cfg['projectName']


def build(dst, name, disp):
    ps = os.path.join(dst, 'scripts', 'build_face.ps1')
    # 显式指定产物名：build_face.ps1 默认按 projectName（现在 = 显示名，可能带空格/点）命名产物，
    # 这里仍然用 NAME，保证 bin/<NAME>.face、dist/<NAME>.face 这些标识路径不变。
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps,
                        '-FaceName', f'{name}.face'],
                       capture_output=True, text=True, errors='replace')
    for l in [x for x in (r.stdout or '').splitlines() if x.strip()][-6:]:
        print('   |', l)
    if r.returncode != 0:
        print('   !! build failed, rc=', r.returncode)
        return False
    # sync 已经把 .fprj 改名成 <显示名>.fprj（里面的 <Screen Title> 也写成了显示名）；
    # 这里改回 NAME，好让下游 finalize_faces.compile_raw 仍按 fprj/<NAME>.fprj 找它。
    fprj_ident = os.path.join(dst, 'watchface', 'fprj', f'{name}.fprj')
    fprj_disp = os.path.join(dst, 'watchface', 'fprj', f'{disp}.fprj')
    if disp != name and os.path.exists(fprj_disp) and not os.path.exists(fprj_ident):
        os.replace(fprj_disp, fprj_ident)
    # 官方脚本按 projectName 命名产物（bin/<显示名>.face）；-FaceName 已经把它压成 NAME，
    # 万一没生效，这里再兜一次（内容一样，只差文件名）。
    face = os.path.join(dst, 'bin', f'{name}.face')
    alt = os.path.join(dst, 'bin', f'{disp}.face')
    if disp != name and os.path.exists(alt) and not os.path.exists(face):
        os.replace(alt, face)
    return True


if __name__ == '__main__':
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name in TARGETS:
        if only and name != only:
            continue
        print(f'== {name} (id={TARGETS[name][0]}) ==')
        dst, disp = prepare(name)
        build(dst, name, disp)
        face = os.path.join(dst, 'bin', f'{name}.face')
        if os.path.exists(face):
            print(f'   OK  {face}  {os.path.getsize(face)} bytes')
        else:
            print('   missing output')
