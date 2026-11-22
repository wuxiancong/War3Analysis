# -*- coding: utf-8 -*-
"""
六路兵线 10Hz (100ms) 高频只读采样器（1.27.0.52240）：
- 优化：首次扫描记录 CUnit 所在的堆块 (MBI region)，后续每 1.0 秒仅扫描这些堆块（耗时 <15ms，不阻塞 100ms 采样循环）。
- 判定光环：直接检查整波新兵中是否有任何单位带有 A2V1/B0H2 或 A2V0/B0H1（不依赖 lane_lvl），
  完整捕获「前 7 分钟有光环波」到「7 分钟后无光环波（至少 3 波）」的切换全过程！
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

OUT_CSV = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\live_six_lanes_10hz.csv"

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


def scan_cunit_regions(h, base, cached_regions=None):
    """快速扫描 CUnit 堆区：首次全扫并缓存命中块，后续仅扫命中块 (<15ms)。"""
    vt = base + 0xA4A704
    pat = struct.pack("<I", vt)
    units = []
    hit_regions = set()

    if cached_regions:
        for ba, sz in cached_regions:
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
                            if tid in CREEP_TYPES and not (flags & 0x100):
                                units.append(u)
                off += chunk
        return units, cached_regions

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
            region_has_unit = False
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
                        region_has_unit = True
                        u = ba + off + i
                        if i + 0x60 <= len(buf):
                            tid = u32(buf, i + 0x30)
                            flags = u32(buf, i + 0x5C)
                            if tid in CREEP_TYPES and not (flags & 0x100):
                                units.append(u)
                off += chunk
            if region_has_unit:
                hit_regions.add((ba, sz))
        nxt = ba + sz
        if nxt <= addr:
            break
        addr = nxt
    return units, sorted(hit_regions)


def main():
    max_duration_s = float(sys.argv[1]) if len(sys.argv) > 1 else 300.0
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

    units0, cached_regions = scan_cunit_regions(h, base, None)
    print(f"Attached PID={pid}, cached {len(cached_regions)} CUnit heap regions ({sum(sz for _,sz in cached_regions)//1024} KB), initial creeps={len(units0)}", flush=True)

    f = open(OUT_CSV, "w", encoding="utf-8")
    f.write("t_sec,wave_id,unit_ptr,obj1,fourcc,team,role,aura,x,y,vx,vy,v_mag,max_spd,amov_base,amov_mul,facing_deg\n")

    known_units = set(units0)
    unit_wave = {u: 0 for u in units0}
    t_start = time.time()
    last_scan = t_start
    last_full_scan = t_start
    wave_id = 0
    last_wave_t = -999.0
    unboosted_waves = 0
    last_unboosted_t = None
    rows = 0

    while time.time() - t_start < max_duration_s:
        t0_loop = time.time()
        elapsed = t0_loop - t_start

        # 每 0.5 秒快速扫描缓存块 (<10ms)，每 25 秒做一次全堆刷新防新分配块遗漏
        if t0_loop - last_scan >= 0.5:
            if t0_loop - last_full_scan >= 25.0:
                cur_units, cached_regions = scan_cunit_regions(h, base, None)
                last_full_scan = t0_loop
            else:
                cur_units, _ = scan_cunit_regions(h, base, cached_regions)
            new_batch = [u for u in cur_units if u not in known_units]
            if len(new_batch) >= 10 and (elapsed - last_wave_t >= 18.0):
                wave_id += 1
                last_wave_t = elapsed
                # 直接通过 CAbilityMove+0x78 (amov_mul) 判断本波是否有 1.25 / 0.75 光环！既快又 100% 准确！
                muls = []
                for u in new_batch:
                    ub = rpm(h, u, 0x200)
                    if ub and len(ub) >= 0x200:
                        amov = u32(ub, 0x1EC)
                        if amov:
                            amb = rpm(h, amov + 0x70, 12)
                            if amb and len(amb) >= 12:
                                muls.append(round(f32(amb, 8), 3))
                has_boost = any(abs(m - 1.25) < 0.02 or abs(m - 0.75) < 0.02 for m in muls)
                print(f"[10Hz Wave {wave_id:2d}] t={elapsed:5.1f}s 新兵={len(new_batch)} | 速度乘数集={sorted(set(muls))} | 含边路光环={has_boost}", flush=True)
                if not has_boost:
                    unboosted_waves += 1
                    last_unboosted_t = elapsed
            for u in new_batch:
                known_units.add(u)
                unit_wave[u] = wave_id
            last_scan = t0_loop

        if unboosted_waves >= 3 and last_unboosted_t is not None and (elapsed - last_unboosted_t >= 27.0):
            print(f"[DONE] 10Hz 采样已捕获 {unboosted_waves} 波 7 分钟后无光环完整轨迹，结束。", flush=True)
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
            pnode = lookup_agent_node(h, table, u32(ub, 0x16C), u32(ub, 0x170))
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
            abase, amul = 325.0, 1.0
            if amov:
                amb = rpm(h, amov + 0x70, 12)
                if amb and len(amb) >= 12:
                    abase = f32(amb, 0)
                    amul = f32(amb, 8)
            aura = "A2V1" if amul > 1.1 else ("A2V0" if amul < 0.9 else "none")
            wid = unit_wave.get(u, 0)
            f.write(f"{elapsed:.2f},{wid},0x{u:08X},0x{obj1:08X},{cc},{team},{role},{aura},{wx:.1f},{wy:.1f},{vx:.1f},{vy:.1f},{vmag:.1f},{mspd:.1f},{abase:.1f},{amul:.3f},{fdeg:.1f}\n")
            rows += 1

        for u in dead:
            known_units.discard(u)
            unit_wave.pop(u, None)

        f.flush()
        dt_sleep = max(0.01, 0.10 - (time.time() - t0_loop))
        time.sleep(dt_sleep)

    f.close()
    kernel32.CloseHandle(h)
    print(f"Done! Wrote {rows} rows to {OUT_CSV}", flush=True)


if __name__ == "__main__":
    main()
