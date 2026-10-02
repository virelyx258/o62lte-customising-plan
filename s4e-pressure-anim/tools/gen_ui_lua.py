"""规范化构建：表盘源码 + 资源 -> .face（两遍，自动回填 resource.bin 内的偏移）

    main.lua                  <- **源码**，含 __UIIMG__ / __PAY__ / __RB__ / __ROLE__ 占位符
    .work/overlay/<NAME>      <- 中间产物（回填后的 Lua 落在这里）
    .work/build/<NAME>        <- 编译工作区
    dist/<NAME>.face          <- 交付物

两份盘（replace / restore）共用同一套流程，只是负载来源不同：
    blob_replace/{payload,fp}.bin  ->  S4PAnim.face
    blob_restore/{payload,fp}.bin  ->  S4PAnimRestore.face
rb 表里放的是**另一侧字节前 64 B 的指纹**（只给版本校验用），所以一个 .face 只装一份负载。
"""
import os, re, sys, json, subprocess
from paths import PROJ, WORK
from build_faces import workspace_fprj      # 工作区 .fprj 归一（vendor 会把它改名成显示名）

ROLE = (sys.argv[1] if len(sys.argv) > 1 else 'replace').lower()
NAME = 'S4PAnim' if ROLE == 'replace' else 'S4PAnimRestore'
RECDIR = 'payload' if ROLE == 'replace' else 'payload_restore'
TOOLS = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(PROJ, 'main.lua')
OVERLAY_APP = os.path.join(WORK, 'overlay', NAME, 'watchface', 'fprj', 'app')
RESOLVED = os.path.join(OVERLAY_APP, 'lua', 'main.lua')
FACE = os.path.join(WORK, 'build', NAME, 'bin', NAME + '.face')
PY = sys.executable

UINAMES = ['back', 'ic_help', 'ic_replace', 'ic_about', 'ic_check', 'ic_rollback',
           'ic_qq', 'logo']


