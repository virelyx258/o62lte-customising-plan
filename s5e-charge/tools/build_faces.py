"""overlay + 官方模板 -> Compiler.exe -> .face（两份盘共用同一个 watchface id）

要点（都是踩过的坑）：
  * preview.png 必须是 326x326，Compiler.exe 会直接拒绝别的尺寸
  * watchfaceId 要带机型家族前缀：S5 家族 = 462150xxx
  * 用 Python 的 copytree 拷目录，别用 PowerShell 的 Copy-Item -Recurse（会拍平）
  * replace 盘与 restore 盘用**同一个 id**：装一份就顶掉另一份，设备上只占一份空间
"""
import os, json, shutil, subprocess, sys
from paths import WORK, TEMPLATE

TPL = TEMPLATE
OVER = os.path.join(WORK, 'overlay')
BUILD = os.path.join(WORK, 'build')

TARGETS = {'S5Chg': ('462150103', 'S5 41mm 充电动画 -> S5 eSIM 46mm（只写负载）'),
           'S5ChgRestore': ('462150103', 'S5 eSIM 46mm 充电动画还原盘（只写原厂字节）')}


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
    return dst


def normalize_fprj(dst):
    """把工作区里的 .fprj 归一成 <name>.fprj，并返回它的路径。

    我们拷进去时就是 <name>.fprj，但 vendor 的 build_face.ps1 会先跑
    sync_watchface_config.ps1：它按 config 的 projectName（现在是**显示名** S5e Pt.3）找
    <projectName>.fprj，找不到就把唯一那份改名过去（Title 也被改写成 projectName）。
    编完这里再改回 <name>.fprj —— 工作区里始终只有一份 .fprj（放两份会被 Compiler.exe
    并成双倍资源，实测资源整体翻倍），文件名也保持项目标识不变。
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


def build(dst):
    ps = os.path.join(dst, 'scripts', 'build_face.ps1')
    # 显式给 -FaceName：vendor 脚本默认用 config 的 projectName 当输出名，而 projectName 现在
    # 是**显示名**（S5e Pt.3），交付/中间文件名必须还是 NAME.face。
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps,
                        '-FaceName', os.path.basename(dst) + '.face'],
                       capture_output=True, text=True, errors='replace')
    normalize_fprj(dst)   # vendor 可能把 .fprj 改名成显示名，编完改回 <name>.fprj
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
        print('== %s (id=%s) ==' % (name, TARGETS[name][0]))
        dst = prepare(name)
        build(dst)
        face = os.path.join(dst, 'bin', name + '.face')
        if os.path.exists(face):
            print('   OK  %s  %d bytes' % (face, os.path.getsize(face)))
        else:
            print('   missing output')
