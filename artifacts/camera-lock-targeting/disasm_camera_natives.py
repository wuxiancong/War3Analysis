# -*- coding: utf-8 -*-
r"""
递归反汇编 War3 1.27.0.52240 与 1.26.0.6401 的镜头原生函数：
- SetCameraTargetController
- SetCameraPosition
- ResetToGameCamera
- GetCameraTargetPositionX
追踪至底层 CGameUI / CWorldFrameWar3 / Camera 对象及字段写入，检查是否存在取消选目标或清悬停副作用。
"""
import os
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

VERS = {
    "1.27.0.52240": {
        "path": r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll",
        "funcs": {
            "SetCameraTargetController": 0x1F42F0,
            "SetCameraPosition":         0x1F4200,
            "ResetToGameCamera":         0x1F3110,
            "GetCameraTargetPositionX":  0x1E1AE0,
        },
    },
    "1.26.0.6401": {
        "path": r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll",
        "funcs": {
            "SetCameraTargetController": 0x3CD760,
            "SetCameraPosition":         0x3B45D0,
            "ResetToGameCamera":         0x3B46B0,
            "GetCameraTargetPositionX":  0x3B4D00,
        },
    },
}

OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\camera-lock-targeting\camera_natives_disasm.txt"

def load_pe(path):
    pe = pefile.PE(path, fast_load=True)
    img_base = pe.OPTIONAL_HEADER.ImageBase
    return pe, img_base

def rva_to_bytes(pe, rva, size):
    try:
        off = pe.get_offset_from_rva(rva)
        return pe.__data__[off:off+size]
    except Exception:
        return b""

def disasm_func(pe, img_base, rva, max_insns=140):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    code = rva_to_bytes(pe, rva, max_insns * 8)
    lines = []
    callees = []
    end_after_ret = False
    for idx, ins in enumerate(md.disasm(code, img_base + rva)):
        cur_rva = ins.address - img_base
        extra = ""
        if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
            try:
                tgt = int(ins.op_str, 16)
                tgt_rva = tgt - img_base
                if 0 < tgt_rva < pe.OPTIONAL_HEADER.SizeOfImage:
                    extra = f"  ; RVA 0x{tgt_rva:X}"
                    if ins.mnemonic == "call" and tgt_rva not in callees:
                        callees.append(tgt_rva)
            except Exception:
                pass
        lines.append(f"  0x{cur_rva:06X}: {ins.mnemonic:<7} {ins.op_str}{extra}")
        if ins.mnemonic.startswith("ret") and idx > 2:
            # 简单检测函数结束（若后面是 int3 / cc / nop 或已有足够指令）
            nxt = rva_to_bytes(pe, cur_rva + ins.size, 1)
            if nxt in (b"\xcc", b"\x90"):
                break
        if idx >= max_insns - 1:
            break
    return lines, callees

def main():
    out = []
    for ver, info in VERS.items():
        pe, img_base = load_pe(info["path"])
        out.append("=" * 100)
        out.append(f"版本: {ver} | ImageBase: 0x{img_base:08X}")
        out.append("=" * 100)
        visited = set()
        for name, rva in info["funcs"].items():
            out.append(f"\n>>> [L0] {name} @ RVA 0x{rva:X}")
            lines, callees = disasm_func(pe, img_base, rva, 100)
            out.extend(lines)
            visited.add(rva)
            # 递归展开 2 层直接 callee
            for c1 in callees:
                if c1 in visited:
                    out.append(f"  --> [L1] RVA 0x{c1:X} (已展开)")
                    continue
                visited.add(c1)
                out.append(f"\n  >>> [L1] callee RVA 0x{c1:X} (from {name})")
                l1, c2s = disasm_func(pe, img_base, c1, 120)
                out.extend(l1)
                for c2 in c2s:
                    if c2 in visited:
                        continue
                    visited.add(c2)
                    out.append(f"\n    >>> [L2] callee RVA 0x{c2:X} (from 0x{c1:X})")
                    l2, _ = disasm_func(pe, img_base, c2, 90)
                    out.extend(l2)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    text = "\n".join(out)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {len(text)} chars to {OUT_PATH}")

if __name__ == "__main__":
    main()
