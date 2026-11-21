"""Read-only live verifier for War3 1.27.0.52240 combat/lasthit memory structures.
Attaches to war3.exe with PROCESS_VM_READ only (no injection, no writes).
"""
import ctypes, ctypes.wintypes as wt
import struct, time, json, sys, os, math

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", wt.LONG), ("dwFlags", wt.DWORD), ("szExeFile", wt.WCHAR * 260),
    ]

class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE), ("szModule", wt.WCHAR * 256),
        ("szExePath", wt.WCHAR * 260),
    ]

def find_pid(exe_name="war3.exe"):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(pe)
    pid = None
    if kernel32.Process32FirstW(snap, ctypes.byref(pe)):
        while True:
            if pe.szExeFile.lower() == exe_name.lower():
                pid = pe.th32ProcessID
                break
            if not kernel32.Process32NextW(snap, ctypes.byref(pe)):
                break
    kernel32.CloseHandle(snap)
    return pid

def find_module_base(pid, mod_name="game.dll"):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    me = MODULEENTRY32W()
    me.dwSize = ctypes.sizeof(me)
    base = None
    if kernel32.Module32FirstW(snap, ctypes.byref(me)):
        while True:
            if me.szModule.lower() == mod_name.lower():
                base = me.modBaseAddr
                break
            if not kernel32.Module32NextW(snap, ctypes.byref(me)):
                break
    kernel32.CloseHandle(snap)
    return base

class ProcReader:
    def __init__(self, pid):
        self.h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not self.h:
            raise OSError(f"OpenProcess failed: {ctypes.get_last_error()}")

    def read(self, addr, size):
        if not addr or addr < 0x10000 or addr > 0x7FFF0000:
            return None
        buf = ctypes.create_string_buffer(size)
        n = ctypes.c_size_t(0)
        if not kernel32.ReadProcessMemory(self.h, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)):
            return None
        return buf.raw[:n.value]

    def u32(self, addr):
        b = self.read(addr, 4)
        return struct.unpack("<I", b)[0] if b and len(b) == 4 else None

    def i32(self, addr):
        b = self.read(addr, 4)
        return struct.unpack("<i", b)[0] if b and len(b) == 4 else None

    def f32(self, addr):
        b = self.read(addr, 4)
        return struct.unpack("<f", b)[0] if b and len(b) == 4 else None

    def close(self):
        kernel32.CloseHandle(self.h)

# 1.27.0.52240 RVAs
RVA_AGENT_MGR      = 0xBE40A8
RVA_VT_UNIT        = 0xA4A704
RVA_VT_MISSILE     = 0x9B07D0
RVA_VT_MSPLASH     = 0x9B089C
RVA_VT_MBOUNCE     = 0x9EBE4C
RVA_VT_MLINE       = 0xA506BC
RVA_NEG_ARMOR_TBL  = 0xBEC2F8
RVA_DMG_BONUS_TBL  = 0xBEC368

def fourcc_str(val):
    if not val: return "0000"
    b = struct.pack(">I", val)
    return "".join(chr(c) if 32 <= c < 127 else "?" for c in b)

def resolve_agent_link(pr, mgr, id1, id2):
    if id1 is None or id2 is None or (id1 & id2) == 0xFFFFFFFF:
        return None
    if id1 & 0x80000000:
        idx = id1 & 0x7FFFFFFF
        cnt = pr.u32(mgr + 0x3C)
        arr = pr.u32(mgr + 0x2C)
    else:
        idx = id1
        cnt = pr.u32(mgr + 0x1C)
        arr = pr.u32(mgr + 0x0C)
    if cnt is None or arr is None or idx >= cnt:
        return None
    entry = pr.read(arr + idx * 8, 8)
    if not entry or len(entry) < 8:
        return None
    tag, link = struct.unpack("<iI", entry)
    if tag != -2 or not link:
        return None
    gen = pr.u32(link + 0x18)
    if gen != id2:
        return None
    return link

def resolve_agent_ptr(pr, mgr, id1, id2):
    link = resolve_agent_link(pr, mgr, id1, id2)
    if not link:
        return None
    if pr.u32(link + 0x20) != 0:
        return None
    return pr.u32(link + 0x54)

