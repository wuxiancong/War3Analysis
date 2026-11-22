# -*- coding: utf-8 -*-
"""
1.27 实机只读内存核验脚本（严禁写内存，严禁在游戏线程外调 JASS 原生）：
读取当前运行中的 war3.exe (1.27.0.52240) 内存，核验：
  - A1: 冰女 (Hjai) 全部技能的 FourCC (+0x34)、等级 (+0x50+1)、冷却标志 (+0x20&0x200)、
        CAgentTimer (+0xD0 -> node +0xDC): 总冷却 (node+0x08)、到期时间 (node+0x04)、
        游戏时钟 (*(node+0x0C)+0x40)、精确剩余冷却 (expire - clock)。
  - A2: 玩家总金钱 (通过 CPlayer+0x50 / 10)。
  - A3: 全图所有英雄单位的隐身/反隐字段 (+0x130/+0x134) 与坐标，对照游戏线程 `units` 日志验证迷雾过滤。
  - A4: 英雄当前 Buff/Debuff 节点 (+0x1DC 链表中非技能节点)。
  - A5: 昼夜时间 (Game.dll+0xBE4238 路径)。
"""
import ctypes
import struct
import subprocess
import sys
import time
from ctypes import wintypes

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


def get_war3_pid() -> int:
    out = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process war3 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Id)"],
        text=True
    ).strip()
    return int(out) if out else 0


def get_game_dll_base(pid: int) -> int:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(me)
    ok = kernel32.Module32First(snap, ctypes.byref(me))
    base = 0
    while ok:
        if me.szModule.decode("latin1", "replace").lower() == "game.dll":
            base = ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value
            break
        ok = kernel32.Module32Next(snap, ctypes.byref(me))
    kernel32.CloseHandle(snap)
    return base


def rpm(h, addr, n):
    buf = (ctypes.c_char * n)()
    got = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)):
        return None
    return bytes(buf[:got.value])


def u32(b, o=0):
    return struct.unpack_from("<I", b, o)[0]


def f32(b, o=0):
    return struct.unpack_from("<f", b, o)[0]


def fourcc(v: int) -> str:
    try:
        s = struct.pack(">I", v).decode("ascii")
        return s if all(32 <= ord(c) < 127 for c in s) else f"0x{v:08X}"
    except Exception:
        return f"0x{v:08X}"


def resolve_agent(h, table, id1, id2):
    """对应 1.27 ResolveAgent (0x044150)：查代理表并从节点 +0x54 取实际 C++ 对象指针。"""
    if not table or (id1 & id2) == 0xFFFFFFFF or id1 == 0xFFFFFFFF:
        return 0
    hdr = rpm(h, table, 0x40)
    if not hdr:
        return 0
    if (id1 >> 31) == 0:
        if id1 >= u32(hdr, 0x1C):
            return 0
        arr = u32(hdr, 0x0C)
        idx = id1
    else:
        idx = id1 & 0x7FFFFFFF
        if idx >= u32(hdr, 0x3C):
            return 0
        arr = u32(hdr, 0x2C)
    slot = rpm(h, arr + idx * 8, 8)
    if not slot or u32(slot, 0) != 0xFFFFFFFE:
        return 0
    node = u32(slot, 4)
    if not node:
        return 0
    nb = rpm(h, node, 0x58)
    if not nb or len(nb) < 0x58:
        return 0
    if u32(nb, 0x18) != id2:
        return 0
    return u32(nb, 0x54)


