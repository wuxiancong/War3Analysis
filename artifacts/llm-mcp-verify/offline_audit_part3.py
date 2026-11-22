# -*- coding: utf-8 -*-
"""
独立离线核验脚本（阶段三）：
1. B5: 通过 RTTI 定位 1.27 CNetCommandUnitOrderBasic / TargetPoint / TargetImage 虚表，反汇编其执行函数验证 abilityFlags 位 (0x01 = Shift Queue?)
2. A1: 定位 1.27 CAbilitySpell 构造与 CTimer 虚表 (vtable+0x18 剩余时间, 总冷却偏移)
3. B4: 提取 war3map.j L20080..L20135 TP 选建筑完整逻辑
4. B3: 检查 war3map.j 信使加速技能 (speedburst) 与 n004/n018/n01C/n01G 真实身份
5. A4: 检查 war3map.j 常见控制 Buff FourCC (眩晕/沉默/减速/妖术) 与 CUnit 状态标志
"""
import re
import struct
import subprocess
import pefile

DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.52.37025\bin\Hostx64\x64\dumpbin.exe"
DLL_127 = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
WAR3MAP_J = r"D:\Qt\workspace\War3Script\war3map.j"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-verify\offline_audit_part3.txt"


def disasm(dll, base, rva, sz):
    va1, va2 = base + rva, base + rva + sz
    res = subprocess.run([DUMPBIN, "/nologo", "/disasm", f"/range:0x{va1:X},0x{va2:X}", dll],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [ln.strip() for ln in res.stdout.splitlines() if re.match(r"^\s+[0-9A-F]{8}:", ln)]


def find_vtable_by_rtti(raw, pe, rtti_name: bytes):
    """通过 MSVC 32 位 RTTI (TypeDescriptor -> CompleteObjectLocator -> vtable[-1]) 查找虚表 RVA。"""
    base = pe.OPTIONAL_HEADER.ImageBase
    pos = raw.find(rtti_name)
    if pos < 0:
        return None
    # TypeDescriptor 起始于 name - 8
    td_rva = pe.get_rva_from_offset(pos - 8)
    if td_rva is None:
        return None
    td_va = base + td_rva
    pat_td = struct.pack("<I", td_va)
    # 在 .rdata 中找 CompleteObjectLocator (signature=0, offset=0, cdOffset=0, pTypeDescriptor=td_va)
    k = 0
    vtables = []
    while True:
        j = raw.find(pat_td, k)
        if j < 0:
            break
        if j >= 12:
            sig, off, cdoff = struct.unpack_from("<III", raw, j - 12)
            if sig == 0 and off == 0 and cdoff == 0:
                col_rva = pe.get_rva_from_offset(j - 12)
                if col_rva is not None:
                    col_va = base + col_rva
                    pat_col = struct.pack("<I", col_va)
                    m = raw.find(pat_col)
                    while m >= 0:
                        vt_rva = pe.get_rva_from_offset(m + 4)
                        if vt_rva is not None:
                            vtables.append(vt_rva)
                        m = raw.find(pat_col, m + 4)
        k = j + 4
    return vtables


def read_vtable(raw, pe, vt_rva, count=12):
    base = pe.OPTIONAL_HEADER.ImageBase
    off = pe.get_offset_from_rva(vt_rva)
    fns = []
    for i in range(count):
        va = struct.unpack_from("<I", raw, off + i * 4)[0]
        fns.append(va - base)
    return fns


def main():
    lines = []
    def log(s=""):
        lines.append(s)

    raw = open(DLL_127, "rb").read()
    pe = pefile.PE(DLL_127, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase

    # 1. B5: CNetCommandUnitOrderBasic / TargetPoint / TargetImage 虚表与反汇编
    log("=== 1. B5: 1.27 CNetCommandUnitOrder* 虚表与 abilityFlags ===")
    for name in [b".?AVCNetCommandUnitOrderBasic@@", b".?AVCNetCommandUnitOrderTargetPoint@@", b".?AVCNetCommandUnitOrderTargetImage@@"]:
        vts = find_vtable_by_rtti(raw, pe, name)
        log(f"  {name.decode()}: vtables={[f'0x{x:X}' for x in (vts or [])]}")
        if vts:
            fns = read_vtable(raw, pe, vts[0], 10)
            log("    slots: " + ", ".join(f"+0x{i*4:02X}=0x{f:X}" for i, f in enumerate(fns)))
            # 反汇编 Execute / Dispatch 槽位 (通常是 +0x18 或 +0x1C 或 +0x20)
            for idx in [5, 6, 7, 8]:
                fn_rva = fns[idx]
                if 0x1000 < fn_rva < 0x900000:
                    asm = disasm(DLL_127, base, fn_rva, 0x80)
                    if any("10h]" in l or "14h]" in l or "test" in l for l in asm):
                        log(f"    --- slot +0x{idx*4:02X} (0x{fn_rva:X}) ---")
                        lines.extend("      " + l for l in asm[:35])

    # 2. A1: 查找 CTimer 虚表 (搜索引用 0x0434F0 / 0x043700 或 RTTI CTimer)
    log("\n=== 2. A1: 1.27 CAbilitySpell & CTimer 虚表 ===")
    for name in [b".?AVCAbilitySpell@@", b".?AVCTimer@@", b".?AVCAgentTimer@@", b".?AVCSimpleTimer@@"]:
        vts = find_vtable_by_rtti(raw, pe, name)
        log(f"  {name.decode()}: vtables={[f'0x{x:X}' for x in (vts or [])]}")
        if vts and b"Timer" in name:
            fns = read_vtable(raw, pe, vts[0], 10)
            log("    slots: " + ", ".join(f"+0x{i*4:02X}=0x{f:X}" for i, f in enumerate(fns)))
            # vtable+0x18 (slot 6) 就是 GetRemainingTime!
            for idx in [5, 6, 7]:
                fn_rva = fns[idx]
                if 0x1000 < fn_rva < 0x900000:
                    log(f"    --- {name.decode()} slot +0x{idx*4:02X} (0x{fn_rva:X}) ---")
                    lines.extend("      " + l for l in disasm(DLL_127, base, fn_rva, 0x70)[:30])

    # 如果上面没找到 CTimer RTTI，直接搜包含 0x0434F0 附近函数的虚表（或 CAbilitySpell 构造函数中写入 [ecx+0D0h] 的虚表）
    text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
    tblob = raw[text.PointerToRawData : text.PointerToRawData + text.SizeOfRawData]
    # 搜 mov dword ptr [esi+0D0h], imm32 或 lea ecx, [esi+0D0h] -> call ctor
    m_all = [m.start() for m in re.finditer(b"\x8D[\x80-\xBF]\xD0\x00\x00\x00\xE8", tblob)]
    log(f"  匹配 lea reg, [reg+0D0h]; call 的位置数: {len(m_all)}")
    ctors = set()
    for pos in m_all[:20]:
        rel = struct.unpack_from("<i", tblob, pos + 7)[0]
        target = text.VirtualAddress + pos + 11 + rel
        ctors.add(target)
    log("  候选 +0xD0 构造函数 RVA: " + ", ".join(f"0x{c:X}" for c in sorted(ctors)))
    for c in sorted(ctors)[:5]:
        asm = disasm(DLL_127, base, c, 0x35)
        log(f"  [ctor 0x{c:X}]")
        lines.extend("    " + l for l in asm[:15])

    # 3. B4: war3map.j L20080..L20135 TP 选建筑
    jlines = open(WAR3MAP_J, "r", encoding="utf-8", errors="replace").read().splitlines()
    log("\n=== 3. B4: war3map.j TP 选建筑 (L20080..L20135) ===")
    for k in range(20079, min(len(jlines), 20135)):
        log(f"  L{k+1}: {jlines[k]}")

    # 4. B3: war3map.j L19325..L19365 (信使识别) & 加速技能
    log("\n=== 4. B3: war3map.j L19325..L19370 & Speedburst ===")
    for k in range(19324, min(len(jlines), 19370)):
        log(f"  L{k+1}: {jlines[k]}")
    # 搜索 L5350..L5365 确认 n004/n018/n01C/n01G 所在函数名
    log("  --- L5348..L5360 ---")
    for k in range(5347, 5360):
        log(f"  L{k+1}: {jlines[k]}")

    pe.close()
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_TXT}")


if __name__ == "__main__":
    main()
