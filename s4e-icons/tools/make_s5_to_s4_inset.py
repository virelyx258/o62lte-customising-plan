"""S5 -> S4 launcher icons, but matching the STOCK S4 sizing convention.

Measured difference (why icons looked bigger):
    stock S4 art  : 136x136 inside the 144x144 canvas (outer 4px fully transparent)
    S5 art        : 144x144 full-bleed (outer ring painted)

So for every replaced slot whose source art is full-bleed we scale it to
136x136 and centre it in the same 144x144 canvas, then re-encode into the S4
slot's exact colour format.  Every emitted blob keeps the slot's byte length, so
ROMFS absolute offsets stay valid (a length change would corrupt the image).

Slots whose S5 counterpart is already inset (== stock) are still copied
verbatim, so identical icons stay bit-exact.
"""
import os, sys, json, shutil, hashlib, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romfs import Romfs, img_header
from lvgl_bin import decode_lvgl_bin
import iconpack as ip
from PIL import Image, ImageFilter

from paths import PROJ, INPUTS, WORK
S4 = os.path.join(INPUTS, 'target', 'vela_app.bin')
S5_IMAGES = [os.path.join(INPUTS, 'source', 'vela_app.bin'),
             os.path.join(INPUTS, 'source', 'vela_health.bin')]
OUTDIR = os.path.join(WORK, 's4_from_s5')
PATCHED = os.path.join(OUTDIR, 'vela_app_s5icons.bin')
MARGIN = 4

# 出「分组表盘」用：ICON_SKIP_WALKIE=1 -> 只出图标（体积回到 6.58MB 那档）
#                    ICON_ONLY_WALKIE=1 -> 只出对讲机素材（小表盘）
# 对讲机素材：**默认不打包**（用户 2026-10-02 决定不改）。ICON_WALKIE=1 可打开。
DO_WALKIE = os.environ.get('ICON_WALKIE') == '1'
SKIP_WALKIE = (os.environ.get('ICON_SKIP_WALKIE') == '1') or not DO_WALKIE
ONLY_WALKIE = os.environ.get('ICON_ONLY_WALKIE') == '1'
if not DO_WALKIE:
    print('!! 对讲机素材默认不打包（ICON_WALKIE=1 可打开）')
if SKIP_WALKIE:
    print('!! ICON_SKIP_WALKIE=1：本次不打包对讲机素材')
if ONLY_WALKIE:
    print('!! ICON_ONLY_WALKIE=1：本次只打包对讲机素材')

# Slots the user hand-replaced with their own PNGs.  These win over the S5
# firmware source and always go through normalization (crop to the painted area,
# scale to the slot's own painted size, centre) so the emitted blob keeps the
# slot's exact byte length:
#   activities / sports_course / interconnect : 112x112 self-made art
#   voice_aivs                                : 144x144 "小爱同学" user PNG
OVERRIDE = {k: os.path.join(PROJ, 'assets', 'override', k + '.png')
            for k in ('activities', 'sports_course', 'interconnect', 'voice_aivs')}

os.makedirs(OUTDIR, exist_ok=True)
if os.path.exists(PATCHED):
    bak = os.path.join(OUTDIR, 'vela_app_s5icons_fullbleed_backup.bin')
    if not os.path.exists(bak):
        shutil.copyfile(PATCHED, bak)
        print(f'backed up previous (full-bleed) image -> {os.path.basename(bak)}')


def ink_bbox(img, thr=16):
    """bounding box of painted pixels (alpha > thr), or None"""
    a = img.convert('RGBA').getchannel('A')
    w, h = a.size
    px = a.load()
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if px[x, y] > thr:
                if x < x0: x0 = x
                if y < y0: y0 = y
                if x > x1: x1 = x
                if y > y1: y1 = y
    if x1 < 0:
        return None
    return (x0, y0, x1, y1)


