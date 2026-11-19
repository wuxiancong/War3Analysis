"""From the hook's Ws2_32hook_Send_F726.log (W3GS_OUTGOING_ACTION hex dumps), list every
0x12 targeted order using an inventory slot (useslot 0xD0028..0xD002D), with time and all fields.
Usage: python -I f726_item_orders.py <log> [HH:MM since]
"""
import re, struct, sys
lines = open(sys.argv[1], encoding='utf-8', errors='replace').read().splitlines()
since = sys.argv[2] if len(sys.argv) > 2 else '00:00'
i = 0
while i < len(lines):
    m = re.match(r'\[(\d\d:\d\d:\d\d\.\d+)\] 数据内容\(Hex\):', lines[i])
    if m and m.group(1) >= since:
        hexs = []
        j = i + 1
        while j < len(lines) and re.fullmatch(r'([0-9A-F]{2} ?)+\s*', lines[j]):
            hexs += lines[j].split(); j += 1
        pkt = bytes(int(h, 16) for h in hexs)
        if len(pkt) > 8 and pkt[0] == 0xF7 and pkt[1] == 0x26:
            body = pkt[8:]   # F7 26 len(2) crc(4) then action block
            k = 0
            while True:
                k = body.find(b'\x12', k)
                if k < 0 or k + 31 > len(body): break
                flags, order = struct.unpack_from('<HI', body, k + 1)
                if 0x000D0028 <= order <= 0x000D002D:
                    ua, ub, x, y, o1, o2 = struct.unpack_from('<IIffII', body, k + 7)
                    print(f'{m.group(1)} flags=0x{flags:04X} slot={order - 0x000D0027} unkA=0x{ua:08X} unkB=0x{ub:08X} '
                          f'x={x:.0f} y={y:.0f} obj1=0x{o1:08X} obj2=0x{o2:08X}')
                    print('   full action block:', body.hex(' ').upper())
                k += 1
        i = j
    else:
        i += 1
