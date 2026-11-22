# -*- coding: utf-8 -*-
"""
六路兵线实时只读内存采样器（1.27.0.52240）：
- 严格只读（PROCESS_VM_READ），不写任何内存，不调任何 JASS 原生，不发任何卡兵指令。
- 同时追踪近卫（esen/edry/ebal）与天灾（ugho/unec/umtw）全部六路小兵：
    - 精确世界坐标：worldX = [posNode+0x78]*32 + mapOriginX(-8192), worldY = [posNode+0x7C]*32 + mapOriginY(-8192)
    - 实时速度向量：velX = [posNode+0x80]*32, velY = [posNode+0x84]*32, maxSpd = [posNode+0x88]*32
    - 实时朝向：facingRad = [posNode+0x90]
    - 技能/Buff 列表 (CUnit+0x1DC)：提取 A007 等级 (2=上/3=中/4=下)、是否存在 A2V1/B0H2 (+25%) 或 A2V0/B0H1 (-25%)
- 自动检测「前 7 分钟光环期」与「7 分钟后无光环期」，采满至少 3 波无光环期（每波走满 26s）后自动退出。
"""
import ctypes
import math
import os
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

OUT_CSV = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\live_six_lanes_trace.csv"

CREEP_TYPES = {
    0x6573656E: ("esen", "rad", "melee"),
    0x65647279: ("edry", "rad", "ranged"),
    0x6562616C: ("ebal", "rad", "siege"),
    0x7567686F: ("ugho", "dire", "melee"),
    0x756E6563: ("unec", "dire", "ranged"),
    0x756D7477: ("umtw", "dire", "siege"),
}


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


def lookup_agent_node(h, table, id1, id2):
    if not table or id1 in (0, 0xFFFFFFFF) or (id1 & id2) == 0xFFFFFFFF:
        return 0
    hdr = rpm(h, table, 0x40)
    if not hdr or len(hdr) < 0x40:
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
    sec = rpm(h, node + 0x18, 4)
    if not sec or u32(sec, 0) != id2:
        return 0
    return node


def resolve_agent_obj(h, table, id1, id2):
    node = lookup_agent_node(h, table, id1, id2)
    if not node:
        return 0
    pb = rpm(h, node + 0x54, 4)
    return u32(pb, 0) if pb else 0


def scan_creep_units(h, base):
    vt = base + 0xA4A704
    pat = struct.pack("<I", vt)
    units = []
    mbi = MBI()
    addr = 0x04000000
    while addr < 0x35000000:
        if kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)) == 0:
            break
        ba = mbi.BaseAddress or 0
        sz = mbi.RegionSize or 0
        if sz == 0:
            break
        prot = mbi.Protect or 0
        if mbi.State == 0x1000 and not (prot & 0x100) and prot not in (0, 1) and sz <= 32 * 1024 * 1024 and ba >= 0x04000000:
            off = 0
            while off < sz:
                chunk = min(1024 * 1024, sz - off)
                buf = rpm(h, ba + off, chunk)
                if buf:
                    s = 0
                    while True:
                        i = buf.find(pat, s)
                        if i < 0:
                            break
                        s = i + 4
                        u = ba + off + i
                        if i + 0x60 <= len(buf):
                            tid = u32(buf, i + 0x30)
                            flags = u32(buf, i + 0x5C)
                        else:
                            ub = rpm(h, u + 0x30, 0x30)
                            if not ub or len(ub) < 0x30:
                                continue
                            tid = u32(ub, 0)
                            flags = u32(ub, 0x2C)
                        if tid in CREEP_TYPES and not (flags & 0x100):
                            units.append(u)
                off += chunk
        nxt = ba + sz
        if nxt <= addr:
            break
        addr = nxt
    return units


def read_creep_abilities(h, table, ub):
    id1, id2 = u32(ub, 0x1DC), u32(ub, 0x1E0)
    cur = resolve_agent_obj(h, table, id1, id2)
    lane_lvl = 0
    aura = "none"
    seen = set()
    while cur and cur not in seen and len(seen) < 16:
        seen.add(cur)
        ab = rpm(h, cur, 0x60)
        if not ab or len(ab) < 0x54:
            break
        aid = u32(ab, 0x34)
        lvl = u32(ab, 0x50) + 1
        if aid == 0x41303037:  # 'A007'
            lane_lvl = lvl
        elif aid in (0x41325631, 0x42304832):  # 'A2V1' or 'B0H2'
            aura = "A2V1"
        elif aid in (0x41325630, 0x42304831):  # 'A2V0' or 'B0H1'
            aura = "A2V0"
        cur = resolve_agent_obj(h, table, u32(ab, 0x24), u32(ab, 0x28))
    return lane_lvl, aura


