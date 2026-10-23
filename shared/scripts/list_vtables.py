"""列出 .rdata 中长度 >= N 的函数指针表。用法: python list_vtables.py <game.dll> [最小槽位数]"""
import sys, struct, pefile
pe = pefile.PE(sys.argv[1]); base = pe.OPTIONAL_HEADER.ImageBase
mn = int(sys.argv[2]) if len(sys.argv) > 2 else 40
text = [(s.VirtualAddress, s.VirtualAddress + len(s.get_data())) for s in pe.sections if s.Characteristics & 0x20000000]
ok = lambda v: any(a <= v - base < b for a, b in text)
for s in pe.sections:
    if s.Characteristics & 0x20000000: continue
    d = s.get_data(); i = 0
    while i + 4 <= len(d):
        if ok(struct.unpack_from("<I", d, i)[0]):
            j = i
            while j + 4 <= len(d) and ok(struct.unpack_from("<I", d, j)[0]): j += 4
            n = (j - i) // 4
            if n >= mn:
                print("%s:%X 槽位=%d 首项=%X 末项=%X" % (s.Name.rstrip(b"\0").decode(), s.VirtualAddress + i, n, struct.unpack_from("<I", d, i)[0] - base, struct.unpack_from("<I", d, j - 4)[0] - base))
            i = j
        else:
            i += 4
