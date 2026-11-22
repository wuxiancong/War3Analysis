#!/usr/bin/env python3
"""Export Rng1/Area1/Cool1 from Units_AbilityData.slk for threat-map (hero abilities with ranges)."""
from __future__ import annotations

import json
import re
from pathlib import Path

SLK = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map\Units_AbilityData.slk")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\threat-map")


def parse_slk(path: Path):
    cells = {}
    x = y = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("C;"):
            continue
        m = re.match(r'C;(?:X(\d+);)?(?:Y(\d+);)?(?:K"([^"]*)"|K([^;]*))?', line)
        if not m:
            continue
        if m.group(1):
            x = int(m.group(1))
        if m.group(2):
            y = int(m.group(2))
        val = m.group(3) if m.group(3) is not None else m.group(4)
        if x and y and val is not None:
            cells[(x, y)] = val
    headers = {cx: v for (cx, yy), v in cells.items() if yy == 1}
    # find alias/code columns
    alias_col = None
    for cx, h in headers.items():
        hl = h.lower()
        if hl in ("alias", "abilityid", "abilid"):
            alias_col = cx
            break
    if alias_col is None:
        alias_col = min(headers)
    rows = {}
    maxy = max(yy for _, yy in cells)
    for yy in range(2, maxy + 1):
        aid = cells.get((alias_col, yy))
        if not aid:
            continue
        rows[aid] = {headers[cx]: cells.get((cx, yy)) for cx in headers}
    return headers, rows


def main():
    headers, rows = parse_slk(SLK)
    # Keep abilities that look like DotA customs (A0.. / A1.. / A2..) with numeric Rng1
    out = []
    for aid, r in rows.items():
        if not re.match(r"^A[0-9A-Z]{3}$", aid):
            continue
        rng = r.get("Rng1") or r.get("rng1")
        area = r.get("Area1") or r.get("area1")
        cool = r.get("Cool1") or r.get("cool1")
        code = r.get("code")
        levels = r.get("levels")
        if rng in (None, "-", ""):
            continue
        try:
            # may be comma-separated per level
            parts = [float(x) for x in str(rng).replace(" ", "").split(",") if x not in ("", "-")]
        except ValueError:
            continue
        if not parts or max(parts) <= 0:
            continue
        out.append(
            {
                "id": aid,
                "code": code,
                "levels": levels,
                "Rng1": rng,
                "Rng1_max": max(parts),
                "Area1": area,
                "Cool1": cool,
            }
        )
    out.sort(key=lambda x: (-x["Rng1_max"], x["id"]))
    (OUT / "ability_cast_ranges.json").write_text(
        json.dumps({"count": len(out), "abilities": out}, indent=2), encoding="utf-8"
    )
    # compact top ranges markdown
    lines = [
        "| Ability | code | Rng1 | Area1 | Cool1 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for a in out[:80]:
        lines.append(f"| `{a['id']}` | `{a['code']}` | {a['Rng1']} | {a['Area1']} | {a['Cool1']} |")
    (OUT / "ability_cast_ranges_top.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("exported", len(out), "abilities; max Rng sample", out[0] if out else None)


if __name__ == "__main__":
    main()
