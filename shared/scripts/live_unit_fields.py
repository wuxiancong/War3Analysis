#!/usr/bin/env python3
"""Re-read live 1.27 units: position node, order, collision-like floats. Read-only."""
import struct
import ctypes
import time
from ctypes import wintypes
from pathlib import Path

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-movement\live-fields.txt")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
TH32CS_SNAPMODULE = 0x8
TH32CS_SNAPMODULE32 = 0x10

class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE),
        ("szModule", ctypes.c_char * 256), ("szExePath", ctypes.c_char * 260),
    ]

class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD), ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD), ("Protect", wintypes.DWORD), ("Type", wintypes.DWORD),
    ]

def pid():
    import subprocess
    out = subprocess.check_output(["powershell","-NoProfile","-Command",
        "(Get-Process war3 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Id)"], text=True).strip()
    return int(out) if out else 0

def modules(p):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, p)
    me = MODULEENTRY32(); me.dwSize = ctypes.sizeof(me)
    out = []
    ok = kernel32.Module32First(snap, ctypes.byref(me))
    while ok:
        out.append((me.szModule.decode("latin1","replace"), ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value, me.modBaseSize))
        ok = kernel32.Module32Next(snap, ctypes.byref(me))
    kernel32.CloseHandle(snap)
    return out

def read(h, addr, n):
    buf = (ctypes.c_char * n)(); got = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)):
        return None
    return bytes(buf[:got.value])

def u32(b, o=0):
    return struct.unpack_from("<I", b, o)[0]
def f32(b, o=0):
    return struct.unpack_from("<f", b, o)[0]

def lookup(h, table, id1, id2):
    if not table or id1 in (0, 0xFFFFFFFF):
        return 0
    hdr = read(h, table, 0x40)
    if not hdr:
        return 0
    if (id1 >> 31) == 0:
        if id1 >= u32(hdr, 0x1C):
            return 0
        arr = u32(hdr, 0x0C)
    else:
        idx = id1 & 0x7FFFFFFF
        if idx >= u32(hdr, 0x3C):
            return 0
        arr = u32(hdr, 0x2C)
        id1 = idx
    slot = read(h, arr + id1 * 8, 8)
    if not slot or u32(slot) != 0xFFFFFFFE:
        return 0
    node = u32(slot, 4)
    if not node:
        return 0
    sec = read(h, node + 0x18, 4)
    if not sec or u32(sec) != id2:
        return 0
    return node

TYPES = {0x6573656E:"esen", 0x65647279:"edry", 0x6562616C:"ebal", 0x486A6169:"Hjai"}

