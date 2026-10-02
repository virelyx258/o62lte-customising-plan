# -*- coding: utf-8 -*-
"""S5 41mm (q63, OS4) launcher icons -> Xiaomi Watch S5 eSIM (p62lte, 480x480).

Target slots live in TWO partitions:
    vela_app.bin    (/dev/app)    34 launcher.bin
    vela_health.bin (/dev/health) 15 launcher.bin
All 49 target slots are 144x144 ARGB8888 (82956 bytes) -- so the replacement is
ALWAYS exactly one slot long, which is what keeps the ROMFS absolute offsets valid.

Sizing convention (measured, not guessed):
    the S5 eSIM stock art is inset in the 144 canvas (136x136 at (4,4) for almost
    every slot, 138 at (3,3) for launcher_*, 144 full-bleed for a few), while the
    OS4 source art is mostly full-bleed 144x144.  So each source is cropped to its
    painted bbox, scaled to the TARGET slot's own painted size and pasted at the
    TARGET slot's origin.  Sources that already match are copied without resampling
    (bit-exact).

Outputs
    watchface_s5e/payload/payload.bin           MAGIC + concat(replace blobs)
    watchface_s5e/payload/payload.lua           per-record table for main.lua
    watchface_s5e/payload_rollback/...          same for the stock bytes
    _out/s5e_from_os4/vela_app_os4.bin          whole-image variants (route C)
    _out/s5e_from_os4/vela_health_os4.bin
"""
import os, sys, json, struct, hashlib, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romfs import Romfs, img_header
from lvgl_bin import decode_lvgl_bin
import iconpack as ip
from PIL import Image, ImageFilter

from paths import PROJ, INPUTS, WORK
NEW = os.path.join(INPUTS, 'target')      # 目标固件分区（p62lte）
OLD = os.path.join(INPUTS, 'source')      # 图标来源分区（q63 = S5 41mm）
WF = PROJ
OUT = os.path.join(WORK, 's5e_from_os4')  # manifest + 整分区镜像（产物）

PART = [('app', 'vela_app.bin', '/dev/app'),
        ('health', 'vela_health.bin', '/dev/health')]
MAGIC_PAY = b'\x00S5E-PAYv1\x00\xa5\x5a\xc3\x3c'      # 15 B, must stay unique in the .face
MAGIC_RB  = b'\x00S5E-RBKv1\x00\x5a\xa5\x3c\xc3'

# 自制图覆盖：优先级高于固件来源（和 S4 项目同一套做法）。
#   activities  : 112x112 的红/绿/青同心环 = 用户要的「跑道」图标
#   voice_aivs  : 144x144 的「小爱同学」用户 PNG
OVERRIDE = {k: os.path.join(PROJ, 'assets', 'override', k + '.png')
            for k in ('activities', 'voice_aivs')}

os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(WF, 'payload'), exist_ok=True)
os.makedirs(os.path.join(WF, 'payload_rollback'), exist_ok=True)


def ink_bbox(img, thr=16):
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
    return None if x1 < 0 else (x0, y0, x1, y1)


def normalize(src_img, slot_bb, canvas):
    """crop to painted bbox -> scale to the slot's painted size -> paste at slot origin"""
    cw, ch = canvas
    if slot_bb is None:
        return Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    sx0, sy0, sx1, sy1 = slot_bb
    tw, th = sx1 - sx0 + 1, sy1 - sy0 + 1
    nb = ink_bbox(src_img)
    if nb is None:
        return Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    if (nb[2] - nb[0] + 1, nb[3] - nb[1] + 1) == (tw, th) and (nb[0], nb[1]) == (sx0, sy0):
        return src_img.convert('RGBA')                   # already identical geometry
    art = src_img.convert('RGBA').crop((nb[0], nb[1], nb[2] + 1, nb[3] + 1))
    if art.size != (tw, th):
        up = tw > art.size[0] or th > art.size[1]
        art = art.resize((tw, th), Image.LANCZOS)
        if up:
            art = art.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3))
    canvas_img = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    canvas_img.paste(art, (sx0, sy0))
    return canvas_img


