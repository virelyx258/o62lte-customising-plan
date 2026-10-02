"""产出最终 .face。

  * Compiler.exe 写 byte5 = 0x00 + 自己的随机 id 到 40..49
  * 官方 set_face_id.ps1 会把 byte5 改成 10 并写 id
  * 固件里 25 个真表盘 byte5 ∈ {0,1}，从不为 10
  => 忠实产物 = Compiler.exe 原始输出，只替换 40..49（我们称 b5=0 那份）
     同时保留官方工具链那份（b5=10），装不上时可以换。
"""
import os, shutil, subprocess, hashlib
from paths import WORK, DIST

BUILD = os.path.join(WORK, 'build')
TARGETS = {'S5Icons': '362150101'}


def compile_raw(name):
    w = os.path.join(BUILD, name)
    exe = os.path.join(w, 'watchface', 'tools', 'Compiler.exe')
    if not os.path.exists(exe):
        print(f'  {name}: 跳过（没有构建树，先跑 build_faces.py {name}）')
        return None
    fprj = os.path.join(w, 'watchface', 'fprj', f'{name}.fprj')
    out = os.path.join(WORK, 'raw_' + name)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    subprocess.run([exe, '-b', fprj, out, f'{name}.face', TARGETS[name]],
                   capture_output=True, text=True, errors='replace')
    p = os.path.join(out, f'{name}.face')
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
    report = []
    for name, wid in TARGETS.items():
        raw = compile_raw(name)
        if not raw:
            continue
        faithful = patch_id(raw, os.path.join(DIST, f'{name}.face'), wid)
        tc_src = os.path.join(BUILD, name, 'bin', f'{name}.face')
        tc = os.path.join(DIST, f'{name}_toolchain.face')
        if os.path.exists(tc_src):
            shutil.copyfile(tc_src, tc)
        for p in (faithful, tc):
            if os.path.exists(p):
                d = open(p, 'rb').read()
                report.append((os.path.basename(p), len(d), d[4], d[5], d[40:50],
                               hashlib.sha256(d).hexdigest()[:16]))
    print(f'{"file":<32}{"bytes":>10} b4  b5  id                 sha256[:16]')
    for f, n, b4, b5, sid, h in report:
        print(f'{f:<32}{n:>10} {b4:<3} {b5:<3} {sid!r:<20} {h}')
    print('->', DIST)


if __name__ == '__main__':
    main()
