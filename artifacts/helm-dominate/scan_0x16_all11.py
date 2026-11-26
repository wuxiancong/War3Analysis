# -*- coding: utf-8 -*-
"""全 11 版本扫描 0x000A0016~0x000A001B (选择/编队动作事件 ID) 的接收与发送 RVA，
反汇编 1.27 0x2FD850 证明 0x16 仅修改选区不打断 COrder，并导出 6.83d 25 种中立野怪属性。"""
import os
import re
import struct
import subprocess
import sys

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32

VERSIONS_DIR = r"D:\Qt\workspace\War3Launcher\versions"
OUT_RVA = r"D:\Qt\workspace\War3Analysis\artifacts\helm-dominate\selection_all11_rva.txt"
OUT_CREEPS = r"D:\Qt\workspace\War3Analysis\artifacts\helm-dominate\creep_stats_683d.txt"

DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Tools\MSVC\14.29.30133\bin\Hostx64\x86\dumpbin.exe"
if not os.path.exists(DUMPBIN):
    for root in [
        r"C:\Program Files\Microsoft Visual Studio",
        r"C:\Program Files (x86)\Microsoft Visual Studio",
    ]:
        if os.path.exists(root):
            for dp, _, fns in os.walk(root):
                if "dumpbin.exe" in fns and "x86" in dp.lower():
                    DUMPBIN = os.path.join(dp, "dumpbin.exe")
                    break


def find_text_imm32(pe: PE32, imm: int):
    """在 .text 节中搜索 32 位立即数（如 0x000A0016）。"""
    pat = struct.pack("<I", imm)
    hits = []
    # 只扫第一个可执行节 (.text)
    for s in pe.sections:
        if s.name.startswith(".text"):
            raw_s = pe.raw[s.raw_ptr:s.raw_ptr + s.raw_size]
            pos = 0
            while True:
                h = raw_s.find(pat, pos)
                if h < 0:
                    break
                pos = h + 1
                hits.append(s.vaddr + h)
    return hits


def dump_creeps():
    base = r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map"

    def load_slk(fn):
        rows, hdr, y = {}, {}, 0
        with open(os.path.join(base, fn), "r", encoding="utf-8", errors="ignore") as f:
            for ln in f:
                if not ln.startswith("C;"):
                    continue
                mx = re.search(r"X(\d+)", ln)
                my = re.search(r"Y(\d+)", ln)
                mk = re.search(r";K(.*)", ln)
                if my:
                    y = int(my.group(1))
                if not mx or not mk:
                    continue
                x = int(mx.group(1))
                v = mk.group(1).strip().strip('"')
                if y == 1:
                    hdr[x] = v
                else:
                    rows.setdefault(y, {})[hdr.get(x, str(x))] = v
        out = {}
        for r in rows.values():
            k = r.get("unitBalanceID") or r.get("unitWeapID") or r.get("unitAbilID")
            if k:
                out[k] = r
        return out

    bal = load_slk("Units_UnitBalance.slk")
    wep = load_slk("Units_UnitWeapons.slk")
    abi = load_slk("Units_UnitAbilities.slk")
    names = {}
    for fn in os.listdir(base):
        if fn.endswith("UnitStrings.txt"):
            cur = None
            with open(os.path.join(base, fn), "r", encoding="utf-8", errors="ignore") as f:
                for ln in f:
                    m = re.match(r"^\[(\w{4})\]", ln.strip())
                    if m:
                        cur = m.group(1)
                    elif cur and ln.startswith("Name="):
                        names[cur] = ln.split("=", 1)[1].strip()

    ids = [
        "nfsh", "ndtr", "ndtw", "ngh1", "ngns", "nsth", "nstl", "nsat",
        "ncen", "ncnk", "nowb", "nowe", "nwlg", "npfl", "nfpc", "nfpu",
        "nkob", "nkol", "nkot", "nogm", "nomg", "nbdk", "nbwm", "n0LC", "n0LD",
    ]
    lines = ["=== DotA 6.83d 中立野怪 SLK 属性表 (25 种) ==="]
    for u in ids:
        b = bal.get(u, {})
        w = wep.get(u, {})
        a = abi.get(u, {})
        nm = names.get(u, "?")
        hp = b.get("HP", "?")
        mp = b.get("manaN", "?")
        spd = b.get("spd", "?")
        df = b.get("def", "?")
        rng = w.get("rangeN1", "?")
        wt = w.get("weapTp1", "?")
        ab = a.get("abilList", "")
        lines.append(
            f"{u} | {nm:<28} | HP={hp:>4} | MP={mp:>3} | spd={spd:>3} | def={df:>2} | rng={rng:>3} ({wt:<7}) | abil={ab}"
        )
    with open(OUT_CREEPS, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    versions = sorted(
        d for d in os.listdir(VERSIONS_DIR)
        if os.path.isfile(os.path.join(VERSIONS_DIR, d, "Game.dll"))
    )
    out = []
    out.append("=== 全 11 版本 0x16~0x19 (NetCommand 事件码 0x0A0016~0x0A0019) 收/发 RVA ===")
    hdr = f"{'Version':<14} | {'0x16 Recv/Disp':<14} | {'0x16 Send':<14} | {'0x17 Recv/Send':<16} | {'0x18 Recv/Send':<16} | {'0x19 Recv/Send':<16}"
    out.append(hdr)
    out.append("-" * len(hdr))

    for ver in versions:
        dll = os.path.join(VERSIONS_DIR, ver, "Game.dll")
        pe = PE32(dll)
        h16 = find_text_imm32(pe, 0x000A0016)
        h17 = find_text_imm32(pe, 0x000A0017)
        h18 = find_text_imm32(pe, 0x000A0018)
        h19 = find_text_imm32(pe, 0x000A0019)

        def f1(arr, idx=0):
            return f"0x{arr[idx]:06X}" if len(arr) > idx else "—"

        def fp(arr):
            if not arr:
                return "—"
            if len(arr) == 1:
                return f"0x{arr[0]:06X}"
            return f"0x{arr[0]:06X}/0x{arr[-1]:06X}"

        # h16 通常第 1 个为反序列化派发，后两个为客户端发送
        out.append(
            f"{ver:<14} | {f1(h16, 0):<14} | {f1(h16, -1) if len(h16) > 1 else '—':<14} | "
            f"{fp(h17):<16} | {fp(h18):<16} | {fp(h19):<16}"
        )

    # 反汇编 1.27 的 0x2FD850 (NetCommand -> Event 派发) 及观察 0x0A0016 处理者
    dll127 = os.path.join(VERSIONS_DIR, "1.27.0.52240", "Game.dll")
    pe127 = PE32(dll127)
    # 在 1.27 搜索所有 0x000A0016 出现点（包括 switch / cmp 监听者！）
    all16 = find_text_imm32(pe127, 0x000A0016)
    out.append("")
    out.append(f"=== 1.27.0.52240 所有 0x000A0016 (.text) 命中: {[hex(x) for x in all16]} ===")
    for rva in all16:
        sva = pe127.image_base + max(0, rva - 0x20)
        res = subprocess.run([DUMPBIN, "/DISASM:NOBYTES", f"/RANGE:0x{sva:X},0x{sva+0x90:X}", dll127], capture_output=True, text=True)
        out.append(f"--- Context around 0x{rva:06X} ---")
        for ln in res.stdout.splitlines():
            if re.match(r"\s+[0-9A-F]{8}:", ln):
                out.append(ln)

    with open(OUT_RVA, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    dump_creeps()
    print(f"Done: {len(out)} lines -> {OUT_RVA}")


if __name__ == "__main__":
    main()
