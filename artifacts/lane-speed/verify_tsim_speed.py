# -*- coding: utf-8 -*-
r"""
读取 CPoPosCl+0x60 (游戏引擎内部仿真时钟 t_sim，单位：游戏秒，32Hz 步进) 与合成世界坐标：
  worldX = ([posNode+0x78] + (t_sim_now - [posNode+0x60]) * [posNode+0x80]) * 32.0 - 8192.0
实测核对 ds / dt_sim 与 2D_dist / dt_sim（完全消除外部 RPM 抢占 VM CPU 导致的墙钟膨胀）。
"""
import ctypes
import ctypes.wintypes as wt
import struct
import time
import math
import subprocess
from collections import defaultdict

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
    ]

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t

def get_pid():
    out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq war3.exe", "/FO", "CSV", "/NH"], text=True)
    for line in out.strip().splitlines():
        if "war3.exe" in line.lower():
            return int(line.split(",")[1].strip('"'))
    return None

def rpm(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)) and n.value == size:
        return buf.raw
    return None

def r_u32(h, addr):
    b = rpm(h, addr, 4)
    return struct.unpack("<I", b)[0] if b else 0

def r_f32(h, addr):
    b = rpm(h, addr, 4)
    return struct.unpack("<f", b)[0] if b else 0.0

CREEP_IDS = {
    b"esen": ("rad", "melee"),
    b"edry": ("rad", "ranged"),
    b"ebal": ("rad", "siege"),
    b"ugho": ("dire", "melee"),
    b"unec": ("dire", "ranged"),
    b"umtw": ("dire", "siege"),
}

def main():
    pid = get_pid()
    if not pid:
        print("war3.exe not running")
        return
    h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    cunit_vt = 0x65820000 + 0xA69108
    vt_bytes = struct.pack("<I", cunit_vt)

    # 扫描一次缓存堆区
    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0x04000000
    regions = []
    while addr < 0x35000000:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if mbi.State == 0x1000 and (mbi.Protect & 0x04) and 0x10000 <= size <= 0x2000000:
            data = rpm(h, base, size)
            if data and vt_bytes in data:
                regions.append((base, size))
        addr = base + max(size, 0x1000)

    print(f"Found {len(regions)} CUnit heap regions")
    samples = defaultdict(list)

    # 间隔 2.0s 采 5 次（低频零 CPU 抢占，同时读取 CPoPosCl+0x60 引擎仿真时钟）
    for step in range(6):
        t_wall = time.time()
        for base, size in regions:
            data = rpm(h, base, size)
            if not data:
                continue
            pos = 0
            while True:
                idx = data.find(vt_bytes, pos)
                if idx == -1:
                    break
                pos = idx + 4
                if idx + 0x290 > size:
                    continue
                type_bytes = data[idx + 0x30 : idx + 0x34][::-1]
                if type_bytes not in CREEP_IDS:
                    continue
                flags = struct.unpack_from("<I", data, idx + 0x20)[0]
                if flags & 0x100:
                    continue
                obj1 = struct.unpack_from("<I", data, idx + 0x0C)[0]
                pos_node = struct.unpack_from("<I", data, idx + 0x168)[0]
                amov = struct.unpack_from("<I", data, idx + 0x1EC)[0]
                if pos_node < 0x01000000:
                    continue
                pbuf = rpm(h, pos_node + 0x60, 0x30)
                if not pbuf:
                    continue
                t_sim0, t_sim1 = struct.unpack_from("<ff", pbuf, 0x00)
                gx, gy, vx, vy, mspd = struct.unpack_from("<fffff", pbuf, 0x18)
                wx = gx * 32.0 - 8192.0
                wy = gy * 32.0 - 8192.0
                vmag = math.hypot(vx * 32.0, vy * 32.0)
                if vmag > 100.0:
                    samples[obj1].append((t_wall, t_sim0, wx, wy, vmag, mspd * 32.0))
        if step < 5:
            time.sleep(2.0)

    out_lines = []
    v_sims = []
    v_walls = []
    for obj1, pts in samples.items():
        if len(pts) < 2:
            continue
        t_w0, t_s0, x0, y0, vm0, ms0 = pts[0]
        t_w1, t_s1, x1, y1, vm1, ms1 = pts[-1]
        dt_sim = t_s1 - t_s0
        dt_wall = t_w1 - t_w0
        dist = math.hypot(x1 - x0, y1 - y0)
        if dt_sim > 2.0 and dist > 500.0:
            v_sim = dist / dt_sim
            v_wall = dist / dt_wall
            v_sims.append(v_sim)
            v_walls.append(v_wall)
            out_lines.append(f"  obj1=0x{obj1:08X}: dist={dist:6.1f}, dt_sim={dt_sim:5.2f}s, dt_wall={dt_wall:5.2f}s | v_sim={v_sim:5.1f}/s, v_wall={v_wall:5.1f}/s, v_mag={vm1:5.1f}/s")

    out_lines.insert(0, f"Valid moving creeps (low-load 0.5Hz): n={len(v_sims)}, avg v_sim={sum(v_sims)/max(1,len(v_sims)):.1f}/s, avg v_wall={sum(v_walls)/max(1,len(v_walls)):.1f}/s")
    res = "\n".join(out_lines)
    with open(r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\tsim_verification.txt", "w", encoding="utf-8") as f:
        f.write(res)
    print(res[:1500])

if __name__ == "__main__":
    main()
