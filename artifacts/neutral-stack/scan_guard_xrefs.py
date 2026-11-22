import struct, collections
from pathlib import Path
import pefile

ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\neutral-stack")
OUT.mkdir(parents=True, exist_ok=True)

NAMES = [
    b"GuardDistance\x00",
    b"MaxGuardDistance\x00",
    b"GuardReturnTime\x00",
    b"CreepCampPathingCellDistance\x00",
    b"CreepCallForHelp\x00",
    b"SetUnitCreepGuard\x00",
    b"RemoveGuardPosition\x00",
    b"RecycleGuardPosition\x00",
    b"RemoveAllGuardPositions\x00",
]

VERSIONS = [
    "1.26.0.6401",
    "1.27.0.52240",
    "1.24.4.6387",
    "1.25.1.6397",
    "1.24.1.6374",
    "1.23.0.6352",
    "1.22.0.6328",
    "1.21.0.6263",
    "1.20.4.6074",
]

def file_rva(pe, file_off):
    for s in pe.sections:
        raw, size = s.PointerToRawData, s.SizeOfRawData
        if raw <= file_off < raw + size:
            return s.VirtualAddress + (file_off - raw)
    return None

def rva_to_off(pe, rva):
    return pe.get_offset_from_rva(rva)

def find_cstrs(data, pe, needle):
    hits = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        prev = data[i-1] if i else 0
        if prev == 0 or i == 0:
            rva = file_rva(pe, i)
            if rva is not None:
                hits.append(rva)
        start = i + 1
    return hits

def find_native_reg(data, image_base, str_rva):
    # mov edx, imm32(strVA); mov ecx, imm32(funcVA)  — common 1.26 pattern
    va = image_base + str_rva
    pat = b"\xBA" + struct.pack("<I", va) + b"\xB9"
    funcs = []
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        func_va = struct.unpack_from("<I", data, i + 6)[0]
        funcs.append(func_va - image_base)
        start = i + 1
    # 1.27 sometimes: push imm32; push imm32
    pat2 = b"\x68" + struct.pack("<I", va)
    start = 0
    while True:
        i = data.find(pat2, start)
        if i < 0:
            break
        # look nearby for another push of a code VA
        window = data[max(0,i-32):i+48]
        for j in range(0, len(window)-5):
            if window[j] == 0x68:
                imm = struct.unpack_from("<I", window, j+1)[0]
                if image_base < imm < image_base + 0x1000000 and imm != va:
                    # heuristically prefer .text
                    funcs.append(imm - image_base)
        start = i + 1
    # lea / mov with absolute
    uniq = []
    for f in funcs:
        if f not in uniq and f > 0x1000:
            uniq.append(f)
    return uniq

def find_ptr_xrefs(data, pe, str_rva, image_base):
    """Find dword pointers to the string VA in data sections."""
    va = image_base + str_rva
    needle = struct.pack("<I", va)
    hits = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        rva = file_rva(pe, i)
        if rva is not None:
            hits.append(rva)
        start = i + 1
        if len(hits) > 40:
            break
    return hits

def find_code_imm_xrefs(data, pe, str_rva, image_base):
    va = image_base + str_rva
    needle = struct.pack("<I", va)
    hits = []
    # restrict to executable sections
    exec_ranges = []
    for s in pe.sections:
        if s.Characteristics & 0x20000000:  # IMAGE_SCN_MEM_EXECUTE
            exec_ranges.append((s.PointerToRawData, s.PointerToRawData + s.SizeOfRawData, s.VirtualAddress))
    for raw0, raw1, vabase in exec_ranges:
        chunk = data[raw0:raw1]
        start = 0
        while True:
            i = chunk.find(needle, start)
            if i < 0:
                break
            hits.append(vabase + i)
            start = i + 1
            if len(hits) > 60:
                break
    return hits

lines = []
for ver in VERSIONS:
    dll = ROOT / ver / "game.dll"
    if not dll.exists():
        lines.append(f"## {ver}: MISSING")
        continue
    pe = pefile.PE(str(dll), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']])
    data = dll.read_bytes()
    image_base = pe.OPTIONAL_HEADER.ImageBase
    lines.append(f"## {ver}  ImageBase=0x{image_base:X}  size={len(data)}")
    for name in NAMES:
        str_rvas = find_cstrs(data, pe, name)
        nice = name[:-1].decode()
        lines.append(f"### {nice}")
        if not str_rvas:
            lines.append("  string: not found")
            continue
        for sr in str_rvas:
            lines.append(f"  string RVA: 0x{sr:X}")
            regs = find_native_reg(data, image_base, sr)
            if regs:
                lines.append("  native-reg candidates: " + ", ".join(f"0x{x:X}" for x in regs[:8]))
            ptrs = find_ptr_xrefs(data, pe, sr, image_base)
            if ptrs:
                lines.append("  data ptrs: " + ", ".join(f"0x{x:X}" for x in ptrs[:12]))
            code = find_code_imm_xrefs(data, pe, sr, image_base)
            if code:
                lines.append("  code imm: " + ", ".join(f"0x{x:X}" for x in code[:16]))
    lines.append("")

out = OUT / "guard_string_xrefs.md"
out.write_text("\n".join(lines), encoding="utf-8")
print(out)
print("\n".join(lines[:80]))
