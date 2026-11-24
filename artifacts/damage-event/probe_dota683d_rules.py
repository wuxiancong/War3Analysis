# -*- coding: utf-8 -*-
"""
轻量级搜索 DotA 6.83d Scripts_war3map.j 中的：
1. 经验分配与反补经验逻辑（AddHeroXP）
2. 神符刷新与拾取/装瓶逻辑
3. 假眼 o004 / 真眼 oeye 及防御塔真视技能
4. 计分板 Multiboard 是否显示敌方英雄等级
"""
import re
from pathlib import Path

J_PATH = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map\Scripts_war3map.j")
OUT_PATH = Path(r"D:\Qt\workspace\War3Analysis\artifacts\damage-event\dota683d_rules_scan.txt")

lines = J_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
out = [f"Loaded Scripts_war3map.j: {len(lines)} lines\n"]


def dump_matches(title, pattern, max_hits=15, ctx_before=3, ctx_after=12):
    out.append(f"================ {title} (pattern={pattern}) ================")
    rx = re.compile(pattern)
    hits = 0
    last_end = -1
    for i, ln in enumerate(lines):
        if rx.search(ln):
            if i <= last_end:
                continue
            hits += 1
            st = max(0, i - ctx_before)
            ed = min(len(lines), i + ctx_after + 1)
            out.append(f"--- L{i+1} ---")
            for k in range(st, ed):
                out.append(f"{k+1:6d}: {lines[k]}")
            last_end = ed
            if hits >= max_hits:
                break
    out.append(f"(total shown: {hits})\n")


# 1. AddHeroXP 调用点（找核心小兵死亡分经验与反补逻辑）
dump_matches("AddHeroXP calls", r"\bAddHeroXP\s*\(", max_hits=15, ctx_before=8, ctx_after=15)

# 2. 经验范围常量 1300 / 1200 或 36 / 18 反补经验
dump_matches("Deny XP / 1300 range", r"(?:1300\.|IsUnitAlly.*AddHeroXP|GetUnitPointValue.*36|36\s*\*)", max_hits=10, ctx_before=5, ctx_after=15)

# 3. 假眼 o004 与真眼 oeye
dump_matches("Wards o004 / oeye", r"'o004'|'oeye'", max_hits=12, ctx_before=4, ctx_after=10)

# 4. 神符拾取 / 刷新（常见神符物品码 I006/I007/I008/I00H/I00J/I01J 或 Rune 字符串）
dump_matches("Rune pickup / spawn", r"has activated|picked up|bottled|'I006'|'I007'|'I008'|'I00H'|'I00J'", max_hits=12, ctx_before=5, ctx_after=12)

# 5. Multiboard 计分板更新（看有没有 GetHeroLevel）
dump_matches("Multiboard & GetHeroLevel", r"MultiboardSetItemValue.*GetHeroLevel|GetHeroLevel.*Multiboard", max_hits=8, ctx_before=4, ctx_after=8)

OUT_PATH.write_text("\n".join(out), encoding="utf-8")
print(f"Wrote {len(out)} lines to {OUT_PATH}")