def run(script, *args):
    r = subprocess.run([PY, os.path.join(TOOLS, script)] + list(args),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        print(r.stdout[-2000:]); print(r.stderr[-2000:])
        raise SystemExit(f'{script} 执行失败')
    return r.stdout


def find_blob(face, blob):
    hits, start = [], 0
    while True:
        i = face.find(blob, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
        if len(hits) > 4:
            break
    return hits


def main():
    tpl = open(SRC, encoding='utf-8').read()
    if '__UIIMG__' not in tpl:
        raise SystemExit('main.lua 里没有占位符 —— 它应该是源码模板，不要把回填后的版本存回去')
    print('=== %s（role=%s）===' % (NAME, ROLE))
    blobs = json.load(open(os.path.join(PROJ, 'blob_' + ROLE, 'offsets.json'), encoding='utf-8'))
    pay_blob = open(os.path.join(PROJ, 'blob_' + ROLE, 'payload.bin'), 'rb').read()
    fp_blob = open(os.path.join(PROJ, 'blob_' + ROLE, 'fp.bin'), 'rb').read()
    ml, mlf = blobs['magic_len'], blobs['magic_fp_len']

    print('第 1 遍：用占位符编一次，量出资源在 resource.bin 里的位置')
    run('make_overlays.py', ROLE)
    run('build_faces.py', NAME)
    # vendor 的 build_face.ps1 会把工作区 .fprj 改名成 projectName（= 显示名）；
    # 编完立刻取**唯一**那份并归一回 <NAME>.fprj，后面的 finalize_faces 才有得可读。
    print('  fprj 归一：%s' % os.path.relpath(
        workspace_fprj(os.path.join(WORK, 'build', NAME)), WORK))
    face = open(FACE, 'rb').read()
    print('  face %d bytes' % len(face))

    ui_rows, bad = [], 0
    for name in UINAMES:
        blob = open(os.path.join(PROJ, 'ui_images', name + '.bin'), 'rb').read()
        hits = find_blob(face, blob)
        if len(hits) != 1:
            print('  !! %s 命中 %d 次（应为 1）' % (name, len(hits))); bad += 1
        if hits:
            ui_rows.append((hits[0], len(blob), name))
    if bad:
        raise SystemExit('有资源无法唯一定位')
    pay_base = face.find(pay_blob[:15])
    fp_base = face.find(fp_blob[:15])
    for tag, blob, base in (('payload', pay_blob, pay_base), ('fp', fp_blob, fp_base)):
        if face.count(blob[:15]) != 1:
            raise SystemExit('%s 魔数命中 %d 次（应为 1）' % (tag, face.count(blob[:15])))
        if face.find(blob) != base:
            raise SystemExit('%s 不是原样连续存放' % tag)
    pay = [(pay_base + ml + r['rel'], r['target'], r['length']) for r in blobs['records']]
    rb = [(fp_base + mlf + r['fprel'], r['target'], r['fplen']) for r in blobs['records']]
    print('  单条目：payload @0x%x（%d B）/ fp @0x%x（%d B），共 %d 条记录'
          % (pay_base, len(pay_blob), fp_base, len(fp_blob), len(pay)))

    ui_txt = '\n'.join('  {%d,%d,"%s"},' % (o, l, n) for o, l, n in ui_rows)
    pay_txt = '  pay = {\n' + '\n'.join('    {%d,%d,%d},' % t for t in pay) + '\n  },'
    rb_txt = '  rb = {\n' + '\n'.join('    {%d,%d,%d},' % t for t in rb) + '\n  },'
    resolved = (tpl.replace('__UIIMG__', ui_txt).replace('__PAY__', pay_txt)
                   .replace('__RB__', rb_txt).replace('__ROLE__', ROLE))
    assert '__UIIMG__' not in resolved and '__ROLE__' not in resolved
    os.makedirs(os.path.dirname(RESOLVED), exist_ok=True)
    open(RESOLVED, 'w', encoding='utf-8', newline='\n').write(resolved)
    print('第 2 遍：回填后的 Lua（%d bytes），重新编译' % len(resolved))
    run('build_faces.py', NAME)
    # 同上：finalize_faces.compile_raw 是按 fprj/<NAME>.fprj 路径找工作区 fprj 的，
    # vendor 刚把它改名成显示名，这里必须归一（并断言只有一份）后再往下走。
    print('  fprj 归一：%s' % os.path.relpath(
        workspace_fprj(os.path.join(WORK, 'build', NAME)), WORK))
    print(run('finalize_faces.py', NAME).strip())

    face2 = open(FACE, 'rb').read()
    drift = 0
    for name in UINAMES:
        blob = open(os.path.join(PROJ, 'ui_images', name + '.bin'), 'rb').read()
        hits = find_blob(face2, blob)
        row = [r for r in ui_rows if r[2] == name]
        if not row or not hits or hits[0] != row[0][0]:
            print('  !! 偏移漂移 %s' % name); drift += 1
    if face2.find(pay_blob) != pay_base or face2.find(fp_blob) != fp_base:
        print('  !! 负载偏移漂移'); drift += 1
    files = [(f, open(os.path.join(PROJ, RECDIR, f), 'rb').read())
             for f in sorted(os.listdir(os.path.join(PROJ, RECDIR))) if f.endswith('.bin')]
    ok = sum(1 for off, tgt, ln in pay
             if any(len(x) == ln and face2[off:off + ln] == x for _, x in files))
    if ok != len(pay):
        print('  !! pay 只有 %d/%d 条吻合' % (ok, len(pay))); drift += 1
    okf = sum(1 for (off, tgt, ln), r in zip(rb, blobs['records'])
              if face2[off:off + ln] == fp_blob[mlf + r['fprel']:mlf + r['fprel'] + ln])
    if okf != len(rb):
        print('  !! fp 只有 %d/%d 条吻合' % (okf, len(rb))); drift += 1
    print('偏移校验：%s' % ('全部吻合，0 漂移' if drift == 0 else '%d 处异常' % drift))
    print('交付物：', os.path.join(PROJ, 'dist', NAME + '.face'))


if __name__ == '__main__':
    main()
