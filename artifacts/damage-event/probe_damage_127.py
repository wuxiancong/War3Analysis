# -*- coding: utf-8 -*-
"""
轻量级追踪 1.27.0.52240 的伤害结算链与 EVENT_UNIT_DAMAGED 派发点：
1. 查找 GetEventDamage / GetEventDamageSource / UnitDamageTarget 原生函数入口并反汇编
2. 反汇编 CMissile::ApplyDamage (0x6B1500) 找到其调用的 CUnit 伤害核心函数
3. 核对 GetEventDamage 读哪个全局/事件对象偏移，反查写入者
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32, disasm, dll_path_for

OUT_DIR = Path(r"D:\Qt\workspace\War3Analysis\artifacts\damage-event")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def find_native_127(pe: PE32, name: str):
    """在 1.27 中查找原生函数注册：push sig; push name; push func; call RegisterNative 或 mov edx, name; mov ecx, func"""
    srvas = pe.find_string_rvas(name)
    for srva in srvas:
        sva = pe.image_base + srva
        # 1.27 注册模式：mov edx, sva (BA xx xx xx xx) 或 push sva (68 xx xx xx xx)
        for prefix in (b"\xBA", b"\x68"):
            refs = pe.find_all_bytes(prefix + struct.pack("<I", sva), ".text")
            for ref in refs:
                lns = disasm(pe.path, pe.image_base, max(0x1000, ref - 0x15), 0x30)
                for ln in lns:
                    # 匹配 mov ecx, 6Fxxxxxxh 或 push 6Fxxxxxxh（紧邻在 name 附近的 .text 函数地址）
                    m = re.search(r"\b(?:mov\s+ecx,|push)\s+([0-9A-F]{8})h", ln)
                    if m:
                        va = int(m.group(1), 16)
                        rva = va - pe.image_base
                        if rva != srva and 0x1000 < rva < 0x900000:
                            sec = pe.get_section(".text")
                            if sec and sec.vaddr <= rva < sec.vaddr + sec.vsize:
                                return rva, ref, lns
    return None, None, []


def main():
    pe = PE32(dll_path_for("1.27.0.52240"))
    out = []

    for name in ("GetEventDamage", "GetEventDamageSource", "UnitDamageTarget"):
        rva, ref, reg_lns = find_native_127(pe, name)
        out.append(f"=== {name} -> func=0x{rva:06X} (reg_ref=0x{ref:06X}) ===" if rva else f"=== {name} NOT FOUND ===")
        if rva:
            out.extend(disasm(pe.path, pe.image_base, rva, 0xA0))
        out.append("")

    # 同时反汇编 1.27 CMissile::ApplyDamage @ 0x6B1500（前 0x140 字节）
    out.append("=== 1.27 CMissile::ApplyDamage @ 0x6B1500 ===")
    out.extend(disasm(pe.path, pe.image_base, 0x6B1500, 0x140))

    p = OUT_DIR / "probe_damage_127.txt"
    p.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(out)} lines to {p}")


if __name__ == "__main__":
    main()