def normalize(img, target, canvas_wh):
    """Scale the painted area so its larger side becomes `target`, keeping the
    aspect ratio, and centre it on a transparent canvas of the SLOT size.

    canvas_wh is the slot's own w,h -- the source may be any size (the S5 art is
    144x144, the Band 11 art the user dropped in is 112x112), so the output
    canvas must not be taken from the source.
    """
    cw, ch = canvas_wh
    bb = ink_bbox(img)
    if bb is None:
        return Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    x0, y0, x1, y1 = bb
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    s = float(target) / float(max(bw, bh))
    if abs(s - 1.0) < 1e-6 and (bw, bh) == (cw, ch):
        return img.convert('RGBA')
    art = img.convert('RGBA').crop((x0, y0, x1 + 1, y1 + 1))
    nw, nh = max(1, int(round(bw * s))), max(1, int(round(bh * s)))
    art = art.resize((nw, nh), Image.LANCZOS)
    if s > 1.05:
        # upsampling always softens; give the edges some bite back
        art = art.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3))
    canvas = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    canvas.paste(art, ((cw - nw) // 2, (ch - nh) // 2))
    return canvas


s4 = Romfs(S4)
s4t = ip.targets(s4)

s5 = {}
S5ROM = []
for path in S5_IMAGES:
    r = Romfs(path)
    S5ROM.append(r)
    tag = r.volume
    for key, ino in ip.targets(r).items():
        if key in s5:
            continue
        blob = r.read(ino)
        _, img = decode_lvgl_bin(blob)
        hh = img_header(blob)
        # an I8 source ships its own 256-entry palette: reuse it verbatim
        pal = blob[12:12 + 1024] if (hh and hh['cf'] == 0x0a and len(blob) >= 1036) else None
        s5[key] = (blob, img, tag, ino.size, pal)

print(f'S4 slots: {len(s4t)}   S5 icons: {len(s5)}\n')

plan, skipped, failed, new_blobs, extra_ino = [], [], [], {}, {}
for key, ino in sorted(s4t.items()):
    if ONLY_WALKIE:
        break
    if key not in s5:
        skipped.append((key, 'no S5 counterpart'))
        continue
    h4 = img_header(s4.read(ino))
    blob5, img5, tag5, size5, pal5 = s5[key]
    slot_len = ino.size
    how = None

    # a hand-replaced PNG wins over the firmware source
    ov = OVERRIDE.get(key)
    if ov and os.path.exists(ov):
        img5 = Image.open(ov).convert('RGBA')
        blob5 = b''                      # force re-encode, never verbatim copy
        pal5 = None                      # the S5 palette does not describe THIS art
        tag5 = 'user-png %dx%d' % img5.size

    # what sizing does THIS slot use in the stock image?
    _, stock_img = decode_lvgl_bin(s4.read(ino))
    sb = ink_bbox(stock_img) if stock_img is not None else None
    target = max(sb[2] - sb[0] + 1, sb[3] - sb[1] + 1) if sb else 136

    nb = ink_bbox(img5) if img5 is not None else None
    need = nb is not None and (nb[2] - nb[0] + 1, nb[3] - nb[1] + 1) != (target, target)
    if need:
        src = normalize(img5, target, (h4["w"], h4["h"]))
        if src.size != (h4['w'], h4['h']):
            src = src.resize((h4['w'], h4['h']), Image.LANCZOS)
        try:
            out = ip.encode(src, h4['cf'], h4['w'], h4['h'], h4['flags'], pad_to=slot_len, palette=pal5)
        except ValueError:
            out = None          # slot is RLE-compressed: an uncompressed encode
                                # cannot fit, so fall through to the copy path
        if out is not None and len(out) == slot_len:
            how = 'normalize->%d' % target
        else:
            out = None
    if how is None:
        if len(blob5) == slot_len:
            out, how = blob5, 'copy'
        elif img5 is None:
            failed.append((key, 'S5 source not decodable'))
            continue
        else:
            src = img5
            if src.size != (h4['w'], h4['h']):
                src = src.resize((h4['w'], h4['h']), Image.LANCZOS)
            out = ip.encode(src, h4['cf'], h4['w'], h4['h'], h4['flags'], palette=pal5)
            if len(out) != slot_len:
                failed.append((key, f'encoded {len(out)} != slot {slot_len}'))
                continue
            how = 're-encode'

    plan.append(dict(name=key, offset=ino.data_off, length=slot_len,
                     s4_format=ip.FMT.get(h4['cf'], f"0x{h4['cf']:02x}"),
                     s4_flags=h4['flags'], s5_bytes=len(blob5), s5_from=tag5,
                     method=how))
    new_blobs[key] = out

# ---------------------------------------------------------------- 控制中心磁贴（q63 -> S4 eSIM）
# S4 eSIM / S5 eSIM 的控制中心是「蓝色主题」（选中 = 实心蓝盘，未选中 = 深色盘）；
# q63（S5 41mm / OS4）是「浅色主题」（选中 = 白盘 + 蓝字形）。整批一起搬才协调。
CC_DIR = 'control_center/icon/'
# 除了整目录的控制中心磁贴，再点名搬这几张系统 UI 素材（和 S5 eSIM 那份一致）。
# 健康分区的两条（notification_stand / notification_vigor）本来就和 q63 逐字节相同，
# 而且 S4 这边只解出了 app 分区，所以列在这里也会被跳过。
SYS_PATHS = [
    'system/icon/lock_icon.bin',
    'common/icon/system_lock.bin',
    'common/icon/lock.bin',
    'system/icon/unlock.bin',
    'common/icon/quiet_mode.bin',
    'common/icon/unread_msg.bin',
    'notifications/default.bin',
    'notifications/default_small.bin',
    'notifications/no_message.bin',
    'settings/icon/notify.bin',
    'settings/disturb/confirm.bin',
    'esimsms/icon/esim_sms_reminder.bin',
    'esimsms/icon/sms_no_read.bin',
    'esimsms/icon/sms_reminder_watch.bin',
    'phone/icon/send_sms_new.bin',
    'mijia/enable_donot_disturb.bin',
    'mijia/disable_donot_disturb.bin',
    # 压力 App 的小表情（S4 没有 health 分区，这些都在 /dev/app；q63 那份在它的 health 里）
    'pressure/icon/presure_relax.bin',
    'pressure/icon/presure_mild.bin',
    'pressure/icon/presure_mid.bin',
    'pressure/icon/presure_severe.bin',
    'pressure/icon/presure_relax32.bin',
    'pressure/icon/presure_mild32.bin',
    'pressure/icon/presure_mid32.bin',
    'pressure/icon/presure_severe32.bin',
    'pressure/icon/presure_relax96.bin',
    'pressure/icon/presure_mild96.bin',
    'pressure/icon/presure_mid96.bin',
    'pressure/icon/presure_severe96.bin',
    'pressure/icon/presure_icon.bin',
    'pressure/icon/press_grade1.bin',
    'pressure/icon/press_grade2.bin',
    'pressure/icon/press_grade3.bin',
    'pressure/icon/press_grade4.bin',
    'pressure/icon/pressure_eomji_bg.bin',
    'pressure/icon/pressure_eomji_widbg.bin',
]
s4_all = {p: i for p, i in s4.entries() if i.type != 1}
s5_all = {}
for _r in S5ROM:
    for _p, _i in _r.entries():
        if _i.type != 1 and _p not in s5_all:
            s5_all[_p] = (_r, _i)

print('\n--- 控制中心磁贴 + 系统 UI 素材（q63 -> S4 eSIM）---')
cc_paths = set()
_all_paths = sorted(p for p in s4_all if p.startswith(CC_DIR) and p.endswith('.bin'))
for _sp in SYS_PATHS:
    if _sp in s4_all and _sp not in _all_paths:
        _all_paths.append(_sp)
if ONLY_WALKIE:
    _all_paths = []
for path in _all_paths:
    tino = s4_all[path]
    got = s5_all.get(path)
    if got is None:
        skipped.append((path, 'q63 没有这个文件')); continue
    qrom, oino = got
    tgt_blob = s4.read(tino)
    src_blob = qrom.read(oino)
    if src_blob == tgt_blob:
        skipped.append((path, '两边字节完全相同')); continue
    th = img_header(tgt_blob) if len(tgt_blob) >= 12 else None
    sh = img_header(src_blob) if len(src_blob) >= 12 else None
    if len(src_blob) == len(tgt_blob):
        new, how = src_blob, 'copy(等长)'
    elif th and sh and th['cf'] == sh['cf']:
        timg = decode_lvgl_bin(tgt_blob)[1]
        simg = decode_lvgl_bin(src_blob)[1]
        if timg is None or simg is None:
            skipped.append((path, '无法解码（cf=0x%02x）' % (th['cf'] if th else 0))); continue
        sb = ink_bbox(timg)
        nb = ink_bbox(simg)
        if sb and nb:
            tw, thh = sb[2] - sb[0] + 1, sb[3] - sb[1] + 1
            art = simg.convert('RGBA').crop((nb[0], nb[1], nb[2] + 1, nb[3] + 1))
            if art.size != (tw, thh):
                up = tw > art.size[0] or thh > art.size[1]
                art = art.resize((tw, thh), Image.LANCZOS)
                if up:
                    art = art.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3))
            canvas = Image.new('RGBA', (th['w'], th['h']), (0, 0, 0, 0))
            canvas.paste(art, (sb[0], sb[1]))
            out = canvas
        else:
            out = simg
        pal = src_blob[12:12 + 1024] if sh['cf'] == ip.CF_I8 else None
        new = ip.encode(out, th['cf'], th['w'], th['h'], th['flags'], palette=pal)
        how = 'rescale %dx%d->%dx%d' % (sh['w'], sh['h'], th['w'], th['h'])
    else:
        skipped.append((path, '长度/格式不支持')); continue
    if len(new) != len(tgt_blob):
        failed.append((path, '编码 %d != 槽位 %d' % (len(new), len(tgt_blob)))); continue
    is_cc = path.startswith(CC_DIR)
    name = ('cc_' if is_cc else 'sys_') + path.split('/')[-1][:-4]
    new_blobs[name] = new
    extra_ino[name] = tino
    cc_paths.add(path)
    plan.append(dict(name=name, kind=('cc' if is_cc else 'sysicon'), path=path, offset=tino.data_off, length=len(tgt_blob),
                     s4_format=ip.FMT.get(th['cf'], '0x%02x' % th['cf']) if th else '?',
                     s4_flags=th['flags'] if th else 0, s5_bytes=len(src_blob),
                     s5_from='q63 %s' % os.path.basename(qrom.path), method=how))
    print('  %-46s %-22s %s' % (path, how, ''))


