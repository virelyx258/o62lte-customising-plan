# -*- coding: utf-8 -*-
"""两遍构建：表盘源码 + 资源 -> dist/S5ePAnim.face / dist/S5ePAnimRestore.face

    main.lua                 <- **源码**，含 __UIIMG__ / __PAY__ / __RB__ / __ROLE__ 占位符
    .work/overlay/<NAME>     <- 中间产物（回填后的 Lua 落在这里）
    .work/build/<NAME>       <- 编译工作区（Compiler.exe 的输入）
    dist/<NAME>.face         <- 交付物

为什么两遍
----------
.face 里各资源的偏移取决于打包顺序；我们靠在 .face 里**搜字节**来定位它们。
Lua 源码排在所有资源之后，所以回填（Lua 变长）不会移动前面的资源 —— 脚本最后逐条校验 0 漂移。

为什么最终产物要"再裸编一次"
----------------------------
两遍构建走的是 vendor 的 scripts/build_face.ps1，它在编译后调 set_face_id.ps1，
把**头里第 5 字节写成 id 长度 10**，而固件自带表盘的 b5 是 0。
所以交付物改从裸 `Compiler.exe -b` 的输出取（b5=0），只覆盖 40..49 = id。
断言：裸产物与 toolchain 产物必须"只差 b5 + id 这 8 个字节"，否则直接拒绝交付。

两份盘共用同一个 watchface id（462150102）：装一份就顶掉另一份，设备上只占一份空间。
"""
import os, re, sys, json, shutil, hashlib, struct, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import PROJ, WORK, DIST, TEMPLATE, WF_ID, SCREEN, DEVICE_TYPE, PREVIEW
import s5e_overlay as OV

ROLE = (sys.argv[1] if len(sys.argv) > 1 else 'replace').lower()
assert ROLE in ('replace', 'restore'), ROLE
NAME = 'S5ePAnim' if ROLE == 'replace' else 'S5ePAnimRestore'   # 路径/标识（不要改）
TITLE = 'S5e Pt.2'    # 手表上显示的表盘名（replace / restore 两张盘同名，须与 s5e_overlay.TITLE 一致）
RECDIR = 'payload' if ROLE == 'replace' else 'payload_restore'
TOOLS = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(PROJ, 'main.lua')
OVER = os.path.join(WORK, 'overlay', NAME)
BUILD = os.path.join(WORK, 'build', NAME)
RESOLVED = os.path.join(OVER, 'watchface', 'fprj', 'app', 'lua', 'main.lua')
LOGLINES = []


def log(s):
    print(s)
    LOGLINES.append(s)


def write_lua(lua_text):
    """把 Lua 写进编译工作区（两遍构建的唯一区别就在这里）。"""
    p = os.path.join(BUILD, 'watchface', 'fprj', 'app', 'lua', 'main.lua')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8', newline='\n').write(lua_text)


def prepare(lua_text, role):
    """把官方模板拷成编译工作区，写 config / fprj / preview / lua / 资源。"""
    if not os.path.exists(TEMPLATE):
        raise SystemExit('找不到官方模板：%s\n请把 LuaDevTemplate-main 放到 vendor/ 下' % TEMPLATE)
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    shutil.copytree(TEMPLATE, BUILD)
    old = os.path.join(BUILD, 'watchface', 'fprj', 'LuaDevTemplate.fprj')
    if os.path.exists(old):
        os.remove(old)

    cfg = {"projectName": TITLE, "watchfaceId": WF_ID, "power_consumption": "3",
           "resourceBin": {"lvglVersion": 9, "colorFormat": "I8", "compress": "NONE",
                           "input": "watchface/fprj/images/preview.png", "name": "preview"}}
    json.dump(cfg, open(os.path.join(BUILD, 'watchface.config.json'), 'w', encoding='utf-8'),
              indent=4, ensure_ascii=False)

    fprj = ('<?xml version="1.0" encoding="utf-16" ?>\r\n'
            '<FaceProject DeviceType="%s">\r\n'
            '    <Screen Title="%s" Bitmap="preview.png">\r\n'
            '        <Widget Shape="34" Name="app_lua%%2Fmain.lua" X="0" Y="0" '
            'Width="%d" Height="%d" Alpha="0" />\r\n'
            '    </Screen>\r\n</FaceProject>\r\n') % (DEVICE_TYPE, TITLE, SCREEN, SCREEN)
    open(os.path.join(BUILD, 'watchface', 'fprj', NAME + '.fprj'), 'w',
         encoding='utf-16', newline='').write(fprj)

    # 预览图 = 真实首页渲染 -> 圆形 -> 326x326（Compiler.exe 对 462 只收这个尺寸）
    prev = os.path.join(OVER, 'watchface', 'fprj', 'images', 'preview.png')
    OV.make_preview(prev)
    shutil.copyfile(prev, os.path.join(BUILD, 'watchface', 'fprj', 'images', 'preview.png'))

    write_lua(lua_text)

    imgdir = os.path.join(BUILD, 'watchface', 'fprj', 'app', 'images')
    for sub, src in (('pay', os.path.join(PROJ, 'blob_' + role)),
                     ('ui', os.path.join(PROJ, 'ui_images'))):
        if not os.path.isdir(src):
            raise SystemExit('缺少 %s/ —— 先跑 tools/s5e_payload.py %s' % (src, role))
        dst = os.path.join(imgdir, sub)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        os.makedirs(dst)
        for fn in sorted(os.listdir(src)):
            shutil.copyfile(os.path.join(src, fn), os.path.join(dst, fn))


