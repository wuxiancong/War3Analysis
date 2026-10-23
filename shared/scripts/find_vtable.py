"""在 game.dll 数据段中查找包含指定 RVA 函数指针的虚表，并打印整张表（连续指向 .text 的 dword）。
用法: python find_vtable.py <game.dll> <hexRVA> [...]
"""
import sys, struct, pefile

pe = pefile.PE(sys.argv[1])
base = pe.OPTIONAL_HEADER.ImageBase
text = [(s.VirtualAddress, s.VirtualAddress + len(s.get_data())) for s in pe.sections if s.Characteristics & 0x20000000]

def in_text(v):
    return any(a <= v - base < b for a, b in text)

for arg in sys.argv[2:]:
    rva = int(arg, 16)
    pat = struct.pack("<I", base + rva)
    for s in pe.sections:
        if s.Characteristics & 0x20000000:
            continue
        d = s.get_data()
        i = -1
        while True:
            i = d.find(pat, i + 1)
            if i < 0:
                break
            if i % 4:
                continue
            lo = i
            while lo >= 4 and in_text(struct.unpack_from("<I", d, lo - 4)[0]):
                lo -= 4
            hi = i
            while hi + 4 <= len(d) - 4 and in_text(struct.unpack_from("<I", d, hi + 4)[0]):
                hi += 4
            print("func %X 在 %s:%X ; 虚表范围 %X..%X, 槽位 %d/%d" % (rva, s.Name.rstrip(b"\0").decode(), s.VirtualAddress + i, s.VirtualAddress + lo, s.VirtualAddress + hi, (i - lo) // 4, (hi - lo) // 4 + 1))
            print("  表起点RVA=%X" % (s.VirtualAddress + lo))
            for k in range(lo, hi + 4, 4):
                print("   [%3d] +0x%03X -> %X" % ((k - lo) // 4, k - lo, struct.unpack_from("<I", d, k)[0] - base))