# ------------------------------------------------- 对讲机素材（用户提供的整套 PNG）
# walkie_talkie/ 下的槽位几乎**全是 I8+RLE 压缩**的：直接编码长度会变（ROMFS 偏移全平移），
# 所以走 ip.encode_into_slot()：量化 -> RLE -> 用 ctrl=0 空指令补齐到原 csize，
# 保证与原槽位逐字节等长。
WALKIE_SRC = os.path.join(PROJ, 'assets', 'walkie_talkie')
walk_paths = set()
mijia_paths = set()
print('\n--- 对讲机素材 walkie_talkie（用户 PNG）-> S4 eSIM ---')
walkie_n = 0
if SKIP_WALKIE or not os.path.isdir(WALKIE_SRC):
    print('  跳过这一组（ICON_SKIP_WALKIE=%s / 目录存在=%s）'
          % (SKIP_WALKIE, os.path.isdir(WALKIE_SRC)))
else:
    _rels = []
    for _root, _, _files in os.walk(WALKIE_SRC):
        for _f in _files:
            if _f.lower().endswith('.png'):
                _rels.append(os.path.relpath(os.path.join(_root, _f), WALKIE_SRC).replace('\\', '/'))
    for rel in sorted(_rels):
        path = 'walkie_talkie/' + rel[:-4] + '.bin'
        tino = s4_all.get(path)
        if tino is None:
            skipped.append((path, '目标固件没有这个槽位')); continue
        tgt_blob = s4.read(tino)
        img = Image.open(os.path.join(WALKIE_SRC, rel))
        new, how = ip.encode_into_slot(img, tgt_blob, tino.size)
        if new is None:
            skipped.append((path, how)); continue
        if new == tgt_blob:
            skipped.append((path, '与现有一致')); continue
        th = img_header(tgt_blob)
        name = 'walk_' + rel[:-4].replace('/', '_')
        new_blobs[name] = new
        extra_ino[name] = tino
        walk_paths.add(path)
        plan.append(dict(name=name, kind='walkie', path=path, offset=tino.data_off,
                         length=tino.size,
                         s4_format=ip.FMT.get(th['cf'], '0x%02x' % th['cf']) if th else '?',
                         s4_flags=th['flags'] if th else 0, s5_bytes=0,
                         s5_from='用户 PNG assets/walkie_talkie/' + rel, method=how))
        walkie_n += 1
        if walkie_n <= 6 or walkie_n % 40 == 0:
            print('  %-52s %-18s %d B' % (path, how, tino.size))
    print('  对讲机素材写入 %d 条' % walkie_n)

