# -*- coding: utf-8 -*-
"""
独立离线核验脚本（阶段四）：
1. B5: 定位 1.27 Action 0x10/0x11/0x12 解析与执行函数，从机器码确认 abilityFlags bit 0x01 是否为 Shift Queue
2. A6: 定位 1.27 Action 0x6B (SyncStoredInteger) 处理函数与现有 hooker 钩子
3. B3: 确认信使加速技能 (speedburst) 与 n004/n018/n01C/n01G 身份 (Spirit Bear / Familiars?)
"""
import re
import struct
import subprocess
import pefile

DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.52.37025\bin\Hostx64\x64\dumpbin.exe"
DLL_127 = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-verify\offline_audit_part4.txt"


def disasm(dll, base, rva, sz):
    va1, va2 = base + rva, base + rva + sz
    res = subprocess.run([DUMPBIN, "/nologo", "/disasm", f"/range:0x{va1:X},0x{va2:X}", dll],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [ln.strip() for ln in res.stdout.splitlines() if re.match(r"^\s+[0-9A-F]{8}:", ln)]


def main():
    lines = []
    def log(s=""):
        lines.append(s)

    raw = open(DLL_127, "rb").read()
    pe = pefile.PE(DLL_127, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase

    # 1. 在 .rdata 中找 CNetCommandUnitOrderBasic 构造/表引用: 搜索 0x6F986D7C (vtable) 在 .text 中的引用
    log("=== 1. B5: CNetCommandUnitOrderBasic (vt 0x986D7C) / 0x10 处理器 ===")
    # 注意: 上次读 0x986D7C 看到的 slots 像对象工厂或小表; 让我们找 0x6F305EE0 附近的 NetCommand 执行函数
    # 更好方法: 在 1.27 中搜索 Action ID switch (0x10, 0x11, 0x12, 0x13) 或搜索 CNetCommandUnitOrderBasic 对应的 Execute
    # 检查 war3hook_ai.cpp 或 war3-unit-collision-and-repath.md 是否有 enqueue/dispatch 地址；直接搜 0x6F95214C (基类 CNetCommand vtable) 的引用
    # 也搜 0x000D0021 (dropitem) 或 0x000D0003 (smart) 或 CNetCommand 解析函数
    # 在 1.27 中，NetCommand 工厂表通常在 0x6FA8420C / 0x6FA8426C (注意上次 slots +0x08=0xA8420C, +0x14=0xA8426C!)
    for name, rva in [("Basic_slot04", 0x305EE0), ("TargetPoint_slot04", 0x305FD0)]:
        log(f"  [{name} @ 0x{rva:X}]")
        lines.extend("    " + l for l in disasm(DLL_127, base, rva, 0x30))

    # 搜索 .text 中引用 0x6F986D7C 或 0x6F986D88 的位置（构造函数或工厂）
    text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
    tblob = raw[text.PointerToRawData : text.PointerToRawData + text.SizeOfRawData]
    for label, va in [("vt_Basic", base + 0x986D7C), ("vt_Point", base + 0x986D88), ("vt_Target", base + 0x986D94)]:
        pat = struct.pack("<I", va)
        pos = tblob.find(pat)
        log(f"  xref {label} (0x{va:X}): {f'0x{text.VirtualAddress + pos:X}' if pos >= 0 else 'NONE'}")

    # 搜索真实 CNetCommandUnitOrderBasic 的另一个 vtable（多重继承/基类）: 搜索 0x6F305F40 的前驱函数或 0x304000..0x308000 中的 NetCommand 处理
    # 直接搜 0x10 / 0x11 / 0x12 的字节解析: 在 1.27 中 CNetData / Action 0x10 处理器会读 uint16 abilityFlags (word ptr [reg+1] 或 [reg+0Ch])
    # 搜 "SyncStoredInteger" 在 1.27 中的原生实现 (发 0x6B)
    log("\n=== 2. A6: 1.27 SyncStoredInteger 原生反汇编 ===")
    pos = raw.find(b"\x00SyncStoredInteger\x00")
    if pos >= 0:
        sva = base + pe.get_rva_from_offset(pos + 1)
        j = tblob.find(struct.pack("<I", sva))
        if j >= 0:
            # 找附近的 fn_va
            for delta in [-5, 5]:
                cand = struct.unpack_from("<I", tblob, j + delta)[0]
                if base < cand < base + 0x900000:
                    rva = cand - base
                    log(f"  SyncStoredInteger @ RVA 0x{rva:X}")
                    lines.extend("    " + l for l in disasm(DLL_127, base, rva, 0x80))
                    break

    # 搜索 1.27 IssueImmediateOrder / CUnit::IssueOrder 中的 Queue 标志 (test ..., 1)
    log("\n=== 3. B5: 1.27 IssueImmediateOrderById (验证内部 Order flags bit 0 = Queue) ===")
    pos = raw.find(b"\x00IssueImmediateOrderById\x00")
    if pos >= 0:
        sva = base + pe.get_rva_from_offset(pos + 1)
        j = tblob.find(struct.pack("<I", sva))
        if j >= 0:
            for delta in [-5, 5]:
                cand = struct.unpack_from("<I", tblob, j + delta)[0]
                if base < cand < base + 0x900000:
                    rva = cand - base
                    log(f"  IssueImmediateOrderById @ RVA 0x{rva:X}")
                    lines.extend("    " + l for l in disasm(DLL_127, base, rva, 0x60))
                    break

    # 搜索 war3hook_ipc.cpp 中 0x6B 处理
    log("\n=== 4. A6: War3Launcher/hooker 中 0x6B 现有处理 ===")
    import os
    for fn in os.listdir(r"D:\Qt\workspace\War3Launcher\hooker"):
        if fn.endswith((".cpp", ".h", ".inl")):
            fp = os.path.join(r"D:\Qt\workspace\War3Launcher\hooker", fn)
            for idx, ln in enumerate(open(fp, encoding="utf-8", errors="replace"), 1):
                if "0x6B" in ln or "0x6b" in ln or "SyncStored" in ln:
                    log(f"  {fn}:L{idx}: {ln.strip()[:120]}")

    pe.close()
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_TXT}")


if __name__ == "__main__":
    main()
