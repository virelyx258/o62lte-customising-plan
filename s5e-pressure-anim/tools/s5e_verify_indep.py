# -*- coding: utf-8 -*-
"""独立总校验 —— 只读两张交付物 + 固件镜像，**不读任何构建中间产物**。

与 tools/s5e_verify.py 的分工
-----------------------------
s5e_verify.py 会读 `blob_<role>/offsets.json` 来核对 Lua 表里的偏移。本脚本刻意
**不读** offsets.json / .work/overlay / .work/build，改为：

  * 自己从 `.face` 里反解 Lua（占位符、ROLE、pay/rb/UIIMG 三张表）
  * 自己从**固件镜像**里量出 119 个槽位（名字 / 偏移 / 长度）
  * 自己证明两张表「自洽 + 连续」：pay[0] 必须紧跟在魔数之后、pay[i+1] == pay[i]+len
  * 自己证明**第 k 条负载落在 Measuring{k}.bin 上**（名字对得上，不只是偏移对得上）
  * 逐条把负载解成像素：RLE 解出**恰好 usize**，且多出来的那 1 字节正好在像素区之后
    （这是"少 1 像素整帧不画"的那个坑）
  * 两张交付物**互相印证**（replace 的 pay 前 64 B == restore 的 rb，反之亦然）——
    这一条完全不碰 .work，也不碰固件镜像
  * 镜像级：inode 表 / superblock / 卷名 / 长度逐位不变；除 119 个槽位外，
    **其余每一个文件的每一个字节都逐字节不变**（不是只做区间统计）

用法：python tools/s5e_verify_indep.py
"""
import os, re, sys, hashlib, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import PROJ, DIST, TARGET_IMAGE, DIRP, FACE_W, FACE_H, WF_ID, PREVIEW, SCREEN, WORK
from romfs import Romfs
import lvgl_bin as L

MAGIC_PAY = b'\x00S5P-PAYv1\x00\xa5\x5a\xc3\x3c'
MAGIC_FP = b'\x00S5P-FPv1\x00\x5a\xa5\x3c\xc3'
FACES = {'replace': 'S5ePAnim.face', 'restore': 'S5ePAnimRestore.face'}
PATCHED = os.path.join(WORK, 'anim', 'vela_health_anim.bin')
UI_NAMES = ['back', 'ic_help', 'ic_replace', 'ic_about', 'ic_check', 'ic_rollback',
            'ic_qq', 'logo']
ok = fail = 0


def ck(cond, msg):
    global ok, fail
    if cond:
        ok += 1
        print('  OK   ' + msg)
    else:
        fail += 1
        print('  FAIL ' + msg)


def parse_face(path):
    """把一张 .face 反解成：头 + Lua 文本 + 三张表 + 魔数位置。"""
    d = open(path, 'rb').read()
    end = d.find(b'return ui\n')
    start = d.rfind(b'--[[', 0, end)
    lua = d[start:end + len(b'return ui\n')]
    txt = lua.decode('utf-8')
    out = dict(data=d, lua=lua, txt=txt, lua_off=start)
    m = re.search(r"local ROLE = '(\w+)'", txt)
    out['role'] = m.group(1) if m else None
    for key, pat in (('pay', r'pay = \{(.*?)\n  \},'), ('rb', r'rb = \{(.*?)\n  \},')):
        blk = re.search(pat, txt, re.S)
        out[key] = ([tuple(int(x) for x in t)
                     for t in re.findall(r'\{(\d+),(\d+),(\d+)\}', blk.group(1))]
                    if blk else [])
    out['ui'] = re.findall(r'\{(\d+),(\d+),"([a-z_]+)"\}', txt)
    out['pay_base'] = d.find(MAGIC_PAY)
    out['fp_base'] = d.find(MAGIC_FP)
    out['pay_magic_n'] = d.count(MAGIC_PAY)
    out['fp_magic_n'] = d.count(MAGIC_FP)
    out['lua_n'] = d.count(lua)
    return out


def slots_of(stock):
    """固件镜像里的 119 个槽位：名字 -> (偏移, 长度)，并给出名字顺序的列表。"""
    sl = {}
    for p, i in stock.entries():
        if i.type == 1 or not p.startswith(DIRP) or not p.endswith('.bin') or i.size == 0:
            continue
        sl[os.path.basename(p)] = (i.data_off, i.size)
    return sl