# ------------------------------------------------- 控制中心顶部状态区（q63 -> S4 eSIM）
# q63 的顶栏素材在 control_center/bar/：wifi 4 档 / 蜂窝信号 5 档 / 3G·4G 文字 /
# 蓝牙连接·断开 / 飞行模式 / 定位 / 勿扰 / 静音。本机同名槽位在 control_center/icon/（48x48 I8）。
# 尺寸不同的（q63 那几张 36x36）按**实心范围**归一化：把 q63 的实心图缩放到本机槽位的实心范围、
# 贴在同样的原点 —— 位置与视觉重量和本机原有图标一致。
CC_TOP = [
    ('control_center/icon/network_4g.bin',       'control_center/bar/network_4g.bin',      '4G 文字'),
    ('control_center/icon/network_3g.bin',       'control_center/bar/network_3g.bin',      '3G 文字'),
    ('control_center/icon/signal_strength.bin',  'control_center/bar/signal_strength0.bin', '蜂窝信号 0'),
    ('control_center/icon/signal_strength1.bin', 'control_center/bar/signal_strength1.bin', '蜂窝信号 1'),
    ('control_center/icon/signal_strength2.bin', 'control_center/bar/signal_strength2.bin', '蜂窝信号 2'),
    ('control_center/icon/signal_strength3.bin', 'control_center/bar/signal_strength3.bin', '蜂窝信号 3'),
    ('control_center/icon/signal_strength4.bin', 'control_center/bar/signal_strength4.bin', '蜂窝信号 4'),
    ('control_center/icon/air_mode_conn.bin',    'control_center/bar/air.bin',             '飞行模式'),
    ('control_center/icon/bt_connect.bin',       'control_center/bar/connect.bin',         '蓝牙已连接手机'),
    ('control_center/icon/bt_disconnect.bin',    'control_center/bar/disconnect.bin',      '蓝牙未连接'),
    ('control_center/icon/location.bin',         'control_center/bar/local.bin',           '定位'),
    ('control_center/icon/wifi_level_0.bin',     'control_center/bar/wifi_level_0.bin',    'WiFi 0'),
    ('control_center/icon/wifi_level_1.bin',     'control_center/bar/wifi_level_1.bin',    'WiFi 1'),
    ('control_center/icon/wifi_level_2.bin',     'control_center/bar/wifi_level_2.bin',    'WiFi 2'),
    ('control_center/icon/wifi_level_3.bin',     'control_center/bar/wifi_level_3.bin',    'WiFi 3'),
]
# 本机把「3G/4G 文字 + 信号格」合成在一张图里，而 q63 是分开的两张 —— 按本机原有的两段实心区域
# 分别填：左边文字段用 q63 的 3G/4G，右边信号段用 q63 的 signal_strengthN。
CC_COMPOSED = []
for _net in ('3g', '4g'):
    for _n in range(1, 5):
        CC_COMPOSED.append(('control_center/icon/network_%s_signal_%d.bin' % (_net, _n),
                            'control_center/bar/network_%s.bin' % _net,
                            'control_center/bar/signal_strength%d.bin' % _n))
    CC_COMPOSED.append(('control_center/icon/network_%s_no_signal.bin' % _net,
                        'control_center/bar/network_%s.bin' % _net,
                        'control_center/bar/signal_strength0.bin'))
# 手机电量（本机 phone/icon/battery_level_*）：q63 同名，只是高度不同
for _n in range(0, 11):
    CC_TOP.append(('phone/icon/battery_level_%d.bin' % _n,
                   'phone/icon/battery_level_%d.bin' % _n, '手机电量 %d' % _n))


def _split_two(img):
    """把「文字 + 信号格」这类合成图按空列切成左右两段，返回两段 bbox（失败返回 None）。"""
    a = img.convert('RGBA').getchannel('A')
    w, h = a.size
    px = a.load()
    cols = [any(px[x, y] > 16 for y in range(h)) for x in range(w)]
    gaps, run = [], None
    for x, on in enumerate(cols):
        if not on:
            run = x if run is None else run
        else:
            # 只认「两侧都有实心」的空隙：开头的空白段（0..n）不是切分点
            if run is not None and run > 0 and x - run >= 1:
                gaps.append((run, x - 1))
            run = None
    if not gaps:
        return None
    # 取**最左边**那个「两侧都有实心」的空隙 = 文字与信号格之间的分界
    # （取最宽的会落在信号格之间，把格数挤进一条缝里）
    g0, g1 = gaps[0]
    left = [x for x in range(0, g0) if cols[x]]
    right = [x for x in range(g1 + 1, w) if cols[x]]
    if not left or not right:
        return None

    def bbox(xs):
        ys = [y for y in range(h) for x in xs if px[x, y] > 16]
        return (min(xs), min(ys), max(xs), max(ys))
    return bbox(left), bbox(right)


def normalize_to_bbox(src_img, target_bb, canvas_wh, fit=False):
    """把 src 的**实心区域**放进 target_bb。

    fit=False：拉伸填满 target_bb（槽位画法本来就一致时用）
    fit=True ：**等比**缩放到能放进 target_bb 的最大尺寸并居中（不拉伸 —— 合成图里
               「信号格」这类会因横纵比例不同被压扁，必须走这条）
    """
    cw, ch = canvas_wh
    if target_bb is None:
        return Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    sb = ink_bbox(src_img)
    if sb is None:
        return Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    tw, thh = target_bb[2] - target_bb[0] + 1, target_bb[3] - target_bb[1] + 1
    art = src_img.convert('RGBA').crop((sb[0], sb[1], sb[2] + 1, sb[3] + 1))
    if fit:
        s = min(tw / art.size[0], thh / art.size[1])
        nw, nh = max(1, round(art.size[0] * s)), max(1, round(art.size[1] * s))
        if (nw, nh) != art.size:
            up = s > 1.0
            art = art.resize((nw, nh), Image.LANCZOS)
            if up:
                art = art.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3))
        pos = (target_bb[0] + (tw - nw) // 2, target_bb[1] + (thh - nh) // 2)
    else:
        if art.size != (tw, thh):
            up = tw > art.size[0] or thh > art.size[1]
            art = art.resize((tw, thh), Image.LANCZOS)
            if up:
                art = art.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3))
        pos = (target_bb[0], target_bb[1])
    canvas = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    canvas.paste(art, pos)
    return canvas


