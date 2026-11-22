# -*- coding: utf-8 -*-
r"""
在 1.27.0.52240 game.dll 中追踪四个核心交叉点：
1. CCameraWar3::HasTargetController (0x343250) 的全部调用点 (Xrefs)
2. CGameUI + 0x1B4 (当前输入模式 CInputMode* / CTargetMode*) 的写入与切换函数 (CGameUI::SetMode / PushMode)
3. CTargetMode 事件处理函数 (0x39F3E0, 0x3A1AA0, 0x3A0FD0, 0x3A6AF0, 0x3A5E20, 0x3A5E40, 0x3A1620, 0x3A1F30)
4. CCameraWar3 边缘滚屏/键盘滚屏/Update 函数 (vtable 0x343DD0, 0x343450, 0x3428E0, 0x341950, 0x344DC0, 0x3437D0)
输出到 D:\Qt\workspace\War3Analysis\artifacts\camera-lock-targeting\crosspoints_127.txt
"""
import os
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll"
OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\camera-lock-targeting\crosspoints_127.txt"

def main():
    pe = pefile.PE(DLL_PATH, fast_load=True)
    data = pe.__data__
    img = pe.OPTIONAL_HEADER.ImageBase
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    t_sec = pe.sections[0]
    t_off, t_rva, t_sz = t_sec.PointerToRawData, t_sec.VirtualAddress, t_sec.SizeOfRawData

    def off_of(rva): return pe.get_offset_from_rva(rva)
    def rva_of(off): return pe.get_rva_from_offset(off)

    def find_calls_to(target_rva):
        hits = []
        # 扫描 .text 中的 E8 rel32 (call) 和 E9 rel32 (jmp)
        buf = data[t_off:t_off + t_sz]
        for i in range(0, t_sz - 5):
            op = buf[i]
            if op in (0xE8, 0xE9):
                rel = struct.unpack_from("<i", buf, i + 1)[0]
                cur_rva = t_rva + i
                if (cur_rva + 5 + rel) == target_rva:
                    hits.append((cur_rva, "call" if op == 0xE8 else "jmp"))
        return hits

    def find_func_start(rva, max_back=0x400):
        o = off_of(rva)
        for d in range(0, max_back):
            if o - d >= 2 and data[o - d - 1] == 0xCC and data[o - d] != 0xCC:
                return rva - d
        return max(0x1000, rva - 0x40)

    def disasm_rva(rva, count=75):
        o = off_of(rva)
        code = data[o:o + count * 8]
        lines = []
        for idx, ins in enumerate(md.disasm(code, img + rva)):
            crva = ins.address - img
            extra = ""
            if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
                try:
                    trva = int(ins.op_str, 16) - img
                    if 0 < trva < pe.OPTIONAL_HEADER.SizeOfImage:
                        extra = f" ; RVA 0x{trva:X}"
                except Exception:
                    pass
            lines.append(f"  0x{crva:06X}: {ins.mnemonic:<7} {ins.op_str}{extra}")
            if ins.mnemonic.startswith("ret") and idx > 1:
                nxt = data[off_of(crva) + ins.size:off_of(crva) + ins.size + 1]
                if nxt in (b"\xcc", b"\x90"):
                    break
            if idx >= count - 1:
                break
        return lines

    out = []
    out.append("=" * 100)
    out.append("1. CCameraWar3::HasTargetController (0x343250) 的全部调用点")
    out.append("=" * 100)
    calls_343250 = find_calls_to(0x343250)
    out.append(f"Xrefs to 0x343250: {[(hex(a), op) for a, op in calls_343250]}")
    for a, op in calls_343250:
        fs = find_func_start(a)
        out.append(f"\n--- Xref @ 0x{a:X} (func ~0x{fs:X}) ---")
        out.extend(disasm_rva(max(fs, a - 0x30), 65))

    out.append("\n" + "=" * 100)
    out.append("2. CTargetMode::ctor (0x34B7D0) 的调用点 & CGameUI 切换 Mode (+0x1B4) 逻辑")
    out.append("=" * 100)
    calls_ctor = find_calls_to(0x34B7D0)
    out.append(f"Xrefs to CTargetMode::ctor 0x34B7D0: {[(hex(a), op) for a, op in calls_ctor]}")
    for a, op in calls_ctor[:4]:
        fs = find_func_start(a, 0x300)
        out.append(f"\n--- CTargetMode::ctor xref @ 0x{a:X} (func ~0x{fs:X}) ---")
        out.extend(disasm_rva(max(fs, a - 0x20), 65))

    # 查找 0x348000..0x358000 (CGameUI 区域) 内访问 +0x1B4 的函数
    out.append("\n--- CGameUI 区域 (0x348000..0x358000) 访问 +0x1B4 的函数 ---")
    o0, o1 = off_of(0x348000), off_of(0x358000)
    buf = data[o0:o1]
    seen_fs = set()
    p = 0
    while True:
        i = buf.find(b"\xb4\x01\x00\x00", p)
        if i < 0: break
        rva = 0x348000 + i
        fs = find_func_start(rva, 0x200)
        if fs not in seen_fs:
            seen_fs.add(fs)
            out.append(f"\n--- CGameUI +0x1B4 @ 0x{rva:X} (func ~0x{fs:X}) ---")
            out.extend(disasm_rva(fs, 55))
        p = i + 1

    out.append("\n" + "=" * 100)
    out.append("3. CTargetMode 关键事件处理函数反汇编")
    out.append("=" * 100)
    for ev, fn in [
        ("0x30064 (MouseDown?)", 0x39F3E0),
        ("0x30065 (MouseUp?)",   0x3A1AA0),
        ("0x1A0064",             0x3A5E20),
        ("0x1A0065",             0x3A0FD0),
        ("0x1A0066 (WorldLBtn?)",0x3A6AF0),
        ("0x1A0067 (WorldRBtn?)",0x3A5E40),
        ("0x1A0068",             0x3A1620),
        ("0x40060064 (Minimap?)",0x3A1F30),
        ("0x40060066",           0x3A20A0),
    ]:
        out.append(f"\n--- CTargetMode::{ev} @ RVA 0x{fn:06X} ---")
        out.extend(disasm_rva(fn, 85))

    out.append("\n" + "=" * 100)
    out.append("4. CCameraWar3 事件/滚屏函数 (vtable: 0x343DD0, 0x343450, 0x3428E0, 0x3437D0)")
    out.append("=" * 100)
    for fn in [0x343DD0, 0x343450, 0x3437D0]:
        out.append(f"\n--- CCameraWar3 @ RVA 0x{fn:06X} ---")
        out.extend(disasm_rva(fn, 70))

    text = "\n".join(out)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {len(text)} chars to {OUT_PATH}")

if __name__ == "__main__":
    main()