def main():
    max_duration_s = float(sys.argv[1]) if len(sys.argv) > 1 else 600.0
    pid = get_war3_pid()
    if not pid:
        print("[ERR] war3.exe 未运行")
        sys.exit(1)
    h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    base = get_game_dll_base(pid)
    tb = rpm(h, base + 0xBE40A8, 4)
    table = u32(tb) if tb else 0
    mb = rpm(h, base + 0xBB82BC, 4)
    map_obj = u32(mb) if mb else 0
    ox, oy = -8192.0, -8192.0
    if map_obj:
        ob = rpm(h, map_obj + 0x6C, 8)
        if ob and len(ob) == 8:
            ox, oy = f32(ob, 0), f32(ob, 4)
    print(f"Attached war3 PID={pid}, Game.dll=0x{base:08X}, AgentTable=0x{table:08X}, Origin=({ox},{oy})", flush=True)

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    f = open(OUT_CSV, "w", encoding="utf-8")
    f.write("t_sec,wave_id,unit_ptr,obj1,fourcc,team,role,lane_lvl,aura,x,y,vx,vy,v_mag,max_spd,amov_base,amov_mul,facing_deg\n")

    known_units = set()
    unit_meta = {}       # u -> (wave_id, lane_lvl, last_check_t, aura)
    t_start = time.time()
    last_scan = 0.0
    last_log = 0.0
    rows_written = 0

    wave_id = 0
    last_wave_spawn_t = -999.0
    first_wave_t = None
    unboosted_waves_seen = 0
    last_unboosted_wave_t = None

    while time.time() - t_start < max_duration_s:
        now = time.time()
        elapsed = now - t_start
        # 每 1.5 秒全堆扫描一次新刷出的兵，确保出兵第 0~1.5s 即捕获
        if now - last_scan >= 1.5 or not known_units:
            current_units = scan_creep_units(h, base)
            new_batch = [u for u in current_units if u not in known_units]
            if len(new_batch) >= 12 and (elapsed - last_wave_spawn_t >= 20.0):
                wave_id += 1
                last_wave_spawn_t = elapsed
                if first_wave_t is None:
                    first_wave_t = elapsed
                # 检查本波新兵在边路是否还带 A2V1 / A2V0
                side_auras = []
                for u in new_batch:
                    ub = rpm(h, u, 0x200)
                    if ub and len(ub) >= 0x200:
                        ll, aura = read_creep_abilities(h, table, ub)
                        unit_meta[u] = (wave_id, ll, elapsed, aura)
                        if ll in (2, 4):
                            side_auras.append(aura)
                has_aura = any(a in ("A2V1", "A2V0") for a in side_auras)
                game_t = elapsed - first_wave_t
                print(f"[Wave {wave_id:2d}] t={elapsed:5.1f}s (game_t={game_t:5.1f}s) 新刷小兵={len(new_batch)} | 边路光环={has_aura} ({set(side_auras)})", flush=True)
                if not has_aura and wave_id >= 2:
                    unboosted_waves_seen += 1
                    last_unboosted_wave_t = elapsed
            for u in new_batch:
                known_units.add(u)
                if u not in unit_meta:
                    unit_meta[u] = (max(1, wave_id), 0, -99.0, "none")
            last_scan = now

        # 若已采满 3 波无光环期且第 3 波已走完 26 秒，则圆满结束
        if unboosted_waves_seen >= 3 and last_unboosted_wave_t is not None and (elapsed - last_unboosted_wave_t >= 26.0):
            print(f"[DONE] 已完整采集 {wave_id} 波（含 {unboosted_waves_seen} 波 7 分钟后无光环波次），停止采样。", flush=True)
            break

        dead = []
        for u in list(known_units):
            ub = rpm(h, u, 0x200)
            if not ub or len(ub) < 0x200:
                dead.append(u)
                continue
            tid = u32(ub, 0x30)
            flags = u32(ub, 0x5C)
            if tid not in CREEP_TYPES or (flags & 0x100):
                dead.append(u)
                continue
            cc, team, role = CREEP_TYPES[tid]
            obj1 = u32(ub, 0x0C)
            pos_id1, pos_id2 = u32(ub, 0x16C), u32(ub, 0x170)
            pnode = lookup_agent_node(h, table, pos_id1, pos_id2)
            if not pnode:
                continue
            pb = rpm(h, pnode + 0x70, 0x30)
            if not pb or len(pb) < 0x28:
                continue
            wx = f32(pb, 0x08) * 32.0 + ox
            wy = f32(pb, 0x0C) * 32.0 + oy
            vx = f32(pb, 0x10) * 32.0
            vy = f32(pb, 0x14) * 32.0
            vmag = math.hypot(vx, vy)
            mspd = f32(pb, 0x18) * 32.0
            fdeg = (f32(pb, 0x20) * 57.2957795) % 360.0

            amov = u32(ub, 0x1EC)
            abase, amul = 0.0, 0.0
            if amov:
                amb = rpm(h, amov + 0x70, 12)
                if amb and len(amb) >= 12:
                    abase = f32(amb, 0)
                    amul = f32(amb, 8)

            wid, ll, last_chk, aura = unit_meta.get(u, (max(1, wave_id), 0, -99.0, "none"))
            if (elapsed - last_chk >= 0.8) or ll == 0:
                new_ll, new_aura = read_creep_abilities(h, table, ub)
                if new_ll != 0:
                    ll = new_ll
                aura = new_aura
                unit_meta[u] = (wid, ll, elapsed, aura)

            f.write(f"{elapsed:.2f},{wid},0x{u:08X},0x{obj1:08X},{cc},{team},{role},{ll},{aura},{wx:.1f},{wy:.1f},{vx:.1f},{vy:.1f},{vmag:.1f},{mspd:.1f},{abase:.1f},{amul:.3f},{fdeg:.1f}\n")
            rows_written += 1

        for u in dead:
            known_units.discard(u)
            unit_meta.pop(u, None)

        if elapsed - last_log >= 20.0:
            print(f"  [t={elapsed:5.1f}s] active_creeps={len(known_units)}, rows={rows_written}, wave={wave_id}, unboosted_waves={unboosted_waves_seen}", flush=True)
            last_log = elapsed

        f.flush()
        time.sleep(0.15)

    f.close()
    kernel32.CloseHandle(h)
    print(f"Done! Wrote {rows_written} rows to {OUT_CSV}", flush=True)


if __name__ == "__main__":
    main()
