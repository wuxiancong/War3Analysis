# -*- coding: utf-8 -*-
"""扫描全部 11 个 War3 版本中 0x16/0x17/0x18/0x19/0x1A/0x1B 选择/编队 NetCommand 虚表与 Execute RVA，
并反汇编 1.27 的 0x16 Execute 核实是否会打断英雄 COrder，同时补全 6.83d 中立野怪属性。"""
import os
import re
import struct
import subprocess
import sys

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32

VERSIONS_DIR = r"D:\Qt\workspace\War3Launcher\versions"
OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\helm-dominate\selection_all11_rva.txt"
DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Tools\MSVC\14.29.30133\bin\Hostx64\x86\dumpbin.exe"
if not os.path.exists(DUMPBIN):
    for root in [
        r"C:\Program Files\Microsoft Visual Studio",
        r"C:\Program Files (x86)\Microsoft Visual Studio",
    ]:
        if os.path.exists(root):
            for dp, _, fns in os.walk(root):
                if "dumpbin.exe" in fns and "x86" in dp.lower():
                    DUMPBIN = os.path.join(dp, "dumpbin.exe")
                    break

RTTI_CLASSES = [
    ("0x16_SelMod", b".?AVCNetCommandUnitSelectionModify@@"),
    ("0x17_DefGrp", b".?AVCNetCommandUnitDefineControlGroup@@"),
    ("0x18_SelGrp", b".?AVCNetCommandUnitSelectControlGroup@@"),
    ("0x19_SubGrp", b".?AVCNetCommandUnitSelectSubGroup@@"),
    ("0x1A_RefSub", b".?AVCNetCommandUnitRefreshSubGroup@@"),
    ("0x1B_SelEvt", b".?AVCNetCommandUnitSelectionEvent@@"),
]


def find_vtable_by_rtti(pe: PE32, rtti_bytes: bytes):
    """通过 MSVC 32-bit RTTI TypeDescriptor -> CompleteObjectLocator -> vtable[-1] 定位虚表 RVA。"""
    raw = pe.raw
    pos = raw.find(rtti_bytes)
    if pos < 0:
        return None
    # TypeDescriptor 头部为 pVFTable(4) + spare(4) + name[]
    td_off = pos - 8
    td_rva = pe.off_to_rva(td_off)
    if td_rva is None:
        return None
    td_va = pe.image_base + td_rva
    td_pat = struct.pack("<I", td_va)
    # 在数据段搜索指向 td_va 的 CompleteObjectLocator (offset +12)
    start = 0
    while True:
        hit = raw.find(td_pat, start)
        if hit < 0:
            break
        start = hit + 1
        col_off = hit - 12
        if col_off < 0:
            continue
        sig, offset, cd_off = struct.unpack_from("<III", raw, col_off)
        if sig != 0 or offset != 0 or cd_off != 0:
            continue
        col_rva = pe.off_to_rva(col_off)
        if col_rva is None:
            continue
        col_va = pe.image_base + col_rva
        col_pat = struct.pack("<I", col_va)
        vt_hit = raw.find(col_pat)
        if vt_hit >= 0:
            vt_rva = pe.off_to_rva(vt_hit + 4)
            if vt_rva is not None:
                return vt_rva
    return None


def read_vt_slots(pe: PE32, vt_rva: int, n=8):
    off = pe.rva_to_off(vt_rva)
    if off is None:
        return []
    slots = []
    for i in range(n):
        va = struct.unpack_from("<I", pe.raw, off + i * 4)[0]
        slots.append(va - pe.image_base if va > pe.image_base else 0)
    return slots


def dump_func(dll_path: str, image_base: int, rva: int, size: int = 0x120):
    if not os.path.exists(DUMPBIN):
        return f"(dumpbin not found)"
    start_va = image_base + rva
    end_va = start_va + size
    cmd = [DUMPBIN, "/DISASM:NOBYTES", f"/RANGE:0x{start_va:X},0x{end_va:X}", dll_path]
    res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return res.stdout


