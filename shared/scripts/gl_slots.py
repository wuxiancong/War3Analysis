"""统计 GL 设备虚表每个槽位函数引用了哪些 gl*/wgl* IAT，用于推断槽位语义。
用法: python gl_slots.py <game.dll> <offsets.json>
"""
import sys, json, struct, pefile, re
pe = pefile.PE(sys.argv[1]); base = pe.OPTIONAL_HEADER.ImageBase
r = json.load(open(sys.argv[2], encoding="utf-8"))
vt = int(r["glvtable"]["base"], 16)
ents = [struct.unpack_from("<I", pe.get_data(vt, 180), i * 4)[0] - base for i in range(45)]
iat = {}
for e in pe.DIRECTORY_ENTRY_IMPORT:
    if e.dll.decode().lower() in ("opengl32.dll", "gdi32.dll", "user32.dll"):
        for i in e.imports:
            if i.name:
                iat[base + i.address - base] = i.name.decode()
text = [s for s in pe.sections if s.Characteristics & 0x20000000][0]
d = text.get_data(); tva = text.VirtualAddress
allfuncs = sorted(set(ents))
for slot, f in enumerate(ents):
    nxt = [x for x in allfuncs if x > f]
    end = min(nxt[0] if nxt else f + 0x400, f + 0x600)
    code = d[f - tva: end - tva]
    names = set()
    for m in re.finditer(b"\xFF[\x15\x25]", code):
        o = m.start()
        v = struct.unpack_from("<I", code, o + 2)[0] if o + 6 <= len(code) else 0
        if v in iat:
            names.add(iat[v])
    print("slot %2d  %X  %s" % (slot, f, ",".join(sorted(names))))
