# -*- coding: utf-8 -*-
"""解析 6.83d Units_UnitBalance.slk 视野与移速，并检查 war3map.w3b / war3map.w3d 里的 D00B / YTlb 等"""
from pathlib import Path

MAP = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")


def parse_slk_clean(path: Path):
    cols = {}
    rows = {}
    cur_y = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("C;"):
            continue
        x = y = k = None
        for p in line.split(";")[1:]:
            if p.startswith("X") and p[1:].isdigit():
                x = int(p[1:])
            elif p.startswith("Y") and p[1:].isdigit():
                y = int(p[1:])
            elif p.startswith("K"):
                k = p[1:].strip('"')
        if y is not None:
            cur_y = y
        if x is not None and k is not None:
            if cur_y == 1:
                cols[x] = k
            else:
                rows.setdefault(cur_y, {})[x] = k
    return cols, rows


cols, rows = parse_slk_clean(MAP / "Units_UnitBalance.slk")
c2i = {v: k for k, v in cols.items()}
print("Key cols:", {k: c2i.get(k) for k in ("unitBalanceID", "sight", "nsight", "spd", "collision", "def", "defType")})

targets = ["efon", "edry", "ugho", "unec", "ebal", "umtw", "e00R", "u00M", "e011", "u00D", "Nfir", "e002", "u001"]
for y, r in sorted(rows.items()):
    uid = r.get(1, "")
    if uid in targets:
        print(
            f"  {uid:6s} (Y={y:4d}): sight={r.get(c2i['sight'], '?'):>5s}, "
            f"nsight={r.get(c2i['nsight'], '?'):>5s}, spd={r.get(c2i['spd'], '?'):>4s}, "
            f"coll={r.get(c2i['collision'], '?'):>4s}"
        )

# 检查 war3map.w3b 与 war3map.w3d 中的字符串（看 D00B / YTlb 是什么）
for fn in ("war3map.w3b", "war3map.w3d"):
    raw = (MAP / fn).read_bytes()
    print(f"\n=== {fn} ({len(raw)} bytes) ===")
    import re
    strs = re.findall(rb"[A-Za-z0-9_\\.\-]{4,}", raw)
    print("  strings:", [s.decode("ascii") for s in strs[:40]])
