"""产出最终 .face（两份盘各一份，都不带工具链变体）。

  * Compiler.exe 写 byte5 = 0x00 + 自己的随机 id 到 40..49
  * 官方 set_face_id.ps1 会把 byte5 改成 10 并写 id；固件里 25 个真表盘 byte5 ∈ {0,1}
  => 忠实产物 = Compiler.exe 原始输出，只替换 40..49（b5=0 那份）
  体积原因：本盘各 ~12 MB，不再额外复制工具链变体（要的话去掉下面的 SKIP_TOOLCHAIN 即可）
"""
import os, sys, shutil, subprocess, hashlib
from paths import WORK, DIST

BUILD = os.path.join(WORK, 'build')
TARGETS = {'S5Chg': '462150103', 'S5ChgRestore': '462150103'}
SKIP_TOOLCHAIN = True


def compile_raw(name):
    w = os.path.join(BUILD, name)
    exe = os.path.join(w, 'watchface', 'tools', 'Compiler.exe')
    if not os.path.exists(exe):
        print('  %s: 跳过（没有构建树，先跑 build_faces.py %s）' % (name, name))
        return None
    # vendor 的 build_face.ps1 会先跑 sync_watchface_config.ps1，它按 config 的 projectName
    # （现在是**显示名** S5e Pt.3）把 <name>.fprj 改名成 <显示名>.fprj。build_faces.py 编完
    # 会改回来；这里再兜一次，保证只取工作区里唯一那份 .fprj（放两份会让资源翻倍）。
    fdir = os.path.join(w, 'watchface', 'fprj')
    fs = sorted(f for f in os.listdir(fdir) if f.endswith('.fprj'))
    if len(fs) != 1:
        raise SystemExit('%s: watchface/fprj 下的 .fprj 应恰好 1 份，实际：%s' % (name, fs))
    fprj = os.path.join(fdir, fs[0])
    if fs[0] != name + '.fprj':
        os.replace(fprj, os.path.join(fdir, name + '.fprj'))
        fprj = os.path.join(fdir, name + '.fprj')
    out = os.path.join(WORK, 'raw_' + name)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    subprocess.run([exe, '-b', fprj, out, name + '.face', TARGETS[name]],
                   capture_output=True, text=True, errors='replace')
    p = os.path.join(out, name + '.face')
    return p if os.path.exists(p) else None


def patch_id(src, dst, wid):
    d = bytearray(open(src, 'rb').read())
    if d[0:4] != b'\x5a\xa5\x34\x12':
        raise SystemExit('bad magic')
    if len(wid) > 10:
        raise SystemExit('id too long')
    d[40:50] = wid.encode() + b'\x00' * (10 - len(wid))
    open(dst, 'wb').write(bytes(d))
    return dst


def main():
    os.makedirs(DIST, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    report = []
    for name, wid in TARGETS.items():
        if only and only != name:
            continue
        raw = compile_raw(name)
        if not raw:
            continue
        faithful = patch_id(raw, os.path.join(DIST, name + '.face'), wid)
        if not SKIP_TOOLCHAIN:
            tc_src = os.path.join(BUILD, name, 'bin', name + '.face')
            tc = os.path.join(DIST, name + '_toolchain.face')
            if os.path.exists(tc_src):
                shutil.copyfile(tc_src, tc)
        for p in (faithful,):
            if os.path.exists(p):
                d = open(p, 'rb').read()
                report.append((os.path.basename(p), len(d), d[4], d[5], d[40:50],
                               hashlib.sha256(d).hexdigest()[:16]))
    print('%-28s%11s b4  b5  id                 sha256[:16]' % ('file', 'bytes'))
    for f, n, b4, b5, sid, h in report:
        print('%-28s%11d %-3d %-3d %-18r %s' % (f, n, b4, b5, sid, h))
    print('->', DIST)


if __name__ == '__main__':
    main()