def run_build():
    ps = os.path.join(BUILD, 'scripts', 'build_face.ps1')
    # 显式给 -FaceName：vendor 脚本默认用 config 的 projectName 当输出名，而 projectName 现在
    # 是**显示名**（S5e Pt.2），交付文件名必须还是 NAME.face。
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps,
                        '-FaceName', NAME + '.face'],
                       capture_output=True, text=True, errors='replace')
    workspace_fprj()      # vendor 可能把 .fprj 改名成显示名，编完改回 NAME.fprj
    out = ((r.stdout or '') + (r.stderr or '')).splitlines()
    for l in [x for x in out if x.strip()][-4:]:
        log('   | ' + l)
    face = os.path.join(BUILD, 'bin', NAME + '.face')
    if not os.path.exists(face):
        raise SystemExit('编译失败：没有产出 %s' % face)
    return open(face, 'rb').read()


def workspace_fprj():
    """把工作区里的 .fprj 归一成 NAME.fprj，并返回它的路径。

    我们写下去时就是 NAME.fprj，但 vendor 的 build_face.ps1 会先跑
    sync_watchface_config.ps1：它按 config 的 projectName（现在是**显示名** S5e Pt.2）找
    <projectName>.fprj，找不到就把唯一那份改名过去（Title 也被改写成 projectName）。
    编完这里再改回 NAME.fprj —— 工作区里始终只有一份 .fprj（放两份会被 Compiler.exe 并成
    双倍资源，实测资源整体翻倍），文件名也保持项目标识不变。
    """
    d = os.path.join(BUILD, 'watchface', 'fprj')
    fs = sorted(f for f in os.listdir(d) if f.endswith('.fprj'))
    if len(fs) != 1:
        raise SystemExit('watchface/fprj 下的 .fprj 应恰好 1 份，实际：%s' % fs)
    want = os.path.join(d, NAME + '.fprj')
    if fs[0] != NAME + '.fprj':
        os.replace(os.path.join(d, fs[0]), want)
    return want


def compile_raw():
    """裸 Compiler.exe —— 拿**忠实产物**（不经 vendor 的 set_face_id.ps1 改头）。

    ★ 为什么必须多这一步（b5=10 的根因）
    run_build() 走的是 vendor 的 build_face.ps1，它编完之后会调
    scripts/internal/set_face_id.ps1，那个脚本里有一句
        $bytes[5] = [byte]$faceIdSize      # = 10
    也就是把「id 字符串长度」写进了头里第 5 字节。固件自带表盘的 b5 是 0，
    交付物照着 0 走；所以最终产物必须取自**裸编译输出**（b5 由编译器给，实测 0），
    然后只把 40..49 覆盖成我们的 id，b5 一个字节都不碰。
    （s5e-icons 的 s5e_build.py 就是 compile_raw() + 补 id 这一套，真机验证过。）
    """
    exe = os.path.join(BUILD, 'watchface', 'tools', 'Compiler.exe')
    fprj = workspace_fprj()
    out = os.path.join(BUILD, 'raw')
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    r = subprocess.run([exe, '-b', fprj, out, NAME + '.face', WF_ID],
                       capture_output=True, text=True, errors='replace')
    p = os.path.join(out, NAME + '.face')
    if not os.path.exists(p):
        raise SystemExit('裸编译失败：%s' % ((r.stdout or '') + (r.stderr or ''))[-400:])
    return open(p, 'rb').read()


def hits(face, blob):
    out, s = [], 0
    while True:
        i = face.find(blob, s)
        if i < 0:
            return out
        out.append(i)
        s = i + 1


UI_NAMES = ['back', 'ic_help', 'ic_replace', 'ic_about', 'ic_check', 'ic_rollback',
            'ic_qq', 'logo']


