# -*- coding: utf-8 -*-
"""
1. 核验 DotA 6.83d Units_AbilityData.slk 中 假眼(A2WH)/真眼(A2WI)/TP/飞鞋/跳刀(AIbk)/推推棒(A19M) 的基类与 DataB1/DataC1
2. 扫描全部 11 个版本 Game.dll 中：
   - EnqueueOrder_0x10 / 0x11 / 0x12（含 0x000A0010 / 0x000A0011 / 0x000A0012 与 0x69FFA0/0x69FCD0/0x69FEB0）
   - SendUnitOrder_0x10 / 0x11 / 0x12（含 flags 拼装位运算）
   - UI 点地分流点（cmp ..., 2 -> 0x11 vs 0x12 NULL）
"""
import json
import os
import re
import struct
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g2_g3_all_versions.txt"
OUT_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g2_g3_all_versions.json"


def find_rel32_callers(pe: PE32, target_rva: int):
    text = pe.get_section(".text")
    blob = pe.raw[text.raw_ptr : text.raw_ptr + text.raw_size]
    out = []
    pos = 0
    while True:
        idx = blob.find(b"\xE8", pos)
        if idx < 0:
            break
        if idx + 5 <= len(blob):
            rel = struct.unpack_from("<i", blob, idx + 1)[0]
            call_rva = text.vaddr + idx
            if call_rva + 5 + rel == target_rva:
                out.append(call_rva)
        pos = idx + 1
    return out


def find_func_start(pe: PE32, rva: int, max_back: int = 0x180) -> int:
    """向前扫描 55 8B EC 或 CC CC 边界定位函数入口"""
    off = pe.rva_to_off(rva)
    if off is None:
        return rva
    start = max(0, off - max_back)
    chunk = pe.raw[start:off]
    # 优先找 CC 后紧跟的 55 8B EC 或 6A FF 68
    best = None
    for pat in [b"\xCC\x55\x8B\xEC", b"\xCC\x6A\xFF\x68", b"\xCC\x83\xEC", b"\xCC\x53\x55", b"\xCC\x56\x8B"]:
        idx = chunk.rfind(pat)
        if idx >= 0:
            cand = rva - (len(chunk) - (idx + 1))
            if best is None or cand > best:
                best = cand
    if best is not None:
        return best
    # 退化找 55 8B EC
    idx = chunk.rfind(b"\x55\x8B\xEC")
    if idx >= 0:
        return rva - (len(chunk) - idx)
    return rva


def scan_slk_abilities():
    slk_path = r"D:\Qt\workspace\War3Analysis\artifacts\ability-orders\map\Units_AbilityData.slk"
    rows = {}
    cur_y = 0
    headers = {}
    for line in open(slk_path, "r", encoding="utf-8", errors="replace"):
        if not line.startswith("C;"):
            continue
        m_y = re.search(r"Y(\d+)", line)
        if m_y:
            cur_y = int(m_y.group(1))
        m_x = re.search(r"X(\d+)", line)
        m_k = re.search(r";K(.*)", line)
        if not m_x or not m_k:
            continue
        x = int(m_x.group(1))
        val = m_k.group(1).strip().strip('"')
        if cur_y == 1:
            headers[x] = val
        else:
            rows.setdefault(cur_y, {})[x] = val
    by_alias = {}
    for y, cols in rows.items():
        alias = cols.get(1)
        if alias:
            by_alias[alias] = {headers.get(x, str(x)): v for x, v in cols.items()}
    return by_alias


