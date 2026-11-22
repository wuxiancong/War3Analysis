# -*- coding: utf-8 -*-
r"""补齐并逐版反汇编验证 11 个版本的 SetTargetController / m_targetUnit / HasTargetController / SetMode / PopMode"""
import os
import re
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

VER_ROOT = r"D:\Qt\workspace\War3Launcher\versions"
OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\camera-lock-targeting\all_versions_part2.txt"

KNOWN = {
    "1.0.17.5988":  (0x2DD570, 0x0FEB60, 0x1B4),
    "1.0.20.6048":  (0x2DD570, 0x0FEB60, 0x1B4),
    "1.20.4.6074":  (0x2DD690, 0x0FEB70, 0x1B4),
    "1.21.0.6263":  (0x2E0C60, 0x0FEB90, 0x1B4),
    "1.22.0.6328":  (0x3C5DF0, 0x306D30, 0x1B4),
    "1.23.0.6352":  (0x3C7B10, 0x308270, 0x1B4),
    "1.24.1.6374":  (0x3CE1E0, 0x308330, 0x1B4),
    "1.24.4.6387":  (0x3CE2A0, 0x3083F0, 0x1B4),
    "1.25.1.6397":  (0x3CD530, 0x307680, 0x1B4),
    "1.26.0.6401":  (0x3CD760, 0x3078B0, 0x1B4),
    "1.27.0.52240": (0x1F42F0, 0x346440, 0x1B4),
}

