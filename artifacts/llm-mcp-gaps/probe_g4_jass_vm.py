# -*- coding: utf-8 -*-
"""
探查 G4：1.27 Game.dll JASS VM 全局变量表指针链（以 EL0 / XS 为例）
策略：
1. 定位 1.27 ExecuteFunc 原生函数（它按字符串查当前 JASS VM 的符号表！）
2. 定位 1.27 JassThreadLocal (TlsGetValue) -> JassEnv -> VirtualMachine -> SymbolTable / GlobalTable
3. 反汇编 JASS VM 查全局变量与数组元素取值 (OP_GETVAR / OP_GETARRAY) 的精确偏移！
"""
import re
import struct
from pe_util import PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\probe_g4_127.txt"


def find_native(pe: PE32, name: str):
    text = pe.get_section(".text")
    tblob = pe.raw[text.raw_ptr : text.raw_ptr + text.raw_size]
    for srva in pe.find_string_rvas(name):
        sva = pe.image_base + srva
        pat = struct.pack("<I", sva)
        pos = 0
        while True:
            idx = tblob.find(pat, pos)
            if idx < 0:
                break
            # 原生注册通常在附近 -5 或 +5 有函数指针
            for delta in [-5, 5, -10, 10]:
                if 0 <= idx + delta <= len(tblob) - 4:
                    cand = struct.unpack_from("<I", tblob, idx + delta)[0]
                    if pe.image_base < cand < pe.image_base + 0x900000:
                        return cand - pe.image_base
            pos = idx + 1
    return None


def main():
    dll = dll_path_for("1.27.0.52240")
    pe = PE32(dll)
    base = pe.image_base
    lines = []

    def log(s=""):
        lines.append(s)

    for nm in ["ExecuteFunc", "GetLocalPlayer", "TriggerAddAction"]:
        rva = find_native(pe, nm)
        log(f"=== Native {nm} @ {hex(rva) if rva else None} ===")
        if rva:
            lines.extend("  " + l for l in disasm(dll, base, rva, 0x90))

    # 搜索 "InitGlobals" 字符串引用（加载 war3map.j 后调 InitGlobals 初始化全局变量表）
    log("\n=== String 'InitGlobals' xrefs ===")
    for srva in pe.find_string_rvas("InitGlobals"):
        xrefs = pe.find_xrefs_to_va(base + srva)
        log(f"  str @ 0x{srva:X} -> xrefs {[hex(x) for x in xrefs]}")
        for x in xrefs[:2]:
            lines.extend("  " + l for l in disasm(dll, base, max(0, x - 0x40), 0xA0))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT}")


if __name__ == "__main__":
    main()
