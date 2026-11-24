# -*- coding: utf-8 -*-
"""
查找 1.27 中 CNetCommandUnitOrderTargetPoint (0x11) 和 CNetCommandUnitOrderTargetObject (0x12)
在接收端的真正执行函数（vtable 0x986D88 / 0x986D94 以及 CPlayerWar3 / CSelectionWar3 处理），
以及 flags bit 0x04 (0x44 vs 0x40) 的作用。
"""
import struct
from pe_util import PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\probe_g2_g3_exec.txt"


def main():
    dll = dll_path_for("1.27.0.52240")
    pe = PE32(dll)
    base = pe.image_base
    lines = []

    def log(s=""):
        lines.append(s)

    # 之前看到 0x305EE0 / 0x305FD0 / 0x305F40 是 vtable 0x986D7C / 0x986D88 / 0x986D94 的 slot+0x04 (dtor)
    # 看一下每个 vtable 附近的完整虚表条目，以及 0xA8420C / 0xA8426C / 0xA842D0 到底是什么（RTTI / 类描述？）
    # 更重要的是：搜 0x10 / 0x11 / 0x12 在 Order 执行层是怎么消费的：
    # 在 0x30AE00 附近是 NetEventQueue 分发！让我们搜 CNetCommandUnitOrderTargetPoint 的消息 ID 0xA0011 在 .rdata 或 .text 中的分发点
    # 或者搜索 0x6F044150 附近，或者看 0x30B000..0x30B200 (0x30ADE0 后半段，它是消息分发循环！)
    log("=== 1. 0x30AF00..0x30B180 (NetCommand 消费分发) ===")
    lines.extend(disasm(dll, base, 0x30AF00, 0x280))

    # 搜索 CNetCommandUnitOrder* 回调注册：看谁在 .text 里用了 0x000A0011 / 0x000A0012，或者看 0x2FBE30 (0x11 收包) 的调用者
    # 搜 0x6F2FBE30 和 0x6F2FBB30 在 .rdata / .text 中的引用（ActionId 跳表！）
    for name, rva in [("Handler_0x10", 0x2FB980), ("Handler_0x12", 0x2FBB30), ("Handler_0x11", 0x2FBE30)]:
        # 先找函数开头
        pass

    # 搜索 0x000D0028 (useslot1) 所在的 CAbilityInventory::OnOrder 或 CUnit::IssueOrder
    # 在 0x63AC50 附近我们看到了 test [eax+20h], 200h，看一下 0x63A000..0x63B500 里 CAbilityInventory 虚表
    log("\n=== 2. RTTI 查找 CAbilityInventory / CNetCommandUnitOrder ===")
    for pat in ["CAbilityInventory", "CAbilityItem", "CAbilitySpell", "CNetCommandUnitOrder"]:
        vts = pe.find_rtti_vtables(pat)
        log(f"  RTTI '{pat}': {[hex(v) for v in vts]}")

    # 查找 0x699F10 (0x10 入队) / 0x69A640 (0x11 入队) / 0x69A1F0 (0x12 入队) 里的实际序列化或入队目标
    log("\n=== 3. 0x69A1F0 (0x12 入队) 和 0x69A640 (0x11 入队) ===")
    lines.extend("  [0x69A1F0] " + l for l in disasm(dll, base, 0x69A1F0, 0x90))
    lines.extend("  [0x69A640] " + l for l in disasm(dll, base, 0x69A640, 0x90))

    # 查找处理 0x000A0011 / 0x000A0012 事件回调：搜索 0xA0011 或 0x11 在注册事件时的常数
    # 在 War3 里，CNetCommandUnitOrder* 继承自 CNetCommand，事件 ID 是 0x000A0010..0x000A0015 (即 'netc' 事件族)
    # 搜索 .text 中 push 0A0011h / push 0A0012h 或 cmp ..., 0A0011h
    log("\n=== 4. 搜索 .text / .rdata 中 0x000A0011 / 0x000A0012 ===")
    for tag in [0x000A0010, 0x000A0011, 0x000A0012]:
        h_text = pe.find_all_bytes(struct.pack("<I", tag), ".text")
        h_rdata = pe.find_all_bytes(struct.pack("<I", tag), ".rdata")
        log(f"  0x{tag:08X}: .text={[hex(x) for x in h_text]}, .rdata={[hex(x) for x in h_rdata]}")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT}")


if __name__ == "__main__":
    main()