def locate(face, blobs, pay_blob, fp_blob):
    """量出 UI 图片 / 负载 / 指纹在 .face 里的偏移，并逐条字节校验。"""
    ui, bad = [], 0
    for name in UI_NAMES:
        blob = open(os.path.join(PROJ, 'ui_images', name + '.bin'), 'rb').read()
        h = hits(face, blob)
        if len(h) != 1:
            log('  !! UI %s 命中 %d 次（应为 1）' % (name, len(h)))
            bad += 1
        if h:
            ui.append((h[0], len(blob), name))
    if bad:
        raise SystemExit('有 UI 资源无法唯一定位')
    ml, mlf = blobs['magic_len'], blobs['magic_fp_len']
    if face.count(pay_blob[:ml]) != 1:
        raise SystemExit('payload 魔数命中 %d 次（应为 1）' % face.count(pay_blob[:ml]))
    if face.count(fp_blob[:mlf]) != 1:
        raise SystemExit('fp 魔数命中 %d 次（应为 1）' % face.count(fp_blob[:mlf]))
    pay_base = face.find(pay_blob)
    fp_base = face.find(fp_blob)
    if pay_base < 0:
        raise SystemExit('payload 不是原样连续存放')
    if fp_base < 0:
        raise SystemExit('fp 不是原样连续存放')
    # 用生成负载时的 sha256 逐条独立校验（避免"自己比自己"这种恒真检查）
    for tag, base, path, key, mag in (
            ('pay', pay_base, os.path.join(PROJ, 'blob_' + ROLE, 'payload.bin'),
             'pay_sha', ml),
            ('fp', fp_base, os.path.join(PROJ, 'blob_' + ROLE, 'fp.bin'), 'fp_sha', mlf)):
        data = open(path, 'rb').read()
        if face.find(data) != base:
            raise SystemExit('%s 文件不是原样连续存放' % tag)
        for i, r in enumerate(blobs['records']):
            res = base + mag + (r['rel'] if tag == 'pay' else r['fprel'])
            ln = r['length'] if tag == 'pay' else r['fplen']
            seg = face[res:res + ln]
            if len(seg) != ln or hashlib.sha256(seg).hexdigest() != r[key]:
                raise SystemExit('%s[%d] 在 0x%x 处字节不吻合' % (tag, i, res))
    pay = [(pay_base + ml + r['rel'], r['target'], r['length']) for r in blobs['records']]
    rb = [(fp_base + mlf + r['fprel'], r['target'], r['fplen']) for r in blobs['records']]
    return ui, pay, rb, pay_base, fp_base


