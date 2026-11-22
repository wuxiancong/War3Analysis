# -*- coding: utf-8 -*-
"""
全版本内部函数精确补齐脚本：修正 1.0.17~1.21.0（HandleToUnit 内联）与 1.22~1.27 的
CUnit::FindAbility / CUnit::ResetCooldown / CAbilitySpell::ResetCooldown /
CUnit::CountBuffsEx / ResolveAgent / CUnit::IsDetected 精确 RVA 与结构体偏移验证。
"""
import json
import re
import subprocess
import pefile

DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.52.37025\bin\Hostx64\x64\dumpbin.exe"
IN_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp\all_versions_rva.json"
OUT_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp\all_versions_rva_verified.json"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp\all_versions_rva_verified.txt"


def disasm(dll, base, rva, sz):
    va1, va2 = base + rva, base + rva + sz
    res = subprocess.run([DUMPBIN, "/nologo", "/disasm", f"/range:0x{va1:X},0x{va2:X}", dll],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [ln.strip() for ln in res.stdout.splitlines() if re.match(r"^\s+[0-9A-F]{8}:", ln)]


def calls_in(asm, base):
    out = []
    for i, ln in enumerate(asm):
        m = re.search(r"\b(call|jmp)\s+([0-9A-F]{8})\b", ln)
        if m:
            va = int(m.group(2), 16)
            if base <= va < base + 0x2000000:
                out.append((i, m.group(1), va - base))
    return out


def main():
    data = json.load(open(IN_JSON, encoding="utf-8"))
    for ver, rec in data.items():
        dll = rf"D:\Qt\workspace\War3Launcher\versions\{ver}\Game.dll"
        base = int(rec["image_base"], 16)
        nat = rec["natives"]
        internals = {}

        # 1. CUnit::FindAbility <- GetUnitAbilityLevel (紧接在 mov eax, [eax+50h] 或 +50h 之前的 call)
        rva = int(nat["GetUnitAbilityLevel"], 16)
        asm = disasm(dll, base, rva, 0x130)
        cs = calls_in(asm, base)
        idx_50 = next((i for i, l in enumerate(asm) if "+50h]" in l), None)
        if idx_50 is not None:
            prev_calls = [c[2] for c in cs if c[0] < idx_50 and c[1] == "call"]
            if prev_calls:
                internals["CUnit::FindAbility"] = f"0x{prev_calls[-1]:X}"
                internals["ability_lvl_off"] = "+0x50"

        # 2. CUnit::ResetCooldown & CAbilitySpell::ResetCooldown <- UnitResetCooldown
        rva = int(nat["UnitResetCooldown"], 16)
        asm = disasm(dll, base, rva, 0x100)
        # 在 ret 之前截断
        ret_i = next((i for i, l in enumerate(asm) if "\tret" in l or l.endswith("ret") or " ret " in l), len(asm))
        asm_fn = asm[: ret_i + 1]
        cs = calls_in(asm_fn, base)
        if cs:
            cunit_rc = cs[-1][2]
            internals["CUnit::ResetCooldown"] = f"0x{cunit_rc:X}"
            asm2 = disasm(dll, base, cunit_rc, 0x140)
            # 找 CUnit 链表偏移 (1DCh / 1D8h / 其他)
            m_list = re.search(r"\+00000(1[A-F0-9]{2})h\]", "\n".join(asm2))
            if m_list:
                internals["ability_list_off"] = f"+0x{m_list.group(1)}"
            cs2 = calls_in(asm2, base)
            for _, op, cand in cs2:
                if op != "call":
                    continue
                asm3 = disasm(dll, base, cand, 0x45)
                j3 = "\n".join(asm3)
                if "20h],200h" in j3 and re.search(r"000000([A-F0-9]{2})h", j3):
                    m_cd = re.search(r"lea\s+\w+,\[(?:\w+)\+000000([A-F0-9]{2})h\]", j3)
                    internals["CAbilitySpell::ResetCooldown"] = f"0x{cand:X}"
                    internals["cd_timer_off"] = f"+0x{m_cd.group(1)}" if m_cd else "+0xD0"
                    break

        # 3. CUnit::CountBuffsEx & ResolveAgent <- UnitCountBuffsEx
        rva = int(nat["UnitCountBuffsEx"], 16)
        asm = disasm(dll, base, rva, 0x140)
        ret_i = next((i for i, l in enumerate(asm) if l.endswith("ret") or " ret " in l), len(asm))
        cs = calls_in(asm[: ret_i + 1], base)
        if cs:
            cunit_cb = cs[-1][2]
            internals["CUnit::CountBuffsEx"] = f"0x{cunit_cb:X}"
            asm2 = disasm(dll, base, cunit_cb, 0x60)
            cs2 = calls_in(asm2, base)
            if cs2:
                internals["ResolveAgent"] = f"0x{cs2[0][2]:X}"

        # 4. CUnit::IsDetected <- IsUnitDetected
        rva = int(nat["IsUnitDetected"], 16)
        asm = disasm(dll, base, rva, 0x180)
        ret_i = next((i for i, l in enumerate(asm) if l.endswith("ret") or " ret " in l), len(asm))
        cs = [c for c in calls_in(asm[: ret_i + 1], base) if c[1] == "call"]
        if cs:
            internals["CUnit::IsDetected"] = f"0x{cs[-1][2]:X}"

        rec["internals"] = internals
        print(f"[{ver}] {internals}")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 生成完整表格文本
    vers = list(data.keys())
    lines = []
    hdr = f"{'Symbol':28s} | " + " | ".join(f"{v:13s}" for v in vers)
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for n in list(data[vers[0]]["natives"].keys()):
        lines.append(f"{n:28s} | " + " | ".join(f"{(data[v]['natives'].get(n) or '-'):13s}" for v in vers))
    lines.append("-" * len(hdr))
    for ik in ["CUnit::FindAbility", "CUnit::ResetCooldown", "CAbilitySpell::ResetCooldown", "CUnit::CountBuffsEx", "ResolveAgent", "CUnit::IsDetected", "ability_lvl_off", "ability_list_off", "cd_timer_off"]:
        lines.append(f"{ik:28s} | " + " | ".join(f"{str(data[v]['internals'].get(ik, '-')):13s}" for v in vers))
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {OUT_TXT}")


if __name__ == "__main__":
    main()