def read_timer_rem(pr, timer_addr):
    node = pr.u32(timer_addr + 0x0C)
    if not node:
        return 0.0
    exp_t = pr.f32(node + 0x04)
    clk = pr.u32(node + 0x0C)
    if exp_t is None or not clk:
        return 0.0
    now_t = pr.f32(clk + 0x40)
    if now_t is None:
        return 0.0
    rem = exp_t - now_t
    return rem if rem > 0.0 else 0.0

def read_unit_life(pr, mgr, unit_addr):
    # CUnit + 0x98 -> CAgentPtr at +0xA0/+0xA4 -> link + 0x78 (baseLife)
    id1 = pr.u32(unit_addr + 0xA0)
    id2 = pr.u32(unit_addr + 0xA4)
    link = resolve_agent_link(pr, mgr, id1, id2)
    if not link:
        return None
    return pr.f32(link + 0x78)

def read_attack_info(pr, unit_addr):
    atk = pr.u32(unit_addr + 0x1E8)
    if not atk:
        return None
    buf = pr.read(atk, 0x2D0)
    if not buf or len(buf) < 0x2C0:
        return None
    idx = struct.unpack_from("<I", buf, 0x2B8)[0]
    if idx not in (0, 1):
        idx = 0
    dice = struct.unpack_from("<i", buf, 0x88 + idx * 4)[0]
    sides = struct.unpack_from("<i", buf, 0x94 + idx * 4)[0]
    base = struct.unpack_from("<i", buf, 0xA0 + idx * 4)[0]
    bonus = struct.unpack_from("<i", buf, 0xAC + idx * 4)[0]
    weap_tp = struct.unpack_from("<I", buf, 0xDC + idx * 4)[0]
    atk_tp = struct.unpack_from("<I", buf, 0xF4 + idx * 4)[0]
    bat = struct.unpack_from("<f", buf, 0x158 + idx * 8)[0]
    dmgpt = struct.unpack_from("<f", buf, 0x16C + idx * 0x10)[0]
    backsw = struct.unpack_from("<f", buf, 0x190 + idx * 0x10)[0]
    ias = struct.unpack_from("<f", buf, 0x1B0)[0]
    slow = struct.unpack_from("<f", buf, 0x1C0)[0]
    acq = struct.unpack_from("<f", buf, 0x244)[0]
    rng = struct.unpack_from("<f", buf, 0x258 + idx * 8)[0]
    f_bc = struct.unpack_from("<f", buf, 0xBC + idx * 0x10)[0]
    f_110 = struct.unpack_from("<f", buf, 0x110 + idx * 0x10)[0]
    f_134 = struct.unpack_from("<f", buf, 0x134 + idx * 0x10)[0]
    return {
        "atk_ptr": hex(atk), "idx": idx,
        "dice": dice, "sides": sides, "base": base, "bonus": bonus,
        "min_dmg": base + bonus + dice, "max_dmg": base + bonus + dice * sides,
        "weap_tp": weap_tp, "atk_tp": atk_tp,
        "bat": round(bat, 4), "dmgpt": round(dmgpt, 4), "backsw": round(backsw, 4),
        "ias": round(ias, 4), "slow": round(slow, 4),
        "eff_cd": round(bat / max(0.2, min(5.0, ias)), 4),
        "eff_dmgpt": round(dmgpt / max(0.2, min(5.0, ias)), 4),
        "acq": round(acq, 1), "range": round(rng, 1),
        "off_BC": round(f_bc, 3), "off_110": round(f_110, 3), "off_134": round(f_134, 3),
    }

def scan_agents(pr, gbase, mgr):
    cnt = pr.u32(mgr + 0x1C)
    arr = pr.u32(mgr + 0x0C)
    if not cnt or not arr or cnt > 200000:
        return [], []
    raw = pr.read(arr, cnt * 8)
    if not raw:
        return [], []
    vt_unit = gbase + RVA_VT_UNIT
    vt_missiles = {gbase + RVA_VT_MISSILE, gbase + RVA_VT_MSPLASH, gbase + RVA_VT_MBOUNCE, gbase + RVA_VT_MLINE}
    units = []
    missiles = []
    for i in range(cnt):
        tag, link = struct.unpack_from("<iI", raw, i * 8)
        if tag != -2 or not link:
            continue
        lbuf = pr.read(link, 0x58)
        if not lbuf or len(lbuf) < 0x58:
            continue
        dead_flag = struct.unpack_from("<I", lbuf, 0x20)[0]
        obj = struct.unpack_from("<I", lbuf, 0x54)[0]
        if dead_flag != 0 or not obj:
            continue
        vt = pr.u32(obj)
        if vt == vt_unit:
            units.append(obj)
        elif vt in vt_missiles:
            missiles.append(obj)
    return units, missiles