def main():
    tpl = open(SRC, encoding='utf-8').read()
    for ph in ('__UIIMG__', '__PAY__', '__RB__', '__ROLE__'):
        if ph not in tpl:
            raise SystemExit('main.lua 里没有占位符 %s —— 它应该是源码模板' % ph)
    log('=== %s（role=%s，id=%s）===' % (NAME, ROLE, WF_ID))
    blobs = json.load(open(os.path.join(PROJ, 'blob_' + ROLE, 'offsets.json'),
                           encoding='utf-8'))
    for r in blobs['records']:
        if 'pay_sha' not in r or 'fp_sha' not in r:
            raise SystemExit('offsets.json 里没有 sha256 —— 请重跑 tools/s5e_payload.py %s' % ROLE)
    pay_blob = open(os.path.join(PROJ, 'blob_' + ROLE, 'payload.bin'), 'rb').read()
    fp_blob = open(os.path.join(PROJ, 'blob_' + ROLE, 'fp.bin'), 'rb').read()
    ml, mlf = blobs['magic_len'], blobs['magic_fp_len']

    log('第 1 遍：用占位符编一次，量出资源在 .face 里的位置')
    prepare(tpl, ROLE)
    face1 = run_build()
    log('  face %d bytes' % len(face1))
    ui, pay, rb, pay_base, fp_base = locate(face1, blobs, pay_blob, fp_blob)
    for o, l, n in ui:
        log('  %-12s off=0x%06x len=%d' % (n, o, l))
    log('  payload base=0x%06x（%d B） / fp base=0x%06x（%d B），共 %d 条记录'
        % (pay_base, len(pay_blob), fp_base, len(fp_blob), len(pay)))

    ui_txt = '\n'.join('  {%d,%d,"%s"},' % (o, l, n) for o, l, n in ui)
    pay_txt = '  pay = {\n' + '\n'.join('    {%d,%d,%d},' % t for t in pay) + '\n  },'
    rb_txt = '  rb = {\n' + '\n'.join('    {%d,%d,%d},' % t for t in rb) + '\n  },'
    resolved = (tpl.replace('__UIIMG__', ui_txt).replace('__PAY__', pay_txt)
                   .replace('__RB__', rb_txt).replace('__ROLE__', ROLE))
    assert '__UIIMG__' not in resolved and '__ROLE__' not in resolved
    assert '__PAY__' not in resolved and '__RB__' not in resolved
    os.makedirs(os.path.dirname(RESOLVED), exist_ok=True)
    open(RESOLVED, 'w', encoding='utf-8', newline='\n').write(resolved)
    log('第 2 遍：回填后的 Lua（%d bytes）重新编译' % len(resolved))
    # ★ 第 1 遍编的是**占位符版**；第 2 遍必须把回填后的 Lua 写回编译工作区再编，
    #   否则交付物里还是 __PAY__/__RB__/__ROLE__（表盘在设备上直接"负载表为空"）。
    write_lua(resolved)
    face2 = run_build()

    # ---- 0 漂移校验 ----
    drift = 0
    ui2, pay2, rb2, pb2, fb2 = locate(face2, blobs, pay_blob, fp_blob)
    if ui2 != ui:
        log('  !! UI 偏移漂移'); drift += 1
    if (pb2, fb2) != (pay_base, fp_base):
        log('  !! 负载偏移漂移'); drift += 1
    if (pay2, rb2) != (pay, rb):
        log('  !! 负载表内容漂移'); drift += 1
    files = [(f, open(os.path.join(PROJ, RECDIR, f), 'rb').read())
             for f in sorted(os.listdir(os.path.join(PROJ, RECDIR))) if f.endswith('.bin')]
    ok = sum(1 for off, tgt, ln in pay
             if any(len(x) == ln and face2[off:off + ln] == x for _n, x in files))
    if ok != len(pay):
        log('  !! pay 只有 %d/%d 条与 %s/ 吻合' % (ok, len(pay), RECDIR)); drift += 1
    log('偏移校验：%s' % ('全部吻合，0 漂移' if drift == 0 else '!! %d 处异常' % drift))

    # ---- 最终产物：id 必须逐字节正确（b5=0，40..49 = id + NUL）----
    # 交付物取**裸编译**的忠实产物：b5 保持编译器给的值（实测 0），只覆盖 id 那 10 字节。
    # （vendor 的 build_face.ps1 会顺手把 b5 写成 id 长度 10，不能拿它当交付物。）
    raw = compile_raw()
    if raw[0:4] != b'\x5a\xa5\x34\x12':
        raise SystemExit('bad face magic')
    nd = [i for i in range(min(len(raw), len(face2))) if raw[i] != face2[i]]
    stray = [i for i in nd if not (i == 5 or 40 <= i < 50)]
    if len(raw) != len(face2) or stray:
        raise SystemExit('忠实产物与 toolchain 产物不是"只差 b5 + id"：'
                         'len %d vs %d，差异 %d 字节，越界位置 %s'
                         % (len(raw), len(face2), len(nd), stray[:8]))
    if raw[5] != 0:
        raise SystemExit('裸编译产物的 b5 = %d（期望 0）—— 设备表盘的约定变了，得重查' % raw[5])
    d = bytearray(raw)
    d[40:50] = WF_ID.encode() + b'\x00' * (10 - len(WF_ID))
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, NAME + '.face')
    open(out, 'wb').write(bytes(d))
    a32, = struct.unpack('<I', bytes(d[32:36]))
    pal, pw, ph, psz = struct.unpack('<IHHI', bytes(d[a32:a32 + 12]))
    log('忠实产物 vs toolchain：%d 字节差异（只允许 b5 + id 这 8 个位置：%s）'
        % (len(nd), nd))
    log('b4=%d b5=%d id=%r' % (d[4], d[5], bytes(d[40:50])))
    log('preview @0x%x: %dx%d palette=%d data=%d' % (a32, pw, ph, pal, psz))
    if (pw, ph) != (PREVIEW, PREVIEW):
        raise SystemExit('预览块尺寸 %dx%d 不是 %dx%d' % (pw, ph, PREVIEW, PREVIEW))
    if d[5] != 0 or bytes(d[40:50]) != WF_ID.encode() + b'\x00' * (10 - len(WF_ID)):
        raise SystemExit('交付物头不对：b5=%d id=%r' % (d[5], bytes(d[40:50])))
    log('交付物：%s  %d B  sha256 %s' % (out, len(d), hashlib.sha256(bytes(d)).hexdigest()))
    if drift:
        raise SystemExit('有偏移漂移，拒绝交付')
    open(os.path.join(WORK, 'build_log_%s.txt' % ROLE), 'w',
         encoding='utf-8').write('\n'.join(LOGLINES))


if __name__ == '__main__':
    main()
