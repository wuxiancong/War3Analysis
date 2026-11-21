#!/usr/bin/env python3
"""Confirm structure signatures across versions and read a live match (read-only)."""
import struct
import ctypes
from ctypes import wintypes
from pathlib import Path

import capstone
import pefile

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-movement")
ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")

SIGS = {
    "fly_eax_208": b"\x8B\x80\x08\x02\x00\x00",          # mov eax,[eax+208h]
    "lea_ecx_164_ret": b"\x8D\x81\x64\x01\x00\x00\xC3",  # lea eax,[ecx+164h]; ret
    "order_pair_19c": b"\x8B\x86\x9C\x01\x00\x00",       # mov eax,[esi+19Ch]
    "order_id_24": b"\x8B\x40\x24",                      # mov eax,[eax+24h] too common, skip count only if wanted
    "type_30_ret": b"\x8B\x40\x30\xC3",                  # mov eax,[eax+30h]; ret
    "amov_1ec": b"\x8B\x89\xEC\x01\x00\x00",             # mov ecx,[ecx+1ECh]
}


def main_sigs():
    lines = ["version\t" + "\t".join(SIGS)]
    for ver in sorted(p for p in ROOT.iterdir() if p.is_dir()):
        dlls = list(ver.glob("game.dll")) + list(ver.glob("Game.dll"))
        if not dlls:
            continue
        data = dlls[0].read_bytes()
        counts = []
        for sig in SIGS.values():
            c = data.count(sig)
            counts.append(str(c))
        lines.append(ver.name + "\t" + "\t".join(counts))
        print(ver.name, " ".join(f"{n}={c}" for n, c in zip(SIGS, counts)))
    (OUT / "offset-sigs.tsv").write_text("\n".join(lines), encoding="utf-8")


def dis_order():
    path = r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll"
    data = Path(path).read_bytes()
    pe = pefile.PE(path, fast_load=True)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    parts = ["# order ctor and lookup tail\n"]
    for name, rva, n in (("ctor", 0x286E80, 50), ("lookup_tail", 0x3FA80, 25)):
        off = pe.get_offset_from_rva(rva)
        lines = []
        for ins in md.disasm(data[off : off + 0x120], rva):
            lines.append("%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
            if len(lines) >= n:
                break
        parts.append("## %s\n```\n%s\n```\n" % (name, "\n".join(lines)))
    # ucol context
    idx = data.find(b"locu")  # 'ucol' as LE fourcc bytes? 'ucol' LE is 6c 6f 63 75 = locu
    parts.append("ucol idx 0x%X\n" % idx)
    if idx >= 0:
        chunk = data[idx - 16 : idx + 48]
        parts.append(chunk.hex() + "\n")
        # nearby dwords
        base = idx - (idx % 4)
        dwords = struct.unpack_from("<8I", data, idx - 8)
        parts.append("dwords " + " ".join(hex(d) for d in dwords) + "\n")
    (OUT / "order-ctor.md").write_text("".join(parts), encoding="utf-8")
    pe.close()


# ---- live ----
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
MEM_COMMIT = 0x1000
PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", ctypes.c_char * 256),
        ("szExePath", ctypes.c_char * 260),
    ]


class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


def find_pid():
    # fixed from the process list; re-resolve by name
    import subprocess
    out = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process war3 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Id)"],
        text=True,
    ).strip()
    return int(out) if out else 0


def modules(pid):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == ctypes.c_void_p(-1).value or snap == -1:
        raise OSError("snapshot failed %s" % ctypes.get_last_error())
    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(MODULEENTRY32)
    out = []
    ok = kernel32.Module32First(snap, ctypes.byref(me))
    while ok:
        out.append((me.szModule.decode("latin1", "replace"),
                    ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value,
                    me.modBaseSize,
                    me.szExePath.decode("latin1", "replace")))
        ok = kernel32.Module32Next(snap, ctypes.byref(me))
    kernel32.CloseHandle(snap)
    return out


def read(h, addr, n):
    buf = (ctypes.c_char * n)()
    got = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)):
        return None
    return bytes(buf[: got.value])


def u32(b, o=0):
    return struct.unpack_from("<I", b, o)[0]


def f32(b, o=0):
    return struct.unpack_from("<f", b, o)[0]