def parse_neutral_creeps():
    """从 DotA 6.83d 解包后的 SLK 与 war3map.w3u 提取中立野怪属性。"""
    base = r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map"
    bal_path = os.path.join(base, "Units_UnitBalance.slk")
    wep_path = os.path.join(base, "Units_UnitWeapons.slk")

    def load_slk(path):
        rows = {}
        headers = {}
        cur_y = 0
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.startswith("C;"):
                    continue
                mx = re.search(r"X(\d+)", line)
                my = re.search(r"Y(\d+)", line)
                mk = re.search(r";K(.*)", line)
                if my:
                    cur_y = int(my.group(1))
                if not mx or not mk:
                    continue
                x = int(mx.group(1))
                val = mk.group(1).strip().strip('"')
                if cur_y == 1:
                    headers[x] = val
                else:
                    rows.setdefault(cur_y, {})[headers.get(x, str(x))] = val
        by_id = {}
        for r in rows.values():
            uid = r.get("unitBalanceID") or r.get("unitWeapID")
            if uid:
                by_id[uid] = r
        return by_id

    bal = load_slk(bal_path)
    wep = load_slk(wep_path)

    # 同时读取 war3map.w3u 中被地图修改过的字段 (HP/spd/rng/def)
    w3u_path = os.path.join(base, "war3map.w3u")
    w3u_overrides = {}
    if os.path.exists(w3u_path):
        raw = open(w3u_path, "rb").read()
        off = 4  # version
        for table_idx in range(2):
            if off + 4 > len(raw):
                break
            cnt = struct.unpack_from("<I", raw, off)[0]
            off += 4
            for _ in range(cnt):
                orig = raw[off:off+4].decode("ascii", "ignore")
                new = raw[off+4:off+8].decode("ascii", "ignore")
                off += 8
                uid = new if new.strip("\x00") else orig
                mcnt = struct.unpack_from("<I", raw, off)[0]
                off += 4
                ov = w3u_overrides.setdefault(uid, {"_orig": orig})
                for _m in range(mcnt):
                    fid = raw[off:off+4].decode("ascii", "ignore")
                    vtype = struct.unpack_from("<I", raw, off+4)[0]
                    off += 8
                    if vtype == 0:
                        val = struct.unpack_from("<i", raw, off)[0]
                        off += 4
                    elif vtype in (1, 2):
                        val = round(struct.unpack_from("<f", raw, off)[0], 2)
                        off += 4
                    elif vtype == 3:
                        z = raw.find(b"\x00", off)
                        val = raw[off:z].decode("utf-8", "ignore")
                        off = z + 1
                    else:
                        break
                    off += 4  # end marker
                    ov[fid] = val

    creeps = [
        ("nfsh", "丘陵巨魔牧师 (Hill Troll Priest)"),
        ("ndtr", "黑暗巨魔 (Dark Troll)"),
        ("ndtw", "黑暗巨魔召唤法师 (Dark Troll Summoner)"),
        ("nhrr", "鹰身女妖风暴巫师 (Harpy Stormcrafter)"),
        ("ngst", "鬼魂 (Ghost)"),
        ("nsth", "萨特苦难使者 (Satyr Tormenter)"),
        ("nstl", "萨特窃魂者 (Satyr Mindstealer)"),
        ("nsty", "萨特放逐者 (Satyr Banisher)"),
        ("ncen", "半人马征服者 (Centaur Conqueror)"),
        ("nowk", "枭兽撕裂者 (Wildwing Ripper)"),
        ("nwlg", "头狼 (Alpha Wolf)"),
        ("nplg", "熊怪粉碎者 (Hellbear Smasher)"),
        ("nkol", "狗头人监工 (Kobold Foreman)"),
        ("ngrk", "泥土傀儡 (Mud Golem - 魔免)"),
    ]
    lines = ["=== 4. DotA 6.83d 中立野怪完整属性 (SLK + w3u 覆盖) ==="]
    for uid, name in creeps:
        b = bal.get(uid, {})
        w = wep.get(uid, {})
        ov = w3u_overrides.get(uid, {})
        hp = ov.get("uhpm", b.get("HP", "?"))
        spd = ov.get("umvs", b.get("spd", "?"))
        df = ov.get("udef", b.get("def", "?"))
        rng = ov.get("ua1r", w.get("rangeN1", "?"))
        wt = ov.get("ua1w", w.get("weapTp1", "?"))
        mana = ov.get("umpm", b.get("manaN", "?"))
        abil = ov.get("uabi", "")
        lines.append(
            f"  {uid:<5} | {name:<36} | HP={str(hp):>4} (+250) | MP={str(mana):>3} | spd={str(spd):>3} | def={str(df):>2} | rng={str(rng):>3} ({wt}) | abil={abil}"
        )
    return lines


