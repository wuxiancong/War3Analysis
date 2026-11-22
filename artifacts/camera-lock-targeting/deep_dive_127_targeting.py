# -*- coding: utf-8 -*-
r"""
深度反汇编 1.27.0.52240 game.dll 中：
1. CTargetMode::OnWorldLBtn (0x3A6AF0) 后半段 + 0x3A62A0 (IssueTargetOrder) + 0x3A6760 (含 HasTargetController 调用 0x3A68A8)
2. CGameUI::PopMode (0x356E50) 与 CGameUI::SetMode (0x356AC0) 的全部调用点，检查镜头函数是否会取消选目标
3. CWorldFrameWar3 中发出 0x1A0064/0x1A0065/0x1A0066 的鼠标点击与射线取目标函数
4. CCameraWar3::Update (0x3474E0) 与 CCameraWar3::OnEvent (0x343DD0) 的滚屏/锁屏机制
输出到 D:\Qt\workspace\War3Analysis\artifacts\camera-lock-targeting\deep_dive_127.txt
"""
import os
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll"
OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\camera-lock-targeting\deep_dive_127.txt"

def main():
    pe = pefile.PE(DLL_PATH, fast_load=True)
    data = pe.__data__
    img = pe.OPTIONAL_HEADER.ImageBase
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    t_sec = pe.sections[0]
    t_off, t_rva, t_sz = t_sec.PointerToRawData, t_sec.VirtualAddress, t_sec.SizeOfRawData

    def off_of(rva): return pe.get_offset_from_rva(rva)

    def find_calls_to(target_rva):
        hits = []
        buf = data[t_off:t_off + t_sz]
        for i in range(0, t_sz - 5):
            op = buf[i]
            if op in (0xE8, 0xE9):
                rel = struct.unpack_from("<i", buf, i + 1)[0]
                cur_rva = t_rva + i
                if (cur_rva + 5 + rel) == target_rva:
                    hits.append(cur_rva)
        return hits

    def find_imm32(val, rva_lo, rva_hi):
        pat = struct.pack("<I", val)
        o0, o1 = off_of(rva_lo), off_of(rva_hi)
        buf = data[o0:o1]
        res, p = [], 0
        while True:
            i = buf.find(pat, p)
            if i < 0: break
            res.append(rva_lo + i)
            p = i + 1
        return res

    def find_func_start(rva, max_back=0x400):
        o = off_of(rva)
        for d in range(0, max_back):
            if o - d >= 2 and data[o - d - 1] == 0xCC and data[o - d] != 0xCC:
                return rva - d
        return max(0x1000, rva - 0x40)

    def disasm_range(rva, end_rva, max_insns=260):
        o = off_of(rva)
        code = data[o:o + max(16, end_rva - rva + 16)]
        lines = []
        for idx, ins in enumerate(md.disasm(code, img + rva)):
            crva = ins.address - img
            if crva >= end_rva or idx >= max_insns:
                break
            extra = ""
            if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
                try:
                    trva = int(ins.op_str, 16) - img
                    if 0 < trva < pe.OPTIONAL_HEADER.SizeOfImage:
                        extra = f" ; RVA 0x{trva:X}"
                except Exception:
                    pass
            lines.append(f"  0x{crva:06X}: {ins.mnemonic:<7} {ins.op_str}{extra}")
        return lines

    out = []
    out.append("=" * 100)
    out.append("1. CTargetMode::OnWorldLBtn (0x3A6AF0) 尾部 + 0x3A6850..0x3A68E4")
    out.append("=" * 100)
    out.append("\n--- 0x3A6E80..0x3A7096 (0x3A6AF0 尾部，含 HasTargetController @ 0x3A7056) ---")
    out.extend(disasm_range(0x3A6FF0, 0x3A7096, 80))

    out.append("\n--- 0x3A62A0..0x3A6480 (IssueTargetOrder?) ---")
    out.extend(disasm_range(0x3A62A0, 0x3A6420, 120))

    out.append("\n" + "=" * 100)
    out.append("2. CGameUI::PopMode (0x356E50) 与 CGameUI::SetMode (0x356AC0) Xrefs 检查")
    out.append("=" * 100)
    out.append("--- CGameUI::PopMode (0x356E50) 本体 ---")
    out.extend(disasm_range(0x356E50, 0x356EE0, 60))
    pop_xrefs = find_calls_to(0x356E50)
    set_xrefs = find_calls_to(0x356AC0)
    out.append(f"PopMode (0x356E50) xrefs ({len(pop_xrefs)}): {[hex(x) for x in pop_xrefs]}")
    out.append(f"SetMode (0x356AC0) xrefs ({len(set_xrefs)}): {[hex(x) for x in set_xrefs]}")
    # 检查是否有任何在 0x340000..0x348000 (CCameraWar3) 内的调用
    cam_pop = [hex(x) for x in pop_xrefs if 0x340000 <= x <= 0x348000]
    cam_set = [hex(x) for x in set_xrefs if 0x340000 <= x <= 0x348000]
    out.append(f"CCameraWar3 内调用 PopMode/SetMode: pop={cam_pop}, set={cam_set}")

    out.append("\n" + "=" * 100)
    out.append("3. CWorldFrameWar3 中发出 0x1A0064 / 0x1A0065 / 0x1A0066 事件的位置")
    out.append("=" * 100)
    for ev in [0x1A0064, 0x1A0065, 0x1A0066, 0x1A0067, 0x1A0068]:
        hs = find_imm32(ev, 0x35D000, 0x373000)
        out.append(f"Event 0x{ev:X} in CWorldFrameWar3: {[hex(h) for h in hs]}")
        for h in hs[:2]:
            fs = find_func_start(h, 0x300)
            out.append(f"  --- @ 0x{h:X} (func ~0x{fs:X}) ---")
            out.extend(disasm_range(max(fs, h - 0x40), h + 0x50, 45))

    out.append("\n" + "=" * 100)
    out.append("4. CCameraWar3::Update (0x3474E0) 全貌 & [cam+0x2C] / [cam+0x30] 用途")
    out.append("=" * 100)
    out.extend(disasm_range(0x3474E0, 0x347700, 140))

    # 检查 0x340000..0x348000 中谁写 [reg+0x2C] 或 [reg+0x30]
    out.append("\n--- CCameraWar3 内 0x3436B0 (被 0x343DD0 滚屏事件调用) ---")
    out.extend(disasm_range(0x3436B0, 0x343720, 45))

    text = "\n".join(out)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {len(text)} chars to {OUT_PATH}")

if __name__ == "__main__":
    main()
