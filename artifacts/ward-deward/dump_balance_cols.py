from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location(
    "pmw", r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\parse_map_wards.py"
)
# Don't exec module main: reimplement parse only
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

base = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")
cols, rows = parse_slk(base / "Units_UnitBalance.slk")
print("BALANCE COLS:")
for x in sorted(cols):
    print(x, cols[x])
print("o004 row:")
for y, r in rows.items():
    if str(r.get(1, "")).strip('"') == "o004":
        for x in sorted(r):
            print(f"  {cols.get(x, 'X'+str(x))}: {r[x]}")

cols, rows = parse_slk(base / "Units_ItemData.slk")
print("ITEM COLS:")
for x in sorted(cols):
    print(x, cols[x])
for want in ["I0KF", "I05H", "I05G", "I0GH"]:
    for y, r in rows.items():
        if str(r.get(1, "")).strip('"') == want:
            print(want, {cols.get(x, f"X{x}"): r[x] for x in sorted(r)})

# UnitAbilities around oeye Y45
cols, rows = parse_slk(base / "Units_UnitAbilities.slk")
print("ABIL COLS:", cols)
for y in range(40, 55):
    if y in rows:
        print(y, {cols.get(x, f"X{x}"): rows[y][x] for x in sorted(rows[y])})
