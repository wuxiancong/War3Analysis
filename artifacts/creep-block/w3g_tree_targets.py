"""List every 0x12 targeted order in a .w3g whose target looks like a map-placed object
(obj1 == obj2, small id), with order id and flags — finds how the game encodes item/ability use on trees.
Usage: python -I w3g_tree_targets.py LastReplay.w3g
"""
import struct, sys, zlib, collections

raw = open(sys.argv[1], 'rb').read()
hdr_size, comp_size, hdr_ver, decomp_size, nblocks = struct.unpack_from('<IIIII', raw, 0x1C)
pos = hdr_size; out = bytearray()
for _ in range(nblocks):
    csize, dsize, _chk = struct.unpack_from('<HHI', raw, pos); pos += 8
    out += zlib.decompressobj().decompress(raw[pos:pos + csize])[:dsize]; pos += csize   # 块不一定以 Z_FINISH 结束
data = bytes(out)

orders = collections.Counter()
i = 0
while True:
    i = data.find(b'\x12', i)
    if i < 0 or i + 31 > len(data): break
    flags, order, ua, ub, x, y, o1, o2 = struct.unpack_from('<HIIIffII', data, i + 1)
    plausible = (abs(x) < 9000 and abs(y) < 9000 and ua == 0xFFFFFFFF and ub == 0xFFFFFFFF
                 and (order >> 16) in (0x000D, 0x0000) or (order & 0xFF000000) == 0x41000000)
    if plausible and o1 == o2 and 0 < o1 < 0x10000:
        orders[(flags, order)] += 1
        print(f'@{i:8d} flags=0x{flags:04X} order=0x{order:08X} x={x:.0f} y={y:.0f} obj=0x{o1:04X}')
    i += 1
print('summary:', {f'flags=0x{f:04X} order=0x{o:08X}': n for (f, o), n in orders.items()})
