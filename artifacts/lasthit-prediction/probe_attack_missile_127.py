# -*- coding: utf-8 -*-
"""
1. 核验 1.27 常量 0xB593EC / 0xB593BC（确认 0.5f 重置）与 +0x6C/+0x70 写入时机
2. 扫描全 11 版 CAbilityAttack 虚表与关键偏移（验证全部 11 版是否一致）
3. 探查 1.27 CMissile (vt 0x9B07D0) 的发射点偏移 (launchX/Y/Z)、到达判定半径、伤害结算帧时机！
"""
import json, re, struct, sys
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-prediction\probe_attack_missile_127.txt"


def main():
    pe = PE32(dll_path_for("1.27.0.52240"))
    base = pe.image_base
    lines = []
    def log(s=""):
        lines.append(s)

    log("=== 1. 1.27 +0x1D8 重置浮点常量 ===")
    for rva in [0xB593EC, 0xB593BC]:
        raw = pe.read_u32_rva(rva)
        val = struct.unpack("<f", struct.pack("<I", raw))[0]
        log(f"  0x{base+rva:X} (RVA 0x{rva:X}) = {val!r} (0x{raw:08X})")

    log("\n=== 2. 1.27 CAbilityAttack 写 +0x6C/+0x70 (target1/target2) 位置 ===")
    # 搜 89 xx 6C 或 C7 xx 6C 在 [0x474000..0x482000]
    s_off, e_off = pe.rva_to_off(0x474000), pe.rva_to_off(0x482000)
    chunk = pe.raw[s_off:e_off]
    hits_6c = []
    for m in re.finditer(rb"\x89[\x40-\x7F]\x6C", chunk):
        rva = 0x474000 + m.start()
        if rva > 0x474B00:
            hits_6c.append(rva)
    log(f"  mov [reg+6Ch], reg hits: {[hex(x) for x in hits_6c]}")
    for h in hits_6c[:4]:
        log(f"  --- around 0x{h:X} ---")
        lines.extend("    " + l for l in disasm(pe.path, base, h - 0x25, 0x55))

    log("\n=== 3. 1.27 CMissile (vt 0x9B07D0) 虚表槽与更新/命中函数 ===")
    vt = 0x9B07D0
    slots = []
    for i in range(24):
        fn = pe.read_u32_rva(vt + i * 4)
        if fn and base < fn < base + 0x1000000:
            slots.append((i * 4, fn - base))
    log("  CMissile vtable slots: " + ", ".join(f"+0x{o:X}=0x{f:X}" for o, f in slots[:16]))
    # 搜指向 CMissile vtable (0x6F9B07D0) 的构造函数
    cx = pe.find_xrefs_to_va(base + vt, ".text")
    log(f"  CMissile vtable .text xrefs: {[hex(x) for x in cx]}")

    # 检查 CMissile 的 Tick/Update 函数（通常在 0x4C0000..0x4E0000 或 vt 槽内）
    # 打印几个关键虚函数（排除简单的 ret/GetClassId）
    seen = set()
    for off, fn in slots:
        if fn in seen:
            continue
        seen.add(fn)
        asm = disasm(pe.path, base, fn, 0x30)
        if len(asm) >= 10:
            log(f"  --- CMissile vt+0x{off:X} @ 0x{fn:X} (head) ---")
            lines.extend("    " + l for l in asm[:14])

    log("\n=== 4. 全 11 版 CAbilityAttack 虚表与关键函数验证 ===")
    for ver in ALL_VERSIONS:
        pv = PE32(dll_path_for(ver))
        vts = pv.find_rtti_vtables(".?AVCAbilityAttack@@")
        vt_s = hex(vts[0]) if vts else None
        # 如果无 RTTI (1.0.17~1.21.0)，用 'Aatk' (0x4161746B) 找
        if not vts:
            ah = pv.find_all_bytes(struct.pack("<I", 0x4161746B), ".text")
            for h in ah:
                for d in range(0, 6):
                    xs = pv.find_all_bytes(struct.pack("<I", pv.image_base + h - d), ".rdata")
                    if xs:
                        vt_s = hex(xs[0] - 0x1C)
                        break
                if vt_s:
                    break
        # 验证构造函数里是否有 +0x1D8 / +0x1EC / +0x200
        ctor_s = None
        if vt_s:
            v_int = int(vt_s, 16)
            xs = pv.find_xrefs_to_va(pv.image_base + v_int, ".text")
            if xs:
                ctor_s = hex(xs[0])
        log(f"  {ver:13s} | CAbilityAttack_vt={str(vt_s):10s} | ctor_xref={str(ctor_s):10s}")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT}")
    for l in lines[:30]:
        print(l)
    print("--- All 11 versions ---")
    for l in lines[-13:]:
        print(l)


if __name__ == "__main__":
    main()
