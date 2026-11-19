"""Extract 0x12 (targeted order) actions that use an inventory slot (useslot 0xD0028..0xD002D)
from a War3 .w3g replay, to compare a human's item-on-tree order with the AI's.
Usage: python -I w3g_item_orders.py LastReplay.w3g
"""
import struct, sys, zlib

raw = open(sys.argv[1], 'rb').read()
hdr_size, comp_size, hdr_ver, decomp_size, nblocks = struct.unpack_from('<IIIII', raw, 0x1C)
pos = hdr_size
out = bytearray()
for _ in range(nblocks):
    # 经典 War3（含 1.27）的块头都是 8 字节：压缩长 u16、解压长 u16、校验 u32（12 字节块头是重制版格式）
    csize, dsize, _chk = struct.unpack_from('<HHI', raw, pos); pos += 8
    chunk = raw[pos:pos + csize]; pos += csize
    try:
        out += zlib.decompress(chunk)[:dsize]
    except zlib.error:
        out += zlib.decompressobj().decompress(chunk)[:dsize]
data = bytes(out)
print(f'header ver {hdr_ver}, blocks {nblocks}, decompressed {len(data)} bytes')

# Scan for 0x12 + flags(2) + order(4) where order is useslot1..6
hits = 0
i = 0
while True:
    i = data.find(b'\x12', i)
    if i < 0 or i + 31 > len(data):
        break
    flags, order = struct.unpack_from('<HI', data, i + 1)
    if 0x000D0028 <= order <= 0x000D002D:
        ua, ub, x, y, o1, o2 = struct.unpack_from('<IIffII', data, i + 7)
        print(f'@{i:8d} flags=0x{flags:04X} order=0x{order:08X} (slot {order - 0x000D0027}) '
              f'unkA=0x{ua:08X} unkB=0x{ub:08X} x={x:.0f} y={y:.0f} obj1=0x{o1:08X} obj2=0x{o2:08X}')
        print('          bytes:', data[i:i + 31].hex(' ').upper())
        hits += 1
    i += 1
print('hits:', hits)
