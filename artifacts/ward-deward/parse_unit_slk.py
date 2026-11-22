from pathlib import Path

def parse_slk(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    cols = {}
    for line in lines[:200]:
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


def dump_unit(path: Path, unit_id: str):
    cols, rows = parse_slk(path)
    for y, r in rows.items():
        uid = str(r.get(1, "")).strip('"')
        if uid == unit_id:
            print(f"=== {path.name} {unit_id} Y={y} ===")
            for x in sorted(r):
                print(f"  X{x} ({cols.get(x, '?')}): {r[x]}")
            return True
    print(f"NOT FOUND {unit_id} in {path}")
    return False


base = Path(r"D:\Qt\workspace\War3Analysis\artifacts\neutral-stack")
for name in [
    "Units_UnitBalance.slk",
    "patch_Units_UnitBalance.slk",
    "Units_UnitWeapons.slk",
    "patch_Units_UnitWeapons.slk",
    r"UnitData.slk\UnitData.slk",
]:
    p = base / name
    if not p.exists():
        print("missing", p)
        continue
    dump_unit(p, "oeye")
    dump_unit(p, "o004")
