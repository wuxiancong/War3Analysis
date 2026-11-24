# -*- coding: utf-8 -*-
"""
完成 G2 + G3 全部 11 个版本 RVA 提取 + 1.27 CAbilityChannel / CAbilityBlink / CAbilityTornado 虚表核验：
1. 1.27 通过 FourCC 'ANcl' / 'AEbl' / 'ANto' 工厂注册点定位虚表，反汇编 GetOrderFlags (+0x30C)
2. 修正 1.22~1.26 的 SendUnitOrder_* 函数入口并提取 UI_PointDispatch (0x11 vs 0x12 NULL 分流点)
3. 通过 flags 拼装特征字节码 (shr reg, 10h; and reg, 20h; shr reg, 12h; and reg, 4) 直接扫描 1.0.17~1.21.0 全部早期版本！
"""
import json
import re
import struct
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g2_g3_complete.txt"
OUT_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g2_g3_complete.json"


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


def find_func_start_strict(pe: PE32, rva: int, max_back: int = 0x140) -> int:
    """精确找函数入口：兼容 MSVC 2003 (无 CC 填充，直接 ret/ret N 后紧跟函数) 与 MSVC 2015 (CC 填充)"""
    off = pe.rva_to_off(rva)
    if off is None:
        return rva
    # 从 rva 往前找最近的函数边界（ret / ret imm16 / int3 后的非 int3 字节）
    # 先找 55 8B EC 或 8B 44 24 / 8B 54 24 / 53 / 56 / 83 EC
    start = max(0, off - max_back)
    chunk = pe.raw[start:off]
    # 1. 如果存在 CC 边界，找最后一个 CC 后的第一字节
    for i in range(len(chunk) - 1, 0, -1):
        if chunk[i - 1] == 0xCC and chunk[i] != 0xCC:
            # 确认后面不是跳表数据，而是常见序言
            if chunk[i] in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0x6A, 0xA1, 0x33, 0x8D):
                return rva - (len(chunk) - i)
    # 2. 否则找 C2 xx 00 (ret imm16) 或 C3 (ret) 后的第一字节
    for i in range(len(chunk) - 1, 2, -1):
        if chunk[i - 3] == 0xC2 and chunk[i - 1] == 0x00 and chunk[i] in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0x6A, 0xA1):
            return rva - (len(chunk) - i)
        if chunk[i - 1] == 0xC3 and chunk[i] in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0x6A, 0xA1):
            return rva - (len(chunk) - i)
    return rva


def scan_flags_packing_senders(pe: PE32):
    """
    所有版本（1.0.17~1.27）的 SendUnitOrder_0x10 / 0x11 / 0x12 / 0x13 / 0x14 / 0x15
    都连续排列在 .text 中，且都包含同一段 flags 位拼装特征：
    and reg, 100h + (shr reg, 10h; and reg, 20h) + (shr reg, 12h; and reg, 4)
    """
    text = pe.get_section(".text")
    blob = pe.raw[text.raw_ptr : text.raw_ptr + text.raw_size]
    # 搜 25 00 01 00 00 (and eax, 100h) 或 81 E? 00 01 00 00
    hits = []
    for pat in [b"\x25\x00\x01\x00\x00", b"\x81\xE1\x00\x01\x00\x00", b"\x81\xE2\x00\x01\x00\x00"]:
        pos = 0
        while True:
            idx = blob.find(pat, pos)
            if idx < 0:
                break
            window = blob[idx : idx + 0x45]
            # 确认附近有 shr 10h/12h 和 and 20h / and 4
            if (b"\xC1\xE8\x10" in window or b"\xC1\xE9\x10" in window or b"\xC1\xEA\x10" in window or b"\xC1\xEB\x10" in window) and (
                b"\xC1\xE9\x12" in window or b"\xC1\xE8\x12" in window or b"\xC1\xEA\x12" in window or b"\xC1\xEC\x12" in window or b"\xC1\xED\x12" in window or b"\xC1\xEE\x12" in window
            ):
                rva = text.vaddr + idx
                fn = find_func_start_strict(pe, rva, 0xD0)
                # 找到函数末尾的 call rel32 (调用 EnqueueOrder_*)
                fn_off = pe.rva_to_off(fn)
                fchunk = pe.raw[fn_off : fn_off + 0x110]
                # 找 idx 之后的第一个 E8 call
                rel_after = (rva - fn)
                e8 = fchunk.find(b"\xE8", rel_after)
                enq_rva = None
                if e8 >= 0 and e8 + 5 <= len(fchunk):
                    rel = struct.unpack_from("<i", fchunk, e8 + 1)[0]
                    enq_rva = fn + e8 + 5 + rel
                hits.append((fn, enq_rva))
            pos = idx + 1
    # 按函数地址排序去重
    seen = set()
    uniq = []
    for fn, enq in sorted(hits):
        if fn not in seen:
            seen.add(fn)
            uniq.append((fn, enq))
    return uniq


