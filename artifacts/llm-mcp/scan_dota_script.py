# -*- coding: utf-8 -*-
"""在 DotA 6.83d war3map.j 中检索可靠/不可靠金钱、买活、防御塔保护(Glyph)、信使与肉山机制。"""
import re

lines = (
    open(r"D:\Qt\workspace\War3Script\war3map.j", "r", encoding="utf-8", errors="replace")
    .read()
    .replace("\r\n", "\n")
    .replace("\r", "\n")
    .split("\n")
)


def grep(label, pat, limit=15):
    print(f"\n=== {label} ===")
    rx = re.compile(pat, re.I)
    n = 0
    for i, l in enumerate(lines):
        if rx.search(l):
            print(f"  L{i+1}: {l[:130]}")
            n += 1
            if n >= limit:
                break


grep("Reliable / Unreliable Gold", r"reliable|unreliable|PLAYER_STATE_RESOURCE_GOLD")
grep("Buyback", r"buyback|bought back|ReviveHero")
grep("Glyph / Fortification", r"fortification|glyph")
grep("Roshan", r"roshan|aegis")
grep("Courier", r"courier|18486518|deliver")