def main():
    p = pid()
    h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, p)
    base = [m[1] for m in modules(p) if m[0].lower()=="game.dll"][0]
    lines = ["base 0x%X" % base]
    g = read(h, base + 0xBE40A8, 4)
    table = u32(g) if g else 0
    lines.append("agentTable 0x%X" % table)
    orgp = read(h, base + 0xBB82BC, 4)
    origin = u32(orgp) if orgp else 0
    lines.append("mapObj 0x%X" % origin)
    if origin:
        ob = read(h, origin + 0x60, 0x20)
        if ob:
            lines.append("map+6C %.3f +70 %.3f" % (f32(ob, 0x0C), f32(ob, 0x10)))

    # narrow scan
    vt = base + 0xA4A704
    pat = struct.pack("<I", vt)
    found = []
    mbi = MBI(); addr = 0x04000000
    while addr < 0x20000000 and len(found) < 24:
        if kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)) == 0:
            break
        ba = mbi.BaseAddress or 0
        sz = mbi.RegionSize or 0
        if sz == 0:
            break
        prot = mbi.Protect or 0
        if mbi.State == 0x1000 and not (prot & 0x100) and prot not in (0, 1) and sz <= 16*1024*1024 and ba >= 0x04000000:
            off = 0
            while off < sz and len(found) < 24:
                buf = read(h, ba+off, min(1024*1024, sz-off))
                if buf:
                    s = 0
                    while len(found) < 24:
                        i = buf.find(pat, s)
                        if i < 0:
                            break
                        s = i+4
                        unit = ba+off+i
                        tb = read(h, unit+0x30, 4)
                        if tb and u32(tb) in TYPES:
                            ids = read(h, unit + 0x16C, 4)
                            if ids and u32(ids) not in (0, 0xFFFFFFFF):
                                found.append(unit)
                off += 1024*1024
        nxt = ba+sz
        if nxt <= addr:
            break
        addr = nxt
    # unique by type, keep 2 each
    picked = []
    seen = {n:0 for n in TYPES.values()}
    for unit in found:
        tb = read(h, unit+0x30, 4)
        name = TYPES[u32(tb)]
        if seen[name] >= 2:
            continue
        seen[name] += 1
        picked.append((name, unit))
    lines.append("picked " + ", ".join("%s:%X" % (n,u) for n,u in picked))

    snaps = []
    for name, unit in picked:
        b = read(h, unit, 0x340)
        snaps.append((name, unit, b))
    time.sleep(0.30)
    for name, unit, b in snaps:
        b2 = read(h, unit, 0x340)
        if not b or not b2 or len(b) < 0x320:
            lines.append("MISS %s %X" % (name, unit))
            continue
        lines.append("==== %s 0x%X ====" % (name, unit))
        lines.append("net %08X %08X flags %08X fly %.2f f2cc %.3f" % (
            u32(b,0x0C), u32(b,0x10), u32(b,0x5C), f32(b,0x208), f32(b,0x2CC)))
        lines.append("speed70 %.2f -> %.2f  mul78 %.3f  gate7c %08X" % (
            f32(read(h, u32(b,0x1EC), 0x80) or b'\0'*0x80, 0x70) if u32(b,0x1EC) else 0,
            f32(read(h, u32(b2,0x1EC), 0x80) or b'\0'*0x80, 0x70) if u32(b2,0x1EC) else 0,
            f32(read(h, u32(b,0x1EC)+0x78, 4) or b'\0\0\0\0', 0) if u32(b,0x1EC) else 0,
            u32(read(h, u32(b,0x1EC)+0x7C, 4) or b'\0\0\0\0', 0) if u32(b,0x1EC) else 0))
        id1, id2 = u32(b,0x16C), u32(b,0x170)
        node = lookup(h, table, id1, id2)
        node2 = lookup(h, table, u32(b2,0x16C), u32(b2,0x170))
        lines.append("posNode %s -> %s" % (hex(node) if node else None, hex(node2) if node2 else None))
        if node:
            nb = read(h, node, 0x120)
            nb2 = read(h, node2, 0x120) if node2 else None
            if nb:
                def fl(buf, a, c):
                    return " ".join("%.2f" % f32(buf, o) for o in range(a, a+c*4, 4))
                lines.append("n70 " + fl(nb, 0x70, 12))
                if nb2:
                    lines.append("n70b " + fl(nb2, 0x70, 12))
                    dx = f32(nb2,0x78)-f32(nb,0x78)
                    dy = f32(nb2,0x7C)-f32(nb,0x7C)
                    dx2 = f32(nb2,0x70)-f32(nb,0x70)
                    dy2 = f32(nb2,0x74)-f32(nb,0x74)
                    lines.append("d0.30s +70 %.2f +74 %.2f +78 %.2f +7C %.2f" % (dx2, dy2, dx, dy))
                # collision-like
                hits = []
                for o in range(0, 0x120, 4):
                    v = f32(nb, o)
                    if v in (16.0, 24.0, 32.0, 48.0, 64.0) or (8 < v < 80 and abs(v-round(v))<0.01):
                        hits.append("+%X=%.1f" % (o, v))
                lines.append("node round floats " + " ".join(hits[:20]))
        # order
        on = lookup(h, table, u32(b,0x19C), u32(b,0x1A0))
        lines.append("orderIds %08X %08X node %s" % (u32(b,0x19C), u32(b,0x1A0), hex(on) if on else None))
        if on:
            nd = read(h, on, 0x60)
            if nd:
                obj = u32(nd, 0x54)
                lines.append("orderObj 0x%X class/node0C %08X" % (obj, u32(nd, 0x0C)))
                if obj:
                    od = read(h, obj, 0x90)
                    if od:
                        vt = u32(od, 0)
                        lines.append("orderVt 0x%X id +24 0x%X +28 0x%X" % (vt, u32(od,0x24), u32(od,0x28)))
                        parts = []
                        for o in range(0x20, 0x80, 4):
                            parts.append("+%02X %.1f/%08X" % (o, f32(od,o), u32(od,o)))
                        lines.append(" | ".join(parts))
        # unit blob small round floats that could be collision
        uh = []
        for o in range(0x40, 0x320, 4):
            v = f32(b, o)
            if 12 <= v <= 64 and abs(v-round(v)) < 0.05:
                uh.append("+%X=%.0f" % (o, v))
        lines.append("unit 12..64 " + " ".join(uh[:24]))

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    kernel32.CloseHandle(h)

if __name__ == "__main__":
    main()