def main():
    versions = sorted(
        d for d in os.listdir(VERSIONS_DIR)
        if os.path.isfile(os.path.join(VERSIONS_DIR, d, "Game.dll"))
    )
    out = []
    out.append("=== 1. 全部 11 版本 0x16~0x1B 选择/编队 NetCommand 虚表与 Execute RVA ===")
    hdr = f"{'Version':<14} | {'0x16 vt':<10} | {'0x16 vt+08':<10} | {'0x16 vt+14':<10} | {'0x17 vt':<10} | {'0x18 vt':<10} | {'0x19 vt':<10} | {'0x1A vt':<10} | {'0x1B vt':<10}"
    out.append(hdr)
    out.append("-" * len(hdr))

    r127_0x16_slots = None
    r127_0x19_slots = None
    r127_base = None
    r127_dll = None

    for ver in versions:
        dll = os.path.join(VERSIONS_DIR, ver, "Game.dll")
        pe = PE32(dll)
        vts = {}
        for key, rtti in RTTI_CLASSES:
            vts[key] = find_vtable_by_rtti(pe, rtti)
        slots16 = read_vt_slots(pe, vts["0x16_SelMod"], 8) if vts["0x16_SelMod"] else []
        if ver == "1.27.0.52240":
            r127_0x16_slots = slots16
            r127_0x19_slots = read_vt_slots(pe, vts["0x19_SubGrp"], 8) if vts["0x19_SubGrp"] else []
            r127_base = pe.image_base
            r127_dll = dll

        def fmt(v):
            return f"0x{v:06X}" if v else "—"

        s08 = slots16[2] if len(slots16) > 2 else 0
        s14 = slots16[5] if len(slots16) > 5 else 0
        out.append(
            f"{ver:<14} | {fmt(vts['0x16_SelMod']):<10} | {fmt(s08):<10} | {fmt(s14):<10} | "
            f"{fmt(vts['0x17_DefGrp']):<10} | {fmt(vts['0x18_SelGrp']):<10} | {fmt(vts['0x19_SubGrp']):<10} | "
            f"{fmt(vts['0x1A_RefSub']):<10} | {fmt(vts['0x1B_SelEvt']):<10}"
        )

    out.append("")
    out.append("=== 2. 1.27.0.52240 CNetCommandUnitSelectionModify (0x16) 虚表槽位 ===")
    if r127_0x16_slots:
        for i, s in enumerate(r127_0x16_slots):
            out.append(f"  vt+0x{i*4:02X}: 0x{s:06X}")
        out.append("--- Disasm 0x16 vt+0x08 (Execute?) ---")
        out.append(dump_func(r127_dll, r127_base, r127_0x16_slots[2], 0x140))
        out.append("--- Disasm 0x16 vt+0x14 ---")
        out.append(dump_func(r127_dll, r127_base, r127_0x16_slots[5], 0x100))

    out.append("=== 3. 1.27.0.52240 CNetCommandUnitSelectSubGroup (0x19) 虚表槽位 ===")
    if r127_0x19_slots:
        for i, s in enumerate(r127_0x19_slots):
            out.append(f"  vt+0x{i*4:02X}: 0x{s:06X}")
        out.append("--- Disasm 0x19 vt+0x08 ---")
        out.append(dump_func(r127_dll, r127_base, r127_0x19_slots[2], 0x100))

    out.append("")
    out.extend(parse_neutral_creeps())

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"Wrote {len(out)} lines to {OUT_PATH}")


if __name__ == "__main__":
    main()
