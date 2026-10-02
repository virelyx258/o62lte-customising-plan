"""Minimal reader for Xiaomi Vela ROMFS partition images (Linux 'rom1fs' variant).

Layout (big-endian):
  super : magic "-rom1fs-", u32 size, u32 checksum, name (NUL-term, padded to 16)
  inode : u32 next (low 4 bits = ROMFH_ type flags), u32 spec, u32 size, u32 checksum,
          name (NUL-term, padded to 16), then file data immediately after.
  type  : 0=hardlink (spec = target inode offset), 1=dir (spec = offset of first child),
          2=regular file, 8=exec bit OR-ed in.
  For a directory, its children are the chain starting at `spec`, linked by
  `next & ~0xF`, and they stay inside the directory's own block.
"""
import struct, os

ROUND16 = lambda n: (n + 15) & ~15

class Inode:
    __slots__ = ('off', 'next', 'spec', 'size', 'cksum', 'name', 'namelen', 'data_off', 'kind')

    @property
    def type_flags(self):
        return self.next & 0xF

    @property
    def type(self):
        return self.next & 0x7

    @property
    def exec_bit(self):
        return bool(self.next & 0x8)

    @property
    def next_off(self):
        return self.next & ~0xF

    KIND = {0: 'HRD', 1: 'DIR', 2: 'REG', 3: 'SYM', 4: 'BLK', 5: 'CHR', 6: 'SCK', 7: 'FIF'}

    def __repr__(self):
        return (f'<Inode @0x{self.off:x} {self.KIND[self.type]}{"X" if self.exec_bit else " "} '
                f'{self.name!r} size={self.size}>')


class Romfs:
    def __init__(self, path):
        self.path = path
        self.data = open(path, 'rb').read()
        d = self.data
        if d[0:8] != b'-rom1fs-':
            raise ValueError('not a romfs image')
        self.sb_size, self.sb_cksum = struct.unpack('>II', d[8:16])
        end = d.index(b'\x00', 16)
        self.volume = d[16:end].decode('latin1')
        self.root_off = 16 + ROUND16(end - 16 + 1)

    def inode(self, off):
        i = Inode()
        i.off = off
        i.next, i.spec, i.size, i.cksum = struct.unpack('>IIII', self.data[off:off+16])
        p = off + 16
        end = self.data.find(b'\x00', p, p + 256)
        if end < 0:
            raise ValueError(f'bad name at 0x{off:x}')
        i.name = self.data[p:end].decode('latin1')
        i.namelen = end - p
        i.data_off = off + 16 + ROUND16(i.namelen + 1)
        return i

    def walk(self, first, limit, prefix=''):
        """Yield (path, Inode) for every entry reachable from `first` below `limit`.

        `limit` bounds the sibling chain.  The LAST entry of a chain has next==0,
        but its own children still live after it: they inherit the parent's limit
        instead of being bounded by that zero.
        """
        off = first
        seen = set()
        while off and (limit == 0 or off < limit) and off not in seen:
            seen.add(off)
            i = self.inode(off)
            path = prefix + i.name
            yield path, i
            if i.type == 1 and i.spec:           # directory -> first child at spec
                yield from self.walk(i.spec, i.next_off or limit, path + '/')
            off = i.next_off

    def entries(self):
        """All entries of the image, as (path, Inode)."""
        return self.walk(self.root_off + 0x20, len(self.data))

    def read(self, ino):
        return self.data[ino.data_off:ino.data_off + ino.size]


def img_header(blob):
    if len(blob) < 12 or blob[0] != 0x19:
        return None
    magic, cf, flags, w, h, stride, res = struct.unpack('<BBHHHHH', blob[:12])
    return dict(magic=magic, cf=cf, flags=flags, w=w, h=h, stride=stride, reserved=res)


if __name__ == '__main__':
    import sys
    r = Romfs(sys.argv[1])
    print(f'{os.path.basename(sys.argv[1])}: volume={r.volume!r} size={r.sb_size} '
          f'file={len(r.data)} root=0x{r.root_off:x}')
    n = 0
    for path, i in r.entries():
        n += 1
        if len(sys.argv) > 2 and sys.argv[2] not in path:
            continue
        kind = ('DIR ' if i.type == 1 else 'LNK ' if i.type == 0 else 'FILE')
        print(f'{kind} {i.size:>9} {path}')
    print(f'-- total entries: {n}')
