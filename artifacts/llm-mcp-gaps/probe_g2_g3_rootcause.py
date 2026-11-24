# -*- coding: utf-8 -*-
"""
深挖 G2+G3 根因：
1. 反汇编 0x3A4B00..0x3A4D00，确认 cmp [ebp-24h], 2 的来源（TargetType 枚举值！）
2. 反汇编 0x30ADA0 往下，找到 0x11 和 0x12 收包后最终执行的虚函数/处理器（看 0x11 vs 0x12 及 flags 0x04 的区别）
"""
from pe_util import PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\probe_g2_g3_rootcause.txt"


def main():
    dll = dll_path_for("1.27.0.52240")
    pe = PE32(dll)
    base = pe.image_base
    lines = []

    def log(s=""):
        lines.append(s)

    log("=== 1. 0x3A4B20..0x3A4CE0 (确定 [ebp-24h] 及 [edi+14h] 来源) ===")
    lines.extend(disasm(dll, base, 0x3A4B20, 0x1C0))

    log("\n=== 2. 0x30ADA0..0x30AF00 (NetCommand 投递) ===")
    lines.extend(disasm(dll, base, 0x30ADA0, 0x160))

    # 检查 1.27 中 CNetCommandUnitOrderTargetPoint (0x11) 和 CNetCommandUnitOrderTargetObject (0x12) 在执行时按 ActionId 0x11 / 0x12 分发的位置
    # 在 War3 引擎里，执行队列消费 CNetCommand 时通常调用 CGameWar3::ProcessNetCommand，里面 switch (cmd->type) 0x10..0x15
    # 我们也可以搜 0x6F986D88 (vt_Point) 和 0x6F986D94 (vt_Target) 的所有引用，或搜 cmp eax, 11h / 12h
    # 先看 0x30ADA0 调了什么，顺藤摸瓜
    log("\n=== 3. 0x3A1140..0x3A12D5 (另一处 cmp [ebp+8], 2) ===")
    lines.extend(disasm(dll, base, 0x3A1140, 0x195))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT}")


if __name__ == "__main__":
    main()
