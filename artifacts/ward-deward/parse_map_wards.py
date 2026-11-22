from pathlib import Path

def parse_slk(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    cols = {}
    for line in lines[:250]:
        if not line.startswith("C;"):
            continue
        x = y = None
        k = None
        for part in line.split(";")[1:]:
            if part.startswith("X") and part[1:].isdigit():
                x = int(part[1:])
            elif part.startswith("Y") and part[1:].isdigit():
                y = int(part[1:])
            elif part.startswith("K"):
                k = part[1:]
        if y == 1 and x is not None and k is not None:
            cols[x] = k.strip('"')
    rows = {}
    cur_y = None
    row = {}
    for line in lines:
        if not line.startswith("C;"):
            continue
        x = y = None
        k = None
        for part in line.split(";")[1:]:
            if part.startswith("X") and part[1:].isdigit():
                x = int(part[1:])
            elif part.startswith("Y") and part[1:].isdigit():
                y = int(part[1:])
            elif part.startswith("K"):
                k = part[1:]
        if y is not None:
            if row and cur_y is not None:
                rows[cur_y] = row
            cur_y = y
            row = {}
        if x is not None and k is not None:
            row[x] = k
    if row and cur_y is not None:
        rows[cur_y] = row
    return cols, rows


def dump(path: Path, unit_id: str):
    cols, rows = parse_slk(path)
    for y, r in rows.items():
        if str(r.get(1, "")).strip('"') == unit_id:
            print(f"=== {path.name} {unit_id} Y={y} ===")
            for x in sorted(r):
                print(f"  X{x} ({cols.get(x, '?')}): {r[x]}")
            return True
    print(f"NOT FOUND {unit_id} in {path.name}")
    return False


base = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")
files = [
    "Units_UnitBalance.slk",
    "Units_UnitData.slk",
    "Units_UnitWeapons.slk",
    "Units_UnitAbilities.slk",
    "Units_UnitUI.slk",
    "Units_ItemData.slk",
]
for name in files:
    p = base / name
    print(name, "exists", p.exists(), "size", p.stat().st_size if p.exists() else 0)

for uid in ["o004", "oeye"]:
    for name in files[:-1]:
        p = base / name
        if p.exists():
            dump(p, uid)

# items with Adtg / AItb / Agyv / ward place
item_path = base / "Units_ItemData.slk"
if item_path.exists():
    cols, rows = parse_slk(item_path)
    print("ItemData cols:", dict(sorted(cols.items())[:30]))
    for y, r in rows.items():
        vals = " ".join(str(v) for v in r.values())
        uid = str(r.get(1, "")).strip('"')
        if any(k in vals for k in ("Adtg", "Agyv", "AItb", "A2WH", "A2WI", "AIsw", "A02X")):
            nice = {cols.get(x, f"X{x}"): r[x] for x in sorted(r)}
            print("ITEM", uid, nice)
