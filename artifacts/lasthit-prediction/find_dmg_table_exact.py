# -*- coding: utf-8 -*-
"""补齐 1.21.0 与 1.22~1.26 的 DamageBonus 7x8 表基址 RVA（追踪 GetDamageBonusSpells 的调用者）"""
import re
import struct
import sys

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for


def find_str_push(pe, s):
    off = pe.raw.find(s + b"\x00")
    srva = pe.off_to_rva(off)
    sva = pe.image_base + srva
    pat = b"\x68" + struct.pack("<I", sva)
    idx = pe.raw.find(pat)
    return pe.off_to_rva(idx) if idx >= 0 else None


def find_callers(pe, func_rva):
    """查找 .text 段中所有 E8 rel32 调用 func_rva 的位置"""
    sec = pe.get_section(".text")
    start, end = sec.raw_ptr, sec.raw_ptr + sec.raw_size
    out = []
    pos = start
    while True:
        idx = pe.raw.find(b"\xE8", pos, end)
        if idx < 0:
            break
        if idx + 5 <= end:
            rel = struct.unpack_from("<i", pe.raw, idx + 1)[0]
            call_rva = pe.off_to_rva(idx)
            if call_rva + 5 + rel == func_rva:
                out.append(call_rva)
        pos = idx + 1
    return out


for ver in ALL_VERSIONS:
    pe = PE32(dll_path_for(ver))
    ref = find_str_push(pe, b"DamageBonusSpells")
    if ver in ("1.0.17.5988", "1.0.20.6048", "1.20.4.6074", "1.21.0.6263"):
        lns = disasm(pe.path, pe.image_base, ref, 0x25)
        tbl = None
        for ln in lns:
            m = re.search(r"mov\s+dword ptr \[.*?\+([0-9A-F]{8})h\],eax", ln)
            if m:
                tbl = int(m.group(1), 16) - pe.image_base
                break
        print(f"{ver:14s} | inline loader @ 0x{ref:06X} | TableBase(Row0) = {hex(tbl) if tbl else '—'}")
    elif ver == "1.27.0.52240":
        # 1.27: lea esi,[edi+40h]; mov [esi+6FBEC328h],eax -> Row0 = 0xBEC328 + 0x40 = 0xBEC368
        print(f"{ver:14s} | inline loader @ 0x{ref:06X} | TableBase(Row0) = 0xBEC368 (base 0xBEC328 + 0x40)")
    else:
        # 1.22 ~ 1.26: ref 位于小包装函数内（func_start = ref - 2），经 .rdata 函数指针表调用
        func_rva = ref - 2
        func_va = pe.image_base + func_rva
        # 先找指向 func_va 的函数指针表项
        ptr_rvas = pe.find_all_bytes(struct.pack("<I", func_va))
        tbl = None
        caller_rva = None
        for pr in ptr_rvas:
            # 找引用该函数指针表地址的指令
            refs_to_tbl = pe.find_all_bytes(struct.pack("<I", pe.image_base + pr), ".text")
            if refs_to_tbl:
                caller_rva = refs_to_tbl[0]
                lns = disasm(pe.path, pe.image_base, max(0x1000, caller_rva - 0x20), 0x80)
                for ln in lns:
                    m = re.search(r"mov\s+dword ptr \[.*?\+([0-9A-F]{8})h\],", ln)
                    if m:
                        r = int(m.group(1), 16) - pe.image_base
                        if r > 0x900000:
                            tbl = r
                            break
                if tbl:
                    break
        print(f"{ver:14s} | helper 0x{func_rva:06X} ptr={hex(ptr_rvas[0]) if ptr_rvas else '—':10s} caller={hex(caller_rva) if caller_rva else '—':10s} | TableBase(Row0) = {hex(tbl) if tbl else '—'}")