print('\n--- 控制中心顶部状态区（q63 control_center/bar -> S4 eSIM）---')
cc_top_n = 0
for tpath, spath, note in CC_TOP:
    tino = s4_all.get(tpath)
    got = s5_all.get(spath)
    if tino is None:
        skipped.append((tpath, '本机没有这个槽位')); continue
    if got is None:
        skipped.append((spath, 'q63 没有这个素材')); continue
    qrom, oino = got
    tgt_blob = s4.read(tino)
    src_blob = qrom.read(oino)
    th = img_header(tgt_blob)
    timg = decode_lvgl_bin(tgt_blob)[1]
    simg = decode_lvgl_bin(src_blob)[1]
    if timg is None or simg is None:
        skipped.append((tpath, '解码失败')); continue
    sb = ink_bbox(timg)
    out = normalize_to_bbox(simg, sb, (th['w'], th['h']))
    pal = src_blob[12:12 + 1024] if img_header(src_blob)['cf'] == ip.CF_I8 else None
    new = ip.encode(out, th['cf'], th['w'], th['h'], th['flags'], palette=pal)
    if len(new) != len(tgt_blob):
        failed.append((tpath, '编码 %d != 槽位 %d' % (len(new), len(tgt_blob)))); continue
    if new == tgt_blob:
        skipped.append((tpath, '两边已经一致')); continue
    # 与 sys 组用同名 -> 同一槽位只保留一条记录（后者覆盖前者）
    name = ('cc_' if tpath.startswith(CC_DIR) else 'sys_') + tpath.split('/')[-1][:-4]
    new_blobs[name] = new
    extra_ino[name] = tino
    cc_paths.add(tpath)
    plan.append(dict(name=name, kind='cctop', path=tpath, offset=tino.data_off, length=tino.size,
                     s4_format=ip.FMT.get(th['cf'], '0x%02x' % th['cf']), s4_flags=th['flags'],
                     s5_bytes=len(src_blob), s5_from='q63 %s' % spath, method='归一化(%s)' % note))
    cc_top_n += 1
    print('  %-46s <- %-40s %s' % (tpath, spath, note))
print('  顶栏状态区写入 %d 条' % cc_top_n)

print('\n--- 控制中心「3G/4G+信号格」合成图（S4e 的 network_* + S5e 的 signal_strength）---')
# 合成来源按要求改：文字取 **本机（S4e）** 的 network_3g/4g，信号格取 **S5e** 的 signal_strength*
# （S5e 表盘里的当前版本，若它已被移植过就是新的蓝色版；没有就用它的原厂版）
S5E_IMG = os.path.join(PROJ, '..', 's5e-icons', '.work', 's5e_from_os4', 'vela_app_os4.bin')
_s5e = Romfs(S5E_IMG) if os.path.exists(S5E_IMG) else None
_s5e_tab = {q: i for q, i in _s5e.entries()} if _s5e else {}
print('  S5e 信号格来源: %s' % ('S5e 表盘镜像' if _s5e else '（缺，回退 q63）'))
cc_comp_n = 0
for tpath, tpath_text, tpath_bars in CC_COMPOSED:
    tino = s4_all.get(tpath)
    gt = s5_all.get(tpath_text)
    gb = s5_all.get(tpath_bars)
    if tino is None or gt is None or gb is None:
        skipped.append((tpath, '缺槽位或 q63 缺素材')); continue
    tgt_blob = s4.read(tino)
    th = img_header(tgt_blob)
    timg = decode_lvgl_bin(tgt_blob)[1]
    if timg is None:
        skipped.append((tpath, '本机图解码失败')); continue
    parts = _split_two(timg)
    if parts is None:
        skipped.append((tpath, '切不开两段（布局不同）')); continue
    (tx0, ty0, tx1, ty1), (bx0, by0, bx1, by1) = parts
    canvas = Image.new('RGBA', (th['w'], th['h']), (0, 0, 0, 0))
    pal = None
    ow = th['w'] - 4                        # 用满整张宽度（左右各留 2px）
    x0 = 2
    gap = 3
    tw_new = max(10, round(ow * 0.44))
    bw_new = max(10, ow - tw_new - gap)
    text_bb = (x0, 0, x0 + tw_new - 1, th['h'] - 1)
    bars_x0 = x0 + tw_new + gap
    bars_bb = (bars_x0, 0, bars_x0 + bw_new - 1, th['h'] - 1)

    # 文字：优先用**本次刚写好的本机 network_3g/4g**（就是 S4e 上的那张）
    tname = ('cc_' if tpath_text.startswith(CC_DIR) else 'sys_') + tpath_text.split('/')[-1][:-4]
    text_img = decode_lvgl_bin(new_blobs[tname])[1] if tname in new_blobs else None
    if text_img is None:
        text_img = decode_lvgl_bin(gt[0].read(gt[1]))[1]
    canvas.alpha_composite(normalize_to_bbox(text_img, text_bb, (th['w'], th['h']), fit=True))
    pal = new_blobs[tname][12:12 + 1024] if tname in new_blobs else None

    # 信号格：**S5e** 的同名槽位（signal_strength / signal_strength1..4）
    lvl = tpath_bars.split('signal_strength')[-1][:-4]      # '', '1'...'4'
    s5e_name = 'control_center/icon/signal_strength%s.bin' % lvl
    bars_img = None
    if _s5e is not None and s5e_name in _s5e_tab:
        bars_img = decode_lvgl_bin(_s5e.read(_s5e_tab[s5e_name]))[1]
    if bars_img is None:
        bars_img = decode_lvgl_bin(gb[0].read(gb[1]))[1]
    if bars_img is None:
        skipped.append((tpath, '信号格来源解码失败')); continue
    canvas.alpha_composite(normalize_to_bbox(bars_img, bars_bb, (th['w'], th['h']), fit=True))

    new = ip.encode(canvas, th['cf'], th['w'], th['h'], th['flags'], palette=pal)
    if len(new) != len(tgt_blob):
        failed.append((tpath, '编码 %d != 槽位 %d' % (len(new), len(tgt_blob)))); continue
    if new == tgt_blob:
        skipped.append((tpath, '两边已经一致')); continue
    # 与 sys 组用同名 -> 同一槽位只保留一条记录（后者覆盖前者）
    name = ('cc_' if tpath.startswith(CC_DIR) else 'sys_') + tpath.split('/')[-1][:-4]
    new_blobs[name] = new
    extra_ino[name] = tino
    cc_paths.add(tpath)
    plan.append(dict(name=name, kind='cctop', path=tpath, offset=tino.data_off, length=tino.size,
                     s4_format=ip.FMT.get(th['cf'], '0x%02x' % th['cf']), s4_flags=th['flags'],
                     s5_bytes=0, s5_from='S4e %s + S5e %s' % (tpath_text, s5e_name),
                     method='合成(文字+信号格)'))
    cc_comp_n += 1
    print('  %-46s <- S4e %s + S5e %s' % (tpath, tpath_text.split('/')[-1], s5e_name.split('/')[-1]))
print('  合成图写入 %d 条' % cc_comp_n)

