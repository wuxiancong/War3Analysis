# -*- coding: utf-8 -*-
"""
探查 1.27 Game.dll 中 0x10 / 0x11 / 0x12 点地物品与技能命令的构造与发送路径（G2 + G3）：
1. 反汇编 CNetCommandUnitOrder* 构造与发送函数（0x3AE4E0 / 0x69FFA0 周边）
2. 定位 0x11 (TargetPoint) 与 0x12 (TargetObject) 序列化和反序列化/执行函数
3. 追踪玩家 UI 点击物品/技能对地释放时，究竟如何决定发 0x11 还是 0x12、flags 0x40 vs 0x44 的来源
"""
from pe_util import PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\probe_g2_g3_127.txt"


def main():
    dll = dll_path_for("1.27.0.52240")
    pe = PE32(dll)
    base = pe.image_base
    lines = []

    def log(s=""):
        lines.append(s)

    log("=== 1. 1.27 发送路径 0x3AE480..0x3AE800 ===")
    lines.extend(disasm(dll, base, 0x3AE480, 0x380))

    log("\n=== 2. 1.27 0x69FF80..0x6A0400 (CNetCommandUnitOrder* 构造与入队) ===")
    lines.extend(disasm(dll, base, 0x69FF80, 0x480))

    log("\n=== 3. 1.27 0x2FB980..0x2FBF50 (CNetCommandUnitOrder* 反序列化/执行) ===")
    lines.extend(disasm(dll, base, 0x2FB980, 0x5D0))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT}")


if __name__ == "__main__":
    main()
