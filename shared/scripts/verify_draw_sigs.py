"""Cross-era first-hit check and GL reset API confirmation."""
import os
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = r"D:\Qt\workspace\War3Launcher\versions"
VERS = [
    "1.0.17.5988", "1.0.20.6048", "1.20.4.6074", "1.21.0.6263",
    "1.22.0.6328", "1.23.0.6352", "1.24.1.6374", "1.24.4.6387",
    "1.25.1.6397", "1.26.0.6401", "1.27.0.52240",
]
END = {
    "1.0.17.5988": 0x0D5BD0, "1.0.20.6048": 0x0D5BD0, "1.20.4.6074": 0x0D5BD0,
    "1.21.0.6263": 0x0D5BD0, "1.22.0.6328": 0x5235E0, "1.23.0.6352": 0x525370,
    "1.24.1.6374": 0x533D00, "1.24.4.6387": 0x533D80, "1.25.1.6397": 0x533050,
    "1.26.0.6401": 0x533280, "1.27.0.52240": 0x0F0CC0,
}
RESET = {
    "1.0.17.5988": 0x0CBED0, "1.0.20.6048": 0x0CBED0, "1.20.4.6074": 0x0CBED0,
    "1.21.0.6263": 0x0CBED0, "1.22.0.6328": 0x51AC70, "1.23.0.6352": 0x51CA00,
    "1.24.1.6374": 0x52B390, "1.24.4.6387": 0x52B410, "1.25.1.6397": 0x52A6E0,
    "1.26.0.6401": 0x52A910, "1.27.0.52240": 0x0E7670,
}
REL = {
    "1.0.17.5988": 0x0D0611, "1.0.20.6048": 0x0D0611, "1.20.4.6074": 0x0D0611,
    "1.21.0.6263": 0x0D0611, "1.22.0.6328": 0x51D451, "1.23.0.6352": 0x51F1E1,
    "1.24.1.6374": 0x52DB71, "1.24.4.6387": 0x52DBF1, "1.25.1.6397": 0x52CEC1,
    "1.26.0.6401": 0x52D0F1, "1.27.0.52240": 0x0EC510,
}
SIGS = {
    "rel": [
        "8B 86 84 05 00 00 85 C0 74 ?? 8B 10 50 FF 52 08 C7 86 84 05 00 00 00 00 00 00",
        "8B 86 84 05 00 00 85 C0 74 ?? 8B 10 50 8B 42 08 FF D0 C7 86 84 05 00 00 00 00 00 00",
        "8B 8E 84 05 00 00 85 C9 74 ?? 8B 01 51 FF 50 08 C7 86 84 05 00 00 00 00 00 00",
    ],
    "end": [
        "55 8B EC 83 EC 0C 53 56 8B 75 08 57 8B D9 8B BB 60 05 00 00",
        "83 EC 08 53 55 56 57 8B 7C 24 1C 8B F1",
        "55 8B EC 83 EC 08 53 8B 5D 08 56 57 8B F9 53 8B 87 60 05 00 00",
    ],
    "reset": [
        "55 8B EC 83 EC 18 53 56 8B D9 57 8D B3 94 00 00 00 B9 06 00 00 00 8D 7D E8 F3 A5 8B CB E8 ?? ?? ?? ?? 8B 75 08",
        "83 EC 18 56 8B F1 8B 8E 98 00 00 00 8B 86 94 00 00 00 8B 96 9C 00 00 00 89 4C 24 08 8B 8E A4 00 00 00 89 44 24 04 8B 86 A0 00 00 00 89 54 24 0C 8B 96 A8 00 00 00 89 4C 24 14 57 8B CE 89 44 24 14 89 54 24 1C E8 ?? ?? ?? ?? 8B 7C 24 24",
        "55 8B EC 83 EC 1C A1 ?? ?? ?? ?? 33 C5 89 45 FC 53 56 8B 75 08 57",
    ],
}
EXPECT = {"rel": REL, "end": END, "reset": RESET}
MD = Cs(CS_ARCH_X86, CS_MODE_32)


def parse(s):
    return [None if t == "??" else int(t, 16) for t in s.split()]


def first_hit(img, sig):
    n = len(sig)
    anchor = next(i for i, b in enumerate(sig) if b is not None)
    pos = 0
    needle = bytes([sig[anchor]])
    count = 0
    first = None
    while True:
        j = img.find(needle, pos)
        if j < 0:
            break
        p = j - anchor
        pos = j + 1
        if p < 0 or p + n > len(img):
            continue
        if all(b is None or img[p + k] == b for k, b in enumerate(sig)):
            count += 1
            if first is None:
                first = p
            if count > 4:
                break
    return first, count


def load(ver):
    pe = pefile.PE(os.path.join(ROOT, ver, "game.dll"))
    img = bytearray(pe.OPTIONAL_HEADER.SizeOfImage)
    base = pe.OPTIONAL_HEADER.ImageBase
    iat = {}
    for s in pe.sections:
        d = s.get_data()
        img[s.VirtualAddress:s.VirtualAddress + len(d)] = d
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for e in pe.DIRECTORY_ENTRY_IMPORT:
            for i in e.imports:
                if i.name and i.name.decode() in (
                    "ChangeDisplaySettingsA", "ChangeDisplaySettingsExA", "wglSwapLayerBuffers", "wglDeleteContext"
                ):
                    iat[i.name.decode()] = i.address
    return img, base, iat


def main():
    images = {}
    for ver in VERS:
        print("load", ver, flush=True)
        images[ver] = load(ver)
    print("\n== first alternative hit ==")
    for kind, sigs in SIGS.items():
        for ver, (img, base, iat) in images.items():
            found = []
            for i, s in enumerate(sigs):
                hit, n = first_hit(img, parse(s))
                if hit is not None:
                    found.append((i, hit, n))
            expect = EXPECT[kind][ver]
            ok = bool(found) and found[0][1] == expect
            print(f"{kind:5} {ver:16} expect {expect:#x} first {found} {'OK' if ok else 'BAD'}")

    print("\n== reset API ==")
    for ver, (img, base, iat) in images.items():
        rva = RESET[ver]
        # direct FF 15 of either import inside 0x1200
        direct = []
        for name, va in iat.items():
            if not name.startswith("Change"):
                continue
            pat = b"\xFF\x15" + va.to_bytes(4, "little")
            blob = bytes(img[rva:rva + 0x1200])
            j = blob.find(pat)
            if j >= 0:
                direct.append((name, hex(rva + j)))
        # one-level E8 callees
        indirect = []
        code = bytes(img[rva:rva + 0x400])
        for ins in MD.disasm(code, rva):
            if ins.mnemonic == "ret":
                break
            if ins.bytes[0] == 0xE8 and len(ins.bytes) == 5:
                rel = int.from_bytes(ins.bytes[1:], "little", signed=True)
                tgt = ins.address + 5 + rel
                if not (0 < tgt < len(img) - 0x300):
                    continue
                sub = bytes(img[tgt:tgt + 0x300])
                for name, va in iat.items():
                    if not name.startswith("Change"):
                        continue
                    pat = b"\xFF\x15" + va.to_bytes(4, "little")
                    if pat in sub:
                        indirect.append((hex(ins.address), hex(tgt), name))
        print(ver, "direct", direct, "via", indirect[:4], "iat", {k: hex(v) for k, v in iat.items() if k.startswith("Change")})


if __name__ == "__main__":
    main()
