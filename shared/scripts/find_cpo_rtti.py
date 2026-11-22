from pathlib import Path
import pefile, json

def read_slk(path):
    rows, cur_y = {}, 0
    for line in Path(path).read_text(encoding="latin-1", errors="replace").splitlines():
        if not line.startswith("C;"):
            continue
        x = y = val = None
        for part in line.split(";")[1:]:
            if part.startswith("X"):
                x = int(part[1:])
            elif part.startswith("Y"):
                y = int(part[1:])
            elif part.startswith("K"):
                val = part[1:]
        if y is not None:
            cur_y = y
            if x is None:
                x = 1
        if x is None or val is None:
            continue
        if len(val) >= 2 and val[0] == chr(34) and val[-1] == chr(34):
            val = val[1:-1]
        rows.setdefault(cur_y, {})[x] = val
    header = rows.get(1, {})
    table = {}
    for y, r in rows.items():
        if y == 1 or 1 not in r:
            continue
        table[r[1]] = {header.get(x, str(x)): v for x, v in r.items() if x in header}
    return table

mapb = read_slk(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map\Units_UnitBalance.slk")
mapd = read_slk(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map\Units_UnitData.slk")
patch = read_slk(r"D:\Qt\workspace\War3Analysis\artifacts\scoring\base\War3Patch.mpq\Units_UnitBalance.slk")
for uid in ("esen", "edry", "ebal", "ugho", "unec", "umtw", "Hjai"):
    print(uid, "mapB", mapb.get(uid, {}).get("collision"), "mapD", mapd.get(uid, {}).get("collision"), "patch", patch.get(uid, {}).get("collision"))

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-collision")
names = [
    b".?AVCPoSeparate@NIpse@@",
    b".?AVCPoPosCl@NIpse@@",
    b".?AVCPoPos@NIpse@@",
]
rep = {}
for ver, path in [
    ("1.24.4.6387", r"D:\Qt\workspace\War3Launcher\versions\1.24.4.6387\game.dll"),
    ("1.26.0.6401", r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll"),
    ("1.27.0.52240", r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll"),
]:
    data = Path(path).read_bytes()
    pe = pefile.PE(path, fast_load=True)
    entry = {}
    for name in names:
        idx = data.find(name + b"\x00")
        if idx < 0:
            entry[name.decode()] = None
            continue
        td_rva = pe.get_rva_from_offset(idx - 8)
        entry[name.decode()] = "0x%X" % td_rva
    rep[ver] = entry
    print(ver, entry)
    pe.close()
OUT.joinpath("cpo_rtti.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