def live():
    pid = find_pid()
    print("pid", pid)
    if not pid:
        return
    h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not h:
        print("OpenProcess failed", ctypes.get_last_error())
        return
    mods = modules(pid)
    game = [m for m in mods if m[0].lower() == "game.dll"]
    print("game", game)
    if not game:
        kernel32.CloseHandle(h)
        return
    name, base, size, path = game[0]
    # identify version by fly-height signature inside the loaded image (read first 2MB of .text is heavy).
    # Compare file size / a few RVAs by reading the on-disk path if readable.
    print("path", path, "base", hex(base), "size", hex(size))
    # read DOS header to confirm
    hdr = read(h, base, 64)
    print("mz", hdr[:2] if hdr else None)

    # Candidate CUnit vtable RVAs
    candidates = {
        "1.26": 0x931934,
        "1.27": 0xA4A704,
        "1.24.4": None,
    }
    # We'll scan for type ids near a vtable pointer. First try reading vtable from base+rva and see if it points into game.dll
    lines = []
    for ver, rva in (("1.26", 0x931934), ("1.27", 0xA4A704), ("1.24.4", 0x9319B4)):
        vt = base + rva
        slot = read(h, vt, 4)
        if not slot:
            lines.append("%s vt 0x%X unreadable" % (ver, vt))
            continue
        fn = u32(slot)
        lines.append("%s vt 0x%X slot0 0x%X in_mod=%s" % (ver, vt, fn, base <= fn < base + size))
    print("\n".join(lines))

    # Pick the vtable whose slot0 is inside the module. Prefer 1.26 then 1.27.
    chosen = None
    for ver, rva in (("1.26", 0x931934), ("1.27", 0xA4A704)):
        slot = read(h, base + rva, 8)
        if not slot:
            continue
        fn = u32(slot)
        b8 = u32(slot) if False else None
        # read slot +0xB8
        sb = read(h, base + rva + 0xB8, 4)
        if not sb:
            continue
        fnb = u32(sb)
        if base <= fn < base + size and base <= fnb < base + size:
            # confirm lea [ecx+164]
            code = read(h, fnb, 7)
            lines.append("check %s +B8 bytes %s" % (ver, code.hex() if code else None))
            if code == b"\x8D\x81\x64\x01\x00\x00\xC3":
                chosen = (ver, base + rva)
                break
    print("CHOSEN", chosen)
    if not chosen:
        (OUT / "live-scan.txt").write_text("\n".join(lines), encoding="utf-8")
        kernel32.CloseHandle(h)
        return
    ver, vt = chosen
    # scan committed memory for the vtable dword
    pat = struct.pack("<I", vt)
    types = {
        0x6573656E: "esen",
        0x65647279: "edry",
        0x6562616C: "ebal",
        0x486A6169: "Hjai",
    }
    found = {k: [] for k in types}
    mbi = MBI()
    addr = 0
    scanned = 0
    regions = 0
    while addr < 0x80000000:
        if kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)) == 0:
            break
        base_a = mbi.BaseAddress or 0
        size_a = mbi.RegionSize or 0
        if size_a == 0:
            break
        prot = mbi.Protect or 0
        if mbi.State == MEM_COMMIT and not (prot & PAGE_GUARD) and prot not in (PAGE_NOACCESS, 0) and size_a <= 32 * 1024 * 1024:
            regions += 1
            # read in chunks
            off = 0
            while off < size_a:
                chunk = min(1024 * 1024, size_a - off)
                buf = read(h, base_a + off, chunk)
                if buf:
                    scanned += len(buf)
                    start = 0
                    while True:
                        i = buf.find(pat, start)
                        if i < 0:
                            break
                        start = i + 4
                        unit = base_a + off + i
                        # type at +0x30
                        tb = read(h, unit + 0x30, 4)
                        if not tb:
                            continue
                        tid = u32(tb)
                        if tid in types and len(found[tid]) < 4:
                            found[tid].append(unit)
                off += chunk
        addr = base_a + size_a
        if addr <= base_a:
            break
    print("scanned", scanned, "regions", regions)
    report = ["version_guess " + ver, "vtable " + hex(vt), "scanned %d" % scanned]
    # sample each
    import time
    samples = []
    for tid, name in types.items():
        for unit in found[tid][:3]:
            blob = read(h, unit, 0x320)
            if not blob or len(blob) < 0x320:
                report.append("%s 0x%X short" % (name, unit))
                continue
            samples.append((name, unit, blob))
            report.append("UNIT %s 0x%X type 0x%X id %08X %08X" % (
                name, unit, u32(blob, 0x30), u32(blob, 0x0C), u32(blob, 0x10)))
    # second sample after 250ms for the first of each type
    time.sleep(0.25)
    for name, unit, blob in samples:
        blob2 = read(h, unit, 0x320)
        if not blob2:
            continue
        report.append("--- %s 0x%X" % (name, unit))
        report.append("fly208 %.3f -> %.3f" % (f32(blob, 0x208), f32(blob2, 0x208)))
        report.append("f2cc %.3f" % f32(blob, 0x2CC))
        report.append("flags5c 0x%X" % u32(blob, 0x5C))
        # order pair
        report.append("order %08X %08X" % (u32(blob, 0x19C), u32(blob, 0x1A0)))
        amov = u32(blob, 0x1EC)
        report.append("amov 0x%X" % amov)
        if amov:
            ab = read(h, amov, 0x90)
            if ab:
                report.append("amov70 %.3f amov78 %.3f amov7c 0x%X" % (f32(ab, 0x70), f32(ab, 0x78), u32(ab, 0x7C)))
        # pos ids
        id1, id2 = u32(blob, 0x16C), u32(blob, 0x170)
        report.append("posId %08X %08X" % (id1, id2))
        # try agent table 1.26 global RVA 0xAB7788
        if ver == "1.26":
            g = read(h, base + 0xAB7788, 4)
            if g:
                table = u32(g)
                report.append("agentTable 0x%X" % table)
                node = lookup_agent(h, table, id1, id2)
                report.append("node %s" % (hex(node) if node else None))
                if node:
                    nb = read(h, node, 0xC0)
                    if nb:
                        report.append("node70 %.2f %.2f %.2f %.2f %.2f %.2f face %.4f turn %.3f" % (
                            f32(nb, 0x70), f32(nb, 0x74), f32(nb, 0x78), f32(nb, 0x7C),
                            f32(nb, 0x80), f32(nb, 0x84), f32(nb, 0x90), f32(nb, 0xB8)))
                        nb2 = None
        # order object via resolve is hard; dump nearby floats of order if we can lookup
        if ver == "1.26":
            g = read(h, base + 0xAB7788, 4)
            if g:
                table = u32(g)
                on = lookup_agent(h, table, u32(blob, 0x19C), u32(blob, 0x1A0))
                report.append("orderNode %s" % (hex(on) if on else None))
                if on:
                    ob = read(h, on, 0x60)
                    if ob:
                        obj = u32(ob, 0x54)
                        report.append("orderObj 0x%X" % obj)
                        if obj:
                            od = read(h, obj, 0x80)
                            if od:
                                report.append("order+24 0x%X" % u32(od, 0x24))
                                floats = []
                                for off in range(0x20, 0x70, 4):
                                    floats.append("+%X=%.2f/%08X" % (off, f32(od, off), u32(od, off)))
                                report.append(" ".join(floats))
    text = "\n".join(report)
    (OUT / "live-scan.txt").write_text(text, encoding="utf-8")
    print(text)
    kernel32.CloseHandle(h)