def classify_enqueue(pe: PE32, enq_rva: int) -> str:
    """根据 EnqueueOrder 函数体中的立即数判断是 0x10 / 0x11 / 0x12 / 0x13 / 0x14 / 0x15"""
    if not enq_rva:
        return "?"
    off = pe.rva_to_off(enq_rva)
    if off is None:
        return "?"
    body = pe.raw[off : off + 0xA0]
    for code in [0x10, 0x11, 0x12, 0x13, 0x14, 0x15]:
        # 1.22~1.27: 0x000A0010..0x000A0015 或 mov word [..], 0x10..0x15
        if struct.pack("<I", 0x000A0000 | code) in body:
            return f"0x{code:02X}"
        if bytes([0x66, 0xC7, 0x45]) in body and bytes([code, 0x00]) in body:
            # 再精确查 66 C7 45 xx <code> 00 或 66 C7 44 24 xx <code> 00
            pass
    # 早期版本 (1.0.17~1.21.0)：检查 push 10h/11h/12h 或 mov word/byte [..], 10h..15h
    for code in [0x10, 0x11, 0x12, 0x13, 0x14, 0x15]:
        if re.search(rb"\x66\xC7[\x40-\x7F].{1,2}" + bytes([code, 0x00]), body):
            return f"0x{code:02X}"
        if bytes([0xC7, 0x44, 0x24]) in body and struct.pack("<I", 0x000A0000 | code) in body:
            return f"0x{code:02X}"
    # 也可能是 mov byte ptr [esp+..], 10h..15h 或 push 10h..15h
    for code in [0x10, 0x11, 0x12, 0x13, 0x14, 0x15]:
        if re.search(rb"\xC6\x44\x24." + bytes([code]), body):
            return f"0x{code:02X}"
        if re.search(rb"\xC6\x45." + bytes([code]), body):
            return f"0x{code:02X}"
    return "?"


def probe_127_ability_flags(lines):
    dll = dll_path_for("1.27.0.52240")
    pe = PE32(dll)
    base = pe.image_base
    lines.append("=== 1. 1.27 CAbilityChannel (ANcl) / CAbilityBlink (AEbl) / CAbilityTornado (ANto) GetOrderFlags (+0x30C) ===")
    for fourcc in ["ANcl", "AEbl", "ANto", "AIrg"]:
        val = struct.unpack(">I", fourcc.encode("ascii"))[0]
        hits = pe.find_all_bytes(struct.pack("<I", val), ".text")
        lines.append(f"  FourCC '{fourcc}' (0x{val:08X}) .text hits: {[hex(h) for h in hits[:8]]}")
        # 工厂函数里通常有 push 'ANcl'; push <ctor_va> 或 mov [reg], vtable
        for h in hits[:4]:
            asm = disasm(dll, base, max(0, h - 0x10), 0x35)
            # 找附近的工厂回调 VA
            for l in asm:
                if "push" in l or "mov" in l or "call" in l:
                    lines.append("    " + l)


def main():
    lines = []
    probe_127_ability_flags(lines)

    lines.append("\n=== 2. 全部 11 个版本 SendUnitOrder_0x10/0x11/0x12 + EnqueueOrder_0x10/0x11/0x12 + UI_PointDispatch ===")
    all_data = {}
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        senders = scan_flags_packing_senders(pe)
        by_type = {}
        # 按顺序也记录下来（War3 中这组 6 个函数顺序固定：0x10, 0x11, 0x13, 0x12, 0x14, 0x15 或 0x10, 0x11, 0x12...）
        seq_info = []
        for fn, enq in senders:
            t = classify_enqueue(pe, enq)
            seq_info.append((f"0x{fn:X}", f"0x{enq:X}" if enq else None, t))
            if t != "?" and t not in by_type:
                by_type[t] = (fn, enq)
        # 找 UI_PointDispatch (同时调用了 Send_0x11 和 Send_0x12 的相邻对)
        pairs = []
        if "0x11" in by_type and "0x12" in by_type:
            c11 = find_rel32_callers(pe, by_type["0x11"][0])
            c12 = find_rel32_callers(pe, by_type["0x12"][0])
            for a in c11:
                for b in c12:
                    if 0 < b - a < 0x60:
                        pairs.append((f"0x{a:X}", f"0x{b:X}"))
        rec = {
            "image_base": f"0x{pe.image_base:X}",
            "Send_0x10": f"0x{by_type['0x10'][0]:X}" if "0x10" in by_type else None,
            "Send_0x11": f"0x{by_type['0x11'][0]:X}" if "0x11" in by_type else None,
            "Send_0x12": f"0x{by_type['0x12'][0]:X}" if "0x12" in by_type else None,
            "Enq_0x10": f"0x{by_type['0x10'][1]:X}" if "0x10" in by_type and by_type["0x10"][1] else None,
            "Enq_0x11": f"0x{by_type['0x11'][1]:X}" if "0x11" in by_type and by_type["0x11"][1] else None,
            "Enq_0x12": f"0x{by_type['0x12'][1]:X}" if "0x12" in by_type and by_type["0x12"][1] else None,
            "UI_PointDispatch_pairs": pairs,
            "raw_senders": seq_info,
        }
        all_data[ver] = rec
        lines.append(
            f"  {ver:13s} | Snd10={str(rec['Send_0x10']):9s} Snd11={str(rec['Send_0x11']):9s} Snd12={str(rec['Send_0x12']):9s} | "
            f"Enq10={str(rec['Enq_0x10']):9s} Enq11={str(rec['Enq_0x11']):9s} Enq12={str(rec['Enq_0x12']):9s} | "
            f"Pairs={len(pairs)} {pairs[:2]}"
        )
        if not pairs:
            lines.append(f"    raw_senders: {seq_info}")

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