# ------------------------------------------------- 米家 / 融合中心（控制中心里的米家设备图标）
# 规则：q63 的 fusion_center/** 与 mijia/** 里，**同名路径**在本机也有的就移植
# （S5e 还有一份 fusion_center/gauss/**，同名的一并写）。画布尺寸两边常常不同
# （q63 是 116/64，本机是 96/128），所以按**实心范围**对齐 + 转成本机槽位的格式。
PLATE_KEEP = ('headset',)   # 只有这种「裸图案」槽位保留底版 + 图案归位
# q63 的「柔光玻璃」底盘（干净的深色玻璃圆盘 + 发丝高光环）—— 用它当底版
_glass = None
_g = s5_all.get('fusion_center/fg.bin')
if _g is not None:
    _glass = decode_lvgl_bin(_g[0].read(_g[1]))[1]
    if _glass is not None:
        _glass = _glass.convert('RGBA')
        print('柔光玻璃盘: q63 fusion_center/fg.bin %dx%d' % _glass.size)
MIJIA_PREFIX = ('fusion_center/', 'mijia/')
# 控制中心的米家/融合中心那组：**默认不打包**（用户 2026-10-02 决定不改）。ICON_MIJIA=1 可打开。
DO_MIJIA = os.environ.get('ICON_MIJIA') == '1'
def plate_glyph_bbox(img, tol=26, min_plate=0.30):
    """目标图标里「底版上的图案」的 bbox。

    本机很多设备图标是「深色圆底版 + 亮色图案」；q63 有的素材是**裸图案（没有底版）**，
    这时按实心范围缩放会把图案放大到整个底版 —— 必须改成：保留底版，把裸图案放回
    原图案的位置/尺寸。做法：底版色 = 出现最多的颜色，其余像素的 bbox 就是原图案。
    """
    rgba = img.convert('RGBA')
    w, h = rgba.size
    px = rgba.load()
    cnt = {}
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] > 16:
                cnt[p] = cnt.get(p, 0) + 1
    if not cnt:
        return None
    plate, n = max(cnt.items(), key=lambda kv: kv[1])
    if n >= min_plate * w * h:
        xs, ys = [], []
        for y in range(h):
            for x in range(w):
                p = px[x, y]
                if p[3] > 16 and (abs(p[0] - plate[0]) + abs(p[1] - plate[1]) + abs(p[2] - plate[2])) > tol:
                    xs.append(x); ys.append(y)
        if xs:
            return (min(xs), min(ys), max(xs), max(ys))
    # 兜底：底版是渐变（没有主导纯色）时，用**亮度**找亮图案（深色底版上的白图案）
    lum = {}
    mx = 0
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] > 16:
                v = 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]
                lum[(x, y)] = v
                mx = max(mx, v)
    if not lum or mx <= 0:
        return None
    thr = 0.62 * mx
    xs = [x for (x, y), v in lum.items() if v >= thr]
    ys = [y for (x, y), v in lum.items() if v >= thr]
    if not xs:
        return None
    bb = (min(xs), min(ys), max(xs), max(ys))
    if (bb[2] - bb[0] + 1) * (bb[3] - bb[1] + 1) > 0.92 * w * h:
        return None                      # 亮像素几乎铺满 -> 它本身就是全幅图案，不做归位
    return bb


def ink_ratio(img):
    """实心范围占画布的比例（两个方向取大者）—— 接近 1.0 说明是"满幅/带底版"的图。"""
    bb = ink_bbox(img)
    if bb is None:
        return 0.0
    w, h = img.size
    return max((bb[2] - bb[0] + 1) / w, (bb[3] - bb[1] + 1) / h)


def overlay_glyph_in_place(tgt_blob, th, src_img, target_bb):
    """在**索引层**把 q63 的裸图案画进本机 I8 图标：底版像素一个比特都不动。

    为什么必须这么做：底版是抖动/渐变，重新量化（无论用谁的调色板）都会出噪点或白环。
    只有直接改索引数组，底版才保持原样；图案像素按最近色映射到**本机自己的调色板**
    （本机图标里本来就有白色，所以白色图案能精确命中）。
    """
    w, h, cf = th['w'], th['h'], th['cf']
    if cf != ip.CF_I8 or (th['flags'] & 0x08):
        return None
    if len(tgt_blob) != 12 + 1024 + w * h:
        return None
    pal_b = tgt_blob[12:12 + 1024]
    pal = [(pal_b[i * 4 + 2], pal_b[i * 4 + 1], pal_b[i * 4 + 0], pal_b[i * 4 + 3]) for i in range(256)]
    idx = bytearray(tgt_blob[12 + 1024:12 + 1024 + w * h])
    # 把图案等比放进 target_bb 后的实际位置/尺寸
    nb = ink_bbox(src_img)
    if nb is None or target_bb is None:
        return None
    tw, thh = target_bb[2] - target_bb[0] + 1, target_bb[3] - target_bb[1] + 1
    art = src_img.convert('RGBA').crop((nb[0], nb[1], nb[2] + 1, nb[3] + 1))
    s = min(tw / art.size[0], thh / art.size[1])
    art = art.resize((max(1, round(art.size[0] * s)), max(1, round(art.size[1] * s))), Image.LANCZOS)
    ox = target_bb[0] + (tw - art.width) // 2
    oy = target_bb[1] + (thh - art.height) // 2
    cache = {}
    for y in range(art.height):
        for x in range(art.width):
            r, g, b, a = art.getpixel((x, y))
            if a < 24:
                continue
            key = (r, g, b, a)
            ci = cache.get(key)
            if ci is None:
                best, bd = 0, 1 << 30
                for k in range(256):
                    pr, pg, pb, pa = pal[k]
                    d = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2 + 2 * (pa - a) ** 2
                    if d < bd:
                        bd, best = d, k
                cache[key] = ci = best
            ix, iy = ox + x, oy + y
            if 0 <= ix < w and 0 <= iy < h:
                idx[iy * w + ix] = ci
    return tgt_blob[:12 + 1024] + bytes(idx)