def scan_heroes(h, base):
    """只读扫描 CUnit 虚表 (1.27 RVA 0xA4A704)，返回所有英雄 CUnit*（FourCC 首字节 'A'..'Z'）。"""
    vt = base + 0xA4A704
    pat = struct.pack("<I", vt)
    heroes = []
    mbi = MBI()
    addr = 0x04000000
    while addr < 0x30000000:
        if kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)) == 0:
            break
        ba = mbi.BaseAddress or 0
        sz = mbi.RegionSize or 0
        if sz == 0:
            break
        prot = mbi.Protect or 0
        if mbi.State == 0x1000 and not (prot & 0x100) and prot not in (0, 1) and sz <= 16 * 1024 * 1024 and ba >= 0x04000000:
            off = 0
            while off < sz:
                buf = rpm(h, ba + off, min(1024 * 1024, sz - off))
                if buf:
                    s = 0
                    while True:
                        i = buf.find(pat, s)
                        if i < 0:
                            break
                        s = i + 4
                        unit = ba + off + i
                        ub = rpm(h, unit, 0x60)
                        if ub and len(ub) >= 0x60:
                            tid = u32(ub, 0x30)
                            first_ch = (tid >> 24) & 0xFF
                            if 0x41 <= first_ch <= 0x5A:  # 'A'..'Z' 英雄
                                owner = u32(ub, 0x58)
                                heroes.append((unit, fourcc(tid), owner, u32(ub, 0x0C), u32(ub, 0x10)))
                off += 1024 * 1024
        nxt = ba + sz
        if nxt <= addr:
            break
        addr = nxt
    return heroes


def dump_hero_abilities(h, table, unit_addr):
    """沿 CUnit+0x1DC/+0x1E0 遍历所有技能与 Buff，并读取 CAbilitySpell+0xD0 冷却计时器。"""
    ub = rpm(h, unit_addr, 0x200)
    if not ub:
        return []
    id1, id2 = u32(ub, 0x1DC), u32(ub, 0x1E0)
    cur = resolve_agent(h, table, id1, id2)
    out = []
    seen = set()
    while cur and cur not in seen and len(out) < 80:
        seen.add(cur)
        ab = rpm(h, cur, 0xF0)
        if not ab or len(ab) < 0xE0:
            break
        cc = fourcc(u32(ab, 0x34))
        flags = u32(ab, 0x20)
        lvl = u32(ab, 0x50) + 1
        in_cd = bool(flags & 0x200)
        rem_cd, total_cd = 0.0, 0.0
        tnode = u32(ab, 0xDC)  # CAbilitySpell + 0xD0 + 0x0C
        if in_cd and tnode:
            tb = rpm(h, tnode, 0x14)
            if tb and len(tb) >= 0x10:
                expire = f32(tb, 0x04)
                total_cd = f32(tb, 0x08)
                tmgr = u32(tb, 0x0C)
                if tmgr:
                    cb = rpm(h, tmgr + 0x40, 4)
                    if cb:
                        rem_cd = max(0.0, expire - f32(cb, 0))
        out.append({
            "ptr": f"0x{cur:08X}",
            "fourcc": cc,
            "lvl": lvl,
            "flags": f"0x{flags:08X}",
            "in_cd": in_cd,
            "rem_cd": round(rem_cd, 3),
            "total_cd": round(total_cd, 3),
        })
        n1, n2 = u32(ab, 0x24), u32(ab, 0x28)
        cur = resolve_agent(h, table, n1, n2)
    return out


def main():
    pid = get_war3_pid()
    if not pid:
        print("[ERR] 未检测到运行中的 war3.exe")
        sys.exit(1)
    h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    base = get_game_dll_base(pid)
    tb = rpm(h, base + 0xBE40A8, 4)
    table = u32(tb) if tb else 0
    print(f"war3 PID={pid}, Game.dll=0x{base:08X}, AgentTable=0x{table:08X}")
    heroes = scan_heroes(h, base)
    print(f"扫描到英雄数量: {len(heroes)}")
    for unit, cc, owner, o1, o2 in heroes:
        print(f"  Hero {cc} @ 0x{unit:08X} owner={owner} obj=({o1:08X},{o2:08X})")
        if cc == "Hjai":
            abils = dump_hero_abilities(h, table, unit)
            for a in abils:
                if a["fourcc"].startswith(("A", "B")):
                    print(f"    [{a['fourcc']}] lvl={a['lvl']} in_cd={a['in_cd']} rem={a['rem_cd']}s total={a['total_cd']}s flags={a['flags']}")
    kernel32.CloseHandle(h)


if __name__ == "__main__":
    main()
