# -*- coding: utf-8 -*-
"""
全 11 个版本 G2/G3 精准提取脚本：
- 通过 flags 拼装指令 `and r32, 0x100` (25 00 01 00 00 或 81 E0..E7 00 01 00 00) 定位全部 11 个版本的
  SendUnitOrder_0x10 / 0x11 / 0x12，并追踪它们调用的 EnqueueOrder_0x10 / 0x11 / 0x12，
  再通过交叉引用找出同时调用 Send_0x11 与 Send_0x12 的 UI_PointDispatch 点地分流函数！
"""
import json
import re
import struct
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g2_g3_all11.txt"
OUT_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g2_g3_all11.json"


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


def find_send_cluster(pe: PE32):
    """定位 6~7 个连续排列的 SendUnitOrder_* 函数簇"""
    text = pe.get_section(".text")
    blob = pe.raw[text.raw_ptr : text.raw_ptr + text.raw_size]
    # 搜 00 01 00 00 前一字节是 0x25 或前两字节是 0x81 0xE0..0xE7
    hits = []
    pos = 0
    while True:
        idx = blob.find(b"\x00\x01\x00\x00", pos)
        if idx < 0:
            break
        is_and = (idx >= 1 and blob[idx - 1] == 0x25) or (idx >= 2 and blob[idx - 2] == 0x81 and 0xE0 <= blob[idx - 1] <= 0xE7)
        if is_and:
            # 附近 [-0x30, +0x45] 内必须有 shr reg, 10h (C1 E8..EF 10) 和 shr reg, 12h (C1 E8..EF 12)
            win = blob[max(0, idx - 0x20) : idx + 0x45]
            has_10 = any(bytes([0xC1, r, 0x10]) in win for r in range(0xE8, 0xF0))
            has_12 = any(bytes([0xC1, r, 0x12]) in win for r in range(0xE8, 0xF0))
            if has_10 and has_12:
                hits.append(text.vaddr + idx)
        pos = idx + 1
    return hits


def find_enq_and_bounds(pe: PE32, hit_rva: int):
    """给定 hit_rva (and reg, 100h)，向后找最后一个 call (EnqueueOrder) 和 ret N，向前找前一个 ret/CC 后的函数头"""
    off = pe.rva_to_off(hit_rva)
    # 向后最多 0x60 字节找 C2 xx 00 (ret N)
    tail = pe.raw[off : off + 0x60]
    m_ret = re.search(rb"\xC2[\x04-\x24]\x00", tail)
    end_rel = m_ret.start() if m_ret else len(tail)
    # 在 [0, end_rel] 中找最后一个 E8 call
    enq_rva = None
    for i in range(end_rel - 5, -1, -1):
        if tail[i] == 0xE8:
            rel = struct.unpack_from("<i", tail, i + 1)[0]
            cand = hit_rva + i + 5 + rel
            if 0x1000 <= cand < pe.image_size:
                enq_rva = cand
                break
    # 向前最多 0xC0 字节找函数头（优先 CC 边界，其次前一个 ret N / ret 后的紧邻字节）
    back_len = 0xC0
    head = pe.raw[off - back_len : off]
    fn_rva = None
    for i in range(len(head) - 1, 2, -1):
        if head[i - 1] == 0xCC and head[i] != 0xCC:
            fn_rva = hit_rva - (len(head) - i)
            break
        if head[i - 3] == 0xC2 and head[i - 1] == 0x00 and head[i] in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0xA1):
            fn_rva = hit_rva - (len(head) - i)
            break
        if head[i - 1] == 0xC3 and head[i] in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0xA1):
            fn_rva = hit_rva - (len(head) - i)
            break
    ret_imm = tail[m_ret.start() + 1] if m_ret else 0
    return fn_rva, enq_rva, ret_imm


def identify_order_type(pe: PE32, enq_rva: int, ret_imm: int):
    """通过 EnqueueOrder 函数体中的包类型立即数 (0x10..0x15) 精准识别"""
    if not enq_rva:
        return "?"
    off = pe.rva_to_off(enq_rva)
    if off is None:
        return "?"
    body = pe.raw[off : off + 0xD0]
    for code in [0x10, 0x11, 0x12, 0x13, 0x14, 0x15]:
        if struct.pack("<I", 0x000A0000 | code) in body:
            return f"0x{code:02X}"
    # 1.0.17~1.21.0: 搜 mov word/byte [esp/ebp+..], 10h..15h 或 push 10h..15h (6A 10..15)
    for code in [0x10, 0x11, 0x12, 0x13, 0x14, 0x15]:
        if re.search(rb"\x66\xC7[\x40-\x7F].{1,2}" + bytes([code, 0x00]), body):
            return f"0x{code:02X}"
    for code in [0x10, 0x11, 0x12, 0x13, 0x14, 0x15]:
        if bytes([0x6A, code]) in body:
            return f"0x{code:02X}"
    return f"?(ret=0x{ret_imm:X})"


def main():
    lines = []
    all_data = {}
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        hits = find_send_cluster(pe)
        items = []
        by_type = {}
        for h in hits:
            fn, enq, rimm = find_enq_and_bounds(pe, h)
            t = identify_order_type(pe, enq, rimm)
            items.append((fn, enq, rimm, t))
            if t in ("0x10", "0x11", "0x12", "0x13") and t not in by_type:
                by_type[t] = (fn, enq)
        # 找 UI_PointDispatch_0x11_0x12 (同时调用 Send_0x11 与 Send_0x12，且距离 < 0x80)
        pairs = []
        if "0x11" in by_type and "0x12" in by_type and by_type["0x11"][0] and by_type["0x12"][0]:
            c11 = find_rel32_callers(pe, by_type["0x11"][0])
            c12 = find_rel32_callers(pe, by_type["0x12"][0])
            for a in c11:
                for b in c12:
                    if 0 < abs(b - a) < 0x80:
                        pairs.append((f"0x{a:X}", f"0x{b:X}"))
        rec = {
            "image_base": f"0x{pe.image_base:X}",
            "Send_0x10": f"0x{by_type['0x10'][0]:X}" if "0x10" in by_type and by_type["0x10"][0] else None,
            "Send_0x11": f"0x{by_type['0x11'][0]:X}" if "0x11" in by_type and by_type["0x11"][0] else None,
            "Send_0x12": f"0x{by_type['0x12'][0]:X}" if "0x12" in by_type and by_type["0x12"][0] else None,
            "Enq_0x10": f"0x{by_type['0x10'][1]:X}" if "0x10" in by_type and by_type["0x10"][1] else None,
            "Enq_0x11": f"0x{by_type['0x11'][1]:X}" if "0x11" in by_type and by_type["0x11"][1] else None,
            "Enq_0x12": f"0x{by_type['0x12'][1]:X}" if "0x12" in by_type and by_type["0x12"][1] else None,
            "UI_PointDispatch_pairs": pairs,
            "all_hits": [(f"0x{f:X}" if f else None, f"0x{e:X}" if e else None, f"0x{r:X}", t) for f, e, r, t in items],
        }
        all_data[ver] = rec
        lines.append(
            f"{ver:13s} | Snd10={str(rec['Send_0x10']):9s} Snd11={str(rec['Send_0x11']):9s} Snd12={str(rec['Send_0x12']):9s} | "
            f"Enq10={str(rec['Enq_0x10']):9s} Enq11={str(rec['Enq_0x11']):9s} Enq12={str(rec['Enq_0x12']):9s} | Pairs={len(pairs)} {pairs[:2]}"
        )
        if not pairs:
            lines.append(f"  detail: {rec['all_hits'][:6]}")

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
