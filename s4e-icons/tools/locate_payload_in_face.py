"""在编好的 .face 里定位每一份负载，好让 Lua 运行时按偏移从 resource.bin 里读出来
（设备不会把 .face 里的 images/ 解包到文件系统，图片仍然躺在 resource.bin 里）。
"""
import os, sys, json
from paths import PROJ, WORK

FACE = os.path.join(WORK, 'build', 'S5Icons', 'bin', 'S5Icons.face')
PDIR = os.path.join(PROJ, 'payload')
RDIR = os.path.join(PROJ, 'payload_rollback')
OUT = os.path.join(WORK, 'face_payload_offsets.json')

face = open(FACE, 'rb').read()
print(f'face {os.path.basename(FACE)}  {len(face)} bytes')

anchor = face.find(b'local lvgl = require("lvgl")')
print(f'lua source starts at 0x{anchor:x} ({anchor})')

out = {}
for tag, d in (('payload', PDIR), ('rollback', RDIR)):
    recs = []
    dup = 0
    for name in sorted(os.listdir(d)):
        if not name.endswith('.bin') or name.endswith('payload.lua'):
            continue
        data = open(os.path.join(d, name), 'rb').read()
        if not data:
            continue
        hits, start = [], 0
        while True:
            i = face.find(data, start)
            if i < 0:
                break
            hits.append(i)
            start = i + 1
            if len(hits) > 8:
                break
        recs.append((name, len(data), hits, data[:16].hex()))
        if len(hits) != 1:
            dup += 1
    out[tag] = recs
    print(f'\n{tag}: {len(recs)} files, {dup} with !=1 occurrence')
    for name, ln, hits, sig in recs[:6]:
        print(f'   {name:<34} {ln:>7}  hits={[hex(h) for h in hits]}')
    if recs:
        print('   ...')

json.dump({k: [(n, l, h, s) for n, l, h, s in v] for k, v in out.items()},
          open(OUT, 'w', encoding='utf-8'), indent=1)
print('\nsaved', OUT)
