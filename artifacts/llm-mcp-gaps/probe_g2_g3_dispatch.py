# -*- coding: utf-8 -*-
"""
深入追踪 1.27 Game.dll 中 0x11 vs 0x12 的：
1. 构造与入队函数 (0x69FCD0, 0x69FEB0)
2. 谁调用了 0x3AE540 (发 0x11) 与 0x3AE660 (发 0x12) —— 找出玩家点地选 0x11 还是 0x12 的分支条件！
3. 收包执行函数 0x2FD710 (执行 0x11) 与 0x2FD650 (执行 0x12) —— 找出为什么 0x11+0x44 被忽略而 0x12+0x40 生效！
"""
import struct
from pe_util import PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\probe_g2_g3_dispatch.txt"


def find_rel32_callers(pe: PE32, target_rva: int):
    """在 .text 中搜索 E8 (call rel32) 指向 target_rva 的所有位置"""
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


def main():
    dll = dll_path_for("1.27.0.52240")
    pe = PE32(dll)
    base = pe.image_base
    lines = []

    def log(s=""):
        lines.append(s)

    log("=== 1. 0x69FCD0 (0x11) 和 0x69FEB0 (0x12) 构造函数 ===")
    lines.extend(disasm(dll, base, 0x69FCD0, 0x2B0))

    log("\n=== 2. 调用 0x3AE540 (发 0x11) / 0x3AE660 (发 0x12) / 0x3AE5D0 的位置 ===")
    for name, rva in [("Send_0x10_3AE4E0", 0x3AE4E0), ("Send_0x11_3AE540", 0x3AE540), ("Send_0x13_3AE5D0", 0x3AE5D0), ("Send_0x12_3AE660", 0x3AE660)]:
        callers = find_rel32_callers(pe, rva)
        log(f"  {name}: {[hex(c) for c in callers]}")
        for c in callers[:5]:
            log(f"    --- caller around 0x{c:X} ---")
            lines.extend("    " + l for l in disasm(dll, base, max(0, c - 0x80), 0xB0))

    log("\n=== 3. 收包执行 0x2FD5D0..0x2FD7A0 (0x10/0x11/0x12/0x13 执行分发) ===")
    lines.extend(disasm(dll, base, 0x2FD5D0, 0x1D0))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT}")


if __name__ == "__main__":
    main()
