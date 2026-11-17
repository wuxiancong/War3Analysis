"""Minimal read-only MPQ (v1) reader: hash/block tables, encrypted files, zlib/bzip2 sectors.
Usage: python -I mpqread.py <archive.mpq> <out_dir> <file1> [file2 ...]
"""
import struct, sys, zlib, bz2, os

def _crypt_table():
    t = [0] * 0x500
    seed = 0x00100001
    for i in range(0x100):
        idx = i
        for _ in range(5):
            seed = (seed * 125 + 3) % 0x2AAAAB
            a = (seed & 0xFFFF) << 16
            seed = (seed * 125 + 3) % 0x2AAAAB
            t[idx] = a | (seed & 0xFFFF)
            idx += 0x100
    return t

CT = _crypt_table()

def hs(s, kind):
    s1, s2 = 0x7FED7FED, 0xEEEEEEEE
    for ch in s.upper().encode('latin-1'):
        s1 = (CT[kind * 0x100 + ch] ^ (s1 + s2)) & 0xFFFFFFFF
        s2 = (ch + s1 + s2 + (s2 << 5) + 3) & 0xFFFFFFFF
    return s1

def decrypt(data, key):
    out = bytearray()
    seed = 0xEEEEEEEE
    for i in range(len(data) // 4):
        seed = (seed + CT[0x400 + (key & 0xFF)]) & 0xFFFFFFFF
        v = struct.unpack_from('<I', data, i * 4)[0]
        v = (v ^ (key + seed)) & 0xFFFFFFFF
        key = ((((~key) << 21) + 0x11111111) | (key >> 11)) & 0xFFFFFFFF
        seed = (v + seed + (seed << 5) + 3) & 0xFFFFFFFF
        out += struct.pack('<I', v)
    out += data[len(data) // 4 * 4:]
    return bytes(out)

class Mpq:
    def __init__(self, path):
        self.f = open(path, 'rb')
        d = self.f.read()
        self.d = d
        off = 0
        while True:
            off = d.find(b'MPQ\x1a', off)
            if off < 0: raise ValueError('no MPQ header')
            hdr = struct.unpack_from('<4sIIHHIIII', d, off)
            if hdr[3] in (0, 1) or True:
                break
        self.base = off
        _, hsize, asize, ver, sshift, htpos, btpos, htcount, btcount = hdr
        self.sector = 512 << sshift
        ht = decrypt(d[off + htpos: off + htpos + htcount * 16], hs('(hash table)', 3))
        bt = decrypt(d[off + btpos: off + btpos + btcount * 16], hs('(block table)', 3))
        self.ht = [struct.unpack_from('<IIHHI', ht, i * 16) for i in range(htcount)]
        self.bt = [struct.unpack_from('<IIII', bt, i * 16) for i in range(btcount)]

    def find(self, name):
        n = len(self.ht)
        i = hs(name, 0) % n
        a, b = hs(name, 1), hs(name, 2)
        for _ in range(n):
            e = self.ht[i]
            if e[4] == 0xFFFFFFFF: return None
            if e[0] == a and e[1] == b and e[4] != 0xFFFFFFFE: return self.bt[e[4]]
            i = (i + 1) % n
        return None

    def read(self, name):
        blk = self.find(name)
        if not blk: return None
        pos, csize, fsize, flags = blk
        if not (flags & 0x80000000): return None
        raw = self.d[self.base + pos: self.base + pos + csize]
        key = 0
        if flags & 0x00010000:
            key = hs(name.replace('/', '\\').split('\\')[-1], 3)
            if flags & 0x00020000: key = ((key + pos) ^ fsize) & 0xFFFFFFFF
        if flags & 0x01000000:  # single unit
            data = decrypt(raw, key) if key else raw
            return self._decomp(data, fsize, flags)
        if not (flags & 0x00000300):
            return decrypt(raw, key) if key else raw
        nsec = (fsize + self.sector - 1) // self.sector
        tbl = raw[:(nsec + 1) * 4]
        if key: tbl = decrypt(tbl, (key - 1) & 0xFFFFFFFF)
        offs = struct.unpack('<%dI' % (nsec + 1), tbl)
        out = bytearray()
        for i in range(nsec):
            chunk = raw[offs[i]:offs[i + 1]]
            if key: chunk = decrypt(chunk, (key + i) & 0xFFFFFFFF)
            want = min(self.sector, fsize - i * self.sector)
            out += self._decomp(chunk, want, flags)
        return bytes(out)

    @staticmethod
    def _decomp(chunk, want, flags):
        if len(chunk) >= want: return chunk[:want]
        if flags & 0x00000200:
            m = chunk[0]; body = chunk[1:]
            if m & 0x10: body = bz2.decompress(body)
            if m & 0x02: body = zlib.decompress(body)
            if m & 0x08: raise NotImplementedError('pkware implode')
            return body
        raise NotImplementedError('implode (0x100)')

if __name__ == '__main__':
    mpq = Mpq(sys.argv[1])
    os.makedirs(sys.argv[2], exist_ok=True)
    for name in sys.argv[3:]:
        try:
            data = mpq.read(name)
        except Exception as e:
            print('ERR', name, e); continue
        if data is None:
            print('MISS', name); continue
        out = os.path.join(sys.argv[2], name.replace('\\', '_'))
        open(out, 'wb').write(data)
        print('OK', name, len(data))