def lookup_agent(h, table, id1, id2):
    """1.26 AgentLookup 0x3FA30. table is CAgentTable*."""
    if not table or id1 == 0xFFFFFFFF:
        return 0
    hdr = read(h, table, 0x40)
    if not hdr or len(hdr) < 0x40:
        return 0
    high = (id1 >> 31) & 1
    if high == 0:
        limit = u32(hdr, 0x1C)
        if id1 >= limit:
            return 0
        arr = u32(hdr, 0x0C)
        slot = read(h, arr + id1 * 8, 8)
        if not slot:
            return 0
        if u32(slot, 0) != 0xFFFFFFFE:
            return 0
        # low path continues at 0x3FA8A — read node from slot+4 and check +0x18
        node = u32(slot, 4)
    else:
        idx = id1 & 0x7FFFFFFF
        limit = u32(hdr, 0x3C)
        if idx >= limit:
            return 0
        arr = u32(hdr, 0x2C)
        slot = read(h, arr + idx * 8, 8)
        if not slot:
            return 0
        if u32(slot, 0) != 0xFFFFFFFE:
            return 0
        node = u32(slot, 4)
    if not node:
        return 0
    nb = read(h, node + 0x18, 4)
    if not nb or u32(nb) != id2:
        return 0
    return node


if __name__ == "__main__":
    main_sigs()
    dis_order()
    live()
