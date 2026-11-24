# -*- coding: utf-8 -*-
"""
查清 G2+G3 的最后两块拼图：
1. 0x3A4E88 / 0x3A4E98 跳转表：确定 targetTypeMask ([edi+0x14] & 0x3FF) 哪些值走 0x11，哪些走 0x12
2. 查找接收端处理 0x11 / 0x12 的代码（特别是 useslot 0xD0028..0xD002D 以及 abilityFlags bit 0x04 的校验）
"""
import struct
from pe_util import PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\probe_g2_g3_recv.txt"


def main():
    dll = dll_path_for("1.27.0.52240")
    pe = PE32(dll)
    base = pe.image_base
    lines = []

    def log(s=""):
        lines.append(s)

    log("=== 1. 0x3A4E88 跳转表与 0x3A4E98 索引表 (targetTypeMask = [edi+14h] & 3FFh) ===")
    jt = [pe.read_u32_rva(0x3A4E88 + i * 4) for i in range(4)]
    log("  jump targets: " + ", ".join(f"[{i}]=0x{t - base:X}" for i, t in enumerate(jt)))
    idx_off = pe.rva_to_off(0x3A4E98)
    idx_bytes = pe.raw[idx_off : idx_off + 0xFF]
    buckets = {}
    for delta, b in enumerate(idx_bytes):
        val = delta + 2
        if b < 4:
            buckets.setdefault(b, []).append(f"0x{val:X}")
    for b, vals in sorted(buckets.items()):
        log(f"  case {b} (-> 0x{jt[b]-base:X}): {vals[:20]} (total {len(vals)})")

    log("\n=== 2. 搜索 .text 中 0x000D0028 (useslot1) 的引用，定位物品使用执行逻辑 ===")
    hits = pe.find_all_bytes(struct.pack("<I", 0x000D0028), ".text")
    log(f"  0xD0028 hits: {[hex(h) for h in hits]}")
    for h in hits[:6]:
        log(f"  --- around 0x{h:X} ---")
        lines.extend("  " + l for l in disasm(dll, base, max(0, h - 0x40), 0xB0))

    log("\n=== 3. 反汇编 0x2760D0 (预检函数，在 0x3A4CB8 调用) 与 0x276530 (在 0x3A4CB1 调用) ===")
    lines.extend("  " + l for l in disasm(dll, base, 0x2760D0, 0x90))

    # 查找 0x11 和 0x12 真正执行函数：在 0x2FB980..0x2FBF00 中我们看到 0x10/0x11/0x12 的 CNetCommand 对象构造后调用 0x30ADA0
    # 搜 0x000A0011 和 0x000A0012 (CNetCommand msg id) 在 .text 中的引用，找到收包分发端！
    log("\n=== 4. 搜索 0x000A0011 / 0x000A0012 (CNetCommand 消息 ID) 的所有引用 ===")
    for tag in [0x000A0010, 0x000A0011, 0x000A0012]:
        hs = pe.find_all_bytes(struct.pack("<I", tag), ".text")
        log(f"  0x{tag:08X} hits: {[hex(x) for x in hs]}")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT}")


if __name__ == "__main__":
    main()
