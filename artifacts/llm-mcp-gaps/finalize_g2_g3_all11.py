# -*- coding: utf-8 -*-
"""
收尾 G2/G3 全 11 版精准 RVA 表：
区分 Send_0x12_PointAndTarget (ret 0x1C，点地目标为空时发 0x12 + FFFFFFFF FFFFFFFF)
与 Send_0x12_TargetOnly (ret 0x14)，补齐 1.0.17~1.21.0 的 Send_0x10/0x11/0x12 入口与全部 11 版的 UI_PointDispatch 分流点！
"""
import json
import struct
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

IN_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g2_g3_all11.json"
OUT_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g2_g3_final11.json"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g2_g3_final11.txt"


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


def find_fn_start_by_ret_or_cc(pe: PE32, call_site: int, max_back: int = 0x100):
    off = pe.rva_to_off(call_site)
    start = max(0, off - max_back)
    chunk = pe.raw[start:off]
    # 优先找 CC 边界，再找 C2 xx 00 / C3 边界，或 55 8B EC
    for i in range(len(chunk) - 1, 2, -1):
        if chunk[i - 1] == 0xCC and chunk[i] != 0xCC and chunk[i] in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0xA1, 0xD9):
            return call_site - (len(chunk) - i)
        if chunk[i - 3] == 0xC2 and chunk[i - 1] == 0x00 and chunk[i] in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0xA1, 0xD9):
            return call_site - (len(chunk) - i)
        if chunk[i - 1] == 0xC3 and chunk[i] in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0xA1, 0xD9):
            return call_site - (len(chunk) - i)
    return call_site


def main():
    raw_data = json.load(open(IN_JSON, encoding="utf-8"))
    out = {}
    lines = []
    hdr = f"{'Version':13s} | {'Send_0x10':9s} | {'Send_0x11':9s} | {'Send_0x12_XY':12s} | {'Enq_0x10':9s} | {'Enq_0x11':9s} | {'Enq_0x12_XY':11s} | {'UI_PointDispatch (0x11 / 0x12_NULL)'}"
    lines.append(hdr)
    lines.append("-" * 125)

    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        hits = raw_data[ver]["all_hits"]
        # hits 顺序里：ret=0x10 -> 0x10; ret=0x18 -> 0x11; ret=0x1C -> 0x12_XY (点地+目标)
        enq10 = enq11 = enq12_xy = None
        snd10 = snd11 = snd12_xy = None
        for fn_s, enq_s, rimm_s, t in hits:
            if t == "0x10" and enq10 is None:
                enq10 = int(enq_s, 16)
                snd10 = int(fn_s, 16) if fn_s else None
            elif t == "0x11" and enq11 is None:
                enq11 = int(enq_s, 16)
                snd11 = int(fn_s, 16) if fn_s else None
            elif t == "0x12" and rimm_s == "0x1C":
                enq12_xy = int(enq_s, 16)
                snd12_xy = int(fn_s, 16) if fn_s else None

        # 如果 1.0.17~1.21.0 的 snd11 / snd12_xy 为 None，直接从 enq11 / enq12_xy 的唯一调用者反推！
        for label, enq, cur in [("10", enq10, snd10), ("11", enq11, snd11), ("12", enq12_xy, snd12_xy)]:
            if cur is None and enq is not None:
                cs = find_rel32_callers(pe, enq)
                if cs:
                    fn = find_fn_start_by_ret_or_cc(pe, cs[0], 0x120)
                    if label == "10":
                        snd10 = fn
                    elif label == "11":
                        snd11 = fn
                    else:
                        snd12_xy = fn
        # 1.0.17~1.21.0 校准 snd10 (刚才 0x140855 是 ret 后，验证一下 callers)
        if snd10 and not find_rel32_callers(pe, snd10):
            # 往前找对齐的函数入口 (最多 0x20)
            for d in range(0, 0x20):
                if find_rel32_callers(pe, snd10 - d):
                    snd10 = snd10 - d
                    break

        # 找 UI_PointDispatch_0x11_0x12 (同一函数内紧邻调用 Send_0x11 和 Send_0x12_XY)
        pairs = []
        if snd11 and snd12_xy:
            c11 = find_rel32_callers(pe, snd11)
            c12 = find_rel32_callers(pe, snd12_xy)
            for a in c11:
                for b in c12:
                    if 0 < abs(b - a) < 0x80:
                        pairs.append((f"0x{a:X}", f"0x{b:X}"))

        out[ver] = {
            "Send_0x10": f"0x{snd10:X}" if snd10 else None,
            "Send_0x11": f"0x{snd11:X}" if snd11 else None,
            "Send_0x12_XY": f"0x{snd12_xy:X}" if snd12_xy else None,
            "Enq_0x10": f"0x{enq10:X}" if enq10 else None,
            "Enq_0x11": f"0x{enq11:X}" if enq11 else None,
            "Enq_0x12_XY": f"0x{enq12_xy:X}" if enq12_xy else None,
            "UI_PointDispatch_pairs": pairs,
        }
        lines.append(
            f"{ver:13s} | {str(out[ver]['Send_0x10']):9s} | {str(out[ver]['Send_0x11']):9s} | {str(out[ver]['Send_0x12_XY']):12s} | "
            f"{str(out[ver]['Enq_0x10']):9s} | {str(out[ver]['Enq_0x11']):9s} | {str(out[ver]['Enq_0x12_XY']):11s} | {len(pairs)} {pairs[:3]}"
        )

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