def calc_armor_mult(armor, neg_tbl, k=0.06):
    if armor >= 0.0:
        red = (k * armor) / (1.0 + k * armor)
        return 1.0 - red
    else:
        n = min(20, int(-armor))
        return 1.0 - neg_tbl[n]

def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
    pid = find_pid("war3.exe")
    if not pid:
        print("ERROR: war3.exe not running")
        sys.exit(1)
    gbase = find_module_base(pid, "game.dll")
    if not gbase:
        print("ERROR: game.dll not found")
        sys.exit(1)
    print(f"Attached RO to war3.exe PID={pid}, game.dll=0x{gbase:08X}")
    pr = ProcReader(pid)
    mgr = pr.u32(gbase + RVA_AGENT_MGR)
    print(f"g_AgentManager = 0x{mgr:08X}")

    # Read DamageBonusTable (7x8) and NegArmorTable (21)
    dmg_tbl_raw = pr.read(gbase + RVA_DMG_BONUS_TBL, 7 * 8 * 4)
    dmg_tbl = [list(struct.unpack_from("<8f", dmg_tbl_raw, r * 32)) for r in range(7)]
    neg_raw = pr.read(gbase + RVA_NEG_ARMOR_TBL, 21 * 4)
    neg_tbl = list(struct.unpack("<21f", neg_raw))
    print("DamageBonusTable[Hero(6)]:", [round(x, 3) for x in dmg_tbl[6]])
    print("DamageBonusTable[Normal(1)]:", [round(x, 3) for x in dmg_tbl[1]])
    print("DamageBonusTable[Pierce(2)]:", [round(x, 3) for x in dmg_tbl[2]])
    print("DamageBonusTable[Siege(3)]:", [round(x, 3) for x in dmg_tbl[3]])
    print("NegArmorTable[0..5]:", [round(x, 4) for x in neg_tbl[:6]])

    # Initial unit scan
    units, _ = scan_agents(pr, gbase, mgr)
    hjai_addr = None
    sample_units = {}
    WANTED = {"Hjai", "esen", "edry", "ebal", "ugho", "unec", "umtw"}
    for u in units:
        tid = fourcc_str(pr.u32(u + 0x30))
        if tid in WANTED:
            if tid == "Hjai":
                hjai_addr = u
            if tid not in sample_units:
                arm = pr.f32(u + 0xE0)
                dtp = pr.u32(u + 0xE4)
                hp = read_unit_life(pr, mgr, u)
                atk = read_attack_info(pr, u)
                sample_units[tid] = {"addr": hex(u), "armor": round(arm, 3) if arm is not None else None, "defType": dtp, "hp": round(hp, 2) if hp is not None else None, "atk": atk}
                print(f"UNIT {tid} @ 0x{u:08X}: armor={sample_units[tid]['armor']} defType={dtp} hp={sample_units[tid]['hp']} atk={atk}")

    if not hjai_addr:
        print("WARNING: Hjai not found yet!")
        pr.close()
        return

    # Track Hjai windups, missiles, and impacts
    active_missiles = {}
    events = []
    in_windup = False
    windup_start = 0.0
    windup_rem0 = 0.0
    t0 = time.perf_counter()
    print(f"\nMonitoring Hjai @ 0x{hjai_addr:08X} for {duration}s...")
    while time.perf_counter() - t0 < duration:
        now = time.perf_counter()
        atk_ptr = pr.u32(hjai_addr + 0x1E8)
        if atk_ptr:
            w_rem = read_timer_rem(pr, atk_ptr + 0x1EC)
            if w_rem > 0.001 and not in_windup:
                in_windup = True
                windup_start = now
                windup_rem0 = w_rem
            elif w_rem <= 0.001 and in_windup:
                in_windup = False

        _, missiles = scan_agents(pr, gbase, mgr)
        seen_now = set()
        for m in missiles:
            mbuf = pr.read(m, 0xAC)
            if not mbuf or len(mbuf) < 0xA8:
                continue
            src_id1, src_id2 = struct.unpack_from("<II", mbuf, 0x2C)
            src = resolve_agent_ptr(pr, mgr, src_id1, src_id2)
            if src != hjai_addr:
                continue
            seen_now.add(m)
            if m not in active_missiles:
                tgt_id1, tgt_id2 = struct.unpack_from("<II", mbuf, 0xA0)
                tgt = resolve_agent_ptr(pr, mgr, tgt_id1, tgt_id2)
                dmg1 = struct.unpack_from("<f", mbuf, 0x44)[0]
                spd = struct.unpack_from("<f", mbuf, 0x54)[0]
                arc = struct.unpack_from("<f", mbuf, 0x8C)[0]
                tgt_tid = fourcc_str(pr.u32(tgt + 0x30)) if tgt else "?"
                tgt_arm = pr.f32(tgt + 0xE0) if tgt else 0.0
                tgt_dtp = pr.u32(tgt + 0xE4) if tgt else 0
                tgt_hp = read_unit_life(pr, mgr, tgt) if tgt else 0.0
                obs_windup = round(now - windup_start, 4) if windup_start > 0 and (now - windup_start) < 1.2 else None
                active_missiles[m] = {
                    "t_spawn": now, "tgt": tgt, "tgt_tid": tgt_tid,
                    "dmg1": dmg1, "spd": spd, "arc": arc,
                    "tgt_arm": tgt_arm, "tgt_dtp": tgt_dtp,
                    "hp_spawn": tgt_hp, "hp_prev": tgt_hp,
                    "obs_windup": obs_windup, "windup_rem0": round(windup_rem0, 4),
                }
            else:
                info = active_missiles[m]
                if info["tgt"]:
                    hp_cur = read_unit_life(pr, mgr, info["tgt"])
                    if hp_cur is not None:
                        info["hp_prev"] = hp_cur

        # Check disappeared missiles (= impacted!)
        for m in list(active_missiles.keys()):
            if m not in seen_now:
                info = active_missiles.pop(m)
                flight = round(now - info["t_spawn"], 4)
                time.sleep(0.015)
                hp_after = read_unit_life(pr, mgr, info["tgt"]) if info["tgt"] else None
                hp_drop = round(info["hp_prev"] - hp_after, 3) if (info["hp_prev"] is not None and hp_after is not None) else None
                arm_mult = calc_armor_mult(info["tgt_arm"], neg_tbl)
                tp_mult = dmg_tbl[6][info["tgt_dtp"]] if info["tgt_dtp"] < 8 else 1.0
                pred_dmg = round(info["dmg1"] * arm_mult * tp_mult, 3)
                ev = {
                    "target": info["tgt_tid"],
                    "raw_missile_dmg": round(info["dmg1"], 3),
                    "missile_speed": round(info["spd"], 1),
                    "target_armor": round(info["tgt_arm"], 3),
                    "target_defType": info["tgt_dtp"],
                    "arm_mult": round(arm_mult, 5),
                    "tp_mult": round(tp_mult, 3),
                    "pred_dmg": pred_dmg,
                    "hp_before": round(info["hp_prev"], 3) if info["hp_prev"] is not None else None,
                    "hp_after": round(hp_after, 3) if hp_after is not None else None,
                    "actual_hp_drop": hp_drop,
                    "obs_windup_s": info["obs_windup"],
                    "timer_windup_s": info["windup_rem0"],
                    "obs_flight_s": flight,
                }
                events.append(ev)
                print(f"HIT {ev['target']:4s} | raw={ev['raw_missile_dmg']:5.2f} arm={ev['target_armor']:.1f}(dt={ev['target_defType']}) | pred={ev['pred_dmg']:6.2f} actual_drop={str(ev['actual_hp_drop']):>6s} | windup={ev['obs_windup_s']}s(tmr={ev['timer_windup_s']}s) flight={ev['obs_flight_s']}s spd={ev['missile_speed']}")
        time.sleep(0.01)

    out_path = os.path.join(os.path.dirname(__file__), "live_verify_results.json")
    json.dump({"sample_units": sample_units, "dmg_tbl": dmg_tbl, "neg_tbl": neg_tbl, "events": events}, open(out_path, "w"), indent=2)
    print(f"\nSaved {len(events)} hit events to {out_path}")
    pr.close()

if __name__ == "__main__":
    main()
