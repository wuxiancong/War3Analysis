#!/usr/bin/env python3
"""Parse Rect(...) literals for spawn/handoff rects from war3map_9.j and print centers."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "War3Script" / "war3map_9.j"
NAMES = {
    "B4", "R3", "C4", "P3", "A4", "T3", "N3", "I4", "M3", "U3", "L3", "Q3",
    "TA", "SA", "NA", "LA", "KA", "MA", "G4", "D4",
}

def main() -> None:
    text = ROOT.read_text(encoding="utf-8", errors="replace")
    pat = re.compile(
        r"set\s+(\w+)\s*=\s*Rect\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)"
    )
    for m in pat.finditer(text):
        name, a, b, c, d = m.group(1), *map(float, m.groups()[1:])
        if name not in NAMES:
            continue
        cx, cy = (a + c) / 2, (b + d) / 2
        print(f"{name}: min=({a},{b}) max=({c},{d}) center=({cx},{cy})")

if __name__ == "__main__":
    main()