def scan_version(ver: str):
    dll = dll_path_for(ver)
    pe = PE32(dll)
    res = {"version": ver, "image_base": f"0x{pe.image_base:X}"}

    # 1. 通过 0x000A0010 / 0x000A0011 / 0x000A0012 (CNetCommand msg id) 定位 EnqueueOrder_* 和 RecvHandler_*
    for cmd_id, tag in [(0x000A0010, "0x10"), (0x000A0011, "0x11"), (0x000A0012, "0x12")]:
        hits = pe.find_all_bytes(struct.pack("<I", cmd_id), ".text")
        funcs = []
        for h in hits:
            fn = find_func_start(pe, h, 0x100)
            if fn not in funcs:
                funcs.append(fn)
        # 区分 EnqueueOrder (被 SendUnitOrder 调用，函数内有 mov word ptr [..], 0x10/0x11/0x12 且无 0xFFFFFFFF 初始反序列化模式)
        # 与 RecvHandler (函数内把 obj1/obj2 预设为 -1 然后调用反序列化)
        enq = []
        recv = []
        for fn in funcs:
            off = pe.rva_to_off(fn)
            body = pe.raw[off : off + 0x120]
            # RecvHandler 通常有 C6 45 .. 10/11/12 (mov byte ptr, 10h/11h/12h) 且有 3B .. (cmp eax, [esi+10h])
            # EnqueueOrder 通常有 66 C7 45 .. 10/11/12 00 (mov word ptr, 0010h/0011h/0012h) 或调用方是 SendUnitOrder
            callers = find_rel32_callers(pe, fn)
            if callers:
                enq.append((fn, callers))
            else:
                recv.append(fn)
        res[f"Enqueue_{tag}_cands"] = [f"0x{fn:X}" for fn, _ in enq]
        res[f"Recv_{tag}_cands"] = [f"0x{fn:X}" for fn in recv]
        # 找 SendUnitOrder_*: 它的特征是函数内含 `C1 E9 12` / `C1 E8 12` (shr reg, 12h) 和 `83 .. 04` (and reg, 4) — 即把 abilFlags bit 20 映到 0x04！
        send_fn = None
        enq_fn = None
        for fn, callers in enq:
            for c in callers:
                cfn = find_func_start(pe, c, 0x120)
                coff = pe.rva_to_off(cfn)
                cbody = pe.raw[coff : coff + 0x100]
                if b"\x00\x01\x00\x00" in cbody and (b"\xC1\xE8\x10" in cbody or b"\xC1\xE9\x12" in cbody or b"\xC1\xEA\x12" in cbody or b"\xC1\xE8\x12" in cbody):
                    send_fn = cfn
                    enq_fn = fn
                    break
            if send_fn:
                break
        res[f"EnqueueOrder_{tag}"] = f"0x{enq_fn:X}" if enq_fn else None
        res[f"SendUnitOrder_{tag}"] = f"0x{send_fn:X}" if send_fn else None

    # 2. 找 UI 点地分流点（同时调用了 SendUnitOrder_0x11 和 SendUnitOrder_0x12 的函数！）
    s11 = int(res["SendUnitOrder_0x11"], 16) if res["SendUnitOrder_0x11"] else None
    s12 = int(res["SendUnitOrder_0x12"], 16) if res["SendUnitOrder_0x12"] else None
    if s11 and s12:
        c11 = find_rel32_callers(pe, s11)
        c12 = find_rel32_callers(pe, s12)
        pairs = []
        for a in c11:
            for b in c12:
                if 0 < b - a < 0x50:
                    pairs.append((f"0x{a:X}", f"0x{b:X}"))
        res["UI_PointDispatch_0x11_0x12_pairs"] = pairs
    else:
        res["UI_PointDispatch_0x11_0x12_pairs"] = []

    return res


def main():
    lines = []
    lines.append("=== 1. DotA 6.83d Units_AbilityData.slk 关键物品技能 ===")
    by_alias = scan_slk_abilities()
    # 查假眼 A2WH, 真眼 A2WI, 跳刀 AIbk, 推推 A19M, TP/飞鞋 (查所有 code==ANto 或 AItp 或 AIte)
    for k in ["A2WH", "A2WI", "AIbk", "A19M", "A017", "A0FO", "A0H6", "A0H7"]:
        d = by_alias.get(k)
        if d:
            lines.append(f"  {k}: code={d.get('code')}, DataB1={d.get('DataB1')}, DataC1={d.get('DataC1')}, Rng1={d.get('Rng1')}, Cool1={d.get('Cool1')}, targs1={d.get('targs1')}")
        else:
            lines.append(f"  {k}: NOT FOUND in map Units_AbilityData.slk")
    lines.append("  --- 所有 code=ANto / AItp / AIte 的地图技能 ---")
    for k, d in by_alias.items():
        if d.get("code") in ("ANto", "AItp", "AIte"):
            lines.append(f"  {k}: code={d.get('code')}, DataA1={d.get('DataA1')}, DataB1={d.get('DataB1')}, Rng1={d.get('Rng1')}, Cool1={d.get('Cool1')}, targs1={d.get('targs1')}")

    lines.append("\n=== 2. 全部 11 个版本 Game.dll G2/G3 RVA 扫描 ===")
    all_res = {}
    for ver in ALL_VERSIONS:
        r = scan_version(ver)
        all_res[ver] = r
        lines.append(
            f"  {ver:13s} | Enq10={str(r['EnqueueOrder_0x10']):10s} Enq11={str(r['EnqueueOrder_0x11']):10s} Enq12={str(r['EnqueueOrder_0x12']):10s} | "
            f"Snd10={str(r['SendUnitOrder_0x10']):10s} Snd11={str(r['SendUnitOrder_0x11']):10s} Snd12={str(r['SendUnitOrder_0x12']):10s} | "
            f"Pairs={len(r['UI_PointDispatch_0x11_0x12_pairs'])} {r['UI_PointDispatch_0x11_0x12_pairs'][:2]}"
        )

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_res, f, indent=2, ensure_ascii=False)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