def main():
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    lines = []
    lines.append(f"{'版本':<13} | {'SetTgtCtrl':>10} | {'tgtU':>4} | {'HasTgtCtrl':>10} | {'xref':>4} | {'SetMode':>8} | {'PopMode':>8}")
    lines.append("-" * 78)
    for ver, (nat_tgt, sp, curm) in KNOWN.items():
        dll = os.path.join(VER_ROOT, ver, "game.dll")
        if not os.path.exists(dll):
            dll = os.path.join(VER_ROOT, ver, "Game.dll")
        pe = pefile.PE(dll, fast_load=True)
        data = pe.__data__
        img = pe.OPTIONAL_HEADER.ImageBase
        sz = pe.OPTIONAL_HEADER.SizeOfImage
        t = pe.sections[0]
        tbuf = data[t.PointerToRawData:t.PointerToRawData + t.SizeOfRawData]
        t_rva, t_sz = t.VirtualAddress, t.SizeOfRawData

        # 1. 从 SetCameraTargetController 原生取最后一个 call（在 SetPosition 附近 ±0x20000）
        o_nat = pe.get_offset_from_rva(nat_tgt)
        calls_nat = []
        for ins in md.disasm(data[o_nat:o_nat + 0x90], img + nat_tgt):
            if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
                tr = int(ins.op_str, 16) - img
                if 0x1000 <= tr < sz:
                    calls_nat.append(tr)
            if ins.mnemonic.startswith("ret"):
                break
        # 在 SetPosition 内找 push 0; push 0; ... call SetTargetController(0)
        stc = None
        for c in reversed(calls_nat):
            if abs(c - sp) < 0x10000:
                stc = c
                break
        if stc is None:
            o_sp = pe.get_offset_from_rva(sp)
            for ins in md.disasm(data[o_sp:o_sp + 0x70], img + sp):
                if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
                    tr = int(ins.op_str, 16) - img
                    if abs(tr - sp) < 0x10000 and tr != sp:
                        # 选带 5 个参数 (ret 0x14) 的那个
                        o_c = pe.get_offset_from_rva(tr)
                        if any(x.mnemonic == "ret" and x.op_str == "0x14" for x in md.disasm(data[o_c:o_c + 0x120], img + tr)):
                            stc = tr
                            break

        tgtU = None
        if stc:
            o_stc = pe.get_offset_from_rva(stc)
            for ins in md.disasm(data[o_stc:o_stc + 0x120], img + stc):
                m = re.search(r"\[e(?:si|di|bx|bp) \+ (0x4[048])\]", ins.op_str)
                if m and "ebp +" not in ins.op_str:
                    tgtU = int(m.group(1), 16)
                    break

        # 2. HasTargetController: 在 SetPosition ±0x10000 找 0x2B61676C，向上找函数头（前1字节 CC/90/C3）且前 12 字节内读 [ecx/esi + tgtU]
        htc = None
        xrefs = []
        if tgtU is not None:
            lo = max(t_rva, sp - 0x10000)
            hi = min(t_rva + t_sz, sp + 0x10000)
            sub = data[pe.get_offset_from_rva(lo):pe.get_offset_from_rva(hi)]
            tag = struct.pack("<I", 0x2B61676C)
            p = 0
            while True:
                i = sub.find(tag, p)
                if i < 0:
                    break
                for back in range(0x34, 6, -1):
                    pos = i - back
                    if pos > 0 and sub[pos - 1] in (0xCC, 0x90, 0xC3) and sub[pos] not in (0xCC, 0x90):
                        # 反汇编前 6 条指令，检查是否读 [+ tgtU] 且短函数返回 0/1
                        cand_rva = lo + pos
                        ins_h = list(md.disasm(sub[pos:pos + 0x58], img + cand_rva))
                        if any(f"+ 0x{tgtU:x}]" in x.op_str for x in ins_h[:5]) and any(x.mnemonic == "ret" for x in ins_h):
                            htc = cand_rva
                            break
                if htc:
                    break
                p = i + 1

        setm, popm = None, None
        if htc:
            for idx in range(0, t_sz - 5):
                if tbuf[idx] == 0xE8:
                    rel = struct.unpack_from("<i", tbuf, idx + 1)[0]
                    if (t_rva + idx + 5 + rel) == htc:
                        xrefs.append(t_rva + idx)
            for xr in xrefs:
                o = pe.get_offset_from_rva(xr)
                ins_x = list(md.disasm(data[o:o + 0x45], img + xr))
                saw_p1 = False
                for ins in ins_x:
                    if ins.mnemonic == "push" and ins.op_str == "1":
                        saw_p1 = True
                    elif saw_p1 and ins.mnemonic == "call" and ins.op_str.startswith("0x"):
                        cand = int(ins.op_str, 16) - img
                        if 0x1000 <= cand < sz:
                            o_sm = pe.get_offset_from_rva(cand)
                            ins_sm = list(md.disasm(data[o_sm:o_sm + 0x90], img + cand))
                            if any(f"0x{curm:x}" in x.op_str for x in ins_sm):
                                setm = cand
                                break
                if setm:
                    break

        if setm:
            stk = f"0x{curm + 8:x}"
            for idx in range(0, t_sz - 5):
                if tbuf[idx] == 0xE8:
                    rel = struct.unpack_from("<i", tbuf, idx + 1)[0]
                    if (t_rva + idx + 5 + rel) == setm:
                        xr = t_rva + idx
                        o = pe.get_offset_from_rva(xr)
                        fs = None
                        for b in range(4, 0x28):
                            if data[o - b - 1] in (0xCC, 0x90, 0xC3) and data[o - b] not in (0xCC, 0x90):
                                fs = xr - b
                                break
                        if fs:
                            o_p = pe.get_offset_from_rva(fs)
                            ins_p = list(md.disasm(data[o_p:o_p + 0x45], img + fs))
                            if any(x.mnemonic == "push" and x.op_str == "0" for x in ins_p[:8]) and any(stk in x.op_str for x in ins_p):
                                popm = fs
                                break

        s_stc = f"0x{stc:X}" if stc is not None else "未确认"
        s_tu = f"0x{tgtU:X}" if tgtU is not None else "未确认"
        s_htc = f"0x{htc:X}" if htc is not None else "未确认"
        s_sm = f"0x{setm:X}" if setm is not None else "未确认"
        s_pm = f"0x{popm:X}" if popm is not None else "未确认"
        lines.append(f"{ver:<13} | {s_stc:>10} | {s_tu:>4} | {s_htc:>10} | {len(xrefs):>4} | {s_sm:>8} | {s_pm:>8}")

    txt = "\n".join(lines)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)

if __name__ == "__main__":
    main()