def plate_share(img, gbb):
    """底版像素占实心像素的比例 —— 用来确认这张图**真的有底版**（不是纯图案）。"""
    if gbb is None:
        return 0.0
    a = img.convert('RGBA').getchannel('A')
    w, h = a.size
    px = a.load()
    ink = tot = 0
    for y in range(h):
        for x in range(w):
            if px[x, y] > 16:
                tot += 1
                if not (gbb[0] <= x <= gbb[2] and gbb[1] <= y <= gbb[3]):
                    ink += 1
    return (ink / tot) if tot else 0.0


print('\n--- 米家 / 融合中心素材（q63 -> S4 eSIM）%s ---' % ('' if DO_MIJIA else '：已按设置跳过'))
mijia_n = 0
for _q in sorted(s5_all):
    if not DO_MIJIA or not _q.startswith(MIJIA_PREFIX):
        continue
    if _q.endswith('launcher.bin'):
        continue                       # 应用图标由 launcher 组处理（那边处理 ARGB 画法）
    _got = s5_all[_q]
    if _got[0] is None:
        continue
    qrom, oino = _got
    cands = [_q]
    if _q.startswith('fusion_center/icon/'):
        cands.append(_q.replace('fusion_center/icon/', 'fusion_center/gauss/'))
    for tpath in cands:
        tino = s4_all.get(tpath)
        if tino is None:
            if tpath == _q:
                skipped.append((tpath, '本机没有这个槽位'))
            continue
        tgt_blob = s4.read(tino)
        src_blob = qrom.read(oino)
        th, sh = img_header(tgt_blob), img_header(src_blob)
        if th is None or sh is None:
            skipped.append((tpath, '头部异常')); continue
        simg = decode_lvgl_bin(src_blob)[1]
        if simg is None:
            skipped.append((tpath, 'q63 素材解码失败(cf=0x%02x)' % sh['cf'])); continue
        how = None
        if (th['flags'] & 0x08) or th['cf'] not in (ip.CF_I8, ip.CF_ARGB8888):
            new, how = ip.encode_into_slot(simg, tgt_blob, tino.size)
        else:
            timg = decode_lvgl_bin(tgt_blob)[1]
            if timg is None:
                skipped.append((tpath, '本机图解码失败(cf=0x%02x)' % th['cf'])); continue
            gbb = plate_glyph_bbox(timg)
            # 只对「裸图案」的槽位用这个模式（本机是底版+图案、q63 是裸图案）。
            # 底版直接用 **q63 那张柔光玻璃盘**（fusion_center/fg.bin），而不是本机原来的平底，
            # 这样移植过去的图标看着就是 S5 41mm 的玻璃质感。
            if (gbb is not None and ink_ratio(simg) < 0.90
                    and plate_share(timg, gbb) >= 0.45
                    and tpath.rsplit('/', 1)[-1][:-4] in PLATE_KEEP):
                # 底版原样保留（索引层），只把 q63 的裸图案画进去
                new = overlay_glyph_in_place(tgt_blob, th, simg, gbb)
                if new is None:
                    skipped.append((tpath, '索引层合成不可用（非未压缩 I8）')); continue
                out, how = None, '底版原样+图案入索引 %dx%d->%dx%d' % (sh['w'], sh['h'], th['w'], th['h'])
            else:
                out = normalize_to_bbox(simg, ink_bbox(timg), (th['w'], th['h']))
                how = '等比归一化 %dx%d->%dx%d' % (sh['w'], sh['h'], th['w'], th['h'])
                pal = src_blob[12:12 + 1024] if sh['cf'] == ip.CF_I8 else None
                new = ip.encode(out, th['cf'], th['w'], th['h'], th['flags'], palette=pal)
        if new is None or len(new) != tino.size:
            failed.append((tpath, '编码失败/长度不符 (%s)' % how)); continue
        if new == tgt_blob:
            skipped.append((tpath, '两边已经一致')); continue
        name = 'sys_' + tpath.replace('/', '_')[:-4]
        new_blobs[name] = new
        extra_ino[name] = tino
        mijia_paths.add(tpath)
        plan.append(dict(name=name, kind='mijia', path=tpath, offset=tino.data_off, length=tino.size,
                         s4_format=ip.FMT.get(th['cf'], '0x%02x' % th['cf']), s4_flags=th['flags'],
                         s5_bytes=len(src_blob), s5_from='q63 %s' % _q, method=how))
        mijia_n += 1
        if mijia_n <= 8 or mijia_n % 20 == 0:
            print('  %-52s <- %-34s %s' % (tpath, _q, how))
print('  米家/融合中心写入 %d 条' % mijia_n)

# ------------------------------------------------- 焦点通知素材（q63 notifications/** -> 本机）
# 同名路径对齐移植；尺寸不同的按实心范围归一化，格式不同自动转换（RLE / ARGB / I8）。
PORT_PREFIXES = ('notifications/', 'phone/', 'recorder/', 'timer/', 'todolist/')
# 用户指定：这两张保持原厂不换（本机槽位形状差太多，压过去效果不好）
NOTIF_SKIP = ('notifications/dotted_line.bin', 'notifications/track.bin',
              # 用户指定：录音机这 3 张不换
              'recorder/mark_opt.bin', 'recorder/menu.bin', 'recorder/confirm.bin',
              # 用户指定：拨号列表这 3 张不换
              'phone/icon/list_icon_keypad.bin', 'phone/icon/list_icon_call_log.bin',
              'phone/icon/list_icon_contact.bin',
              # 用户指定：组件预览底图这 2 张不换
              'phone/widget/phone_widget.bin', 'phone/widget/pre_phone_widget.bin')
