# -*- coding: utf-8 -*-
r"""
在 1.27.0.52240 game.dll 中一次性通过 RTTI + 交叉引用定位：
1. CTargetMode / CWorldFrameWar3 / CCameraWar3 / CGameUI 的 vtable 及其方法
2. CGameUI 中保存当前 UI Mode（含 CTargetMode）的字段偏移与切换/取消函数
3. CWorldFrameWar3+0x38C (SetCameraPosition 写入=1) 的全部引用点反汇编
4. CCameraWar3+0x44 (SetCameraTargetController 写入 CUnit*) 的全部引用点反汇编
输出到 D:\Qt\workspace\War3Analysis\artifacts\camera-lock-targeting\rtti_and_chains_127.txt
"""
import os
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll"
OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\camera-lock-targeting\rtti_and_chains_127.txt"

def main():
    pe = pefile.PE(DLL_PATH, fast_load=True)
    data = pe.__data__
    img = pe.OPTIONAL_HEADER.ImageBase
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    def rva_of(file_off):
        return pe.get_rva_from_offset(file_off)

    def off_of(rva):
        return pe.get_offset_from_rva(rva)

    def read_u32_rva(rva):
        o = off_of(rva)
        return struct.unpack_from("<I", data, o)[0]

    def find_all(buf, pat):
        res, p = [], 0
        while True:
            i = buf.find(pat, p)
            if i < 0: break
            res.append(i)
            p = i + 1
        return res

    def find_func_start(rva, max_back=0x300):
        # 向上找 int3 (0xCC) 或典型序言 55 8B EC
        o = off_of(rva)
        for d in range(0, max_back):
            if o - d >= 2 and data[o - d - 1] == 0xCC and data[o - d] != 0xCC:
                return rva - d
        for d in range(0, max_back):
            if data[o - d:o - d + 3] == b"\x55\x8b\xec":
                return rva - d
        return max(0x1000, rva - 0x40)

    def disasm_rva(rva, count=80):
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
    out.append("1. RTTI -> CompleteObjectLocator -> vtable 定位 (1.27.0.52240)")
    out.append("=" * 100)

    vtables = {}
    for cls in [b"CTargetMode", b"CWorldFrameWar3", b"CCameraWar3", b"CGameUI", b"CGameUIMode", b"CSelectMode", b"CCommandMode", b"CSmartMode"]:
        name_pat = b".?AV" + cls + b"@@"
        hits = find_all(data, name_pat)
        if not hits:
            # 模糊查一下包含 cls 的 RTTI
            hits2 = find_all(data, cls + b"@@")
            if hits2:
                out.append(f"[RTTI 模糊] {cls.decode()}: {[hex(rva_of(h)) for h in hits2[:5]]}")
            continue
        for h in hits:
            td_off = h - 8  # TypeDescriptor: vftable(4), spare(4), name[]
            td_va = img + rva_of(td_off)
            out.append(f"\nClass {cls.decode()}: TypeDescriptor VA=0x{td_va:08X} (RVA 0x{rva_of(td_off):X})")
            # 找 CompleteObjectLocator (sig=0, offset, cdOffset, pTypeDescriptor)
            col_refs = find_all(data, struct.pack("<I", td_va))
            for cr in col_refs:
                col_off = cr - 12
                sig, off_val, cd_off = struct.unpack_from("<III", data, col_off)
                if sig == 0 and off_val < 0x1000:
                    col_va = img + rva_of(col_off)
                    vt_refs = find_all(data, struct.pack("<I", col_va))
                    for vr in vt_refs:
                        vt_rva = rva_of(vr + 4)
                        # 读取前 24 个虚函数
                        fns = []
                        for k in range(28):
                            fv = read_u32_rva(vt_rva + k * 4)
                            if not (img + 0x1000 <= fv < img + 0x940000):
                                break
                            fns.append(fv - img)
                        out.append(f"  vtable (off=0x{off_val:X}) @ RVA 0x{vt_rva:X} ({len(fns)} methods):")
                        for k, fn_rva in enumerate(fns):
                            out.append(f"    [{k:02d}] +0x{k*4:02X}: RVA 0x{fn_rva:06X}")
                        if off_val == 0:
                            vtables[cls.decode()] = (vt_rva, fns)

    # 2. 查找所有引用 CTargetMode vtable 的地方（构造函数 / 切换处）
    out.append("\n" + "=" * 100)
    out.append("2. CTargetMode vtable 引用点（构造 / 激活）及其关键虚函数反汇编")
    out.append("=" * 100)
    if "CTargetMode" in vtables:
        vt_rva, fns = vtables["CTargetMode"]
        vt_va = img + vt_rva
        refs = find_all(data, struct.pack("<I", vt_va))
        out.append(f"CTargetMode vtable VA 0x{vt_va:08X} refs: {[hex(rva_of(r)) for r in refs]}")
        for r in refs[:4]:
            rrva = rva_of(r)
            fs = find_func_start(rrva)
            out.append(f"\n--- Ref @ 0x{rrva:X} (func start ~0x{fs:X}) ---")
            out.extend(disasm_rva(fs, 70))
        # 反汇编 CTargetMode 的前 16 个虚函数
        for k, fn_rva in enumerate(fns[:18]):
            out.append(f"\n--- CTargetMode::vfn[{k}] (+0x{k*4:02X}) @ RVA 0x{fn_rva:06X} ---")
            out.extend(disasm_rva(fn_rva, 75))

    # 3. 反汇编 CWorldFrameWar3+0x38C 的全部引用点
    out.append("\n" + "=" * 100)
    out.append("3. [reg + 0x38C] (CWorldFrameWar3+0x38C) 关键引用点反汇编")
    out.append("=" * 100)
    for rva in [0x35f35f, 0x3687fa, 0x369046, 0x369125, 0x39227e, 0x3a7380, 0x3bb508]:
        fs = find_func_start(rva, 0x400)
        out.append(f"\n--- 0x38C ref @ 0x{rva:X} (func start ~0x{fs:X}) ---")
        out.extend(disasm_rva(max(fs, rva - 0x40), 55))

    # 4. 查找 CCameraWar3::Update（在 0x340000..0x348000 内读取 [reg + 0x44] 的函数）
    out.append("\n" + "=" * 100)
    out.append("4. CCameraWar3 区域 (0x340000..0x348000) 内所有访问 +0x44 的函数")
    out.append("=" * 100)
    o0 = off_of(0x340000)
    o1 = off_of(0x348000)
    # 搜索 8B xx 44 (mov reg, [reg+0x44]) 或 83 7x 44 00 (cmp [reg+0x44], 0)
    cam_funcs = set()
    for pos in range(o0, o1 - 3):
        b0, b1, b2 = data[pos], data[pos+1], data[pos+2]
        if (b0 == 0x8B and (b1 & 0xC0) == 0x40 and b2 == 0x44) or (b0 == 0x83 and (b1 & 0xF8) == 0x78 and b2 == 0x44):
            rva = rva_of(pos)
            fs = find_func_start(rva, 0x500)
            cam_funcs.add((fs, rva))
    for fs, rva in sorted(cam_funcs):
        out.append(f"\n--- Cam +0x44 @ 0x{rva:X} (func start ~0x{fs:X}) ---")
        out.extend(disasm_rva(max(fs, rva - 0x30), 65))

    text = "\n".join(out)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {len(text)} chars to {OUT_PATH}")

if __name__ == "__main__":
    main()
