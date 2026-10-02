"""规范化构建：表盘源码 + 资源 -> .face（两遍，自动回填 resource.bin 内的偏移）

    main.lua               <- **源码**，含 __UIIMG__ / __PAY__ / __RB__ 占位符
    .work/overlay/S5Icons  <- 中间产物（回填后的 Lua 落在这里）
    .work/build/S5Icons    <- 编译工作区（Compiler.exe 的实际输入）
    dist/S5Icons.face      <- 交付物

为什么要两遍：.face 里各资源的偏移取决于打包顺序，我们靠在 .face 里搜文件字节来定位。
Lua 源码排在所有资源**之后**，所以回填（让 Lua 变长）不会移动前面资源的位置 —— 第一遍量出来的
偏移在第二遍依然成立，脚本最后会逐条校验。
"""
import os, re, sys, json, subprocess
from paths import PROJ, WORK

TOOLS = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(PROJ, 'main.lua')
OVERLAY_APP = os.path.join(WORK, 'overlay', 'S5Icons', 'watchface', 'fprj', 'app')
RESOLVED = os.path.join(OVERLAY_APP, 'lua', 'main.lua')
FACE = os.path.join(WORK, 'build', 'S5Icons', 'bin', 'S5Icons.face')
OFFS = os.path.join(WORK, 'face_payload_offsets.json')
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


def payload_rows(tag, lua_payload, offs):
    src = open(lua_payload, encoding='utf-8').read()
    tgt = {}
    for m in re.finditer(r'file = "([^"]+)", offset = (\d+), length = (\d+)', src):
        tgt[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    rows = []
    for name, ln, hits, sig in offs[tag]:
        if name not in tgt:
            continue
        blob = min(hits) if tag == 'payload' else max(hits)
        to, tl = tgt[name]
        rows.append((blob, to, tl))
    rows.sort(key=lambda r: r[1])
    return rows


def main():
    tpl = open(SRC, encoding='utf-8').read()
    if '__UIIMG__' not in tpl:
        raise SystemExit('main.lua 里没有占位符 —— 它应该是源码模板，不要把回填后的版本存回去')
    print('第 1 遍：用占位符编一次，量出资源在 resource.bin 里的位置')
    run('make_overlays.py')
    run('build_faces.py', 'S5Icons')
    face = open(FACE, 'rb').read()
    print(f'  face {len(face)} bytes')

    ui_rows, bad = [], 0
    for name in UINAMES:
        blob = open(os.path.join(PROJ, 'ui_images', name + '.bin'), 'rb').read()
        hits = find_blob(face, blob)
        if len(hits) != 1:
            print(f'  !! {name} 命中 {len(hits)} 次（应为 1）')
            bad += 1
        if hits:
            ui_rows.append((hits[0], len(blob), name))
            print(f'  {name:<12} off=0x{hits[0]:x} len={len(blob)}')
    if bad:
        raise SystemExit('有资源无法唯一定位，检查是否有重复内容')

    # 负载是「魔数 + 顺序拼接」的**单个条目**（blob/），偏移 = 魔数位置 + 魔数长度 + 相对偏移
    blobs = json.load(open(os.path.join(PROJ, 'blob', 'offsets.json'), encoding='utf-8'))
    pay_blob = open(os.path.join(PROJ, 'blob', 'payload.bin'), 'rb').read()
    rb_blob = open(os.path.join(PROJ, 'blob', 'rollback.bin'), 'rb').read()
    ml = blobs['magic_len']
    pay_base = face.find(pay_blob[:15])
    rb_base = face.find(rb_blob[:15])
    if face.count(pay_blob[:15]) != 1 or face.count(rb_blob[:15]) != 1:
        raise SystemExit('魔数命中次数 != 1（payload %d / rollback %d）'
                         % (face.count(pay_blob[:15]), face.count(rb_blob[:15])))
    # 单条目必须**原样连续**存放，否则「base + 魔数长度 + 相对偏移」不成立
    if face.find(pay_blob) != pay_base or face.find(rb_blob) != rb_base:
        raise SystemExit('负载不是原样连续存放')
    pay = [(pay_base + ml + r['rel'], r['target'], r['length']) for r in blobs['records']]
    rb = [(rb_base + ml + r['rel'], r['target'], r['length']) for r in blobs['records']]
    print(f'  单条目：payload @0x{pay_base:x}（{len(pay_blob)} B）/ rollback @0x{rb_base:x}'
          f'（{len(rb_blob)} B），共 {len(pay)} 条记录')

    ui_txt = '\n'.join(f'  {{{o},{l},"{n}"}},' for o, l, n in ui_rows)
    pay_txt = '  pay = {\n' + '\n'.join(f'    {{{o},{t},{l}}},' for o, t, l in pay) + '\n  },'
    rb_txt = '  rb = {\n' + '\n'.join(f'    {{{o},{t},{l}}},' for o, t, l in rb) + '\n  },'
    resolved = (tpl.replace('__UIIMG__', ui_txt)
                   .replace('__PAY__', pay_txt)
                   .replace('__RB__', rb_txt))
    assert '__UIIMG__' not in resolved and 'pay = {}' not in resolved
    os.makedirs(os.path.dirname(RESOLVED), exist_ok=True)
    open(RESOLVED, 'w', encoding='utf-8', newline='\n').write(resolved)
    print(f'第 2 遍：回填后的 Lua 写入 overlay（{len(resolved)} bytes），重新编译')

    run('build_faces.py', 'S5Icons')
    print(run('finalize_faces.py').strip())

    face2 = open(FACE, 'rb').read()
    drift = 0
    for name in UINAMES:
        blob = open(os.path.join(PROJ, 'ui_images', name + '.bin'), 'rb').read()
        hits = find_blob(face2, blob)
        row = [r for r in ui_rows if r[2] == name]
        if not row or not hits or hits[0] != row[0][0]:
            print(f'  !! 偏移漂移 {name}')
            drift += 1
    for tag, rows, d in (('pay', pay, os.path.join(PROJ, 'payload')),
                         ('rb', rb, os.path.join(PROJ, 'payload_rollback'))):
        files = [(f, open(os.path.join(d, f), 'rb').read())
                 for f in sorted(os.listdir(d)) if f.endswith('.bin')]
        ok = sum(1 for off, tgt, ln in rows
                 if any(len(x) == ln and face2[off:off + ln] == x for _, x in files))
        if ok != len(rows):
            print(f'  !! {tag} 只有 {ok}/{len(rows)} 条吻合'); drift += 1
    print(f'偏移校验：{"全部吻合，0 漂移" if drift == 0 else str(drift) + " 处异常"}')
    print('交付物：', os.path.join(PROJ, 'dist', 'S5Icons.face'))


if __name__ == '__main__':
    main()