# 应用图标归「launcher 组」管（那边处理 I8↔ARGB 与留边画法），这里跳过避免重复写同一槽位
PORT_SKIP_TAIL = ('launcher.bin', 'launcher')
print('\n--- 通知/电话/录音机素材（q63 同名移植 -> S4 eSIM）---')
notif_n = 0
for _q in sorted(s5_all):
    if not _q.startswith(PORT_PREFIXES):
        continue
    if _q in NOTIF_SKIP:
        skipped.append((_q, '按约定保持原厂')); continue
    if _q.rsplit('/', 1)[-1].endswith('launcher.bin'):
        continue
    _got = s5_all[_q]
    if _got[0] is None:
        continue
    qrom, oino = _got
    tino = s4_all.get(_q)
    if tino is None:
        skipped.append((_q, '本机没有这个槽位')); continue
    tgt_blob = s4.read(tino)
    src_blob = qrom.read(oino)
    th, sh = img_header(tgt_blob), img_header(src_blob)
    if th is None or sh is None:
        skipped.append((_q, '头部异常')); continue
    simg = decode_lvgl_bin(src_blob)[1]
    if simg is None:
        skipped.append((_q, 'q63 素材解码失败(cf=0x%02x)' % sh['cf'])); continue
    how = None
    if (th['flags'] & 0x08) or th['cf'] not in (ip.CF_I8, ip.CF_ARGB8888):
        new, how = ip.encode_into_slot(simg, tgt_blob, tino.size)
        if new is None:
            skipped.append((_q, how)); continue
    else:
        timg = decode_lvgl_bin(tgt_blob)[1]
        if timg is None:
            skipped.append((_q, '本机图解码失败(cf=0x%02x)' % th['cf'])); continue
        # 一律等比缩放（长宽比不同也不拉伸）
        out = normalize_to_bbox(simg, ink_bbox(timg), (th['w'], th['h']), fit=True)
        pal = src_blob[12:12 + 1024] if sh['cf'] == ip.CF_I8 else None
        new = ip.encode(out, th['cf'], th['w'], th['h'], th['flags'], palette=pal)
        how = '等比归一化 %dx%d->%dx%d' % (sh['w'], sh['h'], th['w'], th['h'])
    if len(new) != tino.size:
        failed.append((_q, '编码 %d != 槽位 %d' % (len(new), tino.size))); continue
    if new == tgt_blob:
        skipped.append((_q, '两边已经一致')); continue
    name = 'sys_' + _q.replace('/', '_')[:-4]
    new_blobs[name] = new
    extra_ino[name] = tino
    mijia_paths.add(_q)
    plan.append(dict(name=name, kind='notif', path=_q, offset=tino.data_off, length=tino.size,
                     s4_format=ip.FMT.get(th['cf'], '0x%02x' % th['cf']), s4_flags=th['flags'],
                     s5_bytes=len(src_blob), s5_from='q63 %s' % _q, method=how))
    notif_n += 1
    print('  %-46s <- q63 %-30s %s' % (_q, _q.split('/')[-1], how))
print('  通知/电话/录音机写入 %d 条' % notif_n)

n_inset = sum(1 for p in plan if p['method'] == 'inset')
print(f'{"name":<24}{"slot":>8}{"fmt":>10}{"S5 bytes":>10}  method')
for p in plan:
    print(f'{p["name"]:<24}{p["length"]:>8}{p["s4_format"]:>10}{p["s5_bytes"]:>10}  {p["method"]}')
for k, why in skipped:
    print(f'{k:<24}{"-":>8}{"-":>10}{"-":>10}  SKIP  {why}')
for k, why in failed:
    print(f'{k:<24}{"-":>8}{"-":>10}{"-":>10}  FAIL  {why}')
print(f'\nreplace {len(plan)} (inset {n_inset})   skip {len(skipped)}   failed {len(failed)}')

# 同一槽位可能被多个组写过（sys / 顶栏 / 米家）-> 按 **inode** 去重，后写的赢
_byoff = {}
for _n, _i in extra_ino.items():
    _byoff[_i.off] = (_n, _i)
extra_ino = {_n: _i for _n, _i in _byoff.values()}

all_items = [(key, ino) for key, ino in sorted(s4t.items()) if key in new_blobs]
all_items += [(name, ino) for name, ino in extra_ino.items()]

# plan 里同一槽位的旧记录也去掉（只留最后一条）
_dedup = {}
for _p in plan:
    _dedup[_p['name']] = _p
plan = list(_dedup.values())
patch, rollback = bytearray(), bytearray()
for key, ino in all_items:
    new, old = new_blobs[key], s4.read(ino)
    patch += struct.pack('<II', ino.data_off, len(new)) + new
    rollback += struct.pack('<II', ino.data_off, len(old)) + old
open(os.path.join(OUTDIR, 'icons.patch'), 'wb').write(patch)
open(os.path.join(OUTDIR, 'icons.rollback'), 'wb').write(rollback)
json.dump(dict(target='Xiaomi Watch S4 eSIM (o62lte) vela_app.bin',
               source='Xiaomi Watch S5 (q63) v4.101.020 icons, inset to S4 convention',
               sizing=f'full-bleed sources scaled to {144-2*MARGIN}x{144-2*MARGIN} '
                      f'and centred with a {MARGIN}px transparent margin',
               image_sha256=hashlib.sha256(s4.data).hexdigest(),
               replace_count=len(plan), records=plan,
               skipped=[dict(name=k, reason=w) for k, w in skipped]),
          open(os.path.join(OUTDIR, 'manifest.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

print('\nwriting patched image ...')
shutil.copyfile(S4, PATCHED)
with open(PATCHED, 'r+b') as f:
    for key, ino in all_items:
        f.seek(ino.data_off)
        f.write(new_blobs[key])

r2 = Romfs(PATCHED)
a = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in s4.entries()]
b = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in r2.entries()]
print(f'entries {len(a)} -> {len(b)}   inode table identical: {a == b}')
print(f'superblock identical: {s4.sb_size == r2.sb_size and s4.sb_cksum == r2.sb_cksum}')
i1 = {p: i for p, i in s4.entries()}
i2 = {p: i for p, i in r2.entries()}
changed = sorted(p for p in i1 if s4.read(i1[p]) != r2.read(i2[p]))
diff_items = [(k, i) for k, i in all_items if new_blobs[k] != s4.read(i)]
print(f'changed files ({len(changed)}), 预期 {len(diff_items)}')
assert len(changed) == len(diff_items), 'changed %d != expected %d' % (len(changed), len(diff_items))
assert all(c.rsplit('/', 1)[-1].endswith('launcher.bin') or c in cc_paths or c in walk_paths
           or c in mijia_paths for c in changed), changed[:5]
print('sha256', hashlib.sha256(open(PATCHED, "rb").read()).hexdigest())
