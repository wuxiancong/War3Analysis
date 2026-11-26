# -*- coding: utf-8 -*-
"""
轻量解析 DotA 6.83d 支配头盔 (I08T / A2V4) 配方、商店、脚本逻辑与中立野怪属性：
1. Units_ItemData.slk / Units_ItemStrings.txt 查找 Helm of the Dominator / Helm of Iron Will / Morbid Mask 物品码与价格
2. Units_AbilityData.slk 核查 A2V4 (ANcl) 的 DataB1 / DataF1 (Base Order ID) / Range / Cool / Cost
3. Scripts_war3map.j 搜索 I08T (1227896916) 与 A2V4 (1093817908) 合成公式与支配脚本
4. 解析常见中立野怪的射程、移速、血量、魔免/远古标记
"""
import re
import struct
from pathlib import Path
import sys

MAP = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")
OUT_DIR = Path(r"D:\Qt\workspace\War3Analysis\artifacts\helm-dominate")
OUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\stealth-rune-route")
from parse_sight_and_doodads import parse_slk_clean


def fourcc_to_int(s: str) -> int:
    return struct.unpack(">I", s.encode("ascii"))[0]


def int_to_fourcc(n: int) -> str:
    try:
        b = struct.pack(">I", n)
        if all(32 <= c < 127 for c in b):
            return b.decode("ascii")
    except Exception:
        pass
    return str(n)


def main():
    out = []

    # 1. 查找 Helm of the Dominator / Helm of Iron Will / Morbid Mask 物品名与码
    istr = (MAP / "Units_ItemStrings.txt").read_text(encoding="utf-8", errors="replace")
    out.append("=== 1. Units_ItemStrings.txt 支配头盔与组件 ===")
    for m in re.finditer(r"\[([A-Za-z0-9]{4})\]([^\[]+)", istr):
        tid, body = m.group(1), m.group(2)
        if any(k in body.lower() for k in ("dominator", "iron will", "morbid mask", "mask of death")):
            name_m = re.search(r"Name=(.+)", body)
            out.append(f"  {tid} ({fourcc_to_int(tid)}): {name_m.group(1).strip() if name_m else '?'}")

    # 2. 从 Units_ItemData.slk 查 I08T 及组件的价格与技能
    icols, irows = parse_slk_clean(MAP / "Units_ItemData.slk")
    ic2i = {v: k for k, v in icols.items()}
    out.append(f"\n=== 2. Units_ItemData.slk 关键物品 (goldcost col={ic2i.get('goldcost')}, abilList col={ic2i.get('abilList')}) ===")
    for y, r in sorted(irows.items()):
        tid = r.get(1, "")
        if tid in ("I08T", "I03G", "I037", "I03B", "I049", "I08U", "I055", "desc", "modt", "helm", "hval"):
            out.append(f"  {tid:6s} (Y={y:4d}): gold={r.get(ic2i.get('goldcost',0),'?')}, abil={r.get(ic2i.get('abilList',0),'?')}, stock={r.get(ic2i.get('stockMax',0),'?')}")

    # 3. 从 Units_AbilityData.slk 查 A2V4 全部非空字段
    acols, arows = parse_slk_clean(MAP / "Units_AbilityData.slk")
    out.append("\n=== 3. Units_AbilityData.slk A2V4 完整字段 ===")
    for y, r in sorted(arows.items()):
        if r.get(1, "") == "A2V4":
            out.append(f"  A2V4 (Y={y}): " + ", ".join(f"{acols.get(k, k)}={v}" for k, v in sorted(r.items())))

    # 4. 在 Scripts_war3map.j 中搜索 I08T (1227896916) 与 A2V4 (1093817908)
    j_lines = (MAP / "Scripts_war3map.j").read_text(encoding="utf-8", errors="replace").splitlines()
    for label, num in [("I08T (支配头盔)", str(fourcc_to_int("I08T"))), ("A2V4 (支配技能)", str(fourcc_to_int("A2V4")))]:
        hits = [i + 1 for i, l in enumerate(j_lines) if num in l]
        out.append(f"\n=== 4. war3map.j {label} ({num}): {len(hits)} hits, lines={hits[:15]} ===")
        for ln_no in hits[:6]:
            out.append(f"--- L{ln_no} ---")
            for k in range(max(0, ln_no - 6), min(len(j_lines), ln_no + 22)):
                line_txt = j_lines[k]
                # 把 10 位十进制 4CC 顺手注释出来方便阅读
                out.append(f"  {k+1:6d}: {line_txt}")

    p = OUT_DIR / "probe_helm_683d.txt"
    p.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(out)} lines to {p}")


if __name__ == "__main__":
    main()
