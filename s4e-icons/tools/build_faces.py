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
    return dst


def build(dst):
    ps = os.path.join(dst, 'scripts', 'build_face.ps1')
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps],
                       capture_output=True, text=True, errors='replace')
    for l in [x for x in (r.stdout or '').splitlines() if x.strip()][-6:]:
        print('   |', l)
    if r.returncode != 0:
        print('   !! build failed, rc=', r.returncode)
    return r.returncode == 0


if __name__ == '__main__':
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name in TARGETS:
        if only and name != only:
            continue
        print(f'== {name} (id={TARGETS[name][0]}) ==')
        dst = prepare(name)
        ok = build(dst)
        face = os.path.join(dst, 'bin', f'{name}.face')
        if os.path.exists(face):
            print(f'   OK  {face}  {os.path.getsize(face)} bytes')
        else:
            print('   missing output')
