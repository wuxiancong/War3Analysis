# -*- coding: utf-8 -*-
"""
单线程轻量核验：
1. 1.27 EnqueuePlayerAction (0x840BBB 所在函数) 与锁步回合队列/时间步长结构
2. 1.27 hold (0xD0019 @ 0x5E0EFF / 0x5E18E3 / 0x5E2F9C) 验证带坐标 0x11/0x12 是否忽略坐标
3. 1.27 CheckGoalReached (0x11B060) 反汇编确认到达判定容差公式
4. 全 11 版本关键 RVA 交叉核验（EnqueuePlayerAction / CAbilityMove OrderCheck / StepTurnAndMove）
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\inplace-turn\net_and_orders_all11.txt")

# 来自 war3hook_offsets.cpp L2238-2244 的 EnqueuePlayerAction hook 点 RVA
ENQUEUE_HOOK_RVA = {
    "1.0.17.5988": 0x6D5332,
    "1.0.20.6048": 0x6D5832,
    "1.20.4.6074": 0x6D6172,
    "1.21.0.6263": 0x6DA192,
    "1.22.0.6328": 0x640562,
    "1.23.0.6352": 0x6421E2,
    "1.24.1.6374": 0x650BD2,
    "1.24.4.6387": 0x650C82,
    "1.25.1.6397": 0x6502B2,
    "1.26.0.6401": 0x6504E2,
    "1.27.0.52240": 0x840BBB,
}


def main():
    pe127 = PE32(dll_path_for("1.27.0.52240"))
    out = []

    # 1. 1.27 EnqueuePlayerAction 附近反汇编
    out.append("=== 1. 1.27 EnqueuePlayerAction 附近 @ 0x840B90 ===")
    out.extend(disasm(pe127.path, pe127.image_base, 0x840B90, 0x70))

    # 2. 1.27 hold (0xD0019) 处理函数 0x5E0EE0 / 0x5E18C0 / 0x5E2F80
    for rva in (0x5E0EE0, 0x5E18C0, 0x5E2F80):
        out.append(f"\n=== 2. 1.27 hold (0xD0019) handler around 0x{rva:06X} ===")
        out.extend(disasm(pe127.path, pe127.image_base, rva, 0x55))

    # 3. 1.27 CheckGoalReached @ 0x11B060（看到达容差 glr +0xB0 单位与比较公式）
    out.append("\n=== 3. 1.27 CPoPosCl::CheckGoalReached @ 0x11B060 ===")
    out.extend(disasm(pe127.path, pe127.image_base, 0x11B060, 0xA0))

    # 4. 全 11 版本 CAbilityMove::IsMoveOrder (cmp eax, 0xD0019; je; cmp eax, 0xD0012; je; cmp eax, 0xD0016)
    # 特征：3D 19 00 0D 00 ... 3D 12 00 0D 00
    out.append("\n=== 4. 全部 11 版本 EnqueuePlayerAction & CAbilityMove(0xD0019/12/16) RVA ===")
    out.append(f"{'Version':14s} | {'EnqueueHook':11s} | {'MoveOrderChk':12s} | {'HoldHandler':11s}")
    out.append("-" * 60)
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        eh = ENQUEUE_HOOK_RVA[ver]
        # 找 cmp eax, 0xD0019 (3D 19 00 0D 00)
        hits = pe.find_all_bytes(b"\x3D\x19\x00\x0D\x00", ".text")
        mchk = hits[0] - 6 if len(hits) >= 1 else None
        hh = hits[-1] if len(hits) >= 2 else None
        fm = f"0x{mchk:06X}" if mchk else "—"
        fh = f"0x{hh:06X}" if hh else "—"
        out.append(f"{ver:14s} | 0x{eh:06X}    | {fm:12s} | {fh:11s}")

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(out)} lines to {OUT}")


if __name__ == "__main__":
    main()
