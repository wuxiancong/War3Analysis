#!/usr/bin/env python3
"""Extract ZS buyback table + death formula constants from War3Script."""
from __future__ import annotations

import json
import re
from pathlib import Path

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\hero-death-buyback")
OUT.mkdir(parents=True, exist_ok=True)
SCRIPT = Path(r"D:\Qt\workspace\War3Script")


def fourcc(v: int) -> str:
    return "".join(chr((v >> (8 * k)) & 0xFF) for k in range(4))


def main():
    text9 = (SCRIPT / "war3map_9.j").read_text(encoding="utf-8", errors="replace")
    zs = {int(a): int(b) for a, b in re.findall(r"set ZS\[(\d+)\]=(\d+)", text9)}
    rows = []
    for i in sorted(zs):
        rows.append({"idx": i, "fourcc_int": zs[i], "fourcc": fourcc(zs[i]), "gold": 50 * (i + 1)})
    (OUT / "zs_buyback_table.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # Also dump WD1 / OPO excerpts
    st = (SCRIPT / "war3map_start_timer.j").read_text(encoding="utf-8", errors="replace")
    # Find GV1 in all scripts
    gv1 = None
    for p in SCRIPT.glob("war3map*.j"):
        t = p.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"function GV1 takes.*?endfunction", t, re.S)
        if m:
            gv1 = m.group(0)
            break
    d7o = None
    for p in SCRIPT.glob("war3map*.j"):
        t = p.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"function D7O takes.*?endfunction", t, re.S)
        if m:
            d7o = m.group(0)[:2500]
            break
    gn1 = gm1 = None
    for p in SCRIPT.glob("war3map*.j"):
        t = p.read_text(encoding="utf-8", errors="replace")
        if gn1 is None:
            m = re.search(r"function GN1 takes.*?endfunction", t, re.S)
            if m:
                gn1 = m.group(0)
        if gm1 is None:
            m = re.search(r"function GM1 takes.*?endfunction", t, re.S)
            if m:
                gm1 = m.group(0)

    excerpts = {
        "GV1": gv1,
        "D7O_head": d7o,
        "GN1": gn1,
        "GM1": gm1,
        "ZS_count": len(zs),
        "ZS_sample": rows[:5] + rows[-3:],
    }
    (OUT / "map_excerpts.json").write_text(json.dumps(excerpts, indent=2, ensure_ascii=False), encoding="utf-8")
    print("ZS", len(zs), "first", rows[0], "last", rows[-1])
    if gv1:
        print("GV1", gv1[:400])


if __name__ == "__main__":
    main()
