"""Print raw code bytes of a PE file around an RVA (no disassembler available on this VM).
Usage: python -I pe_bytes.py game.dll 0x2BD982 [before] [after]
"""
import struct, sys
data = open(sys.argv[1], 'rb').read()
rva = int(sys.argv[2], 16)
before = int(sys.argv[3]) if len(sys.argv) > 3 else 48
after = int(sys.argv[4]) if len(sys.argv) > 4 else 32
pe = struct.unpack_from('<I', data, 0x3C)[0]
nsec = struct.unpack_from('<H', data, pe + 6)[0]
optsz = struct.unpack_from('<H', data, pe + 20)[0]
sec = pe + 24 + optsz
for i in range(nsec):
    name, vsize, va, rawsz, rawptr = struct.unpack_from('<8sIIII', data, sec + i * 40)
    if va <= rva < va + max(vsize, rawsz):
        off = rawptr + (rva - va)
        start = off - before
        print(f'section {name.rstrip(b"\0").decode()} va=0x{va:X} raw=0x{rawptr:X} -> file off 0x{off:X}')
        for j in range(start, off + after, 16):
            line = data[j:j + 16]
            mark = ' <==' if j <= off < j + 16 else ''
            print(f'  rva 0x{rva - (off - j):06X}: ' + ' '.join(f'{b:02X}' for b in line) + mark)
        break