def normalize_fit(src_img, target_bb, canvas):
    """等比缩放源实心区域到能放进 target_bb 的最大尺寸并居中（不拉伸）。"""
    cw, ch = canvas
    cv = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    if target_bb is None:
        return cv
    nb = ink_bbox(src_img)
    if nb is None:
        return cv
    tw, th = target_bb[2] - target_bb[0] + 1, target_bb[3] - target_bb[1] + 1
    art = src_img.convert('RGBA').crop((nb[0], nb[1], nb[2] + 1, nb[3] + 1))
    s = min(tw / art.size[0], th / art.size[1])
    nw, nh = max(1, round(art.size[0] * s)), max(1, round(art.size[1] * s))
    if (nw, nh) != art.size:
        up = s > 1.0
        art = art.resize((nw, nh), Image.LANCZOS)
        if up:
            art = art.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3))
    cv.paste(art, (target_bb[0] + (tw - nw) // 2, target_bb[1] + (th - nh) // 2))
    return cv


# ------------------------------------------------------------------ load slots
slots = []          # ordered records
ROM_N = {}
for tag, fn, dev in PART:
    r = Romfs(os.path.join(NEW, fn))
    ROM_N[tag] = r
    tg = ip.targets(r)
    for name in sorted(tg):
        ino = tg[name]
        blob = r.read(ino)
        h, img = decode_lvgl_bin(blob)
        slots.append(dict(tag=tag, dev=dev, image=fn, name=name, ino=ino, blob=blob,
                          h=h, img=img, bb=ink_bbox(img) if img is not None else None))

src = {}
ROM_O = {}
for fn in ['vela_app.bin', 'vela_health.bin']:
    r = Romfs(os.path.join(OLD, fn))
    ROM_O['app' if fn == 'vela_app.bin' else 'health'] = r
    for name, ino in ip.targets(r).items():
        if name in src: continue
        h, img = decode_lvgl_bin(r.read(ino))
        src[name] = (h, img, r.read(ino))

print('target slots %d   source icons %d' % (len(slots), len(src)))
rows, newblobs, stock_of, skipped = [], {}, {}, []
for s in slots:
    h = s['h']
    if h is None:
        skipped.append((s['name'], 'target not decodable')); continue
    if s['name'] not in src:
        skipped.append((s['name'], 'no OS4 source')); continue
    sh, simg, sblob = src[s['name']]
    if simg is None:
        skipped.append((s['name'], 'source not decodable')); continue
    src_from = 'q63 固件 %s' % s['image']
    ov = OVERRIDE.get(s['name'])
    if ov and os.path.exists(ov):
        # 自制图覆盖：裁到实心 bbox -> 缩放到目标槽位的画法（136x136）-> 居中粘回 (4,4)
        simg = Image.open(ov).convert('RGBA')
        sblob = b''
        src_from = '自制图 %s (%dx%d)' % (os.path.basename(ov), simg.size[0], simg.size[1])
        print('  [override] %-14s <- %s %dx%d' % (s['name'], os.path.basename(ov),
                                                 simg.size[0], simg.size[1]))
    out_img = normalize(simg, s['bb'], (h['w'], h['h']))
    blob = ip.encode(out_img, h['cf'], h['w'], h['h'], h['flags'])
    if len(blob) != s['ino'].size:
        skipped.append((s['name'], 'length %d != slot %d' % (len(blob), s['ino'].size))); continue
    exact = (blob == sblob)
    newblobs[s['name']] = blob
    stock_of[s['name']] = s['blob']
    rows.append(dict(name=s['name'], tag=s['tag'], dev=s['tag'], node=s['dev'], image=s['image'],
                     offset=s['ino'].data_off, length=s['ino'].size,
                     dim='%dx%d' % (h['w'], h['h']), cf=ip.FMT.get(h['cf'], hex(h['cf'])),
                     stock_ink=s['bb'], source_from=src_from,
                     identical_to_stock=exact,
                     sha256=hashlib.sha256(blob).hexdigest(),
                     rb_sha256=hashlib.sha256(s['blob']).hexdigest()))

print('%-24s %-7s %-12s %-14s %s' % ('name', 'part', 'offset', 'slot', 'stock ink -> new'))
for s in slots:
    r = next((x for x in rows if x['name'] == s['name']), None)
    if r:
        print('%-24s %-7s 0x%08x %-8d %-14s' % (r['name'], r['tag'], r['offset'], r['length'],
                                                str(r['stock_ink']) + ('  (identical)' if r['identical_to_stock'] else '')))
for n, why in skipped:
    print('%-24s SKIP  %s' % (n, why))
print('\nreplace %d   skip %d' % (len(rows), len(skipped)))


# ------------------------------------------------- 系统 UI 素材：从 S5 41mm(q63) 搬过来
# 只搬「独立字形图标」（锁屏 / 通知中心 / 设置 / 米家）。控制中心的开关磁贴**故意没搬**：
#   q63 的控制中心是白色主题（白盘 + 深色字形，运行时着色），S5 eSIM 是蓝色主题（预着色成品），
#   只搬那 4 张会变成「白盘混在蓝盘里」；要搬就得整套 ~40 张一起搬。
SYSICONS = [
    ('app', 'system/icon/lock_icon.bin', '锁屏上的锁'),
    ('app', 'common/icon/system_lock.bin', '状态栏系统锁'),
    ('app', 'common/icon/lock.bin', '通用锁'),
    ('app', 'system/icon/unlock.bin', '解锁提示页'),
    ('app', 'common/icon/quiet_mode.bin', '免打扰/静音小图标'),
    ('app', 'common/icon/unread_msg.bin', '未读消息红点'),
    ('app', 'notifications/default.bin', '通知默认大图标'),
    ('app', 'notifications/default_small.bin', '通知默认小图标'),
    ('app', 'notifications/no_message.bin', '通知中心空状态'),
    ('app', 'settings/icon/notify.bin', '设置-通知'),
    ('app', 'settings/disturb/confirm.bin', '免打扰确认按钮'),
    ('app', 'esimsms/icon/esim_sms_reminder.bin', '短信提醒'),
    ('app', 'esimsms/icon/sms_no_read.bin', '未读短信'),
    ('app', 'esimsms/icon/sms_reminder_watch.bin', '手表短信提醒'),
    ('app', 'phone/icon/send_sms_new.bin', '新建短信'),
    ('app', 'mijia/enable_donot_disturb.bin', '米家 免打扰开'),
    ('app', 'mijia/disable_donot_disturb.bin', '米家 免打扰关'),
    ('health', 'activities/icon/notification_stand.bin', '久坐提醒'),
    ('health', 'activities/icon/notification_vigor.bin', '活力提醒'),
    # 压力 App 的小表情（4 档情绪 × 32/48/96，96 那三张两边本来就一样，会被自动跳过）
    ('health', 'pressure/icon/presure_relax.bin', '压力表情-放松 48'),
    ('health', 'pressure/icon/presure_mild.bin', '压力表情-轻度 48'),
    ('health', 'pressure/icon/presure_mid.bin', '压力表情-中度 48'),
    ('health', 'pressure/icon/presure_severe.bin', '压力表情-重度 48'),
    ('health', 'pressure/icon/presure_relax32.bin', '压力表情-放松 32'),
    ('health', 'pressure/icon/presure_mild32.bin', '压力表情-轻度 32'),
    ('health', 'pressure/icon/presure_mid32.bin', '压力表情-中度 32'),
    ('health', 'pressure/icon/presure_severe32.bin', '压力表情-重度 32'),
    ('health', 'pressure/icon/presure_relax96.bin', '压力表情-放松 96'),
    ('health', 'pressure/icon/presure_mild96.bin', '压力表情-轻度 96'),
    ('health', 'pressure/icon/presure_mid96.bin', '压力表情-中度 96'),
    ('health', 'pressure/icon/presure_severe96.bin', '压力表情-重度 96'),
    ('health', 'pressure/icon/presure_icon.bin', '压力 App 小图标'),
    ('health', 'pressure/icon/press_grade1.bin', '压力等级徽标 1'),
    ('health', 'pressure/icon/press_grade2.bin', '压力等级徽标 2'),
    ('health', 'pressure/icon/press_grade3.bin', '压力等级徽标 3'),
    ('health', 'pressure/icon/press_grade4.bin', '压力等级徽标 4'),
    ('health', 'pressure/icon/pressure_eomji_bg.bin', '表情底版'),
    ('health', 'pressure/icon/pressure_eomji_widbg.bin', '表情底版(小)'),
    # 没有搬（体积大 / 不是表情）：pressure_bg、success_bg、success_arc、
    # press_widget_bg*、press_chart_bg、pressure_widget_pre_img*、reminder、measure/*
]


# 整目录一起搬（q63 有同名文件的才搬）：控制中心的开关磁贴
SYSICONS_DIRS = ['control_center/icon/']


def find_inode(romfs, path):
    for p, i in romfs.entries():
        if p == path and i.type != 1:
            return i
    return None


print('\n--- 系统 UI 素材（锁屏 / 勿扰 / 通知 / 控制中心）：q63 -> S5 eSIM ---')
_jobs = [(d, p, n) for d, p, n in SYSICONS]
_seen = {p for _, p, _ in _jobs}
for _dev in ROM_N:
    for _p, _i in ROM_N[_dev].entries():
        if _i.type == 1 or _p in _seen:
            continue
        if any(_p.startswith(_d) for _d in SYSICONS_DIRS):
            _jobs.append((_dev, _p, '控制中心磁贴'))
            _seen.add(_p)
for dev, path, note in _jobs:
    ti = find_inode(ROM_N[dev], path)
    oi = find_inode(ROM_O[dev], path)
    if ti is None:
        skipped.append((path, '目标固件没有这个文件')); continue
    if oi is None:
        skipped.append((path, 'q63 没有这个文件')); continue
    tgt_blob = ROM_N[dev].read(ti)
    src_blob = ROM_O[dev].read(oi)
    if src_blob == tgt_blob:
        print('  %-52s 两边字节完全相同，跳过' % path)
        continue
    th = img_header(tgt_blob)
    sh = img_header(src_blob)
    if len(src_blob) == len(tgt_blob):
        new, how = src_blob, 'copy(等长)'
    elif th and sh and th['cf'] == sh['cf']:
        timg = decode_lvgl_bin(tgt_blob)[1]
        simg = decode_lvgl_bin(src_blob)[1]
        if timg is None or simg is None:
            skipped.append((path, '无法解码')); continue
        pal = src_blob[12:12 + 1024] if sh['cf'] == ip.CF_I8 else None
        out = normalize_fit(simg, ink_bbox(timg), (th['w'], th['h']))
        new = ip.encode(out, th['cf'], th['w'], th['h'], th['flags'], palette=pal)
        how = 'rescale %dx%d->%dx%d' % (sh['w'], sh['h'], th['w'], th['h'])
    else:
        skipped.append((path, '长度/格式不支持')); continue
    if len(new) != len(tgt_blob):
        skipped.append((path, '编码 %d != 槽位 %d' % (len(new), len(tgt_blob)))); continue
    name = 'sys:' + path
    newblobs[name] = new
    stock_of[name] = tgt_blob
    rows.append(dict(name=name, kind='sysicon', path=path, note=note, how=how,
                     tag=dev, dev=dev, node='/dev/' + dev, image=path,
                     offset=ti.data_off, length=ti.size,
                     dim=('%dx%d' % (th['w'], th['h'])) if th else '?',
                     cf=ip.FMT.get(th['cf'], hex(th['cf'])) if th else '?',
                     stock_ink=ink_bbox(decode_lvgl_bin(tgt_blob)[1]) if th and decode_lvgl_bin(tgt_blob)[1] else None,
                     source_from='q63 固件 / ' + path, identical_to_stock=False,
                     sha256=hashlib.sha256(new).hexdigest(),
                     rb_sha256=hashlib.sha256(tgt_blob).hexdigest()))
    print('  %-52s %-22s %s' % (path, how, note))


# ------------------------------------------------- 对讲机素材（用户提供的整套 PNG）
# walkie_talkie/ 下的槽位几乎**全是 I8+RLE 压缩**的：不能像图标那样直接编码（长度会变），
# 必须走 ip.encode_into_slot()：量化 -> RLE -> 用 ctrl=0 空指令补齐到原 csize，
# 这样字节数与原槽位完全相等，ROMFS 后面所有偏移一个字节都不动。
WALKIE_SRC = os.path.join(PROJ, 'assets', 'walkie_talkie')
# 对讲机素材：**默认不打包**（用户 2026-10-02 决定不改）。ICON_WALKIE=1 可打开。
DO_WALKIE = os.environ.get('ICON_WALKIE') == '1'
print('\n--- 对讲机素材 walkie_talkie（用户 PNG）-> S5 eSIM ---')
walkie_n = 0
if not DO_WALKIE:
    print('  按设置跳过这一组（ICON_WALKIE=1 可打开）')
elif not os.path.isdir(WALKIE_SRC):
    print('  没有 %s，跳过这一组' % WALKIE_SRC)
else:
    rels = []
    for root, _, files in os.walk(WALKIE_SRC):
        for f in files:
            if f.lower().endswith('.png'):
                rels.append(os.path.relpath(os.path.join(root, f), WALKIE_SRC).replace('\\', '/'))
    for rel in sorted(rels):
        path = 'walkie_talkie/' + rel[:-4] + '.bin'
        dev = 'app'
        ti = find_inode(ROM_N[dev], path)
        if ti is None:
            skipped.append((path, '目标固件没有这个槽位')); continue
        tgt_blob = ROM_N[dev].read(ti)
        img = Image.open(os.path.join(WALKIE_SRC, rel))
        new, how = ip.encode_into_slot(img, tgt_blob, ti.size)
        if new is None:
            skipped.append((path, how)); continue
        if new == tgt_blob:
            print('  %-52s 与现有一致，跳过' % path); continue
        th = img_header(tgt_blob)
        name = 'walk:' + path
        newblobs[name] = new
        stock_of[name] = tgt_blob
        rows.append(dict(name=name, kind='walkie', path=path, note='对讲机素材', how=how,
                         tag=dev, dev=dev, node='/dev/' + dev, image=path,
                         offset=ti.data_off, length=ti.size,
                         dim=('%dx%d' % (th['w'], th['h'])) if th else '?',
                         cf=ip.FMT.get(th['cf'], hex(th['cf'])) if th else '?',
                         stock_ink=None, source_from='用户 PNG assets/walkie_talkie/' + rel,
                         identical_to_stock=False,
                         sha256=hashlib.sha256(new).hexdigest(),
                         rb_sha256=hashlib.sha256(tgt_blob).hexdigest()))
        walkie_n += 1
        if walkie_n <= 6 or walkie_n % 40 == 0:
            print('  %-52s %-18s %d B' % (path, how, ti.size))
    print('  对讲机素材写入 %d 条' % walkie_n)


# ------------------------------------------------- 控制中心顶部状态区（q63 -> S5 eSIM）
# q63 的顶栏素材在 control_center/bar/：wifi 4 档 / 蜂窝信号 5 档 / 3G·4G 文字 /
# 蓝牙连接·断开 / 飞行模式 / 定位。本机同名槽位在 control_center/icon/（48x48 I8）。
# 尺寸不同的（q63 那几张 36x36）按**实心范围**归一化（normalize(simg, ink_bbox(timg), ...)）。
CC_TOP = [
    ('control_center/icon/network_4g.bin',       'control_center/bar/network_4g.bin',       '4G 文字'),
    ('control_center/icon/network_3g.bin',       'control_center/bar/network_3g.bin',       '3G 文字'),
    ('control_center/icon/signal_strength.bin',  'control_center/bar/signal_strength0.bin', '蜂窝信号 0'),
    ('control_center/icon/signal_strength1.bin', 'control_center/bar/signal_strength1.bin', '蜂窝信号 1'),
    ('control_center/icon/signal_strength2.bin', 'control_center/bar/signal_strength2.bin', '蜂窝信号 2'),
    ('control_center/icon/signal_strength3.bin', 'control_center/bar/signal_strength3.bin', '蜂窝信号 3'),
    ('control_center/icon/signal_strength4.bin', 'control_center/bar/signal_strength4.bin', '蜂窝信号 4'),
    ('control_center/icon/air_mode_conn.bin',    'control_center/bar/air.bin',              '飞行模式'),
    ('control_center/icon/bt_connect.bin',       'control_center/bar/connect.bin',          '蓝牙已连接手机'),
    ('control_center/icon/bt_connect_g.bin',     'control_center/bar/connect.bin',          '蓝牙已连接手机(g)'),
    ('control_center/icon/bt_disconnect.bin',    'control_center/bar/disconnect.bin',       '蓝牙未连接'),
    ('control_center/icon/location.bin',         'control_center/bar/local.bin',            '定位'),
    ('control_center/icon/wifi_level_0.bin',     'control_center/bar/wifi_level_0.bin',     'WiFi 0'),
    ('control_center/icon/wifi_level_1.bin',     'control_center/bar/wifi_level_1.bin',     'WiFi 1'),
    ('control_center/icon/wifi_level_2.bin',     'control_center/bar/wifi_level_2.bin',     'WiFi 2'),
    ('control_center/icon/wifi_level_3.bin',     'control_center/bar/wifi_level_3.bin',     'WiFi 3'),
]
# 手机电量（本机 phone/icon/battery_level_*，64x22）：q63 同名但 64x32
for _n in range(0, 11):
    CC_TOP.append(('phone/icon/battery_level_%d.bin' % _n,
                   'phone/icon/battery_level_%d.bin' % _n, '手机电量 %d' % _n))

print('\n--- 控制中心顶部状态区（q63 control_center/bar -> S5 eSIM）---')
cc_top_n = 0
for tpath, spath, note in CC_TOP:
    ti = find_inode(ROM_N['app'], tpath)
    if ti is None:
        ti = find_inode(ROM_N['health'], tpath)
        dev = 'health'
    else:
        dev = 'app'
    if ti is None:
        skipped.append((tpath, '本机没有这个槽位')); continue
    oi = find_inode(ROM_O[dev], spath)
    if oi is None:
        skipped.append((spath, 'q63 没有这个素材')); continue
    tgt_blob = ROM_N[dev].read(ti)
    src_blob = ROM_O[dev].read(oi)
    th = img_header(tgt_blob)
    sh = img_header(src_blob)
    timg = decode_lvgl_bin(tgt_blob)[1]
    simg = decode_lvgl_bin(src_blob)[1]
    if timg is None or simg is None:
        skipped.append((tpath, '解码失败')); continue
    out = normalize(simg, ink_bbox(timg), (th['w'], th['h']))
    pal = src_blob[12:12 + 1024] if sh['cf'] == ip.CF_I8 else None
    new = ip.encode(out, th['cf'], th['w'], th['h'], th['flags'], palette=pal)
    if len(new) != len(tgt_blob):
        failed.append((tpath, '编码 %d != 槽位 %d' % (len(new), len(tgt_blob)))); continue
    if new == tgt_blob:
        skipped.append((tpath, '两边已经一致')); continue
    # 与 SYSICONS 组同名 -> 同一槽位只保留一条记录（这里覆盖那边的旧风格版本）
    name = 'sys:' + tpath
    rows[:] = [r for r in rows if r['name'] != name]
    newblobs[name] = new
    stock_of[name] = tgt_blob
    rows.append(dict(name=name, kind='sysicon', path=tpath, note=note, how='归一化(%s)' % note,
                     tag=dev, dev=dev, node='/dev/' + dev, image=tpath,
                     offset=ti.data_off, length=ti.size,
                     dim='%dx%d' % (th['w'], th['h']),
                     cf=ip.FMT.get(th['cf'], hex(th['cf'])),
                     stock_ink=ink_bbox(timg), source_from='q63 ' + spath,
                     identical_to_stock=False,
                     sha256=hashlib.sha256(new).hexdigest(),
                     rb_sha256=hashlib.sha256(tgt_blob).hexdigest()))
    cc_top_n += 1
    print('  %-46s <- %-40s %s' % (tpath, spath, note))
print('  顶栏状态区写入 %d 条' % cc_top_n)


# ------------------------------------------------- 米家 / 融合中心（控制中心里的米家设备图标）
# q63 的 fusion_center/** 与 mijia/** 里**同名路径**本机也有的就移植；本机还有一份
# fusion_center/gauss/**（同名的一并写）。画布尺寸两边常常不同（q63 116/64 vs 本机 96/128），
# 按**实心范围**对齐并转成本机槽位的格式。
PLATE_KEEP = ('headset',)   # 只有这种「裸图案」槽位保留底版 + 图案归位
# 控制中心的米家/融合中心那组：**默认不打包**（用户 2026-10-02 决定不改）。ICON_MIJIA=1 可打开。
DO_MIJIA = os.environ.get('ICON_MIJIA') == '1'
# q63 的「柔光玻璃」底盘（干净的深色玻璃圆盘 + 发丝高光环）
_glass = None
_g = find_inode(ROM_O['app'], 'fusion_center/fg.bin')
if _g is not None:
    _glass = decode_lvgl_bin(ROM_O['app'].read(_g))[1]
    if _glass is not None:
        _glass = _glass.convert('RGBA')
        print('柔光玻璃盘: q63 fusion_center/fg.bin %dx%d' % _glass.size)
MIJIA_PREFIX = ('fusion_center/', 'mijia/')
def plate_glyph_bbox(img, tol=26, min_plate=0.30):
    """本机图标是「底版 + 图案」时，返回底版上图案的 bbox（底版色 = 出现最多的颜色）。"""
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
    # 兜底：底版是渐变（没有主导纯色）时，用**亮度**找亮图案
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
        return None
    return bb


def ink_ratio(img):
    bb = ink_bbox(img)
    if bb is None:
        return 0.0
    w, h = img.size
    return max((bb[2] - bb[0] + 1) / w, (bb[3] - bb[1] + 1) / h)


def normalize_fit(src_img, target_bb, canvas):
    """等比缩放源实心区域到能放进 target_bb 的最大尺寸并居中（不拉伸）。"""
    cw, ch = canvas
    cv = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    if target_bb is None:
        return cv
    nb = ink_bbox(src_img)
    if nb is None:
        return cv
    tw, th = target_bb[2] - target_bb[0] + 1, target_bb[3] - target_bb[1] + 1
    art = src_img.convert('RGBA').crop((nb[0], nb[1], nb[2] + 1, nb[3] + 1))
    s = min(tw / art.size[0], th / art.size[1])
    nw, nh = max(1, round(art.size[0] * s)), max(1, round(art.size[1] * s))
    if (nw, nh) != art.size:
        up = s > 1.0
        art = art.resize((nw, nh), Image.LANCZOS)
        if up:
            art = art.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3))
    cv.paste(art, (target_bb[0] + (tw - nw) // 2, target_bb[1] + (th - nh) // 2))
    return cv



def overlay_glyph_in_place(tgt_blob, th, src_img, target_bb):
    """在**索引层**把 q63 的裸图案画进本机 I8 图标：底版像素一个比特都不动。

    底版是抖动/渐变，重新量化（用谁的调色板都一样）会出噪点或白环；只有直接改索引数组
    底版才保持原样。图案像素按最近色映射到**本机自己的调色板**（本机图标里本来就有白色）。
    """
    w, h, cf = th['w'], th['h'], th['cf']
    if cf != ip.CF_I8 or (th['flags'] & 0x08):
        return None
    if len(tgt_blob) != 12 + 1024 + w * h:
        return None
    pal_b = tgt_blob[12:12 + 1024]
    pal = [(pal_b[i * 4 + 2], pal_b[i * 4 + 1], pal_b[i * 4 + 0], pal_b[i * 4 + 3]) for i in range(256)]
    idx = bytearray(tgt_blob[12 + 1024:12 + 1024 + w * h])
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
    """底版像素占实心像素的比例 —— 确认这张图**真的有底版**（不是纯图案）。"""
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


print('\n--- 米家 / 融合中心素材（q63 -> S5 eSIM）%s ---' % ('' if DO_MIJIA else '：已按设置跳过'))
mijia_n = 0
_mijia_srcs = []
if DO_MIJIA:
    for _dev0 in ('app', 'health'):
        for _p, _i in ROM_O[_dev0].entries():
            if _i.type == 2 and _p.startswith(MIJIA_PREFIX) and not _p.endswith('launcher.bin'):
                _mijia_srcs.append((_p, _dev0))
for _q, _srcdev in sorted(set(_mijia_srcs)):
    cands = [_q]
    if _q.startswith('fusion_center/icon/'):
        cands.append(_q.replace('fusion_center/icon/', 'fusion_center/gauss/'))
    for tpath in cands:
        dev = 'app'
        ti = find_inode(ROM_N[dev], tpath)
        if ti is None:
            ti = find_inode(ROM_N['health'], tpath)
            dev = 'health'
        if ti is None:
            if tpath == _q:
                skipped.append((tpath, '本机没有这个槽位'))
            continue
        oi = find_inode(ROM_O[_srcdev], _q)
        if oi is None:
            skipped.append((_q, 'q63 没有这个素材')); continue
        tgt_blob = ROM_N[dev].read(ti)
        src_blob = ROM_O[_srcdev].read(oi)
        th, sh = img_header(tgt_blob), img_header(src_blob)
        if th is None or sh is None:
            skipped.append((tpath, '头部异常')); continue
        simg = decode_lvgl_bin(src_blob)[1]
        if simg is None:
            skipped.append((tpath, 'q63 素材解码失败(cf=0x%02x)' % sh['cf'])); continue
        if (th['flags'] & 0x08) or th['cf'] not in (ip.CF_I8, ip.CF_ARGB8888):
            new, how = ip.encode_into_slot(simg, tgt_blob, ti.size)
        else:
            timg = decode_lvgl_bin(tgt_blob)[1]
            if timg is None:
                skipped.append((tpath, '本机图解码失败(cf=0x%02x)' % th['cf'])); continue
            gbb = plate_glyph_bbox(timg)
            pal = None
            if (gbb is not None and ink_ratio(simg) < 0.90
                    and plate_share(timg, gbb) >= 0.45
                    and tpath.rsplit('/', 1)[-1][:-4] in PLATE_KEEP):
                # 底版原样保留（索引层），只把 q63 的裸图案画进去
                new = overlay_glyph_in_place(tgt_blob, th, simg, gbb)
                if new is None:
                    skipped.append((tpath, '索引层合成不可用')); continue
                out = None
                how = '底版原样+图案入索引 %dx%d->%dx%d' % (sh['w'], sh['h'], th['w'], th['h'])
            else:
                out = normalize_fit(simg, ink_bbox(timg), (th['w'], th['h']))
                how = '归一化 %dx%d->%dx%d' % (sh['w'], sh['h'], th['w'], th['h'])
                pal = src_blob[12:12 + 1024] if sh['cf'] == ip.CF_I8 else None
            if out is not None:
                new = ip.encode(out, th['cf'], th['w'], th['h'], th['flags'], palette=pal)
        if new is None or len(new) != ti.size:
            skipped.append((tpath, '编码失败/长度不符')); continue
        if new == tgt_blob:
            skipped.append((tpath, '两边已经一致')); continue
        name = 'sys:' + tpath
        rows[:] = [r for r in rows if r['name'] != name]
        newblobs[name] = new
        stock_of[name] = tgt_blob
        rows.append(dict(name=name, kind='sysicon', path=tpath, note='米家/融合中心', how=how,
                         tag=dev, dev=dev, node='/dev/' + dev, image=tpath,
                         offset=ti.data_off, length=ti.size,
                         dim='%dx%d' % (th['w'], th['h']),
                         cf=ip.FMT.get(th['cf'], hex(th['cf'])),
                         stock_ink=ink_bbox(timg) if 'timg' in dir() and timg else None,
                         source_from='q63 ' + _q, identical_to_stock=False,
                         sha256=hashlib.sha256(new).hexdigest(),
                         rb_sha256=hashlib.sha256(tgt_blob).hexdigest()))
        mijia_n += 1
        if mijia_n <= 8 or mijia_n % 20 == 0:
            print('  %-52s <- %-34s %s' % (tpath, _q, how))
print('  米家/融合中心写入 %d 条' % mijia_n)


# ------------------------------------------------- 焦点通知素材（q63 notifications/** -> 本机）
PORT_PREFIXES = ('notifications/', 'phone/', 'recorder/', 'timer/', 'todolist/')
# 用户指定：这两张保持原厂不换
NOTIF_SKIP = ('notifications/dotted_line.bin', 'notifications/track.bin',
              # 用户指定：录音机这 3 张不换
              'recorder/mark_opt.bin', 'recorder/menu.bin', 'recorder/confirm.bin',
              # 用户指定：拨号列表这 3 张不换
              'phone/icon/list_icon_keypad.bin', 'phone/icon/list_icon_call_log.bin',
              'phone/icon/list_icon_contact.bin',
              # 用户指定：组件预览底图这 2 张不换
              'phone/widget/phone_widget.bin', 'phone/widget/pre_phone_widget.bin')
# 应用图标归 launcher 组管，这里跳过避免重复写同一槽位
PORT_SKIP_TAIL = ('launcher.bin', 'launcher')
print('\n--- 通知/电话/录音机素材（q63 同名移植 -> S5 eSIM）---')
notif_n = 0
for _q, _srcdev in sorted((p, 'app') for p, i in ROM_O['app'].entries()
                          if i.type == 2 and p.startswith(PORT_PREFIXES)):
    if _q in NOTIF_SKIP:
        skipped.append((_q, '按约定保持原厂')); continue
    if _q.rsplit('/', 1)[-1].endswith('launcher.bin'):
        continue                      # 应用图标归 launcher 组管
    dev = 'app'
    ti = find_inode(ROM_N[dev], _q)
    if ti is None:
        ti = find_inode(ROM_N['health'], _q)
        dev = 'health'
    if ti is None:
        skipped.append((_q, '本机没有这个槽位')); continue
    oi = find_inode(ROM_O[_srcdev], _q)
    if oi is None:
        skipped.append((_q, 'q63 没有这个素材')); continue
    tgt_blob = ROM_N[dev].read(ti)
    src_blob = ROM_O[_srcdev].read(oi)
    th, sh = img_header(tgt_blob), img_header(src_blob)
    if th is None or sh is None:
        skipped.append((_q, '头部异常')); continue
    simg = decode_lvgl_bin(src_blob)[1]
    if simg is None:
        skipped.append((_q, 'q63 素材解码失败(cf=0x%02x)' % sh['cf'])); continue
    if (th['flags'] & 0x08) or th['cf'] not in (ip.CF_I8, ip.CF_ARGB8888):
        new, how = ip.encode_into_slot(simg, tgt_blob, ti.size)
        if new is None:
            skipped.append((_q, how)); continue
    else:
        timg = decode_lvgl_bin(tgt_blob)[1]
        if timg is None:
            skipped.append((_q, '本机图解码失败(cf=0x%02x)' % th['cf'])); continue
        out = normalize_fit(simg, ink_bbox(timg), (th['w'], th['h']))
        pal = src_blob[12:12 + 1024] if sh['cf'] == ip.CF_I8 else None
        new = ip.encode(out, th['cf'], th['w'], th['h'], th['flags'], palette=pal)
        how = '归一化 %dx%d->%dx%d' % (sh['w'], sh['h'], th['w'], th['h'])
    if len(new) != ti.size:
        skipped.append((_q, '编码 %d != 槽位 %d' % (len(new), ti.size))); continue
    if new == tgt_blob:
        skipped.append((_q, '两边已经一致')); continue
    name = 'sys:' + _q
    rows[:] = [r for r in rows if r['name'] != name]
    newblobs[name] = new
    stock_of[name] = tgt_blob
    rows.append(dict(name=name, kind='sysicon', path=_q, note='焦点通知', how=how,
                     tag=dev, dev=dev, node='/dev/' + dev, image=_q,
                     offset=ti.data_off, length=ti.size,
                     dim='%dx%d' % (th['w'], th['h']),
                     cf=ip.FMT.get(th['cf'], hex(th['cf'])),
                     stock_ink=ink_bbox(timg) if 'timg' in dir() and timg else None,
                     source_from='q63 ' + _q, identical_to_stock=False,
                     sha256=hashlib.sha256(new).hexdigest(),
                     rb_sha256=hashlib.sha256(tgt_blob).hexdigest()))
    notif_n += 1
    print('  %-46s %s' % (_q, how))
print('  通知/电话/录音机写入 %d 条' % notif_n)


# ------------------------------------------------------------------ payload files
pay = MAGIC_PAY + b''.join(newblobs[r['name']] for r in rows)
rb = MAGIC_RB + b''.join(stock_of[r['name']] for r in rows)

open(os.path.join(WF, 'payload', 'payload.bin'), 'wb').write(pay)
open(os.path.join(WF, 'payload_rollback', 'rollback.bin'), 'wb').write(rb)

def lua_table(recs, var):
    lines = ['-- %s: {设备, 分区内偏移, 长度, payload 文件内相对偏移} —— 由 _tools/s5e_payload.py 生成' % var,
             'local %s = {' % var]
    rel = 0
    for r in recs:
        lines.append('  { "%s", 0x%08x, %d, %d },' % (r['dev'], r['offset'], r['length'], rel))
        rel += len(stock_of[r['name']])
    lines.append('}')
    return '\n'.join(lines) + '\n'

open(os.path.join(WF, 'payload', 'payload.lua'), 'w', encoding='utf-8', newline='\n').write(
    lua_table(rows, 'PAY'))
open(os.path.join(WF, 'payload_rollback', 'rollback.lua'), 'w', encoding='utf-8', newline='\n').write(
    lua_table(rows, 'RB'))

json.dump(dict(target='Xiaomi Watch S5 eSIM 46mm (p62lte) v3.112.035',
               source='Xiaomi Watch S5 41mm (q63) v4.101.020 launcher icons',
               device_nodes={'app': '/dev/app', 'health': '/dev/health'},
               payload_file='payload.bin', payload_magic=MAGIC_PAY.hex(),
               rollback_file='rollback.bin', rollback_magic=MAGIC_RB.hex(),
               count=len(rows), records=rows,
               skipped=[dict(name=n, reason=w) for n, w in skipped]),
          open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

# ------------------------------------------------------------------ patched whole images
for tag, fn, dev in PART:
    srcp = os.path.join(NEW, fn)
    dstp = os.path.join(OUT, fn.replace('.bin', '_os4.bin'))
    shutil.copyfile(srcp, dstp)
    with open(dstp, 'r+b') as f:
        for r in rows:
            if r['tag'] == tag:
                f.seek(r['offset'])
                f.write(newblobs[r['name']])
    a = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in Romfs(srcp).entries()]
    b = [(p, i.off, i.next, i.spec, i.size, i.cksum) for p, i in Romfs(dstp).entries()]
    r1, r2 = Romfs(srcp), Romfs(dstp)
    i1 = {p: i for p, i in r1.entries()}
    i2 = {p: i for p, i in r2.entries()}
    changed = sorted(p for p in i1 if r1.read(i1[p]) != r2.read(i2[p]))

    # 期望变化的文件 = 所有 new != stock 的记录（launcher 图标 + 系统 UI 素材）
    mine = [r for r in rows if r['tag'] == tag and newblobs[r['name']] != stock_of[r['name']]]
    sys_paths = {r['path'] for r in mine if r.get('kind') in ('sysicon', 'walkie')}
    unexpected = [p for p in changed
                  if not (p.rsplit('/', 1)[-1].endswith('launcher.bin') or p in sys_paths)]
    print('\n%s -> %s' % (fn, os.path.basename(dstp)))
    print('  entries %d, inode table identical: %s, superblock identical: %s' % (
        len(a), a == b, (r1.sb_size, r1.sb_cksum) == (r2.sb_size, r2.sb_cksum)))
    print('  changed files: %d  (expected %d)  sha256 %s' % (
        len(changed), len(mine), hashlib.sha256(open(dstp, 'rb').read()).hexdigest()[:16]))
    assert not unexpected, 'unexpected changed file! %s' % unexpected[:3]
    assert len(changed) == len(mine), 'changed %d != expected %d' % (len(changed), len(mine))
    # 端到端：把负载按 (偏移,长度) 放回去，必须与改后镜像逐字节相同
    d = bytearray(open(srcp, 'rb').read())
    for r in rows:
        if r['tag'] == tag:
            d[r['offset']:r['offset'] + r['length']] = newblobs[r['name']]
    assert bytes(d) == open(dstp, 'rb').read(), 'payload replay != patched image'
    print('  payload replay == patched image: True')
    # 回滚也必须能逐字节还原原厂镜像
    e = bytearray(open(dstp, 'rb').read())
    for r in rows:
        if r['tag'] == tag:
            e[r['offset']:r['offset'] + r['length']] = stock_of[r['name']]
    orig = open(srcp, 'rb').read()
    assert bytes(e) == orig, 'rollback replay != stock image'
    print('  rollback replay == stock image: True (sha256 %s)'
          % hashlib.sha256(orig).hexdigest()[:16])

print('\n-> %s' % OUT)
