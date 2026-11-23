# -*- coding: utf-8 -*-
"""
逆向 War3 1.27.0.52240 Game.dll 中 0x10 / 0x11 / 0x12 动作包的：
1. 客户端构造路径（含 abilityFlags 各位含义，如 0x01 / 0x04 / 0x40 / 0x44）
2. 模拟端（帧同步执行）反序列化与 Execute 分发路径
"""
import sys
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown\127_order_packets.txt"

pe = SimplePE32(DLL_PATH)
md = Cs(CS_ARCH_X86, CS_MODE_32)

def disasm(rva, size=0x160, stop_at_ret=False):
    code = pe.read_bytes(rva, size)
    lines = []
    for insn in md.disasm(code, pe.image_base + rva):
        lines.append(f"  0x{insn.address - pe.image_base:06X} ({insn.address:08X}): {insn.mnemonic:8s} {insn.op_str}")
        if stop_at_ret and insn.mnemonic in ("ret", "retn"):
            break
    return "\n".join(lines)

out = []
out.append("=== 1. RTTI 查找 CNetCommand* 虚表 ===")
for tname, vts in pe.find_rtti_vtables("CNetCommand"):
    if any(k in tname for k in ("Order", "Drop", "Unit", "Item", "Immediate", "Point", "Target", "Action")):
        vt_str = ", ".join(f"(off=0x{o:X}, vt=0x{v:06X})" for o, v in vts)
        out.append(f"  {tname}: {vt_str}")
        for o, vt in vts:
            if o == 0:
                funcs = []
                for i in range(10):
                    v = pe.read_u32(vt + i*4)
                    funcs.append(f"0x{v - pe.image_base:06X}" if v else "0")
                out.append("    vt[0..9]: " + ", ".join(funcs))

out.append("\n=== 2. 客户端动作包构造路径 0x3AE4E0 / 0x3AE5D0 / 0x69FFA0 ===")
for name, rva, sz in [
    ("ClientBuildOrder_0x3AE4E0", 0x3AE4E0, 0x100),
    ("ClientBuildOrder_0x3AE5D0", 0x3AE5D0, 0x160),
    ("CNetCommandUnitOrderBasic_0x69FFA0", 0x69FFA0, 0x180),
]:
    out.append(f"\n--- {name} @ 0x{rva:06X} ---")
    out.append(disasm(rva, sz, stop_at_ret=True))

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"Done. Wrote {len(out)} lines/blocks to {OUT_PATH}")