def main():
    stock_b = open(TARGET_IMAGE, 'rb').read()
    patch_b = open(PATCHED, 'rb').read()
    stock = Romfs(TARGET_IMAGE)
    patched = Romfs(PATCHED)
    sl = slots_of(stock)
    exp_name = ['Measuring%d.bin' % k for k in range(1, len(sl) + 1)]
    print('=' * 78)
    print('独立总校验（不读 blob_*/offsets.json、不读 .work/overlay、不读 .work/build）')
    print('  交付物 : dist/%s + dist/%s' % (FACES['replace'], FACES['restore']))
    print('  固件   : inputs/target/vela_health.bin %d B（卷名 %s）'
          % (len(stock_b), stock.volume))
    print('  改后   : .work/anim/vela_health_anim.bin %d B' % len(patch_b))
    print('=' * 78)
    ck(len(sl) == 119, '固件里 %s 下 %d 个槽位（期望 119）' % (DIRP, len(sl)))
    ck(sorted(sl.keys()) == sorted(exp_name), '槽位名字就是 Measuring1..119.bin')

    faces = {}
    for role, fn in FACES.items():
        f = parse_face(os.path.join(DIST, fn))
        faces[role] = f
        other = patch_b if role == 'replace' else stock_b
        print('\n' + '-' * 78)
        print('[%s] %s  %d B  sha256 %s'
              % (role, fn, len(f['data']), hashlib.sha256(f['data']).hexdigest()))
        print('-' * 78)

        # ---- ① 头 + Lua ----
        d = f['data']
        ck(d[0:4] == b'\x5a\xa5\x34\x12', 'magic')
        ck(d[5] == 0, 'b5 = %d（固件自带表盘是 0）' % d[5])
        ck(d[4] == 0, 'b4 = %d' % d[4])
        ck(d[40:50] == WF_ID.encode() + b'\x00', 'id = %r' % d[40:50])
        a32, = struct.unpack('<I', d[32:36])
        pal, pw, ph, psz = struct.unpack('<IHHI', d[a32:a32 + 12])
        ck((pw, ph) == (PREVIEW, PREVIEW), 'preview %dx%d' % (pw, ph))
        ck(f['lua_n'] == 1, 'Lua 在文件里只出现 1 次（偏移 0x%x）' % f['lua_off'])
        ck(f['role'] == role, "Lua 里的 ROLE == '%s'" % role)
        for ph_ in ('__UIIMG__', '__PAY__', '__RB__', '__ROLE__'):
            ck(ph_ not in f['txt'], '占位符 %s 已回填' % ph_)
        ck(re.search(r'local W, H = %d, %d' % (SCREEN, SCREEN), f['txt']) is not None,
           '界面尺寸 W,H = %d,%d' % (SCREEN, SCREEN))
        m = re.search(r'local DEVS = \{([^}]*)\}', f['txt'])
        ck(m is not None and '/dev/health' in m.group(1),
           'DEVS 有 health -> /dev/health')
        ck(len(f['ui']) == 8, 'UIIMG %d 条（期望 8）' % len(f['ui']))

        # ---- ② 表自洽 + 在文件里连续（完全不看 offsets.json）----
        pay, rb = f['pay'], f['rb']
        ck(len(pay) == 119 and len(rb) == 119, 'pay %d 条 / rb %d 条（期望 119/119）'
           % (len(pay), len(rb)))
        ck(f['pay_magic_n'] == 1 and f['fp_magic_n'] == 1,
           '两个魔数各命中 1 次（payload 0x%x / fp 0x%x）' % (f['pay_base'], f['fp_base']))
        cont = 0
        for i, (o, _t, ln) in enumerate(pay):
            if i == 0:
                if o != f['pay_base'] + len(MAGIC_PAY):
                    cont += 1
            elif o != pay[i - 1][0] + pay[i - 1][2]:
                cont += 1
        for i, (o, _t, ln) in enumerate(rb):
            if i == 0:
                if o != f['fp_base'] + len(MAGIC_FP):
                    cont += 1
            elif o != rb[i - 1][0] + rb[i - 1][2]:
                cont += 1
        ck(cont == 0, '两张表的偏移自洽：首条紧跟魔数，之后逐条紧邻（%d 处不连续）' % cont)
        ck(all(rb[i][2] == 64 for i in range(len(rb))), 'rb 每条都是 64 B')

        # ---- ③ 第 k 条落在 Measuring{k}.bin 上 ----
        bad_name = bad_len = 0
        for i, (o, t, ln) in enumerate(pay):
            if t != sl[exp_name[i]][0]:
                bad_name += 1
            if ln != sl[exp_name[i]][1] or rb[i][1] != t:
                bad_len += 1
        ck(bad_name == 0, '第 k 条负载的目标偏移 == Measuring{k}.bin 的偏移（%d 处不符）' % bad_name)
        ck(bad_len == 0, '每条长度 == 该槽位原厂长度，且 rb 的 target 与 pay 一致（%d 处不符）'
           % bad_len)
        ck(all(t % 512 == 0 for _o, t, _l in pay), '119 个目标偏移全部 512 对齐')
        odd = sum(1 for _o, _t, l in pay if l % 4 != 0)
        print('       （%d/119 条长度不是 4 的倍数 -> Lua 侧必须走 bs=512+4+1 分段写，'
              '否则退化成 bs=1）' % odd)

        # ---- ④ 负载字节 == 对应镜像；⑤ 解码 ----
        bad_bytes = bad_dec = bad_hdr = 0
        big_e = 0
        for i, (o, t, ln) in enumerate(pay):
            blob = d[o:o + ln]
            if blob != other[t:t + ln]:
                bad_bytes += 1
            if blob == (stock_b if role == 'replace' else patch_b)[t:t + ln]:
                big_e += 1
            h = L.parse_header(blob)
            if (h is None or h['cf'] != 0x0a or not (h['flags'] & L.FLAG_COMPRESSED)
                    or (h['w'], h['h']) != (FACE_W, FACE_H) or h['stride'] != FACE_W):
                bad_hdr += 1
                continue
            _m, cs, us = struct.unpack('<III', blob[12:24])
            try:
                raw = L.rle_decompress(blob[24:24 + cs], 1, None)
            except Exception:
                bad_dec += 1
                continue
            # ① 解出来必须**恰好** usize（少一字节设备端整帧不画）
            # ② usize = 1024 + w*h + 1 -> 像素区之后**正好** 1 字节尾巴（usize_tail）
            if (len(raw) != us or us != 1024 + FACE_W * FACE_H + 1
                    or len(raw) - 1024 - FACE_W * FACE_H != 1):
                bad_dec += 1
                continue
            try:
                img = L.decode_lvgl_bin(blob)[1]
                if img is None or img.size != (FACE_W, FACE_H):
                    bad_dec += 1
            except Exception:
                bad_dec += 1
        ck(bad_bytes == 0, '每条负载字节 == %s镜像对应位置（%d 处不符）'
           % ('改后' if role == 'replace' else '原厂', bad_bytes))
        ck(big_e == 0, '每条负载都真的与"另一侧"不同（%d 条与另一侧相同 —— 应当是 0）' % big_e)
        ck(bad_hdr == 0, '每条都是 I8(0x0a) + 压缩 + 464x464 + stride 464（%d 条不符）' % bad_hdr)
        ck(bad_dec == 0, '每条 RLE 解出**恰好** usize=216321 且 1024+464*464 之后正好 1 字节尾巴'
                         '（%d 条不符）' % bad_dec)

        # ---- ⑥ 指纹有区分度 ----
        diff_fp = sum(1 for i in range(len(pay))
                      if stock_b[pay[i][1]:pay[i][1] + 64] != patch_b[pay[i][1]:pay[i][1] + 64])
        ck(diff_fp == 119, '%d/119 条的"原厂前 64 B"与"改后前 64 B"确实不同' % diff_fp)
        ck(all(rb[i] == (rb[i][0], sl[exp_name[i]][0], 64) for i in range(len(rb))),
           'rb 的 target 也指向对应槽位')

        # ---- ⑦ UI 素材 ----
        badui = 0
        for o, l, n in f['ui']:
            blob = open(os.path.join(PROJ, 'ui_images', n + '.bin'), 'rb').read()
            if int(l) != len(blob) or d[int(o):int(o) + int(l)] != blob:
                badui += 1
        ck(badui == 0, '8 张界面素材与 ui_images/*.bin 逐字节一致（%d 处不符）' % badui)

    # ================================================================ 两张盘互证
    print('\n' + '=' * 78)
    print('[互证] 两张交付物互相印证（完全不碰 .work / 固件镜像）')
    print('=' * 78)
    rp, rr = faces['replace'], faces['restore']
    ck(len(rp['data']) == len(rr['data']), '两张盘字节数相同（%d）' % len(rp['data']))
    ck(rp['data'][:50] == rr['data'][:50],
       '头 50 B（magic / b4 / b5 / id）逐字节相同')
    cross = 0
    for i in range(119):
        if rp['pay'][i][1] != rr['pay'][i][1]:
            cross += 1
            continue
        o1, t, l1 = rp['pay'][i]
        o2, _t2, l2 = rr['pay'][i]
        if rp['data'][o1:o1 + 64] != rr['data'][rr['rb'][i][0]:rr['rb'][i][0] + 64]:
            cross += 1
        if rr['data'][o2:o2 + 64] != rp['data'][rp['rb'][i][0]:rp['rb'][i][0] + 64]:
            cross += 1
    ck(cross == 0, 'replace 的负载前 64 B == restore 的指纹；restore 的负载前 64 B == '
                   'replace 的指纹（%d 处不符）' % cross)
    same_ui = all(rp['data'][int(o):int(o) + int(l)] == rr['data'][int(o):int(o) + int(l)]
                  for o, l, _n in rp['ui'])
    ck(same_ui, '两张盘的 8 张界面素材逐字节相同（同一套界面）')
    ck(rp['pay_base'] == rr['pay_base'] and rp['fp_base'] == rr['fp_base'],
       '两张盘的资源基址相同（0x%x / 0x%x）' % (rp['pay_base'], rr['fp_base']))
    ndiff = sum(1 for i in range(119)
                if rp['data'][rp['pay'][i][0]:rp['pay'][i][0] + rp['pay'][i][2]] !=
                   rr['data'][rr['pay'][i][0]:rr['pay'][i][0] + rr['pay'][i][2]])
    ck(ndiff == 119, '119/119 条负载在两张盘里都不一样（%d）' % ndiff)

    # ================================================================ 镜像完整性
    print('\n' + '=' * 78)
    print('[镜像] 改后镜像 vs 原厂镜像')
    print('=' * 78)
    a = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in stock.entries()]
    b = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in patched.entries()]
    ck(a == b, 'inode 表（路径/偏移/next/spec/size/cksum）%d 条逐位不变' % len(a))
    ck((stock.sb_size, stock.sb_cksum, stock.volume) ==
       (patched.sb_size, patched.sb_cksum, patched.volume),
       'superblock 与卷名不变（size %d / cksum %08x / %r）'
       % (patched.sb_size, patched.sb_cksum, patched.volume))
    ck(len(stock_b) == len(patch_b), '分区长度不变（%d B）' % len(patch_b))
    slot_offs = {o for o, _l in sl.values()}
    bad_file = 0
    checked = 0
    for _p, i in stock.entries():
        if i.type == 1 or i.data_off in slot_offs:
            continue                      # 目录项 / 119 个槽位本身：槽位在下面单独查
        checked += 1
        if stock_b[i.data_off:i.data_off + i.size] != patch_b[i.data_off:i.data_off + i.size]:
            bad_file += 1
    ck(bad_file == 0, '除 119 个槽位外，其余 %d 个文件的字节**逐字节**不变（%d 处不符）'
       % (checked, bad_file))
    chg = [i for i in range(len(stock_b)) if stock_b[i] != patch_b[i]]
    lo, hi = min(slot_offs), max(o + sl[n][1] for n, (o, _s) in sl.items())
    ck(chg and chg[0] >= lo and chg[-1] < hi,
       '变化区间 0x%x..0x%x 完全落在槽位区间 0x%x..0x%x 内'
       % (chg[0], chg[-1], lo, hi))
    ident = [n for n, (o, _s) in sl.items() if stock_b[o:o + sl[n][1]] == patch_b[o:o + sl[n][1]]]
    ck(not ident, '119 个槽位全部被改写（未变的：%s）' % (ident or '无'))

    print('\n' + '=' * 78)
    print('独立总校验：%d 项通过，%d 项失败' % (ok, fail))
    print('=' * 78)
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
